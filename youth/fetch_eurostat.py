#!/usr/bin/env python3
"""Pull the Eurostat half of the youth pages into youth/data/eurostat.json.

    fetch_eurostat.py           pull and store
    fetch_eurostat.py --check   check C4: re-pull and compare with the stored copy

Life satisfaction and the pressures block ("Starting out"). None of this enters
the map. Each value keeps Eurostat's flag, since a "u" is low reliability.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "data" / "eurostat.json"
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EU27 = ("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL "
        "PT RO SE SI SK").split()
GEOS = EU27 + ["UK", "EU27_2020"]

# key -> (dataset, filters, label, ages, unit)
SERIES = {
    "life_young": ("ilc_pw01", {"age": "Y16-29", "sex": "T", "isced11": "TOTAL", "statinfo": "AVG",
                                "unit": "RTG", "life_sat": "LIFE"},
                   "Life satisfaction, 0 to 10", "16-29", "rating"),
    "life_all": ("ilc_pw01", {"age": "Y_GE16", "sex": "T", "isced11": "TOTAL", "statinfo": "AVG",
                              "unit": "RTG", "life_sat": "LIFE"},
                 "Life satisfaction, 0 to 10", "16 and over", "rating"),
    "housing": ("ilc_lvho07a", {"age": "Y15-29", "sex": "T", "unit": "PC", "rskpovth": "TOTAL"},
                "Spending over 40% of household income on housing", "15-29", "%"),
    "poverty": ("ilc_peps01n", {"age": "Y16-29", "sex": "T", "unit": "PC"},
                "At risk of poverty or social exclusion", "16-29", "%"),
    "unemployment": ("lfsa_urgan", {"age": "Y15-29", "sex": "T", "unit": "PC", "citizen": "TOTAL"},
                     "Unemployed, share of those in the labour force", "15-29", "%"),
    "with_parents": ("ilc_lvps08", {"age": "Y18-34", "sex": "T", "unit": "PC"},
                     "Living with their parents", "18-34", "%"),
    "age_leaving": ("yth_demo_030", {"sex": "T"},
                    "Average age on leaving the parental home", "all leavers", "years"),
}


def pull(dataset, filters):
    query = urllib.parse.urlencode({"format": "JSON", "lang": "EN", **filters})
    data = json.load(urllib.request.urlopen(f"{API}{dataset}?{query}", timeout=120))
    dims, sizes = data["id"], data["size"]
    geo_at, time_at = dims.index("geo"), dims.index("time")
    mult = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        mult[i] = mult[i + 1] * sizes[i + 1]
    geos = {v: k for k, v in data["dimension"]["geo"]["category"]["index"].items()}
    times = {v: k for k, v in data["dimension"]["time"]["category"]["index"].items()}
    out = {}
    for key, value in data["value"].items():
        k = int(key)
        geo = geos[k // mult[geo_at] % sizes[geo_at]]
        time = times[k // mult[time_at] % sizes[time_at]]
        out.setdefault(geo, {})[time] = {"value": value, "flag": data.get("status", {}).get(key, "")}
    return out, data.get("updated")


def build():
    out = {"source": "Eurostat, reuse with attribution", "series": {}}
    for key, (dataset, filters, label, ages, unit) in SERIES.items():
        cells, updated = pull(dataset, filters)
        # The newest year all 27 share, so every country page compares like with like.
        years = sorted(set.intersection(*(set(cells[c]) for c in EU27)))
        year = years[-1]
        out["series"][key] = {
            "dataset": dataset, "label": label, "ages": ages, "unit": unit, "year": year,
            "updated": updated,
            "values": {g: cells[g][year] for g in GEOS if g in cells and year in cells[g]},
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    fresh = build()
    if not args.check:
        OUT.write_text(json.dumps(fresh, indent=1))
        print(f"wrote {OUT}")
        for key, s in fresh["series"].items():
            print(f"  {key}: {s['year']}, {len(s['values'])} values")
        return
    stored = json.loads(OUT.read_text())
    changed = [(k, g) for k, s in stored["series"].items() for g, v in s["values"].items()
               if fresh["series"][k]["values"].get(g, {}).get("value") != v["value"]
               or fresh["series"][k]["year"] != s["year"]]
    print(f"C4: {len(changed)} values differ from the stored copy")
    for row in changed[:20]:
        print(" ", row)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
