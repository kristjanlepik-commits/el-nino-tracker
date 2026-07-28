"""Capture the MODIS/VIIRS near-real-time overlap before it rolls off.

Why this exists, and why it is urgent rather than merely useful.

MODIS is being switched off during the event we are here to cover: Aqua
stops science collection around August 2026, Terra around January 2027.
The 23-year MCDWD flood archive is a MODIS record, so every baseline
built on it becomes unusable the moment the instrument stops, unless
the VIIRS successor product can be reconciled against it. Reconciling
two instruments requires a period where both observed the same places
on the same days.

The problem is that the VIIRS flood product (VCDWD) has no archive
anywhere. Checked 2026-07-28:

  * LAADS holds MCDWD_L3 (2000-2025, science quality) and
    MCDWD_L3_NRT (2025 to present). Both MODIS.
  * LAADS archive set 5200 contains no VCDWD collection at all.
  * CMR indexes VCDWD_L3_NRT as "2025-04-15 to ongoing", but a granule
    query returns zero results for May 2025 and zero for March 2026.
    Only the last few days resolve.
  * The LANCE server itself holds roughly seven days.

So the successor instrument has a seven-day memory. Every day that
passes without capture is a day permanently absent from any future
VIIRS baseline, and the overlap window with MODIS is closing on its
own schedule regardless of ours.

NASA may yet archive VCDWD the way they archived MCDWD_L3_NRT and then
reprocessed the whole MODIS record in April 2026. That is a reasonable
expectation and a bad thing to depend on. Capturing costs a gigabyte a
run; not capturing cannot be undone.

This script pulls both products for the same tiles and days, computes
box statistics per candidate region, and keeps the raw tiles outside
the repo. It is deliberately not a channel fetcher and does not
publish anything.
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

import numpy as np

NRT = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData"
TOKEN_PATH = os.path.expanduser("~/.earthdata_token")

PRODUCTS = {
    "modis": {"set": 61, "name": "MCDWD_L3_NRT", "ext": ".hdf"},
    "viirs": {"set": 5200, "name": "VCDWD_L3_NRT", "ext": ".h5"},
}

TILE_DEG = 10.0
TILE_PX = 4800
PX_DEG = TILE_DEG / TILE_PX

LAYERS = ("Flood_3Day_250m", "ValidCounts_3Day_250m", "WaterCounts_3Day_250m")
H5_GROUP = ("HDFEOS", "GRIDS", "Flood_Composite", "Data Fields")

REGIONS = {
    "peru_ecuador_coast": {"lon": (-82.0, -75.0), "lat": (-12.0, 2.0)},
    "somalia_shabelle_juba": {"lon": (42.0, 46.5), "lat": (1.0, 6.5)},
    "kenya_tana": {"lon": (38.5, 40.5), "lat": (-2.5, 0.5)},
}


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def token():
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TLS-floods/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["content"]


def box_slices(region):
    """Per-tile pixel windows covering a region box."""
    lon0, lon1 = sorted(region["lon"])
    lat0, lat1 = sorted(region["lat"])
    out = {}
    for h in range(int((lon0 + 180) // TILE_DEG), int((lon1 + 180) // TILE_DEG) + 1):
        for v in range(int((90 - lat1) // TILE_DEG), int((90 - lat0) // TILE_DEG) + 1):
            t_lon0 = -180.0 + TILE_DEG * h
            t_lat1 = 90.0 - TILE_DEG * v
            r0 = max(0, int((t_lat1 - min(lat1, t_lat1)) / PX_DEG))
            r1 = min(TILE_PX, int(np.ceil((t_lat1 - max(lat0, t_lat1 - TILE_DEG)) / PX_DEG)))
            c0 = max(0, int((max(lon0, t_lon0) - t_lon0) / PX_DEG))
            c1 = min(TILE_PX, int(np.ceil((min(lon1, t_lon0 + TILE_DEG) - t_lon0) / PX_DEG)))
            if r1 > r0 and c1 > c0:
                out[f"h{h:02d}v{v:02d}"] = (r0, r1, c0, c1)
    return out


def read_layers(path, kind):
    """Return the three layers as arrays. HDF4 for MODIS, HDF5 for VIIRS."""
    if kind == "modis":
        from pyhdf.SD import SD, SDC

        hdf = SD(path, SDC.READ)
        arrays = {name: hdf.select(name).get() for name in LAYERS}
        hdf.end()
        return arrays
    import netCDF4

    ds = netCDF4.Dataset(path)
    node = ds
    for part in H5_GROUP:
        node = node.groups[part]
    arrays = {name: np.array(node.variables[name][:]) for name in LAYERS}
    ds.close()
    return arrays


def stats(arrays, sl):
    r0, r1, c0, c1 = sl
    flood = arrays["Flood_3Day_250m"][r0:r1, c0:c1]
    valid = arrays["ValidCounts_3Day_250m"][r0:r1, c0:c1].astype(np.int16)
    water = arrays["WaterCounts_3Day_250m"][r0:r1, c0:c1].astype(np.int16)
    valid[valid == 255] = 0
    water[water == 255] = 0
    vals, counts = np.unique(flood, return_counts=True)
    return {
        "px": int(flood.size),
        "flood_hist": {int(v): int(c) for v, c in zip(vals, counts)},
        "observed_px": int((valid > 0).sum()),
        "mean_valid_obs": round(float(valid.mean()), 4),
        "water_ge3_px": int((water >= 3).sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, help="where raw tiles are kept, outside the repo")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    os.makedirs(args.raw_dir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = args.out or os.path.join(here, "data", "nrt_overlap_capture.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    slices = {r: box_slices(REGIONS[r]) for r in REGIONS}
    tiles = sorted({t for s in slices.values() for t in s})
    log(f"tiles needed across {len(REGIONS)} regions: {tiles}")

    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    done.add((r["product"], r["doy"], r["tile"]))
                except Exception:
                    pass
        log(f"resuming, {len(done)} tile-records already captured")

    tok = token()
    grabbed = 0
    bytes_total = 0

    with open(out_path, "a") as out_fh:
        for kind, spec in PRODUCTS.items():
            root = f"{NRT}/{spec['set']}/{spec['name']}"
            years = [c["name"] for c in http_json(f"{root}.json") if c["name"].isdigit()]
            for year in years:
                # The NRT server advertises year directories that no longer
                # hold anything; the rolling window has already passed them
                # by. A 404 here is the normal case, not an error.
                try:
                    days = [c["name"] for c in http_json(f"{root}/{year}.json")]
                except urllib.error.HTTPError as exc:
                    log(f"{kind}: {year} empty ({exc.code}), rolled off")
                    continue
                if not days:
                    log(f"{kind}: {year} empty")
                    continue
                log(f"{kind}: {year} holds doy {days[0]}..{days[-1]} ({len(days)} days)")
                for doy in days:
                    listing = {
                        f["name"].split(".")[2]: f["name"]
                        for f in http_json(f"{root}/{year}/{doy}.json")
                        if len(f["name"].split(".")) > 2
                    }
                    for tile in tiles:
                        key = (kind, f"{year}{doy}", tile)
                        if key in done or tile not in listing:
                            continue
                        fname = listing[tile]
                        url = f"{root}/{year}/{doy}/{fname}"
                        local = os.path.join(args.raw_dir, fname)
                        try:
                            if not os.path.exists(local):
                                req = urllib.request.Request(
                                    url,
                                    headers={
                                        "Authorization": f"Bearer {tok}",
                                        "User-Agent": "TLS-floods/0.1",
                                    },
                                )
                                with urllib.request.urlopen(req, timeout=600) as resp:
                                    payload = resp.read()
                                with open(local, "wb") as fh:
                                    fh.write(payload)
                                bytes_total += len(payload)
                            arrays = read_layers(local, kind)
                        except Exception as exc:
                            log(f"  {kind} {year}{doy} {tile} FAILED {repr(exc)[:100]}")
                            continue
                        for region, sl_map in slices.items():
                            if tile not in sl_map:
                                continue
                            rec = {
                                "product": kind,
                                "collection": spec["name"],
                                "year": int(year),
                                "doy": f"{year}{doy}",
                                "date": (
                                    dt.date(int(year), 1, 1) + dt.timedelta(days=int(doy) - 1)
                                ).isoformat(),
                                "tile": tile,
                                "region": region,
                                "captured_at": dt.datetime.utcnow().isoformat() + "Z",
                                **stats(arrays, sl_map[tile]),
                            }
                            out_fh.write(json.dumps(rec) + "\n")
                        out_fh.flush()
                        grabbed += 1
                        log(f"  {kind} {year}{doy} {tile}  [{grabbed} tiles, {bytes_total/1e9:.2f} GB]")

    log(f"done. {grabbed} tiles captured, raw kept in {args.raw_dir}")


if __name__ == "__main__":
    sys.exit(main())
