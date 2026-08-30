"""One-off land-atmosphere coupling checks behind D-255 and methodology
Known Limitation 9. Reproduces every ERA5 number cited in those two places.

WHY THIS IS COMMITTED. Both documents quote figures ("18th driest of 35",
"2 to 4% of summer heat variance") that were computed on 2026-08-30 in a
session scratchpad. A number in a permanent document whose derivation
lives nowhere is unverifiable by the next reader, so the script lives here
even though it is a one-off, following scripts/cwwa_sensitivity.py.

TWO QUESTIONS, BOTH ANSWERED NEGATIVELY, WHICH IS THE POINT.

1. EUROPE. Does a spring soil-moisture deficit precondition summer heat?
   The literature says the deficit usually leads the heat by 1-6 months.
   Measured over 1991-2025, the same summer explains 27-38% of Jun-Jul
   temperature everywhere, against 2-13% for the preceding spring. The
   coupling is overwhelmingly contemporaneous.

   On the published north-south asymmetry (soil moisture as precursor in
   the south, consequence in the north) the result is PARTIAL. Italy has
   both the strongest precursor (-0.36) and the weakest contemporaneous
   coupling (-0.52) of the four, which is the predicted direction. Iberia
   does not follow: at -0.21 it looks like the UK. So the asymmetry is
   visible in one southern box and not the other, which is weaker than
   the literature and not a refutation of it.

   An earlier version of this test reported Iberia and Italy wrongly
   because it area-averaged temperature from a box whose southern edge
   was 42N, which does not cover either region; xarray sliced it silently
   instead of raising. Both variables are now fetched over one area,
   which is the reason this script exists rather than a notebook.

2. AMAZON. Is the southern Amazon's record-quiet 2026 fire season
   explained by a full water table? No. Wet-season recharge ranked 18th
   driest of 35, i.e. middling, and 2025 paired the 3rd driest recharge
   on record with the lowest fire year on record, which the mechanism
   predicts backwards. The northern Amazon result is the opposite and
   holds hard: driest July in 36 years, third-driest soil.

Requires ~/.cdsapirc. Downloads roughly 80 MB to CACHE on first run and
is instant afterwards. Nothing here touches .fetch_cache/ or any
channel's data; the production pipeline cannot be affected by running it.

    .venv/bin/python scripts/land_coupling_check.py
"""

import calendar
import glob
import os
import tempfile
import zipfile

import numpy as np

CACHE = os.path.join(tempfile.gettempdir(), "tls_land_coupling")
CLIM = range(1991, 2026)

# name -> (lat_south, lat_north, lon_west, lon_east)
EUROPE = {
    "UK":     (50.0, 58.5, -6.0, 1.8),
    "France": (42.5, 51.0, -4.5, 8.0),
    "Iberia": (36.0, 43.5, -9.0, 2.5),
    "Italy":  (37.0, 46.0, 7.0, 18.0),
}
AMAZON = {
    "S. Amazon (5-15S)":   (-15.0, -5.0, -70.0, -50.0),
    "N. Amazon / Roraima": (0.0, 5.0, -64.0, -58.0),
}


def fetch(name, variables, area):
    """One CDS monthly-means request, cached on disk by name."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{name}.nc")
    if not os.path.exists(path):
        import cdsapi
        cdsapi.Client(quiet=True, progress=False).retrieve(
            "reanalysis-era5-single-levels-monthly-means",
            {
                "product_type": ["monthly_averaged_reanalysis"],
                "variable": variables,
                "year": [str(y) for y in range(1991, 2027)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "time": ["00:00"],
                "data_format": "netcdf",
                "download_format": "unarchived",
                "area": list(area),
            },
            path,
        )
    return path


def open_vars(path):
    """CDS returns a bare netCDF or a zip of one file per step type."""
    import xarray as xr
    out = {}
    if zipfile.is_zipfile(path):
        d = path + ".x"
        if not os.path.isdir(d):
            with zipfile.ZipFile(path) as z:
                z.extractall(d)
        members = sorted(glob.glob(os.path.join(d, "*.nc")))
    else:
        members = [path]
    for m in members:
        ds = xr.open_dataset(m)
        for v in ds.data_vars:
            out[v] = ds[v]
    return out


def monthly(da, box):
    """Area-mean the box, return {year: {month: value}}."""
    s, n, w, e = box
    x = da.sel(latitude=slice(n, s), longitude=slice(w, e)).mean(
        dim=["latitude", "longitude"])
    yy = x.valid_time.dt.year.values
    mm = x.valid_time.dt.month.values
    out = {}
    for y, m, v in zip(yy, mm, x.values):
        out.setdefault(int(y), {})[int(m)] = float(v)
    return out


def europe():
    path = fetch("europe",
                 ["2m_temperature", "volumetric_soil_water_layer_3"],
                 [60, -10, 35, 24])
    V = open_vars(path)
    print("EUROPE. Spring soil moisture as a precursor to summer heat.")
    print("Negative r = drier spring soil, hotter following summer.\n")
    print(f"  {'region':10}{'spring -> summer':>18}{'same summer':>14}"
          f"{'2026 spring rank':>19}")
    for name, box in EUROPE.items():
        T = monthly(V["t2m"], box)
        S = monthly(V["swvl3"], box)
        yrs = list(CLIM)
        jj = np.array([np.mean([T[y][m] for m in (6, 7)]) for y in yrs])
        ante = np.array([np.mean([S[y][m] for m in (3, 4, 5)]) for y in yrs])
        same = np.array([np.mean([S[y][m] for m in (6, 7)]) for y in yrs])
        a26 = np.mean([S[2026][m] for m in (3, 4, 5)])
        rank = sorted(list(ante) + [a26]).index(a26) + 1
        print(f"  {name:10}{np.corrcoef(ante, jj)[0, 1]:+18.2f}"
              f"{np.corrcoef(same, jj)[0, 1]:+14.2f}"
              f"{rank:>13} of {len(ante) + 1}")
    print("\n  Spring explains 2-13% of the variance; the same summer 27-38%.")
    print("  Asymmetry is PARTIAL: Italy shows it, Iberia looks like the UK.\n")


def amazon():
    path = fetch("amazon",
                 ["volumetric_soil_water_layer_3", "total_precipitation"],
                 [6, -76, -16, -44])
    V = open_vars(path)
    print("AMAZON. Preceding wet-season recharge, the variable Chen et al.")
    print("2011/2017 identify as governing dry-season fire.\n")
    for name, box in AMAZON.items():
        S = monthly(V["swvl3"], box)
        P = monthly(V["tp"], box)
        rech = {y: float(np.mean([S[y - 1][12]] + [S[y][m] for m in range(1, 6)]))
                for y in range(1992, 2027)}
        order = sorted(rech.values())
        print(f"  === {name} ===")
        print(f"    {'year':6}{'recharge':>10}{'rank':>10}   note")
        notes = {2016: "big burn year", 2024: "record burn year",
                 2025: "LOWEST burn year on record", 2026: "current"}
        for y in (1998, 2016, 2024, 2025, 2026):
            print(f"    {y:<6}{rech[y]:10.4f}"
                  f"{order.index(rech[y]) + 1:>6} of {len(order)}   {notes.get(y, '')}")
        jul = {y: S[y][7] for y in S if 7 in S[y]}
        rain = {y: P[y][7] * 1000 * 31 for y in P if 7 in P[y]}
        print(f"    July 2026 soil moisture rank "
              f"{sorted(jul.values()).index(jul[2026]) + 1} of {len(jul)} driest")
        print(f"    July 2026 rainfall rank "
              f"{sorted(rain.values()).index(rain[2026]) + 1} of {len(rain)} driest\n")
    print("  South: middling recharge, and 2025 is a clean counterexample.")
    print("  North: driest July in the record. The two halves disagree.\n")


if __name__ == "__main__":
    europe()
    amazon()
