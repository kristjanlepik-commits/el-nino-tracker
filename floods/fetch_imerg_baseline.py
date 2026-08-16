"""Same-calendar-week IMERG rainfall baseline for one region box.

The second Phase 1 feasibility instrument for the Floods channel (FLO),
run against the same region and the same calendar window as
`fetch_mcdwd_baseline.py` so the two can be compared directly.

This measures RAINFALL, not flooding, and nothing built on it may be
labelled otherwise. It is here because it has properties MCDWD does not:
it starts in June 2000, it has no sensor discontinuity ahead of it, and
precipitation is not blocked by cloud, so the series cannot go quiet
exactly when the weather gets interesting.

Retrieval is via OPeNDAP server-side subsetting, which returns about
38 KB per region-day instead of the 34 MB global file. The full
subset array is saved alongside the summary statistics, so percentile
thresholds can be computed later without refetching anything.

Source: GPM IMERG Final Precipitation L3 1 day 0.1 degree V07
(GPM_3IMERGDF), NASA GES DISC. Final Run carries roughly a 3.5 month
latency, which is fine for baselines and not fine for current weeks;
the Early Run is the near-real-time counterpart and is a separate
question for Phase 2.
"""

import argparse
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
TOKEN_PATH = os.path.expanduser("~/.earthdata_token")

# IMERG grid: 3600 x 1800 cells at 0.1 degree, cell centres at .05
GRID_DEG = 0.1

REGIONS = {
    "peru_ecuador_coast": {"lon": (-82.0, -75.0), "lat": (-12.0, 2.0)},
    "somalia_shabelle_juba": {"lon": (42.0, 46.5), "lat": (1.0, 6.5)},
    "kenya_tana": {"lon": (38.5, 40.5), "lat": (-2.5, 0.5)},
    # Manila and the Pampanga basin draining into Manila Bay, plus the
    # Zambales/Bataan coast. The area Reuters reported flooded on
    # 2026-08-09 from monsoon rain enhanced by Typhoon Dolphin.
    "manila_luzon_west": {"lon": (119.5, 121.5), "lat": (13.5, 16.0)},
    # Eastern Pyrenees and the upper Segre, the Ebro's largest tributary.
    # Located from data rather than from a news report: an Iberia-wide
    # IMERG scan for 2026-08-01..14 put the fortnight maximum at 42.45N
    # 1.27E, with this catchment at 36.8 mm mean against 6.1 mm for
    # Iberia as a whole.
    #
    # CAVEAT ON THE BOX, and it is the reason ebro_basin is fetched
    # alongside it. This box was drawn AFTER seeing where the rain fell,
    # so it is selected on the outcome. Applying it to all 27 years
    # removes the bias within the comparison but NOT the bias in having
    # chosen this catchment because it was wet. The defensible claim is
    # therefore "this catchment against its own history", never "the
    # wettest place in Spain", which would need every catchment screened
    # on equal terms.
    "catalonia_pyrenees": {"lon": (0.3, 2.2), "lat": (41.9, 42.9)},
    # Drawn in the screen candidate list BEFORE this event, so its
    # selection is independent of the outcome. The honest control.
    "ebro_basin": {"lon": (-2.0, 1.0), "lat": (41.0, 43.0)},
}


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def token():
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def grid_index(value, offset):
    """Cell index for a degree value, given the grid origin offset."""
    return int(round((value + offset) / GRID_DEG - 0.5))


def opendap_url(day, short="GPM_3IMERGDF"):
    """Resolve the OPeNDAP endpoint for one day via CMR."""
    params = {
        "short_name": short,
        "version": "07",
        "temporal": f"{day}T00:00:00Z,{day}T23:59:59Z",
        "page_size": "1",
    }
    url = f"{CMR}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "TLS-floods/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        entries = json.load(resp)["feed"]["entry"]
    if not entries:
        return None
    for link in entries[0].get("links", []):
        href = link.get("href", "")
        if "opendap" in href and href.endswith(".nc4"):
            return href
    return None


def fetch_day(day, box, tok, tries=3, short="GPM_3IMERGDF"):
    lon0, lon1 = sorted(box["lon"])
    lat0, lat1 = sorted(box["lat"])
    i0, i1 = grid_index(lon0, 180.0), grid_index(lon1, 180.0)
    j0, j1 = grid_index(lat0, 90.0), grid_index(lat1, 90.0)

    base = opendap_url(day, short)
    if base is None:
        return None
    ce = (
        f"/precipitation[0][{i0}:{i1}][{j0}:{j1}];"
        f"/lat[{j0}:{j1}];/lon[{i0}:{i1}]"
    )
    url = f"{base}.dap.nc4?dap4.ce={urllib.parse.quote(ce, safe='')}"

    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {tok}",
                    "User-Agent": "TLS-floods/0.1",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = resp.read()
            import netCDF4

            ds = netCDF4.Dataset("inmem", mode="r", memory=payload)
            arr = np.array(ds.variables["precipitation"][:]).squeeze()
            ds.close()
            return arr, len(payload)
        except Exception as exc:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="peru_ecuador_coast")
    ap.add_argument("--start", default="03-24")
    ap.add_argument("--end", default="03-30")
    ap.add_argument("--years", default="2000-2025")
    ap.add_argument("--out", default=None)
    # Final Run is science quality and about ten months behind; Late Run
    # is one to two days behind. A fast-reaction answer needs Late, and
    # the WHOLE comparison must then use Late, because mixing the two
    # products across a baseline measures the product change rather than
    # the weather. Late reaches back to 2000, so this costs nothing.
    ap.add_argument("--product", default="GPM_3IMERGDF",
                    choices=["GPM_3IMERGDF", "GPM_3IMERGDL"])
    args = ap.parse_args()

    box = REGIONS[args.region]
    y0, y1 = (int(x) for x in args.years.split("-"))
    m0, d0 = (int(x) for x in args.start.split("-"))
    m1, d1 = (int(x) for x in args.end.split("-"))

    here = os.path.dirname(os.path.abspath(__file__))
    tag = "late" if args.product.endswith("DL") else "final"
    stem = f"imerg_baseline_{args.region}_{args.start}_{args.end}_{tag}"
    out_path = args.out or os.path.join(here, "data", f"{stem}.jsonl")
    grid_path = os.path.join(os.path.dirname(out_path), f"{stem}_grids.npz")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    done = set()
    grids = {}
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["date"])
                except Exception:
                    pass
    if os.path.exists(grid_path):
        grids = dict(np.load(grid_path))

    days = []
    for year in range(y0, y1 + 1):
        day = dt.date(year, m0, d0)
        last = dt.date(year, m1, d1)
        while day <= last:
            if day.isoformat() not in done:
                days.append(day)
            day += dt.timedelta(days=1)

    log(f"{args.region} {args.start}..{args.end}, {len(days)} days to fetch")
    tok = token()
    total_bytes = 0

    with open(out_path, "a") as fh:
        for day in days:
            iso = day.isoformat()
            try:
                got = fetch_day(iso, box, tok, short=args.product)
            except Exception as exc:
                log(f"{iso}  FAILED {repr(exc)[:120]}")
                continue
            if got is None:
                log(f"{iso}  no granule")
                continue
            arr, nbytes = got
            total_bytes += nbytes
            grids[iso] = arr.astype(np.float32)
            rec = {
                "date": iso,
                "year": day.year,
                "region": args.region,
                "source": args.product + ".07",
                "cells": int(arr.size),
                "mean_mm": round(float(arr.mean()), 4),
                "max_mm": round(float(arr.max()), 3),
                "p95_mm": round(float(np.percentile(arr, 95)), 3),
                "frac_over_20mm": round(float((arr > 20).mean()), 5),
                "frac_over_50mm": round(float((arr > 50).mean()), 5),
                "frac_over_100mm": round(float((arr > 100).mean()), 5),
            }
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            log(f"{iso}  mean {rec['mean_mm']:7.3f}  max {rec['max_mm']:7.2f}  "
                f">20mm {rec['frac_over_20mm']:.3f}")

    np.savez_compressed(grid_path, **grids)
    log(f"done. {len(grids)} grids saved to {grid_path} ({total_bytes/1e6:.1f} MB fetched)")


if __name__ == "__main__":
    sys.exit(main())
