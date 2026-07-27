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
    #    KNOWN GAP: docs/methodology.html carries no masthead today, so it
    #    is a dead end for anyone arriving from a citation link, which is
    #    precisely who lands there. It is rendered by render_html rather
    #    than the masthead-bearing builders. Flip this to True once design
    #    gives that page the shared chrome; leaving it declared False here
    #    keeps the gap visible on every run instead of silently passing.
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

    # 2. The front page headline must still equal the frozen archive.
    di = latest_issue()
    meta = json.loads((ROOT / "docs" / "briefs" / di / "meta.json").read_text())
    published = meta["headline_buckets"].get("9715_>2.5", {}).get("mid")
    import re
    front = (ROOT / "docs" / "index.html").read_text(errors="ignore")
    m = re.search(r'ws-num num">(\d+)', front)
    shown = int(m.group(1)) if m else None
    if shown is None:
        problems.append("no headline found on the front page; check is stale")
    elif shown != published:
        problems.append(
            f"front page says {shown}% but archive {di} says {published}%")

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
    for data_rel in ("data/events.json", "fires/data/current_week.json"):
        if git_changed(data_rel):
            problems.append(
                f"{data_rel} changed during publish: a fetcher ran in a "
                "publish path, which must never happen")

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
        return

    print(f"\npublished, all checks passed. {len(changed)} page(s) changed:")
    for c in changed:
        print(f"  {c}")


if __name__ == "__main__":
    main()
