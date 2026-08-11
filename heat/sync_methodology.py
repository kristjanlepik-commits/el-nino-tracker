"""Regenerate the live claims in heat/methodology.md from the payload.

WHY. The set grew 15 -> 21 -> 24 -> 36 in five days and the prose went stale
at every step. Product held the page off rendering on the day the channel is
promoted to two accounts of roughly 9,800 followers, because line 110 said the
night metric is gated in 10 of 24 cities when the payload says 19 of 36. That
moves night coverage from 58% to 47%: **the document claimed the measure works
for a clear majority of the channel when it works for fewer than half**, which
reads as overclaiming rather than as staleness.

THE NIGHT-METRIC GATE HAS NOW BEEN HARDCODED FROM A STALE LIST THREE TIMES.
Design's file, then VD's, both lifted from this prose. This is the prose
itself, so it is the source both copies came from. `nights_metric_gated` is
emitted per city and correct; every consumer that retyped it was wrong within
days.

WHAT THIS DOES NOT TOUCH. The version history from line 162 is CORRECT AS
HISTORY: "fifteen", "twenty-one", "twenty-four" record what was true at v1.1,
v1.2, v1.3. A changelog is not a stale claim, and regenerating it would
destroy the only record of how the set grew. Only live claims move.

FAILS LOUDLY IF AN ANCHOR IS MISSING. A sync script that silently matches
nothing is worse than no script: it reports success and leaves the document
stale, which is exactly the failure mode it exists to prevent.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "heat" / "methodology.md"
PAYLOAD = ROOT / "heat" / "data" / "city_nights.json"

# GENERATED, not enumerated. The hand-written map stopped at 40 and the set
# reached 41 the same afternoon, so a number-word helper became the thing
# that went stale. Design found it. A lookup table of the numbers we happen
# to use today is the same defect as a typed count.
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _word(n):
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return _TENS[t] + ("-" + _ONES[o] if o else "")
    return str(n)


def _w(n):
    return _word(n)


def rules(d):
    cs = d["cities"]
    n = len(cs)
    gated = sorted(c for c, v in cs.items() if v.get("nights_metric_gated"))
    iberia_fr = sum(1 for v in cs.values() if v["country"] in ("ES", "FR"))
    east = d["selection"]["longitude_span"][1]
    day_rec = sum(1 for v in cs.values() if v["days"]["rank"]["value"] == 1)
    return [
        # line 3: the channel's own scale
        (r"The heat channel tracks two things in [a-z\-]+ European cities:",
         f"The heat channel tracks two things in {_w(n)} European cities:"),
        # line 91: the selection consequence
        (r"[A-Z][a-z\-]+ of the [a-z\-]+ are Iberia and France, there is\nno city east of [\d.]+ degrees",
         f"{_w(iberia_fr).capitalize()} of the {_w(n)} are Iberia and France, "
         f"there is\nno city east of {east} degrees"),
        # line 96: the worked example of the framing rule. Uses a REAL current
        # figure rather than a decorative one, so it cannot drift from the
        # thing it is teaching.
        # Number words may be hyphenated now that they are generated,
        # so the anchor must allow it. The previous pattern silently
        # stopped matching the moment the count reached twenty-two.
        (r'"[A-Z][a-z\-]+ of [a-z\-]+" is',
         f'"{_w(day_rec).capitalize()} of {_w(n)}" is'),
        # line 110: the gate, which is the one that has been retyped three
        # times. The LIST is regenerated too, not just the count, because a
        # correct count beside a short list is the same defect wearing a
        # better number.
        (r"\d+ of the \d+ cities average too few tropical nights for the "
         r"measure to\ncarry a ratio: [^.]+\.",
         f"{len(gated)} of the {n} cities average too few tropical nights "
         f"for the measure to\ncarry a ratio: {', '.join(gated)}."),
    ]


def main() -> int:
    d = json.loads(PAYLOAD.read_text())
    text = DOC.read_text()
    # Version history is off limits. Split it out so no rule can reach it.
    marker = "\n## Version history"
    head, sep, tail = text.partition(marker)
    if not sep:
        print("  no version-history marker; refusing to run in case a rule "
              "rewrites the changelog", file=sys.stderr)
        return 1
    changed, missed = 0, []
    for pat, repl in rules(d):
        new, k = re.subn(pat, repl, head, count=1)
        if k == 0:
            missed.append(pat[:48])
        else:
            changed += k
            head = new
    if missed:
        print("  ANCHOR NOT FOUND, document not written:", file=sys.stderr)
        for m in missed:
            print(f"    {m}", file=sys.stderr)
        return 1
    DOC.write_text(head + sep + tail)
    print(f"  {changed} live claims regenerated, version history untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
