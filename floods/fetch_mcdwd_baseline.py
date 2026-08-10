"""Same-calendar-week MCDWD flood baseline for one region box.

Phase 1 feasibility instrument for the Floods channel (FLO). Not a
channel fetcher yet; this exists to answer one question, which is
whether NASA's MODIS/VIIRS global flood product can support a
"this week versus the same week in past years" claim at Measured
under D-033.

Method. For each year in the archive, for each day of a fixed
calendar window, download the MCDWD_L3 tiles covering a region box,
slice each tile to the box, and accumulate a histogram of the flood
layer plus an observability count. Tiles are streamed and deleted;
nothing large is retained. The artifact is a JSONL file of a few
kilobytes.

Two deliberate choices, both from the product user guide (Slayback,
Rev A):

  * The 3-Day composite is used, not the 1-Day. The 1-Day requires a
    single water detection and the guide warns it is substantially
    contaminated by cloud-shadow false positives. The 3-Day requires
    three independent detections.

  * The full value histogram is stored rather than a single "flood
    pixels" number. Table 5 of the guide carries the pixel coding and
    is not yet transcribed here, so the legend is resolved after the
    pull rather than assumed during it. 255 is "insufficient data",
    which the guide states may be a false negative, so it is counted
    separately and never folded into "no flood".

Interpreter note: needs pyhdf, which is not in the repo .venv.
Platform owns dependency management, so this currently runs against a
scratch venv and pyhdf is a pending request to them.
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
from pyhdf.SD import SD, SDC

ARCHIVE = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3"
TOKEN_PATH = os.path.expanduser("~/.earthdata_token")

TILE_DEG = 10.0
TILE_PX = 4800
PX_DEG = TILE_DEG / TILE_PX

FLOOD_LAYER = "Flood_3Day_250m"
VALID_LAYER = "ValidCounts_3Day_250m"
WATER_LAYER = "WaterCounts_3Day_250m"

# Region boxes. Proposed from the data, not inherited from Fire.
# Coastal Peru and Ecuador is the canonical El Nino flood signature
# and 2017 is the reference event.
REGIONS = {
    "peru_ecuador_coast": {
        "lon": (-82.0, -75.0),
        "lat": (-12.0, 2.0),
        "note": "Coastal Peru and Ecuador, Piura to Guayaquil. Rainfall-driven "
                "coastal flooding. Reference event 2017 coastal El Nino.",
    },
    "somalia_shabelle_juba": {
        "lon": (42.0, 46.5),
        "lat": (1.0, 6.5),
        "note": "Juba and Shabelle basins, Somalia. Slow riverine flooding, "
                "a different mechanism to Peru. Reference event the Deyr "
                "floods of November 2023, Beledweyne.",
    },
    "manila_luzon_west": {
        "lon": (119.5, 121.5),
        "lat": (13.5, 16.0),
        "note": "Manila, the Pampanga basin draining into Manila Bay, and the "
                "Zambales coast. Added 2026-08-10 as the first fast-reaction "
                "test: Reuters reported monsoon flooding enhanced by Typhoon "
                "Dolphin on 2026-08-09. Two tiles, so a 23-year same-week "
                "baseline is 4.6 GB rather than the 13.9 GB a six-tile box costs.",
    },
    "parana_paraguay": {
        "lon": (-60.0, -57.0),
        "lat": (-34.0, -27.0),
        "note": "Lower Parana and Paraguay, Argentina and Paraguay. Aftereffects "
                "rank 2 for Sep-Mar 2026-27 and their best pure instrument match: "
                "very slow riverine flooding on very flat open terrain. El Nino "
                "wet over southeastern South America is among the more robust "
                "South American teleconnections.",
    },
    "rio_grande_do_sul": {
        "lon": (-56.0, -50.0),
        "lat": (-32.0, -27.0),
        "note": "Rio Grande do Sul, southern Brazil. Aftereffects rank 4, harder "
                "than the Parana because catchments are steeper and onset faster. "
                "Strongest recent precedent on their list: May 2024, ~181 deaths "
                "and roughly USD 15bn (the loss figure is ECON's row, not ours).",
    },
    "kenya_tana": {
        "lon": (38.0, 40.8),
        "lat": (-3.0, 0.3),
        "note": "Tana river, Kenya, from around Garissa down to the delta. "
                "Riverine, same Deyr season as Somalia. ENLARGED 2026-08-10 "
                "from (38.5,40.5,-2.5,0.5): the original box failed the count "
                "floor at a median 157 flood pixels a week against a 300 "
                "minimum, while its observability dependence was a healthy "
                "+0.14. So it failed on SIZE, not on the instrument, unlike "
                "Manila. The enlargement is free: both boxes span the same "
                "four tiles, and the tile is the unit of cost, so the original "
                "was paying for four tiles and using a fifth of them.",
    },
}

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def token():
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def http_json(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TLS-floods/0.1"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as exc:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def tiles_for_box(lon_range, lat_range):
    """MODIS h/v tiles intersecting the box, with per-tile pixel slices."""
    lon0, lon1 = sorted(lon_range)
    lat0, lat1 = sorted(lat_range)
    out = []
    h_lo = int(np.floor((lon0 + 180.0) / TILE_DEG))
    h_hi = int(np.floor((lon1 + 180.0) / TILE_DEG))
    v_lo = int(np.floor((90.0 - lat1) / TILE_DEG))
    v_hi = int(np.floor((90.0 - lat0) / TILE_DEG))
    for h in range(h_lo, h_hi + 1):
        for v in range(v_lo, v_hi + 1):
            t_lon0 = -180.0 + TILE_DEG * h
            t_lat1 = 90.0 - TILE_DEG * v
            # Pixel indices within the tile, row 0 at the tile's north edge.
            r0 = int(np.floor((t_lat1 - min(lat1, t_lat1)) / PX_DEG))
            r1 = int(np.ceil((t_lat1 - max(lat0, t_lat1 - TILE_DEG)) / PX_DEG))
            c0 = int(np.floor((max(lon0, t_lon0) - t_lon0) / PX_DEG))
            c1 = int(np.ceil((min(lon1, t_lon0 + TILE_DEG) - t_lon0) / PX_DEG))
            r0, r1 = max(0, r0), min(TILE_PX, r1)
            c0, c1 = max(0, c0), min(TILE_PX, c1)
            if r1 > r0 and c1 > c0:
                out.append({"tile": f"h{h:02d}v{v:02d}", "slice": (r0, r1, c0, c1)})
    return out


_listing_cache = {}
_listing_lock = threading.Lock()


def listing(year, doy):
    key = (year, doy)
    with _listing_lock:
        if key in _listing_cache:
            return _listing_cache[key]
    data = http_json(f"{ARCHIVE}/{year}/{doy:03d}.json")["content"]
    index = {}
    for entry in data:
        parts = entry["name"].split(".")
        if len(parts) > 2:
            index[parts[2]] = entry["name"]
    with _listing_lock:
        _listing_cache[key] = index
    return index


def fetch_tile_stats(year, doy, tile, sl, tok):
    """Download one tile, slice to the box, return counts. Deletes the file."""
    # The listing call sat outside the try block, so a network drop that
    # outlived http_json's retries propagated out of the worker, killed
    # pool.map and ended the whole run. It happened twice on 2026-08-03
    # and 08-10, both times an intermittent DNS failure lasting seconds.
    # A day that cannot be listed is a skipped day, not a dead job: the
    # run is resumable and will pick it up next pass.
    try:
        names = listing(year, doy)
    except Exception as exc:
        return {"tile": tile, "status": "listing_failed", "detail": repr(exc)[:120]}
    fname = names.get(tile)
    if fname is None:
        return {"tile": tile, "status": "absent"}

    url = f"{ARCHIVE}/{year}/{doy:03d}/{fname}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {tok}", "User-Agent": "TLS-floods/0.1"}
    )
    tmp = None
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = resp.read()
        if payload[:4] != b"\x0e\x03\x13\x01":
            return {"tile": tile, "status": "not_hdf4", "bytes": len(payload)}
        fd, tmp = tempfile.mkstemp(suffix=".hdf")
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)

        hdf = SD(tmp, SDC.READ)
        r0, r1, c0, c1 = sl
        start, count = (r0, c0), (r1 - r0, c1 - c0)
        flood = hdf.select(FLOOD_LAYER).get(start=start, count=count)
        valid = hdf.select(VALID_LAYER).get(start=start, count=count)
        water = hdf.select(WATER_LAYER).get(start=start, count=count)
        hdf.end()

        vals, counts = np.unique(flood, return_counts=True)
        hist = {int(v): int(c) for v, c in zip(vals, counts)}
        valid_pos = valid.copy()
        valid_pos[valid_pos == 255] = 0
        water_pos = water.copy()
        water_pos[water_pos == 255] = 0
        return {
            "tile": tile,
            "status": "ok",
            "px": int(flood.size),
            "flood_hist": hist,
            "obs_px": int((valid_pos > 0).sum()),
            "obs_mean": round(float(valid_pos.mean()), 4),
            # Water counts are kept alongside the flood layer because the
            # flood layer depends on the stale MOD44W reference mask, while
            # water detections do not. If the mask turns out to poison the
            # comparison, this is the fallback signal and it costs nothing
            # to carry now; refetching 13 GB later would not be free.
            "water_ge1_px": int((water_pos >= 1).sum()),
            "water_ge3_px": int((water_pos >= 3).sum()),
            "bytes": len(payload),
        }
    except urllib.error.HTTPError as exc:
        return {"tile": tile, "status": f"http_{exc.code}"}
    except Exception as exc:
        return {"tile": tile, "status": "error", "detail": repr(exc)[:160]}
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="peru_ecuador_coast")
    ap.add_argument("--start", default="03-24", help="window start, MM-DD")
    ap.add_argument("--end", default="03-30", help="window end, MM-DD")
    ap.add_argument("--years", default="2003-2025")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    region = REGIONS[args.region]
    tiles = tiles_for_box(region["lon"], region["lat"])
    y0, y1 = (int(x) for x in args.years.split("-"))
    m0, d0 = (int(x) for x in args.start.split("-"))
    m1, d1 = (int(x) for x in args.end.split("-"))

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        f"mcdwd_baseline_{args.region}_{args.start}_{args.end}.jsonl",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    done.add((rec["year"], rec["doy"]))
                except Exception:
                    pass
        log(f"resuming, {len(done)} day-records already present")

    jobs = []
    for year in range(y0, y1 + 1):
        day = dt.date(year, m0, d0)
        last = dt.date(year, m1, d1)
        while day <= last:
            doy = day.timetuple().tm_yday
            if (year, doy) not in done:
                jobs.append((year, doy, day.isoformat()))
            day += dt.timedelta(days=1)

    log(f"region {args.region} box lon {region['lon']} lat {region['lat']}")
    log(f"tiles {[t['tile'] for t in tiles]}  window {args.start}..{args.end}")
    log(f"{len(jobs)} day-records to fetch, {len(jobs) * len(tiles)} tile pulls")

    tok = token()
    written = 0
    bytes_total = 0
    started = time.time()

    with open(out_path, "a") as out_fh:
        for year, doy, iso in jobs:
            with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                results = list(
                    pool.map(
                        lambda t: fetch_tile_stats(year, doy, t["tile"], t["slice"], tok),
                        tiles,
                    )
                )
            hist = {}
            px = obs_px = water1 = water3 = 0
            obs_weighted = 0.0
            for r in results:
                bytes_total += r.get("bytes", 0)
                if r["status"] != "ok":
                    continue
                for k, v in r["flood_hist"].items():
                    hist[str(k)] = hist.get(str(k), 0) + v
                px += r["px"]
                obs_px += r["obs_px"]
                obs_weighted += r["obs_mean"] * r["px"]
                water1 += r["water_ge1_px"]
                water3 += r["water_ge3_px"]
            if not any(r["status"] == "ok" for r in results):
                log(f"{iso}  no tiles retrieved, NOT writing a record "
                    f"({ {r['tile']: r['status'] for r in results} })")
                continue
            rec = {
                "year": year,
                "doy": doy,
                "date": iso,
                "region": args.region,
                "layer": FLOOD_LAYER,
                "box_px": px,
                "flood_hist": hist,
                "observed_px": obs_px,
                "observed_frac": round(obs_px / px, 5) if px else None,
                "mean_valid_obs": round(obs_weighted / px, 4) if px else None,
                "water_ge1_px": water1,
                "water_ge3_px": water3,
                "tiles": {r["tile"]: r["status"] for r in results},
            }
            out_fh.write(json.dumps(rec) + "\n")
            out_fh.flush()
            written += 1
            rate = bytes_total / 1e6 / max(time.time() - started, 1)
            log(
                f"{iso}  obs {rec['observed_frac']}  hist {hist}  "
                f"[{written}/{len(jobs)}  {bytes_total/1e9:.2f} GB  {rate:.1f} MB/s]"
            )

    log(f"done. {written} records to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
