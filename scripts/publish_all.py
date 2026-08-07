#!/usr/bin/env python3
"""Publish every unfrozen surface in one command, then verify the result.

Why this exists
---------------
The repo has more than one publish path, and a change to a generator only
reaches readers when that generator runs. On 2026-07-27 the design chat
made the house masthead shared and changed fires/build_page.py to use it;
the change merged and looked done, but scripts/publish_shell.py does not
regenerate fire pages, so the live fires page still had no nav at all.
Live-but-not-really is the failure mode this script exists to remove.

What it runs, in order:

    scripts/publish_shell.py     front page, About, methodology, archive
    fires/build_page.py          the Fires channel index
    fires/build_country_pages.py the per-country fire pages
    crops/build_page.py          the Crops channel index

All four rebuild from committed state only (snapshots, meta.json,
data/events.json, fires/data/current_week.json,
crops/data/stress_current.json). None of them fetch, so this is
deterministic and safe to re-run.

THE RULE, and it is not negotiable: this script runs renderers, never
fetchers. Specifically fires/build_events.py must NEVER be added here.
It calls the FIRMS API for 45 countries, takes minutes, is the daily
03:10 UTC data job with an 05:30 backstop, and can fail on a network
blip. The same bar applies to crops/pull_asap_indicator.py, which
downloads a 30 MB dekadal archive and must never be reachable from a
publish. Putting a fetcher in
a publish path would make every publish pull live data and quietly move
the published numbers, which is the exact opposite of what this script
is for. If a channel needs new data, run its data job; publishing is a
separate act from fetching. (Rule stated by the Fire chat, 2026-07-27.)

Order matters for fires: the country pages read current_week.json, so
the index builder runs first.

Safety
------
publish_shell.py verifies before it writes. The fires builders are the
Fire chat's code and write directly, so this script wraps the whole run
instead: it records the current bytes of every target, runs the builders,
verifies the result, and restores the originals if anything fails. Either
the whole publish is good, or nothing changed.

Checks after building, before keeping the result:
  - every generated page carries exactly one analytics tag
  - the front page headline still equals the frozen archive's meta.json
  - no dated archive under docs/briefs/ and no snapshot was modified
  - scripts/qa_check.py passes (links, structure, em-dashes, immutability)

Usage:  .venv/bin/python scripts/publish_all.py [--check]
        --check builds and verifies, then restores everything, so it
        publishes nothing. Use it to see whether a publish would be clean.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# Everything a publish is allowed to rewrite. Anything not listed here
# that changes is treated as a failure, which is how a builder quietly
# touching a frozen archive would get caught.
TARGETS = [
    "docs/index.html",
    "docs/about.html",
    "docs/methodology.html",
    "docs/elnino/index.html",
    "docs/briefs/index.html",
    "docs/fires/index.html",
    "docs/crops/index.html",
    "docs/heat/index.html",
    "docs/subscribe/index.html",
    "docs/subscribed/index.html",
]

STEPS = [
    ("shell", [PY, "scripts/publish_shell.py"]),
    ("fires index", [PY, "fires/build_page.py"]),
    ("crops index", [PY, "crops/build_page.py"]),
    ("heat channel", [PY, "design/make_heat_index.py"]),
    ("heat city pages", [PY, "design/make_city_pages.py"]),
    ("fires country pages", [PY, "fires/build_country_pages.py"]),
]

# The ENSO shell. Invariant 1 in CLAUDE.md: the weekly brief always
# ships. D-028 makes that explicit here: a channel failure must never
# take these pages down with it. The weekly brief is the credential
# (T10), and a channel that has existed for three weeks cannot be
# allowed to block it. Do not fold these back into the channel
# roll-back set in a future refactor.
SHELL_TARGETS = {
    "docs/index.html",
    "docs/about.html",
    "docs/methodology.html",
    "docs/elnino/index.html",
    "docs/briefs/index.html",
    # Same reasoning as the pages above: the capture surface must not be
    # taken down by a channel build failing.
    "docs/heat/index.html",
    "docs/subscribe/index.html",
    "docs/subscribed/index.html",
}

# Every file whose contents change what a publish produces. Publishing
# with any of these modified means publishing from source that exists in
# no commit; on 2026-07-28 that regenerated 12 fire pages from another
# chat's work in progress, caught by hand. D-027.
GENERATORS = [
    "run_brief.py",
    "tokens.py",
    "scripts/publish_shell.py",
    "fires/build_page.py",
    "fires/build_country_pages.py",
    "crops/build_page.py",
    "design/make_heat_index.py",
    "design/make_city_pages.py",
    "design/city_coords.json",
    "design/data/europe_coast.json",
]


def snapshot_targets() -> dict[str, bytes | None]:
    """Current bytes of everything a publish may touch, including the
    per-country fire pages, which are discovered rather than listed."""
    saved: dict[str, bytes | None] = {}
    for rel in TARGETS:
        p = ROOT / rel
        saved[rel] = p.read_bytes() if p.exists() else None
    for p in (ROOT / "docs" / "heat").glob("*.html"):
        saved[str(p.relative_to(ROOT))] = p.read_bytes()
    for p in (ROOT / "docs" / "fires").glob("*/index.html"):
        rel = str(p.relative_to(ROOT))
        saved[rel] = p.read_bytes()
    return saved


def restore(saved: dict[str, bytes | None], keep_shell: bool = False) -> None:
    """Put the saved bytes back.

    keep_shell leaves the ENSO shell as freshly built while rolling every
    channel back. That is D-028: a channel failure must not take the
    weekly brief down, per CLAUDE.md invariant 1.
    """
    for rel, data in saved.items():
        if keep_shell and rel in SHELL_TARGETS:
            continue
        p = ROOT / rel
        if data is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(data)


def git_changed(*paths: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", "--", *paths],
                         cwd=ROOT, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def latest_issue() -> str:
    metas = sorted((ROOT / "docs" / "briefs").glob("*/meta.json"))
    if not metas:
        raise SystemExit("no published issue found")
    return metas[-1].parent.name


def check_generators_clean() -> None:
    """Refuse to publish from source that exists in no commit.

    Three chats share this working tree. A publish runs whatever code is
    on disk, so an unrelated chat's half-finished edit becomes published
    output without anyone choosing it. The refusal names the files and
    the remedy on purpose: this will be hit on a Monday with a brief
    waiting, and a guard that only says no costs more than it saves.
    """
    dirty = git_changed(*GENERATORS)
    if not dirty:
        return
    print("REFUSING TO PUBLISH: these generators have uncommitted changes,")
    print("so the pages would be built from source that is in no commit.\n")
    for f in dirty:
        print(f"    {f}")
    print("\nFix, whichever fits:")
    print("    git status <file>              see what changed and whose it is")
    print("    git add <file> && git commit    if the work is yours and ready")
    print("    git stash push <file>           to park it and publish without it")
    print("    git checkout -- <file>          to discard it (destructive)")
    print("\nIf you know the change is safe and want it published as-is,")
    print("re-run with --allow-dirty.")
    raise SystemExit(1)


# D-092: a channel declares how old its own data may be, and a publish
# that would ship older data than that is refused.
#
# WHY THIS IS NOT check_freshness.py, which already exists. That file
# asks a CORRECTNESS question: are we behind our source? This asks a
# VALUE question: is this current enough to be worth putting in front of
# a reader? They are different, and today shows how far apart they can
# be. Crops holds dekad 2026-07-11 and ASAP's newest published dekad is
# also 2026-07-11, so by the correctness measure crops is perfectly
# current and check_freshness reports it green. It is also 26 days old,
# which is what shipped while UK newspapers covered record-dry rivers.
#
# Strategy's count is the argument: twelve mechanisms built this week and
# every one a correctness mechanism. Nothing asked whether a reader would
# care. Accurate, sourced, dated, evidence-tagged and stale is a state
# this system could not previously see.
#
# THE BOUND BELONGS TO THE CHANNEL, in its own payload, because only the
# channel knows what its data is for. A daily hotspot count and a
# dekadal agricultural indicator are different animals and a single
# number would be wrong for both. It lives in the payload rather than
# here so it cannot drift from the data it describes, which is the
# qualifier-level rule CRO named.
#
# SCOPED TO THE CHANNEL, NOT THE PUBLISH. A stale channel must not take
# the ENSO shell down with it, which is D-028 and invariant 1: the weekly
# brief always ships. The existing keep_shell path already does this, and
# a freshness failure is exactly the kind of channel-local problem it was
# built for.
FRESHNESS_DECLARATIONS = [
    {"data": "crops/data/stress_current.json", "date_key": "dekad",
     "pages": ("docs/crops/",), "owner": "CRO"},
    {"data": "fires/data/current_week.json", "date_key": None,
     "pages": ("docs/fires/",), "owner": "FIRE"},
]

# The key a channel sets in its payload to declare its own bound. Absent
# means the channel has not chosen yet, which is reported rather than
# silently defaulted: a default here would be platform guessing a number
# only the channel can know, and a guessed bound that never fires is
# worse than none.
BOUND_KEY = "max_data_age_days"


def check_declared_freshness(problems: list[str]) -> None:
    for spec in FRESHNESS_DECLARATIONS:
        path = ROOT / spec["data"]
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue

        bound = doc.get(BOUND_KEY)
        if not isinstance(bound, (int, float)):
            print(f"  NOTICE: {spec['data']} declares no {BOUND_KEY}, so its "
                  f"pages ship unchecked for age. {spec['owner']} sets this "
                  f"number; platform will not guess it (D-092).")
            continue

        key = spec["date_key"]
        raw = doc.get(key) if key else None
        if not isinstance(raw, str):
            continue
        try:
            as_of = date.fromisoformat(raw[:10])
        except ValueError:
            continue

        age = (date.today() - as_of).days
        if age > bound:
            problems.append(
                f"{spec['data']} is {age} days old against its own declared "
                f"bound of {bound} ({BOUND_KEY}). The channel set that "
                f"number, so this is not platform's judgement about what is "
                f"too old. Its pages are not published. Note this can fire "
                f"while the data is perfectly CURRENT with its source: being "
                f"level with a slow publisher is a correctness property, and "
                f"this gate asks a reader-value question instead. "
                f"Owner: {spec['owner']}.")


def verify() -> list[str]:
    """Every reason this publish should not be kept."""
    problems = []
    check_declared_freshness(problems)

    # 1. Per-page invariants (design chat's suggestion, and a good one).
    #    Structural checks that are identical on every page will happily
    #    green-light a page that silently lost a SHARED component: that is
    #    exactly how the fires page shipped with no masthead while a live
    #    link check reported zero broken links. So assert the shared
    #    components per page, not just that the page exists.
    #
    # No known gaps: every published page carries the shared masthead.
    # docs/methodology.html was the last exception, closed 2026-07-27
    # when render_html stopped emitting a reduced masthead of its own.
    # Anything added here is a dead end for readers, so it wants a
    # dated reason and an owner, not just an entry.
    expect_masthead: dict = {}

    pages = [ROOT / rel for rel in TARGETS]
    pages += sorted((ROOT / "docs" / "fires").glob("*/index.html"))
    for p in pages:
        rel = str(p.relative_to(ROOT))
        if not p.exists():
            problems.append(f"missing after publish: {rel}")
            continue
        html = p.read_text(errors="ignore")

        n = html.count("plausible.io/js")
        if n != 1:
            problems.append(f"{rel} has {n} analytics tags, expected 1")

        wants_masthead = expect_masthead.get(rel, True)
        has_masthead = 'class="prodnav"' in html
        if wants_masthead and not has_masthead:
            problems.append(
                f"{rel} lost the shared masthead: no link home, a dead end")
        if not wants_masthead and has_masthead:
            problems.append(
                f"{rel} now HAS the masthead; remove its entry from "
                "expect_masthead so the gap stays closed")

    # 2. EVERY page showing the headline must agree with the frozen
    #    archive, not just the front page. The channel home at
    #    docs/elnino/ renders the same number from the same meta.json, so
    #    checking only index.html would leave a second published figure
    #    unguarded. Pages that do not display a headline are skipped
    #    rather than failed, but the front page must always have one.
    #    Two markups carry the same figure and both must be checked. The
    #    front page uses the hero number; the channel home uses the
    #    magnitude rung of the odds ladder. Matching only the hero looked
    #    like it was checking every page while silently skipping
    #    docs/elnino/, which is the false-assurance failure this whole
    #    file exists to prevent.
    di = latest_issue()
    meta = json.loads((ROOT / "docs" / "briefs" / di / "meta.json").read_text())
    published = meta["headline_buckets"].get("9715_>2.5", {}).get("mid")
    import re
    HERO = re.compile(r'ws-num num">(\d+)')
    LADDER_MAGN = re.compile(r'rung magn.*?class="pct">(\d+)<', re.S)
    seen_headline = False
    for p in pages:
        if not p.exists():
            continue
        rel = str(p.relative_to(ROOT))
        html = p.read_text(errors="ignore")
        found = [int(m.group(1)) for m in
                 list(HERO.finditer(html)) + list(LADDER_MAGN.finditer(html))]
        if not found:
            continue
        seen_headline = True
        for shown in set(found):
            if shown != published:
                problems.append(
                    f"{rel} says {shown}% but archive {di} says {published}%")
    if not seen_headline:
        problems.append(
            "no headline found on any page; the template changed and this "
            "check is stale")

    # 3. Nothing frozen may move. That is the dated ENSO archives and
    #    snapshots, plus the Fire chat's dated spotlight pages, which are
    #    published artifacts with no regeneration path by design.
    frozen = git_changed("docs/briefs/2026-*", "snapshots",
                         "docs/fires/spotlight-*.html")
    frozen = [f for f in frozen if not f.endswith("briefs/index.html")]
    for f in frozen:
        problems.append(f"frozen surface modified: {f}")

    # 4. A fetcher must never have run as part of a publish. If a data
    #    file moved, someone wired a fetcher into this path.
    #    docs/pacific-sst.* are here for the same reason as the fires
    #    data: they are fetcher output, produced by hand via
    #    design/make_pacific_sst.py, which is deliberately outside the
    #    pipeline. If they move during a publish, someone wired that
    #    generator in.
    for data_rel in ("data/events.json", "fires/data/current_week.json",
                     "crops/data/stress_current.json",
                     "docs/pacific-sst.json", "docs/pacific-sst.png"):
        if git_changed(data_rel):
            problems.append(
                f"{data_rel} changed during publish: a fetcher ran in a "
                "publish path, which must never happen")

    # Country pages whose country has dropped out of the qualifying set.
    # They are NOT pruned: deleting a published URL is a stronger act
    # than editing one, and D-031 settled that published reports stay as
    # published. A shared or cited link must not start 404ing because a
    # country fell below a threshold this week.
    #
    # But an orphan stops being regenerated, so it silently ages in both
    # data and design while still being reachable. That is the "static
    # picture of a moving field" failure again. This is a notice rather
    # than a blocker, because the qualifying set churns daily and a
    # failure here would block publishing most days; the point is that
    # orphans cannot accumulate unseen.
    try:
        ev = json.loads((ROOT / "data" / "events.json").read_text())
        rows = ev.get("events") or ev.get("rows") or []
        live = {re.sub(r"[^a-z0-9]+", "-", (r.get("region") or r.get("name") or "").lower()).strip("-")
                for r in rows}
        dirs = {p.name for p in (ROOT / "docs" / "fires").iterdir() if p.is_dir()}
        orphans = sorted(d for d in dirs - live if d)
        if orphans:
            print(f"  NOTICE: {len(orphans)} fire country page(s) no longer in "
                  f"the qualifying set and no longer regenerated: "
                  f"{', '.join(orphans)}. Kept deliberately so published URLs "
                  "do not 404; they age in place until Fire and design decide "
                  "what a dropped country should say.")
    except (OSError, ValueError):
        pass

    # A hand-refreshed picture of a moving field is the one thing here
    # that rots silently: nothing breaks, the page just quietly shows an
    # older ocean than it claims to be about. The caption states the date,
    # so this is a notice rather than a blocker; it exists so the age is
    # in front of whoever publishes instead of only in the markup.
    sst = ROOT / "docs" / "pacific-sst.json"
    if sst.exists():
        try:
            obs = json.loads(sst.read_text()).get("observation_date")
            issue = date.fromisoformat(latest_issue())
            age = (issue - date.fromisoformat(obs)).days
            if age > 10:
                print(f"  NOTICE: the Pacific SST field was observed {obs}, "
                      f"{age} days before issue {issue}. Refresh it with "
                      "design/make_pacific_sst.py (design chat's surface).")
        except (ValueError, TypeError):
            problems.append(
                "docs/pacific-sst.json has no readable observation_date; "
                "an undated field cannot be shown honestly")

    # 5. The standing gate: links, structure, em-dashes, immutability.
    #
    # --for-publish downgrades rendering-completeness findings (D-046's
    # emitted-field check) to warnings. Those are real defects and CI
    # goes red on them, but they must never stop a publish: a page that
    # renders one field short is worse than yesterday's page only until
    # tomorrow, whereas a blocked publish freezes the channel outright.
    # We have already had a two-day freeze behind a well-formed page and
    # do not need one behind a well-intentioned guard.
    qa = subprocess.run([PY, "scripts/qa_check.py", "--for-publish"],
                        cwd=ROOT, capture_output=True, text=True)
    if qa.returncode != 0:
        problems.append("qa_check failed:\n" + qa.stdout.strip())
    elif "QA ADVISORY" in qa.stdout:
        print(qa.stdout[qa.stdout.index("QA ADVISORY"):].rstrip())

    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="build and verify, then restore; publishes nothing")
    ap.add_argument("--assert-clean", action="store_true",
                    help=("exit non-zero if any page WOULD change. For CI on "
                          "main: proves the committed pages still match the "
                          "generator that claims to produce them."))
    ap.add_argument("--allow-dirty", action="store_true",
                    help=("publish even though a generator has uncommitted "
                          "changes. You are asserting the change is yours "
                          "and ready."))
    args = ap.parse_args()

    if not args.allow_dirty:
        check_generators_clean()

    saved = snapshot_targets()

    for name, cmd in STEPS:
        # fires/*.py import tokens and run_brief from the repo root.
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           env={**__import__("os").environ,
                                "PYTHONPATH": str(ROOT)})
        if r.returncode != 0:
            # D-028. A failing CHANNEL rolls back every channel, never
            # the ENSO shell: invariant 1 says the weekly brief always
            # ships, and a channel three weeks old must not be able to
            # block the credential. A failing shell rolls back
            # everything, because a broken shell is not shippable.
            restore(saved, keep_shell=(name != "shell"))
            kept = "" if name == "shell" else \
                " The ENSO shell is kept and still publishes (invariant 1)."
            print(f"FAILED during {name}. Channels rolled back.{kept}\n"
                  f"{r.stdout}\n{r.stderr}".strip())
            raise SystemExit(1)
        print(f"  ran {name}")

    problems = verify()
    if problems:
        # Same rule for verification failures: if nothing is wrong with a
        # shell page, the shell still ships.
        shell_hit = any(t in p for p in problems for t in SHELL_TARGETS)
        restore(saved, keep_shell=not shell_hit)
        scope = "everything restored" if shell_hit else \
            "channels restored; the ENSO shell still publishes (invariant 1)"
        print(f"\nPUBLISH REJECTED, {scope}:")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)

    changed = git_changed("docs")
    if args.check:
        restore(saved)
        print(f"\ncheck passed. {len(changed)} page(s) would change; "
              f"nothing published.")
        for c in changed:
            print(f"  {c}")
        # Design chat's guard, and a good one. A page can pass every
        # structural check while having been built from a tree that no
        # longer exists: the generator was merged, the publish ran before
        # or during it, and the committed artifact silently disagrees
        # with the source that claims to produce it. That happened on
        # 2026-07-28 and was invisible until someone ran --check by hand.
        # On main, "would change" means docs is stale, so it is a failure.
        if args.assert_clean and changed:
            print("\nFAIL: docs/ is stale relative to its own generator. "
                  "These pages are committed in a state run_brief.py no "
                  "longer produces; run scripts/publish_all.py and commit.")
            raise SystemExit(1)
        return

    print(f"\npublished, all checks passed. {len(changed)} page(s) changed:")
    for c in changed:
        print(f"  {c}")


if __name__ == "__main__":
    main()
