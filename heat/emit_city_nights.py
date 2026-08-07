"""Emit the channel payload design renders the heat pages from.

D-030 seam. Reads ONLY heat/data/city_series.json, which is derived from the
published sources. ECA&D is gone from the pipeline: it is non-commercial and
cannot be published, and both countries were quietly reading it.

FOUR THINGS THIS PAYLOAD ENFORCES RATHER THAN REQUESTS.

`requires_series: true` on every rank. A bare "1st of 105" is an alarm; the
same rank beside 104 ordinary years is a calibrated statement.

`headline_requires_baseline: true` on the record count. "Eight of fifteen at a
record" is unreadable alone: a typical year gives none, but 2003 gave twelve.

`may_not_say` as an explicit field. 2026 is not the worst year on this
measure and no page may imply it is.

The day multiple is ABSENT where its baseline is short, not flagged. Design's
improvement on product's ruling: a field that does not exist cannot be leaked
by a renderer, nor reinstated by a future chat reading a flag as an oversight.

SLOT ACCOUNTING, product 2026-08-07, so a consumer can tell a GAP from an END:

    expected_slots  the station's record span, from the SOURCE
    due_slots       how many could exist as of the cut
    values          what we have
    unusable_slots  observed, computed, too thin to rank. NOT a gap
    gap_slots       no record at all. This is the one to draw

`expected_slots` is never derived from the emitted series. Deriving it that
way is the Barcelona failure the field exists to prevent: a denominator taken
from the data under test cannot detect truncation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "heat" / "data" / "city_series.json"
OUT = ROOT / "heat" / "data" / "city_nights.json"

FEATURED = ("Paris", "Madrid", "Bilbao")

LICENCE = {
    "ES": {"licence": "AEMET legal notice: reuse for commercial and "
                      "non-commercial purposes",
           "commercial_use": True, "attribution": "Source: AEMET",
           "lag_days": 3},
    "FR": {"licence": "Licence Ouverte / Open Licence 2.0",
           "commercial_use": True, "attribution": "Source: Meteo-France",
           "lag_days": 2},
}


def runs(years):
    ys = sorted(years)
    out, start, prev = [], ys[0], ys[0]
    for y in ys[1:]:
        if y != prev + 1:
            out.append([start, prev])
            start = y
        prev = y
    out.append([start, prev])
    return out


def rank_of(value, series, ties_against=True):
    """rank = 1 + prior years at or above. A TIE IS NOT A RECORD.

    Resolving ambiguity toward the more alarming reading is the D-043 defect.
    Three cities tie 2026, so a strict greater-than would manufacture a record
    for Valencia on a 59-59 tie and take the headline from 8 to 9.
    """
    if ties_against:
        return sum(1 for x in series.values() if x >= value) + 1
    return sum(1 for x in series.values() if x > value) + 1


def main() -> int:
    S = json.loads(SERIES.read_text())
    B = json.loads((ROOT / "heat/data/record_rate_baseline.json").read_text())
    ties = S["tie_rule"]["ties_count_against_current_year"]

    cities = {}
    for c, v in S["cities"].items():
        yrs = v["years"]
        cur = str(max(int(y) for y in yrs))
        good = {int(y): d for y, d in yrs.items()
                if d["usable_to_cut"] and int(y) < int(cur)}
        todate = {y: d["nights_to_cut"] for y, d in good.items()}
        n26 = yrs[cur]["nights_to_cut"]
        r = rank_of(n26, todate, ties)
        of_years = len(todate) + 1
        present = sorted(int(y) for y in yrs if int(y) < int(cur))
        unusable = sorted(y for y in present if y not in good)
        expected = present[-1] - present[0] + 1
        below = [n for n in todate.values() if n < n26]

        entry = {
            "country": v["country"], "station": v["station"],
            "source": {"who": v["source"], **LICENCE[v["country"]]},
            "record_from": v["record_from"], "record_to": v["record_to"],
            "nights_2026": n26,
            "counted_to": v["counted_to"],
            "last_observation": v["last_observation"],
            "date_note":
                "counted_to is the cut every year in the series is measured "
                "to. last_observation is how far the source now reaches. "
                "Advancing the cut is a substantive change, not a refresh.",
            "rank": {
                "value": r, "of_years": of_years,
                "percentile": round((1 - (r - 1) / of_years) * 100, 1),
                "ties_count_against": ties,
                "tied_with": sorted(y for y, n in todate.items() if n == n26),
                "tie_note":
                    "A TIE IS NOT A RECORD. rank counts prior years at or "
                    "above 2026, so a tied year keeps 2026 off first place. "
                    "Recomputing with a strict greater-than gives a different "
                    "and more alarming answer; do not recompute.",
                "requires_series": True,
                "requires_series_note":
                    "This rank may not be rendered without the series below "
                    "it. A bare rank is an alarm; the same rank beside its "
                    "ordinary years is a calibrated statement.",
                "matched_to_same_date": True,
            },
            "series_to_same_date": {
                "cut_at": v["counted_to"][5:],
                "cut_note":
                    "Every year counted to this calendar day. NOT comparable "
                    "to a figure cut at a different day, and cities from "
                    "different countries have different cuts because the "
                    "publication lag differs, so a cross-city ranking cannot "
                    "use a single one.",
                "values": {str(y): n for y, n in sorted(todate.items())},
                "expected_slots": expected,
                "due_slots": expected,
                "due_note": "Equal to expected_slots: an annual series, every "
                            "prior year already due.",
                "first_slot": present[0], "last_slot": present[-1],
                "unit": "year",
                "slot_basis":
                    "Span of the station record as held by the published "
                    "source. Taken BEFORE any completeness filter and never "
                    "from the emitted series.",
                "values_present": len(todate),
                "unusable_slots": unusable,
                "unusable_note":
                    "Observed and computed, but below the completeness bar of "
                    "{0:.0%} of days from 1 May to the cut. OBSERVED BUT NOT "
                    "USABLE, which is not absent. Must not be drawn as a "
                    "gap.".format(S["completeness"]["bar"]),
                "gap_slots": expected - len(todate) - len(unusable),
                "gap_note": "Slots with no record at all. This is the one to "
                            "draw.",
                "present_runs": runs(present),
            },
            "record_margin_nights": (n26 - max(below)) if r == 1 and below else None,
            "featured": c in FEATURED,
        }

        days = {
            "thresholds_c": v["thresholds_c"],
            "threshold_basis": v["threshold_basis"],
            "days_2026": yrs[cur]["days_to_cut"],
            "counts_per_year": v["day_counts"],
            "counts_window": {"recent": "2011-2025", "early": "1961-1990"},
            "multiple_available": v["day_counts_comparable"],
        }
        if not v["day_counts_comparable"]:
            days["multiple_withheld_note"] = v["day_counts_note"]
        entry["days"] = days

        if c in FEATURED:
            full = {y: d for y, d in yrs.items() if d["usable_full_year"]}
            entry["full_year_series"] = {
                y: d["nights_full_year"] for y, d in sorted(full.items())}
            entry["warmest_night_c"] = {
                y: d["warmest_night_c"] for y, d in sorted(full.items())
                if "warmest_night_c" in d}
            entry["full_year_series_note"] = (
                "Counted over whole years, so its completeness bar is "
                "stricter than the to-date series and it holds fewer years. "
                "The two are not interchangeable and must not share an axis.")
        cities[c] = entry

    recs = sorted(c for c, v in cities.items() if v["rank"]["value"] == 1)
    top5 = [c for c, v in cities.items() if v["rank"]["percentile"] >= 95]
    top10 = [c for c, v in cities.items() if v["rank"]["percentile"] >= 90]
    thin = [c for c, v in cities.items() if v.get("record_margin_nights") == 1]
    nomult = sorted(c for c, v in cities.items()
                    if not v["days"]["multiple_available"])

    payload = {
        "_readme":
            "Nights that never fall below 20 C, and days above each city's "
            "own extreme-heat thresholds, per European city, each against its "
            "own record. One thermometer per city, nights and days from the "
            "same rows of the same record. City warming included. Not a "
            "climate measurement and never presented as one.",
        "channel": "heat", "evidence_basis": "Measured",
        "attribution": "Not ENSO-linked",
        "definition": {
            "name": "Tropical night",
            "rule": "daily minimum temperature at or above 20.0 C",
            "standard": "ETCCDI index TR, as published by European met "
                        "services. Not a threshold we chose.",
        },
        "day_definition": {
            "rule": "daily maximum at or above this station's own 90th, 95th "
                    "and 99th percentile of July-August maxima, 1971-2000",
            "standard_es":
                "AEMET's own published rule. Verified by reproducing their "
                "published Madrid 36.4 C and Seville 41.2 C exactly.",
            "standard_fr":
                "THE SAME METHOD, NOT A PUBLISHED FRENCH RULE. Meteo-France "
                "publishes no percentile equivalent, so the French thresholds "
                "are our application of AEMET's method to French stations. "
                "Defensible, and NOT the same evidential standing. The phrase "
                "'AEMET's own rule, not ours' must not be copied across.",
            "why_not_35c":
                "A flat 35 C is not a standard and is not usable across "
                "cities: measured 2011-2025 it gives 0.5 days a year in "
                "Barcelona and 66.8 in Seville.",
        },
        "headline": {
            "lead": {
                "claim": "Not one of these cities is having an ordinary "
                         "summer for hot nights.",
                "in_top_10pct": len(top10), "in_top_5pct": len(top5),
                "of_cities": len(cities),
            },
            "records": len(recs), "of_cities": len(cities),
            "record_cities": recs,
            "headline_requires_baseline": True,
            "baseline": {
                "typical_year_records": B["median_year"],
                "mean_2011_2025": B["mean_2011_2025"],
                "expected_no_trend": B["expected_no_trend"],
                "worst_year_on_record": {"year": 2003, "records": 12},
            },
            "may_not_say": B["may_not_say"],
            "the_better_story": B["the_better_story"],
            "fragile_members": thin,
            "fragile_note":
                "A record held by a single night. Carries its margin rather "
                "than hiding it.",
            "caveat": B["caveat_2026_incomplete"],
        },
        "featured_cities": list(FEATURED),
        "cities_without_day_multiple": nomult,
        "cities_without_day_multiple_note":
            "These stations opened after 1961, so their 1961-1990 baseline is "
            "part-length and drawn from the warmer end of the period. The "
            "multiple is NOT EMITTED rather than flagged, so it cannot be "
            "rendered or reinstated. Their recent rate stands on a complete "
            "window and is emitted.",
        "cities": cities,
        "sources_note":
            "Every published figure comes from a national met service that "
            "permits commercial reuse. ECA&D is not read anywhere in this "
            "pipeline.",
        "coverage_note":
            "Spain and France. The night metric does not work in northern "
            "Europe, where tropical nights are near zero and ratios divide by "
            "almost nothing.",
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out}")
    print(f"  {len(cities)} cities, {len(recs)} at record: {recs}")
    print(f"  no day multiple: {nomult}")
    print(f"  fragile (1-night margin): {thin}")
    bad = [c for c, v in cities.items()
           if v["series_to_same_date"]["gap_slots"] < 0]
    print(f"  slot arithmetic consistent: {not bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
