"""Fetch daily station data from SMHI, the Swedish met service.

Licence: SMHI open data, CC-BY 4.0. Commercial reuse permitted with
attribution.

TWO ENDPOINTS AND BOTH ARE NEEDED, the same shape as Meteo-France and DWD.
`corrected-archive` holds the quality-controlled record and stops months
back; `latest-months` carries the rest and reaches yesterday. Either alone
gives a truncated series, which is exactly the shape the span gate exists to
catch.

Parameters are numeric: 19 is daily minimum, 20 is daily maximum. They are
requested separately and joined on date, so a mismatch in coverage between
them is visible rather than silently filling one from the other.

Station 98230 is Stockholm-Observatoriekullen A. The inactive 98210 is the
same site's earlier instrument; it is NOT merged in here, because merging two
instruments under one heading is the Murcia error and Sweden would be the
fourth time.
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
BASE = "https://opendata-download-metobs.smhi.se/api/version/1.0"

# 97200 Stockholm-Bromma, a SINGLE CONTINUOUS station 1951 to now.
#
# Observatoriekullen is the more central site and was tried first. It cannot
# be used without merging two instruments: 98230 "A" (automatic) starts only
# in 1996, too short for the 1971-2000 percentile baseline, and the older
# 98210 ends in 2024 so it cannot carry the current summer. Joining them is
# the Murcia error, and Sweden would be the fourth time.
#
# Bromma is an airport rather than the city centre, the same trade-off as
# Barcelona against Madrid's central park. The station name is emitted so the
# choice is visible rather than buried.
CITIES = {"Stockholm": ("97200", "Stockholm-Bromma")}
PERIODS = ("corrected-archive", "latest-months")
PARAMS = {"tmin": 19, "tmax": 20}


def _series(station, param):
    out = {}
    for period in PERIODS:
        url = f"{BASE}/parameter/{param}/station/{station}/period/{period}/data.csv"
        raw = subprocess.run(["curl", "-sS", "--max-time", "180", url],
                             capture_output=True).stdout.decode("utf-8", "replace")
        # The CSV carries a metadata preamble; the data block starts at the
        # first line whose third field parses as a date. Detecting that rather
        # than skipping a fixed number of lines, because the preamble length
        # differs between the two endpoints.
        for row in csv.reader(io.StringIO(raw), delimiter=";"):
            if len(row) < 4:
                continue
            d = row[2].strip()
            if len(d) != 10 or d[4] != "-":
                continue
            try:
                out[d] = float(row[3])
            except ValueError:
                continue
    return out


def fetch(city):
    sid, _ = CITIES[city]
    tn = _series(sid, PARAMS["tmin"])
    tx = _series(sid, PARAMS["tmax"])
    days = sorted(set(tn) | set(tx))
    return [(d, tn.get(d), tx.get(d)) for d in days]


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city in (sys.argv[1:] or CITIES):
        rows = fetch(city)
        (SRC / f"smhi_{city}.json").write_text(json.dumps(
            [[d, a, b] for d, a, b in rows]))
        trop = sum(1 for d, a, _ in rows
                   if d.startswith("2026") and a is not None and a >= 20.0)
        n_tn = sum(1 for _, a, _ in rows if a is not None)
        n_tx = sum(1 for _, _, b in rows if b is not None)
        print(f"  {city:10s} {len(rows):6d} days  {rows[0][0]} to {rows[-1][0]}"
              f"  tmin {n_tn} tmax {n_tx}  2026 tropical nights: {trop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
