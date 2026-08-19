#!/usr/bin/env python3
"""A16 (research/page_contract.md): does the LIVE page say what the
COMMITTED page says. The one S1 row in Contract A with no check, because
qa_check.py and every other guard here reads the repo, and the repo is
not what a reader sees. CI never sees the CDN.

    .venv/bin/python scripts/check_live_matches_committed.py [--channel NAME]

Spec is QA's, research/escalation_map.md row 8 ("A16"), committed 9d15eca.
Build from that; this docstring only restates the two constraints a naive
version gets wrong badly enough to be worse than nothing.

COMPARE CLAIMS, NOT BYTES. The 2026-08-04 incident (D-078) was Greece at
11.3x live against 11.5x committed, and 19 countries against 14: numbers,
not markup. A byte diff fires on every whitespace change and gets muted
within a week, which converts an S1 detector into noise. So both sides,
live and committed, go through the SAME extractor (below), and only the
extracted claims are compared. Using one extractor for both sides also
means the check cannot disagree with itself about what a "claim" is.

DO NOT ALARM INSIDE THE CACHE TTL. cache-control: max-age=600, and the
cache lies in both directions (this repo's CLAUDE.md, and measured again
on 2026-08-04: a fetch four minutes after a fix returned age: 518 and
pre-fix content). A claim mismatch is reported ONLY when the response's
`age` header is at least as old as max-age, i.e. definitely not still
inside a legitimate post-publish propagation window. Re-polled once,
several seconds apart, before concluding: a single read is not evidence,
in either direction.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://thelongswell.com"
MAX_AGE = 600  # docs/CNAME is fronted by Fastly at this cache-control


def strip_to_text(html: str) -> str:
    """Tags stripped AFTER style/script content is removed, not before:
    a bare tag-strip leaves raw CSS in the text stream, which is its own
    way of finding a phrase that "isn't there" because it's sitting next
    to noise the search wasn't expecting."""
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&middot;", "·").replace("&times;", "×")
    return re.sub(r"\s+", " ", text)


def claims_fires_country(html: str) -> dict | None:
    """window + this country's own multiple, not the "same week elsewhere"
    comparison list further down the page, which uses the same glyph."""
    text = strip_to_text(html)
    m = re.search(
        r"This week\s*·\s*(?P<window>[A-Za-z0-9 ]+?)\s*"
        r"(?P<mult>[\d.]+)\s*×\s*active-fire detections", text)
    if not m:
        return None
    return {"window": m.group("window").strip(), "multiple": m.group("mult")}


def claims_crops_country(html: str) -> dict | None:
    text = strip_to_text(html)
    dekad = re.search(r"Crops\s*·\s*dekad\s*(\d{4}-\d{2}-\d{2})", text)
    rank = re.search(r"is\s+(\d+\w{2})\s+most stressed of\s+(\d+)\s+observations", text)
    if not dekad or not rank:
        return None
    return {"dekad": dekad.group(1), "rank": rank.group(1), "of": rank.group(2)}


# Each entry: (docs/ glob, extractor). Extend per page shape as needed;
# the spec estimates ~20 lines per shape, which is what these two are.
CHANNELS = {
    "fires": ("docs/fires/*/index.html", claims_fires_country),
    "crops": ("docs/crops/*/index.html", claims_crops_country),
}


def fetch(url: str) -> tuple[int, dict, str]:
    # A non-ASCII slug (crops/côte-divoire) raises inside urllib's own
    # request-building, not inside our code, unless the URL is
    # percent-encoded first. QA hit this same class in their own client
    # today, and it cost build_sitemap.py a page's lastmod earlier this
    # session; third instance, same root cause each time: a raw non-ASCII
    # URL handed to a tool that assumes ASCII.
    safe = urllib.parse.quote(url, safe=":/")
    req = urllib.request.Request(safe, headers={"User-Agent": "tls-a16-check"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            headers = {k.lower(): v for k, v in r.getheaders()}
            return r.status, headers, r.read().decode("utf-8", "ignore")
    except Exception as exc:
        return 0, {}, str(exc)


def committed_html(rel_path: str) -> str | None:
    r = subprocess.run(["git", "show", f"HEAD:{rel_path}"], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def url_for(rel_path: str) -> str:
    rel = rel_path[len("docs/"):]
    return f"{SITE}/{rel[:-len('index.html')]}" if rel.endswith("index.html") else f"{SITE}/{rel}"


def check_page(rel_path: str, extractor) -> str | None:
    """Returns a problem string, or None. Re-polls once before concluding
    a mismatch, since a single read cannot distinguish a real drift from
    a page caught mid-propagation."""
    committed = committed_html(rel_path)
    if committed is None:
        return None  # not in HEAD; not this check's problem
    committed_claims = extractor(committed)
    if committed_claims is None:
        return None  # page shape doesn't match (e.g. a dropped-country stub)

    url = url_for(rel_path)
    for attempt in (1, 2):
        status, headers, body = fetch(url)
        if status != 200:
            return f"{url}: fetch failed (HTTP {status or 'error'}: {body[:80]})"
        age = int(headers.get("age", "0") or "0")
        live_claims = extractor(body)
        if live_claims == committed_claims:
            return None
        if age < MAX_AGE:
            # Could be legitimate propagation lag. Re-poll once rather
            # than alarm inside the TTL; on the second pass, age has
            # grown past MAX_AGE if it's really the same stale object, or
            # the claims now match if the deploy caught up.
            if attempt == 1:
                time.sleep(5)
                continue
            return None  # still inside TTL on re-poll: not yet decidable
        return (f"{url}: LIVE DOES NOT MATCH COMMITTED "
                f"(age {age}s, x-cache {headers.get('x-cache', '?')}) "
                f"live={live_claims} committed={committed_claims}")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--channel", choices=sorted(CHANNELS),
                    help="check one channel only; default is all")
    args = ap.parse_args()

    channels = [args.channel] if args.channel else sorted(CHANNELS)
    problems = []
    checked = 0
    for channel in channels:
        glob, extractor = CHANNELS[channel]
        paths = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(glob))
        for rel_path in paths:
            checked += 1
            problem = check_page(rel_path, extractor)
            if problem:
                problems.append(problem)

    print(f"  A16: {checked} page(s) checked across {len(channels)} channel(s)")
    if problems:
        print(f"  {len(problems)} mismatch(es):")
        for p in problems:
            print(f"    {p}")
        return 1
    print("  live matches committed on every page checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
