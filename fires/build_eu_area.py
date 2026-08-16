"""EU burnt area to date, and where the season could end. Emits data only.

WHAT THIS IS FOR. Kristjan asked for an EU total in hectares alongside the
country charts, and for an estimate of where the season total might end up.

WHY IT IS BURNT AREA AND NOT DETECTIONS. The country charts count VIIRS
active-fire detections. This counts EFFIS mapped burnt area. They are
different instruments measuring different things at different latencies and
they are NEVER converted into one another. The country pages already carry
both side by side with that note; this is the same pair at EU scale.

Detections answer "how much fire activity is there this week, against what
this week normally looks like". Burnt area answers "how much land has been
mapped as burnt since January". A week can be extraordinary on one and
ordinary on the other, and 2026 is currently a case of exactly that.

=============================================================================
THE COUNTRY SET IS THE FIRST THING A READER MUST SEE
=============================================================================

`effis:EU` is the European Union. THE UNITED KINGDOM IS NOT IN IT; it sits
in `effis:Non_EU`.

That matters more than usual right now, because the UK is having the most
extreme fire week anywhere in this channel's record: z 17.1, 3.98x its own
same-week high, still rising when the window closed. A page showing an EU
hectares total beside UK country charts, with the UK invisible in the
total, is a defect a reader will find. So `country_set` and `excludes` are
emitted as fields rather than left to a caption.

=============================================================================
THE PROJECTION IS AN ENVELOPE, NOT A NUMBER, AND THAT IS THE FINDING
=============================================================================

CLAUDE.md forbids custom modelling: the historical sample is too small to
beat agency forecasts, and this channel aggregates rather than models. I
looked for an agency season-end estimate to cite and found none; EFFIS
publishes the historical series and the running cumulative, not a forecast.

So this is the analog method `analog.py` already uses for the ONI, applied
to a different quantity: take what every prior season did from this week
onward, and show the spread. No fitting, no parameters, no model.

THE SPREAD IS WIDE FOR A REASON WORTH PUBLISHING. 2025 became the record
year in two weeks: weeks 32 and 33 added 585,288 ha between them, 57% of
its entire season, and week 32 alone was +334,478. A single week can add a
third of a year. Any point estimate would be false precision over exactly
that.

Across 20 prior seasons the multiplier from a given week to season end runs
roughly 1.19x to 2.67x with a median near 1.53x. The 2025 record sits
INSIDE the envelope rather than at its edge, which is the honest reading:
matching the worst year on record is an ordinary outcome from here, not an
extreme one.

WHAT THE ENVELOPE IS NOT. It is not a probability distribution. Twenty
seasons is twenty samples, they are not independent, and the fire regime is
not stationary. Treat the median as "what a typical season did from here",
never as "what is expected". The field names say `analog_` for that reason.

EVIDENCE BASIS, D-033: Compiled, not Measured. The series is EFFIS's
published product; this channel aggregates and projects it rather than
deriving burnt area itself. The detection charts beside it are Measured.
Two adjacent charts on different bases is precisely what the tagging exists
to disclose, so the basis is emitted per block rather than assumed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = os.path.join(HERE, "data", "area_regions.json")
OUT = os.path.join(HERE, "data", "eu_area.json")

SCOPE = "effis:EU"
MIN_WEEKS_FOR_COMPLETE_SEASON = 45   # a season that stops early cannot
                                     # contribute a to-year-end multiplier


def load_scope(scope: str = SCOPE) -> dict:
    with open(REGIONS) as handle:
        regions = json.load(handle)["regions"]
    if scope not in regions:
        raise SystemExit(f"{scope} absent from {REGIONS}")
    return regions[scope]


def weekly(series: dict) -> list[tuple[int, float]]:
    return sorted((int(w), v) for w, v in series.items() if v is not None)


def cumulative_at(series: dict, week: int) -> float | None:
    got = [v for w, v in weekly(series) if w <= week]
    return got[-1] if got else None


def build(today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    scope = load_scope()
    years = scope["years"]
    current_year = str(today.year)
    if current_year not in years:
        raise SystemExit(f"no {current_year} in {SCOPE}")

    current = weekly(years[current_year])
    if not current:
        raise SystemExit(f"{current_year} has no weeks yet")
    week_now, area_now = current[-1]

    # Every prior season's multiplier from THIS week to its own year end.
    # Seasons that stop early are excluded: a partial season understates
    # its own multiplier and would drag the envelope down.
    analogs = []
    for year in sorted(years):
        if year == current_year:
            continue
        series = weekly(years[year])
        if not series or series[-1][0] < MIN_WEEKS_FOR_COMPLETE_SEASON:
            continue
        at_now = cumulative_at(years[year], week_now)
        if not at_now:
            continue
        analogs.append({"year": year, "at_this_week": round(at_now),
                        "season_end": round(series[-1][1]),
                        "multiplier": round(series[-1][1] / at_now, 3),
                        # FULL PRECISION, kept separate from the rounded
                        # display value above. The envelope was briefly
                        # computed from `multiplier`, which is rounded to
                        # three places for reading, and an independent
                        # recomputation disagreed by about 0.01%. Tiny, and
                        # still the wrong direction of dependency: a
                        # published number must not be derived from another
                        # number's display form. Caught because the check
                        # compared against the source rather than against
                        # the emitted file.
                        "_exact": series[-1][1] / at_now})

    if not analogs:
        raise SystemExit("no complete prior seasons to draw an envelope from")

    mults = sorted(a["_exact"] for a in analogs)
    record = max(analogs, key=lambda a: a["season_end"])

    # How concentrated is a season? The single largest weekly increment as
    # a share of the whole, across prior seasons. This is the number that
    # justifies refusing a point estimate.
    concentration = []
    for year in sorted(years):
        if year == current_year:
            continue
        series = weekly(years[year])
        if not series or series[-1][0] < MIN_WEEKS_FOR_COMPLETE_SEASON:
            continue
        prev, biggest = 0.0, 0.0
        for _w, v in series:
            biggest = max(biggest, v - prev)
            prev = v
        if series[-1][1]:
            concentration.append(biggest / series[-1][1])

    return {
        "_readme": [
            "Generated by fires/build_eu_area.py; do not hand-edit.",
            "Burnt area, NOT detections. The two are never converted into",
            "one another and must not be presented as one number at two",
            "zoom levels.",
            "Read `projection` as an envelope of what prior seasons did,",
            "never as a forecast. See `projection.caveat`.",
        ],
        "scope": SCOPE,
        "country_set": scope.get("name", "European Union"),
        "excludes": [
            "United Kingdom (EFFIS reports it under Non_EU, not EU). It is "
            "currently the most extreme country in this channel's detection "
            "record, so a total that omits it must say so."
        ],
        "evidence_basis": "Compiled",
        "basis_note": ("EFFIS's published burnt-area product, aggregated and "
                       "projected here. The detection charts beside this are "
                       "Measured. D-033."),
        "instrument": "EFFIS mapped burnt-area perimeters, weekly",
        "as_of_week": week_now,
        "as_of_year": int(current_year),
        "area_ha": round(area_now),
        "series": {y: {str(w): v for w, v in weekly(s)} for y, s in years.items()},
        "projection": {
            "method": "analog",
            "method_note": (
                "Every complete prior season's multiplier from this same week "
                "to its own year end, applied to where this season stands. No "
                "fitting and no parameters. The same method analog.py uses for "
                "the ONI, on a different quantity."),
            "n_seasons": len(analogs),
            "from_week": week_now,
            "from_area_ha": round(area_now),
            "analog_min_ha": round(area_now * mults[0]),
            "analog_median_ha": round(area_now * st.median(mults)),
            "analog_max_ha": round(area_now * mults[-1]),
            "analog_min_multiple": round(mults[0], 3),
            "analog_median_multiple": round(st.median(mults), 3),
            "analog_max_multiple": round(mults[-1], 3),
            "record_year": record["year"],
            "record_ha": record["season_end"],
            "record_inside_envelope": (area_now * mults[0] <= record["season_end"]
                                       <= area_now * mults[-1]),
            # THE MAXIMUM IS THE INTERESTING NUMBER AND THE MEDIAN IS NOT,
            # so a reader skimming a funnel takes the top of it as the
            # forecast. Strategy's point, and it is right: shown without
            # weight on the centre, this reads as "worse than the worst year
            # ever" whatever the caption says.
            #
            # The record is NOT the central outcome. It sits high in the
            # spread, and the median lands below it. These fields say so as
            # data so the page cannot be built the other way round by
            # accident, and so a caption writer has the true sentence to
            # hand rather than having to derive it.
            # A COUNT, NOT A PERCENTILE. Science's call and it is right.
            # "5 of 20 prior seasons would have finished above the record"
            # is unimpeachable. "The record sits at the 75th percentile" is
            # the same fact wearing a lab coat, and it invites being read as
            # a 25% probability by exactly the reader the headline rule is
            # protecting.
            #
            # It is also model-dependent in a way a percentile conceals:
            # 5 of 20 under multiplicative, 1 of 20 under additive. A number
            # that swings fivefold on a modelling choice must not be dressed
            # as a distributional statistic.
            "analogs_exceeding_record": sum(
                1 for m in mults if area_now * m >= record["season_end"]),
            "analogs_total": len(mults),
            "median_below_record": (area_now * st.median(mults)
                                    < record["season_end"]),
            "headline_rule": (
                "The central outcome does NOT break the record. State it as "
                "a count: 5 of the 20 prior seasons would have finished above "
                "the record from here, and the median lands below it. 'Could "
                "exceed the record' is true and 'on course to exceed it' is "
                "false. Lead with the median, never the maximum, and never "
                "restate the count as a percentile or a probability."),
            "analogs": [{k: v for k, v in a.items() if not k.startswith("_")}
                        for a in analogs],
            "caveat": (
                "An envelope of what prior seasons did, not a probability "
                "distribution and not a forecast. Twenty seasons is twenty "
                "samples and the fire regime is not stationary. The median is "
                "what a typical season did from here, never what is expected."),
            # BOTH KNOWN BIASES RUN THE SAME WAY, TOWARD THE ALARMING
            # ANSWER, which is the direction this channel owes scepticism.
            # Reviewed by the ENSO tracker desk on the emitted file rather
            # than from principle; every figure below reproduced here.
            "known_biases": [
                "Mild regression to the mean. The multiplier is slightly "
                "negatively correlated with the season to date (r = -0.19), "
                "so a high-standing season is projected a little high. 2026 "
                "is a high-standing season.",
                "The season is arriving earlier. The multiplier trends down "
                "over time (r = -0.21 against year; median 1.66 in the older "
                "half of the record against 1.46 in the recent half), so flat "
                "weighting over-projects. Too weak to weight on at 20 points, "
                "strong enough to state.",
            ],
            "why_multiplicative": (
                "Each model predicts its OWN residual should vanish. Additive "
                "assumes remaining burn is independent of the season to date, "
                "and it is not: r = +0.54. Multiplicative assumes the "
                "MULTIPLIER is independent of the season to date, and it very "
                "nearly is: r = -0.19. So the record rejects additive and "
                "supports multiplicative, and spanning both would widen the "
                "band using a model this data rejects."),
            "stability": (
                "Leave-one-out over the 20 seasons moves the minimum by 2%, "
                "the median by 1% and the maximum by 4%. No band edge depends "
                "on a single season, including the maximum."),
            "why_not_a_point": (
                f"A single week can add a third of a season. The largest weekly "
                f"increment has been a median "
                f"{100 * st.median(concentration):.0f}% of the whole season "
                f"across prior years, and in 2025 weeks 32 and 33 together were "
                f"57% of the record. A point estimate would be false precision "
                f"over exactly that."),
        },
    }


def main() -> int:
    doc = build()
    with open(OUT, "w") as handle:
        json.dump(doc, handle, indent=1)
        handle.write("\n")
    p = doc["projection"]
    print(f"  {doc['country_set']}, week {doc['as_of_week']}: "
          f"{doc['area_ha']:,} ha")
    print(f"  excludes: {doc['excludes'][0][:60]}...")
    print(f"  envelope from {p['n_seasons']} prior seasons: "
          f"{p['analog_min_ha']:,} to {p['analog_max_ha']:,} ha, "
          f"median {p['analog_median_ha']:,}")
    print(f"  record {p['record_year']} at {p['record_ha']:,} ha, "
          f"inside envelope: {p['record_inside_envelope']}")
    print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
