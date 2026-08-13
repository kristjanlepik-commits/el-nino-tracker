"""Fetch daily station data from FMI, the Finnish met service.

Licence: FMI open data, CC-BY 4.0. Commercial reuse permitted with
attribution.

PINNED BY FMISID, NEVER BY PLACE NAME. The WFS accepts `place=Helsinki`, and
that is a name lookup: it resolves to whichever station FMI considers to
represent the city, which can change. Four times now a display name has
turned out not to be an identity, so the station id is the only thing this
asks for.

100971 is Helsinki Kaisaniemi, a central-city station. Verified to return the
same coordinates (60.17523, 24.94459) for 1971, 1991 and 2026, which is the
check that a name would have hidden.

The WFS caps a request's span, so years are fetched one at a time and merged.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from safe_write import write_series

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
WFS = ("https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0"
       "&request=getFeature&storedquery_id="
       "fmi::observations::weather::daily::simple")

CITIES = {"Helsinki": ("100971", "Helsinki Kaisaniemi")}
FIRST_YEAR = 1971          # enough for the 1971-2000 percentile baseline
CURRENT_YEAR = 2026


def _year(fmisid, year):
    url = (f"{WFS}&fmisid={fmisid}"
           f"&starttime={year}-01-01T00:00:00Z"
           f"&endtime={year}-12-31T00:00:00Z&parameters=tmin,tmax")
    x = subprocess.run(["curl", "-sS", "--max-time", "240", url],
                       capture_output=True).stdout.decode("utf-8", "replace")
    if "ExceptionReport" in x:
        return {}
    # Time and the parameter pair travel together in document order.
    times = re.findall(r"<BsWfs:Time>(.*?)</BsWfs:Time>", x)
    vals = re.findall(r"<BsWfs:ParameterName>(\w+)</BsWfs:ParameterName>\s*"
                      r"<BsWfs:ParameterValue>([-\d.NaN]+)", x)
    out = {}
    for t, (name, v) in zip(times, vals):
        if v == "NaN":
            continue
        out.setdefault(t[:10], {})[name] = float(v)
    return out


def fetch(city):
    fmisid, _ = CITIES[city]
    days = {}
    for y in range(FIRST_YEAR, CURRENT_YEAR + 1):
        got = _year(fmisid, y)
        days.update(got)
        print(f"    {y}: {len(got)} days", flush=True)
    return sorted((d, v.get("tmin"), v.get("tmax")) for d, v in days.items())


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    for city in (sys.argv[1:] or CITIES):
        rows = fetch(city)
        write_series(SRC / f"fmi_{city}.json", [[d, a, b] for d, a, b in rows], label=city)
        trop = sum(1 for d, a, _ in rows
                   if d.startswith("2026") and a is not None and a >= 20.0)
        print(f"  {city:10s} {len(rows):6d} days  {rows[0][0]} to {rows[-1][0]}"
              f"  2026 tropical nights: {trop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
