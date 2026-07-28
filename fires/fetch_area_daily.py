"""One entry point for the nightly burnt-area pull.

Runs the three Copernicus fetchers in dependency order. This is a
FETCHER: it writes into fires/data/, so it must run as its own
workflow step BEFORE publish_all and its output must be committed
before publishing. Never call it from inside a publish path or it
will trip the guard that exists to catch exactly that.

Cadence note. EFFIS and GWIS publish weekly with roughly six days of
lag, so a daily run mostly re-fetches identical data. That is fine and
deliberate: the whole pull is about 130 requests and two minutes, and
running daily means the site picks the new week up within a day of it
appearing rather than up to seven days later. The alternative, gating
on a changed mddate, saves two minutes a day and adds a failure mode
where a stalled feed looks like a healthy skip.

Exit codes:
  0  all three succeeded
  1  a fetcher failed; the previous data on disk is untouched and
     still valid, just older, so the caller should warn rather than
     fail the build
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("current burnt area, 45 countries", "fetch_burnt_area.py"),
    ("weekly history, current year refreshed", "fetch_area_history.py"),
    ("world and regional aggregates", "fetch_area_regions.py"),
]


def main():
    failed = []
    for label, script in STEPS:
        print(f"\n=== {label} ({script})", flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, script)])
        if r.returncode != 0:
            failed.append(script)
            print(f"    FAILED rc={r.returncode}", flush=True)
    if failed:
        print(f"\nfailed: {', '.join(failed)}. Existing data on disk is "
              f"unchanged and still valid, only older.", file=sys.stderr)
        return 1
    print("\nAREADAILYDONE all three fetchers succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
