"""
Fetch ECMWF SEAS5 ensemble Niño 3.4 forecasts via Copernicus CDS.

Dataset: 'seasonal-monthly-single-levels' (or similar; verify in CDS catalog)
Variable: sea_surface_temperature
Region:   5N-5S, 170W-120W
Cadence:  monthly, ~5th of each month.

Auth:     CDS API key in ~/.cdsapirc or $CDSAPI_KEY environment variable.
          Free for non-commercial use; register at cds.climate.copernicus.eu.

Expected payload:
  issued:   ISO date of model run
  member_count: int (typically 51)
  members_above: dict[threshold_oni] -> int (count of members exceeding)
                  for thresholds 1.0, 1.5, 2.0, 2.5 at the DJF mean
  median_djf_oni: float
  raw_djf_anomalies: list[float]   # all 51 member DJF anomalies, °C

Implementation TODO:
  1. import cdsapi; client = cdsapi.Client()
  2. retrieve seasonal forecast monthly means; cache locally; ~30s-2min
  3. open with xarray; area-average over Niño 3.4 box
  4. average Dec/Jan/Feb of target year per member
  5. count members above each threshold
  6. return FetchResult(source='ecmwf_seas5', ok=True, ...)

Notes:
  - The API expects coordinates in 0-360 longitude; convert -170 to 190 etc.
  - 1991-2020 climatology removal: subtract the SEAS5 model climatology
    for the same lead time, NOT observational climatology, to get a fair
    anomaly. CDS provides hindcasts; compute climo from those.
  - This is the slowest fetcher; expect ~2-5 min on a Monday morning run.
"""

from ._common import FetchResult, now_iso


def fetch() -> FetchResult:
    # TODO: implement cdsapi pull + xarray reduction
    return FetchResult(
        source="ecmwf_seas5",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; needs cdsapi key in ~/.cdsapirc; see docstring",
    )
