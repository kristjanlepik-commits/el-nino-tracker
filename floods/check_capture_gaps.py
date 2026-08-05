"""Set-difference the capture store against the calendar.

A check on VALUES cannot detect a MISSING RECORD. Anything that scans
what is present is structurally unable to see what is absent: a total
cannot be low if there is no row to be low. The only fix is a
set-difference against the dates that should exist.

The Fire chat found this in their archive on 2026-08-03 (24 defective
days detected by a value check, 25 more invisible because those dates
were absent rather than small) and flagged that it is worse here,
because the VIIRS capture cannot be refetched: LANCE deletes after
about seven days, so a hole is permanent rather than a retry.

It was worse here. Running this the same day found 2026-07-22 absent
from the capture manifest while every other day from 07-21 to 08-03 was
present, and by then the day had already rolled off the server. The
manifest carried 43 records for 13 distinct dates, because each run
re-captures a rolling window and appends, so counting records showed
abundance while the calendar showed a hole.

The staleness check in run_daily_capture.sh cannot catch this either. It
measures hours since the LAST capture, which is a value check on the
newest record, and stays happy while a gap sits behind it.

Exit codes: 0 clean, 1 gaps found, 2 could not read the store.
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys


def from_store(d):
    """Dates present as capture files on disk."""
    out = set()
    for p in glob.glob(os.path.join(d, "vcdwd_0p1deg_*.npz")):
        stem = os.path.basename(p).replace("vcdwd_0p1deg_", "").replace(".npz", "")
        try:
            y, doy = int(stem[:4]), int(stem[4:])
            out.add((dt.date(y, 1, 1) + dt.timedelta(days=doy - 1)).isoformat())
        except Exception:
            continue
    return out


def from_manifest(p):
    """Dates the manifest claims, deduplicated. Duplicates are normal:
    each run re-captures a rolling window. They are also what hides a
    gap from anyone counting lines."""
    out = set()
    with open(p) as fh:
        for line in fh:
            try:
                out.add(json.loads(line)["date"])
            except Exception:
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", help="directory of vcdwd_0p1deg_*.npz")
    ap.add_argument("--manifest", help="vcdwd_capture_manifest.jsonl")
    ap.add_argument("--min-age-days", type=int, default=2,
                    help="days younger than this are not expected yet")
    ap.add_argument("--start", help="YYYY-MM-DD; defaults to the earliest date present")
    args = ap.parse_args()

    have = set()
    if args.store:
        have |= from_store(args.store)
    if args.manifest and os.path.exists(args.manifest):
        have |= from_manifest(args.manifest)
    if not have:
        print("FAIL: no capture records found at all")
        return 2

    start = dt.date.fromisoformat(args.start) if args.start else dt.date.fromisoformat(min(have))
    end = dt.date.today() - dt.timedelta(days=args.min_age_days)
    if end < start:
        print("nothing eligible yet")
        return 0

    expected = {(start + dt.timedelta(days=i)).isoformat()
                for i in range((end - start).days + 1)}
    missing = sorted(expected - have)

    print(f"expected {start} .. {end}  ({len(expected)} days)")
    print(f"present  {len(have & expected)}")
    if not missing:
        print("no gaps")
        return 0

    # A gap that has rolled off the LANCE window is unrecoverable, which
    # is a different severity from one still on the server.
    cutoff = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    lost = [d for d in missing if d < cutoff]
    still = [d for d in missing if d >= cutoff]
    print(f"MISSING {len(missing)}: {missing}")
    if still:
        print(f"  recoverable, still inside the LANCE window: {still}")
    if lost:
        print(f"  UNRECOVERABLE, rolled off the server: {lost}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
