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

DO NOT ALARM INSIDE THE CACHE TTL, AND "OUTLIVES THE TTL" MEANS WALL-CLOCK
TIME, NOT THE `age` HEADER. The first build read the spec's "alarm only
when the difference outlives the TTL" as `age >= max-age`, which is
defensible from the words alone and wrong in practice: `age` for an
object honouring `max-age=600` cycles in [0, 600) and never reaches it,
so that branch was reachable only in a fabricated test and never on a
real fetch. A genuinely stale ORIGIN, a deploy that never landed, then
produces a mismatch on every poll forever while the check reports
nothing, which is the exact failure this exists to catch, invisible. So
a candidate mismatch now waits out the TTL for real (RECHECK_WAIT
seconds) and checks once more: if the claims still differ, the
difference has actually outlived any legitimate propagation window. A
clean page costs one fetch, unchanged; the wait only happens once there
is something to wait for.
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
RECHECK_WAIT = MAX_AGE + 15  # margin over the TTL, not over a guess at it


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


def first_pass(rel_path: str, extractor) -> tuple[str | None, dict | None]:
    """One fetch. Returns (immediate_problem, candidate). At most one of
    the two is set. A fetch failure (404, 500, timeout) is immediate: it
    is not a propagation-lag question and gets no TTL wait. A claims
    mismatch becomes a candidate for recheck_candidate, not an immediate
    verdict.

    No sleep here regardless of outcome: waiting per-page is what made
    the original version unusable for the failure it exists to catch,
    because the scenario A16 is FOR is a whole channel's deploy not
    landing, which makes every page in that channel a candidate at once.
    A serial per-page wait would have turned that exact scenario into a
    multi-hour run; see main(), which waits once, shared across every
    candidate this pass produces.
    """
    committed = committed_html(rel_path)
    if committed is None:
        return None, None  # not in HEAD; not this check's problem
    committed_claims = extractor(committed)
    if committed_claims is None:
        return None, None  # page shape doesn't match (e.g. a dropped stub)

    url = url_for(rel_path)
    status, headers, body = fetch(url)
    if status != 200:
        return f"{url}: fetch failed (HTTP {status or 'error'}: {body[:80]})", None
    live_claims = extractor(body)
    if live_claims == committed_claims:
        return None, None
    return None, {"url": url, "committed": committed_claims}


def recheck_candidate(c: dict, extractor) -> str | None:
    """Called only after RECHECK_WAIT has genuinely elapsed, once, shared
    across every candidate from first_pass, not one wait each.

    QA found the first build checked `age >= MAX_AGE`, which reads as
    "the difference has outlived the TTL" but is not the same claim:
    `age` for an object honouring `max-age=600` cycles in [0, 600) and
    never reaches it, so that branch was reachable only in a fabricated
    test and never on a real fetch. A genuinely stale origin then
    mismatched on every poll forever while this returned None every
    time, and 46 clean pages proved the code path works, not that the
    site was fine. QA's line for it: "a known-bad drawn from the
    reachable branch confirms the code; only one drawn from the actual
    failure mode confirms the check." Waiting on wall-clock time rather
    than trusting the header is what makes "outlives the TTL" mean what
    it says.
    """
    status2, headers2, body2 = fetch(c["url"])
    if status2 != 200:
        return f"{c['url']}: fetch failed on recheck (HTTP {status2 or 'error'}: {body2[:80]})"
    live_claims2 = extractor(body2)
    if live_claims2 == c["committed"]:
        return None  # was propagation lag, not drift
    age = headers2.get("age", "?")
    return (f"{c['url']}: LIVE DOES NOT MATCH COMMITTED, persisted past a "
            f"full cache TTL (age now {age}s, x-cache {headers2.get('x-cache', '?')}) "
            f"live={live_claims2} committed={c['committed']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--channel", choices=sorted(CHANNELS),
                    help="check one channel only; default is all")
    args = ap.parse_args()

    channels = [args.channel] if args.channel else sorted(CHANNELS)
    problems = []
    candidates = []  # (candidate dict, extractor)
    checked = 0
    for channel in channels:
        glob, extractor = CHANNELS[channel]
        paths = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(glob))
        for rel_path in paths:
            checked += 1
            problem, candidate = first_pass(rel_path, extractor)
            if problem:
                problems.append(problem)
            elif candidate:
                candidates.append((candidate, extractor))

    if candidates:
        # ONE wait, shared by every candidate, not one per candidate. The
        # scenario this check exists for, a whole channel's deploy not
        # landing, makes every page in that channel a candidate at the
        # same moment, and they are all waiting on the same clock.
        print(f"  {len(candidates)} candidate mismatch(es), waiting "
              f"{RECHECK_WAIT}s past the cache TTL before rechecking...")
        time.sleep(RECHECK_WAIT)
        for candidate, extractor in candidates:
            problem = recheck_candidate(candidate, extractor)
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
