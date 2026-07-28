"""Cumulative burnt area for world and regional aggregates.

The country charts answer "how bad is this year here". These answer it
for the planet and for the fire regions the tracker actually cares
about: the Amazon Regional Observatory and Brazil Legal Amazon are
Copernicus's own boundaries for the basin this project was built
around, so the Amazon gets a real cumulative series rather than a
Brazil-shaped proxy.

GWIS for global scope (2012 on), EFFIS for its European scope (2006
on). One request per region-year. Prior years cached, current year
always re-pulled, same rule as the country history.
"""
import json
import os
import time
import urllib.request
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "fires", "data", "area_regions.json")
BASE = "https://api2.effis.emergency.copernicus.eu/statistics/v2"
UTILS = "https://api2.effis.emergency.copernicus.eu/statistics/utils"


def get(url, tries=3):
    for a in range(1, tries + 1):
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception:
            if a == tries:
                return None
            time.sleep(4 * a)


def main():
    this_year = date.today().year
    doc = {"regions": {}}
    if os.path.exists(OUT):
        try:
            doc = json.load(open(OUT))
        except ValueError:
            doc = {"regions": {}}

    scopes = []
    for scope, first in (("gwis", 2012), ("effis", 2006)):
        aois = get(f"{UTILS}/aoi?scope={scope}") or []
        for a in aois:
            code = a.get("aoi_code") or a.get("code") or a.get("aoi")
            name = a.get("aoi_name") or a.get("name") or code
            if code:
                scopes.append((scope, code, name, first))
    print(f"{len(scopes)} region-scopes to fetch", flush=True)

    for scope, code, name, first in scopes:
        key = f"{scope}:{code}"
        years = doc["regions"].get(key, {}).get("years", {})
        todo = [y for y in range(first, this_year + 1)
                if str(y) not in years or y == this_year]
        for y in todo:
            d = get(f"{BASE}/{scope}/weeklyaoi?aoi={code}&year={y}")
            if not d:
                continue
            rows = {str(r["week"]): r["area_ha"]
                    for r in d.get("banfcumulative", [])
                    if r.get("area_ha") is not None}
            if rows:
                years[str(y)] = rows
            time.sleep(0.25)
        if years:
            cur = years.get(str(this_year), {})
            latest = max(cur.values()) if cur else 0
            finals = {y: max(v.values()) for y, v in years.items()
                      if y != str(this_year)}
            worst = max(finals, key=finals.get) if finals else None
            doc["regions"][key] = {"scope": scope, "code": code,
                                   "name": name, "years": years}
            json.dump(doc, open(OUT, "w"))
            avg = sum(finals.values()) / len(finals) if finals else 0
            print(f"  {key:<16} {len(years):>2} yrs  now {latest:>12,.0f} ha"
                  f"  worst {worst} {finals.get(worst,0):>13,.0f}", flush=True)
    print("REGIONSDONE")


if __name__ == "__main__":
    main()
