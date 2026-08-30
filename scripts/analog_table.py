"""
Emit the matched-date analog comparison table for CWWA and wind bursts.

WHY THIS EXISTS. On 2026-08-30 I hand-computed a CWWA comparison for the
editor's note and matched 2026 against the analog years on the ISSUE date
rather than the OBSERVATION date. ERA5 runs about six days behind, so every
row was mislabelled by roughly a week and the headline ratio came out 70%
of 1997 when the truth was 75%. Editor caught it. The rule I broke is the
one I wrote into methodology.md two weeks earlier ("Comparing against
analog years: match on the last observation").

The production renderer already does this correctly (run_brief.py takes the
comparison date from the series itself). The gap was that numbers reaching
the editor by hand went through no such path. This closes it.

WHAT IT GUARANTEES
  1. Every ratio is computed at the same calendar date in both years.
  2. The observation date is printed in the header and on every row, so a
     figure cannot be quoted without the date it belongs to.
  3. Analog burst counts are truncated at 2026's last observation, never
     compared against a full analog season.
  4. Right-censored bursts are counted separately, so "13 bursts" is never
     emitted bare when one of them is still open.
  5. A missing calendar match is reported, not silently replaced. (Note:
     run_brief.py's _cwwa_at falls back to the last series value in that
     case, which would matter on 29 February. Flagged, not changed; that
     line sits inside design's function.)

Run from the repo root:

    .venv/bin/python scripts/analog_table.py
    .venv/bin/python scripts/analog_table.py --snapshot 2026-08-24
    .venv/bin/python scripts/analog_table.py --dates 2026-07-27,2026-08-24

Reads .fetch_cache/ by default (the live state, what tomorrow's run sees).
--snapshot reads a committed snapshot instead, which is reproducible and is
what you want when checking a figure that has already been published.
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / ".fetch_cache"
SNAPSHOTS = REPO / "snapshots"
CURRENT_YEAR = "2026"

# 2025 is plotted as a NON-EVENT (La Nina) reference, not a super-event peer.
# Its CWWA is near zero, so ratios against it run into the thousands of
# percent and mean nothing. Shown in the table for context, never offered as
# a quotable figure.
NON_EVENT_REFERENCES = {"2025"}

# The years we actually quote against in copy.
SUPER_PEERS = ("1997", "2015")


def _die(msg):
    print(f"analog_table: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_from_cache():
    """Live state: the two ERA5 last-good caches the next run will read."""
    wwe_p, burst_p = CACHE / "era5_wwe_last_good.json", CACHE / "era5_burst_last_good.json"
    if not wwe_p.exists():
        _die(f"no CWWA cache at {wwe_p}. Run a fetch first, or use --snapshot.")
    wwe = json.loads(wwe_p.read_text())
    burst = json.loads(burst_p.read_text()) if burst_p.exists() else {}
    return {
        "origin": ".fetch_cache",
        "issued": wwe.get("issued"),
        "series": wwe["payload"]["cwwa_series"],
        "analogs": wwe["payload"]["cwwa_analogs"],
        "current": wwe["payload"].get("cwwa_ms_days"),
        "events": (burth := burst.get("payload") or {}).get("events_detail") or [],
        "event_analogs": burth.get("analogs") or {},
    }


def load_from_snapshot(date):
    """A committed snapshot. Immutable, so this reproduces a published figure."""
    p = SNAPSHOTS / f"{date}.json"
    if not p.exists():
        _die(f"no snapshot at {p}")
    phys = json.loads(p.read_text()).get("physical_state") or {}
    if not phys.get("cwwa_series"):
        _die(f"snapshot {date} carries no cwwa_series")
    return {
        "origin": f"snapshots/{date}.json",
        "issued": date,
        "series": phys["cwwa_series"],
        "analogs": phys.get("cwwa_analogs") or {},
        "current": phys.get("cwwa_ms_days"),
        "events": phys.get("wwb_events_detail") or [],
        "event_analogs": phys.get("wwb_analogs") or {},
    }


def value_at(series, mmdd):
    """Analog value at the SAME calendar date. None if absent, never a guess."""
    for iso, v in series:
        if iso[5:] == mmdd:
            return float(v)
    return None


def pick_dates(series, explicit, weeks):
    """Default: weekly samples back from the last observation."""
    if explicit:
        return explicit
    have = [iso for iso, _ in series]
    last = have[-1]
    idx = {iso: i for i, iso in enumerate(have)}
    out = [have[i] for i in range(idx[last], -1, -7)][:weeks]
    return sorted(out)


def horizon_of(events):
    """Last date this year's burst data reaches. NOT the end of its season.

    The burst detector sets ongoing = (event ends at the last index of the
    series), so an analog year's final event is flagged open purely because
    the cached series stops. Measured 2026-08-30, the analog burst data ends
    31 August, so 1997's "15 events" is 15 BY 31 AUGUST and says nothing
    about September onward. Printing the horizon stops that being read as a
    season total.
    """
    return max((e.get("end") or "") for e in events) if events else ""


def burst_split(events, cutoff_mmdd=None):
    """Return (started, closed, open) as of the cutoff.

    Openness is taken from the stored `ongoing` flag, which is correct per
    series: it means the event runs to that year's data horizon, so its true
    end is unobserved. That holds for an analog year and for the current one
    alike, which makes "1 open against 1 open" a fair comparison rather than
    an artifact.
    """
    if cutoff_mmdd is not None:
        events = [e for e in events if (e.get("start") or "")[5:] <= cutoff_mmdd]
    open_n = sum(1 for e in events
                 if e.get("ongoing") or e.get("provisional_short"))
    return len(events), len(events) - open_n, open_n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--snapshot", metavar="YYYY-MM-DD",
                    help="read a committed snapshot instead of .fetch_cache")
    ap.add_argument("--dates", help="comma-separated ISO dates to show")
    ap.add_argument("--weeks", type=int, default=5,
                    help="how many weekly rows when --dates is absent (default 5)")
    a = ap.parse_args()

    d = load_from_snapshot(a.snapshot) if a.snapshot else load_from_cache()
    series, analogs = d["series"], d["analogs"]
    years = sorted(y for y in analogs if y != CURRENT_YEAR)
    last_iso = series[-1][0]
    dates = pick_dates(series, a.dates.split(",") if a.dates else None, a.weeks)
    by_iso = {iso: v for iso, v in series}

    print(f"CWWA matched-date comparison, {CURRENT_YEAR} against analog years")
    print(f"source: {d['origin']}  (issued {d['issued']})")
    print()
    print(f"  LAST OBSERVATION: {last_iso}")
    print("  Every ratio below is at the same calendar date in both years.")
    print("  ERA5 runs about six days behind, so this is NOT the issue date.")
    print()

    head = f"  {'date':<12}{CURRENT_YEAR:>9}"
    for y in years:
        head += f"{y:>9}{'%':>6}"
    print(head)
    print("  " + "-" * (len(head) - 2))

    missing = []
    for iso in dates:
        cur = by_iso.get(iso)
        if cur is None:
            missing.append(f"{iso} (no {CURRENT_YEAR} observation)")
            continue
        row = f"  {iso:<12}{cur:9.1f}"
        for y in years:
            av = value_at(analogs[y], iso[5:])
            if av is None or av == 0:
                row += f"{'n/a':>9}{'':>6}"
                missing.append(f"{iso} in {y}")
            else:
                row += f"{av:9.1f}{100 * cur / av:5.0f}%"
        print(row)

    if d["events"]:
        cut = last_iso[5:]
        print()
        print(f"  Westerly wind bursts, all counts truncated at {cut}")
        print()
        t, c, o = burst_split(d["events"])
        note = f"({c} closed, {o} ongoing)" if o else f"({c} closed)"
        print(f"    {CURRENT_YEAR}    {t:>2}   {note}")
        for y in years:
            ev = d["event_analogs"].get(y) or []
            if not ev:
                continue
            t2, c2, o2 = burst_split(ev, cut)
            bits = [f"{c2} closed"] + ([f"{o2} open"] if o2 else [])
            hz = horizon_of(ev)
            if len(ev) != t2:
                bits.append(f"{len(ev)} by {hz}, its data horizon")
            print(f"    {y}    {t2:>2}   ({', '.join(bits)})")
        if o:
            print()
            print(f"    WARNING: {o} of {CURRENT_YEAR}'s bursts is still open. It ends")
            print("    where the observations end, not where the burst ended. Do not")
            print(f"    quote '{t}' against a closed analog count without saying so.")
        print()
        print("    An event is counted in a year if it STARTED on or before the")
        print("    cutoff, so a burst spanning the cutoff counts.")

    if missing:
        print()
        print("  NO CALENDAR MATCH (reported, not substituted):")
        for m in missing:
            print(f"    {m}")

    cur_last = by_iso[last_iso]
    print()
    print("  Safe to write (super-event peers only):")
    for y in SUPER_PEERS:
        if y not in analogs:
            continue
        av = value_at(analogs[y], last_iso[5:])
        if av:
            print(f"    {100 * cur_last / av:.0f}% of {y}'s at {last_iso}")
    skipped = [y for y in years if y in NON_EVENT_REFERENCES]
    if skipped:
        print()
        print(f"    Withheld: {', '.join(skipped)}. Non-event reference years with")
        print("    near-zero CWWA. The ratio is arithmetically fine and editorially")
        print("    meaningless; it belongs in the table above, not in a sentence.")


if __name__ == "__main__":
    main()
