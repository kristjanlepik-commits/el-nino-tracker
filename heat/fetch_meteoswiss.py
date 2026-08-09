"""Fetch daily station data from MeteoSwiss open data.

Licence: Swiss federal open data via data.geo.admin.ch, reuse permitted
including commercial, with attribution.

TWO FILES, the same shape as DWD, Meteo-France, SMHI and CHMI. `historical`
ends at the last full year and `recent` carries the current one. Either alone
truncates, which is the shape the span gate exists to catch.

Column names are MeteoSwiss parameter codes rather than words:

    tre200d0   daily mean air temperature 2 m
    tre200dx   daily MAXIMUM
    tre200dn   daily MINIMUM

They differ by one character, and picking the wrong one gives a plausible
series that is silently the wrong quantity. Named as constants here so the
mistake has to be made once rather than at every use.

SMA is Zurich/Fluntern, the record running from 1864.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
BASE = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn"

TMIN, TMAX = "tre200dn", "tre200dx"
CITIES = {"Zurich": ("sma", "Zurich/Fluntern"),
          "Geneva": ("gve", "Geneve/Cointrin")}


def _read(url, out):
    raw = subprocess.run(["curl", "-sS", "--max-time", "300", url],
                         capture_output=True).stdout.decode("utf-8", "replace")
    if raw.lstrip().startswith("<"):          # an XML error, not a CSV
        return
    for r in csv.DictReader(io.StringIO(raw), delimiter=";"):
        ts = (r.get("reference_timestamp") or "").strip()
        if len(ts) < 10:
            continue
        d = f"{ts[6:10]}-{ts[3:5]}-{ts[0:2]}"      # DD.MM.YYYY -> ISO
        def num(k):
            v = (r.get(k) or "").strip()
            try:
                return float(v)
            except ValueError:
                return None
        out[d] = (num(TMIN), num(TMAX))


def fetch(city):
    slug, _ = CITIES[city]
    days = {}
    for part in ("historical", "recent"):
        _read(f"{BASE}/{slug}/ogd-smn_{slug}_d_{part}.csv", days)
    return sorted((d, v[0], v[1]) for d, v in days.items())


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city in (sys.argv[1:] or CITIES):
        rows = fetch(city)
        (SRC / f"mch_{city}.json").write_text(json.dumps(
            [[d, a, b] for d, a, b in rows]))
        trop = sum(1 for d, a, _ in rows
                   if d.startswith("2026") and a is not None and a >= 20.0)
        print(f"  {city:9s} {len(rows):6d} days  {rows[0][0]} to {rows[-1][0]}"
              f"  2026 tropical nights: {trop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
