"""Fetch daily station data from GeoSphere Austria.

The source behind the chart that started this workstream: Wien Hohe Warte,
klima-v2-1d. Pipeline verified by reproducing that chart's own published
figures exactly (1 day/yr above 32 C in 1872-1980 rising to 14 in 2010-2025,
and 39.8 C as the hottest day of 2026).

Better than every other source tried:
  licence   CC0, public domain. No non-commercial restriction, unlike ECA&D.
  key       none.
  lag       1 day, against AEMET's 3 and ECA&D's six weeks.
  record    1855 to present at Wien Hohe Warte, 170 complete years.

Station ids are dataset-specific: 11035 is the TAWES id and is REFUSED by
klima-v2-1d, which wants 105. Query the dataset's own metadata rather than
reusing an id from elsewhere.
"""
import csv
import io
import subprocess

BASE = "https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-1d"
WIEN_HOHE_WARTE = 105


def fetch(station=WIEN_HOHE_WARTE, start="1850-01-01", end="2026-12-31",
          params=("tlmax", "tlmin")):
    q = "&".join(f"parameters={p}" for p in params)
    url = (f"{BASE}?{q}&start={start}T00:00&end={end}T00:00"
           f"&station_ids={station}&output_format=csv")
    out = subprocess.run(["curl", "-sS", "--max-time", "240", url],
                         capture_output=True).stdout.decode("utf-8", "replace")
    rows = []
    for r in csv.DictReader(io.StringIO(out)):
        d = r.get("time", "")[:10]
        if not d:
            continue
        rows.append((d,
                     float(r["tlmin"]) if r.get("tlmin") else None,
                     float(r["tlmax"]) if r.get("tlmax") else None))
    return rows


def stations(match="Hohe Warte"):
    """Dataset-specific station ids. Do not reuse ids from other datasets."""
    import json
    out = subprocess.run(["curl", "-sS", "--max-time", "60", f"{BASE}/metadata"],
                         capture_output=True).stdout
    return [s for s in json.loads(out).get("stations", [])
            if match.lower() in (s.get("name") or "").lower()]


if __name__ == "__main__":
    rows = fetch()
    have = [r for r in rows if r[1] is not None or r[2] is not None]
    print(f"{len(have)} days, {have[0][0]} to {have[-1][0]}")
