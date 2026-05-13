"""
One-off sensitivity check: CWWA at 10 deg N - 10 deg S vs the production
5 deg N - 5 deg S band.

Per an external reviewer's note that some of the most anomalous westerlies
sit slightly off-equator (7N-7S or 10N-10S), this script computes CWWA at
a wider latitude band for 1997, 2015, 2023, 2025 (analogs) and the current
2026 develop year, then compares against the narrow-band values already
cached by the production fetcher.

Does NOT modify the production fetcher. Cache files use a _10NS suffix so
nothing in .fetch_cache/ that the production pipeline relies on is touched.

Run from the repo root:

    .venv/bin/python scripts/cwwa_sensitivity.py

Total cold-cache CDS time: roughly 20-30 minutes. Subsequent runs are seconds
because intermediate results are cached.

Output: a table at stdout comparing wider-band vs narrow-band CWWA at three
calendar dates (April 22, May 1, end-of-Aug full-window total) for each
analog year and 2026.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".fetch_cache"

DATASET = "reanalysis-era5-pressure-levels"
REGION_WIDE = [10, 130, -10, 210]   # N, W, S, E in 0-360 longitude (10N-10S)
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
            "area": REGION_WIDE,
        },
        path,
    )


def _area_mean_u(ds: xr.Dataset) -> xr.DataArray:
    u = ds["u"]
    if "pressure_level" in u.dims:
        u = u.squeeze("pressure_level", drop=True)
    return u.mean(dim=["latitude", "longitude"])


def _mmdd(times: xr.DataArray) -> np.ndarray:
    return (times.dt.month.values * 100 + times.dt.day.values).astype("int32")


def _clim_path_wide() -> str:
    return str(CACHE_DIR / f"era5_cwwa_clim_{CLIM_YEARS[0]}-{CLIM_YEARS[-1]}_130E-150W_10NS_MarAug.nc")


def _analog_path_wide(year: int) -> str:
    return str(CACHE_DIR / f"era5_cwwa_analog_{year}_130E-150W_10NS.json")


def build_or_load_climatology_wide() -> xr.DataArray:
    path = _clim_path_wide()
    if os.path.exists(path):
        return xr.open_dataarray(path)
    chunks = []
    for month in CLIM_MONTHS:
        print(f"  climatology chunk: 30y x month {month}...", flush=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
        _retrieve([str(y) for y in CLIM_YEARS], [month], ALL_DAYS, tmp)
        ds = xr.open_dataset(tmp)
        u_box = _area_mean_u(ds)
        time_dim = "valid_time" if "valid_time" in u_box.coords else "time"
        u_box = u_box.assign_coords(mmdd=(time_dim, _mmdd(u_box[time_dim])))
        chunk = u_box.groupby("mmdd").mean(dim=time_dim)
        chunks.append(chunk)
        try:
            os.remove(tmp)
        except OSError:
            pass
    clim = xr.concat(chunks, dim="mmdd").sortby("mmdd")
    clim.name = "u_clim"
    clim.to_netcdf(path)
    return xr.open_dataarray(path)


def cwwa_series_for_year_wide(year: int, end_month: int, clim: xr.DataArray) -> list:
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


def build_or_load_analog_wide(year: int, clim: xr.DataArray) -> list:
    path = _analog_path_wide(year)
    if os.path.exists(path):
        return [tuple(pt) for pt in json.loads(open(path).read())]
    print(f"  analog year {year} (Mar-Aug)...", flush=True)
    series = cwwa_series_for_year_wide(year, 8, clim)
    with open(path, "w") as f:
        json.dump([list(pt) for pt in series], f)
    return series


def load_narrow_series(year: int) -> list:
    """Read the production narrow-band cache."""
    path = CACHE_DIR / f"era5_cwwa_analog_{year}_130E-150W.json"
    if not path.exists():
        return []
    return [tuple(pt) for pt in json.loads(path.read_text())]


def value_at(series: list, target_iso: str) -> float | None:
    """CWWA value at the given target date (or the closest preceding date)."""
    if not series:
        return None
    target_md = target_iso[5:]   # "MM-DD"
    last_v = None
    for d_iso, v in series:
        if d_iso[5:] == target_md:
            return float(v)
        if d_iso <= target_iso:
            last_v = float(v)
    return last_v


def main() -> None:
    print("=== CWWA sensitivity: 10N-10S (wider) vs 5N-5S (production) ===", flush=True)
    print(f"Cache dir: {CACHE_DIR}", flush=True)
    print(flush=True)

    print("[1/3] Wider-band climatology (1991-2020, Mar-Aug, 10N-10S)...", flush=True)
    clim = build_or_load_climatology_wide()
    print(f"  climatology has {clim.sizes.get('mmdd')} calendar days", flush=True)
    print(flush=True)

    print("[2/3] Analog years at wider band...", flush=True)
    analogs_wide = {}
    for y in ANALOG_YEARS:
        analogs_wide[y] = build_or_load_analog_wide(y, clim)
    print(flush=True)

    print("[3/3] 2026 observation at wider band...", flush=True)
    today = date.today()
    end = today - timedelta(days=5)
    current_wide = cwwa_series_for_year_wide(end.year, end.month, clim)
    print(f"  2026 series: {len(current_wide)} days, latest = {current_wide[-1][0]}", flush=True)
    print(flush=True)

    print("=== Comparison ===", flush=True)
    for target_label, target_iso in [
        ("Apr 22 (v1.2 internal ref)", "2026-04-22"),
        ("May 1 (recent)", "2026-05-01"),
        ("End-of-Aug (full window)", "2026-08-31"),
    ]:
        print(f"\n[{target_label}, comparing at calendar date {target_iso[5:]}]", flush=True)
        print(f"{'Year':<6} {'Wide':>8} {'Narrow':>8} {'Diff':>8} {'Pct':>8}", flush=True)
        for y in ANALOG_YEARS:
            wide = value_at(analogs_wide[y], f"{y}{target_iso[4:]}")
            narrow = value_at(load_narrow_series(y), f"{y}{target_iso[4:]}")
            if wide is None or narrow is None:
                print(f"{y:<6} {('-' if wide is None else f'{wide:>.0f}'):>8} "
                      f"{('-' if narrow is None else f'{narrow:>.0f}'):>8} - -", flush=True)
                continue
            diff = wide - narrow
            pct = (100.0 * diff / narrow) if narrow else float("inf")
            print(f"{y:<6} {wide:>8.0f} {narrow:>8.0f} {diff:>+8.0f} {pct:>+7.0f}%", flush=True)
        # 2026: end-of-Aug not available (we're in May); only first two dates make sense
        if target_iso[5:] in ("04-22", "05-01"):
            wide_2026 = value_at(current_wide, target_iso)
            # production narrow 2026 series isn't cached separately; read it from the
            # production fetcher's last-good result if available
            narrow_2026_cache = CACHE_DIR / "era5_wwe_last_good.json"
            narrow_2026 = None
            if narrow_2026_cache.exists():
                try:
                    payload = json.loads(narrow_2026_cache.read_text()).get("payload", {})
                    for d_iso, v in payload.get("cwwa_series", []):
                        if d_iso[5:] == target_iso[5:]:
                            narrow_2026 = float(v)
                            break
                except (OSError, ValueError, KeyError):
                    pass
            if wide_2026 is not None and narrow_2026 is not None:
                diff = wide_2026 - narrow_2026
                pct = (100.0 * diff / narrow_2026) if narrow_2026 else float("inf")
                print(f"{'2026':<6} {wide_2026:>8.0f} {narrow_2026:>8.0f} "
                      f"{diff:>+8.0f} {pct:>+7.0f}%", flush=True)
            elif wide_2026 is not None:
                print(f"{'2026':<6} {wide_2026:>8.0f} {'-':>8} - -", flush=True)

    print("\n=== Ranking check (2026 vs analogs at May 1) ===", flush=True)
    for label, getter in [
        ("Narrow (5N-5S)",
         lambda y: value_at(load_narrow_series(y), f"{y}-05-01")),
        ("Wide (10N-10S)",
         lambda y: value_at(analogs_wide[y], f"{y}-05-01")),
    ]:
        ranked = []
        for y in ANALOG_YEARS:
            v = getter(y)
            if v is not None:
                ranked.append((y, v))
        ranked.sort(key=lambda x: x[1], reverse=True)
        print(f"  {label}: " + ", ".join(f"{y}({v:.0f})" for y, v in ranked), flush=True)

    wide_2026_may1 = value_at(current_wide, "2026-05-01")
    if wide_2026_may1 is not None:
        analog_values_wide = {y: value_at(analogs_wide[y], f"{y}-05-01")
                              for y in ANALOG_YEARS}
        analog_values_wide = {y: v for y, v in analog_values_wide.items() if v is not None}
        if analog_values_wide:
            closest = min(analog_values_wide.items(),
                          key=lambda kv: abs(kv[1] - wide_2026_may1))
            print(f"  Wide-band: 2026 ({wide_2026_may1:.0f}) tracks closest to "
                  f"{closest[0]} ({closest[1]:.0f}).", flush=True)


if __name__ == "__main__":
    main()
