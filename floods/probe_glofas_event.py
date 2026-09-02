"""Can GloFAS see a given flood event at all?

A null correlation is only evidence about the world if the instrument
could have seen the signal. This probe asks that question directly:
point it at a box and a window containing an event whose severity is
already known from outside our data, and read what the model does.

It reports, per cell, the peak discharge and the rise over the quiet
level before the event, which is the same shape measure the channel uses
elsewhere. A catastrophic flash flood that leaves no rise here is the
instrument failing to see it, not the flood failing to happen.
"""
import argparse
import datetime as dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_routing_river as grr

MONTHS = grr.MONTHS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--lat", required=True, help="south,north")
    ap.add_argument("--lon", required=True, help="west,east")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--month", type=int, required=True)
    ap.add_argument("--day-start", type=int, required=True)
    ap.add_argument("--day-end", type=int, required=True)
    ap.add_argument("--event-day", required=True, help="YYYY-MM-DD")
    ap.add_argument("--product", default="consolidated")
    ap.add_argument("--quiet-days", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    s, n = [float(v) for v in args.lat.split(",")]
    w, e = [float(v) for v in args.lon.split(",")]
    grr.BOX = {"lat": (s, n), "lon": (w, e)}

    days = list(range(args.day_start, args.day_end + 1))
    nc = f"/tmp/probe_{args.label}_{args.year}{args.month:02d}.nc"
    if not os.path.exists(nc):
        grr.log(f"{args.label}: requesting GloFAS {args.product} "
                f"{args.year}-{args.month:02d} days {days[0]}..{days[-1]}")
        grr.fetch(args.year, args.month, days, args.product, nc)
    else:
        grr.log(f"reusing {nc}")

    import netCDF4
    ds = netCDF4.Dataset(nc)
    dis = np.array(ds.variables["avg_dis"][:])
    lats = np.array(ds.variables["latitude"][:])
    lons = np.array(ds.variables["longitude"][:])
    lons = np.where(lons > 180.0, lons - 360.0, lons)
    times = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(t))
             for t in np.array(ds.variables["valid_time"][:])]
    ds.close()
    dates = [t.date().isoformat() for t in times]
    grr.log(f"grid {dis.shape}; dates {dates[0]}..{dates[-1]}")
    if args.event_day not in dates:
        grr.log(f"WARNING: event day {args.event_day} not in the returned dates")

    valid = np.isfinite(dis).any(axis=0)
    safe = np.where(np.isfinite(dis), dis, -np.inf)
    peak = np.where(valid, safe.max(axis=0), np.nan)
    peak_idx = safe.argmax(axis=0)
    quiet = np.where(valid, np.nanmin(dis[:args.quiet_days], axis=0), np.nan)

    rows = []
    for j in range(dis.shape[1]):
        for i in range(dis.shape[2]):
            pk = float(peak[j, i])
            q = float(quiet[j, i])
            if not np.isfinite(pk) or pk <= 0:
                continue
            rows.append({
                "lat": round(float(lats[j]), 3),
                "lon": round(float(lons[i]), 3),
                "peak_m3s": round(pk, 1),
                "peak_date": dates[int(peak_idx[j, i])],
                "quiet_m3s": round(q, 2),
                "rise": round(pk / q, 1) if q > 0 else None,
                "series": [round(float(v), 1) for v in dis[:, j, i]],
            })
    rows.sort(key=lambda r: -(r["rise"] or 0))

    on_day = [r for r in rows if r["peak_date"] == args.event_day]
    big = [r for r in rows if (r["rise"] or 0) >= 5]
    out = {
        "label": args.label,
        "question": "could GloFAS see this event",
        "instrument": "Copernicus GloFAS v4.0 LISFLOOD, MODELLED, 0.05 degree",
        "product_type": args.product,
        "box": {"lat": [s, n], "lon": [w, e]},
        "window": {"start": dates[0], "end": dates[-1]},
        "event_day": args.event_day,
        "river_cells": len(rows),
        "cells_peaking_on_event_day": len(on_day),
        "cells_rising_5x_or_more": len(big),
        "max_rise_in_box": rows[0]["rise"] if rows else None,
        "max_peak_m3s_in_box": max((r["peak_m3s"] for r in rows), default=None),
        "series_dates": dates,
        "top_20_by_rise": rows[:20],
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)

    grr.log(f"river cells in box: {len(rows)}")
    grr.log(f"cells peaking ON the event day: {len(on_day)}")
    grr.log(f"cells rising 5x or more: {len(big)}")
    grr.log(f"largest rise anywhere in the box: {out['max_rise_in_box']}")
    grr.log(f"largest peak anywhere in the box: {out['max_peak_m3s_in_box']} m3/s")
    print()
    print(f"{'lat':>8}{'lon':>9}{'quiet':>9}{'peak':>10}{'rise':>8}  peak day")
    for r in rows[:12]:
        print(f"{r['lat']:>8}{r['lon']:>9}{r['quiet_m3s']:>9}{r['peak_m3s']:>10}"
              f"{str(r['rise']):>8}  {r['peak_date']}")
    grr.log(f"wrote {args.out}")


if __name__ == "__main__":
    main()
