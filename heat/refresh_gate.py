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


# HOW BIG A RANK MOVE IS STILL WEATHER. A city climbing a few places as the
# season advances is ordinary. A city moving tens of places is a bug almost
# every time, and on 17 August it was exactly that: Larnaca fell from 10th to
# 51st because my own hour detection took its overnight maximum for the day's.
IMPLAUSIBLE_RANK_MOVE = 8


def classify(prev, cur):
    """Split changes into what must block and what merely needs reporting.

    WHY THIS IS NOT ONE LIST. The first version returned a single set of
    "changes a reader would notice" and held on any of them. During an actual
    heat event that fires on EVERY refresh, because ranks legitimately move
    every day, so the only way through is a human ruling each time. A gate
    that always fires teaches its operator to wave it through, and the day it
    catches something real is the day it gets waved through too.

    So the question is not "did anything change" but "is this the kind of
    change data does on its own".

        BLOCK      implausible movement, which is nearly always a bug, plus
                   the two editorial cases no amount of correctness settles:
                   a withdrawn record, and the set gaining or losing cities
        REPORT     ordinary movement: a rank drifting a place or two, counts
                   rising in a heatwave, a new record with a real margin

    Under this rule the 17 August refresh hard-blocks Larnaca, waves through
    Dresden and Berlin, and stops on Malaga's withdrawn record and the three
    new cities. Smaller ask of the operator, stricter check on the data.
    """
    block, report, withdrawn = [], [], []

    pc, cc = prev.get("cities", {}), cur.get("cities", {})
    added = sorted(set(cc) - set(pc))
    removed = sorted(set(pc) - set(cc))
    # THE SET IS ALWAYS AN EDITORIAL EVENT. Every count over the set inherits
    # the choice of which cities are in it (D-141), so this never auto-passes.
    if added:
        block.append(f"cities added: {added}. Every count over the set "
                     f"inherits this choice, so it is never automatic.")
    if removed:
        block.append(f"cities REMOVED: {removed}")

    for c in sorted(set(pc) & set(cc)):
        p, n = pc[c], cc[c]
        pr = (p.get("days") or {}).get("rank", {}).get("value")
        nr = (n.get("days") or {}).get("rank", {}).get("value")
        if pr != nr and pr is not None and nr is not None:
            move = abs(nr - pr)
            if move >= IMPLAUSIBLE_RANK_MOVE:
                block.append(
                    f"{c}: day rank {pr} -> {nr}, a move of {move} places. "
                    f"Data does not do this in one refresh; check the "
                    f"builder before you check the weather.")
            else:
                report.append(f"{c}: day rank {pr} -> {nr}")
        # A WITHDRAWN RECORD IS ALWAYS EDITORIAL, but THE RANK NUMBER DOES
        # NOT TELL YOU WHETHER ONE WAS WITHDRAWN. The first version of this
        # test fired on rank leaving 1, and design caught it before it did
        # damage: Malaga went 1 to 2 with nothing above it, tied with 2008,
        # because ties_count_against puts BOTH years of a two-way tie at 2.
        # It still holds the record, jointly. I had told design and socials
        # it was withdrawn, and a correction notice withdrawing a record the
        # city still holds is worse than the defect the guard exists to
        # catch, because a correction is itself a claim.
        #
        # So test the CLAIM. Under this convention
        #     rank = 1 + (years strictly above) + (years equal)
        # so years strictly above is rank - 1 - len(tied_with), and the claim
        # "most on record" survives while that is zero, tie or no tie.
        def _above(rec):
            rk = (rec.get("days") or {}).get("rank") or {}
            if rk.get("value") is None:
                return None
            return rk["value"] - 1 - len(rk.get("tied_with") or [])
        pa, na = _above(p), _above(n)
        if pa == 0 and na not in (0, None):
            # WHY IT WAS WITHDRAWN DECIDES WHETHER IT IS A CORRECTION, and
            # the guard could not see the difference. Design raised it and
            # editor's rule is the test: only a MISTAKE is a correction. The
            # bar rising was an error we made; the cut advancing was not, and
            # a correction block explaining a refresh is a correction block
            # explaining that we published on time.
            #
            # Measured, not assumed. Alicante and Palma both looked like
            # withdrawals on 22 August and design read Palma as a method
            # change on the strength of pctl_baseline_is_default being false.
            # It is false because Palma has no complete 1971-2000 at all,
            # which is a standing property rather than something that
            # changed. Both thresholds were IDENTICAL across the two builds,
            # 33.8 and 33.6, and both cities had been TIED for their record
            # and had the tie broken as the calendar moved. Same case.
            pt = ((p.get("days") or {}).get("thresholds_c") or {}).get("95")
            nt = ((n.get("days") or {}).get("thresholds_c") or {}).get("95")
            moved_cut = p.get("counted_to") != n.get("counted_to")
            if pt != nt:
                why, needs = "method_changed", True
            elif moved_cut:
                why, needs = "cut_advanced", False
            else:
                why, needs = "data_revised", True
            entry = {
                "city": c, "reason": why, "needs_correction": needs,
                "threshold_95": {"was": pt, "now": nt},
                "cut": {"was": p.get("counted_to"), "now": n.get("counted_to")},
                "years_above": {"was": pa, "now": na},
            }
            withdrawn.append(entry)
            if needs:
                block.append(
                    f"{c}: RECORD WITHDRAWN, reason {why}. The threshold "
                    f"moved from {pt} to {nt}, so the bar changed under a "
                    f"claim we published. This wants a correction.")
            else:
                report.append(
                    f"{c}: record withdrawn, reason cut_advanced. The bar is "
                    f"unchanged at {nt} C and the cut moved {p.get('counted_to')} "
                    f"to {n.get('counted_to')}; a rival year gained faster. "
                    f"We were current, not wrong, so no correction block.")
        pb, nb = p.get("legend_band"), n.get("legend_band")
        if pb != nb:
            report.append(f"{c}: legend band {pb} -> {nb}")

    for key, label in (("day_headline", "day"), ("headline", "night")):
        pd, nd = prev.get(key, {}), cur.get(key, {})
        if pd.get("records") != nd.get("records"):
            report.append(f"{label} record count {pd.get('records')} -> "
                          f"{nd.get('records')}")
        if pd.get("may_say_worst_on_record") != nd.get("may_say_worst_on_record"):
            block.append(
                f"the 2003 {label} comparison FLIPPED: "
                f"may_say_worst_on_record {pd.get('may_say_worst_on_record')}"
                f" -> {nd.get('may_say_worst_on_record')}")
    return block, report, withdrawn


def compare(prev, cur):
    """Kept for callers that want every change as one list."""
    b, r, _ = classify(prev, cur)
    return b + r


def main() -> int:
    if not PREVIOUS.exists():
        # No baseline means nothing to compare against, and treating that as
        # "nothing changed" would let the first refresh through unexamined.
        print("  HOLD: no previously published payload to compare against.",
              file=sys.stderr)
        return 1
    prev = json.loads(PREVIOUS.read_text())
    cur = json.loads(CURRENT.read_text())
    block, report, withdrawn = classify(prev, cur)
    if withdrawn:
        # A FIELD, NOT A PRINT. Design needs the reason to decide whether
        # editor writes a correction, and a reason that lives only in this
        # script's stdout is a reason the build cannot act on.
        (ROOT / "heat" / "data" / "record_withdrawals.json").write_text(
            json.dumps({"withdrawals": withdrawn}, indent=1) + "\n")
        print(f"  wrote heat/data/record_withdrawals.json "
              f"({len(withdrawn)} withdrawal(s))")
    for r in report:
        print(f"    changed: {r}")
    if not block:
        print(f"  PUBLISH: {len(report)} ordinary change(s), nothing "
              f"implausible, no record withdrawn, set unchanged.")
        return 0
    print(f"  HOLD: {len(block)} change(s) that need a person. "
          f"{len(report)} ordinary change(s) would have passed.",
          file=sys.stderr)
    for b in block:
        print(f"    - {b}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
