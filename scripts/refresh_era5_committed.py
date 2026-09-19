"""Pull ERA5 live and commit the compact result for the runner to read.

The writing half of D-300. The weekly brief runs on GitHub Actions with no
cache, so ERA5 comes off the runner: this script runs on a LOCAL machine
that has the ~50 MB climatology cache, does the live pull, and writes the
two compact results (about 47 KB and 9 KB) to data/era5/, which is
tracked. The fetchers on the runner read those files first and never
touch CDS.

Platform owns the schedule that runs this and commits the output. This
script does the pull and the write, prints one line per source saying what
it did, and exits non-zero if either source failed, so the schedule can
log a reason rather than a silence.

Run:   .venv/bin/python scripts/refresh_era5_committed.py
Then:  git commit data/era5/era5_wwe_last_good.json data/era5/era5_burst_last_good.json -m "..."
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetchers import era5_wwe, era5_burst          # noqa: E402
from fetchers._common import (safe_fetch, write_committed,   # noqa: E402
                              committed_path, COMMITTED_DIR)


def _live(source, fn, budget_s, required):
    """Bypass the committed-file short-circuit: we ARE the refresher."""
    import fetchers._common as c
    saved = c.committed_result
    c.committed_result = lambda *a, **k: None       # force the live path
    try:
        return safe_fetch(source, fn, timeout_seconds=budget_s,
                          required_keys=required)
    finally:
        c.committed_result = saved


def main():
    failures = []
    for source, fn, budget, req in (
        ("era5_wwe",   era5_wwe.fetch,   25 * 60, ("cwwa_ms_days", "cwwa_series")),
        ("era5_burst", era5_burst.fetch, 30 * 60, ("events_since_mar1",)),
    ):
        r = _live(source, fn, budget, req)
        if not r.ok or r.used_fallback:
            failures.append(f"{source}: ok={r.ok} used_fallback={r.used_fallback} "
                            f"error={r.error}")
            print(f"  {source}: NOT WRITTEN ({r.error})")
            continue
        path = write_committed(source, r)
        rel = path.relative_to(ROOT)
        print(f"  {source}: wrote {rel}  issued {r.issued}  "
              f"({path.stat().st_size // 1024} KB)")
    if failures:
        sys.exit("REFRESH INCOMPLETE:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    main()
