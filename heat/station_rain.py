"""Daily station rain from SYNOP bulletins, checked against GHCN (D-321).

Heat writes this, floods reviews and consumes it. It exists because D-318
reframed floods around station rain records, and the rain was already in
two readers heat owns and discarded in both.

    .venv/bin/python heat/station_rain.py zagreb --years 2010-2023

WHAT IT DOES, in the order a reviewer should check it:

1. FETCH by calendar month, any month (the heat cache is May to August
   only, so it cannot serve rain). A response that stops before the end of
   the span asked for is CONTINUED from its last bulletin, and the month is
   reported PAGED, because OGIMET truncates silently with HTTP 200. Paging
   rather than a fixed chunk size, because the cap is not one number: Salta
   stopped at 5,798 bulletins on 2026-09-17, while Budapest's May to August
   2026 came back whole at 14,666 in one response.

2. ASSEMBLE a day only from bulletin periods that TILE the 24 hours
   exactly: one 24 h total, two 12 h, four 6 h, or any exact mix. Never a
   sum of whatever arrived. Where two tilings exist they must agree within
   their rounding (0.5 mm per whole-mm piece, 0.1 for a 7RRRR tenths
   total) or the day is a CONFLICT and has no value. iR 3 ("none fell")
   counts as zero only over the period this station measurably reports at
   that hour; iR 4 and / are never zero.

3. COMPARE to GHCN on overlapping days, under both ways of labelling the
   rain day (by the date it ends or the date it starts), and report the
   agreement. The labelling with the better wet-day agreement is used, and
   if the two are within five points of each other that is printed as
   UNRESOLVED rather than chosen quietly.

A day with no complete tiling is ABSENT. That is the whole defence against
truncation becoming dryness: a cut response produces missing days, and a
missing day breaks the unbroken record D-318 clause 1 demands, loudly,
instead of reading as a dry spell.

What this does NOT do: decide which stations or durations may carry a
public record (D-318 clause 3 is floods' and product's), or judge whether
a GHCN value is physically plausible (Lima's 271 mm days pass GHCN's own
quality flags). It reports; it does not rank.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import synop  # noqa: E402
from build_bridge import OGIMET, SRC, _is_synop, read_ghcn_prcp  # noqa: E402

CACHE = SRC / "synop_rain"
OUT = ROOT / "heat" / ".cache" / "rain"

# Station identity: (WMO block for bulletins, GHCN id, rain-day end hour UTC).
# Zagreb is GRIC (14236), NOT the 14240 Maksimir block heat's temperature
# bridge uses: GHCN's HR000142360 is Gric, and rain is too local for a
# different gauge 4 km away to stand in for it. The 06 UTC end hour is the
# European climatological rain day; the GHCN comparison tests it.
STATIONS = {
    "zagreb":   ("14236", "HR000142360", 6),
    "budapest": ("12843", "HUM00012843", 6),
    "vilnius":  ("26730", "LH000026730", 6),
}

PIECE_TOL = {"r24": 0.1}          # rounding of one piece, mm; default 0.5
GHCN_TOL_MM, GHCN_TOL_FRAC = 1.0, 0.10
WET_MM = 1.0


# ---------------------------------------------------------------- fetch

def _ts(line):
    p = line.split(",")
    return dt.datetime(int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5]))


class Unreachable(RuntimeError):
    """OGIMET did not answer at all. Stop the run: carrying on would read a
    refused connection as a station with no reports."""


# PACING. On 2026-10-04 about seventy requests in twenty minutes from this
# laptop were followed by connection timeouts, which is OGIMET refusing us,
# not stations falling silent. The weekly heat refresh fetches from CI and
# is unaffected, but a rain backfill from here has to stay polite.
PAUSE_S = 6


def _get(block, a, b, tries=3):
    """One OGIMET request, retried, [] if the reply carried no bulletins.

    A reply with no bulletins and a connection that failed are different
    answers: the first is a station with nothing in the span (or a flake,
    hence the retries), the second raises Unreachable.
    """
    failed = 0
    for attempt in range(1, tries + 1):
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "200",
             f"{OGIMET}?block={block}&begin={a:%Y%m%d%H%M}&end={b:%Y%m%d%H%M}"],
            capture_output=True)
        if r.returncode != 0:
            failed += 1
        raw = r.stdout.decode("utf-8", "replace")
        lines = [L for L in raw.splitlines()
                 if L.startswith(f"{block},") and "AAXX" in L]
        if lines:
            return lines
        if attempt < tries:
            time.sleep(8 * attempt)
    if failed == tries:
        raise Unreachable(f"OGIMET unreachable for {block} {a:%Y-%m}: "
                          f"{r.stderr.decode(errors='replace').strip()}")
    return []


def fetch_month(block, y, m, today=None):
    """All bulletins for one month, paged past silent truncation.

    Returns (lines, info) where info carries bulletins, last, pages, and
    complete. A finished month is cached and reused; the current month is
    always refetched and replaces the cache only if it is not shorter.
    """
    today = today or dt.date.today()
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{block}_{y}{m:02d}.txt"
    start = dt.datetime(y, m, 1)
    end = (dt.datetime(y + (m == 12), m % 12 + 1, 1)
           - dt.timedelta(minutes=1))
    current = (y, m) == (today.year, today.month)
    cached = None
    if f.exists():
        cached = [L for L in f.read_text(errors="replace").splitlines() if L]
        if not current and _is_synop("\n".join(cached), block):
            return cached, _info(cached, end, pages=0, cached=True)

    lines, pages, a = [], 0, start
    while True:
        # A continuation is asked once: an empty answer is the normal reply
        # for a station whose day ends before midnight, and retrying it three
        # times cost a minute a month.
        got = _get(block, a, end, tries=3 if a == start else 1)
        time.sleep(PAUSE_S)
        new = [L for L in got if not lines or _ts(L) > _ts(lines[-1])]
        if not new:
            break
        lines += new
        pages += 1
        last = _ts(lines[-1])
        # Stations end their day at 21Z, 23Z or 23:50. Anything before 18Z
        # on the last day is asked for again from where it stopped: an empty
        # answer means the station fell silent, a non-empty one means the
        # first response was cut. 18Z is the earliest report a 06Z rain day
        # on the 1st needs from this month.
        if last >= end - dt.timedelta(hours=6):
            break
        a = last + dt.timedelta(minutes=1)
    if cached and len(cached) > len(lines):
        print(f"    {block} {y}-{m:02d}: refetch carried {len(lines)} "
              f"bulletins against {len(cached)} cached; keeping the cache",
              file=sys.stderr)
        return cached, _info(cached, end, pages=0, cached=True)
    if lines:
        f.write_text("\n".join(lines) + "\n")
    return lines, _info(lines, end, pages, cached=False)


def _info(lines, end, pages, cached):
    last = _ts(lines[-1]) if lines else None
    return {"bulletins": len(lines), "last": str(last) if last else None,
            "pages": pages, "cached": cached,
            "complete": bool(last and last.date() == end.date())}


# ---------------------------------------------------------------- assemble

def _reports(lines):
    """{end datetime: {(hours, source): set of (mm, trace)}}, plus iR-3 times
    and a flag tally. Only on-the-hour bulletins carry periods used here."""
    by = defaultdict(lambda: defaultdict(set))
    zeros, flags = [], Counter()
    for L in lines:
        p = L.split(",")
        if len(p) < 7 or not p[1].isdigit() or int(p[5]) != 0:
            continue
        t = dt.datetime(int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        reps, zero, fl = synop.rain_reports(",".join(p[6:]))
        flags.update(fl)
        for hours, mm, trace, src in reps:
            by[t][(hours, src)].add((mm, trace))
        if zero:
            zeros.append(t)
    return by, zeros, flags


def _modal_periods(by):
    """Which (hours, source) this station reports at each hour of day,
    measured from its own explicit groups, so iR 3 can be placed."""
    seen = defaultdict(Counter)
    for t, d in by.items():
        for key in d:
            if key[1] != "r24":
                seen[t.hour][key] += 1
    out = {}
    for h, c in seen.items():
        top = max(c.values())
        out[h] = [k for k, v in c.items() if v >= top / 3]
    return out


def daily(lines, end_hour):
    """{date the rain day ENDS: (mm, trace, pieces)} plus diagnostics."""
    by, zeros, flags = _reports(lines)
    modal = _modal_periods(by)
    placed = 0
    for t in zeros:
        for key in modal.get(t.hour, []):
            if not by[t].get(key):
                by[t][key].add((0.0, False))
                placed += 1

    # A slot reporting two different values (a correction, a duplicate that
    # disagrees) is unusable rather than resolved by picking one.
    conflicts_slot = 0
    pieces = defaultdict(list)          # end time -> [(hours, mm, trace, tol)]
    for t, d in by.items():
        for (hours, src), vals in d.items():
            if len(vals) > 1:
                conflicts_slot += 1
                continue
            mm, trace = next(iter(vals))
            pieces[t].append((hours, mm, trace, PIECE_TOL.get(src, 0.5)))

    @functools.lru_cache(maxsize=None)
    def tilings(t, remaining):
        """Distinct (sum, trace, tol, n) for exact covers of `remaining`
        hours ending at t. Rounded to 0.1 so the set stays small."""
        if remaining == 0:
            return frozenset({(0.0, False, 0.0, 0)})
        out = set()
        for hours, mm, trace, tol in pieces.get(t, ()):
            if hours <= remaining:
                for s, tr, tl, n in tilings(t - dt.timedelta(hours=hours),
                                            remaining - hours):
                    out.add((round(s + mm, 1), tr or trace,
                             round(tl + tol, 2), n + 1))
                    if len(out) > 400:
                        break
        return frozenset(out)

    days, conflict_days = {}, []
    ends = sorted({t.date() for t in pieces})
    for d in ends:
        t = dt.datetime(d.year, d.month, d.day, end_hour)
        cands = tilings(t, 24)
        if not cands:
            continue
        best = min(cands, key=lambda c: (c[2], c[3]))
        if any(abs(c[0] - best[0]) > c[2] + best[2] + 1e-9 for c in cands):
            conflict_days.append(str(d))
            continue
        days[str(d)] = (best[0], best[1] and best[0] == 0.0, best[3])
    diag = {"iR3_zeros_placed": placed, "slot_conflicts": conflicts_slot,
            "conflict_days": conflict_days, "flags": dict(flags)}
    return days, diag


# ---------------------------------------------------------------- compare

def _agree(s, g):
    return abs(s - g) <= max(GHCN_TOL_MM, GHCN_TOL_FRAC * max(s, g))


def compare(syn, ghcn, shift):
    """Agreement with GHCN when the bulletin day is labelled `shift` days
    from its end date (0: by end date, -1: by start date)."""
    pairs = []
    for d, (mm, _tr, _n) in syn.items():
        k = str(dt.date.fromisoformat(d) + dt.timedelta(days=shift))
        if k in ghcn:
            pairs.append((k, mm, ghcn[k][0], ghcn[k][2]))
    wet = [p for p in pairs if p[2] >= WET_MM or p[1] >= WET_MM]
    return {
        "days": len(pairs),
        "agree_all": sum(_agree(p[1], p[2]) for p in pairs) / max(len(pairs), 1),
        "wet_days": len(wet),
        "agree_wet": sum(_agree(p[1], p[2]) for p in wet) / max(len(wet), 1),
        "sources": dict(Counter(p[3] for p in pairs)),
        "pairs": pairs,
    }


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("station", choices=sorted(STATIONS))
    ap.add_argument("--years", required=True, help="e.g. 2010-2023")
    a = ap.parse_args(argv)
    block, gid, end_hour = STATIONS[a.station]
    y0, y1 = (int(x) for x in a.years.split("-"))

    lines, short, paged = [], [], []
    today = dt.date.today()
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            if (y, m) > (today.year, today.month):
                break
            try:
                got, info = fetch_month(block, y, m)
            except Unreachable as e:
                print(f"STOPPED, nothing written: {e}. Finished months are "
                      f"cached; rerun later and it resumes.", file=sys.stderr)
                return 2
            lines += got
            if info["pages"] > 1:
                paged.append(f"{y}-{m:02d}")
            if not info["complete"] and (y, m) != (today.year, today.month):
                short.append(f"{y}-{m:02d} ({info['bulletins']} bulletins, "
                             f"last {info['last']})")
        print(f"  {block} {y}: fetched", file=sys.stderr)

    syn, diag = daily(lines, end_hour)
    ghcn = read_ghcn_prcp(SRC / f"ghcn_{gid}.dly")
    span = [d for d in syn if y0 <= int(d[:4]) <= y1]
    possible = (dt.date(min(y1, today.year), 12, 31)
                - dt.date(y0, 1, 1)).days + 1

    print(f"\n{a.station}: block {block}, GHCN {gid}, rain day ends "
          f"{end_hour:02d} UTC, {y0}-{y1}")
    print(f"  bulletin days assembled: {len(span)} of {possible}")
    print(f"  iR-3 zeros placed: {diag['iR3_zeros_placed']}, "
          f"conflicting slots: {diag['slot_conflicts']}, "
          f"conflict days: {len(diag['conflict_days'])}")
    if diag["flags"]:
        print(f"  parser flags: {diag['flags']}")
    if paged:
        print(f"  PAGED (OGIMET truncated, continued): {', '.join(paged)}")
    if short:
        print(f"  INCOMPLETE months, last bulletin before month end:")
        for s in short:
            print(f"    {s}")

    res = {s: compare(syn, ghcn, s) for s in (0, -1)}
    for s, r in res.items():
        lab = "end date" if s == 0 else "start date"
        print(f"  vs GHCN labelled by {lab}: {r['days']} days, agree "
              f"{r['agree_all']:.1%} all, {r['agree_wet']:.1%} of "
              f"{r['wet_days']} wet; GHCN sources {r['sources']}")
    best = max(res, key=lambda s: res[s]["agree_wet"])
    gap = abs(res[0]["agree_wet"] - res[-1]["agree_wet"])
    if gap < 0.05:
        print("  LABELLING UNRESOLVED: the two conventions agree within "
              "five points; not chosen")
    else:
        print(f"  labelling: by {'end' if best == 0 else 'start'} date "
              f"(wet-day agreement {gap:.0%} better)")
    r = res[best]
    top = sorted(r["pairs"], key=lambda p: -p[2])[:15]
    print("  wettest GHCN days in the overlap, bulletin beside:")
    for d, s, g, src in top:
        mark = "" if _agree(s, g) else "   <-- disagree"
        print(f"    {d}  GHCN {g:6.1f}  bulletins {s:6.1f}  [{src}]{mark}")
    if r["sources"].get("S"):
        print(f"  NOTE: {r['sources']['S']} overlap days are GHCN source S "
              f"(GSOD, built from SYNOP): agreement there is not independent")

    OUT.mkdir(parents=True, exist_ok=True)
    shift = best
    out = {str(dt.date.fromisoformat(d) + dt.timedelta(days=shift)):
           {"mm": mm, "trace": tr, "pieces": n}
           for d, (mm, tr, n) in sorted(syn.items())}
    (OUT / f"{a.station}_bulletin_daily.json").write_text(json.dumps({
        "station": a.station, "block": block, "ghcn": gid,
        "rain_day_end_utc": end_hour,
        "labelled_by": "end" if shift == 0 else "start",
        "labelling_unresolved": gap < 0.05,
        "incomplete_months": short, "paged_months": paged,
        "conflict_days": diag["conflict_days"],
        "days": out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
