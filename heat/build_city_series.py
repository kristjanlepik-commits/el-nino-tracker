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
CURRENT_YEAR = 2026
TROPICAL_NIGHT_C = 20.0
PCTL_BASELINE = (1971, 2000)
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
    cut, W = meta["cut"], window_days(meta["cut"])

    # Thresholds are each city's own July-August maxima percentiles. AEMET's
    # published rule, reproduced exactly for Madrid (36.4) and Seville (41.2).
    ja = [v for y in range(PCTL_BASELINE[0], PCTL_BASELINE[1] + 1)
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
    jn = [v for y in range(PCTL_BASELINE[0], PCTL_BASELINE[1] + 1)
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
        "counted_to": f"{CURRENT_YEAR}-{meta['cut'][0]:02d}-{meta['cut'][1]:02d}",
        "last_observation": f"{CURRENT_YEAR}-{last[0]:02d}-{last[1]:02d}",
        "source": {"ES": "AEMET OpenData",
                   "FR": "Meteo-France, via data.gouv.fr",
                   "AT": "GeoSphere Austria",
                   "DE": "DWD Climate Data Center",
                   "NL": "KNMI",
                   "SE": "SMHI",
                   "CZ": "CHMI",
                   "FI": "FMI"}[meta["country"]],
        "cut_at": f"{cut[0]:02d}-{cut[1]:02d}",
        "record_from": raw[0], "record_to": raw[-1],
        "thresholds_c": th,
        "night_thresholds_c": nth,
        "night_threshold_basis":
            "90th/95th/99th percentile of this station's own July-August "
            "daily MINIMA, 1971-2000. The locally calibrated night metric, "
            "emitted alongside the 20 C tropical-night count rather than "
            "replacing it.",
        "tropical_night_metric_works":
            sum(1 for y in range(2011, 2026)
                if years.get(str(y), {}).get("nights_to_cut", 0) >= 5) >= 8,
        "tropical_night_metric_note":
            "False where the 20 C count is too rare to carry a ratio. Such a "
            "city must lead with the percentile night metric instead.",
        "threshold_basis":
            "90th/95th/99th percentile of this station's own July-August "
            "daily maxima, 1971-2000.",
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
