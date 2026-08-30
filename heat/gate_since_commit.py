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

WATCHED = [
    ("days", "rank", "value"), ("days", "rank", "of_years"),
    ("rank", "value"), ("rank", "of_years"),
    ("legend_band",), ("counted_to",),
    ("joined", "caveat_required"),
]


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
        for path in WATCHED:
            a, b = dig(oc[c], path), dig(cc[c], path)
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
