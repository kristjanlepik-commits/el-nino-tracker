"""Fetch daily station data from DWD, the German met service.

Licence: GeoNutzV. DWD open data may be reused commercially with attribution,
which is why it qualifies where ECA&D does not.

Two archives per station and BOTH are needed. `historical/` ends several days
back and `recent/` covers roughly the last 18 months, so either alone gives a
truncated record. That is the same shape as the Meteo-France hist/recent split
and the same shape as the truncation the span gate was built to catch.

Station ids are zero-padded to five digits in the filename and unpadded in the
station list. Berlin-Tempelhof is 433 in the list and 00433 in the URL.

Column names are German and abbreviated: TNK is the daily minimum in Celsius,
TXK the daily maximum. Missing is -999, NOT blank, so a naive float() gives a
plausible and catastrophically wrong -999 C rather than an error.
"""
from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from safe_write import write_series

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
BASE = ("https://opendata.dwd.de/climate_environment/CDC/observations_germany"
        "/climate/daily/kl")

# Chosen for record length, not for being the most central site. Every one of
# these reaches 1954 or earlier, which is what the 1971-2000 percentile
# baseline and the 1991-2020 sd baseline require.
CITIES = {
    "Berlin":    ("00433", "Berlin-Tempelhof"),
    "Hamburg":   ("01975", "Hamburg-Fuhlsbuettel"),
    "Frankfurt": ("01420", "Frankfurt/Main"),
    "Munich":    ("03379", "Muenchen-Stadt"),
    "Cologne":   ("02667", "Koeln/Bonn"),
    # Added 2026-08-09, chosen from the forecast for next week's event rather
    # than for coverage. Hannover +11.8 C and Stuttgart +11.5 C above their
    # recent-August normal, among the largest anomalies in Europe.
    "Hanover":   ("02014", "Hannover"),
    # Schnarrenberg, the CITY station, not Echterdingen which is the airport.
    "Stuttgart": ("04928", "Stuttgart-Schnarrenberg"),
    # Added 2026-08-09. Leipzig-Holzhausen's record starts in 1759, which
    # would be the longest in the set by a century; whether the early years
    # survive the completeness bar is a separate question the build answers.
    "Leipzig":   ("02928", "Leipzig-Holzhausen"),
    "Dresden":   ("01048", "Dresden-Klotzsche"),
}

MISSING = -999.0


def _listing(kind):
    url = f"{BASE}/{kind}/"
    return subprocess.run(["curl", "-sS", "--max-time", "120", url],
                          capture_output=True).stdout.decode("utf-8", "replace")


def _url_for(sid, kind, listing):
    m = re.search(rf'href="(tageswerte_KL_{sid}_[^"]*\.zip)"', listing)
    return f"{BASE}/{kind}/{m.group(1)}" if m else None


def _rows(url):
    blob = subprocess.run(["curl", "-sS", "--max-time", "300", url],
                          capture_output=True).stdout
    out = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n.startswith("produkt_klima_tag"))
        text = z.read(name).decode("latin-1")
    for r in csv.DictReader(io.StringIO(text), delimiter=";"):
        r = {k.strip(): (v.strip() if isinstance(v, str) else v)
             for k, v in r.items()}
        d = r.get("MESS_DATUM", "")
        if len(d) != 8:
            continue
        def num(k):
            try:
                v = float(r.get(k, MISSING))
            except ValueError:
                return None
            return None if v <= MISSING + 1 else v
        out[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = (num("TNK"), num("TXK"))
    return out


def fetch(city):
    sid, _ = CITIES[city]
    rows = {}
    for kind in ("historical", "recent"):
        listing = _listing(kind)
        url = _url_for(sid, kind, listing)
        if not url:
            raise RuntimeError(f"no {kind} archive for {city} ({sid})")
        got = _rows(url)
        # recent overwrites historical on overlap: it is the later revision
        rows.update(got) if kind == "recent" else rows.update(
            {k: v for k, v in got.items() if k not in rows})
    return sorted((d, mn, mx) for d, (mn, mx) in rows.items())


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city in (sys.argv[1:] or CITIES):
        rows = fetch(city)
        write_series(SRC / f"dwd_{city}.json", [[d, mn, mx] for d, mn, mx in rows], label=city)
        n26 = sum(1 for d, mn, _ in rows
                  if d.startswith("2026") and mn is not None and mn >= 20.0)
        print(f"  {city:10s} {len(rows):6d} days  {rows[0][0]} to {rows[-1][0]}"
              f"  2026 tropical nights: {n26}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
