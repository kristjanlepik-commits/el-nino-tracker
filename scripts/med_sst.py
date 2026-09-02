"""Mediterranean sea surface temperature: every figure the autumn piece uses.

WHY THIS EXISTS. The piece was drafted from figures computed in a session
and quoted into a chat message. Editor refused to typeset one of them on
that basis, correctly: D-269 says a figure another chat sends you is a
cache and should be dated from their build. D-048 makes it worse than a
prose problem, because a number no other chat can reproduce should not be
published at all. This script is the build.

WHAT IT MEASURES. Basin-mean SST over 30-46N, 6W-36E, ERA5, sampled at
12:00 UTC every day of every year. The consistent sampling matters: an
earlier version compared a 12:00 daily mean against ERA5's monthly product
and quoted the difference as an anomaly, which is two bases in one number.

RECORD SCOPE. ERA5 now runs from 1940. Where the August record is
computed over the full period the script says so and the claim is an
86-year one; where the pull is unavailable it falls back to 1991 and
LABELS the window. Heat's `may_not_say` discipline applies: never
"warmest ever", always "warmest in <window>".

Run from the repo root:

    .venv/bin/python scripts/med_sst.py

Writes data/med_sst.json. First run downloads roughly 150 MB from CDS and
caches it; later runs are seconds.
"""

import glob
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "med_sst.json"
CACHE = Path(tempfile.gettempdir()) / "tls_med_sst"
BOX = [46, -6, 30, 36]          # N, W, S, E
CLIM = (1991, 2020)


def _fetch(name, years, months, days=None):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{name}.nc"
    if not p.exists():
        import cdsapi
        cdsapi.Client(quiet=True, progress=False).retrieve(
            "reanalysis-era5-single-levels",
            {"product_type": ["reanalysis"],
             "variable": ["sea_surface_temperature"],
             "year": [str(y) for y in years],
             "month": months,
             "day": days or [f"{d:02d}" for d in range(1, 32)],
             "time": ["12:00"],
             "data_format": "netcdf", "download_format": "unarchived",
             "area": BOX}, str(p))
    return p


def _series(p):
    """Basin-mean daily series from a netCDF or a zip of them."""
    import xarray as xr
    if zipfile.is_zipfile(p):
        d = str(p) + ".x"
        if not os.path.isdir(d):
            with zipfile.ZipFile(p) as z:
                z.extractall(d)
        members = sorted(glob.glob(os.path.join(d, "*.nc")))
        ds = xr.open_mfdataset(members, combine="by_coords") \
            if len(members) > 1 else xr.open_dataset(members[0])
    else:
        ds = xr.open_dataset(p)
    s = ds["sst"].mean(dim=["latitude", "longitude"], skipna=True) - 273.15
    out = {}
    for y, doy, v in zip(s.valid_time.dt.year.values,
                         s.valid_time.dt.dayofyear.values,
                         np.asarray(s.values)):
        if not np.isnan(v):
            out.setdefault(int(y), {})[int(doy)] = round(float(v), 3)
    return out


def main():
    track = _series(_fetch("sst_track", range(1991, 2027),
                           [f"{m:02d}" for m in range(1, 13)]))

    # August means. Extend to 1940 when the pull is available, so the record
    # claim carries its true window rather than the one that was convenient.
    aug = {y: float(np.mean([v for d, v in dd.items() if 213 <= d <= 243]))
           for y, dd in track.items()
           if len([d for d in dd if 213 <= d <= 243]) >= 25}
    early = CACHE / "sst_aug_1940_1990.nc"
    window_first = 1991
    if early.exists():
        for y, dd in _series(early).items():
            vals = [v for d, v in dd.items() if 213 <= d <= 243]
            if len(vals) >= 25:
                aug[y] = float(np.mean(vals))
        window_first = min(aug)

    order = sorted(aug.items(), key=lambda kv: -kv[1])
    clim = float(np.mean([aug[y] for y in range(*CLIM) if y in aug]))
    cur = aug[2026]
    latest_doy = max(track[2026])
    latest = track[2026][latest_doy]

    # Rank of 2026 on given calendar days, against every other year.
    marks = {}
    for d in (32, 91, 152, 182, latest_doy):
        if d not in track[2026]:
            continue
        others = [track[y][d] for y in track if y != 2026 and d in track[y]]
        c = track[2026][d]
        marks[d] = {
            "value": c,
            "rank": sorted(others + [c], reverse=True).index(c) + 1,
            "of": len(others) + 1,
            "clim": round(float(np.mean(
                [track[y][d] for y in range(*CLIM) if d in track.get(y, {})])), 3),
        }
    peak_doy = max(marks, key=lambda d: marks[d]["value"] - marks[d]["clim"])

    payload = {
        "_generator": "scripts/med_sst.py",
        "_generated_from": "ERA5 reanalysis-era5-single-levels via CDS, cached",
        "region": "30-46N, 6W-36E, whole basin",
        "sampling": "daily at 12:00 UTC, identical every year",
        "record_window": {
            "first_year": window_first, "last_year": 2026,
            "n_years": len(aug),
            "means": (f"every record claim in this file is scoped to "
                      f"{window_first}-2026 and must be stated that way. "
                      f"ERA5 itself begins in 1940; saying 'the ERA5 record' "
                      f"while computing a shorter window overclaims by the "
                      f"difference. Never 'warmest ever'."),
        },
        "climatology": {"basis": f"{CLIM[0]}-{CLIM[1]} August mean",
                        "value": round(clim, 3)},
        "august": {
            "2026": round(cur, 3),
            "anomaly_vs_clim": round(cur - clim, 3),
            "rank": [y for y, _ in order].index(2026) + 1,
            "of": len(order),
            "runner_up": {"year": order[1][0], "value": round(order[1][1], 3),
                          "margin": round(cur - order[1][1], 3)},
            "top5": [{"year": y, "value": round(v, 3)} for y, v in order[:5]],
            "caution": ("the margin over second place is small. A different "
                        "SST product could reorder the top two. The anomaly "
                        "is the robust figure; the ranking is not."),
        },
        "latest": {"day_of_year": latest_doy, "value": latest},
        "track_marks": marks,
        "largest_anomaly_day": {
            "day_of_year": peak_doy,
            "anomaly": round(marks[peak_doy]["value"] - marks[peak_doy]["clim"], 3),
            "means": ("the day in 2026 when the sea was furthest above its "
                      "own normal, which is not the day it was warmest"),
        },
        "series_1991_2026": {str(y): dd for y, dd in sorted(track.items())},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  record window     {window_first}-2026  ({len(aug)} Augusts)")
    print(f"  August 2026       {cur:.2f} C   anomaly {cur-clim:+.2f}")
    print(f"  rank              {payload['august']['rank']} of {len(order)}"
          f"   margin over {order[1][0]}: {cur-order[1][1]:+.2f}")
    print(f"  latest            doy {latest_doy}, {latest:.2f} C")
    print()
    print("  2026 rank through the year:")
    for d in sorted(marks):
        m = marks[d]
        print(f"    doy {d:>3}   {m['value']:6.2f}   rank {m['rank']:>2} of {m['of']}"
              f"   anomaly {m['value']-m['clim']:+.2f}")


if __name__ == "__main__":
    main()
