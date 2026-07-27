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

The file carries the full monthly series back to 1979, so the same-month
values for the analog years come from this same fetch: same source, same
column, same 1981-2010 climatology as the current value, which makes the
analog comparison exactly like-for-like with no climatology mismatch.

Expected payload:
  issued: ISO date (last day of the data month)
  anomaly_c: float (most recent monthly anomaly in degrees C, 180W-100W)
  data_year, data_month: ints identifying the month `anomaly_c` covers
  analogs_same_month: dict[str(year) -> float] for ANALOG_YEARS, sampled
      at the SAME calendar month as the current value (not a fixed spring
      month), so "at this stage of development" comparisons are honest
  series: dict["YYYY-MM" -> float] full parsed history, for future use
"""

import calendar
import re
from datetime import date

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ocean/index/heat_content_index.txt"

ANALOG_YEARS = (1997, 2015, 2023)

# CPC writes values without a leading zero (".56", "-.21"), so the numeric
# group must allow an optional integer part. The earlier `-?\d+\.\d+`
# pattern silently skipped every |value| < 1.0: it matched only 192 of 572
# data lines, and would have made the fetcher return a MONTHS-STALE row
# any time the latest month came in below 1.0. Latent bug, fixed here.
_NUM = r"-?(?:\d+)?\.\d+"
_DATA_RE = re.compile(
    rf"^\s*(\d{{4}})\s+(\d{{1,2}})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s*$"
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

        # Same-CALENDAR-MONTH analog values, so the brief compares July to
        # July rather than July to a fixed April constant.
        series = {f"{y:04d}-{m:02d}": v for y, m, _a, _b, v in
                  ((r[0], r[1], r[2], r[3], r[4]) for r in rows)}
        analogs_same_month = {
            str(y): series[f"{y:04d}-{month:02d}"]
            for y in ANALOG_YEARS
            if f"{y:04d}-{month:02d}" in series
        }
        return FetchResult(
            source="heat_content",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={
                "anomaly_c": anomaly_c,
                "data_year": year,
                "data_month": month,
                "analogs_same_month": analogs_same_month,
                "series": series,
            },
        )
    except Exception as e:
        return FetchResult(source="heat_content", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
