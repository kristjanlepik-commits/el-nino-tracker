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

All three rebuild from committed state only (snapshots, meta.json,
data/events.json, fires/data/current_week.json). None of them fetch, so
this is deterministic and safe to re-run.

THE RULE, and it is not negotiable: this script runs renderers, never
fetchers. Specifically fires/build_events.py must NEVER be added here.
It calls the FIRMS API for 45 countries, takes minutes, is the daily
06:00 UTC data job, and can fail on a network blip. Putting a fetcher in
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
]

STEPS = [
    ("shell", [PY, "scripts/publish_shell.py"]),
    ("fires index", [PY, "fires/build_page.py"]),
    ("fires country pages", [PY, "fires/build_country_pages.py"]),
]


def snapshot_targets() -> dict[str, bytes | None]:
    """Current bytes of everything a publish may touch, including the
    per-country fire pages, which are discovered rather than listed."""
    saved: dict[str, bytes | None] = {}
    for rel in TARGETS:
        p = ROOT / rel
        saved[rel] = p.read_bytes() if p.exists() else None
    for p in (ROOT / "docs" / "fires").glob("*/index.html"):
        rel = str(p.relative_to(ROOT))
        saved[rel] = p.read_bytes()
    return saved


def restore(saved: dict[str, bytes | None]) -> None:
    for rel, data in saved.items():
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


def verify() -> list[str]:
    """Every reason this publish should not be kept."""
    problems = []

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
                     "docs/pacific-sst.json", "docs/pacific-sst.png"):
        if git_changed(data_rel):
            problems.append(
                f"{data_rel} changed during publish: a fetcher ran in a "
                "publish path, which must never happen")

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
    qa = subprocess.run([PY, "scripts/qa_check.py"],
                        cwd=ROOT, capture_output=True, text=True)
    if qa.returncode != 0:
        problems.append("qa_check failed:\n" + qa.stdout.strip())

    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="build and verify, then restore; publishes nothing")
    ap.add_argument("--assert-clean", action="store_true",
                    help=("exit non-zero if any page WOULD change. For CI on "
                          "main: proves the committed pages still match the "
                          "generator that claims to produce them."))
    args = ap.parse_args()

    saved = snapshot_targets()

    env_note = ""
    for name, cmd in STEPS:
        # fires/*.py import tokens and run_brief from the repo root.
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           env={**__import__("os").environ,
                                "PYTHONPATH": str(ROOT)})
        if r.returncode != 0:
            restore(saved)
            print(f"FAILED during {name}, nothing published:\n"
                  f"{r.stdout}\n{r.stderr}".strip())
            raise SystemExit(1)
        print(f"  ran {name}")
    print(env_note, end="")

    problems = verify()
    if problems:
        restore(saved)
        print("\nPUBLISH REJECTED, everything restored:")
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
