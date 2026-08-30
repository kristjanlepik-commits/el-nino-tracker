"""Rain-to-river routing dataset for the August 2026 east-Andes event.

Emits the three layers a routing figure needs, kept separate because they
come from different instruments and must not be merged (methodology 1.4):

  rain    GPM IMERG daily totals, observed, 0.1 degree
  river   Copernicus GloFAS daily discharge, MODELLED, 0.05 degree
  anchors named places where we already hold a multiple against the
          47-year record, carried over rather than recomputed

Design consumes this. Nothing here ranks a cell against history except
the anchors, which were ranked by the earlier per-cell sweep.
"""
import argparse
import datetime as dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_imerg_baseline as imerg

# One box spanning both the Peruvian clusters and the Bolivian yungas.
BOX = {"lat": (-17.2, -9.4), "lon": (-78.2, -65.8)}
RAIN_FLOOR_MM = 1.0   # below this a cell is not drawn; stated, not hidden


def daterange(a, b):
    d0 = dt.date.fromisoformat(a)
    d1 = dt.date.fromisoformat(b)
    out = []
    while d0 <= d1:
        out.append(d0.isoformat())
        d0 += dt.timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-08-15")
    ap.add_argument("--end", default="2026-08-22")
    ap.add_argument("--out", default="floods/data/routing_rain_2026-08.json")
    ap.add_argument("--product", default="GPM_3IMERGDL",
                    choices=["GPM_3IMERGDF", "GPM_3IMERGDL"])
    args = ap.parse_args()

    tok = imerg.token()
    days = daterange(args.start, args.end)
    imerg.log(f"rain layer: {len(days)} days, box {BOX}")

    lon0, lon1 = sorted(BOX["lon"])
    lat0, lat1 = sorted(BOX["lat"])
    i0, i1 = imerg.grid_index(lon0, 180.0), imerg.grid_index(lon1, 180.0)
    j0, j1 = imerg.grid_index(lat0, 90.0), imerg.grid_index(lat1, 90.0)
    lons = [(i + 0.5) * imerg.GRID_DEG - 180.0 for i in range(i0, i1 + 1)]
    lats = [(j + 0.5) * imerg.GRID_DEG - 90.0 for j in range(j0, j1 + 1)]
    imerg.log(f"grid {len(lons)} lon x {len(lats)} lat = {len(lons)*len(lats)} cells")

    grids, failed = {}, []
    for day in days:
        try:
            res = imerg.fetch_day(day, BOX, tok, short=args.product)
            if res is None:
                failed.append(day)
                imerg.log(f"  {day}  NO GRANULE")
                continue
            arr, nbytes = res
            grids[day] = arr
            imerg.log(f"  {day}  {arr.shape}  max {float(np.nanmax(arr)):6.1f} mm  {nbytes/1024:.0f} KB")
        except Exception as exc:
            failed.append(day)
            imerg.log(f"  {day}  FAILED {exc}")

    if failed:
        # A missing day is absence of data, not zero rain. Say so loudly.
        imerg.log(f"INCOMPLETE: {len(failed)} of {len(days)} days missing: {failed}")

    total = None
    for a in grids.values():
        total = a.copy() if total is None else total + a

    cells = []
    if total is not None:
        for ii in range(total.shape[0]):
            for jj in range(total.shape[1]):
                tot = float(total[ii, jj])
                if tot < RAIN_FLOOR_MM:
                    continue
                per_day = {d: round(float(grids[d][ii, jj]), 1) for d in grids}
                cells.append({
                    "lat": round(lats[jj], 2),
                    "lon": round(lons[ii], 2),
                    "total_mm": round(tot, 1),
                    "by_day": per_day,
                    "peak_day": max(per_day, key=per_day.get),
                    "peak_mm": round(max(per_day.values()), 1),
                })
    cells.sort(key=lambda c: -c["total_mm"])

    out = {
        "layer": "rain",
        "instrument": ("GPM IMERG %s Run v07, daily, 0.1 degree"
                       % ("Late" if args.product.endswith("DL") else "Final")),
        "product_short_name": args.product,
        "observed_or_modelled": "observed",
        "window": {"start": args.start, "end": args.end},
        "days_requested": days,
        "days_held": sorted(grids),
        "days_missing": failed,
        "complete": not failed,
        "box": {"lat": list(BOX["lat"]), "lon": list(BOX["lon"])},
        "grid_deg": imerg.GRID_DEG,
        "rain_floor_mm": RAIN_FLOOR_MM,
        "floor_note": (
            "Cells whose window total is below the floor are omitted from "
            "'cells'. They are not zero, they are below the drawing floor."
        ),
        "instrument_caveat": (
            "IMERG over-reads light rain and under-reads heavy rain on the "
            "same field on the same day. It is a daily total, so rain that "
            "falls in a few violent hours can flood without moving it."
        ),
        "cells_drawn": len(cells),
        "cells": cells,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    imerg.log(f"wrote {args.out}: {len(cells)} cells above {RAIN_FLOOR_MM} mm")
    if failed:
        imerg.log("EXIT 2 (incomplete)")
        sys.exit(2)


if __name__ == "__main__":
    main()
