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
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "heat" / "data" / "city_nights.json"
PREVIOUS = ROOT / "heat" / "data" / "published" / "city_nights.json"


# HOW BIG A RANK MOVE IS STILL WEATHER. A city climbing a few places as the
# season advances is ordinary. A city moving tens of places is a bug almost
# every time, and on 17 August it was exactly that: Larnaca fell from 10th to
# 51st because my own hour detection took its overnight maximum for the day's.
IMPLAUSIBLE_RANK_MOVE = 8


# A GUARD MUST HAVE AUTHORITY OVER WHAT IT WITHHOLDS, and two of these do
# not. Floods' finding, 2026-08-30, from their own rainfall floor suppressing
# a RANK when it only had authority over a RATIO. Audited here the same day:
#
#   condition                 evidence covers   this blocks     verdict
#   cities added/removed      the SET           whole payload   right
#   2003 comparison flipped   the SET           whole payload   right
#   implausible rank move     ONE city          whole payload   arguable
#   record withdrawn          ONE city          whole payload   OVER-REACH
#
# An implausible move suggests a builder fault, which could have touched
# anything, so holding everything is defensible. A withdrawn record is one
# city's editorial event and there is no reading under which it makes the
# other 44 pages wrong. Palma's withdrawal held 44 correct pages for days,
# and I described that at the time as the gate working as designed. It was
# partly the gate exceeding its evidence.
#
# NOT FIXED HERE, because the fix is not in this file. Holding one city while
# publishing 44 needs the publisher to support a partial publish, which is
# platform's per-channel scope work one level finer. Recorded so that when
# that lands, this is a known consumer rather than a rediscovery.

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

    # THE GATE IS BLIND TO A CITY IT HAS NEVER PUBLISHED, and design found
    # that before I did. It compares the payload against the PUBLISHED
    # reference, so a city that is added but not yet live is reported once as
    # "added" and can then move freely, commit after commit, with nothing
    # reporting it. Neuquen's day rank went 5 to 6 and its legend band near to
    # outside between two of my commits and this said two ordinary changes,
    # neither of them Neuquen.
    #
    # That window is exactly where the nine new cities sit right now. The gate
    # cannot close it on its own: comparing against the previous COMMIT is a
    # different question from comparing against what readers see, and both are
    # worth asking. Design compares commit to commit and caught it; this is
    # recorded so the division of labour is deliberate rather than accidental.
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

        def _is_record(rec):
            """Rank 1 AND untied. A TIE IS NOT A RECORD, and this guard could
            not see a record lost to one.

            _above subtracts ties back out, so Budapest going from an outright
            rank 1 to rank 3 tied with 2012 and 2015 read as "0 years above"
            both before and after, and no withdrawal was recorded. Its live
            page said "the most hot days Budapest has recorded" while three
            years held that count. Caught 2026-09-07 when a stale GHCN archive
            was refreshed and completed the season.

            The convention is already settled everywhere else in this channel:
            rank_of counts ties against, emit's _is_record requires strictly
            greater, and the payload's tie_note says recomputing with a strict
            greater-than manufactures records. This function was the one place
            that disagreed with all three.
            """
            rk = (rec.get("days") or {}).get("rank") or {}
            return rk.get("value") == 1 and not (rk.get("tied_with") or [])

        pa, na = _above(p), _above(n)
        if _is_record(p) and not _is_record(n):
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
            # ASK THE PAYLOAD WHY BEFORE GUESSING. A record vetoed by a year
            # too incomplete to rank leaves the threshold and the cut both
            # unchanged, so it fell through to data_revised and printed "the
            # threshold moved from 27.9 to 27.9", which is a wrong cause under
            # a right verdict. Design reads this field to decide whether the
            # editor writes a correction, and the two differ: a vetoed record
            # was never true, where cut_advanced was true when published.
            vetoed = ((n.get("days") or {}).get("rank") or {}).get(
                "beaten_by_excluded_years") or []
            if vetoed:
                why, needs = "record_never_held", True
            elif pt != nt:
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
            if why == "record_never_held":
                block.append(
                    f"{c}: RECORD WITHDRAWN, reason record_never_held. "
                    + "; ".join(f"{v['year']} counted {v['count_is_a_floor']} "
                                "and was excluded as incomplete, so it is a "
                                "floor and provably was not beaten"
                                for v in vetoed)
                    + f". The bar is unchanged at {nt} C."
                    + (f" The cut also moved {p.get('counted_to')} to "
                       f"{n.get('counted_to')}, so a rival year gained as "
                       f"well, but that is not why this needs a correction: "
                       f"the published claim was already false at the old "
                       f"cut." if moved_cut else
                       " The cut did not move and no observation was revised.")
                    + " A claim that was wrong when published wants a"
                      " correction, not a refresh.")
            elif needs:
                block.append(
                    f"{c}: RECORD WITHDRAWN, reason {why}. The threshold "
                    f"moved from {pt} to {nt}, so the bar changed under a "
                    f"claim we published. This wants a correction."
                    if pt != nt else
                    f"{c}: RECORD WITHDRAWN, reason {why}. The bar is "
                    f"unchanged at {nt} C and the cut did not move, so an "
                    f"observation was revised under a claim we published. "
                    f"This wants a correction.")
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


def frontier(cur):
    """Which cities did NOT reach the last day they could have.

    WHY THIS EXISTS, and it is the guard three separate bugs got past on
    2026-09-07. Each froze a set of cities at a date and each was invisible,
    because everything that looked at them reported on a MECHANISM rather than
    on whether the date moved:

        tracked sources never refreshed   the builders were not called at all
        a per-city loop with no isolation one failure skipped the remainder
        a cache right for finished years  the current year served from disk

    All three reported success. Rome sat at 2026-08-14 for three and a half
    weeks. Platform's framing is the one worth keeping: the thing that looked
    at it reported on a mechanism rather than on whether the date moved. So
    this asks only the second question and knows nothing about mechanisms.

    THE FRONTIER IS NOT "TODAY", and that distinction is what stops this
    crying wolf. Two bounds apply and the earlier one wins:

        today minus the source's own publication lag, which the payload
        already carries per city as source.lag_days

        the season end, because once the window closes no further day can
        enter the count and a city capped at 31 August is finished, not stale

    ADVISORY, NEVER BLOCKING. A short city is correctly labelled by
    counted_to and publishing it is honest; what failed was that nobody
    noticed. And a real gap belongs to the owning desk before it belongs to
    anyone else: Tallinn's source has genuinely stopped, Aberdeen's bulletins
    were refused by a guard doing its job, and neither is a fault to fix.
    """
    today = datetime.now(timezone.utc).date()
    out = []
    for city, v in sorted(cur.get("cities", {}).items()):
        obs = v.get("counted_to")
        season = (v.get("season") or {}).get("months") or []
        lag = ((v.get("source") or {}).get("lag_days") or 1)
        if not obs or not season:
            continue
        m = season[-1]
        end = date(int(obs[:4]), m, monthrange(int(obs[:4]), m)[1])
        reachable = min(today - timedelta(days=lag), end)
        got = date(int(obs[:4]), int(obs[5:7]), int(obs[8:10]))
        if got < reachable:
            out.append((city, obs, reachable.isoformat(),
                        (reachable - got).days))
    return out


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
        #
        # STAMP IT. The file carries was/now fields and no date, so a stale
        # copy reads exactly like a current one. On 2026-09-07 a version
        # dated 2026-08-30 was read as live and three corrections were
        # nearly escalated against pages that were right. A withdrawal is a
        # claim about a moment; without the moment it cannot be checked.
        (ROOT / "heat" / "data" / "record_withdrawals.json").write_text(
            json.dumps({"generated": datetime.now(timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "generated_against_cut": {
                            c: cur["cities"][c]["counted_to"]
                            for c in sorted({w["city"] for w in withdrawn})
                            if c in cur.get("cities", {})},
                        "withdrawals": withdrawn}, indent=1) + "\n")
        print(f"  wrote heat/data/record_withdrawals.json "
              f"({len(withdrawn)} withdrawal(s))")
    short = frontier(cur)
    if short:
        print(f"\n  {len(short)} city/cities did not reach the last day they "
              f"could have. Advisory, not blocking:")
        for city, obs, reach, days in short:
            print(f"    {city:12s} at {obs}, could have reached {reach}, "
                  f"{days} day(s) short")
        print("  A short city is correctly labelled by counted_to. This says "
              "nobody has looked, not that anything is wrong.")
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
