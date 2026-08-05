#!/usr/bin/env python3
"""Pre-publish QA gate for The Long Swell.

Run before any push that publishes to docs/. Stdlib only, so it works
with bare python3 in CI and with .venv/bin/python locally.

Checks:
  1. Em-dash guard: no U+2014 outside the documented allowlist
     (CLAUDE.md invariant 6).
  2. Immutability: files under docs/briefs/ and snapshots/ that exist
     at the base ref are never modified or deleted (invariants 4, 5).
  3. Internal links: every relative href/src in docs/ HTML resolves to
     a file that exists.
  4. Structure: front page, methodology page, CNAME, and per-brief
     index.html + analog.png all present.
  5. snapshots/*.json parse as JSON.

Usage:
  scripts/qa_check.py                  local run, base = origin/main
  scripts/qa_check.py --base SHA       CI run, explicit base
  scripts/qa_check.py --no-frozen-check
  scripts/qa_check.py --allow-frozen-edits   emergency --force fixes only

Exit 0 when clean, 1 when any violation is printed.
"""

import argparse
import json
import re
import subprocess
from datetime import date
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EMDASH = "\u2014"
# Built from the escape so this file never contains the literal char.

# Documented legitimate em-dash carriers; must not grow (invariant 6).
EMDASH_ALLOWLIST = {
    "LICENSE",
    "docs/briefs/2026-05-18/index.html",
    "docs/briefs/2026-05-25/index.html",
    "fetchers/iri.py",
}

TEXT_SUFFIXES = {
    ".py", ".md", ".html", ".htm", ".yml", ".yaml", ".txt", ".css",
    ".js", ".svg", ".json", ".csv", ".toml", ".cfg", ".ini", "",
}

FROZEN_PREFIXES = ("docs/briefs/", "snapshots/")

# What is actually immutable inside those prefixes: a dated archive
# directory, and a dated snapshot. NOT docs/briefs/index.html, which is
# the rolling archive listing that every weekly run rewrites by design
# (run_brief.py step 7); treating it as frozen would fail every Monday.
FROZEN_PATH_RE = re.compile(
    r"^(docs/briefs/\d{4}-\d{2}-\d{2}/|snapshots/\d{4}-\d{2}-\d{2}\.json$)")

CANONICAL_DOMAIN = "thelongswell.com"

LINK_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "data:", "//", "javascript:")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "data:", "//", "#", "javascript:")

# Empty, and it should stay that way. It once held the eleven archives
# whose 'Past briefs' nav link resolved nowhere; those were repaired on
# 2026-07-27 under Kristjan's ruling that immutability protects the
# CONTENT of a report, not its navigation or styling. A suppression here
# is a defect we have agreed to keep shipping, so each entry needs a
# dated reason and an owner, not just a key.
KNOWN_FROZEN_DEFECTS: set[tuple[str, str]] = set()


def git(*args):
    out = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    return out.returncode, out.stdout


def repo_files():
    """Tracked plus untracked-but-not-ignored files, as repo-relative paths."""
    code, out = git("ls-files", "-co", "--exclude-standard", "-z")
    if code != 0:
        return []
    return [p for p in out.split("\0") if p]


def check_emdash(violations):
    for rel in repo_files():
        path = ROOT / rel
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = [i + 1 for i, line in enumerate(text.splitlines()) if EMDASH in line]
        if not hits:
            continue
        if rel in EMDASH_ALLOWLIST:
            continue
        violations.append(
            f"em-dash: {rel} lines {', '.join(map(str, hits[:10]))}"
            + (" ..." if len(hits) > 10 else "")
        )


def check_frozen(violations, base):
    code, _ = git("cat-file", "-e", base)
    if code != 0:
        violations.append(f"frozen-check: base ref '{base}' not found; "
                          "run with --base or --no-frozen-check")
        return
    # Diff base against the working tree; statuses M and D on files that
    # exist at base. Newly added briefs and snapshots show as A and pass.
    _, out = git("diff", "--name-status", "--diff-filter=MD", base, "--",
                 *[p.rstrip("/") for p in FROZEN_PREFIXES])
    for line in out.splitlines():
        status, _, rel = line.partition("\t")
        if not FROZEN_PATH_RE.match(rel):
            continue
        violations.append(f"immutable surface modified ({status}): {rel}")


def check_links(violations):
    docs = ROOT / "docs"
    for html in sorted(docs.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="ignore")
        for url in LINK_RE.findall(text):
            if url.startswith(SKIP_SCHEMES):
                continue
            target = url.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if target.startswith("/"):
                violations.append(
                    f"root-absolute link in {html.relative_to(ROOT)}: {url} "
                    "(breaks on the github.io project path; use relative)")
                continue
            rel_html = str(html.relative_to(ROOT))
            if (rel_html, url) in KNOWN_FROZEN_DEFECTS:
                continue
            if not target:
                continue
            resolved = (html.parent / target).resolve()
            if resolved.is_dir():
                # Pages serves no directory listings; a dir link 404s
                # without an index.html inside.
                if not (resolved / "index.html").is_file():
                    violations.append(
                        f"dead link in {rel_html}: {url} "
                        "(directory without index.html)")
            elif not resolved.exists():
                violations.append(f"dead link in {rel_html}: {url}")


def check_fragments(violations):
    """Every #anchor must have a matching id on the page it lands on.

    Design chat's catch, 2026-07-28, and it exposed a real hole: the link
    check above strips the fragment and skips pure '#anchor' links
    entirely, so the front page carried three href="#issue" links with no
    id="issue" anywhere on it and stayed green for as long as they were
    broken. They were written when the front page WAS the issue page and
    were orphaned by the split to /elnino/.

    A dead anchor is a navigation path that silently does nothing, which
    is worse than a 404: the reader gets no feedback at all. Local check,
    no network.
    """
    docs = ROOT / "docs"
    ids_cache: dict[Path, set[str]] = {}

    def ids_of(path: Path) -> set[str]:
        if path not in ids_cache:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            ids_cache[path] = set(re.findall(r'\bid="([^"]+)"', text))
        return ids_cache[path]

    for html in sorted(docs.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="ignore")
        rel = str(html.relative_to(ROOT))
        for url in LINK_RE.findall(text):
            # NOT SKIP_SCHEMES here: it contains "#", so reusing it skips
            # every same-page anchor, which is exactly what this function
            # exists to check. Caught by testing against the known-bad
            # page rather than by reading the code.
            if "#" not in url or url.startswith(EXTERNAL_SCHEMES):
                continue
            page_part, _, frag = url.partition("#")
            if not frag or frag == "top":      # "#top" is a browser builtin
                continue
            target_page = html if not page_part else (html.parent / page_part)
            if target_page.is_dir():
                target_page = target_page / "index.html"
            if not target_page.exists():
                continue                        # dead link, already reported
            if frag not in ids_of(target_page):
                where = "same page" if target_page == html else \
                    str(target_page.relative_to(ROOT))
                violations.append(
                    f"dead anchor in {rel}: #{frag} has no matching id "
                    f"on {where}")


def check_structure(violations):
    docs = ROOT / "docs"
    for required in ("index.html", "methodology.html"):
        if not (docs / required).is_file():
            violations.append(f"structure: docs/{required} missing")
    # docs/CNAME is what sets the Pages custom domain. Absent is valid
    # (serving from github.io); present with the wrong host silently
    # hands the site to another domain, so that is a failure.
    cname = docs / "CNAME"
    if cname.is_file():
        content = cname.read_text(encoding="utf-8").strip()
        if content != CANONICAL_DOMAIN:
            violations.append(
                f"structure: docs/CNAME is '{content}', "
                f"expected '{CANONICAL_DOMAIN}'")
    briefs = docs / "briefs"
    if briefs.is_dir():
        for day in sorted(p for p in briefs.iterdir() if p.is_dir()):
            for required in ("index.html", "analog.png"):
                if not (day / required).is_file():
                    violations.append(
                        f"structure: {day.relative_to(ROOT)}/{required} missing")


# Known, ACCEPTED disappearances, as (snapshot file, block). Each is a
# defect we have agreed to ship, so each needs a dated reason and a fix
# date, not just a key.
#
# These five are the 2026-08-03 CWWA outage. The era5_wwe fetch failed
# AND its cache read failed, and the snapshot still reported ok:True, so
# the chart published an empty panel. Fixed by the ENSO tracker in
# b3679e2 (read_cache raises rather than swallowing, safe_fetch gains
# required_keys so a degraded success falls back). The snapshot itself is
# frozen under invariant 5 and correctly stays wrong: nothing in it is
# false, the fetch genuinely failed. The fix lands in the 2026-08-10
# issue, and these entries should be DELETED once that snapshot exists,
# at which point the diff compares 08-03 to 08-10 and goes quiet on its
# own.
KNOWN_SNAPSHOT_GAPS = {
    ("2026-08-03.json", "physical_state.cwwa_analogs"),
    ("2026-08-03.json", "physical_state.cwwa_domain"),
    ("2026-08-03.json", "physical_state.cwwa_ms_days"),
    ("2026-08-03.json", "physical_state.cwwa_series"),
    # Not part of the outage: a stale April seed the ENSO tracker removed
    # in the same commit, which had been rendering only on the failure
    # path and so went unreviewed for months.
    ("2026-08-03.json", "physical_state.heat_content_qualitative"),
}


# A UTC time stated in these files is a claim about when a job runs, and
# the workflow is the only thing that decides that. Design's observation,
# 2026-08-04, after four defects in a few days that shared one shape: a
# number was right when written and its inputs moved afterwards.
#
# THE TWO CLASSES, because only one of them was already covered.
#
#   (a) the OUTPUT drifted from its generator. The El Nino index still
#       carrying last week's date, the front page missing a contrast fix.
#       `publish_all --check --assert-clean` catches these, because
#       regenerating produces something different.
#
#   (b) the GENERATOR hard-codes a fact that lives somewhere else. The
#       fires page telling readers "refreshed once daily at 06:00 UTC"
#       when the cron had moved to 03:10. Regenerating reproduces the
#       wrong string faithfully, so (a)'s check passes and always will.
#
# This is (b), for the one fact that has already gone stale twice: the
# schedule. The truth side is DERIVED from the workflow rather than
# listed here, or this guard would go stale the same way.
SCHEDULE_CLAIM_FILES = [
    "fires/build_events.py",
    "fires/build_page.py",
    "scripts/publish_all.py",
    "scripts/check_freshness.py",
]

# Times that are legitimately not schedule slots. Each needs a reason:
# an unexplained entry here turns the guard back into the thing it
# replaced.
NON_SCHEDULE_TIMES = {
    "03:00": "FIRMS near-real-time processing floor, a data-availability "
             "fact rather than a slot. build_events.py refuses before it.",
}

# Known-stale claims, with an owner and a fix path. Same discipline as
# KNOWN_SNAPSHOT_GAPS: a suppression is a defect we have agreed to ship.
KNOWN_STALE_SCHEDULE_CLAIMS = {
    # fires/build_events.py is the Fire chat's. Its module docstring and
    # its refusal message still describe the retired 06:00 slot. Not
    # reader-facing, but it misled a diagnosis on 2026-08-01, which is
    # what stale internal documentation costs. Reported to Fire
    # 2026-08-04; delete this once they land the wording.
    ("fires/build_events.py", "06:00"),
}


def _cron_times(workflow: str) -> set[str]:
    """HH:MM slots declared by a workflow's cron lines."""
    path = ROOT / ".github" / "workflows" / workflow
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    out = set()
    for m in re.finditer(r'cron:\s*["\'](\S+)\s+(\S+)\s', text):
        minute, hour = m.group(1), m.group(2)
        if minute.isdigit() and hour.isdigit():
            out.add(f"{int(hour):02d}:{int(minute):02d}")
    return out


def check_schedule_claims(violations):
    """Does any file state a run time the workflow does not have?"""
    valid = _cron_times("fires.yml")
    if not valid:
        return
    for rel in SCHEDULE_CLAIM_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # A bare "HH:MM UTC" is not enough, and the first version of this
        # check proved it by flagging build_events.py's worked example
        # ("Spain read 4,524 at 15:15 UTC, 4,700 at 15:55"). Those are
        # measurement timestamps, not schedule claims, and a guard that
        # cries wolf on them gets switched off.
        #
        # So the time must sit near a word that makes it a claim about
        # WHEN SOMETHING RUNS. This deliberately under-reports: a stale
        # time phrased without any of these words is missed. That is the
        # right direction to fail, because a missed instance costs one
        # defect and a false positive costs the whole check.
        for m in re.finditer(
                r"(?:runs?|run at|slot|schedul\w*|refreshed|cron|job|"
                r"pull a day|once daily|daily at)[^.\n]{0,60}?"
                r"\b(\d{2}:\d{2})\s*UTC", text, re.I):
            claimed = m.group(1)
            if claimed in valid or claimed in NON_SCHEDULE_TIMES:
                continue
            if (rel, claimed) in KNOWN_STALE_SCHEDULE_CLAIMS:
                continue
            line = text[:m.start()].count("\n") + 1
            violations.append(
                f"{rel}:{line} states '{claimed} UTC', which is not a slot "
                f"the workflow declares ({', '.join(sorted(valid))}). A "
                f"schedule written into prose goes stale the moment the "
                f"cron moves, and regenerating the page reproduces it "
                f"faithfully, so nothing else catches it.")


# D-078: a published page may not lag its own data.
#
# THE DEFECT IT EXISTS FOR. On 2026-08-04 docs/index.html served the
# 07-27..08-02 fire week all day while fires/data/current_week.json had
# held 07-28..08-03 since 11:49. Greece read 11.3x live against 11.5x in
# the data, and 19 countries clearing against 14. Fire computed and
# committed the week correctly; the page was simply never regenerated.
#
# WHY THIS IS NOT REDUNDANT WITH docs-match-source, which is the
# objection I raised before it was ratified and which I now think was
# wrong. That check regenerates and compares, so it catches "the page
# drifted from its generator". It structurally CANNOT catch "the
# generator itself read stale data", because regenerating reproduces the
# stale period faithfully and the comparison passes. This check reads the
# period off the rendered page and compares it to the data file, so it
# sees that case. The two overlap on the common defect and each catches
# something the other cannot.
#
# ARCHIVES ARE EXCLUDED. docs/briefs/<date>/ is deliberately old under
# invariant 5; a frozen brief rendering a frozen week is the system
# working. Only rolling pages are checked.
#
# NOT-OLDER-THAN rather than equality, which was Product's second open
# question. Equality would also fail when a page is NEWER than its data,
# which is a different and much rarer defect (a page rendering something
# no commit supports) and is better caught by docs-match-source. Here the
# only assertion is that the data has not moved past the page.
PAGE_DATA_PAIRS = [
    # front=True marks the highest-consequence artifact we have. Product's
    # option 1: a stale docs/index.html is not the same event as a stale
    # country page, and reporting them identically is part of why three
    # red runs on the front page changed nothing for a morning. The front
    # page is what a first-time reader meets.
    {"page": "docs/index.html", "data": "fires/data/current_week.json",
     "what": "the front page fire week", "front": True},
    {"page": "docs/fires/index.html", "data": "fires/data/current_week.json",
     "what": "the fires channel index"},
    {"page": "docs/crops/index.html", "data": "crops/data/stress_current.json",
     "what": "the crops channel index"},
]


def _page_period(text: str):
    """Newest period a rendered page claims, as a comparable date.

    Pages stamp their period in three different formats, so this reads
    all of them rather than assuming one. Tags are stripped first: a
    phrase that reads as one string on the page is routinely split
    across elements in the source, and grepping raw HTML for it finds
    nothing and looks like proof of absence.
    """
    # TWO strippings, and the reason is the trap this file documents
    # elsewhere. Replacing a tag with a SPACE keeps words apart, which is
    # right for prose, but "<b>07-27</b>..08-02" then becomes
    # "07-27 ..08-02" and no contiguous pattern matches it. Replacing with
    # nothing rejoins the period but can weld unrelated words together.
    # So search both and take whatever either finds.
    #
    # This is not hypothetical: the first version of this check used only
    # the spaced form and scored zero against a faithful reproduction of
    # the 2026-08-04 defect it was written for. Caught by making it fail,
    # per D-069 rule 2, and it is a fair joke on me that I wrote the
    # split-across-tags warning into CLAUDE.md the same afternoon.
    flat = re.sub(r"<[^>]+>", " ", text) + "\n" + re.sub(r"<[^>]+>", "", text)
    best = None
    # "07-28..08-03": take the END of the window, in the current year.
    for m in re.finditer(r"(\d{2})-(\d{2})\.\.(\d{2})-(\d{2})", flat):
        try:
            d = date(date.today().year, int(m.group(3)), int(m.group(4)))
        except ValueError:
            continue
        if d > date.today():
            d = d.replace(year=d.year - 1)
        best = max(best, d) if best else d
    # "dekad 2026-07-11" and "week of 2026-08-03"
    for pat in (r"dekad\s+(\d{4}-\d{2}-\d{2})", r"[Ww]eek of (\d{4}-\d{2}-\d{2})"):
        for m in re.finditer(pat, flat):
            try:
                d = date.fromisoformat(m.group(1))
            except ValueError:
                continue
            best = max(best, d) if best else d
    return best


def _data_period(doc: dict):
    w = doc.get("window")
    if isinstance(w, str):
        m = re.search(r"(\d{2})-(\d{2})\.\.(\d{2})-(\d{2})", w)
        if m:
            try:
                d = date(date.today().year, int(m.group(3)), int(m.group(4)))
                return d.replace(year=d.year - 1) if d > date.today() else d
            except ValueError:
                pass
    for key in ("dekad", "as_of", "observation_date"):
        v = doc.get(key)
        if isinstance(v, str):
            try:
                return date.fromisoformat(v[:10])
            except ValueError:
                continue
    return None


def check_page_lags_data(violations):
    for pair in PAGE_DATA_PAIRS:
        page, data = ROOT / pair["page"], ROOT / pair["data"]
        if not page.exists() or not data.exists():
            continue
        try:
            doc = json.loads(data.read_text(encoding="utf-8"))
            text = page.read_text(encoding="utf-8", errors="ignore")
        except (OSError, ValueError):
            continue
        p_period, d_period = _page_period(text), _data_period(doc)
        if p_period is None or d_period is None:
            continue
        if d_period > p_period:
            lead = ("FRONT PAGE STALE: " if pair.get("front")
                    else "page lags its data: ")
            violations.append(
                lead +
                f"{pair['page']} renders {p_period} but {pair['data']} has "
                f"advanced to {d_period}. {pair['what'].capitalize()} is "
                f"showing older numbers than the committed data, which is "
                f"exactly what shipped on 2026-08-04: the front page served "
                f"Greece at 11.3x for a day while the data said 11.5x. Run "
                f"scripts/publish_all.py and commit. (D-078)")


def _leaf_paths(obj, prefix=()):
    """Every path to a non-empty leaf. Empty containers count as absent."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaf_paths(v, prefix + (str(k),))
    elif isinstance(obj, list):
        if obj:
            yield prefix
    elif obj is not None and obj != "":
        yield prefix


def check_snapshot_regression(violations):
    """Did a field that existed last week vanish this week?

    The ENSO tracker's ask, after the CWWA panel published empty on
    2026-08-03. The fetcher failed, its cache read ALSO failed, and the
    snapshot still reported ok:True with used_fallback:False. Nothing in
    the pipeline said anything was wrong; the defect was visible only as
    a blank panel on the page, and Kristjan found it there.

    WHY A WEEK-OVER-WEEK DIFF RATHER THAN A MUST-EXIST LIST, which is
    their design point and a good one. Several fields are seasonal:
    cwwa_* and wwb_* do not exist before March 1 of a develop year. An
    absolute list would cry wolf every January. A diff is self-correcting,
    because a seasonal field is absent in BOTH weeks and the check stays
    quiet, firing only on a real disappearance.

    THE INVERSE, also theirs: physical_state is seeded ok:True by
    construction, so its ok flag says nothing about whether live data
    arrived. When a field vanishes while ok is still True, that
    contradiction is worth naming separately, because it is the thing
    that made the snapshot look healthy.
    """
    snaps = sorted((ROOT / "snapshots").glob("[0-9]" * 4 + "-*.json"))
    if len(snaps) < 2:
        return
    prev_path, curr_path = snaps[-2], snaps[-1]
    try:
        prev = json.loads(prev_path.read_text(encoding="utf-8"))
        curr = json.loads(curr_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return   # check_snapshots already reports unparseable snapshots

    gone = sorted(set(_leaf_paths(prev)) - set(_leaf_paths(curr)))
    gone = [p for p in gone
            if (curr_path.name, ".".join(p[:2])) not in KNOWN_SNAPSHOT_GAPS]
    if not gone:
        return

    # Collapse to the top two levels: losing 40 leaves under one block is
    # one defect, and listing all 40 buries it.
    blocks = sorted({".".join(p[:2]) for p in gone})
    for block in blocks[:12]:
        violations.append(
            f"snapshot regression: '{block}' had data in "
            f"{prev_path.name} and is empty or absent in {curr_path.name}. "
            f"A field that stops arriving is how the CWWA panel published "
            f"blank on 2026-08-03: every check passed because nothing "
            f"asserts that last week's data is still there. If this "
            f"disappearance is legitimate, it needs a reason.")

    ps = curr.get("physical_state")
    if isinstance(ps, dict) and ps.get("ok") is True:
        phys_gone = [b for b in blocks if b.startswith("physical_state")]
        if phys_gone:
            violations.append(
                f"physical_state reports ok:True in {curr_path.name} while "
                f"{len(phys_gone)} of its block(s) lost data since "
                f"{prev_path.name}. That block is seeded ok:True by "
                f"construction, so the flag says nothing about whether live "
                f"data arrived, which is exactly what made the 2026-08-03 "
                f"snapshot look healthy.")


def check_snapshots(violations):
    snaps = ROOT / "snapshots"
    if not snaps.is_dir():
        return
    for path in sorted(snaps.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            violations.append(f"snapshot unparseable: {path.name}: {exc}")


# Fields a channel emits that no renderer is expected to read. Each one
# needs a REASON, because the whole point is to force a decision rather
# than let a field rot quietly. Adding a name here is a claim that the
# field is deliberately not rendered, not that it is inconvenient.
DECLARED_UNUSED = {
    # Fire chat, 2026-07-30. z is the standardised anomaly and it is one
    # of the three OR-ed signals the gate runs on, so it decides which
    # countries appear. It is deliberately not shown.
    #
    # Two reasons. It is emitted for downstream consumers rather than
    # readers: ECON joins on this file and z is the only field that says
    # how unusual a week is in a form comparable ACROSS countries, which
    # the multiple is not. And "2.5 standard deviations above the
    # same-week mean" is the wrong register for the 4-8 reader D-043
    # names, who wants to know how serious this is, not how it was
    # computed. The multiple and the rank carry that in plain language.
    #
    # If a page ever wants to rank or sort by how unusual a week is
    # rather than by ratio, this is the field to use. Revisit then.
    "z": "gate input and downstream join key; wrong register for readers",
}

# Channel JSON, and the renderers that consume it. A field present in
# the former and absent from all of the latter is either a defect or a
# declaration waiting to be written.
EMITTED_FIELD_SOURCES = [
    {"data": "data/events.json", "collection": "events",
     "renderers": ["fires/build_page.py", "fires/build_country_pages.py",
                   "run_brief.py"]},
]


# THE RESERVED NAMESPACE (Design's proposal, 2026-08-03).
#
# A key prefixed with "_" is guidance to the pipeline and is NEVER
# reader-facing. A renderer that prints one is a bug; a channel that puts
# reader copy there is also a bug.
#
# Underscore rather than a single `_internal` block, for two reasons.
# It is already the de facto convention: `_readme` appears in
# data/events.json and three fires payloads without anyone specifying
# it. And it keeps the guidance ADJACENT to the field it qualifies,
# which a separate block cannot: ECON's `scope` needs a note about
# `scope`, and `_scope_note` sits next to it while `_internal.scope_note`
# drifts away from the thing it is about.
#
# WHAT THIS DOES NOT FIX, and why Design's second clause is the load
# bearing one. A namespace cannot split a field that does two jobs
# inside ONE string. ECON's `scope` opens with a genuine reader-facing
# scope statement and ends with "Must never render as a Spain figure",
# and that printed on a page. No prefix rule reaches inside a string.
# The field has to split, which is a channel migration, and this guard
# only protects the result once it has happened.
RESERVED_PREFIX = "_"

# Below this length a value is too short to attribute confidently: a
# reserved value of "n/a" would match half the site and produce noise
# that gets the check ignored. Long internal prose is the actual failure
# mode, and it is well above this.
RESERVED_MIN_LEN = 30


def _reserved_values(obj, out):
    """Every string under a reserved key, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith(RESERVED_PREFIX):
                if isinstance(v, str):
                    out.append(v)
                else:
                    _collect_strings(v, out)
            else:
                _reserved_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _reserved_values(v, out)


def _collect_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out)


def check_reserved_not_rendered(violations):
    """Nothing in the reserved namespace may reach a rendered page.

    Design's ask, after two internal directives printed at readers in one
    day: ECON's "Must never render as a Spain figure" and a CRO note
    telling the renderer which field to prefer. Both were caught by a
    human looking at the page, which is not a mechanism.

    Same shape as the analytics-tag and masthead assertions in
    publish_all: a substring check over the built HTML. Cheap, and it
    fails at publish rather than on the page.
    """
    values: list[str] = []
    for pattern in ("*/data/*.json", "data/*.json"):
        for path in sorted(ROOT.glob(pattern)):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            found: list[str] = []
            _reserved_values(doc, found)
            values.extend(v for v in found if len(v) >= RESERVED_MIN_LEN)

    if not values:
        return

    docs = ROOT / "docs"
    for html in sorted(docs.rglob("*.html")):
        try:
            text = html.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for v in values:
            if v in text:
                violations.append(
                    f"{html.relative_to(ROOT)} renders a reserved-namespace "
                    f"value, which is pipeline guidance and not reader copy: "
                    f"\"{v[:70]}...\". A key prefixed '{RESERVED_PREFIX}' must "
                    f"never reach a page.")


def check_emitted_fields(violations):
    """Is every field a channel emits actually read by a renderer?

    D-046, from the live UK/Spain defect on 2026-07-29. The Fire chat
    emits `pinned` specifically so a country held in the set for
    continuity cannot render like one at a genuine anomaly. No renderer
    reads it, so the United Kingdom at 407 detections rendered
    identically to Spain at 14.1x and was counted in a live headline
    about countries burning above their seasonal normal.

    Nothing structural was wrong: the page was well-formed, the numbers
    matched the record, every existing guard passed. The failure was a
    field crossing the channel-to-design seam and being dropped on the
    far side, which is invisible to any check that looks at one side.

    HOW IT MATCHES, and the limit is worth stating. It greps the
    renderer sources for the quoted field name, so it proves a name is
    MENTIONED, not that it changes anything rendered. A renderer that
    reads a field and ignores it still passes. It also cannot see
    dynamic access such as `e[k] for k in keys`. So this catches the
    dropped-on-the-floor case, which is the one that has actually
    happened, and is not a substitute for the owning channel signing off
    on its rendered page.
    """
    for spec in EMITTED_FIELD_SOURCES:
        path = ROOT / spec["data"]
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            violations.append(f"emitted-field check: {spec['data']} "
                              f"unreadable: {exc}")
            continue
        rows = doc.get(spec["collection"]) or []
        if not isinstance(rows, list):
            continue
        emitted = sorted({k for r in rows if isinstance(r, dict) for k in r})

        sources = {}
        for rel in spec["renderers"]:
            p = ROOT / rel
            sources[rel] = p.read_text(encoding="utf-8") if p.exists() else ""

        for field in emitted:
            # Reserved keys are exempt BY CONSTRUCTION: they are pipeline
            # guidance, so 'no renderer reads it' is the correct state
            # rather than a defect. check_reserved_not_rendered asserts
            # the other half, that they never reach a page.
            if field.startswith(RESERVED_PREFIX) or field in DECLARED_UNUSED:
                continue
            pattern = re.compile(r"""["']%s["']""" % re.escape(field))
            if any(pattern.search(text) for text in sources.values()):
                continue
            carrying = sum(1 for r in rows if r.get(field) not in (None, False))
            violations.append(
                f"{spec['data']} emits '{field}' ({carrying} of {len(rows)} "
                f"rows carry a value) but no renderer reads it: "
                f"{', '.join(spec['renderers'])}. Either render it or add it "
                f"to DECLARED_UNUSED in scripts/qa_check.py with a reason. "
                f"A field that crosses the seam and is dropped is how a "
                f"non-anomalous country renders like an anomalous one.")


# 5 MB. Nothing this project legitimately commits approaches it: the
# largest non-exempt tracked file is a 0.6 MB derived JSON, and the
# published card PNGs are 0.4 MB. So the threshold sits far above normal
# and far below anything that would matter, which is where a size gate
# belongs.
LARGE_FILE_MAX_BYTES = 5 * 1024 * 1024

# MEASURED COMPRESSED, NOT ON DISK, and the first version got this wrong.
#
# The cost this guard exists to prevent is permanent growth of git
# HISTORY, and git stores objects compressed and delta-compressed. So
# on-disk size is a proxy adjacent to the thing that matters, which is
# the error class that produced half of this week's defects.
#
# The two cases, measured 2026-08-05:
#
#   crops/data/stress_current.json   7.90 MB raw -> 0.87 MB gz   (11%)
#   the 20.7 MB IMERG grid           20.71 MB raw -> 20.68 MB gz (100%)
#
# Raw size calls those the same kind of problem. Compressed size
# separates them exactly, and for the right reason rather than by luck:
# a raw grid is already compressed so it cannot shrink, while a derived
# text payload is one value per line and compresses about ninefold. It
# also deltas well between dekads, which raw size cannot see at all.
#
# So the crops payload passes at 0.87 MB with real headroom and needs no
# exception, and the grid still fails by a factor of four. Fixing the
# measure beat granting an allowlist entry, because an allowlist would
# have left the guard wrong for every future text payload.
#
# NOT raising the threshold, which Design flagged and was right to. A
# guard whose limit moves when a file crosses it manufactures its own
# answer and never fires again.
def _compressed_size(path: Path) -> int:
    import gzip
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    return len(gzip.compress(data, compresslevel=6))

# Files we have decided to keep despite the rule. Each needs a REASON,
# because the entry IS the decision record.
# Empty, and it should stay that way. The one file that would have been
# here, a 20.7 MB IMERG grid committed 2026-07-29 before the *.npz
# ignore rule existed, was untracked by the Floods chat in f54d70f
# ("stop tracking raw grids; commit the derived artifact instead"). The
# blob is still in HISTORY, which is why the pack is 34 MB against 0.6 MB
# of largest tracked file, but nothing oversized is tracked now.
#
# An entry here is a decision to keep shipping something the rule says
# we should not, so it needs a dated reason and an owner, not just a key.
LARGE_FILE_ALLOWED: dict[str, str] = {}


def check_large_files(violations):
    """Is anything oversized being committed?

    Strategy's ask, 2026-08-03, and their framing is the right one: this
    is the same shape as the emitted-field defect. Each instance is fine
    in isolation and only repetition makes it a problem, so nobody
    notices at the moment it is introduced. A check catches the class;
    noticing catches one instance, late.

    The concrete case: a 20.7 MB grid landed on 2026-07-29 and pushed
    before anyone saw it. Git history cannot be trimmed afterwards
    without a force-push, so the only cheap moment is the commit that
    introduces it. This is that moment, mechanised.

    Measures the WORKING TREE rather than git objects, deliberately. The
    question is "should this be committed", which is about the file, and
    a size check that needed a packed repo would answer too late.
    """
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.split("\0")
    except (OSError, subprocess.CalledProcessError) as exc:
        violations.append(f"large-file check could not list tracked "
                          f"files: {exc}")
        return

    for rel in tracked:
        if not rel or rel in LARGE_FILE_ALLOWED:
            continue
        path = ROOT / rel
        try:
            raw = path.stat().st_size
        except OSError:
            continue
        # Cheap skip: nothing can compress to more than its raw size, so
        # a file under the limit on disk is under it compressed too.
        if raw <= LARGE_FILE_MAX_BYTES:
            continue
        size = _compressed_size(path)
        if size > LARGE_FILE_MAX_BYTES:
            violations.append(
                f"{rel} is {size / 1048576:.1f} MB compressed "
                f"({raw / 1048576:.1f} MB on disk), over the "
                f"{LARGE_FILE_MAX_BYTES / 1048576:.0f} MB limit for a "
                f"tracked file. Raw grids and captures belong in the "
                f"GitHub Release store, not in git history, which cannot "
                f"be trimmed later without a force-push. If this one is "
                f"genuinely meant to be committed, add it to "
                f"LARGE_FILE_ALLOWED in scripts/qa_check.py with a reason.")


ALLHANDS_MAX_ENTRIES = 10
ALLHANDS_MAX_AGE_DAYS = 30


def check_allhands(violations):
    """Is the all-hands board still inside its cap?

    D-059 caps `research/allhands.md` at ten entries or thirty days,
    deleted rather than archived, because EVERY chat pays its read cost
    EVERY session. An uncapped broadcast board stops being cheaper than
    the messages it replaced, which was its entire justification.

    Product asked for this as a guard rather than a note, on the house
    rule that a thing which can regress becomes a guard. They are right
    about the specific risk: a size rule is exactly the kind that holds
    for three weeks and then quietly stops, and nothing about a slightly
    too-long file looks wrong when you open it.

    SKIPS SILENTLY WHEN research/ IS ABSENT. That directory is a
    separate private repo which this public one gitignores, so CI has no
    copy and a missing file here means "not applicable", not "failing".
    """
    path = ROOT / "research" / "allhands.md"
    if not path.exists():
        return

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        violations.append(f"allhands.md unreadable: {exc}")
        return

    # Entries are dated H2 headings; the prose sections above them are
    # not entries and must not count against the cap.
    entries = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})\b", text, re.M)
    if len(entries) > ALLHANDS_MAX_ENTRIES:
        violations.append(
            f"research/allhands.md has {len(entries)} entries, cap is "
            f"{ALLHANDS_MAX_ENTRIES} (D-059). Delete the oldest rather "
            f"than archiving them: every chat reads this file every "
            f"session, so length is the cost.")

    today = date.today()
    for d in entries:
        try:
            age = (today - date.fromisoformat(d)).days
        except ValueError:
            violations.append(f"research/allhands.md: unparseable entry "
                              f"date '{d}'")
            continue
        if age > ALLHANDS_MAX_AGE_DAYS:
            violations.append(
                f"research/allhands.md entry dated {d} is {age} days old, "
                f"cap is {ALLHANDS_MAX_AGE_DAYS} (D-059). Delete it. An "
                f"entry nobody has objected to in a month has been "
                f"absorbed or has stopped mattering.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main",
                    help="ref to compare frozen surfaces against")
    ap.add_argument("--no-frozen-check", action="store_true")
    ap.add_argument("--allow-frozen-edits", action="store_true",
                    help="skip immutability check for emergency --force fixes")
    # Severity split, deliberate. The checks above answer "is it safe to
    # publish this": a broken link or a moved archive is a reason to stop.
    # The emitted-field check answers "is the rendering complete", and an
    # incomplete rendering is a defect that should NOT also freeze the
    # daily page, because a stale page is worse than an imperfect one.
    # That is not theoretical: publish_all gates on this script, so
    # making a channel-owned rendering gap blocking would have stopped
    # the 04:00 UTC fire publish tomorrow morning.
    #
    # So publish_all passes --for-publish and gets a warning; CI does not
    # and goes red. Pages deploys from the branch, so a red CI cannot
    # un-publish anything. Visible pressure, no hostage taken.
    ap.add_argument("--for-publish", action="store_true",
                    help="downgrade rendering-completeness findings to "
                         "warnings so a publish is never blocked by them")
    args = ap.parse_args()

    violations = []
    advisories = []
    check_emdash(violations)
    if not (args.no_frozen_check or args.allow_frozen_edits):
        check_frozen(violations, args.base)
    check_links(violations)
    check_fragments(violations)
    check_structure(violations)
    check_snapshots(violations)
    check_snapshot_regression(violations)
    check_schedule_claims(violations)
    check_page_lags_data(violations)
    check_emitted_fields(advisories if args.for_publish else violations)
    check_allhands(violations)
    check_large_files(violations)
    check_reserved_not_rendered(violations)

    if advisories:
        print(f"QA ADVISORY: {len(advisories)} rendering-completeness "
              f"finding(s). Not blocking this publish.\n")
        for a in advisories:
            print(f"  {a}")
        print()

    if violations:
        print(f"QA FAILED: {len(violations)} violation(s)\n")
        for v in violations:
            print(f"  {v}")
        return 1
    print("QA clean." if not advisories else "QA clean apart from the "
          "advisories above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
