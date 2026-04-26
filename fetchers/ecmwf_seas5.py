"""
Fetch ECMWF SEAS5 ensemble Niño 3.4 forecasts via Copernicus CDS.

Dataset: seasonal-monthly-single-levels
Variable: sea_surface_temperature (K)
Region:   5N-5S, 170W-120W (= 190E-240E in 0-360 convention)
Cadence:  monthly, around the 5th.

Auth:     CDS API key in ~/.cdsapirc.

The fetcher pulls the latest SEAS5 monthly forecast (51 members, leads 1-6,
which is the standard SEAS5 product window), then computes member-level
anomalies against the SEAS5 model climatology. The climatology is the mean
across the 1993-2016 hindcasts (25 members, same start month, same leads)
and is cached on disk because it changes essentially never; only the
forecast pull runs on each weekly invocation.

We report on every lead month available, but the headline metric is the
LONGEST-lead month available (forecastMonth=6), which from an April run
is October. DJF target months are typically not reachable until a June or
later run; when they are, the same code path picks them up automatically.

Expected payload:
  issued: ISO date (first day of the SEAS5 run month)
  system: int (51)
  run_year, run_month: ints
  member_count: int (51 for current SEAS5)
  max_lead_month: int (typically 6)
  max_lead_calendar: str ("YYYY-MM")
  median_anomaly: float (median Niño 3.4 anomaly across members at max lead, deg C)
  members_above: dict[str, int] for thresholds {"1.0", "1.5", "2.0", "2.5"} at max lead
  per_lead: list of dicts (one per lead) with the same shape, for the brief
  summary: short auto-generated text describing the headline result
"""

from __future__ import annotations

import os
import tempfile
from datetime import date

import xarray as xr

from ._common import CACHE_DIR, FetchResult, now_iso

DATASET = "seasonal-monthly-single-levels"
SYSTEM = "51"
ORIGIN = "ecmwf"
NINO34_AREA = [5, 190, -5, 240]   # N, W, S, E in 0-360 longitude
HINDCAST_YEARS = [str(y) for y in range(1993, 2017)]  # 1993-2016, 24 years
LEADS = ["1", "2", "3", "4", "5", "6"]
THRESHOLDS = (1.0, 1.5, 2.0, 2.5)


def _cds_client():
    import cdsapi
    return cdsapi.Client(quiet=True, progress=False)


def _retrieve_seas5(years: list[str], month: str, leads: list[str], path: str) -> None:
    _cds_client().retrieve(
        DATASET,
        {
            "format": "netcdf",
            "originating_centre": ORIGIN,
            "system": SYSTEM,
            "variable": "sea_surface_temperature",
            "product_type": "monthly_mean",
            "year": years,
            "month": month,
            "leadtime_month": leads,
            "area": NINO34_AREA,
        },
        path,
    )


def _area_mean(da: xr.DataArray) -> xr.DataArray:
    return da.mean(dim=["latitude", "longitude"])


def _climatology_path(start_month: int) -> str:
    return str(CACHE_DIR / f"seas5_clim_M{start_month:02d}_S{SYSTEM}.nc")


def _build_or_load_climatology(start_month: int) -> xr.DataArray:
    """Return (forecastMonth,) area-mean climatological SST in K."""
    path = _climatology_path(start_month)
    if os.path.exists(path):
        return xr.open_dataarray(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    _retrieve_seas5(HINDCAST_YEARS, f"{start_month:02d}", LEADS, tmp)
    ds = xr.open_dataset(tmp)
    # area-mean per (year, member, lead), then mean over years and members
    sst_box_mean = _area_mean(ds["sst"])
    clim = sst_box_mean.mean(dim=["forecast_reference_time", "number"])
    clim = clim.rename("sst_clim")
    clim.to_netcdf(path)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return xr.open_dataarray(path)


def _summarize_lead(per_lead: list[dict]) -> str:
    # headline at max lead
    headline = per_lead[-1]
    pct_above_2 = round(100 * headline["members_above"]["2.0"] / headline["member_count"])
    pct_above_25 = round(100 * headline["members_above"]["2.5"] / headline["member_count"])
    return (
        f"{headline['member_count']}-member SEAS5 ensemble for "
        f"{headline['calendar']}: median Niño 3.4 anomaly "
        f"{headline['median']:+.2f} deg C; {headline['members_above']['1.5']}/"
        f"{headline['member_count']} members above +1.5 (~{pct_above_2}% above +2.0, "
        f"~{pct_above_25}% above +2.5)."
    )


def _calendar_for_lead(run_year: int, run_month: int, lead: int) -> str:
    abs_month = run_year * 12 + (run_month - 1) + lead
    y = abs_month // 12
    m = (abs_month % 12) + 1
    return f"{y}-{m:02d}"


def _latest_run(now_year: int, now_month: int) -> tuple[int, int, str]:
    """Try the current calendar month first; fall back one month on failure."""
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    for offset in (0, -1):
        abs_m = now_year * 12 + (now_month - 1) + offset
        y, m = abs_m // 12, (abs_m % 12) + 1
        try:
            _retrieve_seas5([str(y)], f"{m:02d}", LEADS, tmp)
            return y, m, tmp
        except Exception:
            continue
    raise RuntimeError("could not retrieve SEAS5 forecast for current or previous month")


def fetch() -> FetchResult:
    try:
        today = date.today()
        run_year, run_month, fc_path = _latest_run(today.year, today.month)

        ds = xr.open_dataset(fc_path)
        fc_box = _area_mean(ds["sst"])  # (number, fcrt, forecastMonth)

        clim = _build_or_load_climatology(run_month)  # (forecastMonth,)

        anom = (fc_box - clim).squeeze("forecast_reference_time", drop=True)
        # anom dims: (number, forecastMonth)

        per_lead = []
        for fm in anom.coords["forecastMonth"].values.tolist():
            arr = anom.sel(forecastMonth=fm).values  # (member,)
            members_above = {f"{t:.1f}": int((arr > t).sum()) for t in THRESHOLDS}
            per_lead.append({
                "lead": int(fm),
                "calendar": _calendar_for_lead(run_year, run_month, int(fm)),
                "member_count": int(arr.size),
                "median": float(_safe_median(arr)),
                "p5": float(_pctl(arr, 5)),
                "p25": float(_pctl(arr, 25)),
                "p75": float(_pctl(arr, 75)),
                "p95": float(_pctl(arr, 95)),
                "members_above": members_above,
            })

        try:
            os.remove(fc_path)
        except OSError:
            pass

        headline = per_lead[-1]
        payload = {
            "system": int(SYSTEM),
            "run_year": run_year,
            "run_month": run_month,
            "member_count": headline["member_count"],
            "max_lead_month": headline["lead"],
            "max_lead_calendar": headline["calendar"],
            "median_anomaly": headline["median"],
            "members_above": headline["members_above"],
            "per_lead": per_lead,
            "summary": _summarize_lead(per_lead),
        }
        issued = date(run_year, run_month, 1).isoformat()
        return FetchResult(
            source="ecmwf_seas5",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload=payload,
        )
    except Exception as e:
        return FetchResult(source="ecmwf_seas5", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")


def _safe_median(arr) -> float:
    import numpy as np
    return float(np.median(arr))


def _pctl(arr, q: float) -> float:
    import numpy as np
    return float(np.percentile(arr, q))
