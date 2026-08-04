"""Gate 0, second design: a power calculation on the trend.

The first design compared city cell to rural ring in LEVEL and was
confounded by geography. Measured: r = 0.806 against elevation, with a
regression slope of 11.0 C/km against a lapse rate near 6.5, the excess
carried by the two coastal cities. Elevation plus maritime moderation, and
no reason to think a third confound does not exist. See FEASIBILITY 5h.

What gate 0 was always for is POWER: could the D-049 trend test detect a
contamination large enough to matter? That is answerable without any of
those confounds, because a static geographic offset has no trend.

PASS if the standard error on the city-minus-ring trend is small enough to
resolve the D-067 contaminated threshold of 0.03 C/decade. Otherwise a flat
trend means the instrument is blunt, not that the channel is clean.

Does NOT compute the growth-versus-flat comparison. That waits for the US
half, per the pre-registration.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import xarray as xr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0 as g  # noqa: E402

CONTAMINATED_THRESHOLD = 0.03      # D-067, degrees C per decade


def ols_trend_se(years: np.ndarray, vals: np.ndarray):
    """Slope per decade and its standard error, with a lag-1 correction.

    Annual means of a temperature difference are close to independent, but
    not exactly, and an uncorrected SE would flatter the power estimate.
    """
    x = years - years.mean()
    slope = float((x * (vals - vals.mean())).sum() / (x ** 2).sum())
    resid = vals - (vals.mean() + slope * x)
    n = len(vals)
    se = float(np.sqrt((resid ** 2).sum() / (n - 2) / (x ** 2).sum()))

    r1 = float(np.corrcoef(resid[:-1], resid[1:])[0, 1]) if n > 3 else 0.0
    if -0.99 < r1 < 0.99 and r1 > 0:
        se *= np.sqrt((1 + r1) / (1 - r1))       # effective-sample-size inflation
    return slope * 10.0, se * 10.0, r1


def main() -> int:
    lsm = g.load_lsm("eu")
    files = sorted(glob.glob(os.path.join(g.CACHE, "nightT_eu_*.nc")))
    geom = {n: g.cell_masks(lsm, c["lat"], c["lon"])[:2]
            for n, c in g.CITIES.items() if c["region"] == "eu"}

    series = {n: {} for n in geom}
    for f in files:
        with xr.open_dataset(f) as ds:
            dmin = g.daily_night_min(ds["t2m"]).load()
            dates, arr = dmin["date"].values, dmin.values
            for name, (ij, ring) in geom.items():
                city = arr[:, ij[0], ij[1]]
                rmean = arr[:, ring].mean(axis=1)
                for d, cv, rv in zip(dates, city, rmean):
                    series[name][d] = cv - rv

    print("GATE 0 (second design): precision of the city-minus-ring TREND")
    print(f"pass if SE resolves the D-067 threshold of "
          f"{CONTAMINATED_THRESHOLD:.2f} C/decade\n")
    print(f"{'city':11s} {'group':7s} {'trend':>9s} {'SE':>7s} {'lag1':>6s} "
          f"{'thr/SE':>7s}  verdict")

    ok = True
    for name in geom:
        recs = series[name]
        years = sorted({d.year for d in recs})
        ann = [(y, np.mean([v for d, v in recs.items() if d.year == y]))
               for y in years]
        ann = [(y, v) for y, v in ann if np.isfinite(v)]
        ys = np.array([a[0] for a in ann], float)
        vs = np.array([a[1] for a in ann], float)
        trend, se, r1 = ols_trend_se(ys, vs)
        ratio = CONTAMINATED_THRESHOLD / se if se else float("inf")
        good = ratio >= 2.0
        ok &= good
        print(f"{name:11s} {g.CITIES[name]['group']:7s} {trend:+9.4f} {se:7.4f} "
              f"{r1:+6.2f} {ratio:7.1f}  {'resolves' if good else 'TOO BLUNT'}")

    print()
    if ok:
        print("GATE 0 PASSES. The trend is measured precisely enough that a")
        print("contamination at the D-067 threshold would be visible, so a flat")
        print("result will mean 'no contamination' rather than 'no power'.")
    else:
        print("GATE 0 FAILS. At least one city's trend cannot be resolved to the")
        print("threshold. A flat result would be uninformative for that city.")
    print("\nGrowth-versus-flat comparison NOT computed: awaits the US half.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
