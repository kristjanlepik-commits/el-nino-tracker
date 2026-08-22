"""What could a LatAm heat page actually say? A survey, not a build.

WHY THIS EXISTS AND WHY IT COMES FIRST. My first LatAm screen asked whether
the DATA supports the instrument and never asked whether the INSTRUMENT
travels. It does not: Buenos Aires' July mean maximum is 15.6 C, their
coldest month, and our threshold is calibrated on July-August. A build would
have derived a hot-day bar from their two coldest months and published
confident, entirely wrong numbers.

So this reports the DERIVED hot season per station, measured from each
record rather than assumed. That is the column that would have caught Buenos
Aires before anyone wrote code, and it is what turns an inventory into an
instrument test.

WHAT IT DELIBERATELY DOES NOT DO. It does not compute page numbers. Design
will want figures for a mockup and these are not them: a count produced
outside the instrument, by a script written for a survey, is exactly the kind
of number that gets believed as inventory a day later. Every figure here
describes the ARCHIVE, not a claim about a city.

TWO COLUMNS, NOT ONE. A complete baseline is not the binding constraint;
having a baseline AND a present is. A city with history and no current year
is a bridge job. A city with neither is out. Both are reported.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "heat" / ".cache" / "src" / "latam"
OUT = ROOT / "heat" / "data" / "latam_survey.json"
MIN_YEAR_DAYS = 300


def read(sid):
    """Daily extremes for one station, quality-flagged values excluded."""
    f = D / f"{sid}.dly"
    if not f.exists():
        return None
    out = {}
    for L in f.read_text(errors="replace").splitlines():
        el = L[17:21]
        if el not in ("TMAX", "TMIN"):
            continue
        y, m = int(L[11:15]), int(L[15:17])
        for d in range(31):
            o = 21 + d * 8
            v, q = L[o:o + 5].strip(), L[o + 6:o + 7]
            if v in ("-9999", "") or q.strip():
                continue
            out.setdefault((y, m, d + 1), {})[el] = int(v) / 10.0
    return out


def hot_season(rows, lo=1991, hi=2020):
    """The three warmest consecutive months, MEASURED.

    Consecutive because a season is a run rather than a set: taking the three
    warmest months independently can straddle a year boundary in the southern
    hemisphere and produce Dec, Jan, Feb as three separate answers with no
    ordering. A wrap-around run is what a southern summer actually is, so the
    search runs over the 12 rotations rather than over combinations.
    """
    mon = collections.defaultdict(list)
    for (y, m, _d), e in rows.items():
        if lo <= y <= hi and "TMAX" in e:
            mon[m].append(e["TMAX"])
    means = {m: statistics.mean(v) for m, v in mon.items() if len(v) >= 60}
    if len(means) < 12:
        return None, None
    best, run = None, None
    for start in range(1, 13):
        months = [((start - 1 + k) % 12) + 1 for k in range(3)]
        val = sum(means[m] for m in months) / 3
        if best is None or val > best:
            best, run = val, months
    return run, {m: round(v, 1) for m, v in sorted(means.items())}


def survey(sid, name, lat, lon):
    rows = read(sid)
    if not rows:
        return None
    per = collections.Counter()
    for k, e in rows.items():
        if len(e) == 2:
            per[k[0]] += 1
    years = sorted(y for y, c in per.items() if c >= MIN_YEAR_DAYS)
    season, monthly = hot_season(rows)
    b71 = sum(1 for y in range(1971, 2001) if per.get(y, 0) >= MIN_YEAR_DAYS)
    b91 = sum(1 for y in range(1991, 2021) if per.get(y, 0) >= MIN_YEAR_DAYS)
    recent = [y for y in range(2017, 2027) if per.get(y, 0) >= MIN_YEAR_DAYS]
    return {
        "station": sid, "name": name, "lat": lat, "lon": lon,
        "hemisphere": "south" if lat < 0 else "north",
        "record": {"from": years[0] if years else None,
                   "to": years[-1] if years else None,
                   "usable_years": len(years)},
        "baseline": {"1971_2000": b71, "1991_2020": b91,
                     "complete": max(b71, b91) == 30},
        "present": {"recent_years_of_10": len(recent),
                    "last_usable_year": years[-1] if years else None,
                    "has_2026": per.get(2026, 0) >= 100,
                    "archive_only": bool(years) and years[-1] < 2025},
        "hot_season": {
            "months": season,
            "monthly_mean_max_c": monthly,
            "matches_our_window": season == [6, 7, 8] or season == [7, 8],
            "note": ("Three warmest CONSECUTIVE months, measured over "
                     "1991-2020. Our instrument calibrates on July-August "
                     "and counts from 1 May, so a station whose hot season "
                     "is not northern summer cannot use it unchanged."),
        },
        "verdict": None,
    }


def main() -> int:
    names = {}
    stations = ROOT / "heat" / ".cache" / "src" / "ghcnd-stations.txt"
    for L in stations.read_text(errors="replace").splitlines():
        names[L[:11]] = (L[41:71].strip(), float(L[12:20]), float(L[21:30]))
    cand = [l.strip() for l in open("/tmp/latam_cand.txt") if l.strip()]
    rows = []
    for sid in cand:
        nm, la, lo = names.get(sid, ("?", 0.0, 0.0))
        r = survey(sid, nm, la, lo)
        if not r:
            continue
        b = r["baseline"]["complete"]
        p = r["present"]["recent_years_of_10"] >= 5
        r["verdict"] = ("ready" if b and p else
                        "bridge_job" if b else
                        "present_only" if p else "out")
        rows.append(r)
    rows.sort(key=lambda r: (r["verdict"] != "ready",
                             r["verdict"] != "bridge_job",
                             -r["baseline"]["1971_2000"]))
    OUT.write_text(json.dumps({
        "_readme": (
            "SURVEY, NOT A BUILD. Every figure describes the archive, not a "
            "claim about a city. Nothing here is page-ready and none of it "
            "was produced by the instrument that produces published counts."),
        "candidates": len(rows),
        "hot_season_note": (
            "The decisive column. Our instrument assumes a northern summer "
            "in four places: WINDOW_START, the percentile baseline, the "
            "coverage window, and the bridge's fetch range. A southern "
            "station's hot season is Dec-Feb, so the instrument cannot be "
            "pointed at it unchanged."),
        "stations": rows}, indent=1) + "\n")

    v = collections.Counter(r["verdict"] for r in rows)
    print(f"  {len(rows)} stations surveyed: {dict(v)}")
    seas = collections.Counter(tuple(r["hot_season"]["months"] or [])
                               for r in rows)
    print("  derived hot seasons:")
    for s, n in seas.most_common(6):
        print(f"    {list(s)}  {n} stations")
    print(f"\n  {'verdict':13s} {'71-00':>5} {'91-20':>5} {'rec':>4} "
          f"{'season':>12}  station")
    for r in rows[:16]:
        print(f"  {r['verdict']:13s} {r['baseline']['1971_2000']:>5} "
              f"{r['baseline']['1991_2020']:>5} "
              f"{r['present']['recent_years_of_10']:>4} "
              f"{str(r['hot_season']['months']):>12}  {r['name'][:26]}")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
