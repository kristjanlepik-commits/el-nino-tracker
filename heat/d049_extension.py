"""Extension test: is Phoenix singular, or the leading edge of a general signal?

Pre-registered in FEASIBILITY 5i-i on 2026-08-05 BEFORE running, with the city
list and both expected outcomes fixed first.

This is a SECOND TEST, not a revision. The original 11-city verdict is GREY and
is not reopened. Adding cities after seeing that one drives the result is a
forking path, and these being free makes it more tempting rather than more
legitimate. heat/d049_test.py is deliberately untouched.

Method identical to 1b-i: same ring, same estimator, same seasons, same D-067
thresholds, same power gate. Only the city list differs.

All 14 lie inside the already-pulled US box with 1.6 degrees of ring clearance,
so this costs no CDS.

Pre-registered expectation:
  general signal  -> added growth cities separate from added flat ones, and the
                     combined 25-city difference holds at or above +0.0251
  idiosyncratic   -> no separation among the added cities, combined difference
                     falls toward clean, Phoenix remains an outlier

Neither outcome overturns GREY. The second localises the problem to one city,
which is more useful operationally than a channel-wide verdict.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0 as g                                  # noqa: E402
import d049_test as base                           # noqa: E402
from gate0_power import ols_trend_se               # noqa: E402

ADDED = {
    "Austin":      {"lat": 30.27, "lon": -97.74,  "group": "growth", "region": "us"},
    "Atlanta":     {"lat": 33.75, "lon": -84.39,  "group": "growth", "region": "us"},
    "Charlotte":   {"lat": 35.23, "lon": -80.84,  "group": "growth", "region": "us"},
    "Nashville":   {"lat": 36.16, "lon": -86.78,  "group": "growth", "region": "us"},
    "Raleigh":     {"lat": 35.78, "lon": -78.64,  "group": "growth", "region": "us"},
    "Denver":      {"lat": 39.74, "lon": -104.99, "group": "growth", "region": "us"},
    "OklahomaCty": {"lat": 35.47, "lon": -97.52,  "group": "growth", "region": "us"},
    "Pittsburgh":  {"lat": 40.44, "lon": -79.996, "group": "flat",   "region": "us"},
    "StLouis":     {"lat": 38.63, "lon": -90.20,  "group": "flat",   "region": "us"},
    "Milwaukee":   {"lat": 43.04, "lon": -87.91,  "group": "flat",   "region": "us"},
    "Cincinnati":  {"lat": 39.10, "lon": -84.51,  "group": "flat",   "region": "us"},
    "Toledo":      {"lat": 41.65, "lon": -83.54,  "group": "flat",   "region": "us"},
    "Rochester":   {"lat": 43.16, "lon": -77.61,  "group": "flat",   "region": "us"},
    "Birmingham":  {"lat": 33.52, "lon": -86.80,  "group": "flat",   "region": "us"},
}

# Original powered results, transcribed from the committed run so the combined
# figure can be formed without re-running the pre-registered test.
ORIGINAL_ANNUAL = {
    "Madrid": ("growth", -0.0160), "Phoenix": ("growth", +0.0642),
    "Dallas": ("growth", +0.0072), "Houston": ("growth", +0.0047),
    "Leipzig": ("flat", +0.0038), "Liverpool": ("flat", -0.0343),
    "Buffalo": ("flat", -0.0115), "Cleveland": ("flat", -0.0067),
    "Detroit": ("flat", -0.0017),
}


def main() -> int:
    base.ALL_CITIES = ADDED                 # reuse the identical machinery
    series = base.build_series("us")

    for season in ("annual", "JJA"):
        print("=" * 78)
        print(f"EXTENSION, {season}.  14 added cities, method identical to 1b-i")
        print("=" * 78)
        print(f"{'city':13s} {'group':7s} {'OLS':>9s} {'SE':>7s} {'TheilSen':>9s} "
              f"{'power':>6s}  note")

        powered = {"growth": [], "flat": []}
        for name, c in ADDED.items():
            ys, vs = base.annual_means(series[name], season)
            if len(vs) < 20:
                print(f"{name:13s} {c['group']:7s}  insufficient years")
                continue
            ols, se, _ = ols_trend_se(ys, vs)
            ts = base.theil_sen(ys, vs)
            ratio = base.CONTAMINATED / se if se else float("inf")
            ok = ratio >= base.POWER_RATIO_MIN
            flag = "" if ok else "NO POWER"
            if np.sign(ols) != np.sign(ts) and abs(ols) > 1e-4:
                flag = (flag + " SIGN DISAGREE").strip()
            print(f"{name:13s} {c['group']:7s} {ols:+9.4f} {se:7.4f} {ts:+9.4f} "
                  f"{ratio:6.1f}  {flag}")
            if ok:
                powered[c["group"]].append(ols)

        gm = np.mean(powered["growth"]) if powered["growth"] else float("nan")
        fm = np.mean(powered["flat"]) if powered["flat"] else float("nan")
        print(f"\n  ADDED ONLY: growth {gm:+.4f} (n={len(powered['growth'])}), "
              f"flat {fm:+.4f} (n={len(powered['flat'])}), diff {gm - fm:+.4f}")

        if season == "annual":
            og = [v for grp, v in ORIGINAL_ANNUAL.values() if grp == "growth"]
            of = [v for grp, v in ORIGINAL_ANNUAL.values() if grp == "flat"]
            cg = np.mean(og + powered["growth"])
            cf = np.mean(of + powered["flat"])
            print(f"  COMBINED 25-city: growth {cg:+.4f}, flat {cf:+.4f}, "
                  f"diff {cg - cf:+.4f}")
            noph = [v for n, (grp, v) in ORIGINAL_ANNUAL.items()
                    if grp == "growth" and n != "Phoenix"]
            cg2 = np.mean(noph + powered["growth"])
            print(f"  COMBINED without Phoenix: growth {cg2:+.4f}, "
                  f"diff {cg2 - cf:+.4f}")
        print()

    print("Reading is per 5i-i. GREY is not reopened either way.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
