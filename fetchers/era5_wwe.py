"""
Fetch ERA5 daily 850 hPa zonal wind and detect westerly wind events.

Dataset: reanalysis-era5-pressure-levels (the raw hourly product). The
         CDS-derived daily-statistics dataset has a cost cap that
         rejects 30-year climatology pulls; the raw dataset's cap is
         looser. We work around the question of "what daily value to
         use" by sampling a single timestep per day (12:00 UTC), which
         is good enough for a WWE counting diagnostic and avoids
         downloading 24 hours per day across 30 years.

Variable: u_component_of_wind at 850 hPa.
Region:   5N-5S, 160E-120W (= 160E-240E in 0-360 longitude).
Cadence:  ERA5 has ~5 day lag. Re-pulled on every brief; the
          1991-2020 climatology is computed once and cached on disk.

Simplified McPhaden (1999) WWE criterion as used here: area-mean 850
hPa zonal-wind anomaly > 5 m/s sustained for more than 5 consecutive
days.

Climatology pull is chunked one month at a time (30 years x 1 month
fits comfortably in the CDS cost limit; 30 years x 2 months does
not). Six chunks for the Mar-Aug window.

Cold-cache run: ~18 minutes for the 6 climatology chunks plus the
observation pull. Warm-cache run: ~1-3 minutes (observation only).

Expected payload:
  issued: ISO date of the most recent ERA5 day in the observation pull
  wwe_count_since_mar1: int
  observation_days: int
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

import numpy as np
import xarray as xr

from ._common import CACHE_DIR, FetchResult, now_iso

DATASET = "reanalysis-era5-pressure-levels"
REGION = [5, 160, -5, 240]
CLIM_YEARS = list(range(1991, 2021))
CLIM_MONTHS = ["03", "04", "05", "06", "07", "08"]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
SAMPLE_TIME = "12:00"
WWE_THRESHOLD_MS = 5.0
WWE_MIN_DURATION_DAYS = 5


def _retrieve(years: list[str], months: list[str], days: list[str], path: str) -> None:
    import cdsapi
    cdsapi.Client(quiet=True, progress=False).retrieve(
        DATASET,
        {
            "product_type": ["reanalysis"],
            "variable": ["u_component_of_wind"],
            "year": years,
            "month": months,
            "day": days,
            "time": [SAMPLE_TIME],
            "pressure_level": ["850"],
            "data_format": "netcdf",
            "area": REGION,
        },
        path,
    )


def _area_mean_u(ds: xr.Dataset) -> xr.DataArray:
    u = ds["u"]
    if "pressure_level" in u.dims:
        u = u.squeeze("pressure_level", drop=True)
    return u.mean(dim=["latitude", "longitude"])


def _clim_path() -> str:
    return str(CACHE_DIR / f"era5_wwe_clim_{CLIM_YEARS[0]}-{CLIM_YEARS[-1]}_MarAug.nc")


def _build_or_load_climatology() -> xr.DataArray:
    """Return mean 850 hPa zonal wind by mmdd (int 0301..0831), area-meaned."""
    path = _clim_path()
    if os.path.exists(path):
        return xr.open_dataarray(path)

    chunk_means = []
    for month in CLIM_MONTHS:
        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
        _retrieve([str(y) for y in CLIM_YEARS], [month], ALL_DAYS, tmp)
        ds = xr.open_dataset(tmp)
        u_box = _area_mean_u(ds)
        time_dim = "valid_time" if "valid_time" in u_box.coords else "time"
        times = u_box[time_dim]
        mmdd = (times.dt.month.values * 100 + times.dt.day.values).astype("int32")
        u_box = u_box.assign_coords(mmdd=(time_dim, mmdd))
        chunk = u_box.groupby("mmdd").mean(dim=time_dim)
        chunk_means.append(chunk)
        try:
            os.remove(tmp)
        except OSError:
            pass
    clim = xr.concat(chunk_means, dim="mmdd")
    clim = clim.sortby("mmdd")
    clim.name = "u_clim"
    clim.to_netcdf(path)
    return xr.open_dataarray(path)


def _count_wwe(daily_anom: np.ndarray) -> int:
    above = daily_anom > WWE_THRESHOLD_MS
    n = 0
    run_len = 0
    for v in above:
        if v:
            run_len += 1
        else:
            if run_len > WWE_MIN_DURATION_DAYS:
                n += 1
            run_len = 0
    if run_len > WWE_MIN_DURATION_DAYS:
        n += 1
    return n


def fetch() -> FetchResult:
    try:
        today = date.today()
        end = today - timedelta(days=5)
        if end.month < 3:
            return FetchResult(source="era5_wwe", ok=False, fetched_at=now_iso(),
                               error="too early in develop year for Mar-onwards WWE count")
        year = end.year
        months = [f"{m:02d}" for m in range(3, end.month + 1)]
        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
        _retrieve([str(year)], months, ALL_DAYS, tmp)
        ds = xr.open_dataset(tmp)
        u_box = _area_mean_u(ds)
        time_dim = "valid_time" if "valid_time" in u_box.coords else "time"
        times = u_box[time_dim]

        clim = _build_or_load_climatology()
        obs_mmdd = (times.dt.month.values * 100 + times.dt.day.values).astype("int32")
        clim_per_day = clim.sel(mmdd=obs_mmdd).values
        anom = u_box.values - clim_per_day
        wwe_count = _count_wwe(anom)

        last_day = times.values[-1].astype("datetime64[D]").astype(str)
        try:
            os.remove(tmp)
        except OSError:
            pass

        return FetchResult(
            source="era5_wwe",
            ok=True,
            issued=last_day,
            fetched_at=now_iso(),
            payload={
                "wwe_count_since_mar1": int(wwe_count),
                "observation_days": int(times.size),
            },
        )
    except Exception as e:
        return FetchResult(source="era5_wwe", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
