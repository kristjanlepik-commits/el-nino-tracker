"""Reproduce the ERA5 rainfall half of the September 2026 record
(Ben Noll / Washington Post): about 17% of the planet had September rainfall
in the top 10% of its historical values, a record share for September.

Method: ERA5 monthly means, total_precipitation, every September 1940-2026,
regridded by CDS to 1 degree. For each cell, the threshold is the 90th
percentile of its own Septembers over a baseline period. For each year, the
share of Earth's area above that threshold. The claim is that 2026's share is
the largest of any September.

Two baselines and two record lengths, reported separately, never merged:
1940-2025 (all of ERA5) and 1979-2025 (the satellite era). ERA5 rainfall is a
model forecast field, not assimilated directly, and before 1979 the model had
no satellite data at all, so the satellite-era version is the one to lean on.

Run:  .venv/bin/python floods/verify_rain_record.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".era5_cache")
F_NC = os.path.join(CACHE, "tp_september_1940_2026.nc")


def fetch():
    if os.path.exists(F_NC):
        return
    import cdsapi
    os.makedirs(CACHE, exist_ok=True)
    cdsapi.Client().retrieve("reanalysis-era5-single-levels-monthly-means", {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": ["total_precipitation"],
        "year": [str(y) for y in range(1940, 2027)], "month": ["09"],
        "time": ["00:00"], "grid": [1.0, 1.0],
        "data_format": "netcdf", "download_format": "unarchived"}, F_NC)


def main():
    fetch()
    import netCDF4
    import datetime as dt
    d = netCDF4.Dataset(F_NC)
    P = np.array(d.variables["tp"][:])
    t = np.array(d.variables["valid_time"][:])
    lat = np.array(d.variables["latitude"][:])
    d.close()
    years = [(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x))).year for x in t]
    order = np.argsort(years); years = [years[i] for i in order]; P = P[order]
    missing = sorted(set(range(1940, 2027)) - set(years))
    if missing:
        print(f"INCOMPLETE: Septembers missing {missing}")
    w = np.cos(np.radians(lat))[:, None] * np.ones(P.shape[1:])
    yi = {y: i for i, y in enumerate(years)}

    out = {"claim": "about 17% of the planet had Sept rainfall in its top 10%, a record share",
           "source": "ERA5 monthly means, total_precipitation, 1 deg", "septembers": len(years)}
    for b0 in (1940, 1979):
        base = [y for y in years if b0 <= y <= 2025]
        thr = np.percentile(np.stack([P[yi[y]] for y in base]), 90, axis=0)
        wet = thr > 0                          # a cell that never rains has no top 10%
        area = (w * wet).sum()
        share = {y: float((((P[yi[y]] > thr) & wet) * w).sum() / area)
                 for y in years if y >= b0}
        ranked = sorted(share.items(), key=lambda kv: -kv[1])
        r26 = 1 + sum(1 for y, s in share.items() if s > share[2026])
        print(f"\nbaseline {b0}-2025: Sept 2026 had {share[2026]:.1%} of the planet's (wet) area "
              f"above its own 90th percentile; rank {r26} of {len(share)}")
        print("  largest shares: " + ", ".join(f"{y} {s:.1%}" for y, s in ranked[:6]))
        out[f"baseline_{b0}"] = {"share_2026": share[2026], "rank_2026": [r26, len(share)],
                                 "share_by_year": {str(y): s for y, s in share.items()}}
    json.dump(out, open(os.path.join(HERE, "data", "era5_rain_record.json"), "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
