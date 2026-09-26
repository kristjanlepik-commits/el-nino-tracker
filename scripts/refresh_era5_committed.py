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
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetchers import era5_wwe, era5_burst          # noqa: E402
import json                                          # noqa: E402
from fetchers._common import (safe_fetch, write_committed,   # noqa: E402
                              committed_path, COMMITTED_DIR)


def _live(source, fn, budget_s, required):
    """Force the live path via TLS_ERA5_FORCE_LIVE, which both fetchers read.

    This used to monkeypatch fetchers._common.committed_result. That never
    worked: both fetcher modules bind the function by name at import, so
    the patch was invisible to them and the refresher silently no-opped
    whenever the committed file was fresh. See _force_live's docstring.
    """
    os.environ["TLS_ERA5_FORCE_LIVE"] = "1"
    try:
        return safe_fetch(source, fn, timeout_seconds=budget_s,
                          required_keys=required)
    finally:
        os.environ.pop("TLS_ERA5_FORCE_LIVE", None)


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
        before = committed_path(source)
        prev_fetched = None
        if before.exists():
            try:
                prev_fetched = json.loads(before.read_text()).get("fetched_at")
            except Exception:
                pass
        path = write_committed(source, r)
        rel = path.relative_to(ROOT)
        # A refresh that did not actually fetch is the failure this script
        # had for six days while printing "wrote". fetched_at moving is the
        # proof that a live pull happened; issued may legitimately repeat
        # when ERA5 has not published a new day yet.
        if prev_fetched and r.fetched_at == prev_fetched:
            failures.append(f"{source}: fetched_at did not move ({prev_fetched}); "
                            f"no live pull happened")
            print(f"  {source}: NO LIVE PULL, fetched_at unchanged {prev_fetched}")
            continue
        print(f"  {source}: wrote {rel}  issued {r.issued}  "
              f"fetched_at {r.fetched_at}  ({path.stat().st_size // 1024} KB)")
    if failures:
        sys.exit("REFRESH INCOMPLETE:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    main()
