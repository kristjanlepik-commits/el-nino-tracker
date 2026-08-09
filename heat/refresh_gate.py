"""Decide whether a weekly refresh may publish itself or needs a human.

Kristjan set the cadence on 2026-08-08: Monday refreshes, May to September.
Product ratified this gate. The point is not to slow publishing down but to
make the weeks that need attention distinguishable from the weeks that do
not, because otherwise every week needs the same attention and none gets it.

FOUR TRIGGERS. Two were mine and the two that matter more were product's.

  1  any city's DAY rank moves
  2  the headline record count changes
  3  ANY CITY CHANGES LEGEND BAND                          product
  4  the 2003 comparison flips, so may_say_worst changes    product

Three is the one I would have missed. A city moving between record, near and
outside changes the whole picture the map tells WITHOUT changing any rank,
and the map is the headline. Four is claim-level: it governs whether any page
may say "worst on record" at all, and no rank captures it.

WHY IT COMPARES PAYLOADS RATHER THAN RECOMPUTING. The previous published
payload is the only external reference for what a reader last saw. Deriving
"what changed" from the new data alone would be the Barcelona failure again:
a denominator taken from the artifact under test.

EXIT CODE IS THE PRODUCT. 0 means publish, 1 means a human looks. Printing a
verdict and exiting 0 would make this a comment, which is the shape of guard
this project has already shipped twice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "heat" / "data" / "city_nights.json"
PREVIOUS = ROOT / "heat" / "data" / "published" / "city_nights.json"


def compare(prev, cur):
    """Return a list of triggered reasons. Empty means safe to publish."""
    hits = []

    pc, cc = prev.get("cities", {}), cur.get("cities", {})
    added = sorted(set(cc) - set(pc))
    removed = sorted(set(pc) - set(cc))
    if added:
        hits.append(f"cities added: {added}")
    if removed:
        hits.append(f"cities REMOVED: {removed}")

    for c in sorted(set(pc) & set(cc)):
        p, n = pc[c], cc[c]
        pr = p.get("days", {}).get("rank", {}).get("value")
        nr = n.get("days", {}).get("rank", {}).get("value")
        if pr != nr:
            hits.append(f"{c}: day rank {pr} -> {nr}")
        pb, nb = p.get("legend_band"), n.get("legend_band")
        if pb != nb:
            hits.append(f"{c}: legend band {pb} -> {nb}")

    pd = prev.get("day_headline", {})
    nd = cur.get("day_headline", {})
    if pd.get("records") != nd.get("records"):
        hits.append(f"day record count {pd.get('records')} -> {nd.get('records')}")
    if pd.get("may_say_worst_on_record") != nd.get("may_say_worst_on_record"):
        hits.append("the 2003 comparison FLIPPED: may_say_worst_on_record "
                    f"{pd.get('may_say_worst_on_record')} -> "
                    f"{nd.get('may_say_worst_on_record')}")

    ph = prev.get("headline", {})
    nh = cur.get("headline", {})
    if ph.get("records") != nh.get("records"):
        hits.append(f"night record count {ph.get('records')} -> {nh.get('records')}")
    if ph.get("may_say_worst_on_record") != nh.get("may_say_worst_on_record"):
        hits.append("nights may_say_worst_on_record flipped")
    return hits


def main() -> int:
    if not PREVIOUS.exists():
        # No baseline means nothing to compare against, and treating that as
        # "nothing changed" would let the first refresh through unexamined.
        print("  HOLD: no previously published payload to compare against.",
              file=sys.stderr)
        return 1
    prev = json.loads(PREVIOUS.read_text())
    cur = json.loads(CURRENT.read_text())
    hits = compare(prev, cur)
    if not hits:
        print("  PUBLISH: no rank moved, no band changed, no count changed, "
              "the 2003 comparison holds.")
        return 0
    print(f"  HOLD: {len(hits)} change(s) a reader would notice. "
          f"Product decides before this ships.", file=sys.stderr)
    for h in hits:
        print(f"    - {h}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
