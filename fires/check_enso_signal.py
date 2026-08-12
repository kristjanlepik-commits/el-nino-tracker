"""Does Indonesian fire track ENSO across the record, or only at extremes?

WHY THIS EXISTS. Indonesia hit a same-week record on 2026-08-05..08-11,
inside its declared Aug-Oct ENSO window and in the R5 region the literature
predicts. Aftereffects raised a counter-example from this channel's own
data, and it was a good one:

    In the same week, the 2015-16 super El Nino recorded 11,893. The
    standing record, 18,075, was set in neutral 2012.

Read at face value that says a record Indonesian fire week does not require
a super El Nino, which is a real constraint on how loudly the teleconnection
can be claimed. It is also true.

=============================================================================
AND IT DOES NOT GENERALISE. THE WINDOW WAS THE WRONG UNIT.
=============================================================================

Aftereffects attached a caveat and did not drop it: one calendar week is
not a season, and the seasonal test is the real version. That caveat
carried the entire result.

Integrated over the whole Aug-Oct season, the ordering reverses:

                    this calendar week        whole Aug-Oct season
    2012 neutral        18,075  rank 1            188,690  rank 3
    2015 el_nino        11,893  rank 4            656,242  rank 1

    2015 as a multiple of 2012:   week 0.66x          season 3.48x

2015's season is 2.2x the next highest in the series. It was overwhelmingly
the largest fire season on record; it simply did not peak in the particular
calendar week that happens to be current.

So the counter-example is an artefact of a seven-day window, and the
weaker conclusion would have understated the teleconnection at exactly the
moment the season begins.

=============================================================================
WHAT THE RECORD ACTUALLY SAYS
=============================================================================

Classification is NOT this channel's. It comes from data/enso_events.csv,
derived by the aftereffects desk from CPC's full ONI series by applying
CPC's published rule mechanically: five or more consecutive overlapping
seasons beyond +/-0.5, banded on the peak. No per-event judgement, per
D-033. This module reads those labels and does not second-guess them.

    Aug-Oct integrated     el_nino  n=4  median 225,645  max 656,242
                           neutral  n=6  median  53,336  max 188,690
                           la_nina  n=3  median  41,617  max  45,259

    El Nino season ranks    1, 2, 4, 5   of 13
    La Nina season ranks    10, 11, 12
    permutation p = 0.0127  (20,000 shuffles of the ENSO labels)

At week scale the same test gives El Nino at ranks 2, 3, 4, 5 and p =
0.027, so the signal is present either way and is cleaner and larger
seasonally.

THE SENTENCE THIS SUPPORTS: El Nino lifts the whole distribution of
Indonesian fire and La Nina suppresses it, and at seasonal scale it also
holds the record. The sentence it does NOT support is that any single week
tells you which phase you are in.

=============================================================================
CAVEATS THAT TRAVEL WITH IT
=============================================================================

n = 13 seasons, of which four are El Nino and three La Nina. That is a
small sample and the permutation test is doing real work; treat p = 0.0127
as evidence rather than as settled.

One country. Indonesia is the strongest ENSO fire teleconnection there is,
so this says nothing about the other 93.

THE OBSERVABILITY ALTERNATIVE, RAISED AND THEN CLOSED. Detections are an
observability-limited instrument, this channel has measured that cloud
suppresses them (check_observability.cloud_test), and ENSO changes cloud.
So an apparent ENSO FIRE signal could have been an ENSO OBSERVABILITY
signal: drier El Nino conditions, clearer skies, more detections at the
same amount of fire.

Run on BURNT AREA instead, which is a scar mapped after the fact and is not
blinded the same way, the signal holds and the two instruments agree
closely:

    burnt area, Aug-Oct   el_nino  n=4  median 4,101,728 ha  ranks 1,3,5,6
                          neutral  n=7  median   739,746 ha
                          la_nina  n=3  median   593,608 ha  ranks 9,11,13
                          permutation p = 0.0424

    2015 against 2012     3.40x on burnt area, 3.48x on hotspots

Two instruments with different failure modes giving the same ratio is what
makes this a fire signal rather than a seeing signal. `burnt_area_seasons`
below runs it.

A TRAP IN THE CLASSIFICATION, worth knowing before using enso_events.csv
anywhere. A year absent from the file reads as "neutral" by DEFAULT, not by
classification. 2026 is absent, because the current event has not been
closed out under the five-consecutive-season rule, so it silently labels
as neutral. Any test that includes the current year will therefore file the
event we are living through as a non-event. This module excludes 2026 for
that reason AND because its Aug-Oct season is still running.

Also excluded: 2014 carries only 10 days of Aug-Oct detection coverage, and
2022 carries 82 of 92. Restricting to seasons with 90+ days changes
nothing (ranks identical, p 0.0127 against 0.0124), which is the check
worth having rather than the assurance.
"""
from __future__ import annotations

import csv
import io
import json
import os
import random
import statistics as st

HERE = os.path.dirname(__file__)
REPO = os.path.dirname(HERE)
EVENTS = os.path.join(REPO, "data", "enso_events.csv")
FULL_HISTORY = os.path.join(HERE, "data", "full_history")

SEASON_MONTHS = ("08", "09", "10")
MIN_SEASON_DAYS = 80          # near-complete Aug-Oct coverage
SHUFFLES = 20000
SEASON_START_WEEK = 30        # cumulative burnt area at end of July
SEASON_END_WEEK = 44          # and at end of October
# A year absent from enso_events.csv reads as neutral by DEFAULT rather than
# by classification, so including the current year would file the event we
# are living through as a non-event. Its season is also still running.
CURRENT_YEAR_EXCLUDED = 2026


def enso_phase_by_year() -> dict[int, str]:
    """develop_year..peak_year -> phase, from the desk that owns the labels."""
    with open(EVENTS) as handle:
        rows = [line for line in handle if not line.startswith("#")]
    span: dict[int, str] = {}
    for event in csv.DictReader(io.StringIO("".join(rows))):
        for year in range(int(event["develop_year"]), int(event["peak_year"]) + 1):
            span[year] = event["type"]
    return span


def seasons(iso: str) -> list[tuple[str, int, str]]:
    """(year, Aug-Oct detection total, phase) for near-complete seasons."""
    path = os.path.join(FULL_HISTORY, f"{iso}.json")
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        detections = json.load(handle)
    phase = enso_phase_by_year()
    out = []
    for year in sorted(y for y in detections.get("_complete", [])
                       if len(detections.get(y, {})) >= 300):
        days = [(day, count) for day, count in detections[year].items()
                if day[5:7] in SEASON_MONTHS]
        if len(days) < MIN_SEASON_DAYS:
            continue
        out.append((year, sum(c for _d, c in days),
                    phase.get(int(year), "neutral")))
    return out


def burnt_area_seasons(iso: str = "IDN") -> list[tuple[str, float, str]]:
    """(year, Aug-Oct burnt hectares, phase) from the OTHER instrument.

    The point of running this is that burnt area fails differently from
    detections. A detection needs a clear view at the moment of overpass; a
    scar persists and is mapped later. If ENSO were only changing how well
    we SEE fire, this series would not carry the signal.

    2026 excluded: incomplete season, and it would silently label neutral.
    """
    path = os.path.join(HERE, "data", "area_history", f"{iso}.json")
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        years = json.load(handle)["years"]
    phase = enso_phase_by_year()
    out = []
    for year in sorted(years):
        if int(year) >= CURRENT_YEAR_EXCLUDED:
            continue
        weekly = {int(k): v for k, v in years[year].items() if v is not None}
        if not weekly:
            continue

        def cumulative_at(week, series=weekly):
            keys = [k for k in series if k <= week]
            return series[max(keys)] if keys else 0.0

        if not cumulative_at(SEASON_END_WEEK):
            continue
        out.append((year,
                    cumulative_at(SEASON_END_WEEK) - cumulative_at(SEASON_START_WEEK),
                    phase.get(int(year), "neutral")))
    return out


def permutation_p(values: list[int], labels: list[str], seed: int = 3) -> float:
    """P(El Nino median minus La Nina median this large | labels shuffled)."""
    def gap(assigned):
        a = [v for v, t in zip(values, assigned) if t == "el_nino"]
        b = [v for v, t in zip(values, assigned) if t == "la_nina"]
        return (st.median(a) - st.median(b)) if a and b else 0.0

    observed = gap(labels)
    rng = random.Random(seed)
    hits = 0
    for _ in range(SHUFFLES):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        if gap(shuffled) >= observed:
            hits += 1
    return hits / SHUFFLES


def report(iso: str = "IDN") -> None:
    rows = seasons(iso)
    if not rows:
        print(f"No near-complete Aug-Oct seasons cached for {iso}.")
        return

    print(f"{iso}, Aug-Oct integrated detections by ENSO phase\n")
    for year, total, phase in rows:
        print(f"   {year}  {total:>9,}  {phase}")

    groups: dict[str, list[int]] = {}
    for _y, total, phase in rows:
        groups.setdefault(phase, []).append(total)
    print()
    for phase in ("el_nino", "neutral", "la_nina"):
        if phase in groups:
            values = groups[phase]
            print(f"  {phase:<9} n={len(values):<3} median {st.median(values):>10,.0f}"
                  f"  max {max(values):>10,}")

    order = sorted(rows, key=lambda r: -r[1])
    rank = {year: i + 1 for i, (year, _t, _p) in enumerate(order)}
    for phase in ("el_nino", "la_nina"):
        ranks = sorted(rank[y] for y, _t, p in rows if p == phase)
        print(f"\n  {phase} season ranks (1 = largest of {len(rows)}): {ranks}")

    p = permutation_p([t for _y, t, _p in rows], [p for _y, _t, p in rows])
    print(f"\n  permutation p = {p:.4f} ({SHUFFLES:,} label shuffles)")
    print("\n  Hotspots, not burnt area. ENSO changes cloud and cloud changes")
    print("  detections, so part of this could be an observability signal")
    print("  rather than a fire signal. See the module docstring.")


if __name__ == "__main__":
    report()
