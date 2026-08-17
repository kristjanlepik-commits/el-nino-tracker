#!/usr/bin/env python3
"""Generate docs/sitemap.xml and docs/robots.txt from what actually shipped.

    scripts/build_sitemap.py [--check]

Runs as the last step of publish_all.py, after every page exists, because
a sitemap written from a list of pages we INTEND to publish is a list of
promises. This one is built by walking docs/ and is therefore incapable
of disagreeing with the site.

WHY THIS EXISTS. Business measured the baseline at a median of 22 uniques
a day, with one 372 spike that decayed rather than settled. Search is the
only channel that produces a floor instead of a spike, and we had no
sitemap and no robots.txt across 184 published pages.

A NOINDEX PAGE IS NEVER LISTED, and that rule is why this needs no
hand-maintained allowlist. Google treats a sitemap that lists pages the
pages themselves forbid as a reason to trust the whole file less, so the
contradiction costs more than the entry gains. Reading each page's own
robots meta also means the exclusion list cannot go stale: a page that
stops being unlisted is picked up the next time this runs, with nobody
remembering to edit anything. An allowlist here would have needed an
entry for all 53 fires pages and would have been wrong the day fires
went listed.

LASTMOD COMES FROM GIT, NOT FROM MTIME, and this is the one thing in
here worth arguing about. mtime is the obvious choice and it is wrong in
CI: actions/checkout stamps every file with the checkout time, so an
mtime sitemap claims all 184 pages changed today, every day. Google
discounts a lastmod it finds untrustworthy, so the field would be worse
than absent. It would also flatten the archive: briefs are immutable
(invariant 5) and their real dates are exactly what a crawler should
see, not the timestamp of the runner that happened to check them out.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = "https://thelongswell.com"

ROBOTS_META = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]*>', re.I)


def commit_dates() -> dict[str, str]:
    """Newest commit date per path, in ONE git call.

    Per-file `git log -1` would be 184 subprocesses on every publish. This
    walks the log once and keeps the first date each path appears with,
    which is its most recent commit because git log is newest-first.
    """
    # core.quotePath=false or non-ASCII paths come back C-escaped, as
    # "docs/crops/t\303\274rkiye/index.html", which matches no real path
    # and silently costs those pages their lastmod. Caught on türkiye,
    # the one such page we have; it reported as "not in any commit" while
    # being perfectly well committed.
    out = subprocess.run(
        ["git", "-c", "core.quotePath=false",
         "log", "--format=%cI", "--name-only", "--no-renames"],
        cwd=ROOT, capture_output=True, text=True).stdout
    dates: dict[str, str] = {}
    stamp = ""
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}T", line):
            stamp = line[:10]
        elif line not in dates:
            dates[line] = stamp
    return dates


def is_noindex(html: str) -> bool:
    m = ROBOTS_META.search(html)
    return bool(m and "noindex" in m.group(0).lower())


def url_for(path: Path) -> str:
    """Canonical URL. index.html is the directory, everything else is itself."""
    rel = str(path.relative_to(DOCS)).replace("\\", "/")
    if rel == "index.html":
        return f"{SITE}/"
    if rel.endswith("/index.html"):
        return f"{SITE}/{rel[:-len('index.html')]}"
    return f"{SITE}/{rel}"


def collect() -> tuple[list[tuple[str, str]], list[str]]:
    """(url, lastmod) for every indexable page, plus the excluded paths."""
    dates = commit_dates()
    entries, excluded, uncommitted = [], [], []
    for p in sorted(DOCS.rglob("*.html")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        html = p.read_text(encoding="utf-8", errors="ignore")
        if is_noindex(html):
            excluded.append(str(p.relative_to(DOCS)))
            continue
        when = dates.get(rel)
        if not when:
            # Never committed. Publishing an uncommitted page is its own
            # problem and check_generators_clean is where that is caught;
            # here it just means there is no honest date, so omit the
            # field rather than invent one from the filesystem.
            uncommitted.append(rel)
        entries.append((url_for(p), when or ""))
    if uncommitted:
        print(f"  note: {len(uncommitted)} page(s) not in any commit, listed "
              f"without lastmod: {', '.join(uncommitted[:4])}"
              f"{' ...' if len(uncommitted) > 4 else ''}", file=sys.stderr)
    return entries, excluded


def sitemap_xml(entries: list[tuple[str, str]]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, when in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        if when:
            lines.append(f"    <lastmod>{when}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def robots_txt() -> str:
    # Deliberately not disallowing anything. The pages that must stay out
    # of the index say so themselves, in a meta tag a crawler must fetch
    # the page to read, and Disallow would PREVENT that fetch: a blocked
    # page can still be indexed from inbound links, with its noindex
    # never seen. The two mechanisms look interchangeable and are not.
    return (f"User-agent: *\n"
            f"Allow: /\n"
            f"\n"
            f"Sitemap: {SITE}/sitemap.xml\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report what would be written, write nothing")
    args = ap.parse_args()

    entries, excluded = collect()
    if not entries:
        # A sitemap listing nothing would deploy over a working one and
        # look like a successful run. The empty case must raise.
        raise SystemExit(
            "REFUSING: no indexable page found under docs/. That is either "
            "a broken walk or a site that told every crawler to go away; "
            "either way writing an empty sitemap over the live one is the "
            "worst available outcome.")

    xml, robots = sitemap_xml(entries), robots_txt()
    print(f"  sitemap: {len(entries)} url(s), {len(excluded)} excluded as "
          f"noindex")
    if args.check:
        print("  --check: nothing written.")
        return 0
    (DOCS / "sitemap.xml").write_text(xml, encoding="utf-8")
    (DOCS / "robots.txt").write_text(robots, encoding="utf-8")
    print(f"  wrote docs/sitemap.xml and docs/robots.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
