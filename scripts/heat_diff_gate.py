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

ONE DEFINITION IS MINE AND NEEDS CONFIRMING. Product specified "the 2003
comparison" without stating the arithmetic, and nothing in the payload
names one, so this compares each city's 2026 extreme-day count against
its own 2003 count at the same cut and flags a flip when any city crosses
that line in either direction. That is the reading that matches how the
pages use 2003, as a per-city benchmark year, but it is an assumption and
it is flagged as such rather than buried.

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
        years = S[name]["years"]

        def count(y):
            rec = years.get(str(y)) or {}
            d = rec.get("days_to_cut") or {}
            return d.get(EXTREME)

        now, then = count(2026), count(2003)
        if now is None or then is None:
            cmp2003 = None
        elif now > then:
            cmp2003 = "above"
        elif now < then:
            cmp2003 = "below"
        else:
            cmp2003 = "equal"
        cities[name] = {"rank": rank,
                        "band": state({"rank": rank}),
                        "vs_2003": cmp2003}

    return {"counted_to": N["cities"][next(iter(N["cities"]))].get("counted_to"),
            "headline_records": N["day_headline"]["records"],
            "of_cities": N["day_headline"]["of_cities"],
            "cities": cities}


def compare(prev: dict, now: dict) -> list[str]:
    """The four conditions. Returns the reasons to hold, empty if clear."""
    reasons = []

    if prev["headline_records"] != now["headline_records"]:
        reasons.append(
            f"HEADLINE: {prev['headline_records']} cities at a day record "
            f"becomes {now['headline_records']}. This is the sentence at the "
            f"top of the channel.")

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
        if a["vs_2003"] != b["vs_2003"]:
            reasons.append(
                f"2003: {name} was {a['vs_2003']} its 2003 count and is now "
                f"{b['vs_2003']}. This is the comparison that governs whether "
                f"a page may claim a worst-on-record summer.")
    return reasons


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
    reasons = compare(prev, now)

    print(f"  cut        {prev.get('counted_to')} -> {now.get('counted_to')}")
    print(f"  headline   {prev['headline_records']} -> "
          f"{now['headline_records']} of {now['of_cities']} at a day record")
    print(f"  cities     {len(now['cities'])}\n")

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
