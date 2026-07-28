"""Daily global capture of the VIIRS flood product, retained as aggregates.

The standing insurance policy against the MODIS shutdown, per Kristjan's
call on 2026-07-28.

The situation this answers. The 23-year MCDWD flood archive is a MODIS
record and MODIS is being switched off during the event: Aqua around
August 2026, Terra around January 2027. The VIIRS successor (VCDWD) is
the forward instrument, and it has no archive anywhere. LANCE holds
roughly seven days and then deletes. So the data needed to reconcile
the two instruments, and every future VIIRS baseline, exists only if
something writes it down as it goes past.

Why global rather than the regions we care about. We do not yet know
which regions we care about. Today's Peru result showed the measured
signal moving by a factor of four depending on where the box is drawn,
so region choice has to follow the baselines rather than precede them,
and a region-scoped capture would spend exactly the flexibility that
finding says we need. Global capture also covers regions that become
newsworthy later, which is the whole premise of T4.

Why aggregates rather than raw. Raw is 3.57 GB per global day, about
1.2 TB by January. Reduced to 0.1 degree cells, the same day is a few
megabytes, and 0.1 degree is finer than anything we would publish. The
trade accepted: sub-0.1-degree detail cannot be recovered later. Full
resolution stays available for the recent window and for any region we
choose to pull raw from the LANCE server while it is still there.

What a cell holds. Native pixels are 250m, so a 0.1 degree cell is a
48 by 48 block, 2304 pixels. Per cell we keep five counts:

    flood        Flood_3Day in {2, 3}, water outside the reference mask
    surfacewater Flood_3Day == 1, water inside the reference mask
    nodata       Flood_3Day == 255, "insufficient data", NOT dry
    observed     ValidCounts_3Day > 0, the observability denominator
    water3       WaterCounts_3Day >= 3, mask-independent water signal

The nodata and observed counts are not optional extras. An optical
flood product goes quiet exactly when the weather gets interesting, and
without a denominator a cloudy week is indistinguishable from a dry
one. Carrying both is what lets this support a Measured claim rather
than an impressionistic one.

Not a channel fetcher. Renders nothing, publishes nothing.
"""

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import numpy as np

NRT = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_NRT"
TOKEN_PATH = os.path.expanduser("~/.earthdata_token")

TILE_PX = 4800
CELL_PX = 48                      # 48 x 250m ~= 0.1 degree
CELLS = TILE_PX // CELL_PX        # 100 x 100 cells per 10 degree tile

H5_GROUP = ("HDFEOS", "GRIDS", "Flood_Composite", "Data Fields")
COUNTS = ("flood", "surfacewater", "nodata", "observed", "water3")

_lock = threading.Lock()



def log(msg):
    with _lock:
        print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def token():
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def http_json(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TLS-floods/0.1"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)["content"]
        except urllib.error.HTTPError:
            raise
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def block_count(mask):
    """Sum a boolean mask into 0.1 degree cells."""
    return (
        mask.reshape(CELLS, CELL_PX, CELLS, CELL_PX)
        .sum(axis=(1, 3))
        .astype(np.uint16)
    )


def reduce_tile(path):
    """Phase two. Runs only on the main thread, one file at a time."""
    import netCDF4

    ds = netCDF4.Dataset(path)
    node = ds
    for part in H5_GROUP:
        node = node.groups[part]
    flood = np.array(node.variables["Flood_3Day_250m"][:])
    valid = np.array(node.variables["ValidCounts_3Day_250m"][:])
    water = np.array(node.variables["WaterCounts_3Day_250m"][:])
    ds.close()
    return np.stack(
        [
            block_count((flood == 2) | (flood == 3)),
            block_count(flood == 1),
            block_count(flood == 255),
            block_count((valid > 0) & (valid != 255)),
            block_count((water >= 3) & (water != 255)),
        ]
    )


def capture_day(year, doy, out_dir, tok, workers):
    stamp = f"{year}{doy}"
    final = os.path.join(out_dir, f"vcdwd_0p1deg_{stamp}.npz")
    if os.path.exists(final):
        return None

    parts_dir = os.path.join(out_dir, f".parts_{stamp}")
    os.makedirs(parts_dir, exist_ok=True)

    entries = http_json(f"{NRT}/{year}/{doy}.json")
    tiles = {}
    for e in entries:
        bits = e["name"].split(".")
        if len(bits) > 2:
            tiles[bits[2]] = e["name"]

    todo = [t for t in sorted(tiles) if not os.path.exists(os.path.join(parts_dir, t + ".npy"))]
    log(f"{stamp}: {len(tiles)} tiles, {len(todo)} to fetch")

    # Downloads are handed to curl rather than a Python thread pool.
    #
    # This job hung three times tonight with three different symptoms,
    # and my diagnosis was wrong twice. First I blamed HDF5 thread
    # safety and serialised the parse behind a lock; it hung again in
    # ninety seconds. Then I separated download and parse into strict
    # phases so no thread touched HDF5; it hung a third time, with the
    # main thread waiting on the pool, all six workers parked idle, no
    # open sockets and no partial files. Work items were being lost
    # rather than blocked.
    #
    # At that point the honest move is to delete the moving part rather
    # than produce a fourth theory. curl does parallel downloads with a
    # decade of hardening behind it, and the failure mode of a
    # subprocess is an exit code rather than a silent hang.
    fetched_before = len([t for t in todo if os.path.exists(os.path.join(parts_dir, t + ".h5"))])
    want = [t for t in todo if not os.path.exists(os.path.join(parts_dir, t + ".h5"))]
    if want:
        cfg = os.path.join(parts_dir, "_curl.cfg")
        with open(cfg, "w") as fh:
            fh.write(f'header = "Authorization: Bearer {tok}"\n')
            fh.write('user-agent = "TLS-floods/0.1"\n')
            for tile in want:
                fh.write(f'url = "{NRT}/{year}/{doy}/{tiles[tile]}"\n')
                fh.write(f'output = "{os.path.join(parts_dir, tile + ".h5")}"\n')
        log(f"{stamp}: curl fetching {len(want)} tiles, {workers} at a time")
        rc = subprocess.call(
            ["curl", "-sS", "-L", "--fail", "-Z", "--parallel-max", str(workers),
             "--retry", "3", "--retry-delay", "3", "--connect-timeout", "60",
             "--max-time", "900", "-K", cfg]
        )
        os.unlink(cfg)
        log(f"{stamp}: curl exit {rc}")

    for tile in want:
        raw = os.path.join(parts_dir, tile + ".h5")
        if os.path.exists(raw):
            with open(raw, "rb") as fh:
                if fh.read(8) != b"\x89HDF\r\n\x1a\n":
                    log(f"  {stamp} {tile}: not HDF5, discarding")
                    os.unlink(raw)
    got = [
        fetched_before + len([t for t in want if os.path.exists(os.path.join(parts_dir, t + ".h5"))]),
        sum(
            os.path.getsize(os.path.join(parts_dir, t + ".h5"))
            for t in todo
            if os.path.exists(os.path.join(parts_dir, t + ".h5"))
        ),
    ]

    reduced = 0
    for tile in todo:
        raw = os.path.join(parts_dir, tile + ".h5")
        if not os.path.exists(raw):
            continue
        try:
            np.save(os.path.join(parts_dir, tile + ".npy"), reduce_tile(raw))
            reduced += 1
        except Exception as exc:
            log(f"  {stamp} {tile} REDUCE FAILED {repr(exc)[:90]}")
        finally:
            os.unlink(raw)
    log(f"{stamp}: reduced {reduced}/{len(todo)}, raw discarded")

    bundle = {}
    for tile in sorted(tiles):
        p = os.path.join(parts_dir, tile + ".npy")
        if os.path.exists(p):
            bundle[tile] = np.load(p)
    if not bundle:
        log(f"{stamp}: nothing captured, leaving parts in place")
        return None

    np.savez_compressed(final, **bundle)
    shutil.rmtree(parts_dir, ignore_errors=True)
    size = os.path.getsize(final)
    log(
        f"{stamp}: wrote {len(bundle)}/{len(tiles)} tiles -> {size/1e6:.1f} MB "
        f"(from {got[1]/1e9:.2f} GB downloaded, {got[1]/max(size,1):.0f}x reduction)"
    )
    return {
        "date": (dt.date(int(year), 1, 1) + dt.timedelta(days=int(doy) - 1)).isoformat(),
        "doy": stamp,
        "tiles_expected": len(tiles),
        "tiles_captured": len(bundle),
        "bytes_downloaded": got[1],
        "bytes_stored": size,
        "captured_at": dt.datetime.utcnow().isoformat() + "Z",
        "cell_deg": 0.1,
        "counts": list(COUNTS),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, help="where the daily npz files go")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = args.manifest or os.path.join(here, "data", "vcdwd_capture_manifest.jsonl")
    os.makedirs(os.path.dirname(manifest), exist_ok=True)

    tok = token()
    years = [c["name"] for c in http_json(f"{NRT}.json") if c["name"].isdigit()]

    # Oldest first on purpose. The rolling window deletes from the old
    # end, so the oldest day on the server is the one most likely to be
    # gone if this run is interrupted.
    with open(manifest, "a") as mf:
        for year in years:
            try:
                days = sorted(c["name"] for c in http_json(f"{NRT}/{year}.json"))
            except urllib.error.HTTPError as exc:
                log(f"{year}: empty ({exc.code})")
                continue
            for doy in days:
                try:
                    rec = capture_day(year, doy, args.out_dir, tok, args.workers)
                except Exception as exc:
                    log(f"{year}{doy}: FAILED {repr(exc)[:110]}")
                    continue
                if rec:
                    mf.write(json.dumps(rec) + "\n")
                    mf.flush()

    log("capture pass complete")


if __name__ == "__main__":
    sys.exit(main())
