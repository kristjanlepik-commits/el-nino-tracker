"""River low water from German federal gauges, observed and live.

D-159 routed river low water to this channel and deferred it. This is the
instrument, and it turned out to need no acquisition at all.

WHY THIS WORKS WHEN THE OBVIOUS APPROACH DOES NOT. RIVER_LOW_WATER.md
records two blockers on saying "the Rhine is at its lowest since X": the
published record low carries no reference period, and the gauge datum at
Cologne has validFrom 2019-11-01, AFTER the 2018 record it encodes. Both
bite only when comparing TODAY against a HISTORICAL VALUE.

This does not do that. It asks a cross-sectional question instead: how
much of a river is below its own normal low water RIGHT NOW. WSV already
publishes that judgement per gauge, in `stateMnwMhw`, computed against
that gauge's own reference levels in that gauge's own datum. We count
their classifications rather than computing our own, so no datum is
crossed and no reference period is needed.

The claim it supports is "24 of 26 classified Rhine gauges are below
their mean low water today", attributed to WSV. The claim it does NOT
support is any superlative. History is capped at 30 days (P1Y and P5Y
both fail), so duration within the current spell is available and
"lowest since" is not.

Free, no credential, no expiry. That matters more than it sounds on a
channel whose other two instruments need tokens that have each died once.
"""

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys

BASE = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
# Federal waterways worth reporting. Canals and Baltic/North Sea gauges
# are excluded deliberately: a canal is level-regulated, so "below mean
# low water" is a lock setting rather than a drought.
RIVERS = ["RHEIN", "ELBE", "WESER", "DONAU", "MOSEL", "MAIN", "NECKAR",
          "SAAR", "HAVEL", "SPREE"]
FRESH_HOURS = 6          # a reading older than this is not "now"


def get(url, timeout=90):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", str(timeout), url],
                       capture_output=True)
    body = r.stdout.decode("utf-8", "replace")
    # CONTENT, not status. The house rule of 2026-08-18: three instruments
    # served failures as HTTP 200 that day, so only the body decides.
    if not body.lstrip().startswith(("[", "{")):
        raise SystemExit(f"pegelonline: not JSON ({len(body)} bytes). "
                         f"Refusing to treat a non-answer as an answer.")
    return json.loads(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD, the run date")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    stations = get(f"{BASE}/stations.json?includeTimeseries=true"
                   f"&includeCurrentMeasurement=true", timeout=120)
    # REFERENCE POINT IS THE NEWEST READING, NOT A CLOCK. The first
    # version used as_of at 23:59, which inflated every age by up to a day
    # and reported 0 fresh gauges of 738 without erroring. Anchoring to the
    # newest reading in the payload makes freshness mean "how far behind
    # the rest of the network is this gauge", which is the question, and it
    # cannot be thrown off by clock skew or timezone.
    now = None

    stamps = []
    for s in stations:
        for t in s.get("timeseries", []):
            if t.get("shortname") == "W":
                ts = (t.get("currentMeasurement") or {}).get("timestamp", "")[:16]
                if ts:
                    try:
                        stamps.append(dt.datetime.fromisoformat(ts))
                    except ValueError:
                        pass
    if not stamps:
        raise SystemExit("pegelonline: no timestamps at all. Refusing to "
                         "report an empty network as a measurement.")
    now = max(stamps)

    rows = []
    for s in stations:
        for t in s.get("timeseries", []):
            if t.get("shortname") != "W":
                continue
            cm = t.get("currentMeasurement") or {}
            ts = cm.get("timestamp", "")[:16]
            age = None
            if ts:
                try:
                    age = (now - dt.datetime.fromisoformat(ts)).total_seconds() / 3600
                except ValueError:
                    pass
            rows.append({
                "river": (s.get("water") or {}).get("longname", "?"),
                "station": s.get("longname", "?"),
                "uuid": s.get("uuid"),
                "value_cm": cm.get("value"),
                "state": cm.get("stateMnwMhw"),
                "timestamp": ts,
                "age_hours": None if age is None else round(age, 1),
            })

    out = {
        "reference_time": now.isoformat(),
        "instrument": "WSV Pegelonline, German federal waterway gauges",
        "measures": "water level against each gauge's own mean low water",
        "authorship": "tls_built",
        "evidence_basis": "measured",
        "generated": args.as_of,
        "method": (
            "WSV classifies each gauge against ITS OWN mean low and mean high "
            "water, in that gauge's own datum. We count their classifications "
            "rather than computing our own, so no datum is crossed and no "
            "reference period is assumed."),
        "cannot_claim": (
            "any superlative. Pegelonline serves at most 30 days of history "
            "(P1Y and P5Y both fail), so duration within the current spell is "
            "available and 'lowest since' is not. That would need GRDC or the "
            "BfG archive, and the gauge datum question in "
            "floods/RIVER_LOW_WATER.md would have to be settled first."),
        "rivers": [],
    }

    stale = [r for r in rows if r["age_hours"] is None or r["age_hours"] > FRESH_HOURS]
    for river in RIVERS:
        rs = [r for r in rows if r["river"] == river
              and r["age_hours"] is not None and r["age_hours"] <= FRESH_HOURS]
        if not rs:
            continue
        c = collections.Counter(str(r["state"]) for r in rs)
        known = [r for r in rs if r["state"] in ("low", "normal", "high")]
        low = [r for r in known if r["state"] == "low"]
        out["rivers"].append({
            "river": river.title(),
            "gauges_fresh": len(rs),
            "gauges_classified": len(known),
            # UNCLASSIFIED IS REPORTED, NEVER SILENTLY DROPPED. Roughly half
            # of all WSV gauges carry no mean-low-water value, so a
            # percentage computed over every gauge would be wrong and a
            # percentage computed over classified ones is only honest if the
            # denominator travels with it.
            "gauges_unclassified": len(rs) - len(known),
            "low": len(low),
            "normal": sum(1 for r in known if r["state"] == "normal"),
            "high": sum(1 for r in known if r["state"] == "high"),
            "share_low_of_classified": (round(len(low) / len(known), 3)
                                        if known else None),
            "verdict": ("measured" if len(known) >= 5 else "too_few_gauges"),
            "lowest_gauges": sorted(
                ({"station": r["station"], "cm": r["value_cm"]} for r in low),
                key=lambda x: (x["cm"] is None, x["cm"]))[:5],
        })

    out["coverage"] = {
        "stations_seen": len(rows),
        "stations_fresh": len(rows) - len(stale),
        "stations_stale_excluded": len(stale),
        "freshness_hours": FRESH_HOURS,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)

    print(f"  {out['coverage']['stations_fresh']} fresh gauges of "
          f"{len(rows)} ({len(stale)} stale, excluded)\n")
    print(f"  {'river':10}{'fresh':>7}{'classif':>9}{'low':>6}{'share':>8}  verdict")
    for r in out["rivers"]:
        sh = "n/a" if r["share_low_of_classified"] is None else f"{r['share_low_of_classified']:.0%}"
        print(f"  {r['river']:10}{r['gauges_fresh']:7d}{r['gauges_classified']:9d}"
              f"{r['low']:6d}{sh:>8}  {r['verdict']}")
    print(f"\n  wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
