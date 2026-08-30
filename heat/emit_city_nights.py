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
# HEAT_SERIES lets the extremes test point the emitter at a synthetic series.
# Unset in every real run, so production reads the committed artifact.
SERIES = Path(__import__("os").environ.get(
    "HEAT_SERIES", ROOT / "heat" / "data" / "city_series.json"))
OUT = ROOT / "heat" / "data" / "city_nights.json"

# Product's ruling 2026-08-07. Bilbao is OUT and the argument is the one
# neither design nor I made: Bilbao's headline figure is 13.7x, a ratio
# against a 1.17-night baseline, which is precisely the construction the
# nights gate exists to distrust. The number that made it look like a
# featured city is the number we are not permitted to quote.
#
# Vienna in: the metric holds at 4.33 nights a year, it is at an outright
# record on BOTH instruments, and it is neither Spanish nor French, which is
# the point of the geography headline.
#
# Order is deliberate. PARIS IS THE GATED CASE, VIENNA THE UNGATED ONE, so
# building them in that sequence exercises both branches of the optional
# blocks template rather than discovering the second branch on city four.
FEATURED = ("Paris", "Madrid", "Vienna")

# Cities chosen from a FORECAST of the following week rather than from
# observed history. Named here because any claim comparing 2026 against a
# past year has to survive their removal: they were selected for 2026's heat
# and would otherwise prove such a claim by construction.
FORECAST_SELECTED = frozenset({"Bordeaux", "Toulouse", "Strasbourg",
                               "Hanover", "Stuttgart", "Geneva"})

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
    "Amsterdam": (52.3, 4.8), "Stockholm": (59.3, 18.1),
    "Prague": (50.1, 14.4), "Helsinki": (60.2, 24.9),
    "Zurich": (47.4, 8.6), "Bordeaux": (44.8, -0.6),
    "Toulouse": (43.6, 1.4), "Strasbourg": (48.6, 7.8),
    "Hanover": (52.4, 9.7), "Stuttgart": (48.8, 9.2), "Geneva": (46.2, 6.1),
    "Leipzig": (51.3, 12.4), "Dresden": (51.1, 13.8),
    "Basel": (47.5, 7.6), "Lugano": (46.0, 8.96),
    # Heathrow, and this one is NOT hand-typed. MIDAS gives 51.479,-0.453 and
    # OSCAR gives 51-28-45N 000-27-02W for WMO 03772; they agree to three
    # decimals, which is the check that confirmed the two transports are one
    # station. Recorded here so London is not the only city whose mark is a
    # guess when it is the one city whose position was actually verified.
    "London": (51.479, -0.451),
    "Nottingham": (53.0053, -1.2497),
    "Belfast": (54.6636, -6.2244),
    "Aberdeen": (57.2051, -2.2037),
    "Tallinn": (59.398, 24.603),
    "Larnaca": (34.8831, 33.6331),
    "Tallinn": (59.398, 24.603),
}

def _coord(city):
    """(lat, lon, source) for a city's map mark.

    Reads heat/data/station_coords.json, written by station_coords.py from
    each service's own station list, and falls back to the hand-typed COORDS
    above for cities not yet resolved. The fallback is LABELLED rather than
    silent: a hand-typed value is off by 3 to 15 km, which is a data-quality
    defect the page should disclose rather than hide behind 4 decimal places.
    """
    import json as _json
    global _COORD_CACHE
    if _COORD_CACHE is None:
        path = ROOT / "heat" / "data" / "station_coords.json"
        try:
            _COORD_CACHE = _json.loads(path.read_text())
        except Exception:
            _COORD_CACHE = {}
    r = _COORD_CACHE.get(city)
    if r and r.get("coord_source") != "hand_typed":
        return (r["lat"], r["lon"], r["coord_source"])
    return (COORDS[city][0], COORDS[city][1], "hand_typed")


_COORD_CACHE = None

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
    "NL": {"licence": "KNMI open data: reuse permitted, including "
                      "commercial, with attribution",
           "commercial_use": True, "attribution": "Source: KNMI",
           "lag_days": 2},
    "SE": {"licence": "CC-BY 4.0", "commercial_use": True,
           "attribution": "Source: SMHI", "lag_days": 1},
    "CZ": {"licence": "CHMI open data: reuse permitted with attribution",
           "commercial_use": True, "attribution": "Source: CHMI",
           "lag_days": 5},
    "FI": {"licence": "CC-BY 4.0", "commercial_use": True,
           "attribution": "Source: FMI", "lag_days": 1},
    "CY": {"licence": "History from NOAA GHCN-Daily, US federal open data. "
                      "2014-2026 from the station's own WMO synoptic "
                      "bulletins, licence UNRESOLVED and not yet confirmed "
                      "with the Cyprus Department of Meteorology.",
           "commercial_use": False,
           "attribution": "Source: Cyprus Department of Meteorology",
           "lag_days": 1},
    # SAME CONSTRUCTION AS CYPRUS, and the same unresolved half. GHCN history
    # is US federal open data; the recent seasons come from each station's own
    # WMO bulletins and their re-use terms are NOT confirmed with the national
    # service. Requests go to LHMT, DHMZ and OMSZ. Marked commercial_use False
    # until each answers, exactly as Larnaca is.
    # Argentina, same construction as Cyprus and the others: GHCN history
    # is US federal open data, the recent seasons are the station's own WMO
    # bulletins and their re-use terms are NOT confirmed with SMN.
    # Algeria, same construction and the same unresolved half. A request to
    # ONM Algeria for the missing 1999 is outstanding; that year is why this
    # city publishes a range rather than a count.
    "DZ": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Office National de la Meteorologie.",
        "commercial_use": False,
        "attribution": "Source: Office National de la Meteorologie (ONM)",
        "lag_days": 1,
    },
    "AR": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Servicio Meteorologico Nacional.",
        "commercial_use": False,
        "attribution": "Source: Servicio Meteorologico Nacional (SMN)",
        "lag_days": 1,
    },
    "LT": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Lithuanian Hydrometeorological Service.",
        "commercial_use": False,
        "attribution": "Source: Lithuanian Hydrometeorological Service",
        "lag_days": 1,
    },
    "HR": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Croatian Meteorological and Hydrological Service.",
        "commercial_use": False,
        "attribution": "Source: Croatian Meteorological and Hydrological "
                       "Service (DHMZ)",
        "lag_days": 1,
    },
    "HU": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Hungarian Meteorological Service.",
        "commercial_use": False,
        "attribution": "Source: Hungarian Meteorological Service (OMSZ)",
        "lag_days": 1,
    },
    "IT": {
        "licence": "History from NOAA GHCN-Daily, US federal open data. "
                   "Recent seasons from the station's own WMO synoptic "
                   "bulletins, licence UNRESOLVED and not yet confirmed with "
                   "the Italian Air Force meteorological service.",
        "commercial_use": False,
        "attribution": "Source: Servizio Meteorologico dell'Aeronautica "
                       "Militare",
        "lag_days": 1,
    },
    "EE": {"licence": "Keskkonnaagentuur, the Estonian Environment Agency, "
                      "supplied on request. Station Tallinn-Harku only; "
                      "the three other Tallinn stations in the same "
                      "archive are a relay, not one record, and are not "
                      "read.",
           "commercial_use": True,
           "attribution": "Source: Riigi Ilmateenistus / Keskkonnaagentuur",
           "lag_days": 1},
    # RESOLVED 2026-08-11. The Met Office National Meteorological Library
    # and Archive supplied the 2026 season directly and its workbook states
    # the terms: provided under their re-use obligations, re-use in a
    # product requires acknowledgement of the source, Crown Copyright.
    #
    # THE WORD "PROVISIONAL" MUST NOT APPEAR IN THIS STRING. Design gates
    # the page's provisional notice on finding it here, correctly and on
    # my instruction. When the licence resolved I updated
    # london_provenance.json and left this string alone, so the payload said
    # cleared in one field and provisional in another, and the page rendered
    # the stale one. A post went out pointing at a page that contradicted it.
    #
    # Fix-in-one-place, for the fifth time in two days, and the first that
    # reached a reader who had just been sent there.
    "UK": {"licence": "Met Office. History from MIDAS Open under the Open "
                      "Government Licence. 2026 season supplied by the Met "
                      "Office National Meteorological Library and Archive "
                      "under their re-use obligations, Crown Copyright, "
                      "re-use permitted with acknowledgement of the source. "
                      "Values may be revised under quality control for up "
                      "to twelve months from capture.",
           "commercial_use": True, "attribution": "Source: Met Office",
           "lag_days": 1},
    "CH": {"licence": "Swiss federal open data: reuse permitted, including "
                      "commercial, with attribution",
           "commercial_use": True, "attribution": "Source: MeteoSwiss",
           "lag_days": 1},
}


# Load-bearing for PROSE, not just for rendering. Editor's request 2026-08-08:
# the banned-word rule depends on this number, and if it changes shape the
# copy keeps rendering and quietly means something else. So it is emitted as
# a field rather than living inside a generated sentence, and the guard below
# refuses to write a payload where the prose contract has drifted.
ELEVATED_PCT = 85.0
MIN_SCALE_SPAN = 5.0     # a colour ramp needs a non-zero domain

# Every field the editor's rules bind to. A renderer failing is visible; copy
# silently meaning something else is not.
PROSE_CONTRACT = {
    ("geography", "elevated_threshold_pct"): float,
    ("geography", "all_elevated_on_days"): bool,
    ("geography", "lowest_day_percentile"): dict,
    ("geography", "banned_word"): str,
    ("headline", "lead", "claim"): str,
    ("headline", "lead", "framing_rule"): str,
    ("headline", "lead", "not_elevated"): list,
}


def check_prose_contract(payload):
    """Fail the emit if a field the copy is built from has changed shape."""
    bad = []
    for path, typ in PROSE_CONTRACT.items():
        node = payload
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
            if node is None and k != path[-1]:
                break
        if node is None or not isinstance(node, typ):
            bad.append(".".join(path))
    return bad


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


def _is_record(v, key, pct="95"):
    """Is the current year at a record for this city on this instrument?"""
    yrs = v["years"]
    cur = str(max(int(y) for y in yrs))
    now = (yrs[cur]["nights_to_cut"] if key == "nights"
           else yrs[cur]["days_to_cut"][pct])
    prior = [(d["nights_to_cut"] if key == "nights" else d["days_to_cut"][pct])
             for y, d in yrs.items() if d["usable_to_cut"] and y != cur]
    return bool(prior) and now > max(prior)


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
    # Documented station relocations, read from each service's own metadata.
    # The statistical route was built, calibrated and found to have no power
    # at this effect size; see heat/blend_gate.py. A relocation is an
    # administrative event and the service publishes it.
    HP = ROOT / "heat/data/station_history.json"
    HIST = json.loads(HP.read_text())["stations"] if HP.exists() else {}
    EARLIEST_USED = (json.loads(HP.read_text())["thresholds"]
                     ["earliest_year_that_matters"] if HP.exists() else 1961)
    B = json.loads((ROOT / "heat/data/record_rate_baseline.json").read_text())
    ties = S["tie_rule"]["ties_count_against_current_year"]

    # Each instrument's own answer, derived from the record counts. Done
    # before the city loop because every city carries both.
    _pre_n = record_rate(S, "nights")
    _pre_d = record_rate(S, "days")
    _n_now = sum(1 for cc, vv in S["cities"].items()
                 if _is_record(vv, "nights"))
    _d_now = sum(1 for cc, vv in S["cities"].items()
                 if _is_record(vv, "days"))
    # LEAVE-ONE-OUT ON THE FORECAST-SELECTED CITIES. Product's ruling
    # 2026-08-09, and the reasoning is theirs: six cities were chosen because
    # 2026 is forecast hot there, so their 2026 counts are high BY
    # CONSTRUCTION while their 2003 counts are incidental. That makes
    # "2026 beats 2003" circular on this set and leaves "2003 beats 2026"
    # safe, because the bias runs against it.
    #
    # I had checked that both sides recompute over the same 32 cities, which
    # kills the counting-more-places artefact and is NOT this. The set itself
    # is selected toward one of the two years being compared.
    #
    # So the claim must survive REMOVING the selected cities. That is a test
    # rather than a judgement, and it discriminates: nights fails it, days
    # passes. A blanket block would have withheld a defensible claim.
    _sub = {"cities": {c: v for c, v in S["cities"].items()
                       if c not in FORECAST_SELECTED},
            "tie_rule": S["tie_rule"], "completeness": S["completeness"]}
    _n_sub = sum(1 for c, v in _sub["cities"].items() if _is_record(v, "nights"))
    _d_sub = sum(1 for c, v in _sub["cities"].items() if _is_record(v, "days"))
    _pre_n_sub = record_rate(_sub, "nights")
    _pre_d_sub = record_rate(_sub, "days")

    # CROSS-YEAR RECORD COUNTS ARE NOT PUBLISHABLE. Product ruling
    # 2026-08-10, and the reasoning goes further than the bug that prompted
    # it. Adding London flipped this from false to true, 20 cities at a night
    # record against 19 in 2003, on a one-city margin, and London was added
    # that day BECAUSE London was hot.
    #
    # I proposed recomputing on a fixed city set. That is not enough, and
    # product was right that it only LOOKS like the rigorous answer. A fixed
    # set fixes comparability of MEMBERSHIP. It does not fix the defect,
    # which is that OUR SET WAS ASSEMBLED DURING 2026 WITH KNOWLEDGE OF 2026.
    # Same-set arithmetic does not repair a set selected on the outcome
    # variable, so every recomputation inherits the selection.
    #
    # THE GENERAL RULE, one rung above the one we already had. A claim
    # quantified over a set must be regenerated from the set. AND a claim
    # quantified over a set is only comparable ACROSS TIME if the set was
    # chosen without reference to any of the years being compared. Ours was
    # not and cannot retroactively become so.
    #
    # WHAT SURVIVES IS NEARLY EVERYTHING. Selection cannot bias a comparison
    # a city makes with itself, so every per-city rank stands. The selection
    # effect kills the aggregate, not the instrument: "20 of our 36" is
    # publishable with the set named, "more than 2003" is not publishable at
    # all. London being added because it is hot makes the aggregate
    # meaningless and makes "London's hottest since 1949" no less true.
    #
    # EARNING IT BACK is a 2027 capability: declare the selection rule,
    # freeze the set, and cross-year counts become valid from the freeze
    # forward. Better honestly in eighteen months than fraudulently now.
    nights_worst = False
    days_worst = False
    _cross_year_note = (
        "NOT COMPUTED. A cross-year record count requires a city set chosen "
        "without reference to the years being compared. This set was "
        "assembled during 2026 with knowledge of 2026, so no recomputation "
        "repairs it, including on a fixed set. Per-city ranks are unaffected: "
        "selection cannot bias a comparison a city makes with itself.")
    _loo = {
        "test": "The claim must hold with the forecast-selected cities "
                "REMOVED, because those cities were chosen for 2026's heat "
                "and would otherwise prove the claim by construction.",
        "excluded": sorted(FORECAST_SELECTED),
        "cross_year_comparison": _cross_year_note,
        "nights": {"full": [_n_now, _pre_n["worst_year_on_record"]["cities"]],
                   "without_selected": [
                       _n_sub, _pre_n_sub["worst_year_on_record"]["cities"]]},
        "days": {"full": [_d_now, _pre_d["worst_year_on_record"]["cities"]],
                 "without_selected": [
                     _d_sub, _pre_d_sub["worst_year_on_record"]["cities"]]},
    }
    # COVERAGE. Editor found this in their own copy and it applies to every
    # count we publish, not only theirs. Services publish on different lags,
    # so cities reach different dates. A city whose window ends on 3 August
    # CANNOT register a record on the 4th, and 4 August was the peak.
    #
    # So every count of cities-at-something is a FLOOR, not a census, for as
    # long as any city is short of the set's latest cut. More data can only
    # add to it: a city already counted stays counted.
    #
    # A FIELD RATHER THAN A QUALIFIER IN PROSE, at editor's request and for
    # their reason: "at least 22" versus "22" should be decided from the data
    # rather than by whoever last edited the string. When every source
    # reaches the cut, coverage_complete goes true and the qualifier
    # disappears on its own.
    #
    # This is the third count to go wrong today. Counts keep getting through
    # because they look like measurements rather than claims, and a
    # denominator makes them look complete when it only makes them look it.
    _cuts = {cc: vv["counted_to"] for cc, vv in S["cities"].items()}
    _latest = max(_cuts.values())
    _short = sorted(cc for cc, t in _cuts.items() if t < _latest)
    coverage = {
        "latest_cut": _latest,
        "cities_at_latest_cut": len(_cuts) - len(_short),
        "cities_short_of_it": len(_short),
        "short_cities": {cc: _cuts[cc] for cc in _short},
        "coverage_complete": not _short,
        "counts_are_floors": bool(_short),
        "means": ("every count of cities-at-something is a floor while any "
                  "city is short of the latest cut, because a city with no "
                  "observation on a day cannot register that day."),
        # SCOPED TO THE FINDING COUNTS, and editor caught why it has to be.
        # The first version said "prefix counts with 'at least'" without
        # saying which, and `cities_short_of_it` lives in this same object
        # and moves the OTHER WAY: it falls as late sources land. A renderer
        # applying the rule as written produces "at least 21 cities are
        # short of the cut", which is backwards, and it is exactly the
        # mistake a renderer makes at 2am during a live event.
        "floors_apply_to": ["cities_at_night_record", "cities_at_day_record",
                            "cities_above_percentile"],
        "ceilings_not_floors": ["cities_short_of_it"],
        "render_rule": ("prefix a count in floors_apply_to with 'at least' "
                        "while counts_are_floors is true, and drop it when "
                        "false. Never apply it to ceilings_not_floors, "
                        "which fall as late data lands. Never type either "
                        "form."),
        "direction": ("finding counts can only rise as late sources land. "
                      "cities_short_of_it can only fall. They are not the "
                      "same quantity and must not share a qualifier."),
    }

    def _reason(now, base, sub_now, sub_base, ok):
        """Say which test decided it. A note that contradicts its own verdict
        is the failure platform found in the definitions row this morning."""
        head = ("{0} cities at a record against {1} in {2}, the worst prior "
                "year.".format(now, base["cities"], base["year"]))
        if ok:
            return head + (" It exceeds that, and still exceeds it with the "
                           "forecast-selected cities removed ({0} against "
                           "{1}), so the claim does not rest on how those "
                           "cities were chosen.".format(sub_now,
                                                        sub_base["cities"]))
        if now > base["cities"]:
            return head + (" It exceeds that on the full set, BUT NOT WITH "
                           "THE FORECAST-SELECTED CITIES REMOVED ({0} against "
                           "{1}). Those six were chosen because 2026 is "
                           "forecast hot there, so the claim would be true by "
                           "construction. Unavailable, and not because the "
                           "arithmetic fails.".format(sub_now,
                                                      sub_base["cities"]))
        return head + " It does not exceed that, so the claim is unavailable."

    nights_reason = _reason(_n_now, _pre_n["worst_year_on_record"],
                            _n_sub, _pre_n_sub["worst_year_on_record"],
                            nights_worst)
    days_reason = _reason(_d_now, _pre_d["worst_year_on_record"],
                          _d_sub, _pre_d_sub["worst_year_on_record"],
                          days_worst)

    # The newest cut anywhere in the set, which is the closest thing we have
    # to "now" without reading a clock the payload cannot show a reader.
    _newest_cut = max(v["counted_to"] for v in S["cities"].values())
    cities = {}
    for c, v in S["cities"].items():
        yrs = v["years"]
        cur = str(max(int(y) for y in yrs))
        # A SEASON THAT HAS NOT STARTED MUST NOT BE RANKED. Santiago del
        # Estero came out "rank 70 of 70, zero days above its 95th
        # percentile", which reads as its coolest summer on record. Its
        # summer had not begun: the season is December to January and the
        # cut is 29 August, so the year has no days to count and ranking
        # zero against seventy real summers puts it last by construction.
        #
        # This is the shape the whole channel has been catching all week,
        # arriving on a new surface: absence produced by the calendar,
        # presented as a measurement. It would have been the first number on
        # the first Argentine page.
        season_open = yrs[cur]["usable_to_cut"] or yrs[cur]["window_days"] > 0
        good = {int(y): d for y, d in yrs.items()
                if d["usable_to_cut"] and int(y) < int(cur)}
        todate = {y: d["nights_to_cut"] for y, d in good.items()}
        n26 = yrs[cur]["nights_to_cut"]
        r = rank_of(n26, todate, ties) if season_open else None
        of_years = (len(todate) + 1) if season_open else len(todate)
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
            # RAW STATION START. Kept because "when did this thermometer
            # begin reporting" is a real question, and RENAMED IN MEANING by
            # the note below because it is not the answer to "how far back
            # can we see", which is what four live pages were using it for.
            #
            # Socials swept all 36 and found nine cities where a partial
            # first year makes this one to two years earlier than the first
            # usable year, and four pages publishing the overstated figure
            # in prose directly above a chart whose axis contradicts it.
            # Leipzig's page justifies its baseline window with "this
            # thermometer starts in 1863" over an axis reading 1864.
            #
            # This is the same correction landing in one place and not its
            # neighbour, for the fourth time: record_scope fixed, post_form
            # not; post_form fixed, record_from not. So this field now says
            # what it is not, rather than waiting to be read innocently.
            "record_from": v["record_from"], "record_to": v["record_to"],
            # CARRIED THROUGH, not recomputed. Product's 2026-08-11 ruling
            # lets a city whose record cannot cover 1971-2000 use another
            # complete WMO standard normal, so the period that built a
            # threshold is no longer the same for every city and must
            # travel with it. Same rule as record_scope: a page cannot
            # state a threshold without stating what built it.
            # Carried through, not recomputed. This is the answer to the
            # reader challenge on Heathrow, and it is useless in a file no
            # page reads, which is where pctl_baseline sat for an hour.
            "station_class": v.get("station_class"),
            "station_class_note": v.get("station_class_note"),
            "station_class_limit": v.get("station_class_limit"),
            # THE SEASON MUST REACH THE CONSUMER. It was emitted to
            # city_series.json and design reads city_nights.json, so the field
            # the entire southern render turns on was invisible to the only
            # chat that needed it. Third time this week I have emitted
            # something to one file and told someone it was in another.
            "season": v.get("season"),
            # FOURTH TIME. Emitted to city_series and not to the file design
            # reads. A disclosure that does not reach the consumer is not a
            # disclosure, and this one is the whole basis on which Kristjan
            # approved publishing a short baseline.
            "pctl_baseline_shortfall": v.get("pctl_baseline_shortfall"),
            "pctl_baseline": v.get("pctl_baseline"),
            "pctl_baseline_is_default": v.get("pctl_baseline_is_default"),
            "pctl_baseline_note":
                "the percentile thresholds on this page are computed over "
                "this period. Where it is not the default 1971-2000, the "
                "city's record does not cover that window and a complete "
                "later WMO normal is used instead, which yields a HIGHER "
                "threshold and so understates rather than overstates.",
            "record_from_note":
                "THE STATION'S RAW START, NOT OUR RANKING WINDOW. A partial "
                "first year appears here and is excluded from the ranked "
                "series, so this is one to two years earlier than "
                "record_scope.from_year in nine cities. ANY PROSE ABOUT HOW "
                "FAR BACK THE RECORD GOES MUST USE record_scope.from_year: "
                "it is the window the ranks are computed on and the one the "
                "charts are drawn on. Use this field only to say when the "
                "thermometer began reporting.",
            "nights_2026": n26,
            "counted_to": v["counted_to"],
            "last_observation": v["last_observation"],
            "date_note":
                "counted_to is the cut every year in the series is measured "
                "to. last_observation is how far the source now reaches. "
                "Advancing the cut is a substantive change, not a refresh.",
            "rank": {
                "value": r, "of_years": of_years,
                "percentile": (round((1 - (r - 1) / of_years) * 100, 1)
                               if r is not None else None),
                "season_open": season_open,
                "season_not_started_note": (
                    None if season_open else
                    "This city's season has not begun. It is not ranked, and "
                    "a count of zero here means no days have been observed "
                    "yet rather than a cool season. The last complete season "
                    "is the most recent figure this city has."),
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
                # Kristjan's ruling 2026-08-07: Frankfurt keeps its record and
                # the 2014 move is stated on the page. The condition is that
                # the asterisk is DRIVEN BY THIS FIELD, never typed, exactly
                # as requires_series blocks a bare rank.
                #
                # Structural rather than a one-off because the night gate
                # closed Frankfurt's worst exposure BY ACCIDENT. Luck that
                # holds today is not a control, and the next city with a move
                # may not be gated.
                "requires_relocation_note": bool(
                    HIST.get(c, {}).get("relocations_in_period")),
                "relocation_note_text": (
                    "This station moved {0} in {1}, so the record is not one "
                    "continuous site and 'of {2}' spans more than one.".format(
                        ", ".join(f"{m['km']} km" for m in
                                  HIST[c]["relocations_in_period"]),
                        ", ".join(m["date"][:4] for m in
                                  HIST[c]["relocations_in_period"]),
                        of_years)
                    if HIST.get(c, {}).get("relocations_in_period") else None),
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
            # COMPUTED PER INSTRUMENT, never asserted. The first version
            # hardcoded that the two caveats INVERT: nights may not claim the
            # worst year, days may. That was true of August 2026 and is not a
            # property of the channel. Fed a calm year the guard failed
            # because NEITHER may claim it; fed a record year it failed
            # because BOTH may. Found by the extremes test on its first run.
            #
            # What is permanent is that each instrument has its own answer and
            # they must not be assumed to agree. That is now derived.
            "page_constraints": {
                "nights": {
                    "may_say_worst_on_record": nights_worst,
                    "reason": nights_reason,
                },
                "days": {
                    "may_say_worst_on_record": days_worst,
                    "reason": days_reason,
                },
                "selection_robustness": _loo,
                "instruments_agree": nights_worst == days_worst,
                "instruments_agree_note":
                    "Whether the two instruments happen to give the same "
                    "answer is a fact about this season, not a rule. A page "
                    "must read each one rather than carrying a caveat across.",
                # DERIVED PER CITY, not a blanket ban. Editor found the
                # stated reason had become false: it said no city in the set
                # is ordinary and that the least extreme sit at the 86th to
                # 90th percentile. With the set at 36, Helsinki is the 51.8th
                # percentile of its own record. By its own history that is an
                # unremarkable summer, and the ban was preventing a TRUE
                # sentence while its justification asserted the opposite of
                # the data.
                #
                # A guard is a claim about the data and it goes stale exactly
                # like copy does. This one was read, was correct, and the
                # world moved under it when the set grew by twelve cities.
                # That is the fourth instance today of something true when
                # written, hard-coded, with no expiry attached.
                #
                # Editorially the point is the opposite of hiding it: a set
                # where everything is extreme invites the question of how the
                # set was chosen, and one genuinely unremarkable member
                # answers it before it is asked.
                # Set below, once both ranks exist on the entry. Placeholders
                # rather than a blanket ban, so a stale claim cannot ship if
                # the assignment is ever removed.
                "banned_words": [],
                "banned_words_reason": "",
                "why_here":
                    "Repeated on every city because a page renders one city "
                    "and cannot be asked to read the headline object. A "
                    "constraint the renderer cannot reach is a constraint "
                    "that does not exist.",
            },
            # ON THE CITY, because a relocation qualifies THIS city's rank and
            # a city page renders one city. Same rule as page_constraints.
            "station_relocations": HIST.get(c, {}).get(
                "relocations_in_period", []),
            "station_moved_in_period": bool(
                HIST.get(c, {}).get("relocations_in_period")),
            "station_history_checked": c in HIST,
            "station_disclosure": (
                "Station history not yet checked."
                if c not in HIST else
                "The met service states this series is inhomogeneous, because "
                "of station relocations and changes in observation technique, "
                "and not suitable for comparison across time."
                if HIST[c].get("producer_inhomogeneity_warning") else
                # THREE cases here, not two, and the third was reading as the
                # second. A city with NO second copy is not the same as a city
                # whose second copy is a redistribution, and neither is the
                # same as one that was genuinely compared. Amsterdam has no
                # second copy at all; the branch fired because its changepoint
                # value is ABSENT and absent was reading as zero.
                ("No published station history exists for this service, and no "
                 "independent copy of this station is available, so a change "
                 "of instrument could not be ruled out."
                 if HIST[c].get("changepoint_t") is None else
                 "No published station history exists for this service, and "
                 "the second copy available is a redistribution of the same "
                 "observations, so a change of instrument could not be ruled "
                 "out by comparison."
                 if HIST[c]["changepoint_t"] < 0.01 else
                 "No published station history exists for this service. "
                 "Compared against a second copy of the same station and no "
                 "change of instrument was detected.")
                if HIST[c].get("history_available") is False else
                "Station record combines two instruments at the same site, "
                "with a documented handover in 1993."
                if HIST[c].get("composite") else
                "Station has not moved since {0}.".format(EARLIEST_USED)
                if not HIST[c]["relocations_in_period"] else
                "Station moved {0} in {1}.".format(
                    ", ".join(f"{m['km']} km" for m in
                              HIST[c]["relocations_in_period"]),
                    ", ".join(m["date"][:4] for m in
                              HIST[c]["relocations_in_period"]))),
            "station_disclosure_note":
                "Kristjan's ruling 2026-08-07: show the state per city rather "
                "than verify quietly or hedge across the set. THREE DIFFERENT "
                "FACTS and the reader gets whichever is true. Generated from "
                "the fields, never typed. When a city moves from unchecked to "
                "checked-and-clean the page improves with no copy change.",
            "station_note":
                "Documented moves inside the period we publish, from the met "
                "service's own station history. WHERE THIS IS NON-EMPTY the "
                "record is not a single continuous site, so 'Nth of M years' "
                "overstates comparability and any baseline spanning the move "
                "is computed across two sites. Empty list means checked and "
                "clean; station_history_checked false means NOT CHECKED, "
                "which is not the same thing.",
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
        # SAME SUPPRESSION AS THE NIGHT RANK. The days rank is computed in a
        # second place, and my first pass fixed only the first, so Santiago
        # still printed "70 of 70" on the instrument the Argentine pages
        # actually lead with. Two ranks in two blocks: fix one, ship the
        # other.
        dr = rank_of(d26, dser, ties) if season_open else None
        dof = (len(dser) + 1) if season_open else len(dser)
        dbelow = [n for n in dser.values() if n < d26]

        days = {
            "rank": {
                "value": dr, "of_years": dof,
                "percentile": (round((1 - (dr - 1) / dof) * 100, 1)
                               if dr is not None else None),
                "season_open": season_open,
                "season_not_started_note": (
                    None if season_open else
                    "This city's season has not begun, so it is not ranked. "
                    "A count of zero here means no days observed yet, not a "
                    "cool season."),
                "measured_on": "95",
                "ties_count_against": ties,
                "tied_with": sorted(y for y, n in dser.items() if n == d26),
                "requires_series": True,
                "requires_series_note":
                    "Read this rank, never derive it. Same rule as the night "
                    "rank and the same reason: a strict greater-than promotes "
                    "ties and manufactures records.",
                "margin_days": (d26 - max(dbelow)) if dr == 1 and dbelow else None,
                "days_so_far": d26 if season_open else None,
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
        # THE LEGEND BAND, emitted rather than derived by the renderer.
        #
        # Product ratified a refresh gate whose triggers include "any city
        # changing legend band", because a city moving between bands changes
        # the map's whole picture WITHOUT changing anyone's rank. The band was
        # being derived inside design's template, so the gate could not see
        # the property it was built to watch.
        #
        # Same seam defect as the nights gate living at headline level, only
        # inverted: there a renderer could not reach a constraint, here a
        # check could not reach a property. One definition, emitted once.
        # BAND ON THE CLAIM, NOT THE RANK NUMBER. Under ties-count-against,
        # BOTH years of a two-way tie at the top sit at rank 2, so a city
        # that holds the record jointly was being banded "near" and its page
        # understated a record it actually holds. Dresden hit this on 19
        # August, tied with 2018 at 16 days with nothing above it, banded
        # near. Malaga hit the identical thing in the refresh gate the day
        # before and design caught that one.
        #
        # Same fix in both places: years strictly above is
        # rank - 1 - len(tied_with), and a city is at its record while that
        # is zero, tie or no tie.
        # A CITY WITH NO SEASON YET GETS NO BAND and no _above. It is not at
        # a record and not outside one; there is nothing to band. Emitting
        # "outside" would colour six Argentine cities as having quiet summers
        # when they have not had summers.
        _above = (None if dr is None
                  else dr - 1 - len(entry["days"]["rank"].get("tied_with") or []))
        # THE SELECTION CAVEAT, AS A FIELD. Emitted for every city so a
        # template can rely on it, and flagged for rendering only where the
        # reader's question is live: a city that joined recently AND is at or
        # near its own record. Budapest went live at its first appearance
        # claiming a record with none of this on the page.
        from build_city_series import JOINED, JOINED_CAVEAT_DAYS
        import datetime as _dt
        _j = JOINED.get(c)
        if _j:
            # AGAINST THE SET'S NEWEST CUT, not this city's own. Budapest's
            # data lags nine days behind the set, so measuring from its own
            # counted_to made it join in the future: days_in_set of -9.
            _days = (_dt.date.fromisoformat(_newest_cut)
                     - _dt.date.fromisoformat(_j[0])).days
        else:
            _days = None
        entry["joined"] = {
            "date": _j[0] if _j else None,
            "why": _j[1] if _j else None,
            "days_in_set": _days,
            "is_recent": bool(_j and _days is not None
                              and _days <= JOINED_CAVEAT_DAYS),
            "caveat_required": bool(
                _j and _days is not None and _days <= JOINED_CAVEAT_DAYS
                and _above is not None and _above <= 4),
            "caveat": (f"Added to the set on {_j[0]}. {_j[1]}"
                       if _j else None),
            "why_this_matters": (
                "A count over a set inherits the choice of which cities are "
                "in it (D-141). A city entering at or near its own record "
                "reads as chosen for that number unless the page says "
                "otherwise first, so where caveat_required is true the "
                "caveat belongs ON the page, not in the methodology."),
        }

        entry["legend_band"] = (None if _above is None else
                                "record" if _above == 0 else
                                "near" if _above < 5 else "outside")
        entry["legend_band_note"] = (
            "record = nothing in its own record stands above this year, "
            "which INCLUDES a tie for the highest; near = 1 to 4 years "
            "above; outside = 5 or more above. READ THIS, do not re-derive "
            "it: a second definition living in a template is a second thing "
            "to drift, and deriving it from the rank number rather than from "
            "the claim is exactly how a joint record got banded as near.")

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

        # RECORD SCOPE. A rank is only ever against the record WE HOLD, and
        # for most of these cities the station observed for decades before
        # our series starts. Vienna's is the live case: Hohe Warte reached
        # 39.8 C on 2026-08-04, above anything since 1950, and its
        # observations begin well before 1950. "Vienna's hottest day ever"
        # is false; "the hottest in the record we hold" is true.
        #
        # A FIELD, NOT A CAVEAT, at product's instruction and editor's. A
        # caveat is a sentence someone cuts for length. This cannot be
        # rendered away, and the prose version stays too, because the two
        # fail differently.
        # THE "ordinary" BAN, DERIVED PER CITY. Editor found the old blanket
        # ban's stated reason had become false: it said no city in the set is
        # ordinary and the least extreme sit at the 86th to 90th percentile.
        # With the set at 36, Helsinki is the 51.8th percentile of its own
        # record. By its own history that is an unremarkable summer, so the
        # ban was preventing a TRUE sentence while its justification asserted
        # the opposite of the data.
        #
        # A guard is a claim about the data and goes stale exactly like copy.
        # This one was read, was correct, and the world moved under it when
        # the set grew by twelve cities. Fourth instance today of something
        # true when written, hard-coded, with no expiry attached.
        #
        # Editorially the point is to NAME the quiet city rather than hide
        # it: a set where everything is extreme invites the question of how
        # the set was chosen, and one unremarkable member answers it first.
        # A CITY WHOSE SEASON HAS NOT STARTED IS NOT "ordinary" AND NOT HOT.
        # Both percentiles are null then, and max() over a null was the last
        # place the not-started case leaked. The word ban exists to stop a
        # page calling a record summer ordinary; with no season yet there is
        # nothing to describe either way, so nothing is banned.
        _ps = [x for x in (entry["rank"]["percentile"],
                           entry["days"]["rank"]["percentile"])
               if x is not None]
        _pk = max(_ps) if _ps else None
        _hot = _pk is not None and _pk >= ELEVATED_PCT
        entry["page_constraints"]["banned_words"] = (
            ["ordinary", "unremarkable", "quiet"] if _pk is None
            else ["ordinary"] if _hot else [])
        entry["page_constraints"]["banned_words_reason"] = (
            # NO SEASON, NO VERDICT. A city whose season has not begun is
            # neither remarkable nor unremarkable, and the "may be described
            # as unremarkable" branch would have licensed calling six
            # Argentine cities' absent summers ordinary.
            "This city's season has not begun, so nothing may be said about "
            "how this year compares. Not 'ordinary', not 'unremarkable', and "
            "not a rank. The last complete season is the most recent figure "
            "it has." if _pk is None else
            f"This city is at the {_pk:g}th percentile of its own record, at "
            f"or above the {ELEVATED_PCT:g}th, so 'ordinary' is false of it. "
            "That is the error that turned a 91st-percentile Marseille into "
            "'an ordinary summer'." if _hot else
            f"NO BAN. This city is at the {_pk:g}th percentile of its own "
            f"record, below the {ELEVATED_PCT:g}th on both instruments, so "
            "by its own history this summer is unremarkable and may be "
            "described that way. Say it plainly rather than reaching for a "
            "softer word: a set in which every city is extreme invites the "
            "question of how the set was chosen.")

        # FROM THE RANKED SERIES, NOT THE RAW RECORD START, and design found
        # why. Frankfurt's source begins in 1935; its ranked series begins in
        # 1937, because 1935 and 1936 fail the completeness bar. The footer
        # printed "our series, from 1935" beside a chart starting in 1937, so
        # it claimed two years the reader cannot see and the rank was never
        # computed over.
        #
        # record_scope exists to BOUND A RANK CLAIM, so it has to name the
        # window the rank was actually computed on. record_from answers a
        # different question, when the station started reporting, and both
        # are correct. That is the two-bases collision a third time: Vienna's
        # previous high, the selection prose, and now this.
        _ranked_years = sorted(
            int(y) for y, d in yrs.items() if d.get("usable_to_cut"))
        _from = (_ranked_years[0] if _ranked_years
                 else int(str(v["record_from"])[:4]))
        entry["record_scope"] = {
            "from_year": _from,
            "record_starts": int(str(v["record_from"])[:4]),
            "differs_because": (
                "the record starts earlier than the ranked series: the "
                "early years fail the completeness bar and are not ranked "
                "over. Cite from_year, which is the window the rank was "
                "computed on."
                if _from != int(str(v["record_from"])[:4]) else None),
            "text": f"our series, from {_from}",
            "is_all_time": False,
            "why": "the station may have observed before our record starts, "
                   "so a rank is against the record we hold and never "
                   "against the city's full history.",
            "may_not_say": ["hottest ever", "all-time record",
                            "hottest since records began"],
        }

        # THE LEADING RUN IS NOT EMITTED YET, and the reason is recorded
        # rather than left as a gap. Editor's rule: "Vienna's five hottest
        # days all fell in 2026" is the LENGTH OF THE LEADING RUN of
        # current-year days in the all-time sorted daily list. A sixth hot
        # day makes it six; a cool week leaves it at five. Typed into prose
        # it goes wrong on the next hot day, silently, and in the flattering
        # direction.
        #
        # It CANNOT be computed here. This emitter reads city_series.json,
        # which carries per-year aggregates, and the run needs the daily
        # series. It belongs in build_city_series.py, where the dailies
        # live, and must be carried through as a field.
        #
        # Written down instead of half-built: I drafted it against two names
        # that do not exist in this module, which would have failed on the
        # first run. An empty field would have been worse, because a
        # renderer would read zero as "no run" rather than "not computed".

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
    # EVERY CONSUMER OF percentile HAD TO LEARN ABOUT THE NOT-STARTED CASE,
    # and I patched three of them one at a time before noticing that was the
    # wrong shape. A city whose season has not begun has no percentile, and
    # each aggregate below wants it EXCLUDED rather than defaulted: it is not
    # cool, not hot, not the lowest, and not in the top five.
    def _pct(v, key="rank"):
        return v[key]["rank"]["percentile"] if key != "rank" else v["rank"]["percentile"]

    def _has(v):
        return (v["rank"]["percentile"] is not None
                and v["days"]["rank"]["percentile"] is not None)

    _rankable = {c: v for c, v in cities.items() if _has(v)}
    _low = sorted(((v["days"]["rank"]["percentile"], c)
                   for c, v in _rankable.items()))
    low_pct, low_city = _low[0]
    ldays = [{"city": c, "day_percentile": p} for p, c in _low[:4]]
    nbase = record_rate(S, "nights")
    recs = sorted(c for c, v in cities.items() if v["rank"]["value"] == 1)
    recs_ok = [c for c in recs if c in ok_cities]
    top5 = [c for c, v in _rankable.items() if v["rank"]["percentile"] >= 95]
    top10 = [c for c, v in _rankable.items() if v["rank"]["percentile"] >= 90]
    # A NIGHT-fragility list must not contain a city whose night metric is
    # gated. Amsterdam arrived with 3 tropical nights against a baseline of
    # 0.17 and landed in a list about one-night margins, which would have
    # invited exactly the ratio the gate forbids.
    thin = [c for c, v in cities.items()
            if v.get("record_margin_nights") == 1
            and not v["nights_metric_gated"]]
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
                # DESCRIPTIVE AND COUNTED, never universal. Kristjan's ruling
                # 2026-08-08: "we should not tie ourselves to some irrational
                # slogans."
                #
                # Two universal claims have already broken here. "Not one of
                # these cities is having an ordinary summer" went false when
                # Berlin joined at the 70.9th percentile on nights. "Every
                # city in the set is elevated on days" went false when
                # Stockholm joined at 76.3. Both were true when written and
                # both were really claims about a set size.
                #
                # A COUNT CANNOT BREAK THAT WAY. It restates itself every run,
                # it is checkable against the table below it, and it does not
                # need defending when the set grows. "Some of these cities are
                # abnormally hot" is weaker as a slogan and stronger as a
                # statement, which is the correct trade.
                "claim": "{0} of these {1} cities are having their hottest "
                         "summer on record for days above their own extreme "
                         "threshold.".format(len(drecs), len(cities)),
                "at_day_record": len(drecs),
                "in_top_10pct": len(top10), "in_top_5pct": len(top5),
                "of_cities": len(cities),
                "not_elevated": [x["city"] for x in ldays
                                 if x["day_percentile"] is not None
                                 and x["day_percentile"] < ELEVATED_PCT],
                "framing_rule":
                    "NEVER phrase this as a universal. No 'none', 'not one', "
                    "'every' or 'all'. Two such claims have already gone false "
                    "here as the set grew, and both read as verified while "
                    "being wrong. State the count and let the reader see the "
                    "table.",
                "why_counts":
                    "A count is checkable against the cities listed beside it "
                    "and survives the set changing. A universal claim is a "
                    "slogan that has to be re-proved every time a city is "
                    "added, and nothing in the pipeline re-proves it.",
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
            "may_say_worst_on_record": nights_worst,
            "may_say_worst_note": nights_reason,
            "may_not_say": B["may_not_say"],
            "may_not_say_note":
                "Curated text, retained. Where it disagrees with "
                "may_say_worst_on_record above, the COMPUTED field wins: that "
                "one regenerates and this one does not.",
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
            # COMPUTED. This read True unconditionally, so a calm year would
            # have told a page it may claim the worst on record with zero
            # cities at one. Found by the extremes test, not by review.
            "may_say_worst_on_record": days_worst,
            "may_say_worst_note": days_reason,
        },
        "geography": {
            # COMPUTED, NOT WRITTEN. The previous version said "every city in
            # the set is elevated on days" and pinned the evidence as "the
            # lowest is Berlin at 87.3". Stockholm joined at 76.3 and the
            # claim became false while still reading as verified.
            #
            # That is the SECOND time a sentence true of one membership
            # survived into a larger one: the lead said "not one of these
            # cities is having an ordinary summer" until Berlin arrived. Both
            # were written as facts and were really facts-as-of-a-set-size.
            # So this one is generated from the data every run and cannot rot.
            "claim": ("The extreme is concentrated in the middle latitudes, "
                      "not at the hot end."),
            "lowest_day_percentile": {"city": low_city, "value": low_pct},
            "elevated_threshold_pct": ELEVATED_PCT,
            "elevated_threshold_note":
                "LOAD-BEARING FOR PROSE. The banned-word rule is defined "
                "against this number, so copy must read it here rather than "
                "hardcoding 85. Changing it changes what may be written.",
            "all_elevated_on_days": low_pct >= ELEVATED_PCT,
            "all_elevated_note":
                ("Every city in the set sits above the {2}th percentile of "
                 "its own day record; the lowest is {0} at {1}."
                 if low_pct >= ELEVATED_PCT else
                 "NOT every city is elevated: {0} sits at {1}, below the {2}th "
                 "percentile of its own record. A page must not say the whole "
                 "set is elevated.").format(low_city, low_pct,
                                            int(ELEVATED_PCT)),
            "banned_word": "ordinary",
            "banned_word_note":
                "No city ABOVE the {0}th percentile may be called ordinary. "
                .format(int(ELEVATED_PCT)) + 
                "Where all_elevated_on_days is false the lowest city may "
                "legitimately be described as having an unremarkable summer. "
                "STATE IT AND STOP: do not add a clause explaining what "
                "naming it proves. Editor's rule 2026-08-08, and the reason "
                "is that the exception persuades by being there, and arguing "
                "that it persuades converts it back into an argument.",
            # `band` REMOVED, product ratified 2026-08-10. It held a fixed
            # 38N to 51N, a v1.2 finding about a 24-city set, and by 36 it
            # excluded ten cities including Helsinki at 60.2N and Stockholm
            # at 59.3N. Nothing rendered it, so it was never a live defect.
            #
            # DROPPED RATHER THAN REGENERATED, and that is the whole point:
            # regenerating it would have preserved a claim we would not make
            # today. A latitude band was an answer about a set that no longer
            # exists, and the honest move is to stop asserting it rather than
            # to keep it arithmetically current.
            #
            # This is the counterpart to the day's other lesson. Most stale
            # fields want assembling from the data. Some want deleting, and
            # telling them apart is asking whether we would write the claim
            # fresh today.
            "band": None,
            "band_removed_note":
                "A fixed latitude band was a finding about the 24-city set. "
                "It is not regenerated, because the claim itself is one we "
                "would not make now: the set spans 36.7N to 60.2N and no "
                "band describes it.",
            "least_extreme_on_days": ldays,
            "mechanism": None,
            "mechanism_note":
                "DELIBERATELY ABSENT. Stating the geography is measurement; "
                "explaining it is speculation. The page says where, not why.",
            "map": {
                "colour_by": "percentile within each city's own record",
                "never_colour_by": "absolute temperature, which would redraw "
                                   "the Mediterranean climate map rather than "
                                   "this summer",
                # A zero-width domain divides by zero in a renderer. When
                # every city is at a record the floor collapses to 100, which
                # the extremes test produced immediately. Floored to a usable
                # span rather than left for design to discover.
                "scale_domain": [min(low_pct, 100.0 - MIN_SCALE_SPAN), 100.0],
                "scale_domain_floored": low_pct > 100.0 - MIN_SCALE_SPAN,
                "scale_domain_note":
                    "Computed from the set, not fixed. On a 0-100 ramp every "
                    "mark crowds the top sliver and the set reads as uniformly "
                    "extreme, which is both less informative and less true. "
                    "DO NOT use a diverging cool-to-hot scale: it would imply "
                    "cities are cool, and above the 85th percentile none is.",
                "quiet_cities": "must be visibly quiet, never absent. Their "
                                "presence is what makes the map evidence "
                                "rather than decoration.",
                "not_a_surface": "marks, not an interpolated field. This is "
                                 "one thermometer per city and must not read "
                                 "as a European temperature map.",
                "points": [
                    {"city": c, "lat": _coord(c)[0], "lon": _coord(c)[1],
                     "coord_source": _coord(c)[2],
                     "day_percentile": v["days"]["rank"]["percentile"],
                     "night_percentile": v["rank"]["percentile"],
                     "night_metric_holds": c in ok_cities}
                    for c, v in sorted(cities.items())],
                # PROVENANCE TRAVELS WITH THE POINT, not in a sibling file.
                # station_coords.json existed for a whole afternoon carrying
                # nine resolved coordinates that nothing downstream read,
                # because the resolver was committed and never wired in here.
                # Design found it by checking which nine had moved. Building
                # the better data is not the same as shipping it.
                "coord_resolution": {
                    "resolved": sum(1 for c in cities
                                    if _coord(c)[2] != "hand_typed"),
                    "total": len(cities),
                    "means": "the mark is the STATION, which is what the "
                             "disclosure names and what completeness is "
                             "measured on, not the city centre.",
                    "hand_typed_means": "typed by me at 1 dp with no source, "
                                        "off by 3 to 15 km where checked. "
                                        "Legible rather than passing as "
                                        "sourced.",
                },
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
        # THE MOST IMPORTANT LIMIT ON THIS PAYLOAD, and the easiest to forget
        # because every individual number is correct. Kristjan, 2026-08-08:
        # "you should also know about us picking cities that were in the hot
        # area of the map. If we would take all European cities, the data
        # would be very different."
        "coverage": coverage,
        "selection": {
            "is_representative_of_europe": False,
            "cities": len(cities),
            "by_country": {k: sum(1 for v in cities.values()
                                  if v["country"] == k)
                           for k in sorted({v["country"]
                                            for v in cities.values()})},
            "longitude_span": [
                round(min(_coord(c)[1] for c in cities), 1),
                round(max(_coord(c)[1] for c in cities), 1)],
            "latitude_span": [
                round(min(_coord(c)[0] for c in cities), 1),
                round(max(_coord(c)[0] for c in cities), 1)],
            "selection_is_deliberate": True,
            "how_these_cities_were_chosen":
                "ON PURPOSE, toward where the abnormality is. That is what "
                "this channel is for: showing where the extremes are and how "
                "hard, not estimating a continental average. The first "
                "fifteen were Spanish and French because the tropical-night "
                "measure only works where tropical nights are common. "
                "Germany and Austria reached north, Amsterdam was added "
                "where heat was expected, and Stockholm was added to include "
                "a city that was not extreme.",
            "forecast_selected_cities": ["Bordeaux", "Toulouse", "Strasbourg",
                                         "Hanover", "Stuttgart", "Geneva"],
            "forecast_selected_note":
                "A NEW SELECTION CRITERION, added 2026-08-09 and recorded "
                "because it differs from the rest. Every earlier city was "
                "chosen for where the abnormality HAD BEEN, or for where the "
                "metric works. These six were chosen from a MODEL FORECAST of "
                "the following week, all sitting +10 to +13 C above their "
                "recent-August normal, and all on fetchers already built. "
                "Their published figures remain pure observation; only the "
                "decision to measure them was forecast-driven. Hanover is the "
                "honest illustration: third-largest forecast anomaly in "
                "Europe and currently 8th of 88 on observations.",
            "not_an_apology":
                "Purposive selection is the right design for this channel "
                "and is not a defect to be corrected. The only thing it "
                "forbids is generalising a proportion to a population we did "
                "not sample.",
            "what_may_not_be_said":
                "NOTHING HERE SUPPORTS A CLAIM ABOUT EUROPE. Not 'Europe is "
                "having its hottest summer', not 'European cities are "
                "breaking records', not a proportion presented as if the set "
                "were a sample of the continent. Every count is a count of "
                "THESE cities, chosen the way described above.",
            # ASSEMBLED, NOT TYPED, and design found why it has to be. These
            # three sentences had gone stale against the machine fields
            # beside them: "the map is 24 marks" next to cities: 36,
            # "fifteen of the 24 are Iberia and France" when it is 18 of 36,
            # and "no city east of 18.1 E" when Helsinki is at 24.9.
            #
            # The third is the one that changes a conclusion rather than a
            # count. The bound was true when Stockholm was the easternmost
            # city, and it stopped being true when Helsinki arrived, so a
            # chat reading the field could not tell whether the conclusion
            # it supports had survived the city that broke it.
            #
            # THE WORST PLACE IN THE PAYLOAD TO CARRY A STALE NUMBER, because
            # these are the fields that tell another chat what it may not
            # say. cities: 36 updated itself and the prose that scopes it did
            # not, which is the Vienna collision again: a figure and the
            # thing that bounds it, separated, with the bounding half going
            # stale.
            "what_may_be_said":
                "Each city against its own record, and the pattern across "
                "this set stated as a pattern across this set. WHERE THE "
                "ABNORMALITY IS AND HOW HARD, which is the thing these "
                f"cities were chosen to show. The map is {len(cities)} marks "
                f"and means what those {len(cities)} thermometers recorded.",
            "known_absences":
                f"No city east of "
                f"{max(_coord(c)[1] for c in cities):.1f} E. No Italy, "
                "Greece, Portugal or the UK. "
                + (lambda n: f"{n} of {len(cities)} are Iberia and France.")(
                    sum(1 for v in cities.values()
                        if v["country"] in ("ES", "FR"))),
            "known_absences_note":
                "The longitude bound is DERIVED and moves when a city is "
                "added. Which countries it excludes is a judgement that has "
                "to be re-read against it, not carried forward: this "
                "sentence previously said 18.1 E and named Poland, the "
                "Baltics, the Balkans, Ukraine and European Russia, and kept "
                "saying so after Helsinki moved the bound to 24.9 E.",
            "if_you_wanted_a_european_average":
                "You would need a different set, chosen at random or by "
                "population, and it would show a smaller share at a record. "
                "That is a different product and we are not making it. "
                "Stated so the distinction is explicit rather than so the "
                "selection reads as a flaw.",
        },
        "coverage_note":
            "Seven countries, listed in selection.by_country. The 20 C night "
            "metric does not work in the northern half of the set, which is "
            "why the percentile night series exists and why ten cities are "
            "night-gated.",
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
    # Does the emitted permission match what the counts actually say? This
    # checks CONSISTENCY, not a particular answer, so it holds in a calm year
    # and a record year alike.
    # Expected now includes the leave-one-out test, because the rule does.
    # This guard fired when the rule changed and the guard did not, which is
    # the guard being right rather than in the way.
    for label, emitted, expected in (
            ("nights", nights_worst,
             len(recs) > nbase["worst_year_on_record"]["cities"]
             and _n_sub > _pre_n_sub["worst_year_on_record"]["cities"]),
            ("days", days_worst,
             len(drecs) > dbase["worst_year_on_record"]["cities"]
             and _d_sub > _pre_d_sub["worst_year_on_record"]["cities"])):
        # THE ARITHMETIC CHECK NOW ONLY APPLIES IN ONE DIRECTION. Product
        # ruled 2026-08-10 that a cross-year record count is not publishable
        # from this set at all, so the flag is forced False regardless of
        # what the counts say. Emitting False while the counts say True is
        # now the CORRECT state, not a drift.
        #
        # The guard is kept for the other direction, which is the dangerous
        # one: True while the counts say False would claim something the data
        # does not support. It fired correctly when I forced the flag and
        # had not yet taught it the ruling, which is the guard being right
        # rather than in the way.
        if emitted and not expected:
            print(f"  FAIL: {label} may_say_worst_on_record is True but "
                  f"the counts say False. The copy would claim something "
                  f"the data does not support.", file=sys.stderr)
            return 1

    drift = check_prose_contract(payload)
    if drift:
        print(f"  FAIL: prose contract drifted, copy would silently change "
              f"meaning: {drift}", file=sys.stderr)
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
