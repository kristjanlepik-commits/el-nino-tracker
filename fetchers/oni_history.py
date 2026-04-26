"""
Fetch CPC's full ONI seasonal time series.

URL:    https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
Format: whitespace-delimited ASCII, one row per 3-month season:
        SEAS  YR    TOTAL    ANOM
        DJF  1950   25.36    -1.45
        ...

Cadence: monthly, alongside the ENSO Diagnostic Discussion.

Used by analog.py to refresh the current-year ONI trajectory each
Monday so the chart picks up new CPC issuances (e.g., FMA 2026 lands
in mid-May 2026 and immediately appears on the analog plot without
hand-editing data/oni_historical.csv). Historical years (1997, 2015,
2023, 2025) remain frozen in the CSV; the live fetch only overrides
the current calendar year.

Expected payload:
  issued: ISO date (last day of the latest complete season's last month)
  by_year: dict[int year -> dict[season trigram -> oni anomaly float]]
  latest_year: int (the most recent year present in the file)
  latest_season: str (the most recent season trigram in the file)
"""

import calendar
from datetime import date

from ._common import FetchResult, http_get, now_iso

URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

_TRIGRAM_LAST_MONTH = {
    "JFM": (0, 3), "FMA": (0, 4), "MAM": (0, 5), "AMJ": (0, 6),
    "MJJ": (0, 7), "JJA": (0, 8), "JAS": (0, 9), "ASO": (0, 10),
    "SON": (0, 11), "OND": (0, 12), "NDJ": (1, 1), "DJF": (0, 2),
}


def _issued_for_season(year: int, season: str) -> str:
    year_offset, last_month = _TRIGRAM_LAST_MONTH[season]
    last_day = calendar.monthrange(year + year_offset, last_month)[1]
    return date(year + year_offset, last_month, last_day).isoformat()


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=20)
        by_year: dict = {}
        latest_year = None
        latest_season = None
        for line in r.text.splitlines():
            parts = line.split()
            if len(parts) != 4:
                continue
            season, year_s, _total, anom_s = parts
            if season not in _TRIGRAM_LAST_MONTH:
                continue
            try:
                year = int(year_s)
                anom = float(anom_s)
            except ValueError:
                continue
            by_year.setdefault(year, {})[season] = anom
            latest_year = year
            latest_season = season
        if latest_year is None:
            return FetchResult(source="oni_history", ok=False, fetched_at=now_iso(),
                               error="no data rows parsed from oni.ascii.txt")
        issued = _issued_for_season(latest_year, latest_season)
        return FetchResult(
            source="oni_history",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={
                "by_year": by_year,
                "latest_year": latest_year,
                "latest_season": latest_season,
            },
        )
    except Exception as e:
        return FetchResult(source="oni_history", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
