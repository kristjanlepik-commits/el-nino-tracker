"""Weekly cumulative burnt-area history per country, every year.

Feeds the per-country cumulative chart, the one that answers "how bad
has this year been" and keeps answering it after the fires stop. The
weekly view drops a country the moment its detections fall back to
normal; this does not.

EFFIS where it has coverage (2006 onward), GWIS elsewhere (2012 on).
One request per country-year. Resumable: each finished country is
written immediately and a rerun skips it.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(REPO, "fires", "data", "burnt_area.json")
OUTDIR = os.path.join(REPO, "fires", "data", "area_history")
BASE = "https://api2.effis.emergency.copernicus.eu/statistics/v2"
os.makedirs(OUTDIR, exist_ok=True)


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
    cur = json.load(open(CUR))["countries"]
    this_year = date.today().year
    for i, (iso, c) in enumerate(cur.items(), 1):
        path = os.path.join(OUTDIR, f"{iso}.json")
        if os.path.exists(path):
            continue
        scope = c["source"].lower()
        first = 2006 if scope == "effis" else 2012
        years = {}
        for y in range(first, this_year + 1):
            doc = get(f"{BASE}/{scope}/weekly?country={iso}&year={y}")
            if not doc:
                continue
            rows = {str(r["week"]): r["area_ha"]
                    for r in doc.get("banfcumulative", [])
                    if r.get("area_ha") is not None}
            if rows:
                years[str(y)] = rows
            time.sleep(0.3)
        if years:
            json.dump({"iso": iso, "name": c["name"], "source": c["source"],
                       "years": years}, open(path, "w"))
            final = {y: max(v.values()) for y, v in years.items()}
            peak = max(final, key=lambda y: final[y]) if final else "-"
            print(f"{i:>3}/{len(cur)} {iso} {c['source']:<5} {len(years)} yrs, "
                  f"worst {peak} at {final.get(peak,0):,} ha", flush=True)
    print("AREAHISTDONE")


if __name__ == "__main__":
    main()
