"""The D-049 urbanisation test: growth cities against flat or shrinking ones.

This is the test the channel was gated on. Thresholds were ratified as D-067
on 2026-08-03, before any data existed, and have never moved:

    contaminated   growth-minus-flat mean dtrend  >  0.03 C/decade
    clean                                         <  0.01
    grey           between, publishes carrying the measured contamination
                   as a field on the datum per D-051

Specification frozen in FEASIBILITY 1b-i, amended once (1b-ii, six-hour night
window, for cost, before any data existed) and with one ambiguity resolved
(great-circle ring, 2026-08-04, before the analysis ran).

Reported PER CITY as well as per group, because gate 0's second design showed
the test only speaks where it has power: Munich and Naples cannot resolve the
threshold, so a flat result there means a blunt instrument rather than a clean
city (5h-ii).

Both seasons are computed and both are reported, fixed in advance so neither
can be chosen after the fact. Theil-Sen runs alongside OLS as a pre-registered
robustness check; a sign disagreement is investigated, not resolved by
preference.

One limitation with a known direction, from 1b-i: the ring is not screened for
suburban growth, so if ring cells have themselves urbanised this test
UNDERSTATES contamination. The bias runs toward finding the channel clean.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import xarray as xr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0 as g                      # noqa: E402
from gate0_power import ols_trend_se   # noqa: E402

CONTAMINATED, CLEAN = 0.03, 0.01       # D-067, C per decade
POWER_RATIO_MIN = 2.0                  # gate 0 second design

ALL_CITIES = {
    "Madrid":    {"lat": 40.42, "lon": -3.70,   "group": "growth", "region": "eu"},
    "Munich":    {"lat": 48.14, "lon": 11.58,   "group": "growth", "region": "eu"},
    "Phoenix":   {"lat": 33.45, "lon": -112.07, "group": "growth", "region": "us"},
    "Dallas":    {"lat": 32.78, "lon": -96.80,  "group": "growth", "region": "us"},
    "Houston":   {"lat": 29.76, "lon": -95.37,  "group": "growth", "region": "us"},
    "Leipzig":   {"lat": 51.34, "lon": 12.37,   "group": "flat",   "region": "eu"},
    "Liverpool": {"lat": 53.41, "lon": -2.98,   "group": "flat",   "region": "eu"},
    "Naples":    {"lat": 40.85, "lon": 14.27,   "group": "flat",   "region": "eu"},
    "Buffalo":   {"lat": 42.89, "lon": -78.88,  "group": "flat",   "region": "us"},
    "Cleveland": {"lat": 41.50, "lon": -81.69,  "group": "flat",   "region": "us"},
    "Detroit":   {"lat": 42.33, "lon": -83.05,  "group": "flat",   "region": "us"},
}

JJA = {6, 7, 8}


def theil_sen(x, y):
    n = len(x)
    slopes = [(y[j] - y[i]) / (x[j] - x[i])
              for i in range(n) for j in range(i + 1, n) if x[j] != x[i]]
    return float(np.median(slopes)) * 10.0


def build_series(region: str):
    lsm = g.load_lsm(region)
    cities = {n: c for n, c in ALL_CITIES.items() if c["region"] == region}
    geom = {n: g.cell_masks(lsm, c["lat"], c["lon"])[:2] for n, c in cities.items()}
    out = {n: {} for n in geom}
    for f in sorted(glob.glob(os.path.join(g.CACHE, f"nightT_{region}_*.nc"))):
        with xr.open_dataset(f) as ds:
            dmin = g.daily_night_min(ds["t2m"]).load()
            dates, arr = dmin["date"].values, dmin.values
            for n, (ij, ring) in geom.items():
                city = arr[:, ij[0], ij[1]]
                rmean = arr[:, ring].mean(axis=1)
                for d, cv, rv in zip(dates, city, rmean):
                    out[n][d] = cv - rv
    return out


def annual_means(recs, season):
    keep = (lambda d: True) if season == "annual" else (lambda d: d.month in JJA)
    years = sorted({d.year for d in recs})
    rows = []
    for y in years:
        vals = [v for d, v in recs.items() if d.year == y and keep(d)]
        need = 200 if season == "annual" else 60
        if len(vals) >= need:
            rows.append((y, float(np.mean(vals))))
    return np.array([r[0] for r in rows], float), np.array([r[1] for r in rows], float)


def main() -> int:
    series = {}
    for region in ("eu", "us"):
        try:
            series.update(build_series(region))
        except SystemExit as e:
            print(f"skipping {region}: {e}")

    for season in ("annual", "JJA"):
        print("=" * 78)
        print(f"D-049 TEST, {season}.  contaminated >{CONTAMINATED}, clean <{CLEAN} C/decade")
        print("=" * 78)
        print(f"{'city':11s} {'group':7s} {'OLS':>9s} {'SE':>7s} {'TheilSen':>9s} "
              f"{'power':>6s}  note")

        per_group = {"growth": [], "flat": []}
        for name, c in ALL_CITIES.items():
            if name not in series:
                continue
            ys, vs = annual_means(series[name], season)
            if len(vs) < 20:
                print(f"{name:11s} {c['group']:7s}  insufficient years")
                continue
            ols, se, _ = ols_trend_se(ys, vs)
            ts = theil_sen(ys, vs)
            ratio = CONTAMINATED / se if se else float("inf")
            powered = ratio >= POWER_RATIO_MIN
            flag = "" if powered else "NO POWER"
            if np.sign(ols) != np.sign(ts) and abs(ols) > 1e-4:
                flag = (flag + " SIGN DISAGREE").strip()
            print(f"{name:11s} {c['group']:7s} {ols:+9.4f} {se:7.4f} {ts:+9.4f} "
                  f"{ratio:6.1f}  {flag}")
            if powered:
                per_group[c["group"]].append(ols)

        g_mean = np.mean(per_group["growth"]) if per_group["growth"] else float("nan")
        f_mean = np.mean(per_group["flat"]) if per_group["flat"] else float("nan")
        diff = g_mean - f_mean

        print(f"\n  growth mean {g_mean:+.4f}  (n={len(per_group['growth'])} powered)")
        print(f"  flat mean   {f_mean:+.4f}  (n={len(per_group['flat'])} powered)")
        print(f"  DIFFERENCE  {diff:+.4f} C/decade")

        if not np.isfinite(diff):
            verdict = "UNDETERMINED: too few powered cities"
        elif diff > CONTAMINATED:
            verdict = "CONTAMINATED: city-level level claims need explicit correction"
        elif diff < CLEAN:
            verdict = "CLEAN: the level claim stands"
        else:
            verdict = "GREY: publishes carrying the contamination as a D-051 field"
        print(f"  VERDICT ({season}): {verdict}")
        print("  Reminder: the unscreened ring biases this toward CLEAN (1b-i).\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
