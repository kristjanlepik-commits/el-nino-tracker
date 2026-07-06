"""
Fetch NMME multi-model Nino 3.4 forecast for the brief's target peak season.

Source: https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/{MODEL}/{INIT}/
Cadence: monthly, around the 8th of each month.

Data format. Each model publishes per-month anomaly NetCDF files of shape
(ensmem, target, lat, lon) with global 1-degree resolution, where each
'target' coordinate is a future month and each 'ensmem' is an individual
ensemble member of that model's run. Anomalies are computed against the
model's own hindcast climatology, matching SEAS5's convention so the two
sources are apples-to-apples comparable.

Why we use NMME alongside SEAS5. Through v1.7 the only model deflection
input to the v1.5 smoothed headline was SEAS5. When CPC's anchor is
materially below the model consensus (as happened in May 2026), SEAS5's
deflection saturates at the +-10 ppt cap and additional model agreement
cannot move the headline. Adding NMME contributes one or more independent
model signals to the same deflection channel, so the multi-model
consensus pulls the smoothed headline rather than a single model.

Out of scope this fetcher. We pull per-model member counts at four upper
tail thresholds plus each model's ensemble mean peak. We do NOT yet wire
the result into probs.smoothed_headline_buckets; that is a separate
methodology change (queued for v1.8 after the panel data is validated
visually).

Expected payload.
  issued:              ISO date of the NMME init we used
  models:              dict[model_name] -> {
                         peak_month_iso:  ISO date of the peak target month
                         ensemble_mean_peak: float, deg C
                         n_members:       int
                         frac_above: {'1.0': pct, '1.5': pct,
                                      '2.0': pct, '2.5': pct}
                       }
  ensemble_mean_peak:  float, mean across models of ensemble_mean_peak
  ensemble_frac_above: {threshold -> percent, averaged across models}
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date

import numpy as np
import xarray as xr

from ._common import CACHE_DIR, FetchResult, http_get, now_iso

FTP_BASE = "https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom"

# Models with multi-member anomaly NetCDFs on the NMME FTP. Each model
# directory contains files named "{MODEL}.tmpsfc.{YYYYMM}.anom.nc".
# GFDL_SPEAR and NASA_GEOS5v2 are excluded for the MVP because GFDL
# uses a different file layout and GEOS5v2 has smaller member counts
# that may not bound an upper-tail probability stably; both are queued
# for a phase-2 sweep.
MODELS = [
    "CFSv2",
    "CanESM5",
    "GEM5.2_NEMO",
    "NCAR_CCSM4",
    "NCAR_CESM1",
]

# Nino 3.4 region: 5N-5S, 170W-120W (= 190E-240E in 0-360 longitude).
NINO34_LAT = (5.0, -5.0)     # slice expects descending if lat goes 90 to -90
NINO34_LON = (190.0, 240.0)

# Peak window for the brief's headline target (DJF 2026-27): use NDJ to
# DJF months, then take the per-member max. NMME models cover roughly 9
# months from init, so a May 2026 init reaches Jan 2027; some models
# extend through Feb. We accept any subset that overlaps Nov 2026 - Feb 2027.
PEAK_WINDOW_FIRST = (2026, 11)   # Nov 2026
PEAK_WINDOW_LAST = (2027, 2)     # Feb 2027

# Traditional ONI thresholds (deg C). +3.0 is included because the 2026
# multi-model consensus clusters near +3.3, so +2.5 saturates toward
# certainty and stops discriminating at the top. +3.0 exceeds every
# event in the instrumental record (1997 ~2.4, 2015 ~2.6, 1877 ~2.5 on
# HadISST), so the "above +3.0" fraction is a directly-measured count of
# members forecasting an unprecedented event. Unlike the CPC-anchored
# headline (where +3.0 would be a deep skew-normal tail extrapolation
# beyond CPC's published bins), here it is an empirical member count.
THRESHOLDS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]   # traditional ONI degC

# Months base for the NMME files' 'target' coordinate, which uses
# "months since 1960-01-02 21:00:00".
_NMME_TIME_ORIGIN = (1960, 1)


def _months_to_year_month(months_since_origin: float) -> tuple[int, int]:
    """Convert NMME's 'months since 1960-01' integer to (year, month)."""
    total = _NMME_TIME_ORIGIN[0] * 12 + (_NMME_TIME_ORIGIN[1] - 1) + int(round(months_since_origin))
    return total // 12, (total % 12) + 1


def _year_month_in_window(y: int, m: int) -> bool:
    n = y * 12 + (m - 1)
    lo = PEAK_WINDOW_FIRST[0] * 12 + (PEAK_WINDOW_FIRST[1] - 1)
    hi = PEAK_WINDOW_LAST[0] * 12 + (PEAK_WINDOW_LAST[1] - 1)
    return lo <= n <= hi


def _latest_init(model: str) -> str:
    """Return the most recent YYYYMMDDHH init dir present for `model`."""
    url = f"{FTP_BASE}/{model}/"
    r = http_get(url, timeout=30)
    inits = sorted(set(re.findall(r"(20\d{8})/", r.text)))
    if not inits:
        raise RuntimeError(f"no init directories found for {model}")
    return inits[-1]


def _model_file_url(model: str, init: str) -> str:
    """e.g. .../{model}/2026050800/{model}.tmpsfc.202605.anom.nc"""
    yyyymm = init[:6]
    return f"{FTP_BASE}/{model}/{init}/{model}.tmpsfc.{yyyymm}.anom.nc"


def _cache_path(model: str, init: str) -> str:
    # _v2: cache now also stores the per-target-month median trajectory
    # (needed for the analog chart's CFSv2 extension line), not just the
    # per-member peaks. Bumping the key forces a one-time rebuild.
    return str(CACHE_DIR / f"nmme_{model}_{init}_nino34_peaks_v2.json")


def _frac_above(peaks: list[float]) -> dict[str, float]:
    """Percent of members whose peak exceeds each THRESHOLDS value.

    Computed fresh on every call (not cached), so changing THRESHOLDS
    never requires re-downloading the model files. The expensive part
    (the NetCDF pull and Nino 3.4 extraction) caches the raw per-member
    peaks; thresholds are pure post-processing on top.
    """
    arr = np.array(peaks, dtype=float)
    return {
        f"{t:.1f}": round(100.0 * float(np.mean(arr > t)), 1)
        for t in THRESHOLDS
    }


def _raw_peaks(model: str, init: str) -> dict:
    """Pull one model's anomaly NetCDF and return the per-member peak
    Nino 3.4 anomaly over the brief's target peak window. The result
    (raw peaks plus metadata, NO threshold fractions) is cached so that
    THRESHOLDS can change without a re-download."""
    cache = _cache_path(model, init)
    if os.path.exists(cache):
        cached = json.loads(open(cache).read())
        # Treat a cache that predates the trajectory format (or is otherwise
        # missing the per-month trajectory) as a miss and recompute, so
        # cfsv2_trajectory is never silently empty. The _v2 key already
        # forces this once; this guard also catches any stale or partial
        # cache that slips through.
        if cached.get("trajectory"):
            return cached

    url = _model_file_url(model, init)
    r = http_get(url, timeout=180)
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    with open(tmp, "wb") as f:
        f.write(r.content)
    try:
        ds = xr.open_dataset(tmp, decode_times=False)
        # Find Nino 3.4 box. Lat coord runs 90 to -90 in NMME files; use
        # sel with explicit slice direction.
        lat_first, lat_last = NINO34_LAT  # (5, -5)
        lon_first, lon_last = NINO34_LON  # (190, 240)
        fcst = ds["fcst"]
        # Some files have lat ascending vs descending; handle both.
        lat_vals = ds["lat"].values
        if lat_vals[0] > lat_vals[-1]:
            lat_slice = slice(lat_first, lat_last)
        else:
            lat_slice = slice(lat_last, lat_first)
        box = fcst.sel(lat=lat_slice, lon=slice(lon_first, lon_last))
        # Area-mean over the box. cos-weight by latitude.
        weights = np.cos(np.deg2rad(box["lat"]))
        nino34_per_target = (box * weights).sum(("lat", "lon")) / (
            weights * xr.ones_like(box.isel(ensmem=0, target=0))
        ).sum(("lat", "lon"))
        # Shape: (ensmem, target). Build per-member peak over the
        # NDJ-DJF window.
        target_months = ds["target"].values
        peak_window_idx = [
            i for i, m in enumerate(target_months)
            if _year_month_in_window(*_months_to_year_month(float(m)))
        ]
        if not peak_window_idx:
            raise RuntimeError(
                f"{model} {init} target window has no months in NDJ-DJF "
                f"2026-27 (targets: {target_months.tolist()})"
            )
        in_window = nino34_per_target.isel(target=peak_window_idx)
        peaks = in_window.max(dim="target").values   # per-member peak
        ensemble_mean_peak = float(np.nanmean(peaks))
        n_members = int(len(peaks))
        peak_month_idx = int(in_window.mean(dim="ensmem").argmax(dim="target"))
        peak_month_year, peak_month_month = _months_to_year_month(
            float(target_months[peak_window_idx[peak_month_idx]])
        )
        # Per-target-month ensemble trajectory over the FULL forecast
        # range (not just the peak window). The analog chart uses this to
        # draw the model's median line beyond SEAS5's 6-month horizon.
        trajectory = []
        for i, mraw in enumerate(target_months):
            ty, tm = _months_to_year_month(float(mraw))
            col = nino34_per_target.isel(target=i).values
            col = col[~np.isnan(col)]
            if col.size == 0:
                continue
            trajectory.append({
                "calendar": f"{ty:04d}-{tm:02d}",
                "median": round(float(np.median(col)), 2),
                "p25": round(float(np.percentile(col, 25)), 2),
                "p75": round(float(np.percentile(col, 75)), 2),
            })
        result = {
            "model": model,
            "init": init,
            "ensemble_mean_peak": round(ensemble_mean_peak, 2),
            "n_members": n_members,
            "peak_month_iso": f"{peak_month_year:04d}-{peak_month_month:02d}-01",
            "peaks_per_member": [round(float(p), 2) for p in peaks.tolist()],
            "trajectory": trajectory,
        }
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    with open(cache, "w") as f:
        json.dump(result, f, indent=2)
    return result


def _download_and_extract_peaks(model: str, init: str) -> dict:
    """Raw cached peaks plus freshly-computed threshold fractions."""
    raw = _raw_peaks(model, init)
    return {**raw, "frac_above": _frac_above(raw["peaks_per_member"])}


def _ensemble_average(model_results: list[dict]) -> tuple[float, dict[str, float]]:
    """Equal-weighted mean across models of peak forecasts and threshold probs."""
    peaks = [m["ensemble_mean_peak"] for m in model_results if m]
    fracs: dict[str, list[float]] = {f"{t:.1f}": [] for t in THRESHOLDS}
    for m in model_results:
        if not m:
            continue
        for k, v in m["frac_above"].items():
            fracs[k].append(v)
    avg_peak = round(float(np.mean(peaks)), 2) if peaks else float("nan")
    avg_frac = {k: round(float(np.mean(vs)), 1) if vs else 0.0
                for k, vs in fracs.items()}
    return avg_peak, avg_frac


def fetch() -> FetchResult:
    try:
        # Use ENSMEAN as the reference for the latest init, since it is
        # always present and updated whenever NMME publishes a new month.
        init = _latest_init("ENSMEAN")
        model_results = []
        for model in MODELS:
            try:
                model_results.append(_download_and_extract_peaks(model, init))
            except Exception as e:
                model_results.append({
                    "model": model, "init": init,
                    "error": f"{type(e).__name__}: {e}",
                })
        ok_results = [m for m in model_results if "error" not in m]
        if not ok_results:
            return FetchResult(source="nmme", ok=False, fetched_at=now_iso(),
                               error=f"all {len(MODELS)} models failed; first error: "
                                     f"{model_results[0].get('error')}")
        avg_peak, avg_frac = _ensemble_average(ok_results)
        # NMME init dirs are YYYYMMDDHH; CPC publishes around the 8th.
        # Convert to ISO date for the FetchResult.issued field.
        yyyy, mm, dd = int(init[:4]), int(init[4:6]), int(init[6:8])
        issued_iso = date(yyyy, mm, dd).isoformat()
        # CFSv2 per-month median trajectory, surfaced top-level for the
        # analog chart's extension line (it reaches the DJF peak that
        # SEAS5's 6-month horizon cannot). Slim per-model dicts: the panel
        # needs neither raw members nor the trajectory.
        cfsv2 = next((m for m in model_results if m.get("model") == "CFSv2"
                      and "error" not in m), None)
        cfsv2_trajectory = cfsv2.get("trajectory") if cfsv2 else None
        return FetchResult(
            source="nmme",
            ok=True,
            issued=issued_iso,
            fetched_at=now_iso(),
            payload={
                "init": init,
                "models": {m["model"]: {k: v for k, v in m.items()
                                         if k not in ("peaks_per_member",
                                                      "trajectory")}
                           for m in model_results},
                "cfsv2_trajectory": cfsv2_trajectory,
                "ensemble_mean_peak": avg_peak,
                "ensemble_frac_above": avg_frac,
                "thresholds_degC": THRESHOLDS,
                "peak_window": "Nov 2026 - Feb 2027 (NDJ-DJF)",
                "nino34_region": "5N-5S, 170W-120W",
                "n_models_ok": len(ok_results),
                "n_models_attempted": len(MODELS),
            },
        )
    except Exception as e:
        return FetchResult(source="nmme", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
