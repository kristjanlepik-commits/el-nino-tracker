"""Testability screen: which cities can the D-049 method actually measure?

Product's first ask, 2026-08-05. Answers one question per city: is the
city-minus-ring trend resolved precisely enough for a contamination estimate
to mean anything, at the D-067 threshold of 0.03 C/decade?

DELIBERATELY REPORTS POWER ONLY, NEVER THE TREND VALUE.

Computing power requires computing a trend, but printing those trends would
put fourteen unregistered city results into circulation, and any later
hypothesis test on them would then be run by someone who had already seen the
answers. Power is a property of the instrument and the geography; the trend is
a result. Only the first is needed to answer "can this city be measured", so
only the first is emitted. If a city later needs a verdict, it gets its own
pre-registration.

Not a D-049 test and not a revision of one. The 11-city verdict is GREY and
is untouched by anything here.

Diagnostics are included per city so a failure is explicable rather than just
flagged: ring elevation offset and spread, and the sea fraction of the
annulus. Those are the two confounds gate 0 identified (5h).
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import xarray as xr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0 as g                                  # noqa: E402
from gate0_power import ols_trend_se               # noqa: E402

THRESHOLD = 0.03
POWER_MIN = 2.0

EU_FREE = {
    "London": (51.51, -0.13), "Paris": (48.86, 2.35), "Berlin": (52.52, 13.40),
    "Madrid": (40.42, -3.70), "Barcelona": (41.39, 2.17), "Rome": (41.90, 12.50),
    "Milan": (45.46, 9.19), "Amsterdam": (52.37, 4.90), "Brussels": (50.85, 4.35),
    "Hamburg": (53.55, 9.99), "Frankfurt": (50.11, 8.68), "Lyon": (45.76, 4.84),
    "Prague": (50.08, 14.44), "Marseille": (43.30, 5.37),
}
US_FREE = {
    "Chicago": (41.88, -87.63), "New Orleans": (29.95, -90.07),
    "Memphis": (35.15, -90.05), "Kansas City": (39.10, -94.58),
    "Indianapolis": (39.77, -86.16), "Columbus": (39.96, -82.999),
    "Jacksonville": (30.33, -81.66),
}


def diagnostics(region, lat, lon):
    lsm = g.load_lsm(region)
    o = xr.open_dataset(os.path.join(g.CACHE, f"orog_{region}.nc"))
    zv = "z" if "z" in o else list(o.data_vars)[0]
    elev = o[zv].squeeze(drop=True) / 9.80665
    ij, ring, dist = g.cell_masks(lsm, lat, lon)
    annulus = (dist >= g.RING_INNER_DEG) & (dist <= g.RING_OUTER_DEG)
    sea = 1.0 - ring.sum() / max(annulus.sum(), 1)
    ce = float(elev.values[ij[0], ij[1]])
    return {
        "cells": int(ring.sum()),
        "sea_frac": float(sea),
        "elev_offset": float(elev.values[ring].mean() - ce),
        "elev_sd": float(elev.values[ring].std()),
    }, (ij, ring)


def run(region, cities):
    geom = {n: diagnostics(region, la, lo) for n, (la, lo) in cities.items()}
    series = {n: {} for n in cities}
    for f in sorted(glob.glob(os.path.join(g.CACHE, f"nightT_{region}_*.nc"))):
        with xr.open_dataset(f) as ds:
            dmin = g.daily_night_min(ds["t2m"]).load()
            dates, arr = dmin["date"].values, dmin.values
            for n, (_, (ij, ring)) in geom.items():
                city = arr[:, ij[0], ij[1]]
                rmean = arr[:, ring].mean(axis=1)
                for d, cv, rv in zip(dates, city, rmean):
                    series[n][d] = cv - rv

    print(f"\n{'city':13s} {'SE':>7s} {'thr/SE':>7s} {'cells':>6s} {'sea':>5s} "
          f"{'dElev':>7s} {'sdElev':>7s}  verdict")
    print("-" * 78)
    rows = []
    for n in cities:
        diag, _ = geom[n]
        recs = series[n]
        years = sorted({d.year for d in recs})
        ann = [(y, np.mean([v for d, v in recs.items() if d.year == y]))
               for y in years]
        ys = np.array([a[0] for a in ann], float)
        vs = np.array([a[1] for a in ann], float)
        _, se, _ = ols_trend_se(ys, vs)          # trend value discarded on purpose
        ratio = THRESHOLD / se if se else float("inf")
        ok = ratio >= POWER_MIN
        why = ""
        if not ok:
            bits = []
            if diag["sea_frac"] > 0.35:
                bits.append(f"{diag['sea_frac']*100:.0f}% of ring is sea")
            if abs(diag["elev_offset"]) > 300 or diag["elev_sd"] > 400:
                bits.append("ring is a different thermal regime (terrain)")
            why = "; ".join(bits) or "noisy for reasons not explained by terrain or coast"
        rows.append((n, ok))
        print(f"{n:13s} {se:7.4f} {ratio:7.1f} {diag['cells']:6d} "
              f"{diag['sea_frac']:5.2f} {diag['elev_offset']:+7.0f} "
              f"{diag['elev_sd']:7.0f}  {'TESTABLE' if ok else 'NOT TESTABLE: ' + why}")
    return rows


def main() -> int:
    print("TESTABILITY SCREEN. Power only; no trend values are emitted.")
    print(f"testable if the trend SE resolves {THRESHOLD} C/decade at {POWER_MIN}x")
    allrows = []
    for region, cities in (("eu", EU_FREE), ("us", US_FREE)):
        print(f"\n=== {region.upper()} ===")
        allrows += run(region, cities)
    ok = [n for n, v in allrows if v]
    bad = [n for n, v in allrows if not v]
    print(f"\n{'='*78}\nTESTABLE ({len(ok)}): {', '.join(ok)}")
    print(f"NOT TESTABLE ({len(bad)}): {', '.join(bad) if bad else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
