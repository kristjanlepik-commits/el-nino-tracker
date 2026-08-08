"""Fetch daily station data from CHMI, the Czech met service.

Licence: CHMI open data, opendata.chmi.cz, reusable with attribution.

TWO BRANCHES, the same shape as every other service here. `historical` holds
one large JSON per station and stops at the end of last year; `recent` holds
one file per station per month and reaches the current summer. Either alone
truncates.

Elements are Czech abbreviations. TMI is the daily minimum and TMA the daily
maximum. There is also TMInoc, a night-specific minimum, which is NOT used:
our tropical-night definition is the ETCCDI index TR over the calendar day,
and swapping in a differently-windowed minimum for one country would make
that city's count incomparable with the other twenty-two while looking
identical.

Station 11520 is Praha-Karlov, a central observatory with a record to 1921.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
HIST = "https://opendata.chmi.cz/meteorology/climate/historical/data/daily"
RECENT = "https://opendata.chmi.cz/meteorology/climate/recent/data/daily"

CITIES = {"Prague": ("11520", "Praha-Karlov")}
CURRENT_YEAR = 2026


def _rows(url):
    raw = subprocess.run(["curl", "-sS", "--max-time", "600", url],
                         capture_output=True).stdout
    if len(raw) < 500:
        return []
    return json.loads(raw)["data"]["data"]["values"]


def _collect(values, tn, tx):
    for v in values:
        el, dt, val = v[1], v[3], v[4]
        if el not in ("TMI", "TMA") or val in ("", None):
            continue
        d = dt[:10]
        (tn if el == "TMI" else tx)[d] = float(val)


def fetch(city):
    sid, _ = CITIES[city]
    tn, tx = {}, {}
    _collect(_rows(f"{HIST}/dly-0-20000-0-{sid}.json"), tn, tx)
    for m in range(1, 13):
        url = f"{RECENT}/{m:02d}/dly-0-20000-0-{sid}-{CURRENT_YEAR}{m:02d}.json"
        _collect(_rows(url), tn, tx)
    days = sorted(set(tn) | set(tx))
    return [(d, tn.get(d), tx.get(d)) for d in days]


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city in (sys.argv[1:] or CITIES):
        rows = fetch(city)
        (SRC / f"chmi_{city}.json").write_text(json.dumps(
            [[d, a, b] for d, a, b in rows]))
        trop = sum(1 for d, a, _ in rows
                   if d.startswith("2026") and a is not None and a >= 20.0)
        cur = [d for d, a, _ in rows if d.startswith(str(CURRENT_YEAR))]
        print(f"  {city:9s} {len(rows):6d} days  {rows[0][0]} to {rows[-1][0]}"
              f"  {CURRENT_YEAR}: {len(cur)} days  tropical nights: {trop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
