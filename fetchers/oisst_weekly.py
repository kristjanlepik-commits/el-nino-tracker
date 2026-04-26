"""
Fetch CPC weekly Niño 3.4 SST anomaly (traditional, against 1991-2020 climo).

URL:    https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for
Cadence: weekly, Mondays.
Format: fixed-width ASCII; one row per week. Columns include Niño 3.4
        anomaly. The latest line is the most recent week.

Expected payload:
  issued: ISO date of latest week (the week-ending date in the file)
  weekly_traditional: float (most recent Niño 3.4 anomaly °C)

Implementation TODO:
  1. http_get the .for file
  2. parse last line; extract date and Niño 3.4 anomaly column
  3. return FetchResult(source='oisst_weekly', ok=True, ...)
"""

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"


def fetch() -> FetchResult:
    # TODO: implement fixed-width parse
    return FetchResult(
        source="oisst_weekly",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; see fetchers/oisst_weekly.py docstring",
    )
