"""Fetch cumulative burnt area in hectares from Copernicus EFFIS/GWIS.

The second rung of the metrics ladder in fires/SPEC.md, and the metric
that answers "how bad has this year been" rather than "how bad is this
week". Detections and hectares disagree by design and sometimes by
direction: on 2026-07-28 Canada read 2.1x normal on weekly detections
and 0.8x on year-to-date hectares. Never convert one into the other.

Why this needs no baseline build, unlike the FIRMS side: each weekly
row ships `area_ha` next to `area_ha_avg`, `area_ha_min` and
`area_ha_max` for the same week across all prior years, computed
server-side. So the comparison is Copernicus's, not ours, which also
suits the aggregator posture.

Sources, both unauthenticated:
  EFFIS  Europe, North Africa, Middle East. History from 2006.
  GWIS   global. History from 2012.
EFFIS is preferred where it has coverage because its record is six
years longer; GWIS is the fallback and the only option outside Europe.

Guards, both from real defects:
  - The weekly series pads to 52 rows with nulls, so a stale feed
    looks like a healthy short array. Assert the reported mddate is
    recent, do not trust array length.
  - Cadence is weekly with roughly six days of lag, unlike the daily
    detections. The freshness stamp is per country and gets published.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(REPO, "fires", "data", "country_history.json")
OUT = os.path.join(REPO, "fires", "data", "burnt_area.json")
BASE = "https://api2.effis.emergency.copernicus.eu/statistics/v2"
MAX_LAG_DAYS = 14          # weekly cadence plus ~6 days lag, plus slack
YEAR = date.today().year


def get(url, tries=3):
    for a in range(1, tries + 1):
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception:
            if a == tries:
                raise
            time.sleep(5 * a)


def latest_cumulative(scope, iso):
    """Last populated cumulative row, or None if the source has no data."""
    try:
        doc = get(f"{BASE}/{scope}/weekly?country={iso}&year={YEAR}")
    except Exception:
        return None
    rows = [r for r in doc.get("banfcumulative", [])
            if r.get("area_ha") is not None]
    return rows[-1] if rows else None


def main():
    hist = json.load(open(HISTORY))["countries"]
    out, stale, missing = {}, [], []
    for i, (iso, c) in enumerate(hist.items(), 1):
        # EFFIS first for its longer record, GWIS as the global fallback.
        row, scope = latest_cumulative("effis", iso), "effis"
        if row is None:
            row, scope = latest_cumulative("gwis", iso), "gwis"
        if row is None:
            missing.append(iso)
            continue
        md = str(row["mddate"])
        asof = datetime.strptime(md, "%Y%m%d").date()
        lag = (date.today() - asof).days
        if lag > MAX_LAG_DAYS:
            stale.append(f"{iso} ({lag}d)")
        avg = row.get("area_ha_avg") or 0
        out[iso] = {
            "name": c["name"], "source": scope.upper(),
            "week": row["week"], "as_of": asof.isoformat(), "lag_days": lag,
            "area_ha": row["area_ha"],
            "avg_ha": round(avg, 1),
            "max_ha": row.get("area_ha_max"),
            "multiple": round(row["area_ha"] / avg, 2) if avg else None,
            "vs_max": (round(row["area_ha"] / row["area_ha_max"], 2)
                       if row.get("area_ha_max") else None),
            "fires": row.get("events"),
        }
        print(f"{i:>3}/{len(hist)} {iso} {scope:<5} wk{row['week']:>2} "
              f"{row['area_ha']:>11,} ha  x{out[iso]['multiple'] or 0:<5}",
              flush=True)
        time.sleep(0.3)

    doc = {
        "_readme": [
            "Cumulative burnt area, hectares, year to date, from",
            "Copernicus EFFIS (Europe, 2006+) and GWIS (global, 2012+).",
            "Baselines are computed by Copernicus at the same week of",
            "prior years, not by us. Weekly cadence, ~6 day lag, so this",
            "is deliberately staler than the daily detections and must",
            "carry its own as_of. Hectares and detections measure",
            "different things and are never converted into each other.",
        ],
        "fetched": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "year": YEAR, "countries": out,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print(f"\nwrote {len(out)} countries to {OUT}")
    if missing:
        print(f"no burnt-area data: {', '.join(missing)}")
    if stale:
        print(f"STALE beyond {MAX_LAG_DAYS}d: {', '.join(stale)}", file=sys.stderr)


if __name__ == "__main__":
    main()
