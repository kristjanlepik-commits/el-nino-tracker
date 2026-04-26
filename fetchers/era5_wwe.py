"""
Fetch ERA5 daily 850 hPa zonal wind and compute Cumulative Westerly Wind
Anomaly (CWWA), a continuous scalar index of westerly forcing since
March 1 of the develop year.

Dataset: reanalysis-era5-pressure-levels (raw hourly product, sampled
         at 12:00 UTC). The CDS-derived daily-statistics dataset rejects
         30-year requests on its cost cap; the raw dataset accepts them.
Variable: u_component_of_wind at 850 hPa.
Region:   5N-5S, 130E-150W (= 130E-210E in 0-360 longitude). The
          domain extends west to 130E to capture western-Pacific WWE
          source bursts and contracts east to 150W to drop the central
          Pacific where WWE is more downstream response than driver.

Methodology (per external review, methodology version 1.2):

We compute area-mean 850 hPa zonal-wind anomaly daily, vs the 1991-2020
same-calendar-day climatology. We then integrate only the POSITIVE
(westerly) anomalies forward in time from March 1 of the develop year:

    CWWA(t) = sum_{tau=Mar1}^{t} max(0, u'_850(tau))   (m/s * days)

This is physically representative of cumulative momentum transfer to
the ocean surface, the mechanism that excites downwelling Kelvin waves
and drives moderate-to-super event escalation. It preserves intensity
information that any discrete event-counting metric throws away.

For the brief we report:
- CWWA value as of the latest available ERA5 day (~5-day lag from today)
- The full daily series (so the analog plot can show 2026 vs reference years)
- Equivalent series for 1997, 2015, 2023, 2025 develop years, fetched once
  and cached on disk; never recomputed thereafter

Cold-cache run: ~17 minutes (climatology rebuild) + ~12 minutes (four
analog-year pulls) + ~3 minutes (current observation) = ~32 minutes.
Warm-cache run: ~3 minutes (current observation only).

Expected payload:
  issued: ISO date of the most recent ERA5 day in the observation pull
  cwwa_ms_days: float (latest CWWA value)
  cwwa_series: list of (date_iso, value) tuples, one per observation day
  cwwa_analogs: dict[year_int -> list of (date_iso, value)]
  domain: str (descriptive)
  observation_days: int
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, timedelta

import numpy as np
import xarray as xr

from ._common import CACHE_DIR, FetchResult, now_iso

DATASET = "reanalysis-era5-pressure-levels"
REGION = [5, 130, -5, 210]   # N, W, S, E in 0-360 longitude
CLIM_YEARS = list(range(1991, 2021))
CLIM_MONTHS = ["03", "04", "05", "06", "07", "08"]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
SAMPLE_TIME = "12:00"

ANALOG_YEARS = [1997, 2015, 2023, 2025]


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
    return str(CACHE_DIR / f"era5_cwwa_clim_{CLIM_YEARS[0]}-{CLIM_YEARS[-1]}_130E-150W_MarAug.nc")


def _analog_path(year: int) -> str:
    return str(CACHE_DIR / f"era5_cwwa_analog_{year}_130E-150W.json")


def _mmdd(times: xr.DataArray) -> np.ndarray:
    return (times.dt.month.values * 100 + times.dt.day.values).astype("int32")


def _build_or_load_climatology() -> xr.DataArray:
    """Mean 850 hPa zonal wind by mmdd (int 0301..0831), area-meaned over 130E-150W."""
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
        u_box = u_box.assign_coords(mmdd=(time_dim, _mmdd(u_box[time_dim])))
        chunk = u_box.groupby("mmdd").mean(dim=time_dim)
        chunk_means.append(chunk)
        try:
            os.remove(tmp)
        except OSError:
            pass
    clim = xr.concat(chunk_means, dim="mmdd").sortby("mmdd")
    clim.name = "u_clim"
    clim.to_netcdf(path)
    return xr.open_dataarray(path)


def _cwwa_series_for_year(year: int, end_month: int, clim: xr.DataArray) -> list[tuple[str, float]]:
    """Pull Mar-{end_month} of `year`, compute daily anomaly vs clim, integrate positives."""
    months = [f"{m:02d}" for m in range(3, end_month + 1)]
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    _retrieve([str(year)], months, ALL_DAYS, tmp)
    ds = xr.open_dataset(tmp)
    u_box = _area_mean_u(ds)
    time_dim = "valid_time" if "valid_time" in u_box.coords else "time"
    times = u_box[time_dim]
    obs_mmdd = _mmdd(times)
    clim_per_day = clim.sel(mmdd=obs_mmdd).values
    anom = u_box.values - clim_per_day
    cum = np.cumsum(np.maximum(0.0, anom))
    series = [(str(t.astype("datetime64[D]")), float(v))
              for t, v in zip(times.values, cum)]
    try:
        os.remove(tmp)
    except OSError:
        pass
    return series


def _build_or_load_analog(year: int, clim: xr.DataArray) -> list[tuple[str, float]]:
    """Cache the full Mar-Aug CWWA series for an analog year."""
    path = _analog_path(year)
    if os.path.exists(path):
        return [tuple(pt) for pt in json.loads(open(path).read())]
    series = _cwwa_series_for_year(year, 8, clim)
    with open(path, "w") as f:
        json.dump([list(pt) for pt in series], f)
    return series


def fetch() -> FetchResult:
    try:
        today = date.today()
        end = today - timedelta(days=5)
        if end.month < 3:
            return FetchResult(source="era5_wwe", ok=False, fetched_at=now_iso(),
                               error="too early in develop year for Mar-onwards CWWA")
        clim = _build_or_load_climatology()
        current_series = _cwwa_series_for_year(end.year, end.month, clim)
        analogs = {y: _build_or_load_analog(y, clim) for y in ANALOG_YEARS}

        latest_date, latest_value = current_series[-1]
        return FetchResult(
            source="era5_wwe",
            ok=True,
            issued=latest_date,
            fetched_at=now_iso(),
            payload={
                "cwwa_ms_days": round(latest_value, 2),
                "cwwa_series": current_series,
                "cwwa_analogs": analogs,
                "domain": "5N-5S, 130E-150W",
                "observation_days": len(current_series),
            },
        )
    except Exception as e:
        return FetchResult(source="era5_wwe", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
