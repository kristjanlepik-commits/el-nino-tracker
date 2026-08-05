"""Pull the two US coastal boxes product ruled for, satellite era only.

Covers the cities the first pull missed: New York, Boston, Philadelphia and
Miami on the east; Los Angeles, Seattle and San Francisco on the west. The
original US box spanned Phoenix to Detroit for the growth-versus-flat pairing
and never reached either coast.

Satellite era 1979-2026 rather than back to 1950, per product's ruling. A
reader-facing "this July against its own record" claim does not need the long
baseline, and staying inside one observing regime avoids the production
boundary that forced D-068.

NIGHT WINDOWS ARE PER BOX AND THIS IS NOT COSMETIC. The existing us box used
09:00-14:00 UTC as a compromise across 39 degrees of longitude. These boxes
are narrower, so each gets a window matched to its own solar time: the east
coast runs about UTC-5, the west about UTC-8, and a single window would put
one of them hours away from its true night minimum. This is the same error
caught in 1b-ii, where 00-05 UTC was night in Madrid and evening in Phoenix.

Same resumability as pull_night_minima.py: every chunk cached, completed
chunks skipped, atomic writes. Survives connection loss, which is the point
today; cdsapi retries to 500 at 120s intervals and the previous job finished
with zero failures through 1,667 connection errors.
"""
from __future__ import annotations

import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
DATASET = "reanalysis-era5-single-levels"

REGIONS = {
    # New York, Boston, Philadelphia, Miami. Local 03-08 -> UTC 08-13.
    "use": {
        "area": [44, -82, 24, -69],
        "hours": ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"],
    },
    # Los Angeles, Seattle, San Francisco. Local 03-08 -> UTC 11-16.
    "usw": {
        "area": [50, -125, 32, -114],
        "hours": ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00"],
    },
}

BLOCKS = [list(range(y, min(y + 10, 2027))) for y in range(1979, 2027, 10)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]

MAX_WORKERS = 4
_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def chunk_path(region: str, block: list[int], month: str) -> str:
    return os.path.join(CACHE, f"nightT_{region}_{block[0]}-{block[-1]}_{month}.nc")


def is_complete(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return False
    try:
        import xarray as xr
        with xr.open_dataset(path) as ds:
            return "t2m" in ds.variables and ds.sizes.get("valid_time", 0) > 0
    except Exception:
        return False


def fetch_chunk(region: str, block: list[int], month: str):
    path = chunk_path(region, block, month)
    if is_complete(path):
        return path, "cached"
    import cdsapi
    tmp = path + ".part"
    t0 = time.time()
    cdsapi.Client(quiet=True, progress=False).retrieve(
        DATASET,
        {
            "product_type": ["reanalysis"],
            "variable": ["2m_temperature"],
            "year": [str(y) for y in block],
            "month": [month],
            "day": ALL_DAYS,
            "time": REGIONS[region]["hours"],
            "data_format": "netcdf",
            "area": REGIONS[region]["area"],
        },
        tmp,
    )
    os.replace(tmp, path)
    return path, f"{time.time() - t0:.0f}s"


def main() -> int:
    os.makedirs(CACHE, exist_ok=True)
    jobs = [(r, b, m) for r in REGIONS for b in BLOCKS for m in MONTHS]
    todo = [j for j in jobs if not is_complete(chunk_path(*j))]
    log(f"{len(jobs)} chunks, {len(jobs)-len(todo)} cached, {len(todo)} to fetch, "
        f"{MAX_WORKERS} at a time")
    if not todo:
        log("nothing to do")
        return 0

    done = failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = {pool.submit(fetch_chunk, *j): j for j in todo}
        for f in as_completed(futs):
            r, b, m = futs[f]
            tag = f"{r} {b[0]}-{b[-1]} m{m}"
            try:
                _, how = f.result()
                done += 1
                log(f"OK   {tag} ({how})  [{done}/{len(todo)}, {failed} failed]")
            except Exception as e:
                failed += 1
                log(f"FAIL {tag}: {type(e).__name__}: {e}")

    log(f"finished: {done} fetched, {failed} failed. Re-run to retry failures.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
