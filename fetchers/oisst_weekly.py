"""
Fetch CPC weekly Niño 3.4 SST anomaly (traditional, against 1991-2020 climo).

URL:    https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for
Cadence: weekly, Mondays.
Format: fixed-width ASCII; one row per week. First 4 lines are header.
        Data rows: " DDMMMYYYY     SST  ANOM    SST  ANOM    SST  ANOM    SST  ANOM"
        for the four Niño regions in order: 1+2, 3, 3.4, 4.
        SST and anomaly run together when anomaly is negative
        (e.g., "26.5-0.2"), so we extract floats by regex rather than
        assuming whitespace separation.

Expected payload:
  issued: ISO date of latest week (the week-ending date in the file)
  weekly_traditional: float (most recent Niño 3.4 anomaly in degrees C)
"""

import re
from datetime import datetime

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"

_MONTH = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
          "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

_DATE_RE = re.compile(r"^\s*(\d{2})([A-Z]{3})(\d{4})\b")
_FLOAT_RE = re.compile(r"-?\d+\.\d+")


def _parse_date(s: str) -> str:
    m = _DATE_RE.match(s)
    if not m:
        raise ValueError(f"no leading date in line: {s[:40]!r}")
    day, mon, year = int(m.group(1)), m.group(2), int(m.group(3))
    if mon not in _MONTH:
        raise ValueError(f"unknown month code {mon!r} in line: {s[:40]!r}")
    return datetime(year, _MONTH[mon], day).date().isoformat()


def fetch() -> FetchResult:
    try:
        r = http_get(URL)
        lines = r.text.splitlines()
        data_lines = [l for l in lines if _DATE_RE.match(l)]
        if not data_lines:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error="no data lines matched DDMMMYYYY pattern")
        last = data_lines[-1]
        issued = _parse_date(last)
        nums = _FLOAT_RE.findall(last)
        if len(nums) < 8:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"expected 8 floats, got {len(nums)} in {last!r}")
        weekly_traditional = float(nums[5])
        if not -5.0 <= weekly_traditional <= 5.0:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"Niño 3.4 anomaly out of sane range: {weekly_traditional}")
        return FetchResult(
            source="oisst_weekly",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={"weekly_traditional": weekly_traditional},
        )
    except Exception as e:
        return FetchResult(source="oisst_weekly", ok=False,
                           fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
