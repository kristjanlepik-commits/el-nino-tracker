"""River layer of the rain-to-river routing dataset.

Copernicus GloFAS v4 (LISFLOOD) daily river discharge. This is a
HYDROLOGICAL MODEL, not an observation, and every consumer of this file
must label it so. It answers "did the modelled river rise, and when",
which is a different question from the rain layer's "where did water
fall". The two are never merged.
"""
import argparse
import datetime as dt
import json
import os
import sys

import numpy as np

BOX = {"lat": (-17.2, -9.4), "lon": (-78.2, -65.8)}
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
FLOW_FLOOR = 5.0  # m3/s; below this a cell is not a drawable river reach


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# GloFAS lives on the Early Warning Data Store, NOT on cds.climate.
# The key is shared with CDS; only the endpoint differs.
EWDS = "https://ewds.climate.copernicus.eu/api"


def _key():
    import re
    txt = open(os.path.expanduser("~/.cdsapirc")).read()
    return re.search(r"key:\s*(\S+)", txt).group(1)


def fetch(year, month, days, product, target):
    import cdsapi
    c = cdsapi.Client(url=EWDS, key=_key())
    n, w = BOX["lat"][1], BOX["lon"][0]
    s, e = BOX["lat"][0], BOX["lon"][1]
    c.retrieve(
        "cems-glofas-historical",
        {
            # system_version stays at 4.0: the anchors' 47-year multiples
            # were computed on v4, and a version crossing must be measured
            # before it is used, not assumed.
            "system_version": "version_4_0",
            "hydrological_model": "lisflood",
            "product_type": product,
            "timespan": "time_mean",
            "variable": "average_river_discharge_in_the_last_24_hours",
            "year": str(year),
            "month": f"{month:02d}",
            "day": [f"{d:02d}" for d in days],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [n, w, s, e],
        },
        target,
    )
    return target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--month", type=int, default=8)
    ap.add_argument("--day-start", type=int, default=12)
    ap.add_argument("--day-end", type=int, default=26)
    ap.add_argument("--product", default="intermediate",
                    choices=["intermediate", "consolidated"])
    ap.add_argument("--nc", default="/tmp/routing_glofas_2026-08.nc")
    ap.add_argument("--out", default="floods/data/routing_river_2026-08.json")
    args = ap.parse_args()

    days = list(range(args.day_start, args.day_end + 1))
    if not os.path.exists(args.nc):
        log(f"requesting GloFAS {args.product} {args.year}-{args.month:02d} "
            f"days {days[0]}..{days[-1]}, box {BOX}")
        fetch(args.year, args.month, days, args.product, args.nc)
    else:
        log(f"reusing cached {args.nc}")

    import netCDF4
    ds = netCDF4.Dataset(args.nc)
    dis = np.array(ds.variables["avg_dis"][:])
    lats = np.array(ds.variables["latitude"][:])
    lons = np.array(ds.variables["longitude"][:])
    # GloFAS returns longitude on 0..360. Everything else in this channel,
    # the rain layer included, is on -180..180. Convert here so the two
    # layers can be drawn on one map without the consumer discovering this.
    lons = np.where(lons > 180.0, lons - 360.0, lons)
    tvar = ds.variables["valid_time"]
    times = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(t))
             for t in np.array(tvar[:])]
    ds.close()
    dates = [t.date().isoformat() for t in times]
    log(f"grid {dis.shape} (time, lat, lon); dates {dates[0]}..{dates[-1]}")

    requested = [f"{args.year}-{args.month:02d}-{d:02d}" for d in days]
    missing = sorted(set(requested) - set(dates))
    if missing:
        log(f"INCOMPLETE: {len(missing)} of {len(requested)} days missing: {missing}")

    # Cells with no river carry all-NaN columns; nanargmax raises on those,
    # so mask them out rather than letting one ocean cell kill the run.
    valid = np.isfinite(dis).any(axis=0)
    safe = np.where(np.isfinite(dis), dis, -np.inf)
    peak = np.where(valid, safe.max(axis=0), np.nan)
    peak_idx = safe.argmax(axis=0)
    first = dis[0]

    cells = []
    for j in range(dis.shape[1]):
        for i in range(dis.shape[2]):
            pk = float(peak[j, i])
            if not np.isfinite(pk) or pk < FLOW_FLOOR:
                continue
            base = float(first[j, i])
            cells.append({
                "lat": round(float(lats[j]), 3),
                "lon": round(float(lons[i]), 3),
                "peak_m3s": round(pk, 1),
                "peak_date": dates[int(peak_idx[j, i])],
                "first_day_m3s": round(base, 1),
                "rise_x_first_day": round(pk / base, 1) if base > 0 else None,
                "series": [round(float(v), 1) for v in dis[:, j, i]],
            })
    cells.sort(key=lambda c: -c["peak_m3s"])

    out = {
        "layer": "river",
        "instrument": "Copernicus GloFAS v4.0, LISFLOOD, river discharge in the last 24 hours, 0.05 degree",
        "observed_or_modelled": "MODELLED, not observed",
        "product_type": args.product,
        "window": {"start": requested[0], "end": requested[-1]},
        "days_requested": requested,
        "days_held": dates,
        "days_missing": missing,
        "complete": not missing,
        "box": {"lat": list(BOX["lat"]), "lon": list(BOX["lon"])},
        "grid_deg": 0.05,
        "flow_floor_m3s": FLOW_FLOOR,
        "floor_note": (
            "Cells whose peak flow is below the floor are omitted. They are "
            "not dry, they are below the drawable-reach floor."
        ),
        "rise_note": (
            "rise_x_first_day compares each cell against ITS OWN first day of "
            "this window. It is a within-window rise, NOT a multiple against "
            "the historical record. Only the anchors carry a record multiple."
        ),
        "series_dates": dates,
        "cells_drawn": len(cells),
        "cells": cells,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    log(f"wrote {args.out}: {len(cells)} reaches above {FLOW_FLOOR} m3/s")
    if missing:
        log("EXIT 2 (incomplete)")
        sys.exit(2)


if __name__ == "__main__":
    main()
