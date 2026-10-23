"""Reproduce the ERA5 atmospheric moisture record (Ben Noll / Washington Post,
October 2026) from the same source, before anything here repeats it.

Claim being checked: global total column water vapour, September 2026, was
+6.5% above the 1991-2020 September average, the highest September since
1940, and the most anomalous month on record; August 2026 also a record; and
about 10% of the planet set a moisture record.

Method: ERA5 monthly means, total_column_water_vapour, regridded by CDS to
1 degree (a global mean needs nothing finer), area-weighted by cos(latitude).
Anomaly in percent against the same calendar month's 1991-2020 mean.

Two record lengths are reported, never merged, per D-318: since 1940 (all of
ERA5) and since 1979 (the satellite era). Before 1979 ERA5 assimilated no
satellite humidity, so its moisture is largely the model's estimate; a record
against those years is weaker than one against 1979 onward.

Run:  .venv/bin/python floods/verify_moisture_record.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".era5_cache")
LAST_YEAR, LAST_MONTH = 2026, 9


def fetch():
    import cdsapi
    os.makedirs(CACHE, exist_ok=True)
    c = cdsapi.Client()
    for d0 in range(1940, LAST_YEAR + 1, 10):
        years = [str(y) for y in range(d0, min(d0 + 10, LAST_YEAR + 1))]
        f = os.path.join(CACHE, f"tcwv_{years[0]}_{years[-1]}.nc")
        if os.path.exists(f):
            continue
        months = [f"{m:02d}" for m in range(1, 13)]
        print(f"fetching {years[0]}-{years[-1]}", flush=True)
        c.retrieve("reanalysis-era5-single-levels-monthly-means", {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["total_column_water_vapour"],
            "year": years, "month": months, "time": ["00:00"],
            "grid": [1.0, 1.0], "data_format": "netcdf",
            "download_format": "unarchived"}, f)


def load():
    import netCDF4
    import datetime as dt
    fields, stamps, expver, lat = [], [], [], None
    for f in sorted(os.listdir(CACHE)):
        if not f.startswith("tcwv_"):
            continue
        d = netCDF4.Dataset(os.path.join(CACHE, f))
        a = np.array(d.variables["tcwv"][:])
        t = np.array(d.variables["valid_time"][:])
        ev = (np.array(d.variables["expver"][:]).astype(str) if "expver" in d.variables
              else np.array(["?"] * len(t)))
        lat = np.array(d.variables["latitude"][:])
        d.close()
        for k in range(len(t)):
            when = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(t[k]))
            stamps.append((when.year, when.month))
            fields.append(a[k])
            expver.append(str(ev[k]) if k < len(ev) else "?")
    order = np.argsort([y * 12 + m for y, m in stamps])
    return ([stamps[i] for i in order], np.stack([fields[i] for i in order]),
            [expver[i] for i in order], lat)


def main():
    fetch()
    stamps, F, expver, lat = load()
    w = np.cos(np.radians(lat))[:, None] * np.ones(F.shape[1:])
    gm = (F * w).sum(axis=(1, 2)) / w.sum()
    idx = {s: i for i, s in enumerate(stamps)}

    have = set(stamps)
    want = {(y, m) for y in range(1940, LAST_YEAR + 1) for m in range(1, 13)
            if (y, m) <= (LAST_YEAR, LAST_MONTH)}
    missing = sorted(want - have)
    if missing:
        print(f"INCOMPLETE: {len(missing)} months missing, first {missing[:4]}")

    clim = {m: np.mean([gm[idx[(y, m)]] for y in range(1991, 2021) if (y, m) in idx])
            for m in range(1, 13)}
    anom = np.array([100 * (gm[i] / clim[stamps[i][1]] - 1) for i in range(len(stamps))])

    def rank_of(y, m, since):
        same = [(yy, anom[idx[(yy, m)]]) for yy in range(since, LAST_YEAR + 1)
                if (yy, m) in idx]
        v = anom[idx[(y, m)]]
        return 1 + sum(1 for _, a in same if a > v), len(same)

    out = {"claim": "Ben Noll / Washington Post, Oct 2026", "source": "ERA5 monthly means, tcwv, 1 deg",
           "months": len(stamps), "missing_months": missing}
    print(f"\nERA5 global total column water vapour, {stamps[0]} to {stamps[-1]}, "
          f"{len(stamps)} months\n")
    for (y, m) in [(2026, 7), (2026, 8), (2026, 9)]:
        if (y, m) not in idx:
            continue
        r40, n40 = rank_of(y, m, 1940)
        r79, n79 = rank_of(y, m, 1979)
        a = anom[idx[(y, m)]]
        print(f"  {y}-{m:02d}: {gm[idx[(y, m)]]:.3f} kg/m2, {a:+.2f}% vs 1991-2020;  "
              f"rank {r40} of {n40} since 1940, {r79} of {n79} since 1979   [expver {expver[idx[(y, m)]]}]")
        out[f"{y}-{m:02d}"] = {"tcwv": float(gm[idx[(y, m)]]), "anom_pct": float(a),
                               "rank_since_1940": [r40, n40], "rank_since_1979": [r79, n79],
                               "expver": expver[idx[(y, m)]]}

    top = np.argsort(anom)[::-1][:5]
    print("\nmost anomalous months on record (any month, % vs its own 1991-2020 mean):")
    for i in top:
        print(f"  {stamps[i][0]}-{stamps[i][1]:02d}  {anom[i]:+.2f}%")
    out["most_anomalous"] = [[f"{stamps[i][0]}-{stamps[i][1]:02d}", float(anom[i])] for i in top]

    # share of the planet's area setting a September record, per cell
    for since in (1940, 1979):
        yrs = [y for y in range(since, LAST_YEAR + 1) if (y, 9) in idx]
        S = np.stack([F[idx[(y, 9)]] for y in yrs])
        rec = S[-1] > S[:-1].max(axis=0)
        frac = float((rec * w).sum() / w.sum())
        print(f"\nshare of Earth's area where Sept {yrs[-1]} is the moistest September since {since}: {frac:.1%}")
        out[f"area_share_record_since_{since}"] = frac

    json.dump(out, open(os.path.join(HERE, "data", "era5_moisture_record.json"), "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
