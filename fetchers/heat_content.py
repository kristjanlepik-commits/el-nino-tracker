"""
Fetch 0-300m equatorial Pacific heat content anomaly.

URL:    https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ocean/index/heat_content_index.txt
        (the older /products/GODAS/heat_content_index.txt URL is now 404;
        the canonical location is under analysis_monitoring/ocean/index/.)
Cadence: monthly.
Format: ASCII whitespace-delimited, 5 columns:
        YR  MON  130E-80W  160E-80W  180W-100W
        anomalies are vs CPC's 1981-2010 climatology, not the 1991-2020
        baseline used elsewhere in the brief; difference is small (a
        couple tenths °C). The brief uses this value qualitatively, so
        the climatology mismatch is noted in the docstring rather than
        corrected for.

We use the 180W-100W column, which is the equatorial-Pacific (~5N-5S)
0-300m subsurface heat content the rest of the brief refers to.

Expected payload:
  issued: ISO date (last day of the data month)
  anomaly_c: float (most recent monthly anomaly in degrees C, 180W-100W)
"""

import calendar
import re
from datetime import date

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ocean/index/heat_content_index.txt"

_DATA_RE = re.compile(
    r"^\s*(\d{4})\s+(\d{1,2})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=30)
        rows = []
        for line in r.text.splitlines():
            m = _DATA_RE.match(line)
            if m:
                rows.append((int(m.group(1)), int(m.group(2)),
                             float(m.group(3)), float(m.group(4)), float(m.group(5))))
        if not rows:
            return FetchResult(source="heat_content", ok=False, fetched_at=now_iso(),
                               error="no data rows matched YYYY MM v1 v2 v3 pattern")
        year, month, _v1, _v2, anomaly_c = rows[-1]
        if not -5.0 <= anomaly_c <= 5.0:
            return FetchResult(source="heat_content", ok=False, fetched_at=now_iso(),
                               error=f"anomaly out of sane range: {anomaly_c}")
        last_day = calendar.monthrange(year, month)[1]
        issued = date(year, month, last_day).isoformat()
        return FetchResult(
            source="heat_content",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={"anomaly_c": anomaly_c},
        )
    except Exception as e:
        return FetchResult(source="heat_content", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
