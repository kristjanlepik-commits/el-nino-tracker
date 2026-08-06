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

Running it the same day found 2026-07-22 absent from the capture
manifest while every other day from 07-21 to 08-03 was present. The
manifest carried 43 records for 13 distinct dates, because each run
re-captures a rolling window and appends, so counting records showed
abundance while the calendar showed a hole.

The staleness check in run_daily_capture.sh cannot catch this either. It
measures hours since the LAST capture, which is a value check on the
newest record, and stays happy while a gap sits behind it.

**And the first version of this script had the same blind spot one level
up.** It read the manifest, reported 2026-07-22 as an unrecoverable
loss, and was wrong: platform had uploaded that day to the release store
on 2026-07-29, six days before anyone noticed the gap. The archive was
complete; only the index was wrong.

So the authoritative set is the RELEASE STORE, not the manifest. The
store cannot drift from the data because it is the data; the manifest is
a log of what each run did, which is a useful thing to keep and a bad
thing to trust. This reconciles the two and reports each direction of
divergence separately, because they mean different things:

    in store, not in manifest   the index is wrong, the data is safe
    in manifest, not in store   the data is missing, which is serious
    in neither                  a genuine hole against the calendar

Exit codes: 0 clean, 1 gaps or divergence, 2 could not read the store.
"""

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys


def _iso(stem):
    y, doy = int(stem[:4]), int(stem[4:])
    return (dt.date(y, 1, 1) + dt.timedelta(days=doy - 1)).isoformat()


def from_release(tag):
    """Dates present in the release store. THE AUTHORITATIVE SET."""
    try:
        raw = subprocess.check_output(
            ["gh", "release", "view", tag, "--json", "assets",
             "--jq", ".assets[].name"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    out = set()
    for name in raw.split():
        if name.startswith("vcdwd_0p1deg_") and name.endswith(".npz"):
            try:
                out.add(_iso(name[13:-4]))
            except Exception:
                continue
    return out


def from_store(d):
    """Dates present as capture files on local disk. A cache, not truth."""
    out = set()
    for p in glob.glob(os.path.join(d, "vcdwd_0p1deg_*.npz")):
        try:
            out.add(_iso(os.path.basename(p)[13:-4]))
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
    ap.add_argument("--release-tag", default="vcdwd-capture",
                    help="authoritative store; pass empty to skip")
    ap.add_argument("--store", help="local directory of vcdwd_0p1deg_*.npz (a cache)")
    ap.add_argument("--manifest", help="vcdwd_capture_manifest.jsonl")
    ap.add_argument("--min-age-days", type=int, default=2,
                    help="days younger than this are not expected yet")
    ap.add_argument("--start", help="YYYY-MM-DD; defaults to the earliest date present")
    args = ap.parse_args()

    release = from_release(args.release_tag) if args.release_tag else None
    manifest = (from_manifest(args.manifest)
                if args.manifest and os.path.exists(args.manifest) else None)
    local = from_store(args.store) if args.store else None

    # Truth order: release store, else local disk. Never the manifest, and
    # never the union of stores: checking manifest and local together on
    # 2026-08-03 reported no gaps, which was true and useless, because one
    # filled the other's hole and hid that the index was incomplete.
    have = release if release is not None else local
    if not have:
        print("FAIL: could not read an authoritative store")
        return 2
    src = "release store" if release is not None else "local disk"
    print(f"authoritative source: {src} ({len(have)} days)")

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

    rc = 0
    if manifest is not None and release is not None:
        only_store = sorted(release - manifest)
        only_man = sorted(manifest - release)
        if only_store:
            print(f"INDEX WRONG, data safe: in store but not manifest: {only_store}")
            rc = 1
        if only_man:
            print(f"DATA MISSING: in manifest but not store: {only_man}")
            rc = 1
        if not only_store and not only_man:
            print("manifest reconciles with store")

    if not missing:
        if rc == 0:
            print("no gaps")
        return rc

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
