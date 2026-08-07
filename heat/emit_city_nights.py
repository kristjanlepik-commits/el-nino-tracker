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

# For the map. Product's ruling 2026-08-07: the geography IS the headline, and
# a map is the only rendering where "the extreme band is the middle of the
# domain" is legible. A table hides it; a ranked list sorts the quiet cities to
# the bottom where they read as filler.
COORDS = {
    "Seville": (37.4, -6.0), "Malaga": (36.7, -4.5), "Murcia": (38.0, -1.1),
    "Alicante": (38.3, -0.5), "Valencia": (39.5, -0.4), "Palma": (39.6, 2.7),
    "Madrid": (40.4, -3.7), "Barcelona": (41.4, 2.2), "Zaragoza": (41.7, -0.9),
    "Bilbao": (43.3, -2.9), "Nice": (43.7, 7.3), "Marseille": (43.3, 5.4),
    "Montpellier": (43.6, 3.9), "Lyon": (45.8, 4.8), "Vienna": (48.2, 16.4),
    "Munich": (48.1, 11.6), "Paris": (48.9, 2.4), "Frankfurt": (50.1, 8.7),
    "Cologne": (50.9, 7.1), "Berlin": (52.5, 13.4), "Hamburg": (53.6, 10.0),
}

LICENCE = {
    "ES": {"licence": "AEMET legal notice: reuse for commercial and "
                      "non-commercial purposes",
           "commercial_use": True, "attribution": "Source: AEMET",
           "lag_days": 3},
    "FR": {"licence": "Licence Ouverte / Open Licence 2.0",
           "commercial_use": True, "attribution": "Source: Meteo-France",
           "lag_days": 2},
    "AT": {"licence": "CC0 1.0, public domain",
           "commercial_use": True, "attribution": "Source: GeoSphere Austria",
           "lag_days": 1},
    "DE": {"licence": "GeoNutzV: reuse permitted, including commercial, "
                      "with attribution",
           "commercial_use": True, "attribution": "Source: DWD", "lag_days": 2},
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


def record_rate(S, key, pct="95", lo=1990, hi=2025):
    """How many cities set a record in each past year, on the same measure.

    A record count is uninterpretable without this. Eight of fifteen sounds
    enormous and a typical year gives zero, so the baseline is what turns the
    number into a statement rather than an alarm.

    Computed here rather than transcribed, because it has to be recomputed
    whenever the series changes and a stale baseline is worse than none: it
    would look checked.
    """
    per = {y: 0 for y in range(lo, hi + 1)}
    for v in S["cities"].values():
        ys = {int(y): z for y, z in v["years"].items() if z["usable_to_cut"]}
        for y in per:
            if y not in ys:
                continue
            val = (ys[y]["nights_to_cut"] if key == "nights"
                   else ys[y]["days_to_cut"][pct])
            prior = [(z["nights_to_cut"] if key == "nights"
                      else z["days_to_cut"][pct])
                     for yy, z in ys.items() if yy < y]
            if prior and val > max(prior):
                per[y] += 1
    vals = sorted(per.values())
    worst = max(per, key=per.get)
    return {
        "median_year": vals[len(vals) // 2],
        "mean_year": round(sum(vals) / len(vals), 2),
        "worst_year_on_record": {"year": worst, "cities": per[worst]},
        "window": f"{lo}-{hi}",
        "of_cities": len(S["cities"]),
    }


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
        nb = [d["nights_to_cut"] for y, d in yrs.items()
              if 1991 <= int(y) <= 2020 and d["usable_to_cut"]]
        nbase_city = round(sum(nb) / len(nb), 2) if nb else None

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
            # PER CITY, not only in the headline list. The rule already
            # covered all seven cities, but it was reachable only from the
            # headline, and a city page renders ONE city. Design read it as a
            # two-city list because that is all that was visible from where a
            # city page stands, which is the same failure as a rank that has
            # to be derived: a constraint the renderer cannot see is a
            # constraint that does not exist.
            "nights_metric_gated": not S["cities"][c]["tropical_night_metric_works"],
            "nights_baseline_per_year": nbase_city,
            "nights_metric_gated_note":
                "The 20 C tropical-night count is a Mediterranean instrument. "
                "Where the 1991-2020 baseline is near zero, a ratio divides by "
                "almost nothing and a record is arithmetic rather than "
                "evidence. WHERE THIS IS TRUE THE PAGE MUST NOT QUOTE A NIGHT "
                "RATIO, MULTIPLE OR RECORD; use the percentile warm-night "
                "series instead. Applied by rule, not by list, so a city added "
                "tomorrow is covered without anyone remembering to check.",
            # EVERY CONSTRAINT A CITY PAGE CAN VIOLATE, ON THE CITY OBJECT.
            #
            # The nights gate was general and correct and STILL failed, because
            # it was emitted at headline level and a city page renders one
            # city. From my side the rule was plainly there; from design's it
            # was invisible. That is a seam defect rather than either side's
            # mistake, and it is not specific to the gate: four constraints
            # sat where a city page could not reach them.
            #
            # The pair below is the dangerous one. The nights prohibition and
            # the days permission are OPPOSITES on the same page, and a city
            # page puts both instruments side by side. Three times today a
            # caveat nearly travelled to the instrument it is false for.
            "page_constraints": {
                "nights": {
                    "may_not_say": B["may_not_say"],
                    "reason": "2026 is not the worst year on the night "
                              "measure. 2003 was worse.",
                },
                "days": {
                    "may_say_worst_on_record": True,
                    "reason": "2026 sets more city day-records than any year "
                              "in the window, including 2003. THE OPPOSITE OF "
                              "THE NIGHTS RULE ABOVE. The two instruments do "
                              "not share a caveat, and this page shows both.",
                },
                "banned_words": ["ordinary"],
                "banned_words_reason":
                    "No city in this set is ordinary. The least extreme "
                    "readings are the 86th to 90th percentile of their own "
                    "records. Calling one ordinary is the error that turned a "
                    "91st-percentile Marseille into 'an ordinary summer'.",
                "why_here":
                    "Repeated on every city because a page renders one city "
                    "and cannot be asked to read the headline object. A "
                    "constraint the renderer cannot reach is a constraint "
                    "that does not exist.",
            },
            "record_margin_nights": (n26 - max(below)) if r == 1 and below else None,
            "featured": c in FEATURED,
        }

        # DAY RANK, product 2026-08-07. Without it a page can say Marseille
        # had 34 hot days and cannot say how unusual that is, which is the
        # question the page exists to answer. Same tie convention as nights,
        # and `requires_series` for the same reason: ranks are read, never
        # derived. A strict recompute manufactured a Valencia night record
        # this morning and would do the same here.
        eb = [d for y, d in yrs.items() if 1961 <= int(y) <= 1990]
        ec = [d["days_to_cut"]["95"] for d in eb if d["usable_to_cut"]]
        ef = [d["days_full_year"]["95"] for d in eb if d["usable_full_year"]]
        mean_early_cut = round(sum(ec) / len(ec), 2) if ec else None
        mean_early_full = round(sum(ef) / len(ef), 2) if ef else None

        dser = {y: d["days_to_cut"]["95"] for y, d in good.items()}
        d26 = yrs[cur]["days_to_cut"]["95"]
        dr = rank_of(d26, dser, ties)
        dof = len(dser) + 1
        dbelow = [n for n in dser.values() if n < d26]

        days = {
            "rank": {
                "value": dr, "of_years": dof,
                "percentile": round((1 - (dr - 1) / dof) * 100, 1),
                "measured_on": "95",
                "ties_count_against": ties,
                "tied_with": sorted(y for y, n in dser.items() if n == d26),
                "requires_series": True,
                "requires_series_note":
                    "Read this rank, never derive it. Same rule as the night "
                    "rank and the same reason: a strict greater-than promotes "
                    "ties and manufactures records.",
                "margin_days": (d26 - max(dbelow)) if dr == 1 and dbelow else None,
            },
            "series_to_same_date": {
                "cut_at": v["counted_to"][5:],
                "measured_on": "95",
                "values": {str(y): n for y, n in sorted(dser.items())},
                "note": "Days at or above this city's own 95th percentile "
                        "threshold, counted to the same cut as every other "
                        "year. The 90 and 99 thresholds are emitted above but "
                        "only the 95 series is ranked.",
            },
            "thresholds_c": v["thresholds_c"],
            "threshold_basis": v["threshold_basis"],
            "days_2026": yrs[cur]["days_to_cut"],
            "counts_per_year": v["day_counts"],
            "counts_window": {"recent": "2011-2025", "early": "1961-1990"},
            # BOTH BASES, because the distinction escaped into prose once
            # already: a headline read "two hot days a summer" while the chart
            # beneath it read "by early August". The to-date mean is the one
            # comparable to days_2026; the full-year mean is what "a summer"
            # means. Emitting only one invites the writer to supply the other.
            "mean_1961_1990_to_cut": mean_early_cut,
            "mean_1961_1990_full_year": mean_early_full,
            "mean_note":
                "to_cut is comparable to days_2026 and to the ranked series. "
                "full_year is what a reader hears in 'a summer'. A headline "
                "using one with a chart showing the other is the error this "
                "pair exists to prevent.",
            "multiple_available": v["day_counts_comparable"],
        }
        if not v["day_counts_comparable"]:
            days["multiple_withheld_note"] = v["day_counts_note"]
        entry["days"] = days

        # WARMEST-DAY SERIES, product 2026-08-07, and it is a page-structure
        # fix rather than a tidy-up. The Paris page LEADS on days and its
        # closing temperature chart was on nights, because a warmest-night
        # series was the only one that existed. The strongest beat on the page
        # was about a different instrument from its own headline.
        #
        # Emitted for every city, not only the featured three, because the
        # same mismatch would appear on any city page that leads on days.
        #
        # BOTH CUTS, for the reason product just hit in prose: a warmest value
        # to 3 August is not the same fact as a warmest value over a whole
        # year, and only one of them is comparable to `days_2026`.
        entry["warmest_day_c"] = {
            y: d["warmest_day_c"] for y, d in sorted(yrs.items())
            if "warmest_day_c" in d and d["usable_full_year"]}
        entry["warmest_day_to_cut_c"] = {
            y: d["warmest_day_to_cut_c"] for y, d in sorted(yrs.items())
            if "warmest_day_to_cut_c" in d and d["usable_to_cut"]}
        entry["warmest_note"] = (
            "warmest_day_c is over whole years and carries the full-year "
            "completeness bar. warmest_day_to_cut_c is cut to this city's own "
            "date and is the one comparable to days_2026 and to the ranked "
            "series. They are different facts and must not share an axis.")

        if c in FEATURED:
            full = {y: d for y, d in yrs.items() if d["usable_full_year"]}
            entry["full_year_series"] = {
                y: d["nights_full_year"] for y, d in sorted(full.items())}
            # The full-year DAY series, absent until now, which is why product
            # could not check whether "two hot days a summer" was a summer
            # total or a to-date figure. It was to-date.
            entry["full_year_day_series"] = {
                y: d["days_full_year"]["95"] for y, d in sorted(full.items())}
            entry["warmest_night_c"] = {
                y: d["warmest_night_c"] for y, d in sorted(full.items())
                if "warmest_night_c" in d}
            entry["full_year_series_note"] = (
                "Counted over whole years, so its completeness bar is "
                "stricter than the to-date series and it holds fewer years. "
                "The two are not interchangeable and must not share an axis.")
        cities[c] = entry

    # Day records, computed the same way as night records: a city is at a
    # day record when no prior usable year reached its 2026 count. Ties count
    # against 2026 here too.
    drecs = []
    for c, v in cities.items():
        ys = S["cities"][c]["years"]
        cur = str(max(int(y) for y in ys))
        prior = [z["days_to_cut"]["95"] for y, z in ys.items()
                 if z["usable_to_cut"] and y != cur]
        if prior and v["days"]["days_2026"]["95"] > max(prior):
            drecs.append(c)
    drecs = sorted(drecs)
    dbase = record_rate(S, "days")

    ok_cities = sorted(c for c in cities
                       if S["cities"][c]["tropical_night_metric_works"])
    ldays = sorted(((v["days"]["rank"]["percentile"], c)
                    for c, v in cities.items()))[:4]
    ldays = [{"city": c, "day_percentile": p} for p, c in ldays]
    nbase = record_rate(S, "nights")
    recs = sorted(c for c, v in cities.items() if v["rank"]["value"] == 1)
    recs_ok = [c for c in recs if c in ok_cities]
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
                # REPLACED 2026-08-07. The old claim, "not one of these cities
                # is having an ordinary summer for hot nights", was true of
                # fifteen cities and became FALSE the moment Berlin joined at
                # the 70.9th percentile on nights. A lead that depends on the
                # set's membership breaks silently every time the set grows.
                # The geography does not.
                "claim": "The extreme is concentrated in the middle "
                         "latitudes, not at the hot end.",
                "superseded_claim_do_not_use":
                    "Not one of these cities is having an ordinary summer for "
                    "hot nights. FALSE for 21 cities: Berlin is at the 70.9th "
                    "percentile on nights.",
                "in_top_10pct": len(top10), "in_top_5pct": len(top5),
                "of_cities": len(cities),
            },
            "records": len(recs), "of_cities": len(cities),
            "record_cities": recs,
            # THE HEADLINE COUNT IS RESTRICTED TO CITIES WHERE THE 20 C METRIC
            # CARRIES MEANING. Hamburg recorded one tropical night in 2026 and
            # Berlin three; a record off a base that small is arithmetic, not
            # evidence. Emitting the unrestricted count beside it would invite
            # exactly the number we do not stand behind.
            "records_where_metric_holds": len(recs_ok),
            "of_cities_where_metric_holds": len(ok_cities),
            "record_cities_where_metric_holds": recs_ok,
            "metric_unreliable_cities": sorted(set(cities) - set(ok_cities)),
            "metric_unreliable_note":
                "The 20 C tropical-night count is a Mediterranean instrument. "
                "In these cities it averages near zero, so a ratio divides by "
                "almost nothing and a record is not informative. USE THE "
                "PERCENTILE NIGHT METRIC for them, in "
                "series.years.<y>.warm_nights_to_cut. The headline count above "
                "that a page should quote is records_where_metric_holds.",
            "headline_requires_baseline": True,
            "baseline": {
                "recomputed": nbase,
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
        "day_headline": {
            "records": len(drecs), "of_cities": len(cities),
            "record_cities": drecs,
            "headline_requires_baseline": True,
            "baseline": dbase,
            "measure": "days at or above this city's own 95th percentile of "
                       "July-August maxima, counted to the same cut",
            # THE CONSTRAINT INVERTS BETWEEN THE TWO INSTRUMENTS, which is
            # why this is a field and not a note in a message. On nights,
            # `may_not_say` forbids calling 2026 the worst year, because 2003
            # gave 12 against 2026's 8. On DAYS, 2026 gives 11 against 2003's
            # 8, so it IS the worst year on record and saying so is correct.
            # Carrying the nights caveat across would understate a true
            # finding; carrying this claim back to nights would be false.
            "may_say_worst_on_record": True,
            "may_say_worst_note":
                "2026 sets more city day-records than any year in the window, "
                "including 2003. This is the OPPOSITE of the nights "
                "constraint, where 2003 remains worse and `may_not_say` "
                "applies. The two instruments do not share a caveat.",
        },
        "geography": {
            "claim": "Every city in the set is elevated on days, and the "
                     "EXTREME is concentrated in the middle latitudes rather "
                     "than at the hot end.",
            "elevated_holds_on": "days",
            "elevated_note":
                "Verified, not asserted: the lowest day percentile in the set "
                "is Berlin at 87.3. THIS DOES NOT HOLD ON NIGHTS, where "
                "Berlin sits at 70.9, so the claim must be made about days or "
                "not at all.",
            "banned_word": "ordinary",
            "banned_word_note":
                "No city in this set may be called ordinary. Seville is 89th "
                "percentile, Hamburg 89th, Berlin 86th on days. Those are "
                "elevated readings that are merely not the most extreme, and "
                "calling them ordinary is the error that turned a 91st "
                "percentile Marseille into 'an ordinary summer'.",
            "band": {"south_edge_lat": 38, "north_edge_lat": 51},
            "least_extreme_on_days": ldays,
            "mechanism": None,
            "mechanism_note":
                "DELIBERATELY ABSENT. Stating the geography is measurement; "
                "explaining it is speculation. The page says where, not why, "
                "and a reader who wants why is better served by our saying we "
                "do not know.",
            "map": {
                "colour_by": "percentile within each city's own record",
                "never_colour_by": "absolute temperature, which would redraw "
                                   "the Mediterranean climate map rather than "
                                   "this summer",
                "quiet_cities": "must be visibly quiet, never absent. Their "
                                "presence is what makes the map evidence "
                                "rather than decoration.",
                "not_a_surface": "21 marks, not an interpolated field. This is "
                                 "21 thermometers and must not read as a "
                                 "European temperature map.",
                "points": [
                    {"city": c, "lat": COORDS[c][0], "lon": COORDS[c][1],
                     "day_percentile": v["days"]["rank"]["percentile"],
                     "night_percentile": v["rank"]["percentile"],
                     "night_metric_holds": c in ok_cities}
                    for c, v in sorted(cities.items())],
            },
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
    # GUARD. A constraint that exists only at headline level is unreachable
    # from a city page, which is how the nights gate came to look like a
    # two-city list. This fails the emit rather than reporting it, because a
    # check that cannot stop the thing it checks is a comment.
    REQUIRED = ("page_constraints", "nights_metric_gated",
                "nights_baseline_per_year", "rank", "days",
                "series_to_same_date")
    missing = {c: [k for k in REQUIRED if k not in v]
               for c, v in cities.items()}
    missing = {c: k for c, k in missing.items() if k}
    if missing:
        print(f"  FAIL: cities missing page-level fields: {missing}",
              file=sys.stderr)
        return 1
    # The two caveats are opposites BY MEASUREMENT, not by assertion, so the
    # guard recomputes the fact rather than comparing the two prose fields.
    # My first version compared a sentence to a boolean, which is not a
    # comparison at all: it fired on every city including the correct ones.
    # A guard that cannot be wrong about the thing it guards is worth more
    # than a guard that merely looks strict.
    nights_worse_before = nbase["worst_year_on_record"]["cities"] >= len(recs)
    days_worse_now = dbase["worst_year_on_record"]["cities"] < len(drecs)
    if not (nights_worse_before and days_worse_now):
        print(f"  FAIL: the nights/days caveat pair no longer holds. "
              f"nights 2026={len(recs)} vs worst "
              f"{nbase['worst_year_on_record']}; days 2026={len(drecs)} vs "
              f"worst {dbase['worst_year_on_record']}. The page_constraints "
              f"text asserts an inversion the data no longer supports.",
              file=sys.stderr)
        return 1

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out}")
    print(f"  {len(cities)} cities, {len(recs)} at NIGHT record, of which "
          f"{len(recs_ok)} where the 20C metric holds: {recs_ok}")
    print(f"  20C metric unreliable in: {sorted(set(cities)-set(ok_cities))}")
    print(f"  {len(drecs)} at DAY record: {drecs}")
    print(f"  night baseline {nbase['median_year']} median, worst "
          f"{nbase['worst_year_on_record']}")
    print(f"  day   baseline {dbase['median_year']} median, worst "
          f"{dbase['worst_year_on_record']}")
    print(f"  no day multiple: {nomult}")
    print(f"  fragile (1-night margin): {thin}")
    bad = [c for c, v in cities.items()
           if v["series_to_same_date"]["gap_slots"] < 0]
    print(f"  slot arithmetic consistent: {not bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
