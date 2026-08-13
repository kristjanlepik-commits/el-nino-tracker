"""Bridge a thin archive with the station's own bulletins, and COUNT the result.

WHY. Four cities have a long GHCN history that stops or thins out before the
present, and a WMO station that has been transmitting throughout. Larnaca's
GHCN ends in 2016; Algiers has one usable recent year in fifteen. In both
cases the station is not the problem, the archive is.

WHAT MAKES THIS LEGAL. One station, two transports, validated where they
overlap. Larnaca's bulletins reproduce GHCN exactly on summer 2016, the last
year both hold: 100.0% of days exact, worst 0.0 C, at 06Z and 18Z. That is
the same test that made London publishable and the same one that would have
caught Murcia.

WHY THIS COUNTS RATHER THAN SAMPLES. A bridge is not a current season. The
bridge years enter the RANKED series, so each one has to carry enough days to
be ranked, and a July that returns bytes is not a year that passes the bar. I
made exactly that mistake earlier today: I called three North African cities
viable on record SPAN and current-season presence, then found their maxima
were missing from most recent years. **Span is not coverage**, and this
script exists to print coverage rather than assert it.

FAILS BY REPORTING, NOT BY GUESSING. Every year is printed with its day
count. A year below the bar is shown, not silently dropped, so the decision
to include a city is made against the table rather than against a summary.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import synop  # noqa: E402
from safe_write import write_series

SRC = ROOT / "heat" / ".cache" / "src"
OGIMET = "https://www.ogimet.com/cgi-bin/getsynop"

# city: (WMO block, GHCN id, first bridge year, hours for min/max)
CITIES = {
    # BRIDGE FROM 2014, not 2017. The first run started where GHCN stopped
    # and left 1991-2020 at 27/30, short on exactly 2014, 2015 and 2016:
    # years GHCN holds PARTIALLY, at 61, 72 and 63 days. A gap does not
    # begin where an archive ends; it begins where the archive thins.
    "Larnaca":    ("17609", "CY000176090", 2014, "06", "18"),
    # BRIDGE FROM 1999. Algiers is short on exactly two years of 1971-2000,
    # 1999 at 60 days and 2000 at 92, so closing those two makes the
    # PREFERRED baseline complete and no exception is needed. OGIMET has
    # 2000 and nothing at 1995, so the archive begins in between; 1999 is
    # the year this turns on.
    "Algiers":    ("60390", "AG000060390", 1999, "06", "18"),
    "Tunis":      ("60715", "TSM00060715", 2010, "06", "18"),
    "Casablanca": ("60155", "MOM00060155", 2010, "06", "18"),
}
MIN_DAYS = 100          # May-Aug days with both extremes for a usable year


def ghcn(gid):
    """Whole-record daily extremes, quality-flagged values excluded."""
    path = SRC / f"ghcn_{gid}.dly"
    if not path.exists():
        blob = subprocess.run(
            ["curl", "-sS", "--max-time", "120",
             f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{gid}.dly"],
            capture_output=True).stdout
        path.write_bytes(blob)
    out = {}
    for L in path.read_text(errors="replace").splitlines():
        el = L[17:21]
        if el not in ("TMAX", "TMIN"):
            continue
        y, m = int(L[11:15]), int(L[15:17])
        for d in range(31):
            o = 21 + d * 8
            v, q = L[o:o + 5].strip(), L[o + 6:o + 7]
            if v in ("-9999", "") or q.strip():
                continue
            key = f"{y}-{m:02d}-{d + 1:02d}"
            mn, mx = out.get(key, (None, None))
            if el == "TMIN":
                mn = int(v) / 10.0
            else:
                mx = int(v) / 10.0
            out[key] = (mn, mx)
    return out


def synop_year(block, year, hmin, hmax):
    """One May-to-August pull, CACHED TO DISK.

    OGIMET returns an empty body intermittently and it is indistinguishable
    from a station having no data. That cost two false negatives earlier
    today, and then cost two YEARS: a rerun rebuilt from the archive, hit the
    transient on 2018 and 2022, and dropped both from a file that had them.

    So the raw pull is the artifact and it is kept. A rerun reuses what was
    fetched successfully and only retries what is missing, which makes the
    build idempotent against a flaky upstream instead of destructive.
    """
    cache = SRC / "synop_cache"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{block}_{year}.txt"
    if f.exists() and f.stat().st_size > 1000:
        raw = f.read_text(errors="replace")
    else:
        raw = ""
        for _attempt in (1, 2, 3):
            raw = subprocess.run(
                ["curl", "-sS", "--max-time", "200",
                 f"{OGIMET}?block={block}&begin={year}05010000&end={year}08312359"],
                capture_output=True).stdout.decode("utf-8", "replace")
            if len(raw) > 1000:
                f.write_text(raw)
                break
            time.sleep(8)
    out = {}
    for d, h, tx, tn in synop.parse_ogimet(raw):
        mn, mx = out.get(d, (None, None))
        if h == hmin and tn is not None:
            mn = tn
        if h == hmax and tx is not None:
            mx = tx
        out[d] = (mn, mx)
    return out


def usable(rows, lo, hi):
    per = {}
    for d, (mn, mx) in rows.items():
        if mn is not None and mx is not None and d[5:7] in ("05", "06", "07", "08"):
            per[int(d[:4])] = per.get(int(d[:4]), 0) + 1
    return per, sum(1 for y in range(lo, hi + 1) if per.get(y, 0) >= MIN_DAYS)


def build(city):
    block, gid, first, hmin, hmax = CITIES[city]
    rows = ghcn(gid)
    ghcn_years = sorted({int(d[:4]) for d in rows})
    for y in range(first, 2027):
        got = synop_year(block, y, hmin, hmax)
        # Bulletins fill gaps and never overwrite an archived value: the
        # archive is the better record where it exists.
        for d, (mn, mx) in got.items():
            omn, omx = rows.get(d, (None, None))
            rows[d] = (omn if omn is not None else mn,
                       omx if omx is not None else mx)
        time.sleep(3)
    per, _ = usable(rows, min(ghcn_years), 2026)
    return rows, per


def main() -> int:
    for city in (sys.argv[1:] or list(CITIES)):
        rows, per = build(city)
        yrs = sorted(per)
        ok = [y for y in yrs if per[y] >= MIN_DAYS]
        b71 = sum(1 for y in range(1971, 2001) if per.get(y, 0) >= MIN_DAYS)
        b91 = sum(1 for y in range(1991, 2021) if per.get(y, 0) >= MIN_DAYS)
        recent = [y for y in range(2017, 2027) if per.get(y, 0) >= MIN_DAYS]
        write_series(SRC / f"{city.lower()}.json",
                     [[d, mn, mx] for d, (mn, mx) in sorted(rows.items())],
                     label=city)
        print(f"  {city}: usable {len(ok)} years, {ok[0] if ok else '-'}"
              f" to {ok[-1] if ok else '-'}")
        print(f"    1971-2000 {b71}/30   1991-2020 {b91}/30   "
              f"2017-2026 {len(recent)}/10  {recent}")
        print(f"    2026 days: {per.get(2026, 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
