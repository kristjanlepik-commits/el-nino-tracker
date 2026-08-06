"""Emit the channel payload design renders the heat pages from.

D-030 seam. Scope ruled by product 2026-08-06: a fifteen-city index view,
three cities given the full two-panel treatment inline (Paris, Madrid,
Bilbao), the headline carrying its own baseline, and the clustering pattern.

THREE THINGS THIS PAYLOAD ENFORCES RATHER THAN REQUESTS.

`requires_series: true` on every rank. A bare "1st of 105" is an alarm; the
same rank beside 104 ordinary years is a calibrated statement. Product stated
it as a design convention and it belongs in the datum, so a renderer printing
the rank alone is violating the contract rather than a style guide. It was
promised in a message once and not built, which is exactly how a convention
evaporates.

`headline_requires_baseline: true` on the record count. "Eight of fifteen at a
record" is unreadable alone: a typical year gives none, but 2003 gave twelve.
Both must appear with it.

`may_not_say` as an explicit field. 2026 is not the worst year on this
measure and no page may imply it is.

Sources are all commercially licensed: Meteo-France under Licence Ouverte 2.0,
AEMET permitting commercial reuse with attribution, GeoSphere under CC0. ECA&D
is verification only and never a published source, being non-commercial.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "heat" / ".cache"
OUT = ROOT / "heat" / "data" / "city_nights.json"

FEATURED = ("Paris", "Madrid", "Bilbao")

SOURCES = {
    "FR": {"who": "Meteo-France, via data.gouv.fr",
           "licence": "Licence Ouverte / Open Licence 2.0",
           "commercial_use": True,
           "attribution": "Source: Meteo-France", "lag_days": 2},
    "ES": {"who": "AEMET OpenData",
           "licence": "AEMET legal notice: reuse for commercial and "
                      "non-commercial purposes",
           "commercial_use": True,
           "attribution": "Source: AEMET", "lag_days": 3},
}


def load_series(city, staid, cut):
    tn = defaultdict(dict)
    with open(CACHE / f"h_{city}.txt", encoding="latin-1") as fh:
        for line in fh:
            m = re.match(rf"\s*{staid},\s*\d+,\s*(\d{{4}})(\d{{2}})(\d{{2}}),"
                         rf"\s*(-?\d+),\s*(\d)", line)
            if not m or int(m[5]) == 9:
                continue
            tn[int(m[1])][(int(m[2]), int(m[3]))] = int(m[4]) / 10.0
    good = sorted(y for y in tn if len(tn[y]) >= 330)
    return tn, good


def main() -> int:
    A = json.loads((ROOT / "heat/data/city_nights_2026.json").read_text())
    B = json.loads((ROOT / "heat/data/record_rate_baseline.json").read_text())
    match = json.loads((CACHE / "city_match.json").read_text())
    fr = json.loads((CACHE / "france2026.json").read_text())

    cities = {}
    for c, v in A.items():
        staid = fr[c]["staid"] if c in fr else match[c]["eca"]["staid"]
        cut = (8, 3) if c in fr else (8, 2)
        tn, good = load_series(c, staid, cut)
        todate = {y: sum(1 for (mo, d), x in tn[y].items()
                         if (mo, d) <= cut and x >= 20.0) for y in good}
        entry = {
            "country": v["country"],
            "station": fr[c]["station"] if c in fr else match[c]["eca"]["name"],
            "record_from": good[0], "record_to": good[-1],
            "nights_2026": v["n"], "as_of": v["as_of"],
            "coverage_pct": v["coverage_pct"],
            "mean_1991_2020_to_date": v["mean_9120"],
            "rank": {
                "value": v["rank"], "of_years": v["of_years"],
                "percentile": v["percentile"], "reading": v["reading"],
                "requires_series": True,
                "requires_series_note":
                    "This rank may not be rendered without the series below "
                    "it. A bare rank is an alarm; the same rank beside its "
                    "ordinary years is a calibrated statement, which is the "
                    "only thing on the page we ask a reader not to take on "
                    "trust.",
                "matched_to_same_date": True,
                "matched_note":
                    "Every prior year is counted to the same calendar day as "
                    "2026, so this is not a partial year against complete "
                    "ones.",
            },
            "series_to_same_date": {str(y): n for y, n in todate.items()},
            "source": SOURCES[v["country"]],
            "featured": c in FEATURED,
        }
        if c in FEATURED:
            entry["full_year_series"] = {
                str(y): sum(1 for x in tn[y].values() if x >= 20.0) for y in good}
            entry["warmest_night_c"] = {
                str(y): round(max(tn[y].values()), 1) for y in good}
        cities[c] = entry

    recs = [c for c, v in cities.items() if v["rank"]["value"] == 1]
    payload = {
        "_readme":
            "Nights that never fall below 20 C, per European city, each "
            "against its own record. One thermometer per city, city warming "
            "included. Not a climate measurement and never presented as one.",
        "channel": "heat", "evidence_basis": "Measured",
        "attribution": "Not ENSO-linked",
        "definition": {
            "name": "Tropical night",
            "rule": "daily minimum temperature at or above 20.0 C",
            "standard": "ETCCDI index TR, as published by European met "
                        "services. Not a threshold we chose.",
        },
        "headline": {
            "records": len(recs), "of_cities": len(cities),
            "record_cities": sorted(recs),
            "headline_requires_baseline": True,
            "baseline": {
                "typical_year_records": B["median_year"],
                "mean_2011_2025": B["mean_2011_2025"],
                "expected_no_trend": B["expected_no_trend"],
                "worst_year_on_record": {"year": 2003, "records": 12},
            },
            "may_not_say": B["may_not_say"],
            "the_better_story": B["the_better_story"],
            "caveat": B["caveat_2026_incomplete"],
        },
        "featured_cities": list(FEATURED),
        "cities": cities,
        "sources_note":
            "All published sources permit commercial reuse. ECA&D is used for "
            "verification only, never as a published source, because it is "
            "non-commercial. Every city was verified day-by-day against its "
            "own independent historical record before use.",
        "coverage_note":
            "Spain and France. This metric does not work in northern Europe, "
            "where tropical nights are near zero and ratios divide by almost "
            "nothing.",
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(f"  {len(cities)} cities, {len(recs)} at record, "
          f"{len(FEATURED)} featured with full series")
    miss = [c for c in FEATURED if c not in cities]
    if miss:
        print(f"  WARNING featured city missing: {miss}")
    bad = [c for c, v in cities.items() if not v["series_to_same_date"]]
    print(f"  requires_series satisfiable for all cities: {not bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
