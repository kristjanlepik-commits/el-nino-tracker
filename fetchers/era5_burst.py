"""
Spatial-peak westerly wind burst (WWB) detection from ERA5.

Runs alongside the CWWA fetcher (era5_wwe.py); the two are complementary
indicators of the same physical phenomenon. CWWA is the cumulative-area-mean
scalar (smooth, comparable across years); this fetcher is the discrete-event
counter (captures transient localized bursts that CWWA misses).

Motivated by two independent expert reviews:
- Gemini (early): recommended McPhaden 1999 full method with dual threshold
  and spatial-peak detection, instead of the simplified area-mean event count.
- Daniel Swain (later): pointed out that transient bursts often occur just
  outside the 5N-5S band and are systematically understated by cumulative
  metrics. The right metric is "did a sufficiently intense burst occur in
  the basin," not "what's the area-averaged westerly anomaly."

Methodology (v1.6):

For each day, slide a 5deg lat x 10deg lon window over the search domain
10N-10S, 130E-150W. Compute the area-mean of u'_850 anomaly within each
window position. The maximum across all window positions for that day is
the day's "spatial peak anomaly."

Event detection on the resulting time series:
- Base threshold: spatial peak > 5 m/s sustained > 5 consecutive days
- Peak threshold (dual): at least one day within the event > 7 m/s

These are McPhaden 1999 inspired (5 m/s base) plus Gemini's recommendation
to require an intensity peak (7 m/s) to filter persistent-but-weak westerly
periods from genuine bursts.

Climatology and observation pulls reuse the same dataset
(reanalysis-era5-pressure-levels at 12 UTC) as era5_wwe, but in a wider
latitude band (10N-10S instead of 5N-5S), and the full field is cached
rather than just the area-mean (necessary for the sliding window).

Cold-cache: ~30 min (climatology rebuild + 4 analog years).
Warm-cache: ~3 min (current observation only).

Expected payload:
  issued: ISO date of latest ERA5 day
  events_since_mar1: int (count for current 2026)
  events_detail: list of dicts with start, end, peak, location
  analogs: dict[int year -> list of event dicts]
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
from scipy.ndimage import uniform_filter

from ._common import CACHE_DIR, FetchResult, now_iso

DATASET = "reanalysis-era5-pressure-levels"
REGION = [10, 130, -10, 210]   # N, W, S, E in 0-360 longitude; wider than CWWA's 5N-5S
CLIM_YEARS = list(range(1991, 2021))
CLIM_MONTHS = ["03", "04", "05", "06", "07", "08"]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
SAMPLE_TIME = "12:00"

ANALOG_YEARS = [1997, 2015, 2023, 2025]

# Burst detection parameters (McPhaden 1999 + Gemini dual-threshold spec)
WINDOW_LAT_DEG = 5.0
WINDOW_LON_DEG = 10.0
THRESHOLD_BASE_MS = 5.0
THRESHOLD_PEAK_MS = 7.0
MIN_DURATION_DAYS = 5


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


def _extract_u_field(ds: xr.Dataset) -> xr.DataArray:
    u = ds["u"]
    if "pressure_level" in u.dims:
        u = u.squeeze("pressure_level", drop=True)
    return u


def _mmdd(times: xr.DataArray) -> np.ndarray:
    return (times.dt.month.values * 100 + times.dt.day.values).astype("int32")


def _clim_path() -> str:
    return str(CACHE_DIR / f"era5_burst_clim_{CLIM_YEARS[0]}-{CLIM_YEARS[-1]}_130E-150W_10NS_MarAug.nc")


def _analog_path(year: int) -> str:
    return str(CACHE_DIR / f"era5_burst_events_{year}_130E-150W_10NS.json")


def _build_or_load_climatology() -> xr.DataArray:
    """Full-field climatology: u_850 mean by mmdd, lat, lon at 10N-10S 130E-150W."""
    path = _clim_path()
    if os.path.exists(path):
        return xr.open_dataarray(path)
    chunk_means = []
    for month in CLIM_MONTHS:
        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
        _retrieve([str(y) for y in CLIM_YEARS], [month], ALL_DAYS, tmp)
        ds = xr.open_dataset(tmp)
        u = _extract_u_field(ds)
        time_dim = "valid_time" if "valid_time" in u.coords else "time"
        u = u.assign_coords(mmdd=(time_dim, _mmdd(u[time_dim])))
        chunk = u.groupby("mmdd").mean(dim=time_dim)
        chunk_means.append(chunk)
        try:
            os.remove(tmp)
        except OSError:
            pass
    clim = xr.concat(chunk_means, dim="mmdd").sortby("mmdd")
    clim.name = "u_clim_field"
    clim.to_netcdf(path)
    return xr.open_dataarray(path)


def _grid_resolution(da: xr.DataArray) -> tuple[float, float]:
    """Return (lat_step, lon_step) in degrees."""
    lat_step = float(abs(da["latitude"].values[1] - da["latitude"].values[0]))
    lon_step = float(abs(da["longitude"].values[1] - da["longitude"].values[0]))
    return lat_step, lon_step


def _spatial_peak_per_day(anom_field: np.ndarray, lat_step: float, lon_step: float) -> np.ndarray:
    """Return time series of per-day spatial peak (max sub-region area-mean).

    anom_field shape: (time, lat, lon). For each timestep, slide a
    WINDOW_LAT_DEG x WINDOW_LON_DEG box over the lat-lon plane, compute
    the area-mean within each window, and take the maximum.

    Implementation: scipy.ndimage.uniform_filter computes the centered
    sliding-window mean efficiently. We then mask out the edge pixels
    where the window would extend beyond the data domain.
    """
    n_time, n_lat, n_lon = anom_field.shape
    lat_w = max(1, int(round(WINDOW_LAT_DEG / lat_step)))
    lon_w = max(1, int(round(WINDOW_LON_DEG / lon_step)))
    lat_pad = lat_w // 2
    lon_pad = lon_w // 2

    out = np.empty(n_time, dtype=np.float64)
    for t in range(n_time):
        smoothed = uniform_filter(anom_field[t], size=(lat_w, lon_w),
                                  mode="constant", cval=0.0)
        if lat_pad > 0 and lon_pad > 0:
            valid = smoothed[lat_pad:-lat_pad, lon_pad:-lon_pad]
        elif lat_pad > 0:
            valid = smoothed[lat_pad:-lat_pad, :]
        elif lon_pad > 0:
            valid = smoothed[:, lon_pad:-lon_pad]
        else:
            valid = smoothed
        out[t] = float(np.nanmax(valid)) if valid.size else float("nan")
    return out


def _detect_events(peak_series: np.ndarray, dates: list[str]) -> list[dict]:
    """Detect WWB events from a daily spatial-peak time series.

    An event is a run of consecutive days where peak > THRESHOLD_BASE_MS,
    the run lasts more than MIN_DURATION_DAYS days, and at least one day
    within the run exceeds THRESHOLD_PEAK_MS.
    """
    events = []
    in_run = False
    run_start_idx = -1
    run_max = -np.inf
    for i, v in enumerate(peak_series):
        is_above = bool(v > THRESHOLD_BASE_MS)
        if is_above:
            if not in_run:
                in_run = True
                run_start_idx = i
                run_max = v
            else:
                run_max = max(run_max, v)
        else:
            if in_run:
                duration = i - run_start_idx
                if duration > MIN_DURATION_DAYS and run_max > THRESHOLD_PEAK_MS:
                    events.append({
                        "start": dates[run_start_idx],
                        "end": dates[i - 1],
                        "duration_days": duration,
                        "peak_ms": round(float(run_max), 2),
                    })
                in_run = False
                run_start_idx = -1
                run_max = -np.inf
    if in_run:
        duration = len(peak_series) - run_start_idx
        if duration > MIN_DURATION_DAYS and run_max > THRESHOLD_PEAK_MS:
            events.append({
                "start": dates[run_start_idx],
                "end": dates[-1],
                "duration_days": duration,
                "peak_ms": round(float(run_max), 2),
            })
    return events


def _events_for_year(year: int, end_month: int, clim: xr.DataArray) -> list[dict]:
    """Pull year's Mar-{end_month} full field, detect spatial-peak burst events."""
    months = [f"{m:02d}" for m in range(3, end_month + 1)]
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    _retrieve([str(year)], months, ALL_DAYS, tmp)
    ds = xr.open_dataset(tmp)
    u = _extract_u_field(ds)
    time_dim = "valid_time" if "valid_time" in u.coords else "time"
    times = u[time_dim]
    obs_mmdd = _mmdd(times)
    # Look up climatology at each day's mmdd, broadcasting over lat-lon
    clim_per_day = clim.sel(mmdd=obs_mmdd).values  # (time, lat, lon)
    anom = u.values - clim_per_day                 # (time, lat, lon)
    lat_step, lon_step = _grid_resolution(u)
    peaks = _spatial_peak_per_day(anom, lat_step, lon_step)
    dates = [str(t.astype("datetime64[D]")) for t in times.values]
    events = _detect_events(peaks, dates)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return events


def _build_or_load_analog(year: int, clim: xr.DataArray) -> list[dict]:
    """Cache the full Mar-Aug WWB event list for an analog year."""
    path = _analog_path(year)
    if os.path.exists(path):
        return json.loads(open(path).read())
    events = _events_for_year(year, 8, clim)
    with open(path, "w") as f:
        json.dump(events, f, indent=2)
    return events


def fetch() -> FetchResult:
    try:
        today = date.today()
        end = today - timedelta(days=5)
        if end.month < 3:
            return FetchResult(source="era5_burst", ok=False, fetched_at=now_iso(),
                               error="too early in develop year for Mar-onwards WWB detection")
        clim = _build_or_load_climatology()
        current_events = _events_for_year(end.year, end.month, clim)
        analogs = {y: _build_or_load_analog(y, clim) for y in ANALOG_YEARS}
        return FetchResult(
            source="era5_burst",
            ok=True,
            issued=end.isoformat(),
            fetched_at=now_iso(),
            payload={
                "events_since_mar1": len(current_events),
                "events_detail": current_events,
                "analogs": analogs,
                "domain": "10N-10S, 130E-150W; 5x10 deg sliding window; "
                          "thresholds 5 m/s base + 7 m/s peak, >5 days persistence",
            },
        )
    except Exception as e:
        return FetchResult(source="era5_burst", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
