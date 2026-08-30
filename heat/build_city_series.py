"""Derive the per-city night and day series from the PUBLISHED sources only.

This file exists because the payload used to name one source and read
another. Every Spanish city ranked an AEMET 2026 against an ECA&D history,
and every French city named Meteo-France while reading ECA&D too. Both were
invisible to spot checks, because the 2026 value was always genuinely from
the named source; only the history was borrowed.

ECA&D is non-commercial and cannot be published once a sponsor exists, so
it is gone from the pipeline rather than demoted. Nothing here reads it.

  Spain    AEMET OpenData, station identity matched, re-sourced 2026-08-06
  France   Meteo-France via data.gouv.fr, TN and TX from the same rows

The output is a compact derived series committed to heat/data/, the same
policy crops uses: the raw dailies stay in the gitignored cache, the
derived artifact is small enough to read in a diff.

CONSTANTS RATIFIED BY PRODUCT 2026-08-07, not chosen here:

  WINDOW_START / WINDOW_BAR   completeness measured over 1 May to the cut,
                              at 0.90. Measured, not asserted: across all
                              cities and years, 99.98% of tropical nights
                              fall on or after 1 May. The old bar of 330 of
                              365 days was measured over the whole year on
                              a series cut in early August, which discarded
                              Madrid 1936 (complete to the cut) and kept
                              years whose gaps sat in July.

  TIE_COUNTS_AGAINST          a tie is not a record. Resolving ambiguity
                              toward the more alarming reading is the D-043
                              defect, so it is resolved the other way and
                              stated rather than left implicit.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
OUT = ROOT / "heat" / "data" / "city_series.json"

# THE SEASON IS DERIVED PER STATION, NOT ASSUMED. Four constants used to
# encode a northern summer: this one, the July-August percentile filter, the
# May-August coverage window, and the bridge's fetch range. Buenos Aires'
# July mean maximum is 15.6 C, their COLDEST month, so pointing the
# instrument south unchanged would have derived a hot-day threshold from
# their two coldest months and published confident, entirely wrong numbers.
#
# NOT A HEMISPHERE SWITCH. The LatAm survey found THIRTEEN distinct hot
# seasons across 116 stations: Puerto Limon is August to October and Tlaxcala
# is March to May, neither of which is either hemisphere's summer. A
# north/south flag handles Argentina and breaks on Costa Rica.
#
# THE RULE: the threshold months are the two warmest CONSECUTIVE months of
# the station's own 1991-2020 record, and counting starts WINDOW_LEAD_MONTHS
# before the first of them.
#
# ZERO DRIFT IS BY CONSTRUCTION, NOT BY LUCK. All 46 cities in CITIES derive
# (7, 8) as their warmest consecutive pair, and two months before July is
# 1 May, so every existing city reproduces its current definition exactly.
# That was measured before this was written rather than hoped for afterwards.
#
# Consecutive, because a season is a run rather than a set: the two warmest
# months taken independently can be December and February, which is not a
# season, and a southern summer wraps the year boundary.
WINDOW_LEAD_MONTHS = 2

# Below this amplitude, hottest monthly mean minus coldest, a station has no
# hot season and this instrument does not apply to it. Sixteen of the 116
# LatAm stations sit under it, Tarapoto at 1.3 C, where the warmest pair is
# noise. Such a station gets no thresholds rather than a threshold derived
# from a distinction that does not exist. Four degrees because every city we
# publish is above twelve, so the bar refuses the tropics without coming near
# anything we currently carry.
MIN_SEASON_AMPLITUDE_C = 4.0

WINDOW_START = (5, 1)          # fallback only; derived per city in build()
WINDOW_BAR = 0.90
FULL_YEAR_DAYS = 330
TIE_COUNTS_AGAINST = True

# AEMET station ids, RESOLVED AND VERIFIED 2026-08-10.
#
# These existed nowhere in the repo. The cache was built with them ad hoc and
# only Madrid's ever reached the code, so when the pull broke on 2026-08-09
# Spain could not be refetched at all: eleven ids had to be rediscovered
# before a single day could be recovered. Spain sat stale through the peak of
# a heat event and I reported that gap to two chats as AEMET's publication
# lag, which it was not.
#
# RESOLVED BY NAME AND THEN VERIFIED, never trusted on the name alone. Every
# id was checked against our own cached series over summer 2025: 46 shared
# days each, 100.0% exact, worst difference 0.0 C. Name matching alone is the
# error that put an air base's history under Murcia's name, and the check is
# what makes these safe rather than the lookup.
#
# Murcia is 7178I, the CITY station, not the air base ECA&D blends in.
ES_STATION_ID = {
    "Madrid": "3195", "Barcelona": "0076", "Valencia": "8416",
    "Seville": "5783", "Malaga": "6155A", "Alicante": "8025",
    "Murcia": "7178I", "Palma": "B228", "Zaragoza": "9434",
    "Bilbao": "1082",
}


# STATION CLASS, product ruling 2026-08-12, prompted by readers on X asking
# whether Heathrow's record is inflated by the airport growing around it.
#
# OUR EXISTING FIELD ANSWERS THE WRONG QUESTION. station_history_checked says
# DID THE STATION MOVE. The challenge is DID ITS SURROUNDINGS CHANGE, and
# Heathrow can be clean on the first while being exactly what they mean.
#
# NOT DERIVED FROM THE NAME, and product's own search shows why: they looked
# for "airport" and found 7 of 42, missing Heathrow, because its station name
# is "Heathrow". The same substring misses Schiphol, Orly, Marignane,
# Merignac, Blagnac, Entzheim, Cointrin, Aldergrove, Dyce, Fuhlsbuettel,
# Klotzsche and Bromma. Every one is an airport and none says so.
#
# So this is an EXPLICIT TABLE, the same decision as ES_STATION_ID: a fact
# about each station, recorded once, rather than inferred from a string that
# was never meant to carry it.
#
# "unverified" MEANS NOT YET ESTABLISHED, NOT "not an airport". A city absent
# from the airport list has not been cleared; it has not been checked. That
# distinction is the whole reason station_history_checked needed a third
# state, and repeating the error one field over would be indefensible.
#
# NO DETECTOR. Product was explicit and they are right: we built one for
# relocations, calibrated it on 105 clean pairs, proved it had no power and
# kept it as marked dead code. Site-context change is harder than relocation
# and has no clean-pair set to calibrate against. State the class and stop.
STATION_CLASS = {
    # Airports, established from the station being the named civil airport
    # of that city. Where the name does not say so it is given here.
    "London": "airport",        # Heathrow
    "Amsterdam": "airport",     # Schiphol
    "Paris": "airport",         # Orly
    "Marseille": "airport",     # Marignane
    "Bordeaux": "airport",      # Merignac
    "Toulouse": "airport",      # Blagnac
    "Strasbourg": "airport",    # Entzheim
    "Lyon": "airport",          # Saint-Exupery
    "Montpellier": "airport",
    "Nice": "airport",          # Cote d'Azur, poste 06088001
    "Geneva": "airport",        # Cointrin
    "Cologne": "airport",       # Koeln/Bonn
    "Hamburg": "airport",       # Fuhlsbuettel
    "Dresden": "airport",       # Klotzsche
    "Stockholm": "airport",     # Bromma
    "Belfast": "airport",       # Aldergrove
    "Aberdeen": "airport",      # Dyce
    "Larnaca": "airport",
    "Rome": "airport",            # Ciampino
    "Budapest": "airport",        # Pestszentlorinc

    "Barcelona": "airport",
    "Bilbao": "airport",
    "Malaga": "airport",
    "Seville": "airport",
    "Zaragoza": "airport",
    # Named for a closed airport. Tempelhof ceased flying in 2008, so the
    # site's context CHANGED WITHIN OUR RECORD and in the opposite direction
    # to the objection being raised about Heathrow.
    "Berlin": "former airport",
    # City and observatory sites, established from the station name stating
    # the district or observatory rather than an aerodrome.
    "Madrid": "urban",          # Retiro park
    "Vienna": "urban",          # Hohe Warte observatory
    "Munich": "urban",          # Muenchen-Stadt
    "Helsinki": "urban",        # Kaisaniemi park
    "Prague": "suburban",       # Praha-Libus, southern edge, not central Karlov
    "Zurich": "urban",          # Fluntern, not Kloten airport
    "Stuttgart": "urban",       # Schnarrenberg
    "Basel": "suburban",        # Binningen observatory
    "Zagreb": "urban",          # Gric, the old city observatory
    "Vilnius": "urban",         # city station
    "Leipzig": "suburban",      # Holzhausen
}
STATION_CLASS_UNVERIFIED = (
    "Alicante", "Valencia", "Murcia", "Palma", "Frankfurt", "Hanover",
    "Lugano", "Nottingham", "Tallinn",
)

CURRENT_YEAR = 2026
TROPICAL_NIGHT_C = 20.0
PCTL_BASELINE = (1971, 2000)

# BASELINE PERIOD, SELECTED BY RULE. Product D-151, 2026-08-11, with two
# tightenings they added to what I proposed.
#
# TWO PERIODS, NOT THREE. 1961-1990 is excluded because it is the only one
# that runs the wrong way: it is the coolest normal, so it gives a LOWER
# threshold and an OVERSTATED count, which is the D-043 direction we refuse.
# And no station reporting today can plausibly need it, since a complete
# 1961-1990 alongside an incomplete 1991-2020 describes a station that has
# stopped. Excluding it costs nothing and removes the only unsafe branch.
#
# NOBODY CHOOSES. I proposed a per-city declaration; product removed the
# choice entirely, on my own argument that the fix for a knob is removing it
# rather than being careful with it. The rule is:
#
#     prefer 1971-2000. If not complete at 30/30, use 1991-2020 if complete
#     at 30/30. Otherwise the city gets no thresholds.
#
# So the safe direction is structural rather than a fact about Tallinn.
# SCOPE THE SEASON WORK AS "DERIVE PER STATION", NOT "HANDLE THE SOUTHERN
# HEMISPHERE". Aftereffects' note, 2026-08-22, and it is worth more than the
# question that prompted it: scoped as a hemisphere switch this needs doing
# twice.
#
# The survey found THIRTEEN distinct hot seasons across 116 LatAm stations,
# not two. Puerto Limon is August to October and Tlaxcala is March to May,
# and neither is either hemisphere's summer. A north/south flag handles
# Argentina and breaks on Costa Rica.
#
# And the northern cases are not uniform either. Northern high-latitude
# stations sit awkwardly under a July-August calibration and a 1 May count
# for reasons that have nothing to do with hemisphere, so a station in
# Siberia would need the same treatment as one in Mendoza.
#
# The four places the assumption is hardcoded: WINDOW_START below,
# PCTL_BASELINE's July-August filter, the coverage window in build(), and
# the bridge's fetch range. All four are per-station questions.

WMO_NORMALS = [(1971, 2000), (1991, 2020)]


def derive_season(tx, lo=1991, hi=2020):
    """The two warmest consecutive months of this station's own record.

    Returns (months, amplitude) or (None, amplitude) where the station has no
    season worth calibrating against. Measured over 1991-2020, the WMO
    current standard normal, and requiring all twelve months present so a
    station with a seasonal gap cannot win by absence.
    """
    mon = {}
    for y, dd in tx.items():
        if not (lo <= y <= hi):
            continue
        for (m, _d), v in dd.items():
            if v is not None:
                mon.setdefault(m, []).append(v)
    means = {m: sum(v) / len(v) for m, v in mon.items() if len(v) >= 60}
    if len(means) < 12:
        return None, None
    amp = max(means.values()) - min(means.values())
    if amp < MIN_SEASON_AMPLITUDE_C:
        return None, round(amp, 1)
    best = run = None
    for start in range(1, 13):
        ms = [((start - 1 + k) % 12) + 1 for k in range(2)]
        val = sum(means[m] for m in ms) / 2
        if best is None or val > best:
            best, run = val, ms
    return tuple(run), round(amp, 1)


def season_window(months):
    """Counting starts WINDOW_LEAD_MONTHS before the season, and the coverage
    window is the season plus that lead.

    For (7, 8) this returns (5, 1) and months 5, 6, 7, 8, which is exactly
    what the four constants used to hardcode.
    """
    first = months[0]
    start_m = ((first - 1 - WINDOW_LEAD_MONTHS) % 12) + 1
    cover = []
    for k in range(WINDOW_LEAD_MONTHS + len(months)):
        cover.append(((start_m - 1 + k) % 12) + 1)
    return (start_m, 1), tuple(cover)


def _ja_days(series, lo, hi, years=None, months=(7, 8)):
    """Pooled in-season daily values across a window."""
    return [v for y in range(lo, hi + 1) if years is None or y in years
            for (m, _d), v in series.get(y, {}).items()
            if m in months and v is not None]


def _shortfall_is_immaterial(series, lo, hi, missing, present,
                             months=(7, 8)):
    """Can the missing years move a published threshold? Measured, not waived.

    THE TEST. Refill each missing year twice, once with the July-August days
    of the window's COOLEST present year and once with its WARMEST, and
    recompute the 90th, 95th and 99th percentiles under both. If all three
    round to the same 0.1 C either way, no value the missing year could have
    held would change a number we publish, so the gap is immaterial to the
    threshold rather than merely small.

    WHY THE EXTREMES AND NOT THE MEAN. Imputing the window mean would assume
    the answer: a missing year filled with the average cannot move an average.
    The extremes bound what the year could have been, and the bound is what
    makes the shortfall safe to carry rather than convenient to ignore.

    D-043 lives here. A missing baseline year that came in HOT would raise the
    threshold and cut our count; one that came in COLD would lower it and
    inflate our count. Testing only one side would leave exactly the alarming
    direction untested.
    """
    import numpy as _np
    # THE SEASON MUST BE PASSED IN. This defaulted to July-August, which is
    # the northern summer and Trelew's WINTER. The shortfall test therefore
    # refused a southern city on whether a missing year would move a
    # percentile we never publish for it. The refusal looked identical to
    # Algiers' legitimate one, which is why it took a disagreeing number to
    # find: the test reported P95 20.6 for a station whose summer P95 is 36.
    base = _ja_days(series, lo, hi, present, months)
    if not base or not missing:
        return True, {}
    by_year = {y: _ja_days(series, y, y, months=months) for y in present}
    by_year = {y: v for y, v in by_year.items() if v}
    if not by_year:
        return False, {}
    cold = min(by_year, key=lambda y: sum(by_year[y]) / len(by_year[y]))
    warm = max(by_year, key=lambda y: sum(by_year[y]) / len(by_year[y]))
    out = {}
    for tag, donor in (("cold", cold), ("warm", warm)):
        pool = base + by_year[donor] * len(missing)
        out[tag] = {p: round(float(_np.percentile(pool, p)), 1)
                    for p in (90, 95, 99)}
    same = all(out["cold"][p] == out["warm"][p] for p in (90, 95, 99))
    out["donors"] = {"cold": cold, "warm": warm}
    return same, out


def shortfall_effect(tx, lo, hi, missing, present, season, counts_fn,
                     pct=95):
    """What does the gap do to the PUBLISHED count, not to the threshold?

    THE OLD TEST ASKED THE WRONG QUESTION and Kristjan caught it. It refused a
    city when the missing year could move the THRESHOLD, which is an
    intermediate value no reader sees. The claim is the COUNT. Trelew's
    threshold moves 0.2 C and its count is five days either way, at rank 22 of
    55 either way, so nothing a reader would ever see changes and the city was
    being refused for nothing.

    That is precisely the error design caught in the withdrawn-record test,
    where I checked the rank number instead of the claim. I fixed it there and
    did not carry it here.

    Refills each missing year from the coldest and the warmest year in the
    window and returns the range the current season's count could take.
    Returns None when there is nothing to assess.
    """
    # THE RANGE MUST COUNT WHAT THE PAGE COUNTS. My first version counted
    # the threshold months only, while the payload counts the whole window to
    # the cut, so the disclosure read "9 to 12 days" beside a published count
    # of 13. A caveat that contradicts the number it qualifies is worse than
    # no caveat: the reader cannot tell which is wrong.
    #
    # The threshold is still built from the season months, because that is
    # what calibrates it. Only the COUNTING uses the page's own window.
    def in_season(y):
        return [v for (m, _), v in tx.get(y, {}).items() if m in season]

    def counted(y):
        return [v for k, v in tx.get(y, {}).items() if counts_fn(k, y)]

    base = [y for y in range(lo, hi + 1) if len(in_season(y)) >= 40]
    if not base or not missing:
        return None
    by = {y: in_season(y) for y in base}
    cold = min(by, key=lambda y: sum(by[y]) / len(by[y]))
    warm = max(by, key=lambda y: sum(by[y]) / len(by[y]))
    counts, ranks, ths = [], [], []
    for donor in (cold, warm):
        pool = [v for y in base for v in by[y]] + by[donor] * len(missing)
        t = float(np.percentile(pool, pct))
        cnt = {y: sum(1 for v in counted(y) if v > t)
               for y in range(lo, 2027) if len(counted(y)) >= 40}
        if not cnt:
            return None
        last = max(cnt)
        order = sorted(cnt, key=lambda y: -cnt[y])
        counts.append(cnt[last]); ranks.append(order.index(last) + 1)
        ths.append(round(t, 1))
    return {
        "missing_years": list(missing),
        "threshold_range_c": sorted(set(ths)),
        "count_range": sorted(set(counts)),
        "rank_range": sorted(set(ranks)),
        "count_moves": counts[0] != counts[1],
        "rank_moves": ranks[0] != ranks[1],
    }


def pick_baseline(tx, tn, cover=(5, 6, 7, 8), season=(7, 8),
                  counts_fn=None):
    """The first standard normal that qualifies, in the fixed order above.

    Returns (lo, hi, missing_years). Complete means 30 of 30 years carrying
    at least 100 May-August days with both extremes, and a complete window
    always wins outright.

    THE SHORTFALL BRANCH, and why it is not the knob product deleted in D-151.
    Kristjan's instruction 2026-08-13 was to make Algiers an exception. A
    per-city waiver would have been three lines and would have reintroduced
    exactly the per-city declaration product removed, against his own standing
    rule that nothing in heat is hardcoded to a city.

    So the exception is a PROPERTY OF THE DATA, not of the city. A window
    short by up to MAX_SHORTFALL_YEARS qualifies only if the missing years
    provably cannot move its thresholds, tested at both extremes above. Any
    city passing that test qualifies; Algiers is not named anywhere in it, and
    if Algiers stops passing it, it stops qualifying with no edit here.

    The shortfall is then carried as a field, never as prose beside the number
    (D-051), so a page built on 29 of 30 years says so from the datum.
    """
    per = {}
    for y, dd in tx.items():
        n = sum(1 for (m, _d), v in dd.items()
                if m in cover and v is not None)
        per[y] = n
    for lo, hi in WMO_NORMALS:
        yrs = range(lo, hi + 1)
        present = {y for y in yrs if per.get(y, 0) >= 100}
        if len(present) == hi - lo + 1:
            return (lo, hi, (), None)
    for lo, hi in WMO_NORMALS:
        yrs = range(lo, hi + 1)
        present = {y for y in yrs if per.get(y, 0) >= 100}
        missing = tuple(y for y in yrs if y not in present)
        if not missing or len(missing) > MAX_SHORTFALL_YEARS:
            continue
        # THE CLAIM DECIDES, NOT THE THRESHOLD. Kristjan's ruling 2026-08-30.
        eff = shortfall_effect(tx, lo, hi, missing, present, season,
                               counts_fn)
        if eff is None:
            continue
        if not eff["count_moves"] and not eff["rank_moves"]:
            print(f"    baseline {lo}-{hi} short {len(missing)} "
                  f"({', '.join(map(str, missing))}), but the published count "
                  f"is {eff['count_range'][0]} and the rank "
                  f"{eff['rank_range'][0]} at BOTH extremes: immaterial")
            return (lo, hi, missing, None)
        # The count moves, so the city is publishable only WITH the range
        # stated as a field. Kristjan: launch them, say plainly what is
        # missing. A point estimate here would be a number we cannot defend.
        print(f"    baseline {lo}-{hi} short {missing}: count ranges "
              f"{eff['count_range']}, rank {eff['rank_range']}. Publishable "
              f"WITH the gap disclosed.")
        return (lo, hi, missing, eff)
    return None


COMPARE_EARLY = (1961, 1990)
COMPARE_RECENT = (2011, 2025)
MIN_BASELINE_YEARS = 27          # of 30; below this a multiple is not comparable
# A window may be short by at most this many years, and only if the missing
# years provably cannot move its thresholds. Two, so a single bad year plus
# its neighbour is reachable and a decade of gaps is not.
MAX_SHORTFALL_YEARS = 2

# WHEN EACH CITY JOINED THE SET, AND WHY. A field because a caveat that lives
# in a message is a caveat the page cannot carry.
#
# Budapest went live on 22 August claiming "the most hot days Budapest has
# recorded", its first appearance, at 45 times the 1961-1990 rate, the highest
# multiple in the set, with NOTHING on the page saying it had joined three
# days earlier. I had put that caveat to product, to socials and to design in
# prose and never emitted it, so there was nothing for design to render. That
# is D-141's exact exposure: a set assembled with knowledge of the current
# year, where a new city arriving at a record reads as chosen for its number.
#
# The rule these three were chosen under is the defence, and it only works if
# the reader can see it: they were selected because the region was uncovered,
# BEFORE anyone looked at their 2026 figures.
# DATES VERIFIED AGAINST GIT, NOT TYPED FROM MEMORY. Three of these were
# wrong when first written: Budapest, Vilnius and Zagreb read 2026-08-19 and
# git's first appearance of each in CITIES is 2026-08-17. The wrong date was
# live on three pages inside an hour of the field being created.
#
# Aftereffects' point, the same day: a confident FIELD can stand in for a
# confident sentence. Emitting the caveat as a field rather than saying it in
# a message fixed one failure and left the other one open, because nothing
# checks that a hand-typed date is true. Recover it with:
#   git log --format=%ad --date=short -S'"<City>":' -- heat/build_city_series.py
JOINED = {
    "Larnaca":  ("2026-08-12", "Cyprus was the only Mediterranean island in "
                               "range with a long record and no coverage."),
    "Tallinn":  ("2026-08-11", "Baltic coverage, chosen for the gap."),
    "Nottingham": ("2026-08-11", "A second English city outside London."),
    "Belfast":  ("2026-08-11", "Northern Ireland, uncovered."),
    "Aberdeen": ("2026-08-11", "Scotland, uncovered."),
    "Budapest": ("2026-08-17", "Central and eastern Europe was three cities "
                               "of forty-two. Selected for the gap, before "
                               "its 2026 figures were looked at."),
    "Vilnius":  ("2026-08-17", "As Budapest: the Baltic and eastern gap."),
    # Argentina, added 2026-08-30 while their season is dormant.
    "Santiago del Estero": ("2026-08-30", "The southern hemisphere was zero "
                            "cities. Selected for the gap, months before the "
                            "summer it will measure."),
    "Parana":    ("2026-08-30", "As Santiago del Estero."),
    "Laboulaye": ("2026-08-30", "As Santiago del Estero."),
    "Mar del Plata": ("2026-08-30", "As Santiago del Estero, and the only "
                      "coastal station in the Argentine set."),
    "Neuquen":   ("2026-08-30", "As Santiago del Estero, and the "
                  "northern-Patagonian end of the set."),
    "Salta":     ("2026-08-30", "As Santiago del Estero."),
    "Algiers":  ("2026-08-30", "North Africa was zero cities."),
    "Rome":     ("2026-08-30", "Italy was zero cities."),
    "Trelew":   ("2026-08-30", "As the other Argentine stations."),
    "Zagreb":   ("2026-08-17", "The Balkans were zero cities. Selected for "
                               "the gap, before its 2026 figures were "
                               "looked at."),
}
# A city entering at or near its own record within this many days of joining
# carries the caveat on the page. Thirty days, because the reader's question
# is "did you add this city because it was hot", and that question is live for
# as long as the addition is recent enough to have been motivated by it.
JOINED_CAVEAT_DAYS = 30

MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

CITIES = {
    "Madrid":      dict(country="ES", station="MADRID, RETIRO", cut=(8, 2)),
    "Barcelona":   dict(country="ES", station="BARCELONA AEROPUERTO", cut=(8, 2)),
    "Valencia":    dict(country="ES", station="VALENCIA", cut=(8, 2)),
    "Seville":     dict(country="ES", station="SEVILLA AEROPUERTO", cut=(8, 2)),
    "Malaga":      dict(country="ES", station="MALAGA AEROPUERTO", cut=(8, 2)),
    "Alicante":    dict(country="ES", station="ALACANT/ALICANTE", cut=(8, 2)),
    # 7178I, the CITY station, not 7228 "ALCANTARILLA, BASE AEREA" ~10 km
    # away. The pairing had matched ECA&D by NAME; ECA&D publishes this
    # series under the Alcantarilla name while splicing the city station in
    # for recent decades, so name-matching paired the history with the air
    # base while the live 2026 value came from the city. Measured: ECA&D is
    # 99.99% identical to 7178I from 1990 on and 2.01% identical to 7228.
    # A blended reference agrees perfectly until the splice, so only an
    # era-by-era comparison finds it. Costs 43 years of record and is the
    # station the page is named after.
    "Murcia":      dict(country="ES", station="MURCIA", cut=(8, 2),
                        file="aemet_MurciaCity.json"),
    "Palma":       dict(country="ES", station="PALMA, PUERTO", cut=(8, 2)),
    "Zaragoza":    dict(country="ES", station="ZARAGOZA, AEROPUERTO", cut=(8, 2)),
    "Bilbao":      dict(country="ES", station="BILBAO AEROPUERTO", cut=(8, 2)),
    # LONDON, added 2026-08-10. The only city whose history and current
    # season reach us by different transports, both from the same
    # thermometer at Heathrow: MIDAS Open for 1949-2025 under the Open
    # Government Licence, and the station's own SYNOP bulletins for 2026,
    # because MIDAS Open publishes annually in arrears.
    #
    # Assembled by heat/build_london.py into the ordinary cache shape, so
    # nothing here or downstream knows about the split. Provenance is
    # emitted separately in heat/data/london_provenance.json.
    #
    # THE 2026 SEASON IS PROVISIONAL. Its licence is unresolved and the Met
    # Office Library Team is sending the official file. When it lands,
    # rerun the builder and this entry does not change.
    "London":    dict(country="UK", station="Heathrow", cut=(8, 10),
                      file="london.json"),
    # TALLINN, added 2026-08-11, DAYS ONLY and the omission is deliberate.
    #
    # I told Kristjan and product this was a summer-2027 city. It was
    # reachable the whole time, and the reason I missed it is the same bad
    # rule that cost London, Athens and Rome: I concluded from Tallinn that
    # SYNOP carries maxima and not minima, and generalised it. Re-tested
    # against GHCN for summer 2025, the truth is narrower and stranger:
    #
    #     Tmax @ 18Z   93.7% exact, 98.4% within 0.5 C, bias -0.01
    #     Tmin @ 06Z   48.5% exact, 67.6% within 0.5 C, bias +0.56, worst 4.9
    #
    # So the observation was right ABOUT TALLINN and wrong as a rule. The
    # 06Z window does not reliably contain the night's true minimum here, so
    # a derived minimum sits WARM, which is the same failure a sampled
    # minimum has.
    #
    # THEREFORE NO 2026 MINIMA ARE EMITTED AT ALL. Not a flagged value, not
    # a best effort: absent. A warm-biased minimum would understate tropical
    # nights while looking like a measurement, and this channel has spent a
    # week removing exactly that shape.
    #
    # History is GHCN EN000026038, network 0 rather than ECA&D, so it is
    # commercially usable: 1936-2025, 30 of 30 baseline years.
    # TALLINN: OUT, and now for a MEASURED reason rather than a guess.
    #
    # Keskkonnaagentuur sent their archive 2026-08-11. It contains FOUR
    # Tallinn stations in relay, not one record:
    #
    #     Majakas    1919-1949        Ulemiste   1937-1980
    #     Kose       1948-1964        Harku      1980-2026
    #
    # Harku is the station the collector and the SYNOP bulletins report, and
    # alone it runs 1980-2026: 21 of the 30 baseline years, below the bar of
    # 27. So Tallinn does not qualify on a single station.
    #
    # AND THE ROUTE I NEARLY SHIPPED WAS THE MURCIA ERROR AGAIN. GHCN
    # EN000026038 advertises 1936-2025 with 30 of 30 baseline years, which is
    # why it looked like the answer this morning. Measured against the
    # Estonian archive:
    #
    #     GHCN vs Harku     1980-1989   100.00% identical
    #     GHCN vs Harku     1990-2025    66.90%
    #     GHCN vs Ulemiste  1960-1979    75.89%
    #
    # Perfect agreement with one station for one decade, then divergence.
    # That is a blended series, and a days-only Tallinn built on it would
    # have ranked a 2026 Harku value against a history that is not Harku.
    #
    # So Tallinn waits for Harku to accumulate baseline years, or for a
    # documented same-site continuation we can verify. The hourly collector
    # keeps running: it is still the only route to true minima at this site.
    # NOTTINGHAM, BELFAST and ABERDEEN, added 2026-08-11. Same pattern as
    # London and built by heat/build_uk.py: MIDAS Open for the history under
    # the Open Government Licence, and the Met Office National
    # Meteorological Library and Archive for the 2026 season, Crown
    # Copyright with acknowledgement.
    #
    # Station identity was verified BEFORE any of this was built, by three
    # independent sources agreeing: MIDAS coordinates, the SYNOP station's
    # OGIMET coordinates, and the Met Office workbook's own header. Then
    # validated day by day against summer 2025, 100% of days within 0.5 C.
    #
    # Nottingham is the case that needed it. Its SYNOP station is called
    # "Nottingham Weather Centre" and its MIDAS record is "nottingham-
    # watnall", and MIDAS lists three Nottingham stations. The name says
    # nothing; 53.006,-1.251 on both sides says everything.
    #
    # Newcastle, Edinburgh and Birmingham were rejected here: their
    # currently reporting stations opened in 2003, 1998 and 1997, so none
    # covers the 1971-2000 baseline.
    "Nottingham": dict(country="UK", station="Nottingham Watnall", cut=(8, 10),
                       file="nottingham.json"),
    "Belfast":   dict(country="UK", station="Belfast Aldergrove", cut=(8, 10),
                      file="belfast.json"),
    "Aberdeen":  dict(country="UK", station="Aberdeen Dyce", cut=(8, 10),
                      file="aberdeen.json"),
    # TALLINN, in on product's ruling 2026-08-11. Harku alone, 1980-2026,
    # built by heat/build_tallinn.py from Keskkonnaagentuur's archive.
    #
    # Its percentile thresholds use 1991-2020, the WMO CURRENT standard
    # normal, because Harku gives 21 of 30 years on our 1971-2000 default
    # and 30 of 30 on this one. A complete later normal, not a shortened
    # earlier one, and the direction understates rather than overstates.
    #
    # The three other Tallinn stations in that archive are not read. Four
    # stations in relay are not one record.
    "Tallinn":   dict(country="EE", station="Tallinn-Harku", cut=(8, 10),
                      file="tallinn.json"),
    # LARNACA, added 2026-08-11, and the first city outside Europe proper.
    # Prompted by a reader asking what is happening in Cyprus and North
    # Africa, which our set could not answer at all.
    #
    # Built by heat/build_bridge.py: GHCN 1976-2016 plus the station's own
    # SYNOP bulletins for 2014-2026, one station, two transports. Validated
    # on summer 2016, the last year both hold: 100.0% of days exact at 06Z
    # and 18Z, worst 0.0 C.
    #
    # Uses the 1991-2020 normal under D-151: the station opened in 1976 so
    # 1971-2000 can never pass, and 1991-2020 is complete at 30/30 only
    # because the bridge reaches back to 2014. GHCN holds 2014-2016 at 61,
    # 72 and 63 days, below the bar, so the gap began where the archive
    # THINNED rather than where it ended.
    #
    # THE 2026 SEASON IS BULLETIN-SOURCED AND ITS LICENCE IS UNRESOLVED.
    # Same position London was in before the Met Office supplied its own
    # file. The Cyprus Department of Meteorology is the equivalent ask.
    "Larnaca":   dict(country="CY", station="Larnaca Airport", cut=(8, 10),
                      file="larnaca.json"),
    # EASTERN AND SOUTHERN EUROPE, added 2026-08-13. Each is GHCN history
    # bridged to the present with the station's own WMO bulletins, the same
    # construction as Larnaca and validated the same way.
    #
    # THESE WERE ADDED WHILE UNREMARKABLE, ON PURPOSE. Rome sits well below
    # Paris and is not in the August event; Vilnius and Zagreb are not either.
    # Adding a city because it is hot is the selection effect D-141 killed, and
    # the option to add a region uncontaminated expires the moment a forecast
    # verifies. A quiet city beside a loud one is what makes the loud one
    # credible.
    #
    # One station in Rome is not Italy, one in Zagreb is not the Balkans. That
    # limit lives in record_scope and the station disclosure, not in prose.
    "Rome":      dict(country="IT", station="Roma/Ciampino", cut=(8, 13),
                      file="rome.json"),
    "Vilnius":   dict(country="LT", station="Vilnius", cut=(8, 13),
                      file="vilnius.json"),
    "Zagreb":    dict(country="HR", station="Zagreb-Gric", cut=(8, 13),
                      file="zagreb.json"),
    # Budapest can never hold 1971-2000: GHCN begins 1973. If it qualifies at
    # all it is on 1991-2020, where it sits two years short and therefore
    # depends on the measured shortfall test rather than on being wanted.
    "Budapest":  dict(country="HU", station="Budapest/Pestszentlorinc",
                      cut=(8, 10), file="budapest.json"),
    # ALGIERS CARRIES A 29 OF 30 BASELINE, on Kristjan's instruction of
    # 2026-08-13 after the gap was shown to be unclosable. 1999 is absent from
    # GHCN at 88 minima and 85 maxima, OGIMET's bulletins do not reach it, and
    # NCEI's ISD-Lite holds the days but only as sampled observations: checked
    # against summer 2000, that transport understates the daily maximum by
    # 0.63 C on a day with 23 observations, and 1999 has a median of 9. Filling
    # the gap that way would have biased the BASELINE cool and pushed 2026's
    # rank up, which is the one direction D-043 forbids.
    #
    # It qualifies on the measured test in pick_baseline, not on being Algiers.
    # ARGENTINA. Six stations, identity PROVEN against each one's own GHCN
    # archive rather than parsed from its id, and bridged with whole-year
    # bulletins because these peak in December and January. Trelew is proven
    # and held at 29/30; Buenos Aires is not buildable at all, its baseline
    # and its present sitting on two different thermometers 5 km apart.
    #
    # Added while their season is DORMANT, months before the summer they
    # would measure. That is D-141 answered by construction: nobody can say
    # these were chosen for their numbers, because their numbers do not exist
    # yet. The last complete southern summer was quiet at every one.
    "Santiago del Estero": dict(country="AR", station="Santiago del Estero",
                                cut=(8, 30), file="santiago_del_estero.json"),
    "Parana":      dict(country="AR", station="Parana Aero", cut=(8, 30),
                        file="parana.json"),
    "Laboulaye":   dict(country="AR", station="Laboulaye Aero", cut=(8, 30),
                        file="laboulaye.json"),
    "Mar del Plata": dict(country="AR", station="Mar del Plata Aero",
                          cut=(8, 30), file="mar_del_plata.json"),
    "Neuquen":     dict(country="AR", station="Neuquen Aero", cut=(8, 30),
                        file="neuquen.json"),
    "Salta":       dict(country="AR", station="Salta Aero", cut=(8, 30),
                        file="salta.json"),

    # ALGIERS, ROME AND TRELEW carry a SHORT baseline and are published with
    # the gap as a field. Kristjan's ruling 2026-08-30, reversing the
    # complete-or-nothing half of D-151 while keeping its substance: a city
    # may ship short, and must say what is missing and what it costs.
    #
    # Algiers is 29/30, missing 1999, and its count ranges 9 to 12 days.
    # 1999 is unclosable: GHCN holds 88 minima and 85 maxima, OGIMET's
    # bulletins do not reach it, and NCEI's ISD-Lite has the days only as
    # sampled observations that understate the daily maximum by 0.63 C on a
    # day carrying 23 observations, against a median of 9 in 1999. Filling it
    # that way would bias the BASELINE cool and push this year's rank up,
    # which is the one direction D-043 refuses.
    "Algiers":   dict(country="DZ", station="Algiers Houari Boumediene",
                      cut=(8, 10), file="algiers.json"),
    "Trelew":    dict(country="AR", station="Trelew Aero", cut=(8, 30),
                      file="trelew.json"),
"Paris":       dict(country="FR", station="ORLY", cut=(8, 3)),
    "Marseille":   dict(country="FR", station="MARIGNANE", cut=(8, 3)),
    "Nice":        dict(country="FR", station="NICE", cut=(8, 3)),
    "Montpellier": dict(country="FR", station="MONTPELLIER-AEROPORT", cut=(8, 3)),
    "Lyon":        dict(country="FR", station="LYON-ST EXUPERY", cut=(8, 3)),
    # Austria and Germany, added 2026-08-07. Both licences permit commercial
    # reuse: GeoSphere is CC0, DWD is GeoNutzV with attribution.
    #
    # THESE CITIES ARE WHY THE PERCENTILE NIGHT METRIC EXISTS. Hamburg
    # recorded ONE tropical night in 2026 and Berlin three. A 20 C count
    # cannot carry a ratio off that base, and no amount of extra data fixes
    # it, because the threshold is the problem rather than the record.
    # GeoSphere 105, which is typed COMBINED. Within our window it splices
    # two instruments AT THE SAME OBSERVATORY: Hohe Warte 5901 at 203 m to
    # 1992, Hohe Warte 5904 at 198 m after. That is categorically milder than
    # Murcia (two towns, 1.19 C) or Frankfurt (5.9 km, 0.57 C).
    #
    # The individual station 5904 was tried and REJECTED: this dataset carries
    # no Tmin for it before 1991, so it yields 34 usable years against 77. The
    # metadata's valid_from of 1934 is when the station existed, not when this
    # series holds its minima, which is a trap worth naming.
    #
    # Neighbour testing at the declared 1993 handover gives +0.44 C with the
    # same sign against 3 of 4 neighbours. SUGGESTIVE, not established: the
    # neighbours are German cities 350-750 km away and one of them (Frankfurt)
    # has a confirmed step of its own. Disclosed in the payload rather than
    # resolved, and it is product's call whether Vienna stays featured.
    "Vienna":    dict(country="AT", station="Wien Hohe Warte", cut=(8, 3),
                      file="gs_Vienna.json"),
    "Berlin":    dict(country="DE", station="Berlin-Tempelhof", cut=(8, 3),
                      file="dwd_Berlin.json"),
    "Hamburg":   dict(country="DE", station="Hamburg-Fuhlsbuettel", cut=(8, 3),
                      file="dwd_Hamburg.json"),
    "Frankfurt": dict(country="DE", station="Frankfurt/Main", cut=(8, 3),
                      file="dwd_Frankfurt.json"),
    "Munich":    dict(country="DE", station="Muenchen-Stadt", cut=(8, 3),
                      file="dwd_Munich.json"),
    "Cologne":   dict(country="DE", station="Koeln/Bonn", cut=(8, 3),
                      file="dwd_Cologne.json"),
    # REINSTATED 2026-08-07 after the hold, on evidence rather than argument.
    #
    # Amsterdam was held because KNMI prints "not suitable for trend analysis"
    # on its responses. Tested: that text is IDENTICAL on every KNMI station,
    # including De Bilt, the station KNMI itself uses for national climate
    # reporting. It is a service-wide disclaimer on raw station data, not an
    # assessment of Schiphol, and it is substantively what DWD says about the
    # series behind five German cities we publish.
    #
    # KNMI publishes current position only, exactly like AEMET, so Amsterdam
    # carries the no-published-history disclosure the ten Spanish cities
    # already carry. Not a clean bill: the same one they have.
    "Amsterdam": dict(country="NL", station="Schiphol", cut=(8, 3),
                      file="knmi_Amsterdam.json"),
    # PHASE 2, added 2026-08-08.
    #
    # Stockholm-Bromma, SMHI, CC-BY. A SINGLE CONTINUOUS station 1951 to now.
    # The more central Observatoriekullen cannot be used without merging two
    # instruments, since its automatic successor starts in 1996 and its
    # predecessor ends in 2024. An airport rather than a city centre, the same
    # trade-off as Barcelona against Madrid's park, and the station name is
    # emitted so the choice is visible.
    #
    # Expected to gate on nights: zero tropical nights in 2026. That is the
    # point rather than a problem. Every Phase 1 city sits in the hot half of
    # Europe, so "every city in our set is elevated" was partly a finding and
    # partly a consequence of which stations we held.
    "Stockholm": dict(country="SE", station="Stockholm-Bromma", cut=(8, 3),
                      file="smhi_Stockholm.json"),
    # Praha-Karlov, CHMI. Cut at 07-31 because CHMI has not yet published
    # August; every city already carries its own cut and no cross-city ranking
    # is offered. Temperature record starts 1971, so both the percentile and
    # sd baselines are complete but the 1961-1990 comparison is not, and the
    # day multiple withholds itself by rule.
    #
    # NOT evidence for the geography headline. Prague at 14.4E is WEST of
    # Vienna at 16.4E and does not extend our eastern reach.
    "Prague":    dict(country="CZ", station="Praha-Libuš", cut=(7, 31),
                      file="chmi_Prague.json"),
    # FMI Helsinki Kaisaniemi, pinned by fmisid 100971 rather than by the
    # place name the WFS also accepts. Verified to return the same
    # coordinates for 1971, 1991 and 2026, which a name lookup would have
    # hidden. Fourth city where that check was the whole difference.
    "Helsinki":  dict(country="FI", station="Helsinki Kaisaniemi", cut=(8, 3),
                      file="fmi_Helsinki.json"),
    # MeteoSwiss SMA, Zurich/Fluntern. The longest record in the set at 1864,
    # and the columns are parameter codes differing by one character:
    # tre200dn is the minimum, tre200dx the maximum. Picking the wrong one
    # yields a plausible series that is silently the wrong quantity.
    "Zurich":    dict(country="CH", station="Zurich/Fluntern", cut=(8, 3),
                      file="mch_Zurich.json"),
    # ADDED 2026-08-09, chosen from next week's forecast rather than for
    # coverage. All six sit in the core of the event, +10 to +13 C above
    # their recent-August normal, and all six are on fetchers already built
    # and verified. That is the whole reason to pick these six: the cheapest
    # cities happen to be the ones where the story is.
    "Bordeaux":  dict(country="FR", station="BORDEAUX-MERIGNAC", cut=(8, 3)),
    "Toulouse":  dict(country="FR", station="TOULOUSE-BLAGNAC", cut=(8, 3)),
    "Strasbourg": dict(country="FR", station="STRASBOURG-ENTZHEIM", cut=(8, 3)),
    "Hanover":   dict(country="DE", station="Hannover", cut=(8, 3),
                      file="dwd_Hanover.json"),
    "Stuttgart": dict(country="DE", station="Stuttgart-Schnarrenberg",
                      cut=(8, 3), file="dwd_Stuttgart.json"),
    "Geneva":    dict(country="CH", station="Geneve/Cointrin", cut=(8, 3),
                      file="mch_Geneva.json"),
    # Added 2026-08-09, on fetchers already built. NOT forecast-selected:
    # these are ordinary additions and must not join FORECAST_SELECTED, or
    # the leave-one-out robustness test would exclude cities that carry no
    # selection bias and weaken a claim for the wrong reason.
    "Leipzig":   dict(country="DE", station="Leipzig-Holzhausen", cut=(8, 3),
                      file="dwd_Leipzig.json"),
    "Dresden":   dict(country="DE", station="Dresden-Klotzsche", cut=(8, 3),
                      file="dwd_Dresden.json"),
    "Basel":     dict(country="CH", station="Basel/Binningen", cut=(8, 3),
                      file="mch_Basel.json"),
    "Lugano":    dict(country="CH", station="Lugano", cut=(8, 3),
                      file="mch_Lugano.json"),
}


def wraps(months, start):
    """Does this season cross the year boundary?"""
    return not (start <= season_end(months))


def to_season_year(cal_year, month, start, months):
    """Which SEASON does a (year, month) belong to?

    A CALENDAR YEAR IS NOT A SEASON WHEN THE SEASON WRAPS, and treating it as
    one added two different summers together for every southern city. Calendar
    2025 at Santiago del Estero held January 2025, the tail of the 2024-25
    summer, AND October to December 2025, the head of the 2025-26 one. The
    payload counted both as a single row, so its "69 ranked seasons" were 69
    spliced pairs and its last complete season read 19 days when the real
    figure was neither of the halves.

    The season is labelled by the year it STARTS, so October 2025 to January
    2026 is season 2025. Months at or after the window's opening month belong
    to that calendar year's season; months before it belong to the previous
    one.

    For a non-wrapping season this returns the calendar year unchanged, which
    is why no northern city moves by a single day.
    """
    if not wraps(months, start):
        return cal_year
    return cal_year if month >= start[0] else cal_year - 1


def season_end(months):
    """Last day of the final season month, as (month, day)."""
    m = months[-1]
    return (m, MONTH_LEN[m - 1])


def effective_cut(cut, start, months):
    """Clip the cut to the season, and say when the season has not begun.

    THE WRAPPING WINDOW NEEDED A SECOND BOUND AND I ONLY GAVE IT ONE. For a
    northern city the cut always sits inside or after the season, so
    `start <= md <= cut` is the whole story. For a southern city on 30 August
    the season is December to January and the window starts 1 October, so the
    cut sits BEFORE the window opens. `md >= start or md <= cut` then admits
    almost the entire year, midwinter included, and Santiago came out with a
    241-day window on a four-month season.

    So: if the cut falls outside the season window, the current season has
    NOT STARTED and there is nothing to count. Returning None says that
    rather than counting the previous summer under this year's label, which
    is what the bug did and what a page would have printed as fact.
    """
    end = season_end(months)
    if in_window(cut, start, end):
        return cut
    return None


def in_window(md, start, cut):
    """Is this (month, day) inside the counting window?

    A NORTHERN WINDOW IS AN INTERVAL; A SOUTHERN ONE IS NOT. May to August
    is a single ordered range and `start <= md <= cut` decides it. November
    to February WRAPS the year boundary, and that comparison is false for
    every day in it, so a southern city would silently count zero days and
    report a station that observed nothing.

    That is exactly the failure shape this channel spent the week on, so it
    is handled rather than assumed away: when the window wraps, a day
    qualifies if it is at or after the start OR at or before the cut.
    """
    if start <= cut:
        return start <= md <= cut
    return md >= start or md <= cut


def window_days(cut, start=None):
    start = start or WINDOW_START
    return sum(1 for m in range(1, 13) for d in range(1, MONTH_LEN[m - 1] + 1)
               if in_window((m, d), start, cut))


def load_aemet(city, fname=None):
    tn, tx = defaultdict(dict), defaultdict(dict)
    for d, mn, mx in json.loads((SRC / (fname or f"aemet_{city}.json")).read_text()):
        y, mo, dd = int(d[:4]), int(d[5:7]), int(d[8:])
        if mn is not None:
            tn[y][(mo, dd)] = mn
        if mx is not None:
            tx[y][(mo, dd)] = mx
    return tn, tx


# NUM_POSTE, pinned. Filtering by display name is the Murcia mistake in a
# second costume: FOUR posts publish under the name NICE, at 2 m, 6 m, 37 m
# and 79 m elevation and up to 8 km apart. Measured, they contribute no
# temperature at all, only rain and wind, so the series was clean by luck
# rather than by construction. Had one of them carried a Tmin, the loader
# would have taken whichever row it read last and nothing would have said so.
MF_POSTE = {
    "Paris": "91027002", "Marseille": "13054001", "Nice": "06088001",
    "Montpellier": "34154001", "Lyon": "69299001",
    "Bordeaux": "33281001", "Toulouse": "31069001",
    "Strasbourg": "67124001",
}


def load_mf(city, station):
    tn, tx = defaultdict(dict), defaultdict(dict)
    poste = MF_POSTE[city]
    for part in ("hist", "recent"):
        p = SRC / f"mf_{city}_{part}.csv.gz"
        with gzip.open(p, "rt", encoding="latin-1") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if r.get("NUM_POSTE") != poste:
                    continue
                d = r.get("AAAAMMJJ", "")
                if len(d) != 8:
                    continue
                y, mo, dd = int(d[:4]), int(d[4:6]), int(d[6:])
                a, b = r.get("TN", "").strip(), r.get("TX", "").strip()
                if a:
                    tn[y][(mo, dd)] = float(a)
                if b:
                    tx[y][(mo, dd)] = float(b)
    return tn, tx


def build(city, meta):
    # AEMET, GeoSphere and DWD all land as [date, tmin, tmax] JSON, so one
    # loader serves three sources. Meteo-France is the odd one, being gzipped
    # CSV with a station-name filter.
    if meta["country"] == "FR":
        tn, tx = load_mf(city, meta["station"])
    else:
        tn, tx = load_aemet(city, meta.get("file"))
    # THE CUT IS DERIVED, NOT TYPED. Ratified by Kristjan via product
    # 2026-08-09, and it is the same rule he gave for everything else here:
    # no heat logic hardcoded, every element adjustable from the data.
    #
    # Platform found the failure it fixes. The weekly refresh pulled ten
    # services through 8 August and not one published number moved, because
    # the cut was a static per-city constant sitting days behind the
    # observations. So the job fetched, rebuilt, committed, and changed
    # nothing a reader could see. Six days of observations were outside it,
    # including three of the hottest days Vienna has recorded.
    #
    # The cut is the LAST DAY THIS CITY ACTUALLY OBSERVED, per city, because
    # services publish on different lags and a shared cut would throw away
    # good days from the prompt ones. A city with a real observation on
    # 8 August counts to 8 August; one that stops on 3 August counts to the
    # 3rd and says so in counted_to.
    #
    # meta["cut"] survives as an explicit override for a city whose recent
    # days are known bad. It is a floor on nothing: when set, it wins.
    _cur = {(m, d) for (m, d), v in tx.get(CURRENT_YEAR, {}).items()
            if v is not None}
    _cur |= {(m, d) for (m, d), v in tn.get(CURRENT_YEAR, {}).items()
             if v is not None}
    cut = meta["cut"] if meta.get("cut_is_override") else (
        max(_cur) if _cur else meta["cut"])
    # THE SEASON, DERIVED FROM THIS STATION'S OWN RECORD. All 46 cities in
    # CITIES derive (7, 8), which is what the constants used to hardcode, so
    # this changes no existing number. A station with no season worth
    # calibrating against, amplitude under MIN_SEASON_AMPLITUDE_C, gets none
    # and is skipped, the same treatment as one with no complete baseline.
    season, amplitude = derive_season(tx)
    if season is None:
        print(f"  {city}: SKIPPED, no hot season worth calibrating "
              f"(amplitude {amplitude} C, floor {MIN_SEASON_AMPLITUDE_C}). "
              f"A threshold here would describe a distinction that does not "
              f"exist in the record.", file=sys.stderr)
        return None
    win_start, season_cover = season_window(season)
    # A season that has not begun is not a season with no days in it.
    eff = effective_cut(cut, win_start, season)
    season_started = eff is not None
    W = window_days(eff, win_start) if season_started else 0

    # THE COUNTERS MUST USE THE WINDOW, NOT A RAW `k <= cut`. On a (month,
    # day) tuple `k <= cut` means "before 29 August", which for a southern
    # season silently drops October, November and December: Santiago showed a
    # complete 123-day season with ZERO hot days because every one of them
    # fell after the cut in tuple order. in_window knows the season wraps and
    # `k <= cut` does not.
    def _counts(k, y):
        # EVERY YEAR IS COUNTED TO THE SAME POINT, which is what "to date"
        # means. My previous version counted historical seasons to the season
        # END and the current one to the CUT, which compared 2026-to-21-August
        # against 1976-to-31-August and moved 27 claims across the northern
        # set, withdrawing three records that had not changed.
        #
        # When the cut falls inside the window, it is the common point and
        # every year uses it. When it falls outside, the current season has
        # not begun: historical seasons are then whole, and the current one
        # has nothing to count, which _counts returns False for by way of
        # season_started.
        if season_started:
            return in_window(k, win_start, eff)
        if y == CURRENT_YEAR:
            return False
        return in_window(k, win_start, season_end(season))

    # Thresholds are each city's own in-season maxima percentiles. AEMET's
    # published rule, reproduced exactly for Madrid (36.4) and Seville (41.2).
    # RE-KEY THE OBSERVATIONS BY SEASON before anything counts them. For a
    # northern city this is the identity; for a southern one it moves January
    # out of its calendar year and into the summer it belongs to.
    def by_season(series):
        out = {}
        for cy, dd in series.items():
            for (m, d), v in dd.items():
                sy = to_season_year(cy, m, win_start, season)
                out.setdefault(sy, {})[(m, d)] = v
        return out
    tn_s, tx_s = by_season(tn), by_season(tx)

    # THE SHORTFALL TEST MUST SEE THE SAME SERIES THE PAGE DOES. It was
    # reading calendar years while the payload read season years, so Trelew's
    # disclosed range said 7 days at rank 19 while the page published 5 at
    # rank 34. Northern cities agreed because for them the two keyings are
    # identical; the wrapping season exposed it, as it has exposed everything
    # else today.
    pctl = pick_baseline(tx_s, tn_s, season_cover, season, _counts)
    if pctl is None:
        # SKIP THIS CITY, DO NOT ABORT THE BUILD. A city with no complete
        # baseline gets no thresholds, which is right. Killing the whole run
        # is not: adding Rome, which does not qualify, silently stopped all
        # 42 cities from rebuilding on 17 August. The payload kept its old
        # dates, and the refresh gate then compared it against itself and
        # printed PUBLISH. A false green is worse than the failure it hides,
        # because the failure was loud and the green was not.
        print(f"  {city}: SKIPPED, no complete WMO standard normal. "
              f"Tried {WMO_NORMALS}.", file=sys.stderr)
        return None
    ja = [v for y in range(pctl[0], pctl[1] + 1)
          for (m, _), v in tx.get(y, {}).items() if m in season]
    th = {str(p): round(float(np.percentile(ja, p)), 1) for p in (90, 95, 99)}

    # NIGHT thresholds, the same construction applied to minima. The 20 C
    # tropical-night count is a Mediterranean instrument: Amsterdam averages
    # under one such night a year, so every ratio divides by almost nothing
    # and the metric simply does not reach northern Europe. A per-city
    # percentile is locally calibrated by construction, which is the same
    # reason the day thresholds are percentiles rather than a flat 35 C.
    #
    # THIS DOES NOT REPLACE THE 20 C COUNT. Both are emitted. TR is an ETCCDI
    # standard and "tropical night" is a term a reader already knows; the
    # percentile is abstract but travels. Mediterranean cities carry both,
    # northern cities can only carry the second.
    jn = [v for y in range(pctl[0], pctl[1] + 1)
          for (m, _), v in tn.get(y, {}).items() if m in season]
    nth = {str(p): round(float(np.percentile(jn, p)), 1) for p in (90, 95, 99)}


    years = {}
    for y in sorted(set(tn_s) | set(tx_s)):
        # THE CUT CLIPS THE CURRENT YEAR ONLY. Historical years are whole
        # seasons and are measured against the whole window; only the year in
        # progress is cut short. My first fix applied season_started to every
        # year, so a southern city whose next season had not begun reported
        # ZERO usable years across its entire record, which is a worse answer
        # than the bug it replaced.
        # Coverage is measured against the same window the counts use.
        win = sum(1 for k in tn_s.get(y, {}) if _counts(k, y))
        if season_started:
            bar = W
        else:
            bar = 0 if y == CURRENT_YEAR else window_days(
                season_end(season), win_start)
        rec = {
            "window_days": win,
            "full_days": len(tn_s.get(y, {})),
            # A ZERO-DAY WINDOW IS NOT A COMPLETE ONE. With W = 0 the test
            # `win >= W * WINDOW_BAR` reads 0 >= 0 and returns True, so a
            # season that has not started came out "usable" with no days in
            # it. Caught on Santiago before it reached a page.
            "usable_to_cut": bar > 0 and win >= bar * WINDOW_BAR,
            "usable_full_year": len(tn_s.get(y, {})) >= FULL_YEAR_DAYS,
            "nights_to_cut": sum(1 for k, v in tn_s.get(y, {}).items()
                                 if _counts(k, y) and v >= TROPICAL_NIGHT_C),
            "nights_full_year": sum(1 for v in tn_s.get(y, {}).values()
                                    if v >= TROPICAL_NIGHT_C),
            "days_to_cut": {p: sum(1 for k, v in tx_s.get(y, {}).items()
                                   if _counts(k, y) and v >= t)
                            for p, t in th.items()},
            "warm_nights_to_cut": {p: sum(1 for k, v in tn_s.get(y, {}).items()
                                          if _counts(k, y) and v >= t)
                                   for p, t in nth.items()},
            "days_full_year": {p: sum(1 for v in tx_s.get(y, {}).values() if v >= t)
                               for p, t in th.items()},
        }
        if tn.get(y):
            rec["warmest_night_c"] = round(max(tn[y].values()), 1)
        if tx.get(y):
            rec["warmest_day_c"] = round(max(tx[y].values()), 1)
            # NO SENTINEL. -99 stood for "this year has no in-season
            # maxima", and sixteen years carried it: Frankfurt 1945, Leipzig
            # 1863, Belfast 1930, Zurich 1890 and the rest, war years and
            # record starts where minima exist and maxima do not. Any
            # consumer taking a min or a mean over the series would get a
            # temperature no thermometer produced. Design found four; there
            # were sixteen. Absent is now null and says so.
            _dv = [v for k, v in tx_s.get(y, {}).items() if _counts(k, y)]
            rec["warmest_day_to_cut_c"] = round(max(_dv), 1) if _dv else None
        if tn.get(y):
            _nv = [v for k, v in tn_s.get(y, {}).items() if _counts(k, y)]
            rec["warmest_night_to_cut_c"] = round(max(_nv), 1) if _nv else None
        years[str(y)] = rec

    def rate(lo, hi, p):
        ys = [y for y in range(lo, hi + 1)
              if years.get(str(y), {}).get("usable_full_year")]
        if not ys:
            return None, 0
        return (round(float(np.mean([years[str(y)]["days_full_year"][p]
                                     for y in ys])), 1), len(ys))

    counts, nbase = {}, {}
    for p in th:
        e, ne = rate(*COMPARE_EARLY, p)
        r, nr = rate(*COMPARE_RECENT, p)
        counts[p] = {"b6190": e, "r1125": r}
        nbase[p] = ne
    n_early = max(nbase.values()) if nbase else 0
    comparable = n_early >= MIN_BASELINE_YEARS

    # Design's improvement on product's ruling, adopted 2026-08-07. A
    # non-comparable multiple is not emitted-and-flagged, it is ABSENT: a
    # field that does not exist cannot be leaked by a renderer, and cannot be
    # reinstated by a future chat reading a flag as an oversight. Same shape
    # as `may_not_say`, the constraint carried by the data rather than
    # trusted to whoever draws it.
    #
    # The recent rate survives, because it stands on a complete 15 of 15
    # window. Only the baseline it would be divided by is missing, so only
    # the baseline goes.
    if not comparable:
        counts = {p: {"r1125": v["r1125"]} for p, v in counts.items()}

    raw = sorted(int(y) for y in years if int(y) < CURRENT_YEAR)
    last = max(tn.get(CURRENT_YEAR, {}) or {(1, 1)})
    return {
        "country": meta["country"],
        "station": meta["station"],
        # TWO DATES, NOT ONE, because they are not the same fact and a single
        # `as_of` conflates them. `counted_to` is the cut every year in the
        # series is measured to; `last_observation` is how far the source now
        # reaches. They diverge whenever the source refreshes after the cut
        # was fixed, and advancing the cut is a substantive change rather than
        # a refresh: Malaga's record is held by ONE night.
        # Reads the DERIVED cut, not meta["cut"]. These were the same value
        # until the cut became data-driven, and this line kept the old one,
        # so counted_to would have reported a date the counts no longer used.
        "counted_to": f"{CURRENT_YEAR}-{cut[0]:02d}-{cut[1]:02d}",
        "last_observation": f"{CURRENT_YEAR}-{last[0]:02d}-{last[1]:02d}",
        "source": {"ES": "AEMET OpenData",
                   "FR": "Meteo-France, via data.gouv.fr",
                   "AT": "GeoSphere Austria",
                   "DE": "DWD Climate Data Center",
                   "NL": "KNMI",
                   "SE": "SMHI",
                   "CZ": "CHMI",
                   "FI": "FMI",
                   "CH": "MeteoSwiss",
                   "AR": "NOAA GHCN-Daily and WMO bulletins",
                   "DZ": "NOAA GHCN-Daily and WMO bulletins",
                   # GHCN history bridged to the present with the station's
                   # own WMO bulletins, the Larnaca construction. Named as
                   # both, because a reader deserves to know the recent
                   # season and the history came by different routes.
                   "LT": "NOAA GHCN-Daily and WMO bulletins",
                   "HR": "NOAA GHCN-Daily and WMO bulletins",
                   "HU": "NOAA GHCN-Daily and WMO bulletins",
                   "IT": "NOAA GHCN-Daily and WMO bulletins",
                   # History MIDAS Open, 2026 season the same
                   # station's SYNOP bulletins. One thermometer,
                   # two transports; see build_london.py.
                   "UK": "Met Office",
                   # Keskkonnaagentuur's own archive, Harku only. NOT
                   # GHCN EN000026038, which is a blend of Harku and
                   # Ulemiste and was the route this replaced.
                   "EE": "Keskkonnaagentuur, Estonian Environment Agency",
                   "CY": "NOAA GHCN-Daily and WMO synoptic bulletins"}[meta["country"]],
        "cut_at": f"{cut[0]:02d}-{cut[1]:02d}",
        "station_class": STATION_CLASS.get(city, "unverified"),
        "station_class_note":
            "What kind of site this is, which is a DIFFERENT question from "
            "whether the station moved. An airport that grew around a "
            "thermometer that never budged is clean on station history and "
            "is exactly the thing readers challenge. 'unverified' means not "
            "yet established, NOT that the site is unremarkable.",
        "station_class_limit":
            ("This station is at an airport. Its surroundings have changed "
             "over the record in ways we have not measured, so part of its "
             "long-term warming may be local to the site rather than "
             "regional. The rank is true of this thermometer."
             if STATION_CLASS.get(city) in ("airport", "former airport")
             else None),
        # EMITTED, so no page or post can state a threshold without the
        # period that built it. Same rule as record_scope.
        # THE SEASON AS A FIELD. Derived above and recorded here, because a
        # season that lives only in a local is a season no page can disclose
        # and no guard can check. Every European city reads (7, 8); an
        # Argentine one reads (12, 1), and a reader deserves to see which.
        "season": {
            "months": list(season),
            "amplitude_c": amplitude,
            "window_start": list(win_start),
            "coverage_months": list(season_cover),
            "derived": True,
            "note": ("The two warmest CONSECUTIVE months of this station's "
                     "own 1991-2020 record, not an assumed summer. Counting "
                     "starts two months before the first of them. Every city "
                     "currently published derives July-August, which is what "
                     "the instrument previously hardcoded, so this changed "
                     "no number when it landed."),
        },
        "pctl_baseline": list(pctl[:2]),
        # D-051: the shortfall is a property of the datum. Empty for every
        # city with a complete normal, which is all but one.
        "pctl_baseline_missing_years": list(pctl[2]),
        "pctl_baseline_complete": not pctl[2],
        # THE GAP AS A FIELD, WITH ITS CONSEQUENCE. Kristjan's ruling
        # 2026-08-30: launch a city with a short baseline, and say plainly
        # what is missing. A footnote beside a point estimate would imply the
        # number is firm and the caveat cosmetic. Where the gap moves the
        # count, the RANGE is the honest figure and the point estimate is not
        # ours to give.
        "pctl_baseline_shortfall": (None if not pctl[2] else {
            "missing_years": list(pctl[2]),
            "years_present": 30 - len(pctl[2]),
            # ONLY EMIT THE RANGES THAT AGREE WITH THE PAGE. The rank range
            # is computed on a slightly different denominator from the
            # published rank, so where the gap is immaterial and nothing
            # renders it, a stale rank range would sit in the payload waiting
            # for a consumer to read it and contradict the page. Emitted only
            # when the count actually moves, which is when it is used.
            "count_range": (pctl[3] or {}).get("count_range"),
            "rank_range": ((pctl[3] or {}).get("rank_range")
                           if (pctl[3] or {}).get("count_moves") else None),
            "threshold_range_c": (pctl[3] or {}).get("threshold_range_c"),
            "count_is_a_range": bool((pctl[3] or {}).get("count_moves")),
            "must_say": (
                None if not (pctl[3] or {}).get("count_moves") else
                f"{', '.join(str(y) for y in pctl[2])} "
                f"{'is' if len(pctl[2]) == 1 else 'are'} missing from this "
                f"station's archive. Refilled from the coldest and the "
                f"warmest year in the window, this season's count is "
                f"{' to '.join(str(x) for x in (pctl[3] or {}).get('count_range', []))} "
                f"days. The range is the figure; a single number here would "
                f"be one we cannot defend."),
            "note": (
                "The baseline is short of the full WMO normal. Where "
                "count_is_a_range is false the gap provably cannot move the "
                "published count or rank, tested by refilling at both "
                "extremes. Where it is true, must_say belongs ON the page."),
        }),
        "pctl_baseline_shortfall_note": (
            "" if not pctl[2] else
            f"This baseline is {30 - len(pctl[2])} of 30 years; "
            f"{', '.join(str(y) for y in pctl[2])} missing."),
        "pctl_baseline_is_default": tuple(pctl[:2]) == PCTL_BASELINE,
        "record_from": raw[0], "record_to": raw[-1],
        "thresholds_c": th,
        "night_thresholds_c": nth,
        # DERIVED FROM THE PERIOD ACTUALLY USED. Editor caught these still
        # reading 1971-2000 after three cities moved to 1991-2020, which
        # would have put a source note claiming the old window four lines
        # under copy explaining that the old window could not be built.
        # The number is corrected and the field describing it is not: the
        # day's most repeated defect, landing on the correction that exists
        # to fix a description.
        "night_threshold_basis":
            f"90th/95th/99th percentile of this station's own July-August "
            f"daily MINIMA, {pctl[0]}-{pctl[1]}. The locally calibrated "
            f"night metric, emitted alongside the 20 C tropical-night count "
            f"rather than replacing it.",
        "tropical_night_metric_works":
            sum(1 for y in range(2011, 2026)
                if years.get(str(y), {}).get("nights_to_cut", 0) >= 5) >= 8,
        "tropical_night_metric_note":
            "False where the 20 C count is too rare to carry a ratio. Such a "
            "city must lead with the percentile night metric instead.",
        "threshold_basis":
            f"90th/95th/99th percentile of this station's own July-August "
            f"daily maxima, {pctl[0]}-{pctl[1]}."
            + ("" if tuple(pctl[:2]) == PCTL_BASELINE else
               f" This station's record starts in {min(int(y) for y in years)}"
               f" and cannot cover {PCTL_BASELINE[0]}-{PCTL_BASELINE[1]}, so "
               f"the complete {pctl[0]}-{pctl[1]} WMO normal is used instead."),
        "day_counts": counts,
        "day_counts_baseline_years": n_early,
        "day_counts_comparable": comparable,
        "day_counts_note": (
            "Comparable with the other cities: the 1961-1990 baseline is "
            "complete." if comparable else
            "NOT COMPARABLE and the multiple is withheld. This station's "
            "1961-1990 baseline holds only {0} of 30 years, drawn from the "
            "warmer end of the period, so the multiple would understate "
            "itself while looking like the figures beside it.".format(n_early)),
        "years": years,
    }


def main() -> int:
    out = {
        "_readme":
            "Per-city night and day series derived from PUBLISHED sources "
            "only. ECA&D is not read anywhere in this pipeline: it is "
            "non-commercial and cannot be published. Spain is AEMET, France "
            "is Meteo-France, one station per city, nights and days from the "
            "same rows of the same record.",
        "completeness": {
            "window": "1 May to each city's own cut",
            "bar": WINDOW_BAR,
            "why": "99.98% of tropical nights fall on or after 1 May, "
                   "measured across all cities and years. Days outside the "
                   "window cannot hide a tropical night, so counting them "
                   "toward completeness discards usable years.",
            "full_year_bar_days": FULL_YEAR_DAYS,
        },
        "tie_rule": {
            "ties_count_against_current_year": TIE_COUNTS_AGAINST,
            "note": "A TIE IS NOT A RECORD. rank = 1 + the number of prior "
                    "years whose count is greater than OR EQUAL TO the "
                    "current year. Three cities tie 2026, so recomputing a "
                    "rank with a strict greater-than would manufacture a "
                    "record. Stated as a field because a convention that "
                    "lives only in the code gets re-derived differently.",
        },
        "cities": {},
    }
    skipped = []
    for city, meta in CITIES.items():
        c = build(city, meta)
        if c is None:
            skipped.append(city)
            continue
        out["cities"][city] = c
        n = sum(1 for y in c["years"].values() if y["usable_to_cut"])
        print(f"  {city:12s} {c['source'][:14]:14s} {c['record_from']}-"
              f"{c['record_to']}  {n:3d} usable  P95 {c['thresholds_c']['95']:5.1f}C"
              + ("" if c["day_counts_comparable"]
                 else f"   multiple WITHHELD ({c['day_counts_baseline_years']}/30)"))
    if skipped:
        print(f"\n  SKIPPED, no complete baseline: {skipped}. These are in "
              f"CITIES and are NOT in the payload, so the set is "
              f"{len(out['cities'])} rather than {len(CITIES)}.")
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
