"""
Fetch CPC weekly Niño 3.4 anomaly in both traditional and relative form,
and compute the RONI-to-traditional-ONI offset for the most recent week.

URLs:
  https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for       (traditional)
  https://www.cpc.ncep.noaa.gov/data/indices/rel_wksst9120.txt   (relative)

Cadence: weekly, Mondays.

Both files are fixed-width ASCII with 4 header lines and one data row per
week. The traditional file has SST and anomaly columns for each of the
four Niño regions; the relative file has just anomalies. SST and anomaly
run together when the anomaly is negative (e.g., "26.5-0.2") in the
traditional file, so floats are extracted by regex rather than whitespace.

The RONI-to-traditional offset for any given week equals the tropical-mean
SST anomaly for that week (by the definition of RONI), which we compute
directly as `traditional_anom - relative_anom` from the two files. This
replaces the static +0.3 °C constant previously hardcoded in sources.py.
The offset shifts with the tropical-mean SST trend (~+0.15 °C/decade) and
small seasonal cycle, so the live value is more accurate than any fixed
estimate over the brief's 6-9 month forecast horizon.

Expected payload:
  issued: ISO date of the latest week
  weekly_traditional: float (Niño 3.4 anomaly, traditional ONI sign, °C)
  weekly_relative:    float (Niño 3.4 anomaly, RONI sign, °C)
  roni_to_oni_offset: float (traditional minus relative for this week, °C)
"""

import re
from datetime import datetime

from ._common import FetchResult, http_get, now_iso

URL_TRADITIONAL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
URL_RELATIVE = "https://www.cpc.ncep.noaa.gov/data/indices/rel_wksst9120.txt"

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


def _last_data_line(text: str) -> str:
    lines = [l for l in text.splitlines() if _DATE_RE.match(l)]
    if not lines:
        raise ValueError("no data lines matched DDMMMYYYY pattern")
    return lines[-1]


def fetch() -> FetchResult:
    try:
        r_trad = http_get(URL_TRADITIONAL)
        last_trad = _last_data_line(r_trad.text)
        issued = _parse_date(last_trad)
        trad_nums = _FLOAT_RE.findall(last_trad)
        if len(trad_nums) < 8:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"traditional file: expected 8 floats, got {len(trad_nums)} in {last_trad!r}")
        weekly_traditional = float(trad_nums[5])

        r_rel = http_get(URL_RELATIVE)
        last_rel = _last_data_line(r_rel.text)
        rel_issued = _parse_date(last_rel)
        if rel_issued != issued:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"week mismatch: traditional {issued} vs relative {rel_issued}")
        rel_nums = _FLOAT_RE.findall(last_rel)
        if len(rel_nums) < 4:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"relative file: expected 4 floats, got {len(rel_nums)} in {last_rel!r}")
        weekly_relative = float(rel_nums[2])

        if not -5.0 <= weekly_traditional <= 5.0:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"traditional anomaly out of sane range: {weekly_traditional}")
        if not -5.0 <= weekly_relative <= 5.0:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"relative anomaly out of sane range: {weekly_relative}")

        offset = round(weekly_traditional - weekly_relative, 2)
        if not -2.0 <= offset <= 2.0:
            return FetchResult(source="oisst_weekly", ok=False,
                               fetched_at=now_iso(),
                               error=f"RONI offset out of sane range: {offset}")

        return FetchResult(
            source="oisst_weekly",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={
                "weekly_traditional": weekly_traditional,
                "weekly_relative": weekly_relative,
                "roni_to_oni_offset": offset,
            },
        )
    except Exception as e:
        return FetchResult(source="oisst_weekly", ok=False,
                           fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
