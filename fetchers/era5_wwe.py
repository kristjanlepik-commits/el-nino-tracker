"""
Fetch ERA5 daily 850 hPa zonal wind and detect westerly wind events.

Dataset: 'reanalysis-era5-single-levels' on CDS.
Variable: 'u_component_of_wind' at 850 hPa.
Region:   5N-5S, 160E-120W (Pacific west-to-central).
Cadence:  ERA5 has ~5 day delay. Run monthly, not weekly. The Niño 3.4
          weekly is the leading indicator; WWE count is a slower-moving
          confirmation signal.

WWE definition (McPhaden 1999):
  - zonal wind anomaly > 5 m/s
  - persisting > 5 days
  - centered east of 160°E

Expected payload:
  issued: ISO date of latest ERA5 day available
  wwe_count_since_mar1: int

Implementation TODO:
  1. cdsapi retrieve daily u850 from Mar 1 to most recent
  2. compute climatology from ERA5 1991-2020 same calendar days
  3. compute anomaly; spatial mean over 5N-5S, 160E-120W
  4. apply McPhaden criteria; count distinct events
  5. return FetchResult(source='era5_wwe', ok=True, ...)

Notes:
  - This is by far the heaviest fetch; daily data is ~50MB/month.
  - Run only on the first Monday of each month, not every week.
  - The orchestrator should treat WWE as "monthly-cadence input" and
    not count it as stale on intermediate weeks.
"""

from ._common import FetchResult, now_iso


def fetch() -> FetchResult:
    # TODO: implement cdsapi pull + WWE detection
    return FetchResult(
        source="era5_wwe",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; needs cdsapi key; monthly cadence only",
    )
