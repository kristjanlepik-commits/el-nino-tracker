"""Do the rendered pages say what the payload says? Checked, not assumed.

WHY THIS EXISTS. On 22 August three chats independently believed the heat
pages were current and they were not. The payload said 21 August, design's
sweep updated most pages, three kept their previous renders, and nobody
noticed because each layer looked fine from where they stood:

    heat      the payload is correct and committed     true
    design    the render ran and did not error         true
    platform  budapest, vilnius and zagreb are present true

Every statement was true and the site was still wrong. Budapest sat live
claiming "the most hot days Budapest has recorded", eleven days stale, on a
first appearance, with no note that it had joined the set three days earlier.

THE GAP IS BETWEEN LAYERS, so no layer's own check can close it. Existence was
the right test for pages that had never existed; the moment they exist, "is it
there" stops being the question and "what does it say" starts.

WHAT THIS CHECKS, and it is deliberately narrow: for every city in the
payload, does its rendered page carry the SAME cut date, and where the payload
says a selection caveat is required, is that caveat on the page. Those two
because they are the ones that have actually gone wrong, not because they are
the only things that could.

It reads the rendered HTML, strips tags before searching, and takes a URL
instead of a path when asked to check live rather than local. Both matter:
the date sits inside a span so a raw grep finds nothing, and a local file
being right says nothing about what a reader is served.
"""
from __future__ import annotations

import html as _html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "heat" / "data" / "city_nights.json"
DOCS = ROOT / "docs" / "heat"
LIVE = "https://thelongswell.com/heat"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def as_text(markup):
    """Strip tags before searching. A phrase that reads as one string on the
    page is usually split across tags in the source, so a grep for it finds
    nothing and looks exactly like proof of absence."""
    t = _html.unescape(markup)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", t))


def expected_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def fetch(city, live):
    """Return (markup, error). An UNREADABLE page is not a WRONG page.

    The first version returned "" for both, so a fetch that failed and a page
    whose date was missing produced the same output, and the caller reported
    "page says to None" for a page it had never read. Design hit it on Berlin,
    reported stale against a page that matched its payload, and product hit
    the same shape an hour later reading a 404 as a missing caveat.

    That is the exact failure this channel spent the week naming: absence
    produced by a failure, presented as absence measured. It is uncomfortable
    that it was in the tool written to stop it, and it is the reason a guard
    gets checked like anything else.
    """
    if live:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "40", "-w", "\n%{http_code}",
             f"{LIVE}/{city}.html"], capture_output=True)
        body = r.stdout.decode("utf-8", "replace")
        if r.returncode != 0:
            return "", f"fetch failed: curl exit {r.returncode}"
        body, _, code = body.rpartition("\n")
        if code.strip() != "200":
            return "", f"HTTP {code.strip()}, page not read"
        if len(body) < 500:
            return "", f"only {len(body)} bytes returned, not a page"
        return body, None
    p = DOCS / f"{city}.html"
    if not p.exists():
        return "", "no file in docs/"
    return p.read_text(errors="replace"), None


def check(live=False):
    payload = json.loads(PAYLOAD.read_text())["cities"]
    bad, unread = [], []
    for name, v in sorted(payload.items()):
        slug = name.lower().replace(" ", "-")
        markup, err = fetch(slug, live)
        if err:
            # UNREADABLE, not wrong. Reported separately so a network fault
            # is never counted as a page defect.
            unread.append(f"{name}: {err}")
            continue
        text = as_text(markup)
        want = expected_date(v["counted_to"])
        m = re.search(r"to (\d+ \w+ \d{4})", text)
        got = m.group(1) if m else None
        if got != want:
            bad.append(f"{name}: page says 'to {got}', payload says "
                       f"'to {want}'. The render is stale.")
        j = v.get("joined") or {}
        if j.get("caveat_required") and "Added to the set on" not in text:
            bad.append(
                f"{name}: payload sets caveat_required, and the page does "
                f"not carry it. This city joined {j.get('days_in_set')} days "
                f"ago and sits at or near its own record, so the page makes "
                f"a record claim a reader cannot check the selection of.")
    return bad, unread, len(payload)


def main() -> int:
    live = "--live" in sys.argv
    bad, unread, n = check(live)
    where = "LIVE" if live else "docs/"
    if unread:
        print(f"  {where}: {len(unread)} page(s) COULD NOT BE READ. This is "
              f"not a verdict on them.", file=sys.stderr)
        for u in unread:
            print(f"    ? {u}", file=sys.stderr)
    if not bad and not unread:
        print(f"  {where}: all {n} pages match the payload on cut date and "
              f"selection caveat.")
        return 0
    if not bad:
        print(f"  {where}: {n - len(unread)} of {n} checked and matching; "
              f"{len(unread)} unread. NOT a pass.", file=sys.stderr)
        return 1
    print(f"  {where}: {len(bad)} of {n} pages disagree with the payload.",
          file=sys.stderr)
    for b in bad:
        print(f"    - {b}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
