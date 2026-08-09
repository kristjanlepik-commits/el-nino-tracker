#!/usr/bin/env python3
"""Decide whether a heat refresh may publish itself or needs product.

WHY THIS EXISTS. The 26 heat pages are built from a payload, and each
weekly refresh advances the cut. That is a substantive change rather than
a top-up: advancing the cut changes every count and can move ranks, move
a city between legend bands, and change the headline. Heat measured a
one-day advance on 7 August in which no rank moved and 14 counts changed,
and were explicit that this was luck rather than a property of the data.

So the question a refresh has to answer is not "did anything change", it
is "did anything change that a reader would read as a different claim".

THE GATE, product's spec, ratified 2026-08-09. Publish automatically only
if all four hold; otherwise it goes to product before it ships.

    1. no city's rank changes
    2. the headline count is unchanged
    3. no city changes legend band (record / near / outside)
    4. the 2003 comparison does not flip

Conditions 3 and 4 are product's additions to heat's version, and both
earn their place. A city moving between bands changes the whole picture
of the map without moving anyone's rank. The 2003 comparison governs
whether a page may say "worst on record" at all, so a flip is a
claim-level change that no rank captures.

DEFINITIONS ARE READ FROM THE RENDERER, not restated here. `state()` and
NEAR_RANK are imported from design/make_heat_index.py so the bands this
gate compares are by construction the bands the page draws. A gate that
reimplements its subject's logic drifts from it silently, and then passes
while the page says something else, which is this week's whole lesson.

THE 2003 COMPARISON IS SET-LEVEL, AND THE PAYLOAD ALREADY ANSWERS IT.
The first version of this gate compared each city's 2026 count against
its own 2003 count. That was wrong, product corrected it, and the
correction is worth keeping visible: per-city it fires constantly and
does not track the claim at all. The question is how many cities in the
SET are at a record now against how many were in 2003, per instrument.

Better than recomputing that: `headline.may_say_worst_on_record` and
`day_headline.may_say_worst_on_record` are already in the payload, and
they are not the arithmetic. They carry the forecast-selection
correction, which no count can see: six cities were chosen off a 2026
forecast, so the set leans toward 2026's heat by construction, which
makes "2003 was worse" conservative and "2026 is worse" circular. On
2026-08-09 nights read 17 against 12 and STILL said False, because with
the forecast-selected cities removed it does not clear.

So this gate reads the flag rather than deriving it, exactly as it reads
`state()` out of the renderer. Both counts are tracked too, so a crossing
is reported even in the cases where the flag does not move.

EXIT CODES follow the repo convention: 0 did work and it may publish,
3 nothing to compare against, 2 held for product. A hold is not an error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "design"))

NIGHTS = ROOT / "heat/data/city_nights.json"
SERIES = ROOT / "heat/data/city_series.json"
SNAPSHOT = ROOT / "heat/data/refresh_snapshot.json"

# The extreme-day threshold the pages count on. Same key the index
# generator reads for its baseline mean.
EXTREME = "95"


def _state_fns():
    """Borrow the renderer's own band logic rather than restating it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_mhi", ROOT / "design/make_heat_index.py")
    # The module builds pages at import, so read the two definitions out
    # of its source instead of executing it. They are small, stable, and
    # a gate that renders 27 pages as a side effect of checking them is
    # not a gate.
    src = (ROOT / "design/make_heat_index.py").read_text()
    ns: dict = {}
    import re
    near = re.search(r"^NEAR_RANK\s*=\s*(\d+)", src, re.M)
    fn = re.search(r"^def state\(d\):\n(?:.+\n)+?(?=\n)", src, re.M)
    if not (near and fn):
        raise SystemExit(
            "heat_diff_gate: cannot find NEAR_RANK or state() in "
            "design/make_heat_index.py. The gate borrows the renderer's "
            "band logic on purpose; if that moved, this must follow it "
            "rather than guess.")
    ns["NEAR_RANK"] = int(near.group(1))
    exec(fn.group(0), ns)
    return ns["state"], ns["NEAR_RANK"]


def summarise() -> dict:
    N = json.loads(NIGHTS.read_text())
    S = json.loads(SERIES.read_text())["cities"]
    state, _near = _state_fns()

    cities = {}
    for name, v in N["cities"].items():
        rank = v["days"]["rank"]["value"]
        cities[name] = {"rank": rank, "band": state({"rank": rank})}

    def instrument(block):
        base = block.get("baseline", {}).get("worst_year_on_record", {}) or {}
        return {"records": block.get("records"),
                "of_cities": block.get("of_cities"),
                # 2003 names the count differently in the two blocks
                # ("records" for nights, "cities" for days). Read both
                # rather than pick one and silently get None.
                "prior_worst_year": base.get("year"),
                "prior_worst_count": base.get("records", base.get("cities")),
                "may_say_worst": block.get("may_say_worst_on_record")}

    return {"counted_to": N["cities"][next(iter(N["cities"]))].get("counted_to"),
            "nights": instrument(N["headline"]),
            "days": instrument(N["day_headline"]),
            "cities": cities}


def compare(prev: dict, now: dict) -> list[str]:
    """The four conditions. Returns the reasons to hold, empty if clear."""
    reasons = []

    for inst in ("nights", "days"):
        a, b = prev.get(inst, {}), now.get(inst, {})
        if a.get("records") != b.get("records"):
            reasons.append(
                f"HEADLINE ({inst}): {a.get('records')} of {a.get('of_cities')} "
                f"at a record becomes {b.get('records')} of "
                f"{b.get('of_cities')}. This is the sentence at the top of the "
                f"channel.")
        # The claim gate, which is not the arithmetic. It carries the
        # forecast-selection correction that no count can see, so it can
        # move while the counts do not, and can stay put while they do.
        if a.get("may_say_worst") != b.get("may_say_worst"):
            reasons.append(
                f"CLAIM ({inst}): may_say_worst_on_record goes "
                f"{a.get('may_say_worst')} to {b.get('may_say_worst')}. This "
                f"governs whether any page may say worst on record, and it is "
                f"the one change here that rewrites sentences rather than "
                f"numbers.")
        # Crossing 2003 in either direction, reported even when the flag
        # above does not move, because product's trigger is the set count
        # crossing and the flag can be held back for selection reasons.
        def side(d):
            r, p = d.get("records"), d.get("prior_worst_count")
            return None if r is None or p is None else (
                "above" if r > p else "below" if r < p else "equal")
        if side(a) != side(b):
            reasons.append(
                f"2003 ({inst}): the set was {side(a)} its "
                f"{a.get('prior_worst_year')} count of {a.get('prior_worst_count')} "
                f"and is now {side(b)} against {b.get('prior_worst_count')}.")

    gone = sorted(set(prev["cities"]) - set(now["cities"]))
    added = sorted(set(now["cities"]) - set(prev["cities"]))
    if gone:
        reasons.append(f"CITIES REMOVED: {', '.join(gone)}. A city leaving the "
                       f"set is never automatic.")
    if added:
        reasons.append(f"CITIES ADDED: {', '.join(added)}. A new city changes "
                       f"every denominator on the index.")

    for name in sorted(set(prev["cities"]) & set(now["cities"])):
        a, b = prev["cities"][name], now["cities"][name]
        if a["rank"] != b["rank"]:
            reasons.append(f"RANK: {name} moves {a['rank']} to {b['rank']}.")
        if a["band"] != b["band"]:
            reasons.append(
                f"BAND: {name} moves from {a['band']} to {b['band']}, which "
                f"changes its mark on the map and its group on the index.")
    return reasons


def schema_ok(snap: dict) -> bool:
    """Is this baseline comparable with what summarise() now produces?

    The per-city 2003 comparison was replaced by a set-level one, so a
    baseline written by the earlier version has fields this no longer
    reads and lacks fields it needs. Comparing across that boundary threw
    a KeyError, which is a bad failure but an honest one; passing would
    have been the dangerous alternative. Refuse explicitly instead and
    say what to do, because "re-baseline" is the correct action and
    nobody should have to read a traceback to find it.
    """
    return all(k in snap for k in ("nights", "days", "cities"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--update", action="store_true",
                    help="write the current summary as the new baseline, "
                         "after a refresh has been accepted")
    args = ap.parse_args()
    snap = Path(args.snapshot)

    now = summarise()

    if not snap.exists():
        if args.update:
            snap.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n")
            print(f"heat-diff-gate: wrote first baseline to {snap}.")
            return 0
        print(f"heat-diff-gate: no baseline at {snap}, so there is nothing to "
              f"compare against. Run with --update once the current payload "
              f"is known good. Not treating an absent baseline as a pass.")
        return 3

    prev = json.loads(snap.read_text())
    if not schema_ok(prev):
        if args.update:
            snap.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n")
            print(f"heat-diff-gate: replaced an incomparable baseline at "
                  f"{snap}. Nothing was compared, so this run asserts "
                  f"nothing about the payload.")
            return 0
        print(f"heat-diff-gate: the baseline at {snap} predates the set-level "
              f"2003 comparison and cannot be compared against. Re-baseline "
              f"with --update once the current payload is known good. Not "
              f"treating an incomparable baseline as a pass.")
        return 3
    reasons = compare(prev, now)

    print(f"  cut        {prev.get('counted_to')} -> {now.get('counted_to')}")
    for inst in ("nights", "days"):
        a, b = prev.get(inst, {}), now.get(inst, {})
        print(f"  {inst:<9}  {a.get('records')} -> {b.get('records')} of "
              f"{b.get('of_cities')} at a record | 2003 "
              f"{b.get('prior_worst_count')} | may say worst: "
              f"{a.get('may_say_worst')} -> {b.get('may_say_worst')}")
    print(f"  cities     {len(prev['cities'])} -> {len(now['cities'])}\n")

    if reasons:
        print(f"HOLD: {len(reasons)} reader-visible change(s). This refresh "
              f"goes to product before it ships.\n")
        for r in reasons:
            print(f"  {r}")
        print("\nNothing here is an error. It is the gate doing its job; a "
              "refresh that moves a rank or a claim wants a human.")
        return 2

    if args.update:
        snap.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n")
        print("baseline updated.")
    print("CLEAR: no rank, band, headline or 2003 change. Safe to publish "
          "automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
