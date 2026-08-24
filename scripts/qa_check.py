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
import ast
import json
import posixpath
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
    # The four cwwa_* entries for 2026-08-03 were HERE and are gone, on
    # the schedule this comment set for them: they expired the moment the
    # 2026-08-10 snapshot existed, because the diff then compares 08-03 to
    # 08-10 and goes quiet without help. Science flagged that the date had
    # arrived rather than deleting them, which was right; the exemption is
    # platform's to retire.
    #
    # Second self-expiring exemption to actually retire itself this week,
    # after NAV_KNOWN_STALE emptied. Both were deleted because a check
    # said the date had come, not because anyone remembered.
    # Not part of the outage: a stale April seed the ENSO tracker removed
    # in the same commit, which had been rendering only on the failure
    # path and so went unreviewed for months.
    ("2026-08-03.json", "physical_state.heat_content_qualitative"),
    # Same class, same commit (b3679e2), one week later because this seed
    # was still present in the 08-03 snapshot and only disappears in the
    # 08-10 diff. `wwe_qualitative` was a hand-written April sentence that
    # rendered ONLY when the ERA5 fetch failed, so it sat unreviewed for
    # months and then published a paragraph about "March and early April"
    # conditions on the 2026-08-03 page. Removed deliberately; the CWWA
    # failure note is now generated from the run's own state. Entry added
    # by the ENSO tracker chat, whose removal it is, on 2026-08-10 with
    # Kristjan's go-ahead to publish; flagged to platform in the same
    # session since scripts/ is theirs.
    ("2026-08-10.json", "physical_state.wwe_qualitative"),
    # NOT a loss. CPC's strength table is a ROLLING NINE-SEASON WINDOW, so
    # when they issued the 13 August table the earliest season dropped off
    # the front and a new one appeared at the back:
    #
    #     2026-08-10   JJA 2026 ... FMA 2027    9 seasons
    #     2026-08-17            ... MAM 2027    9 seasons, JJA rotated out
    #
    # The leaf `cpc_strength.table.JJA 2026` genuinely disappears, the
    # guard collapses to the top two levels, and the whole block reads as
    # gone. Verified before suppressing: both snapshots hold 9 entries and
    # the new one is issued 2026-08-13, so the table advanced rather than
    # emptied.
    #
    # PLATFORM, THIS WILL RECUR AND AN ALLOWLIST IS THE WRONG CURE. Every
    # CPC issuance rotates the window, so roughly monthly this fires and
    # someone adds another dated line. The check that would actually hold
    # is "the block lost leaves AND gained none" or a leaf-count floor;
    # a rolling window is a legitimate shape your guard has no way to
    # express. Entry added by the ENSO tracker chat on 2026-08-17 with
    # Kristjan's go-ahead to publish, since scripts/ is yours.
    ("2026-08-17.json", "cpc_strength.table"),
    # IRI's plume is a ROLLING NINE-SEASON WINDOW, same shape as CPC's
    # strength table above. The 2026-08-19 issuance dropped JAS 2026 off
    # the front and added AMJ 2027 at the back; nine seasons before and
    # after. Verified as rotation, not loss.
    #
    # PLATFORM: this is the SECOND rolling-window false positive in two
    # weeks and the second dated line added for one. Every CPC and IRI
    # issuance rotates a window, so this recurs roughly monthly per
    # source and the allowlist grows without anyone learning anything.
    # The check that would hold is "lost leaves AND gained none", or a
    # leaf-count floor. A rolling window is a legitimate shape the guard
    # cannot currently express, and suppressing each instance is the one
    # cure guaranteed not to fix it.
    ("2026-08-24.json", "iri.three_cat"),
    # NOT a loss: `basis` went from a string to a per-field map in
    # 15f130d, so the leaf nmme.models.<MODEL>.basis no longer exists and
    # is now basis.frac_above, basis.ensemble_mean_peak and so on.
    # ensemble_mean_peak_oni was added in the same commit. The node has
    # MORE data than last week, and the guard reads a leaf becoming a
    # subtree as a disappearance.
    #
    # That change was itself the fix for a D-051 violation: a single
    # model-level `basis` described frac_above while sitting beside a
    # monthly ensemble_mean_peak, and product read it and told three
    # chats the comparability question was settled. Entry added by the
    # ENSO tracker chat, whose change it is, on 2026-08-24 with
    # Kristjan's go-ahead to publish; scripts/ is platform's.
    ("2026-08-24.json", "nmme.models"),
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


def _cron_times(workflow=None):
    """HH:MM slots declared by cron lines, across every workflow by default.

    IT READ ONE FILE AND CALLED THAT "THE SCHEDULE". The check below asks
    whether prose states a run time the workflows do not have, and its
    slot list came from fires.yml alone. So every accurate reference to
    any OTHER workflow's schedule was a violation: it fired on
    "13:00 UTC" for the weekly brief, which is declared in
    weekly_brief.yml as "0 13 * * 1" and is entirely correct.

    Six workflows have crons now. The guard was written when one did, and
    it aged into a check whose failures were mostly its own.
    """
    if workflow:
        paths = [ROOT / ".github" / "workflows" / workflow]
    else:
        paths = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                     for p in paths if p.exists())
    if not text:
        return set()
    out = set()
    for m in re.finditer(r'cron:\s*["\'](\S+)\s+(\S+)\s', text):
        minute, hour = m.group(1), m.group(2)
        if minute.isdigit() and hour.isdigit():
            out.add(f"{int(hour):02d}:{int(minute):02d}")
    return out


def check_schedule_claims(violations):
    """Does any file state a run time the workflow does not have?"""
    valid = _cron_times()          # every workflow, not one
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
    # Fire chat, 2026-08-06. Emitted AHEAD of its consumer, deliberately
    # and with design's agreement, so they do not re-derive the gate in
    # the renderer. Two copies of a threshold drift.
    #
    # Design found the fires index orders by the multiple while the
    # multiple disagrees with both z and rank-on-record: mean shift 3.6
    # places, where rank and z agree to 1.3. Portugal renders fifth at
    # 2.3x with z = 0.81, inside one standard deviation of its own
    # normal, seven rows above Saudi Arabia at 1.5x with z = 4.3.
    #
    # The fix is to split the list where the multiple is the ONLY signal
    # supporting a country, which is a property of the gate rather than a
    # threshold design would maintain separately. qualifies_on carries
    # that. Design renders the split; this is the field it renders from.
    #
    # REMOVE THIS ENTRY once build_page reads it. If it is still here in
    # a fortnight, the split did not happen and the page is still ordered
    # by its own weakest measure.
    "qualifies_on": "emitted for design's list split; renderer lands separately",
    # Same expiry as qualifies_on, and the same fortnight. Design asked
    # for BOTH shapes rather than either: the list alone forces them to
    # write `qualifies_on == ["multiple"]` in the renderer, which puts
    # this channel's gate rule in their code, where it agrees today and
    # drifts silently the first time the gate moves. The verdict alone is
    # safe and says nothing, and the page has to state WHY those four sit
    # below the line rather than assert it. Shape copied from heat's
    # drift_weight: verdict to branch on, components to print.
    "strength": "verdict plus components for design's split; renderer lands separately",
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


# Pages whose nav is known to lag, with the reason each one is allowed to.
# THIS LIST MAY ONLY SHRINK. A page not on it that disagrees with CHANNELS
# is a violation, so a NEW page or a NEW channel fails immediately; the
# entries here are the backlog that existed when the check was written.
#
# Self-tightening on purpose, the same shape as the pending_until exemption
# in check_freshness: an entry that starts passing is reported so it can be
# deleted. An allowlist nobody prunes stops being an allowlist and becomes
# a blind spot with a comment on it.
# THE ESCAPE HATCH GETS AN EXPIRY, because 30 of them accumulated
# silently and product is right about why. A guard that reports a defect
# and then exits clean is not coverage, it is decoration that looks like
# coverage: the list scrolls past, the exit code says clean, and every
# publish since these pages were orphaned has been green while the nav
# drifted through two channel launches.
#
# An advisory nobody has ever acted on is a suppressed failure. So these
# entries stop being forgiven on a date, and after it they FAIL. The date
# is the same for both blocks below because, as their own comments say,
# they are one question: what a dropped country page should say.
NAV_STALE_EXPIRY = date(2026, 8, 24)

NAV_KNOWN_STALE = {
    # EMPTY, and it got here the way it was designed to. Both original
    # entries were reported as prunable by the check itself within hours:
    # docs/index.html when Kristjan asked for the front page link the same
    # day, docs/elnino/index.html when design regenerated it. Neither was
    # remembered by a person. The dict stays because the next channel
    # launch will need it.
}
# The fire countries that dropped out of the qualifying set. They are kept
# published so live URLs do not 404 and nothing regenerates them, so their
# nav is frozen at whatever shipped the week they dropped. Several predate
# the crops launch and are missing that entry too, which is the same defect
# one channel earlier and the clearest evidence this recurs by default.
#
# NOT a permanent exemption. It ends when fire and design decide what a
# dropped country page should say, which is already an open question in
# publish_all's orphan notice. Whoever answers it deletes these lines.
# BOTH BLOCKS DELETED 2026-08-10, and by the mechanism rather than by
# anyone remembering. Product argued the advisory was a suppressed
# failure, I gave the exemption an expiry, design fixed the nav at the
# template within the hour, and the check then reported all thirty
# entries as prunable in one run. Zero pages now disagree with CHANNELS.
#
# Third self-expiring exemption to retire itself today, after
# NAV_KNOWN_STALE's original two and the four cwwa_* snapshot entries.
# The dict above stays empty on purpose: the next channel launch will
# need it, and it now carries a date by construction.

def check_gate_currency(violations, base):
    """Is this gate itself out of date relative to what it will merge into?

    A NEW FAILURE MODE, found 2026-08-09 and worse than the defect that
    exposed it. Design reported qa_check clean as evidence their branch
    was safe. It was clean. It was clean because the branch predated both
    checks that would have caught the defect, so the gate ran without
    them and said so in exactly the words a current gate uses.

    A green result from a stale gate is indistinguishable from a green
    result from a current one, and nothing in the output says which you
    have. That is the whole problem: every other failure here announces
    itself somehow.

    SCOPED TO THIS FILE ON PURPOSE. "Your branch is behind" is true of
    most branches most of the time and blocking on it would be noise
    nobody reads. The narrow question is whether the CHECKS have moved,
    because that is when a pass means something different from what the
    reader thinks. Design's phrasing, which is the right one: a gate that
    refuses to pass when its branch is behind the branch it will merge
    into.

    Silent when the base ref is unavailable. A shallow CI checkout or a
    fresh clone has no origin/main, and a check that fails on absence of
    information rather than on evidence is how a guard gets switched off.
    """
    code, _ = git("rev-parse", "--verify", "--quiet", base)
    if code != 0:
        return
    code, behind = git("rev-list", "--count", f"HEAD..{base}")
    if code != 0 or not behind.strip().isdigit() or int(behind) == 0:
        return
    me = "scripts/qa_check.py"
    code, changed = git("log", "--format=%h %s", f"HEAD..{base}", "--", me)
    if code != 0 or not changed.strip():
        return
    lines = [l for l in changed.strip().splitlines() if l.strip()]
    violations.append(
        f"this gate is {behind.strip()} commit(s) behind {base}, and "
        f"{len(lines)} of them changed {me} itself. A pass here does not "
        f"mean what a pass on {base} means, and nothing in the output "
        f"would tell you. Rebase before trusting the result:\n"
        + "\n".join(f"      {l}" for l in lines[:5]))


def check_heat_pages_match_reference(violations):
    """Do the live heat pages match the payload product actually approved?

    THE PUBLISH PATH IS `git push`, NOT publish_all. GitHub Pages serves
    docs/ straight from the repo, so any commit carrying built HTML
    publishes it. I closed the publish_all route this morning and wrote
    that the gate "can no longer be routed around". It could: design built
    36 city pages locally, committed them, I merged and pushed, and ten
    cities plus two record-count jumps went live while the gate sat
    reporting HOLD about them.

    A gate on a path that does not publish is not a gate.

    So this checks the artifact rather than the route: every city page
    under docs/ must correspond to a city in the APPROVED payload, and
    every approved city must have a page. Whatever tool built them, and
    whoever pushed, the pages and the approved reference have to agree.

    Why it matters more than a stale file, in design's words: the gate
    would keep reporting HOLD on ten cities forever, so the signal stops
    meaning anything, and when product finally approves believing they
    are clearing ten cities they are actually clearing everything that
    changed since the reference was written. An approval that does not
    mean what the approver thinks it means is worse than no gate.
    """
    ref = ROOT / "heat/data/published/city_nights.json"
    pages_dir = ROOT / "docs" / "heat"
    if not ref.exists() or not pages_dir.exists():
        return
    try:
        approved = set(json.loads(ref.read_text())["cities"])
    except (OSError, ValueError, KeyError):
        violations.append(
            "heat/data/published/city_nights.json is unreadable, so there is "
            "nothing to check the live heat pages against. That file is the "
            "record of what readers were last approved to see.")
        return

    def slug(name):
        return name.lower().replace(" ", "-")

    # Not every page in docs/heat is a city. The channel index was already
    # excluded by name; the methodology page arrived and was reported as a
    # city not in the approved payload, which is a true statement about a
    # file and a false one about the channel.
    #
    # Named rather than pattern-matched, so a real stray page still fails.
    NOT_CITIES = {"index", "methodology"}
    on_disk = {p.stem for p in pages_dir.glob("*.html")
               if p.stem not in NOT_CITIES}
    approved_slugs = {slug(c) for c in approved}

    extra = sorted(on_disk - approved_slugs)
    missing = sorted(approved_slugs - on_disk)
    if extra:
        violations.append(
            f"docs/heat has {len(extra)} page(s) for cities not in the "
            f"approved payload: {', '.join(extra)}. These are live to readers "
            f"and the refresh gate has never cleared them, so it will keep "
            f"reporting HOLD about changes that already shipped. Either the "
            f"pages should not be published yet, or the reference should be "
            f"promoted and product told what went out unreviewed.")
    if missing:
        violations.append(
            f"the approved payload has {len(missing)} city(ies) with no page: "
            f"{', '.join(missing)}. A reader following the index finds a 404.")


def check_conflict_markers(violations):
    """Is a git conflict marker committed anywhere in the tree?

    On 2026-08-10 `fires/data/country_history.json` was committed with
    `<<<<<<< Updated upstream` in it. That is the AUTOSTASH marker
    format, and autostash is something I added to scripts/push_retry.sh
    the day before: a stash pop that conflicts leaves markers in the
    working tree, the rebase itself having succeeded, so nothing in the
    script's error path fires and the next `git add` commits them.

    The file is the baseline every detections run reads. It stopped
    being valid JSON, and the only thing that noticed was a freshness
    layer reporting it "unreadable" hours later, in a run I made for an
    unrelated reason.

    Cheap, total, and it can never be forgotten: a marker at line start
    is not a thing any of our generators emit. Checked across tracked
    and untracked-but-not-ignored files, since an uncommitted marker is
    a commit away from being a committed one.
    """
    pat = re.compile(r"^(<<<<<<< |=======$|>>>>>>> )")
    for rel in repo_files():
        path = ROOT / rel
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        # This file documents the markers it looks for.
        if rel == "scripts/qa_check.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = [i + 1 for i, line in enumerate(text.splitlines())
                if pat.match(line)]
        if hits:
            violations.append(
                f"git conflict marker in {rel}, line(s) "
                f"{', '.join(map(str, hits[:6]))}. A merge or an autostash "
                f"pop left this behind and it was committed. If the file is "
                f"data, it has almost certainly stopped parsing.")


def check_social_card(violations, advisories):
    """Does a page promising a large share card actually supply one?

    Socials' finding, 2026-08-10, measured on the live site. 37 pages
    declare `summary_large_image` and carry no `og:image`, so every
    platform reserves a large card and renders it EMPTY. The brief
    archive and the front page are correct; the three channels added
    since are not.

    The pattern is worth more than the count and Socials named it: the
    surfaces that predate the channel build-out carry the tag, the ones
    added since do not. That is a missing shared head partial rather
    than four independent oversights, which means the next channel
    ships with the same gap unless the fix is structural.

    SAME CLASS AS THE ANALYTICS-TAG AND MASTHEAD CHECKS already here: a
    structural property, cheaply checkable, and invisible to every human
    review because it only appears in somebody else's feed. Nobody
    opening the page can see it.

    NOT a violation yet, and dated rather than open-ended, for the same
    reason as the nav exemption and on the same day so there is ONE
    deadline: failing today would block heat from rebuilding on a defect
    design fixes in a template, while fresh data waited. A page carrying
    no card at all is not flagged; that is a design decision about
    whether a surface is shareable, and a guard should not invent it.
    """
    offenders = []
    for p in sorted((ROOT / "docs").rglob("*.html")):
        rel = str(p.relative_to(ROOT))
        html = p.read_text(encoding="utf-8", errors="replace")
        if "summary_large_image" not in html:
            continue
        if re.search(r"""property=["']og:image["']""", html):
            continue
        offenders.append(rel)
    if not offenders:
        return
    msg = (f"{len(offenders)} page(s) declare summary_large_image and supply "
           f"no og:image, so a shared link renders an empty card. "
           f"Exemption expires {NAV_STALE_EXPIRY}, after which these FAIL. "
           f"The brief archive and front page do it correctly, so the fix is "
           f"a shared head partial rather than {len(offenders)} edits.")
    if date.today() > NAV_STALE_EXPIRY:
        violations.append(msg)
    else:
        advisories.append(msg)


def check_masthead_present(violations):
    """Does every published shell and channel page still HAVE a masthead?

    THE GATE THAT CAN STOP THE PIPELINE WAS NOT AVAILABLE TO THE PERSON
    MOST LIKELY TO TRIP IT. publish_all asserted this and qa_check did
    not, so design ran qa_check and publish_shell --check on every push,
    passed both, and still broke the site-wide publish. Design found the
    asymmetry in themselves and volunteered it; fire passed it on.

    check_masthead_wellformed next door only inspects a masthead that is
    already there, and skips a page without one, which is precisely the
    case that failed. Presence and well-formedness are different
    questions and only one of them was asked here.

    The page set comes from publish_all rather than being restated, so
    the two cannot drift into disagreeing about what must carry it. That
    is the same defect one level up: two lists, one fact.

    STILL THE LITERAL class="prodnav", deliberately. Design's new front
    page used class="nav" carrying the same links, so no reader could
    have seen a difference and this fired anyway. They fixed it by
    adopting site_masthead() rather than asking for a second accepted
    string, which is the right call: a bespoke nav on the one page that
    defines the design system is exactly what drifts. Teaching the guard
    more spellings would license that.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from publish_all import TARGETS
    except Exception as exc:
        violations.append(
            f"qa_check: cannot read TARGETS from publish_all ({exc}), so the "
            f"masthead-presence check has no page list and is not running. "
            f"A check with no subject is not a check.")
        return

    # HTML only. TARGETS is "everything a publish may touch", which is the
    # right set for the roll-back it was written for and a superset of the
    # right set here: it now also carries sitemap.xml and robots.txt, and
    # asking an XML file for a nav bar is a category error, not a defect.
    # Reusing another list's subject is cheaper than keeping a second list
    # until the moment the two questions stop being the same question.
    pages = [ROOT / rel for rel in TARGETS if rel.endswith(".html")]
    pages += sorted((ROOT / "docs" / "fires").glob("*/index.html"))
    for p in pages:
        if not p.exists():
            continue
        rel = str(p.relative_to(ROOT))
        if 'class="prodnav"' not in p.read_text(errors="ignore"):
            violations.append(
                f"{rel} has no shared masthead: no link home, a dead end. "
                f"publish_all rejects the whole publish on this, and a "
                f"rejection discards every channel's completed work for that "
                f"run, so it is worth catching here first.")


def check_masthead_wellformed(violations):
    """One masthead per page, and a channel page marks its own section.

    Both from design's sweep of 2026-08-09, which produced 77 pages with a
    literal `<header class="field"><header class="field">` and a stray
    closing tag, and stripped the `on` marker from 76 channel pages so
    every country page lost the highlight saying which channel the reader
    was in. qa_check and publish_all --check both passed it.

    UNLIKE the nav check next door, this is not a cross-page property. A
    doubled tag and a missing state class are visible inside one file, so
    this is a plain gap rather than a blind spot, and worth saying so:
    not every miss this week was the interesting kind.

    Deliberately counts rather than parses. A regex HTML parser is a bad
    idea in general, but "how many times does this exact string appear"
    is counting, and the defect is duplication.
    """
    CHANNEL_DIRS = {"fires", "crops", "heat", "elnino"}
    for p in sorted((ROOT / "docs").rglob("*.html")):
        rel = str(p.relative_to(ROOT))
        if rel.startswith("docs/briefs/20"):
            continue
        html = p.read_text(encoding="utf-8", errors="replace")
        nav = re.search(r'<nav class="prodnav".*?</nav>', html, re.S)
        if not nav:
            continue
        opens = len(re.findall(r'<header class="field"', html))
        closes = len(re.findall(r"</header>", html))
        if opens != 1 or closes != opens:
            violations.append(
                f"{rel}: {opens} opening <header class=\"field\"> and "
                f"{closes} </header>. Exactly one of each. A sweep that "
                f"wraps the masthead instead of replacing it produces this, "
                f"and the page still renders, so nothing else notices.")
        parts = rel.split("/")
        if len(parts) > 2 and parts[1] in CHANNEL_DIRS and ' on"' not in nav.group(0):
            violations.append(
                f"{rel} is a {parts[1]} page and its nav marks no current "
                f"section. The 'on' class is what tells a reader which "
                f"channel they are in; without it the masthead is correct "
                f"and says nothing about where they are.")


def check_nav_consistency(violations, advisories):
    """Does every page's nav agree with the channel list?

    THE GENERAL FORM, and the reason this check exists rather than a
    link check. Six defects this week were the same failure: a claim that
    is false only in relation to something OUTSIDE the thing being
    checked. Heat's framing, 2026-08-09, after finding the fifth. The fix
    is not more checks, it is checks whose reference lies outside their
    subject.

    Here the subject is a page and the reference is CHANNELS in
    run_brief.py. Every one of the 76 pages that lacked a heat entry on
    the day heat launched was internally valid: real markup, resolving
    links, correct against itself. qa_check, publish_all --check and the
    link checker all passed them. The wrong property was one no single
    page could see, which is why no per-page check could ever have found
    it.

    Read from source rather than imported, because importing run_brief
    for a constant runs a module that renders briefs.
    """
    src = (ROOT / "run_brief.py").read_text()
    m = re.search(r"^CHANNELS\s*=\s*(\[.*?\n\])", src, re.S | re.M)
    if not m:
        violations.append("qa_check: cannot find CHANNELS in run_brief.py, so "
                          "nav consistency cannot be checked against anything. "
                          "A check with no reference is not a check.")
        return
    expected = set()
    for slug, _label, href in ast.literal_eval(m.group(1)):
        expected.add((href or f"{slug}/").rstrip("/").split("/")[-1])

    passing_stale = []
    known = []
    for p in sorted((ROOT / "docs").rglob("*.html")):
        rel = str(p.relative_to(ROOT))
        # Archived issues are immutable (invariant 5) and legitimately
        # carry the nav of the week they were published.
        if rel.startswith("docs/briefs/20"):
            continue
        nav = re.search(r'<nav class="prodnav".*?</nav>',
                        p.read_text(encoding="utf-8", errors="replace"), re.S)
        if not nav:
            continue
        got = {h.rstrip("/").split("/")[-1]
               for h in re.findall(r'href="([^"]+)"', nav.group(0))
               if not h.endswith(".html")}
        if got == expected:
            if rel in NAV_KNOWN_STALE:
                passing_stale.append(rel)
            continue
        missing = ", ".join(sorted(expected - got)) or "none"
        extra = ", ".join(sorted(got - expected))
        msg = (f"{rel}: nav lists [{', '.join(sorted(got))}] and CHANNELS is "
               f"[{', '.join(sorted(expected))}]. Missing: {missing}."
               + (f" Unknown: {extra}." if extra else ""))
        if rel in NAV_KNOWN_STALE:
            if date.today() > NAV_STALE_EXPIRY:
                violations.append(
                    f"{msg} Its exemption expired {NAV_STALE_EXPIRY}: "
                    f"{NAV_KNOWN_STALE[rel]}. The reason was recorded with a "
                    f"date so it could not be forgiven forever.")
            else:
                known.append(rel)
        else:
            violations.append(
                msg + " Every link on this page resolves, which is why "
                "nothing else catches it. Rebuild the page, or add it to "
                "NAV_KNOWN_STALE with a reason if it genuinely cannot be.")

    if known:
        # ONE LINE, NOT THIRTY. The per-page list is what let this scroll
        # past unread for two channel launches. A count is readable; a
        # wall is not.
        miss = {}
        for rel in known:
            miss[rel.split("/")[1]] = miss.get(rel.split("/")[1], 0) + 1
        advisories.append(
            f"{len(known)} page(s) carry a known-stale nav ("
            + ", ".join(f"{v} under docs/{k}" for k, v in sorted(miss.items()))
            + f"). Exemption expires {NAV_STALE_EXPIRY}, after which these "
            f"FAIL. They are the dropped-country pages nothing regenerates; "
            f"the fix is what a dropped page should say, not more entries.")

    for rel in passing_stale:
        advisories.append(
            f"{rel} is in NAV_KNOWN_STALE and its nav now agrees with "
            f"CHANNELS. Delete the entry; a stale exemption is how a guard "
            f"quietly stops guarding.")


def check_orphan_pages(violations, advisories):
    """Is every page we want INDEXED reachable by a link from some page?

    Business measured 38 unlinked pages on 2026-08-17 and proposed a check
    with a hand-maintained allowlist for the ones unlisted on purpose,
    warning it would cry wolf otherwise. The warning was right and the
    allowlist is not needed: 37 of the 38 already declared `noindex` in
    their own markup, so the intent is recorded ON the page and this check
    can simply read it.

    That matters beyond saving a list. An allowlist is the recurring defect
    in this repo, a claim whose reference lives outside the thing being
    checked: it would have needed all 53 fires entries, and it would have
    been wrong the moment fires went listed, silently, with nobody
    remembering it existed. Reading the page's own tag cannot drift from
    the page.

    So the question is narrow on purpose. A noindex page with no inbound
    link is CONSISTENT and says nothing. A page asking to be indexed that
    nothing links to is the defect, because a crawler reaches it only via
    the sitemap and a reader cannot reach it at all.

    Advisory during a publish, like the nav check: an under-linked page is
    incomplete, not malformed, and must not hold a channel's publish.
    """
    docs = ROOT / "docs"
    pages = sorted(docs.rglob("*.html"))
    if not pages:
        violations.append(
            "orphan check walked docs/ and found no pages at all. A link "
            "check that examines nothing passes silently, which is worse "
            "than no check.")
        return

    linked = set()
    for p in pages:
        rel = str(p.parent.relative_to(docs)).replace("\\", "/")
        here = "/" if rel == "." else f"/{rel}/"
        html = p.read_text(encoding="utf-8", errors="ignore")
        for href in re.findall(r'href="([^"#?]+)', html):
            if href.startswith(("http://", "https://", "mailto:")):
                if "thelongswell.com" not in href:
                    continue
                href = re.sub(r"^https?://[^/]+", "", href) or "/"
            if not href.startswith("/"):
                href = posixpath.normpath(posixpath.join(here, href))
            linked.add(href)
            linked.add(href.rstrip("/") or "/")

    orphans = []
    for p in pages:
        html = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]*>', html, re.I)
        if m and "noindex" in m.group(0).lower():
            continue
        rel = str(p.relative_to(docs)).replace("\\", "/")
        if rel.endswith("index.html"):
            canon = "/" + rel[:-len("index.html")]
        else:
            canon = "/" + rel
        if canon in linked or canon.rstrip("/") in linked:
            continue
        if canon + "index.html" in linked:
            continue
        # The site root is the entry point by definition; nothing needs to
        # link to it. It never surfaced on the live site because the
        # masthead logo happens to link home, which is an accidental pass
        # rather than a correct one, and those are the ones that bite.
        if canon == "/":
            continue
        orphans.append(canon)

    if orphans:
        advisories.append(
            f"{len(orphans)} indexable page(s) have no inbound link from any "
            f"published page, so a reader cannot reach them: "
            f"{', '.join(sorted(orphans)[:6])}"
            f"{' ...' if len(orphans) > 6 else ''}. Either link them or, if "
            f"they are unlisted on purpose, say so on the page with "
            f'<meta name="robots" content="noindex"> and this check will '
            f"respect it.")


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
            # -co --exclude-standard, NOT bare ls-files. Heat found this
            # hole in scripts/check_emdash.sh and asked whether it was
            # here too. It was, and in the worst place: bare `ls-files`
            # lists TRACKED files only, so a brand-new file is invisible
            # to this guard until someone stages it.
            #
            # The 20.7 MB grid that caused this check to exist was a
            # brand-new file. So the guard written to catch that case
            # could not see that case. Verified before fixing: a 20 MB
            # incompressible file scores 0 violations untracked and 1
            # once staged.
            #
            # Same reach failure Heat hit twice in their own guard, and
            # the same shape as everything else this week: the pattern
            # was right and it was pointed at the wrong set.
            ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT,
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


def check_allhands_cadence(advisories):
    """Has a standing entry that claims a weekly rewrite gone stale?

    Aftereffects raised this as a CLASS rather than an incident, and they
    are right that it is the escalation map's finding at a new site: any
    recurring push that depends on a chat being awake has no liveness
    signal. No reader of the board can tell "a quiet fortnight" from "the
    desk did not run", because both look like an entry that has not
    changed. That is worse than a job which fails loudly.

    THE CHECK READS THE ENTRY'S OWN DATE, not whether a new entry
    appeared, and that distinction is theirs. The look-ahead is ONE
    standing entry rewritten in place each Monday, because a weekly
    append would evict a standing entry every week under D-059's
    ten-entry window and leave the board nothing but look-aheads inside
    two months. So no new entry ever appears, and a check watching for
    one would never fire.

    8 days, not 7. A Monday rewrite that slips to Tuesday is late, not
    broken, and a guard that cries on the first hour of lateness gets
    ignored by the second week. Same reasoning as the 30-hour run-age
    bound: allow the known slack, catch the miss.

    Advisory. A stale look-ahead misleads a planner; it does not put a
    wrong number in front of a reader, and this must never block a
    publish.
    """
    board = ROOT / "research" / "allhands.md"
    if not board.exists():
        return          # worktrees have no research/; that is its own check
    pat = re.compile(r"^## (\d{4}-\d{2}-\d{2}) · (.*REWRITTEN WEEKLY.*)$",
                     re.M | re.I)
    for m in pat.finditer(board.read_text(encoding="utf-8", errors="replace")):
        try:
            when = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        age = (date.today() - when).days
        if age > 8:
            advisories.append(
                f"research/allhands.md: \"{m.group(2)[:52]}\" declares a "
                f"weekly rewrite and its date is {age} days old. Either the "
                f"desk that owns it has not run, or it ran and did not update "
                f"the date. A reader cannot tell those from a quiet week, "
                f"which is the point of checking it here.")


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
    check_allhands_cadence(advisories)
    # Advisory during a publish, blocking in CI, same split and same reason
    # as check_emitted_fields: a nav that lags is a completeness defect and
    # a stale page is worse than an under-linked one, so this must never
    # hold the daily fire publish hostage.
    check_nav_consistency(advisories if args.for_publish else violations,
                          advisories)
    # Blocking even during a publish, unlike the nav check. An under-linked
    # page is incomplete; a page with two mastheads is malformed, and
    # publishing malformed markup is worse than publishing nothing.
    check_masthead_wellformed(violations)
    check_masthead_present(violations)
    check_social_card(violations, advisories)
    check_conflict_markers(violations)
    check_heat_pages_match_reference(violations)
    check_gate_currency(violations, args.base)
    check_orphan_pages(violations, advisories)
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
