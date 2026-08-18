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
# certainty and stops discriminating at the top. +3.0 exceeds every event
# in the instrumental record, so the "above +3.0" fraction is a
# directly-measured count of members forecasting an unprecedented event.
# Unlike the CPC-anchored headline (where +3.0 would be a deep
# skew-normal tail extrapolation beyond CPC's published bins), here it is
# an empirical member count.
#
# Record peaks, from CPC's own ONI series (data/oni_full_history.csv,
# persisted from fetchers/oni_history.py):
#
#     2015-16  NDJ  +2.59      <- the record
#     1997-98  NDJ  +2.37
#     1982-83  NDJ  +2.12
#     2023-24  NDJ  +1.99
#
# The record year is 2015-16, not the more famous 1997-98.
#
# This comment has now been wrong in both directions in one week, which
# is why it names its source. It originally said 2015 was "~2.6", which
# was right. On 2026-08-11 I "corrected" it to +2.80 to match
# data/oni_historical.csv, and instructed the reader to prefer that file
# on disagreement. Both were wrong: the CSV was a hand-assembled copy
# that had drifted from CPC and it was retired the next day. Quote
# oni_full_history.csv or the fetcher, never this comment, and if a
# number here disagrees with CPC then CPC wins.
THRESHOLDS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]   # traditional ONI degC

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
    # _v3 (methodology v1.9): cache now also stores per-member monthly
    # values (members_by_month), enabling a true equal-model-weight pooled
    # band for the analog chart's forecast extension instead of CFSv2's
    # own IQR. _v2 added the per-model median trajectory. Bumping the key
    # forces a one-time rebuild.
    return str(CACHE_DIR / f"nmme_{model}_{init}_nino34_peaks_v3.json")


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
        # Treat a cache that predates the current format (missing the
        # trajectory or the per-member monthly values) as a miss and
        # recompute, so downstream fields are never silently empty. The
        # _v3 key already forces this once; this guard also catches any
        # stale or partial cache that slips through.
        if cached.get("trajectory") and cached.get("members_by_month"):
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
        # draw the forecast line beyond SEAS5's horizon. members_by_month
        # (v1.9) keeps the raw member values so the pooled multi-model
        # band can be computed as true weighted percentiles, not an
        # average of per-model percentiles.
        trajectory = []
        members_by_month: dict = {}
        for i, mraw in enumerate(target_months):
            ty, tm = _months_to_year_month(float(mraw))
            col = nino34_per_target.isel(target=i).values
            col = col[~np.isnan(col)]
            if col.size == 0:
                continue
            cal_key = f"{ty:04d}-{tm:02d}"
            members_by_month[cal_key] = [round(float(v), 2) for v in col.tolist()]
            trajectory.append({
                "calendar": cal_key,
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
            "members_by_month": members_by_month,
        }
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    with open(cache, "w") as f:
        json.dump(result, f, indent=2)
    return result


def _oni_peaks_from_members(members_by_month: dict) -> list:
    """Per-member peak ONI over the target window, from monthly member values.

    ONI is a THREE-MONTH RUNNING MEAN. Until 2026-08-15 the threshold
    fractions were computed from each member's peak MONTHLY Nino 3.4 value
    and then compared against CPC's ONI-based strength table, so the anchor
    and the consensus were two different quantities being blended. A running
    mean cuts peaks, so the monthly basis overstated every upper rung, and by
    more the higher the rung:

        threshold   monthly    ONI
          >3.0        100       96
          >3.5         79       70
          >4.0         57       43

    Seasons are the 3-month windows CENTRED in the target window, so the
    NDJ/DJF peak CPC's table describes is the one measured here.

    Members are matched by position across months, so a month whose member
    count differs (an all-NaN column dropped upstream) is skipped rather than
    silently misaligning one member's November with another's December.
    """
    if not members_by_month:
        return []
    counts = {len(v) for v in members_by_month.values() if v}
    if not counts:
        return []
    n_members = max(counts, key=lambda c: sum(
        1 for v in members_by_month.values() if len(v) == c))
    usable = {k: v for k, v in members_by_month.items() if len(v) == n_members}

    lo = PEAK_WINDOW_FIRST[0] * 12 + (PEAK_WINDOW_FIRST[1] - 1)
    hi = PEAK_WINDOW_LAST[0] * 12 + (PEAK_WINDOW_LAST[1] - 1)
    windows = []
    for centre in range(lo, hi + 1):
        keys = []
        for off in (-1, 0, 1):
            y, m = divmod(centre + off, 12)
            keys.append(f"{y:04d}-{m + 1:02d}")
        if all(k in usable for k in keys):
            windows.append(keys)
    if not windows:
        return []

    peaks = []
    for j in range(n_members):
        peaks.append(round(max(
            sum(usable[k][j] for k in w) / 3.0 for w in windows), 2))
    return peaks


def _download_and_extract_peaks(model: str, init: str) -> dict:
    """Raw cached peaks plus freshly-computed threshold fractions.

    Fractions come from the ONI-basis peaks (3-month running mean), because
    they are compared against, and blended with, a CPC anchor derived from
    CPC's ONI-based strength table. `peaks_per_member` stays as it was, the
    peak MONTHLY value, since the trajectory and the pooled band are monthly
    objects; it is simply no longer what the probabilities are computed from.

    Falls back to the monthly basis only when a cache predates
    members_by_month (the v2 entries used by the backfill), so an old cache
    degrades to the previous behaviour rather than to no number at all. The
    `basis` field says which was used, so a consumer never has to guess.
    """
    raw = _raw_peaks(model, init)
    oni = _oni_peaks_from_members(raw.get("members_by_month") or {})

    # PER-FIELD basis, not per-model. A single `basis` string sat at model
    # level from 2026-08-15 and appeared to describe the whole node while
    # only describing frac_above. `ensemble_mean_peak` is a MONTHLY peak
    # and sat right beside it labelled oni_3mo_mean.
    #
    # That is not a cosmetic mislabel. Product read the field, concluded
    # the pooled 3.96 headline was already ONI-comparable, told another
    # desk the question was settled and told aftereffects to stop looking.
    # It is 3.96 monthly against about 3.81 on the ONI basis, so any
    # comparison against the 2.59 record overstated by ~0.15. Found by
    # aftereffects, 2026-08-17.
    #
    # A map because this node accumulates fields, and the next one to be
    # misread will not announce itself. D-051 applied to emitted data
    # rather than to copy: the qualifier travels with the datum, and a
    # qualifier that describes its NEIGHBOUR is worse than none, because
    # it is trusted.
    if oni:
        return {**raw,
                "oni_peaks_per_member": oni,
                "ensemble_mean_peak_oni": round(float(np.nanmean(oni)), 2),
                "frac_above": _frac_above(oni),
                "basis": {
                    "frac_above": "oni_3mo_mean",
                    "oni_peaks_per_member": "oni_3mo_mean",
                    "ensemble_mean_peak_oni": "oni_3mo_mean",
                    "ensemble_mean_peak": "monthly_peak",
                    "peaks_per_member": "monthly_peak",
                    "trajectory": "monthly_percentiles",
                    "members_by_month": "monthly_per_member",
                }}
    return {**raw, "frac_above": _frac_above(raw["peaks_per_member"]),
            "basis": {
                "frac_above": "monthly_peak",
                "ensemble_mean_peak": "monthly_peak",
                "peaks_per_member": "monthly_peak",
            }}


def _weighted_percentile(values, weights, pct: float) -> float:
    """Percentile of `values` under `weights` via the cumulative-weight
    midpoint convention. values/weights are parallel lists."""
    order = np.argsort(values)
    v = np.asarray(values, dtype=float)[order]
    w = np.asarray(weights, dtype=float)[order]
    cum = np.cumsum(w) - 0.5 * w
    cum /= np.sum(w)
    return float(np.interp(pct / 100.0, cum, v))


def _pooled_trajectory(model_results: list) -> list:
    """Equal-model-weight pooled monthly forecast across the NMME suite.

    For each target month, pool every model's members with weight
    1/(n_models x n_members_of_that_model), so each MODEL contributes
    equally regardless of ensemble size (the same convention as the
    consensus threshold fractions). Returns a list of
    {calendar, median, p25, p75, n_models, n_members} sorted by month.

    This is the "per-month member pool" band for the analog chart's
    forecast extension (methodology v1.9), replacing the earlier first
    cut that used CFSv2's own IQR: a true mixture is wider than any one
    model's spread when the models disagree, which is exactly the
    uncertainty the extension should show.
    """
    ok = [m for m in model_results
          if "error" not in m and m.get("members_by_month")]
    if not ok:
        return []
    months = sorted({cal for m in ok for cal in m["members_by_month"]})
    out = []
    for cal in months:
        vals, wts, n_models = [], [], 0
        contributing = [m for m in ok if m["members_by_month"].get(cal)]
        for m in contributing:
            mv = m["members_by_month"][cal]
            w = 1.0 / (len(contributing) * len(mv))
            vals.extend(mv)
            wts.extend([w] * len(mv))
            n_models += 1
        if not vals:
            continue
        out.append({
            "calendar": cal,
            "median": round(_weighted_percentile(vals, wts, 50), 2),
            "p25": round(_weighted_percentile(vals, wts, 25), 2),
            "p75": round(_weighted_percentile(vals, wts, 75), 2),
            "n_models": n_models,
            "n_members": len(vals),
        })
    return out


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


def _ensemble_average_oni(model_results: list[dict]) -> float:
    """Cross-model mean of the ONI-basis peak.

    The pooled headline was reported as ~3.96 monthly, which is ~3.81 on
    this basis. Anywhere a model peak is set beside the +2.59 ONI record,
    THIS is the comparable figure; the monthly one overstates by ~0.15
    because a three-month mean cuts peaks.
    """
    peaks = [m["ensemble_mean_peak_oni"] for m in model_results
             if m and m.get("ensemble_mean_peak_oni") is not None]
    return round(float(np.mean(peaks)), 2) if peaks else None


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
        # Trajectories surfaced top-level for the analog chart's forecast
        # extension (reaching past SEAS5's horizon). pooled_trajectory
        # (v1.9) is the equal-model-weight member pool and is preferred;
        # cfsv2_trajectory is retained as a fallback and for continuity.
        # Slim per-model dicts: the panel needs neither raw members, the
        # trajectory, nor members_by_month.
        cfsv2 = next((m for m in model_results if m.get("model") == "CFSv2"
                      and "error" not in m), None)
        cfsv2_trajectory = cfsv2.get("trajectory") if cfsv2 else None
        pooled_traj = _pooled_trajectory(model_results)
        return FetchResult(
            source="nmme",
            ok=True,
            issued=issued_iso,
            fetched_at=now_iso(),
            payload={
                "init": init,
                "models": {m["model"]: {k: v for k, v in m.items()
                                         if k not in ("peaks_per_member",
                                                      "trajectory",
                                                      "members_by_month")}
                           for m in model_results},
                "cfsv2_trajectory": cfsv2_trajectory,
                "pooled_trajectory": pooled_traj,
                "ensemble_mean_peak": avg_peak,
                "ensemble_mean_peak_oni": _ensemble_average_oni(model_results),
                # Which basis each top-level field is on. Same reason as the
                # per-model map: a node that grows fields outgrows a single
                # label, and the one that gets misread is never the one you
                # labelled.
                "basis": {
                    "ensemble_mean_peak": "monthly_peak",
                    "ensemble_mean_peak_oni": "oni_3mo_mean",
                    "ensemble_frac_above": "oni_3mo_mean",
                    "pooled_trajectory": "monthly_percentiles",
                    "cfsv2_trajectory": "monthly_percentiles",
                },
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
