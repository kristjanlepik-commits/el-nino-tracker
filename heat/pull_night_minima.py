"""Pull ERA5 night-hour 2m temperature for the D-049 urbanisation test.

Design and thresholds are pre-registered in heat/FEASIBILITY.md section 1
and were ratified as D-067 BEFORE any data was pulled. Do not change the
specification here; amend the document first, dated, with a reason.

Product choice, measured (FEASIBILITY 5b): the derived daily-statistics
product rejects 3-year requests on its cost cap, so it cannot carry a
77-year record. The raw product takes 10 years of one month at six night
hours in ~320s. Hence raw, chunked by (region, decade block, month).

Night windows are PER REGION and this matters: a single UTC window cannot
serve boxes 37 degrees of longitude apart. 00-05 UTC is night in Madrid
and evening in Phoenix. See FEASIBILITY 1b-ii.

Resumable by construction: every chunk is cached to disk and a completed
chunk is skipped, so a killed or crashed run resumes where it stopped
rather than restarting. Verified before running unattended, per CLAUDE.md.
"""
from __future__ import annotations

import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
DATASET = "reanalysis-era5-single-levels"

# N, W, S, E. Boxes cover every city in the frozen test set plus its ring.
REGIONS = {
    # Madrid, Munich, Leipzig, Liverpool, Naples
    "eu": {
        "area": [56, -7, 38, 17],
        "hours": ["02:00", "03:00", "04:00", "05:00", "06:00", "07:00"],
    },
    # Phoenix, Dallas-Fort Worth, Houston, Buffalo, Cleveland, Detroit
    "us": {
        "area": [45, -115, 28, -76],
        "hours": ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00"],
    },
}

# 1950-2026, in blocks of ten. Probe D confirmed ten years per request.
BLOCKS = [list(range(y, min(y + 10, 2027))) for y in range(1950, 2027, 10)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]

MAX_WORKERS = 4          # CDS queues per account; more is not faster and risks throttling
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def chunk_path(region: str, block: list[int], month: str) -> str:
    return os.path.join(CACHE, f"nightT_{region}_{block[0]}-{block[-1]}_{month}.nc")


def is_complete(path: str) -> bool:
    """A cached chunk counts as done only if it opens. A truncated file from a
    killed run must not be mistaken for a finished one."""
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return False
    try:
        import xarray as xr
        with xr.open_dataset(path) as ds:
            return "t2m" in ds.variables and ds.sizes.get("valid_time", 0) > 0
    except Exception:
        return False


def fetch_chunk(region: str, block: list[int], month: str) -> tuple[str, str]:
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
    os.replace(tmp, path)          # atomic: no half-written file is ever named as done
    return path, f"{time.time() - t0:.0f}s"


def main() -> int:
    os.makedirs(CACHE, exist_ok=True)
    jobs = [(r, b, m) for r in REGIONS for b in BLOCKS for m in MONTHS]
    todo = [j for j in jobs if not is_complete(chunk_path(*j))]
    log(f"{len(jobs)} chunks total, {len(jobs) - len(todo)} already cached, "
        f"{len(todo)} to fetch, {MAX_WORKERS} at a time")
    if not todo:
        log("nothing to do")
        return 0

    done = failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_chunk, *j): j for j in todo}
        for fut in as_completed(futures):
            region, block, month = futures[fut]
            tag = f"{region} {block[0]}-{block[-1]} m{month}"
            try:
                _, how = fut.result()
                done += 1
                log(f"OK   {tag} ({how})  [{done}/{len(todo)}, {failed} failed]")
            except Exception as e:
                failed += 1
                log(f"FAIL {tag}: {type(e).__name__}: {e}")

    log(f"finished: {done} fetched, {failed} failed. Re-run to retry failures.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
