"""
Fetch 0-300m equatorial Pacific (180W-100W, 5N-5S) heat content anomaly.

Source: NOAA CPC equatorial upper-ocean heat content monitoring.
Page:   https://www.cpc.ncep.noaa.gov/products/GODAS/
Data:   The numerical time series is published as part of the GODAS
        monthly update. The page has a plot; the underlying ASCII is
        typically at https://www.cpc.ncep.noaa.gov/products/GODAS/heat_content_index.txt
        (verify URL on first run).
Cadence: ~weekly to bi-weekly updates.

Expected payload:
  issued: ISO date of latest pentad/week
  anomaly_c: float (latest 0-300m anomaly °C)

Implementation TODO:
  1. fetch the ASCII time series
  2. take last row
  3. return FetchResult(source='heat_content', ok=True, ...)
"""

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/products/GODAS/heat_content_index.txt"


def fetch() -> FetchResult:
    # TODO: implement
    return FetchResult(
        source="heat_content",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; see fetchers/heat_content.py docstring",
    )
