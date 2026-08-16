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

Methodology (v1.7):

For each day, slide a 5deg lat x 10deg lon window over the search domain
10N-10S, 130E-150W. Compute the area-mean of u'_850 anomaly within each
window position. The maximum across all window positions for that day is
the day's "spatial peak anomaly."

Event detection on the resulting time series (v1.7, peak-based with
recovery interval, replaces v1.6 run-detection):

1. Candidate peak days: days where spatial peak > THRESHOLD_PEAK_MS (7 m/s).
2. Non-maximum suppression by amplitude: starting from the strongest
   candidate, select it; suppress all candidates within +/-RECOVERY_DAYS
   (10) of any already-selected peak. This produces a set of distinct
   peak days separated by at least RECOVERY_DAYS days each.
3. For each surviving peak day, define the event window as the
   contiguous run of days surrounding it where spatial peak >
   THRESHOLD_BASE_MS (5 m/s), bounded by midpoint to neighboring
   selected peaks (so two close peaks split the contiguous run rather
   than each claiming the whole thing).
4. Drop events shorter than MIN_DURATION_DAYS.

This fixes the v1.6 limitation where a 71-day or 104-day sustained
westerly period was collapsed into a single "event" despite physically
containing multiple distinct bursts. RECOVERY_DAYS = 10 matches the
typical separation between distinct equatorial WWBs in the
super-event literature (McPhaden 1999, Lengaigne et al. 2003).

Cache layout:

- era5_burst_clim_*.nc:                 full-field climatology
- era5_burst_peakseries_{year}_*.json:  per-day spatial peak series
                                        (algorithm-independent, derived
                                        directly from ERA5 anomalies)
- era5_burst_events_{year}_*_v18.json:  events detected by v1.7 algorithm,
                                        v18 adds censoring flags
                                        (algorithm-version-tagged so a
                                        future v1.8 detector reuses the
                                        peakseries cache without CDS calls)

Cold-cache: ~30 min (climatology rebuild + 4 analog years).
Warm-cache: ~3 min (current observation only).
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

# Algorithm version tag; bump when detection logic changes.
ALGORITHM_VERSION = "v18"

# Burst detection parameters
WINDOW_LAT_DEG = 5.0
WINDOW_LON_DEG = 10.0
THRESHOLD_BASE_MS = 5.0
THRESHOLD_PEAK_MS = 7.0
MIN_DURATION_DAYS = 5
RECOVERY_DAYS = 10  # NEW in v1.7: minimum peak-to-peak separation


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


def _peakseries_path(year: int) -> str:
    return str(CACHE_DIR / f"era5_burst_peakseries_{year}_130E-150W_10NS.json")


def _events_path(year: int) -> str:
    return str(CACHE_DIR / f"era5_burst_events_{year}_130E-150W_10NS_{ALGORITHM_VERSION}.json")


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


def _compute_peakseries(year: int, end_month: int, clim: xr.DataArray) -> tuple[list[str], np.ndarray]:
    """CDS pull + spatial-peak reduction for one year, Mar through end_month."""
    months = [f"{m:02d}" for m in range(3, end_month + 1)]
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    _retrieve([str(year)], months, ALL_DAYS, tmp)
    ds = xr.open_dataset(tmp)
    u = _extract_u_field(ds)
    time_dim = "valid_time" if "valid_time" in u.coords else "time"
    times = u[time_dim]
    obs_mmdd = _mmdd(times)
    clim_per_day = clim.sel(mmdd=obs_mmdd).values
    anom = u.values - clim_per_day
    lat_step, lon_step = _grid_resolution(u)
    peaks = _spatial_peak_per_day(anom, lat_step, lon_step)
    dates = [str(t.astype("datetime64[D]")) for t in times.values]
    try:
        os.remove(tmp)
    except OSError:
        pass
    return dates, peaks


def _load_or_build_analog_peakseries(year: int, clim: xr.DataArray) -> tuple[list[str], np.ndarray]:
    """Cached peakseries for an analog year (always full Mar-Aug)."""
    path = _peakseries_path(year)
    if os.path.exists(path):
        data = json.loads(open(path).read())
        return data["dates"], np.array(data["peaks"], dtype=np.float64)
    dates, peaks = _compute_peakseries(year, 8, clim)
    with open(path, "w") as f:
        json.dump({"year": year, "end_month": 8, "dates": dates, "peaks": peaks.tolist()}, f)
    return dates, peaks


def _detect_events(peak_series: np.ndarray, dates: list[str]) -> list[dict]:
    """v1.7 peak-detection with recovery interval.

    Algorithm:
    1. Find all days where peak > THRESHOLD_PEAK_MS (candidate peaks).
    2. Greedy non-maximum suppression by amplitude: select the strongest
       remaining candidate, then suppress all candidates within
       +/-RECOVERY_DAYS days of it; repeat.
    3. For each surviving peak day, define the event interval as the
       contiguous run of days around it where peak > THRESHOLD_BASE_MS,
       bounded by the midpoint to neighboring selected peaks.
    4. Drop events shorter than MIN_DURATION_DAYS days.

    The midpoint bound prevents long sustained-westerly periods from
    being entirely claimed by one peak; each distinct burst gets its
    own slice of the active run.
    """
    n = len(peak_series)
    if n == 0:
        return []

    # Step 1: candidate peak days
    candidates = [(i, float(peak_series[i])) for i in range(n)
                  if float(peak_series[i]) > THRESHOLD_PEAK_MS]
    if not candidates:
        return []

    # Step 2: greedy NMS by amplitude
    candidates_sorted = sorted(candidates, key=lambda x: -x[1])
    selected: list[tuple[int, float]] = []
    for idx, val in candidates_sorted:
        if all(abs(idx - sel_idx) >= RECOVERY_DAYS for sel_idx, _ in selected):
            selected.append((idx, val))
    selected.sort(key=lambda x: x[0])

    # Step 3: event boundaries with midpoint capping
    events = []
    for k, (p_idx, p_val) in enumerate(selected):
        left_bound = (selected[k-1][0] + p_idx) // 2 + 1 if k > 0 else 0
        right_bound = (p_idx + selected[k+1][0]) // 2 if k < len(selected) - 1 else n - 1

        # Walk back from peak while above base threshold; never cross left_bound
        event_start_idx = p_idx
        for i in range(p_idx - 1, left_bound - 1, -1):
            if float(peak_series[i]) > THRESHOLD_BASE_MS:
                event_start_idx = i
            else:
                break

        # Walk forward from peak while above base threshold; never cross right_bound
        event_end_idx = p_idx
        for i in range(p_idx + 1, right_bound + 1):
            if float(peak_series[i]) > THRESHOLD_BASE_MS:
                event_end_idx = i
            else:
                break

        duration = event_end_idx - event_start_idx + 1

        # An event still above threshold on the LAST observed day has not been
        # seen to end. Its end date and duration are lower bounds, set by where
        # the data stops rather than by the atmosphere. ERA5 runs about six
        # days behind, so the current year's most recent event is censored
        # more often than not: on 2026-08-15 the active burst was reported as
        # a finished 16-day event ending 2026-08-09, which was simply the last
        # day we had.
        #
        # Emitted rather than corrected, because there is nothing to correct.
        # A consumer that prints durations needs to say "16 days so far", and
        # one that compares against analog years must not treat a censored
        # duration as comparable to a completed one.
        ongoing = event_end_idx == n - 1

        # The same censoring can DELETE an event: one that began within
        # MIN_DURATION_DAYS of the data edge is dropped for being too short
        # when it may simply be too young. Kept when it is still active, and
        # flagged, so a burst that starts near the boundary is visible as
        # provisional instead of absent. Absence is the harder failure to
        # notice, and this week has been a lesson in that.
        if duration < MIN_DURATION_DAYS and not ongoing:
            continue

        events.append({
            "start": dates[event_start_idx],
            "end": dates[event_end_idx],
            "duration_days": duration,
            "peak_ms": round(float(p_val), 2),
            "peak_date": dates[p_idx],
            # True when the event is still above threshold on the last
            # observed day: `end` and `duration_days` are then lower bounds,
            # and `peak_ms` may yet be exceeded.
            "ongoing": ongoing,
            "provisional_short": duration < MIN_DURATION_DAYS,
        })
    return events


def _events_for_current_year(year: int, end_month: int, clim: xr.DataArray) -> list[dict]:
    """Current-year events: always re-pull from CDS (data accretes weekly)."""
    dates, peaks = _compute_peakseries(year, end_month, clim)
    return _detect_events(peaks, dates)


def _events_for_analog_year(year: int, clim: xr.DataArray) -> list[dict]:
    """Analog-year events: peakseries cached, events cached per algorithm version."""
    ev_path = _events_path(year)
    if os.path.exists(ev_path):
        return json.loads(open(ev_path).read())
    dates, peaks = _load_or_build_analog_peakseries(year, clim)
    events = _detect_events(peaks, dates)
    with open(ev_path, "w") as f:
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
        current_events = _events_for_current_year(end.year, end.month, clim)
        analogs = {y: _events_for_analog_year(y, clim) for y in ANALOG_YEARS}
        return FetchResult(
            source="era5_burst",
            ok=True,
            issued=end.isoformat(),
            fetched_at=now_iso(),
            payload={
                "events_since_mar1": len(current_events),
                "events_detail": current_events,
                "analogs": analogs,
                "algorithm_version": ALGORITHM_VERSION,
                "domain": "10N-10S, 130E-150W; 5x10 deg sliding window; "
                          "thresholds 5 m/s base + 7 m/s peak, >=5 days persistence, "
                          "10-day peak-to-peak recovery (v1.7)",
            },
        )
    except Exception as e:
        return FetchResult(source="era5_burst", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
