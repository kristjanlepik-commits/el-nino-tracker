"""Paired product comparison over one region box.

Three flood products cover overlapping periods and are not
interchangeable. This pulls any of them for the same region and dates
so the differences can be measured rather than assumed:

    mcdwd_l3       MODIS, science quality, LAADS, 2000-2025
    mcdwd_l3_nrt   MODIS, near real time,   LAADS, 2025 to present
    vcdwd_l3_nrt   VIIRS, near real time,   LANCE, last ~7 days only

Two questions this exists to answer, in priority order.

1. Does the near-real-time MODIS product agree with the science-quality
   archive? This is the more fundamental one. Baselines are built from
   the archive and current weeks arrive as near real time, so if the two
   disagree materially then every published comparison is measuring the
   product change rather than the weather. LAADS holds both for 2025,
   which makes this directly testable. Fire hit the same trap with
   FIRMS and its spec calls it out; the difference there was small but
   nonzero.

2. Does VIIRS agree with MODIS? Needed because MODIS switches off during
   the event. A first pass over late July 2026 was inconclusive: the
   ratio ran about 2.6x in Peru and about 0.3x in Somalia, on counts
   small enough to be dominated by shadow false positives rather than
   water. It has to be redone where there is real flooding.

Emits the same record shape as fetch_mcdwd_baseline.py, with a
`product` field, so the two can be analysed together.
"""

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

import numpy as np

TOKEN_PATH = os.path.expanduser("~/.earthdata_token")

PRODUCTS = {
    "mcdwd_l3": {
        "root": "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3",
        "format": "hdf4",
        "label": "MODIS science quality",
    },
    "mcdwd_l3_nrt": {
        "root": "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3_NRT",
        "format": "hdf4",
        "label": "MODIS near real time",
    },
    "vcdwd_l3_nrt": {
        "root": "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_NRT",
        "format": "hdf5",
        "label": "VIIRS near real time",
    },
}

TILE_DEG, TILE_PX = 10.0, 4800
PX_DEG = TILE_DEG / TILE_PX
H5_GROUP = ("HDFEOS", "GRIDS", "Flood_Composite", "Data Fields")
LAYERS = ("Flood_3Day_250m", "ValidCounts_3Day_250m", "WaterCounts_3Day_250m")

REGIONS = {
    "peru_ecuador_coast": {"lon": (-82.0, -75.0), "lat": (-12.0, 2.0)},
    "somalia_shabelle_juba": {"lon": (42.0, 46.5), "lat": (1.0, 6.5)},
    "kenya_tana": {"lon": (38.5, 40.5), "lat": (-2.5, 0.5)},
    "manila_luzon_west": {"lon": (119.5, 121.5), "lat": (13.5, 16.0)},
    # High-signal monsoon regions, for a comparison that is not dominated
    # by false positives. Counts here run orders of magnitude above the
    # dry-season boxes above.
    "ganges_brahmaputra": {"lon": (86.0, 92.0), "lat": (21.0, 26.5)},
    "mekong_lower": {"lon": (104.0, 107.0), "lat": (10.0, 13.5)},
}

_lock = threading.Lock()


def log(msg):
    with _lock:
        print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def token():
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TLS-floods/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["content"]


def box_slices(region):
    lon0, lon1 = sorted(region["lon"])
    lat0, lat1 = sorted(region["lat"])
    out = {}
    for h in range(int((lon0 + 180) // TILE_DEG), int((lon1 + 180) // TILE_DEG) + 1):
        for v in range(int((90 - lat1) // TILE_DEG), int((90 - lat0) // TILE_DEG) + 1):
            t_lon0, t_lat1 = -180.0 + TILE_DEG * h, 90.0 - TILE_DEG * v
            r0 = max(0, int((t_lat1 - min(lat1, t_lat1)) / PX_DEG))
            r1 = min(TILE_PX, int(np.ceil((t_lat1 - max(lat0, t_lat1 - TILE_DEG)) / PX_DEG)))
            c0 = max(0, int((max(lon0, t_lon0) - t_lon0) / PX_DEG))
            c1 = min(TILE_PX, int(np.ceil((min(lon1, t_lon0 + TILE_DEG) - t_lon0) / PX_DEG)))
            if r1 > r0 and c1 > c0:
                out[f"h{h:02d}v{v:02d}"] = (r0, r1, c0, c1)
    return out


def read_slice(payload, fmt, sl):
    r0, r1, c0, c1 = sl
    if fmt == "hdf4":
        from pyhdf.SD import SD, SDC

        fd, tmp = tempfile.mkstemp(suffix=".hdf")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
            hdf = SD(tmp, SDC.READ)
            out = {
                n: hdf.select(n).get(start=(r0, c0), count=(r1 - r0, c1 - c0)) for n in LAYERS
            }
            hdf.end()
            return out
        finally:
            os.unlink(tmp)
    import netCDF4

    ds = netCDF4.Dataset("inmem", mode="r", memory=payload)
    node = ds
    for part in H5_GROUP:
        node = node.groups[part]
    out = {n: np.array(node.variables[n][r0:r1, c0:c1]) for n in LAYERS}
    ds.close()
    return out


def tile_stats(root, fmt, year, doy, tile, sl, tok):
    try:
        listing = {
            f["name"].split(".")[2]: f["name"]
            for f in http_json(f"{root}/{year}/{doy:03d}.json")
            if len(f["name"].split(".")) > 2
        }
    except urllib.error.HTTPError as exc:
        return {"tile": tile, "status": f"listing_{exc.code}"}
    if tile not in listing:
        return {"tile": tile, "status": "absent"}
    url = f"{root}/{year}/{doy:03d}/{listing[tile]}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {tok}", "User-Agent": "TLS-floods/0.1"}
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = resp.read()
        arrays = read_slice(payload, fmt, sl)
    except Exception as exc:
        return {"tile": tile, "status": "error", "detail": repr(exc)[:120]}

    flood = arrays["Flood_3Day_250m"]
    valid = arrays["ValidCounts_3Day_250m"].astype(np.int16)
    water = arrays["WaterCounts_3Day_250m"].astype(np.int16)
    valid[valid == 255] = 0
    water[water == 255] = 0
    vals, counts = np.unique(flood, return_counts=True)
    return {
        "tile": tile,
        "status": "ok",
        "px": int(flood.size),
        "flood_hist": {int(v): int(c) for v, c in zip(vals, counts)},
        "observed_px": int((valid > 0).sum()),
        "water_ge3_px": int((water >= 3).sum()),
        "bytes": len(payload),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True, choices=sorted(REGIONS))
    ap.add_argument("--products", required=True, help="comma separated, from " + ",".join(PRODUCTS))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    slices = box_slices(REGIONS[args.region])
    products = [p.strip() for p in args.products.split(",")]
    d0 = dt.date.fromisoformat(args.start)
    d1 = dt.date.fromisoformat(args.end)

    here = os.path.dirname(os.path.abspath(__file__))
    out_path = args.out or os.path.join(
        here, "data", f"compare_{args.region}_{args.start}_{args.end}.jsonl"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    done.add((r["product"], r["date"]))
                except Exception:
                    pass

    log(f"{args.region}: tiles {sorted(slices)}  products {products}  {d0}..{d1}")
    tok = token()

    with open(out_path, "a") as out_fh:
        for product in products:
            spec = PRODUCTS[product]
            day = d0
            while day <= d1:
                if (product, day.isoformat()) in done:
                    day += dt.timedelta(days=1)
                    continue
                doy = day.timetuple().tm_yday
                with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                    results = list(
                        pool.map(
                            lambda kv: tile_stats(
                                spec["root"], spec["format"], day.year, doy, kv[0], kv[1], tok
                            ),
                            sorted(slices.items()),
                        )
                    )
                hist, px, obs, w3 = {}, 0, 0, 0
                for r in results:
                    if r["status"] != "ok":
                        continue
                    for k, v in r["flood_hist"].items():
                        hist[str(k)] = hist.get(str(k), 0) + v
                    px += r["px"]
                    obs += r["observed_px"]
                    w3 += r["water_ge3_px"]
                flood = int(hist.get("2", 0)) + int(hist.get("3", 0))
                rec = {
                    "product": product,
                    "product_label": spec["label"],
                    "region": args.region,
                    "date": day.isoformat(),
                    "box_px": px,
                    "flood_px": flood,
                    "flood_hist": hist,
                    "observed_px": obs,
                    "observed_frac": round(obs / px, 5) if px else None,
                    "water_ge3_px": w3,
                    "tiles": {r["tile"]: r["status"] for r in results},
                }
                out_fh.write(json.dumps(rec) + "\n")
                out_fh.flush()
                log(f"  {product:13s} {day}  flood {flood:8d}  obs {rec['observed_frac']}")
                day += dt.timedelta(days=1)

    log(f"done -> {out_path}")


if __name__ == "__main__":
    sys.exit(main())
