"""What moved in an unpublished city since a given commit?

WHY THIS IS SEPARATE FROM refresh_gate. That gate compares the payload with
what readers currently see, which is the right question before a publish and
the wrong one for a city readers have never seen. A city added but not yet
live is reported once as "added" and can then change on every commit with
nothing noticing.

Design found Neuquen doing exactly that: day rank 5 to 6, legend band near to
outside, joined.caveat_required true to false, between two of my commits,
while the refresh gate reported two ordinary changes and neither was Neuquen.
The cause turned out to be data rather than code, a bridge rerun filling gaps
in 2008 and 2011, which is if anything worse: historical counts moved and
nothing in my tooling would have said so.

So this asks the other question. Run it before handing a payload to design.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "heat" / "data" / "city_nights.json"

# EVERY NUMBER, MINUS AN EXPLICIT IGNORE LIST. This was an allowlist of
# seven paths and it watched where a city PLACES without watching what it
# DID.
#
# Design caught it on 2026-08-30. Removing a corrupt 91.0 C reading from
# Salta lowered that station's own 95th percentile, so more days cleared it
# and the count went 9 to 11. I reported "only Salta's ranks moved" because
# that is what this gate told me, and the count is the number the headline
# prints. They would have shipped a page saying 9 if they had trusted my
# report over the payload. Earlier the same evening I said "no European city
# moved", also true, also narrower than what I let it stand for.
#
# Both omissions ran the same direction, and an allowlist guarantees that
# direction: a field nobody thought to add is silently identical to a field
# that did not change. So the default is now inverted. Every scalar leaf is
# compared and the list below says what to ignore, which fails loud instead
# of quiet: a new field I forget about shows up as noise I then classify,
# rather than as silence I mistake for stability.
IGNORE_SUBSTRINGS = ("note", "_readme", "caveat_text", "reason", "basis",
                     "label_note", "deprecated", "banned_words")


def leaves(d, path=()):
    """Every scalar leaf in the city entry, as (path tuple, value).

    Lists are compared whole rather than walked, because a per-year series
    changing length is itself the news and element-wise diffs would bury it.
    """
    if isinstance(d, dict):
        for k, v in d.items():
            yield from leaves(v, path + (k,))
    else:
        yield path, d


def watched(path):
    """Prose is excluded; numbers never are."""
    return not any(sub in k for k in path for sub in IGNORE_SUBSTRINGS)


def dig(d, path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    old = json.loads(subprocess.run(
        ["git", "show", f"{ref}:heat/data/city_nights.json"],
        capture_output=True, text=True, cwd=ROOT).stdout or "{}")
    cur = json.loads(CUR.read_text())
    oc, cc = old.get("cities", {}), cur.get("cities", {})
    hits = []
    for c in sorted(set(oc) & set(cc)):
        before = {p: v for p, v in leaves(oc[c]) if watched(p)}
        after = {p: v for p, v in leaves(cc[c]) if watched(p)}
        for path in sorted(set(before) | set(after)):
            a, b = before.get(path, "<absent>"), after.get(path, "<absent>")
            if a != b:
                hits.append(f"{c}: {'.'.join(path)} {a} -> {b}")
    added = sorted(set(cc) - set(oc))
    if added:
        print(f"  added since {ref}: {added}")
    if not hits:
        print(f"  no watched field moved in any city present at {ref}.")
        return 0
    print(f"  {len(hits)} field(s) moved since {ref}:", file=sys.stderr)
    for h in hits:
        print(f"    - {h}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
