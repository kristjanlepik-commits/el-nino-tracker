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

WINDOW_START = (5, 1)
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
WMO_NORMALS = [(1971, 2000), (1991, 2020)]


def pick_baseline(tx, tn):
    """The first complete standard normal, in the fixed order above.

    Complete means 30 of 30 years carrying at least 100 May-August days with
    both extremes. A period that is merely long enough is not enough: a
    truncated window is what the bar exists to refuse.
    """
    per = {}
    for y, dd in tx.items():
        n = sum(1 for (m, _d), v in dd.items()
                if m in (5, 6, 7, 8) and v is not None)
        per[y] = n
    for lo, hi in WMO_NORMALS:
        if sum(1 for y in range(lo, hi + 1) if per.get(y, 0) >= 100) == hi - lo + 1:
            return (lo, hi)
    return None


COMPARE_EARLY = (1961, 1990)
COMPARE_RECENT = (2011, 2025)
MIN_BASELINE_YEARS = 27          # of 30; below this a multiple is not comparable

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
    "Prague":    dict(country="CZ", station="Praha-Karlov", cut=(7, 31),
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


def window_days(cut):
    return sum(1 for m in range(1, 13) for d in range(1, MONTH_LEN[m - 1] + 1)
               if WINDOW_START <= (m, d) <= cut)


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
    W = window_days(cut)

    # Thresholds are each city's own July-August maxima percentiles. AEMET's
    # published rule, reproduced exactly for Madrid (36.4) and Seville (41.2).
    pctl = pick_baseline(tx, tn)
    if pctl is None:
        raise SystemExit(
            f"{city}: no complete WMO standard normal in the record. "
            f"Tried {WMO_NORMALS}. A city with no complete baseline gets no "
            f"thresholds rather than a truncated one.")
    ja = [v for y in range(pctl[0], pctl[1] + 1)
          for (m, _), v in tx.get(y, {}).items() if m in (7, 8)]
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
          for (m, _), v in tn.get(y, {}).items() if m in (7, 8)]
    nth = {str(p): round(float(np.percentile(jn, p)), 1) for p in (90, 95, 99)}

    years = {}
    for y in sorted(set(tn) | set(tx)):
        win = sum(1 for k in tn.get(y, {}) if WINDOW_START <= k <= cut)
        rec = {
            "window_days": win,
            "full_days": len(tn.get(y, {})),
            "usable_to_cut": win >= W * WINDOW_BAR,
            "usable_full_year": len(tn.get(y, {})) >= FULL_YEAR_DAYS,
            "nights_to_cut": sum(1 for k, v in tn.get(y, {}).items()
                                 if k <= cut and v >= TROPICAL_NIGHT_C),
            "nights_full_year": sum(1 for v in tn.get(y, {}).values()
                                    if v >= TROPICAL_NIGHT_C),
            "days_to_cut": {p: sum(1 for k, v in tx.get(y, {}).items()
                                   if k <= cut and v >= t)
                            for p, t in th.items()},
            "warm_nights_to_cut": {p: sum(1 for k, v in tn.get(y, {}).items()
                                          if k <= cut and v >= t)
                                   for p, t in nth.items()},
            "days_full_year": {p: sum(1 for v in tx.get(y, {}).values() if v >= t)
                               for p, t in th.items()},
        }
        if tn.get(y):
            rec["warmest_night_c"] = round(max(tn[y].values()), 1)
        if tx.get(y):
            rec["warmest_day_c"] = round(max(tx[y].values()), 1)
            rec["warmest_day_to_cut_c"] = round(
                max([v for k, v in tx[y].items() if k <= cut], default=-99), 1)
        if tn.get(y):
            rec["warmest_night_to_cut_c"] = round(
                max([v for k, v in tn[y].items() if k <= cut], default=-99), 1)
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
        # EMITTED, so no page or post can state a threshold without the
        # period that built it. Same rule as record_scope.
        "pctl_baseline": list(pctl),
        "pctl_baseline_is_default": pctl == PCTL_BASELINE,
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
            + ("" if pctl == PCTL_BASELINE else
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
    for city, meta in CITIES.items():
        out["cities"][city] = build(city, meta)
        c = out["cities"][city]
        n = sum(1 for y in c["years"].values() if y["usable_to_cut"])
        print(f"  {city:12s} {c['source'][:14]:14s} {c['record_from']}-"
              f"{c['record_to']}  {n:3d} usable  P95 {c['thresholds_c']['95']:5.1f}C"
              + ("" if c["day_counts_comparable"]
                 else f"   multiple WITHHELD ({c['day_counts_baseline_years']}/30)"))
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
