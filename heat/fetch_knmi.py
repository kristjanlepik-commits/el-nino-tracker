"""Fetch daily station data from KNMI, the Dutch met service.

Licence: KNMI publishes its observations as open data, reusable including
commercially with attribution. That is the bar every source here must clear
and the reason ECA&D is not in this pipeline.

Values are in TENTHS of a degree, integers. Reading them as degrees gives a
station apparently running at 150 C, which is obvious; reading TX as TN is
not, so both are named explicitly in the request rather than positionally.

240 is Schiphol, the Amsterdam station. De Bilt (260) has a far longer record
and is not Amsterdam: it is 35 km away in a different setting, and using it
under an Amsterdam heading would be the same substitution that put Murcia's
history on an air base.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"

CITIES = {"Amsterdam": ("240", "Schiphol")}


def fetch(station, start="19010101", end="20261231"):
    url = f"{URL}?stns={station}&vars=TN:TX&start={start}&end={end}"
    txt = subprocess.run(["curl", "-sS", "--max-time", "300", url],
                         capture_output=True).stdout.decode("utf-8", "replace")
    rows = []
    for line in txt.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        p = [x.strip() for x in line.split(",")]
        if len(p) < 4 or len(p[1]) != 8:
            continue
        d = f"{p[1][:4]}-{p[1][4:6]}-{p[1][6:]}"
        tn = float(p[2]) / 10.0 if p[2] else None
        tx = float(p[3]) / 10.0 if p[3] else None
        rows.append((d, tn, tx))
    return sorted(rows)


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city, (sid, name) in CITIES.items():
        rows = fetch(sid)
        (SRC / f"knmi_{city}.json").write_text(json.dumps(
            [[d, a, b] for d, a, b in rows]))
        trop = sum(1 for d, a, _ in rows
                   if d.startswith("2026") and a is not None and a >= 20.0)
        print(f"  {city:10s} {name:10s} {len(rows):6d} days  {rows[0][0]} to "
              f"{rows[-1][0]}  2026 tropical nights: {trop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
