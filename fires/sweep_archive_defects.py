"""Regenerate fires/data/archive_defects.json from the cache itself.

WHY THIS IS A SCRIPT RATHER THAN A LIST. The register was first written
as a frozen snapshot of one sweep and then made authoritative over the
cache. That is the defect it exists to prevent, one level up: a check
that reads a static index inherits the index's staleness, so a defect
appearing after the sweep would be summed as a zero exactly as before.

Floods' framing, from finding the same shape on their channel and then
finding it again in their own fix: point the difference at a store that
cannot disagree with the data. The cache IS the data, so the sweep runs
against the cache and the register is derived. Run it whenever the cache
grows, and the register cannot silently fall behind.

TWO CLASSES, because a check on VALUES cannot detect a MISSING RECORD.

    thin    present but far below its own neighbourhood. Found by
            comparing roster-wide daily totals against a local median,
            judged against neighbours rather than a fixed cut because
            fire is seasonal and a global threshold would flag every
            boreal winter day.

    absent  no record at all, inside a year the builder marked complete,
            so it was being read as a genuine zero. Found by
            set-difference against the calendar. Invisible to the first
            sweep: a total cannot be low if there is no row to be low.

WHY IT MATTERS. Summed as zero, a defective day lowers the baseline mean
and INFLATES every multiple computed against it, in the direction that
flatters our own headlines. Measured 2026-08-05: 0.5% on a typical
weekly window, 6.6% on the worst.

Confirmed against VIIRS NOAA-20, an independent platform with its own
downlink and processing: five sampled thin days read 0.00 to 0.06 of
NOAA-20 while two controls read 0.92 and 0.99. They do not heal, so
exclusion is the only remedy: 2022-08-01 is still zero in
science-quality four years on while NOAA-20 holds 12,813 for it.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from datetime import date, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "fires", "data", "full_history")
OUT = os.path.join(REPO, "fires", "data", "archive_defects.json")

# A day under half its own neighbourhood is thin. Loose on purpose: a
# genuinely calm day sits near 0.8 of its neighbours, and the observed
# defects sat at 0.02 to 0.28. Where a choice of error exists, take the
# one that makes our own numbers look worse.
THIN_FRACTION = 0.5
MIN_NEIGHBOUR_MEDIAN = 2000    # below this the ratio is noise
MIN_COUNTRIES = 8              # a date needs enough holders to judge


def load():
    """Roster-wide daily totals, and how many countries hold each date."""
    totals, holders, eligible = {}, {}, {}
    for f in sorted(os.listdir(CACHE)):
        if not f.endswith(".json"):
            continue
        doc = json.load(open(os.path.join(CACHE, f)))
        complete = {y for y in doc.get("_complete", [])
                    if len(doc.get(y, {})) >= 300}
        for y in complete:
            eligible[y] = eligible.get(y, 0) + 1
            for k, v in doc[y].items():
                totals[k] = totals.get(k, 0) + v
                holders[k] = holders.get(k, 0) + 1
    return totals, holders, eligible


def sweep_thin(totals):
    dates = sorted(totals)
    out = []
    for i, dt in enumerate(dates):
        lo, hi = max(0, i - 7), min(len(dates), i + 8)
        nbrs = [totals[dates[j]] for j in range(lo, hi) if j != i]
        if len(nbrs) < MIN_COUNTRIES:
            continue
        med = st.median(nbrs)
        if med > MIN_NEIGHBOUR_MEDIAN and totals[dt] < med * THIN_FRACTION:
            out.append(dt)
    return out


def sweep_absent(holders, eligible):
    rows = []
    for y, n in sorted(eligible.items()):
        d = date(int(y), 1, 1)
        while d.year == int(y):
            rows.append((d.isoformat(), holders.get(d.isoformat(), 0)))
            d += timedelta(days=1)
    out = []
    for i, (k, n) in enumerate(rows):
        lo, hi = max(0, i - 7), min(len(rows), i + 8)
        nbrs = [rows[j][1] for j in range(lo, hi)
                if j != i and rows[j][0][:4] == k[:4]]
        if len(nbrs) < MIN_COUNTRIES:
            continue
        med = st.median(nbrs)
        if med >= MIN_COUNTRIES and n < med * 0.5:
            out.append(k)
    return out


def main() -> int:
    totals, holders, eligible = load()
    thin = sweep_thin(totals)
    absent = sweep_absent(holders, eligible)
    # A date can be both: absent for most countries and thin for the few
    # that hold it. Absent is the stronger statement, so it wins.
    thin = [d for d in thin if d not in set(absent)]

    prev = {}
    try:
        prev = json.load(open(OUT))
    except (OSError, ValueError):
        pass
    was = set(prev.get("thin", [])) | set(prev.get("absent", []))
    now = set(thin) | set(absent)
    added, gone = sorted(now - was), sorted(was - now)

    doc = dict(prev)
    doc.update({
        "_readme": [
            "DERIVED, not hand-maintained. Regenerate with",
            "python -m fires.sweep_archive_defects whenever the cache grows.",
            "A frozen list would inherit the staleness this file exists to",
            "prevent: a defect appearing after the last sweep would be",
            "summed as a zero exactly as before.",
            "",
            "A date listed here must be excluded from BOTH sides of any",
            "comparison, never summed as zero. A day the instrument did",
            "not observe is not a day without fire, and summing it as one",
            "lowers the baseline and inflates every multiple against it.",
            "",
            "thin   present but far below its own neighbourhood.",
            "absent no record at all inside a year marked complete, so it",
            "       was read as a genuine zero. A check on values cannot",
            "       find these; only a set-difference against the calendar.",
        ],
        "swept": date.today().isoformat(),
        "sensor": "VIIRS_SNPP",
        "thin": sorted(thin),
        "absent": sorted(absent),
    })
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"swept {len(totals):,} cached dates: "
          f"{len(thin)} thin, {len(absent)} absent")
    if added:
        print(f"::error::{len(added)} NEW archive defect(s) since the last "
              f"sweep: {', '.join(added[:10])}"
              f"{' ...' if len(added) > 10 else ''}. Every multiple computed "
              f"against these was inflated until now.", file=sys.stderr)
    if gone:
        print(f"  no longer flagged ({len(gone)}): {', '.join(gone[:10])}",
              file=sys.stderr)
    if not added and not gone and was:
        print("  unchanged since the last sweep")
    return 0


if __name__ == "__main__":
    sys.exit(main())
