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

A TRAP IN THE CLASSIFICATION, HIT HERE AND SINCE FIXED AT SOURCE. The
original `enso_events.csv` was event-indexed, so a year absent from it read
as "neutral" by DEFAULT rather than by classification. 2026 is absent,
because the CPC rule needs five consecutive seasons and the current run is
two, so the event we are living through silently classified as a non-event
AND dragged the neutral baseline down while doing it. The first burnt-area
run here did exactly that, and nothing flagged it; it was caught because a
number looked too small.

Aftereffects fixed the interface rather than documenting around it.
`data/enso_year_status.csv` now carries every year 1950 to present with an
explicit type of el_nino, la_nina, neutral or UNDECIDED, plus a reason
separating closed from series_incomplete. A missing year is now a bug
rather than a signal, and the live event is visible as in progress instead
of invisible.

This module reads that file and excludes years by their DECLARED STATE
rather than by hardcoding 2026, which would go stale the moment the run
closes. That distinction is the same one that bit this channel three times
in a day: a denominator, a record span and a window count all asserted
where they should have been derived.

WHAT THE UNDECIDED STATE DOES NOT DO, per aftereffects and worth repeating
before anyone leans on this: it does not make 2026 classifiable. Any test
wanting the current event in it has to make a judgement their file
deliberately declines to make. Take that from the brief's forecast
probabilities with their issue date, labelled as FORECAST rather than as
state, and never joined to this column.

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
YEAR_STATUS = os.path.join(REPO, "data", "enso_year_status.csv")
FULL_HISTORY = os.path.join(HERE, "data", "full_history")

SEASON_MONTHS = ("08", "09", "10")
MIN_SEASON_DAYS = 80          # near-complete Aug-Oct coverage
SHUFFLES = 20000
SEASON_START_WEEK = 30        # cumulative burnt area at end of July
SEASON_END_WEEK = 44          # and at end of October
# Phases a year must NOT be in to enter the test. "undecided" is a real
# state, not a missing value: the CPC rule needs five consecutive seasons
# and the current event's run is shorter, so it cannot be classified yet.
# Read it rather than hardcoding a year, which would go stale the moment
# the run closes.
EXCLUDED_PHASES = {"undecided"}


def enso_phase_by_year() -> dict[int, str]:
    """year -> phase, from the desk that owns the labels. Never inferred.

    Reads data/enso_year_status.csv, which carries EVERY year and an
    explicit "undecided" for years the CPC five-season rule cannot yet
    decide. The earlier event-indexed file could not express that: a year
    absent from it read as "neutral", so the event currently in progress
    silently classified as a non-event and dragged the neutral baseline
    down. Aftereffects fixed the interface after this channel hit it.

    A year missing from the file is now a bug rather than a signal, so this
    does not default.
    """
    with open(YEAR_STATUS) as handle:
        rows = [line for line in handle if not line.startswith("#")]
    return {int(r["year"]): r["type"]
            for r in csv.DictReader(io.StringIO("".join(rows)))}


def seasons(iso: str) -> list[tuple[str, int, str]]:
    """(year, Aug-Oct detection total, phase) for near-complete seasons.

    Years whose ENSO state is undecided are excluded, same as the burnt-area
    version. Today the season-length filter would drop 2026 anyway, since
    its year is not complete, so this is belt over braces. It is here
    because those two filters answer different questions and will come
    apart: a year can be complete and still unclassifiable, which is
    exactly what next January looks like.
    """
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
        state = phase.get(int(year), "undecided")
        if state in EXCLUDED_PHASES:
            continue
        out.append((year, sum(c for _d, c in days), state))
    return out


def burnt_area_seasons(iso: str = "IDN") -> list[tuple[str, float, str]]:
    """(year, Aug-Oct burnt hectares, phase) from the OTHER instrument.

    The point of running this is that burnt area fails differently from
    detections. A detection needs a clear view at the moment of overpass; a
    scar persists and is mapped later. If ENSO were only changing how well
    we SEE fire, this series would not carry the signal.

    Years the classifier calls "undecided" are excluded, which currently
    means 2026: its season is also still running, but the exclusion is on
    the declared state rather than on the date.
    """
    path = os.path.join(HERE, "data", "area_history", f"{iso}.json")
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        years = json.load(handle)["years"]
    phase = enso_phase_by_year()
    out = []
    for year in sorted(years):
        if phase.get(int(year), "undecided") in EXCLUDED_PHASES:
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
    print("\n  These are hotspots, which cloud can suppress, and ENSO moves")
    print("  cloud. That alternative is CLOSED rather than open: run")
    print("  burnt_area_seasons() for the scar-based instrument, which")
    print("  gives 3.40x for 2015 against 2012 where hotspots give 3.48x.")
    print("  Two instruments, different failure modes, same ratio.")


if __name__ == "__main__":
    report()
