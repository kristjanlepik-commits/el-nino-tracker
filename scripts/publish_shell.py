"""Publish the unfrozen public surfaces from already-stored state.

Platform's surface: written by the design chat as a proposal, theirs to
accept, change or reject. It deliberately does not touch run_brief.main().

## Why this exists, and why it is safe

The weekly run will not republish docs/index.html, because main() exits
early once the current issue's archive exists. That guard protects
frozen archives, but it also freezes the front page, which is not an
archive and carries no issue numbers of its own beyond one headline.

The obvious workaround, a full re-run, is NOT safe: `freshness` is
popped before the snapshot is written and meta.json stores only date,
methodology_version and headline_buckets, so a rebuild would need a live
fetch, and a refetch moves the buckets by roughly a point. The front
page would then disagree with the frozen archive copy of the same issue,
one click apart, same methodology version.

This script avoids that by rebuilding ONLY from what is already stored,
and by regenerating only pages that are not frozen:

    docs/index.html          the front page
    docs/about.html          static, no issue data
    docs/methodology.html    rendered from methodology.md
    docs/briefs/index.html   rolling index, rewritten every run anyway

It never writes docs/briefs/<date>/ or snapshots/. Verify with:

    git diff --stat -- docs/briefs/2026-* snapshots     # must be empty

The front page needs no fetch because it is no longer an issue page: it
carries the lead, the map, the event list and one headline probability,
and that probability is read straight out of the published meta.json, so
it is identical to the archive by construction rather than by luck.

Usage:  .venv/bin/python scripts/publish_shell.py [--check]
        --check writes to .publish-check/ instead of docs/.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Belt and braces: this script must never target a dated archive or a
# snapshot, whatever a future edit to the page list does.
FROZEN_RE = re.compile(r"(^|/)briefs/\d{4}-\d{2}-\d{2}/|^snapshots/")

import sources as S           # noqa: E402
import run_brief as R         # noqa: E402


def latest_issue() -> str:
    metas = sorted(glob.glob(str(ROOT / "docs" / "briefs" / "*" / "meta.json")))
    if not metas:
        raise SystemExit("no published issue found")
    return Path(metas[-1]).parent.name


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="write to .publish-check/ instead of docs/")
    args = ap.parse_args()

    di = latest_issue()
    snap = json.loads((ROOT / "snapshots" / f"{di}.json").read_text())
    meta = json.loads((ROOT / "docs" / "briefs" / di / "meta.json").read_text())
    S.BRIEF_DATE = date.fromisoformat(di)

    fetched = dict(snap)
    fetched["ecmwf_seas5"] = snap.get("ecmwf", {})
    fetched["roni_to_oni_offset"] = snap.get("roni_to_oni_offset_block", {})
    for key in ("oni_history", "nmme"):
        fetched.setdefault(key, {})

    out = (ROOT / ".publish-check") if args.check else (ROOT / "docs")

    base = R.PAGES_BASE_URL
    # Build every page in memory FIRST. The checks below are worthless if
    # the file is already on disk when they run: an abort would leave a
    # bad front page live, which is exactly the failure this guards.
    # freshness is {} on purpose: the front page no longer displays it,
    # and passing a fabricated one would be inventing state.
    pages = {}
    pages["index.html"] = R.build_public_html(
        fetched, {}, meta["headline_buckets"],
        methodology_href="methodology.html", brief_date_iso=di,
        canonical_url=f"{base}/", og_image_url=f"{base}/card.png",
        world_map_href="world-map.svg", root_prefix="", is_front=True)
    pages["about.html"] = R.build_about_html()
    meth = ROOT / "methodology.md"
    if meth.exists():
        pages["methodology.html"] = R.render_html(
            meth.read_text(),
            title=f"Methodology, {R.PRODUCT_NAME} · {R.SITE_NAME}",
            root_prefix="", analytics=True)
    # build_archive_html, not the markdown table. The archive is now a
    # real page with the trend across issues, and main() builds it the
    # same way; calling render_html here would publish a different
    # archive depending on which path ran.
    pages["briefs/index.html"] = R.build_archive_html()

    # The El Nino channel home: the current issue, rendered live, at a
    # URL that does not move week to week. The nav used to point at the
    # newest dated archive, which made an immutable record the channel's
    # front door and meant the landing page could not be restyled
    # without editing a frozen archive. This page is not an archive, so
    # it carries the current template, and it links to the frozen copy
    # that remains the citable record. Built from the same stored state
    # as the front page, so it needs no fetch and cannot drift from the
    # published numbers.
    pages["elnino/index.html"] = R.build_public_html(
        fetched, {}, meta["headline_buckets"],
        methodology_href="../methodology.html", brief_date_iso=di,
        canonical_url=f"{base}/elnino/",
        og_image_url=f"{base}/card.png",
        world_map_href="../world-map.svg", briefs_href="../briefs/",
        root_prefix="../", is_front=False,
        as_published_href=f"../briefs/{di}/",
        # analog.png and card.png sit beside the page on the front page
        # and inside each dated dir. This page is a directory deeper, so
        # it points at the rolling copies at the docs root, which track
        # the current issue exactly as this page does.
        asset_prefix="../")

    # /subscribe and /subscribed. Written but wired to nothing until now:
    # templates/subscribe.py had no caller anywhere, so neither page was
    # ever published and every link pointing at them would have 404ed.
    #
    # They belong in the SHELL rather than in a channel, for the reason
    # D-028 gives about the pages above: a channel failure must not be
    # able to take down the thing that collects the reader.
    #
    # The embed is platform's, landed on main as EMAIL_CAPTURE_SNIPPET
    # (08e543c). Imported rather than copied, so there is one form id in
    # the repo and changing the provider is one edit in their file.
    from templates import subscribe as SUB       # noqa: E402
    SUB.verify_dated_findings(R._load_events())
    pages["subscribe/index.html"] = SUB.render_subscribe(
        form_embed=R.EMAIL_CAPTURE_SNIPPET, root_prefix="../")
    pages["subscribed/index.html"] = SUB.render_subscribed(
        latest_href=f"briefs/{di}/", latest_label=f"the issue of {di}",
        root_prefix="../")

    front = pages["index.html"]
    published = meta["headline_buckets"].get("9715_>2.5", {}).get("mid")
    shown = re.search(r'ws-num num">(\d+)', front)
    shown = int(shown.group(1)) if shown else None
    tags = front.count("plausible.io/js")

    print(f"issue {di}")
    print(f"  headline on front page: {shown}%")
    print(f"  frozen archive value:   {published}%")
    print(f"  analytics tags on front page: {tags}")

    # Preconditions, all checked before a single byte is written.
    if shown is None:
        raise SystemExit("ABORT: no headline found on the front page; "
                         "the template changed and this check is stale")
    if shown != published:
        raise SystemExit("ABORT: front page disagrees with the frozen archive")
    # Every page, not just the front. A refactor that swaps one page's
    # builder can silently drop or double its tag while the front page
    # still looks right; that nearly happened when the archive moved from
    # render_html(analytics=True) to build_archive_html().
    for rel, html in sorted(pages.items()):
        n = html.count("plausible.io/js")
        if n != 1:
            raise SystemExit(
                f"ABORT: {rel} has {n} analytics tags, expected exactly 1")
    if tags != 1:
        raise SystemExit(f"ABORT: expected exactly 1 analytics tag, got {tags}")
    for rel in pages:
        if FROZEN_RE.search(rel):
            raise SystemExit(f"ABORT: refusing to write a frozen surface: {rel}")
    print("  match confirmed, no drift")

    # Create each page's own parent rather than a hardcoded list of
    # them: adding docs/elnino/ to the page dict crashed the write loop
    # mid-way, which is the one place this script is not atomic.
    out.mkdir(parents=True, exist_ok=True)
    for rel, html in pages.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(html)
    print(f"  wrote {out.relative_to(ROOT)}/: {', '.join(sorted(pages))}")


if __name__ == "__main__":
    main()
