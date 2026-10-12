"""Europe autumn flood ingredients, autumn 2026: where they stand against
their own history. Not a forecast. Each ingredient is ranked against the
same calendar window in earlier years, and the seasonal outlooks are quoted
as the agencies issue them, one centre at a time, never averaged.

Ingredients:
  1. Sea surface temperature, Mediterranean and nearby seas, September and
     1-10 October (ERA5; hourly at 00 UTC for October, since a partial-month
     window must be compared with the same days in earlier years, not with a
     full-month mean that the seasonal cooling would bias).
  2. Topsoil moisture, September (ERA5 volumetric soil water, layer 1, 0-7 cm).
     Wet ground turns more of the next rain into runoff.
  3. Seasonal precipitation outlooks, 1 October 2026 runs, Oct/Nov/Dec
     (C3S post-processed anomalies, per centre).

Run:  .venv/bin/python floods/europe_ingredients.py [fetch|report]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".era5_cache")
EUROPE = [72, -25, 28, 45]           # N, W, S, E
MED = [46, -6, 30, 37]
YEARS = [str(y) for y in range(1991, 2027)]
CENTRES = [("ecmwf", "51"), ("meteo_france", "9"), ("dwd", "22"), ("cmcc", "35"),
           ("ukmo", "604"), ("ncep", "2")]

F_MON = os.path.join(CACHE, "eu_sst_swvl1_augsep_1991_2026.nc")
F_OCT = os.path.join(CACHE, "med_sst_oct01_10_1991_2026.nc")
F_MON_OLD = os.path.join(CACHE, "med_sst_sep_1940_1990.nc")


def f_seas(c, s):
    return os.path.join(CACHE, f"seas_tp_anom_{c}_{s}_2026_10.nc")


def fetch():
    import cdsapi
    os.makedirs(CACHE, exist_ok=True)
    c = cdsapi.Client(quiet=True, progress=False)
    if not os.path.exists(F_MON):
        print("fetching ERA5 monthly SST + soil moisture", flush=True)
        c.retrieve("reanalysis-era5-single-levels-monthly-means", {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["sea_surface_temperature", "volumetric_soil_water_layer_1"],
            "year": YEARS, "month": ["08", "09"], "time": ["00:00"],
            "area": EUROPE, "grid": [0.5, 0.5],
            "data_format": "netcdf", "download_format": "unarchived"}, F_MON)
    if not os.path.exists(F_MON_OLD):
        print("fetching ERA5 monthly September SST 1940-1990", flush=True)
        c.retrieve("reanalysis-era5-single-levels-monthly-means", {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["sea_surface_temperature"],
            "year": [str(y) for y in range(1940, 1991)], "month": ["09"], "time": ["00:00"],
            "area": MED, "grid": [0.5, 0.5],
            "data_format": "netcdf", "download_format": "unarchived"}, F_MON_OLD)
    if not os.path.exists(F_OCT):
        print("fetching ERA5 SST 1-10 October, 00 UTC", flush=True)
        c.retrieve("reanalysis-era5-single-levels", {
            "product_type": ["reanalysis"], "variable": ["sea_surface_temperature"],
            "year": YEARS, "month": ["10"], "day": [f"{d:02d}" for d in range(1, 11)],
            "time": ["00:00"], "area": MED, "grid": [0.5, 0.5],
            "data_format": "netcdf", "download_format": "unarchived"}, F_OCT)
    for centre, system in CENTRES:
        f = f_seas(centre, system)
        if os.path.exists(f):
            continue
        print(f"fetching seasonal precip anomaly {centre} system {system}", flush=True)
        try:
            c.retrieve("seasonal-postprocessed-single-levels", {
                "originating_centre": centre, "system": system,
                "variable": ["total_precipitation_anomalous_rate_of_accumulation"],
                "product_type": ["monthly_mean"], "year": ["2026"], "month": ["10"],
                "leadtime_month": ["1", "2", "3"], "area": EUROPE,
                "data_format": "netcdf"}, f)
        except Exception as e:                      # one centre failing must not hide the others
            print(f"  FAILED {centre} {system}: {str(e).splitlines()[0][:200]}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "fetch":
        fetch()


SEA_BOXES = {                       # (S, N, W, E), sea cells only
    "Western Mediterranean (Alboran, Balearic, Gulf of Lion)": (35, 44.5, -5.5, 9.5),
    "Central Mediterranean (Tyrrhenian, Ionian, Adriatic)": (35, 46, 9.5, 20.5),
    "Eastern Mediterranean (Aegean, Levantine)": (30, 41, 20.5, 37),
}
LAND_BOXES = {                      # land cells only
    "Eastern Spain": (37, 42.5, -2.5, 3.5),
    "Southern France": (42.5, 45.5, 1, 8),
    "Northern Italy": (44, 47, 7, 14),
    "Southern Italy": (37.5, 42, 13, 18.5),
    "Western Balkans": (40, 46, 14, 21),
    "Greece": (36.5, 41.5, 20, 26.5),
    "UK and Ireland": (50, 58.5, -10, 2),
    "Central Europe": (47, 53, 6, 20),
}


def _load(path, var):
    import netCDF4
    import datetime as dt
    d = netCDF4.Dataset(path)
    a = d.variables[var][:]
    t = d.variables["valid_time"][:]
    lat = np.array(d.variables["latitude"][:]); lon = np.array(d.variables["longitude"][:])
    d.close()
    when = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x)) for x in t]
    return a, when, lat, lon


def _box_mean(field, lat, lon, box, cells):
    s, n, w, e = box
    m = cells & ((lat >= s) & (lat <= n))[:, None] & ((lon >= w) & (lon <= e))[None, :]
    wt = np.cos(np.radians(lat))[:, None] * m
    return float((np.asarray(field) * wt).sum() / wt.sum()), int(m.sum())


def _rank(series, year=2026):
    v = series[year]
    return 1 + sum(1 for y, x in series.items() if x > v), len(series)


def report():
    out = {"note": "ranks are 1 = highest of the years listed; anomalies vs 1991-2020"}
    sst, when, lat, lon = _load(F_MON, "sst")
    sea = ~np.ma.getmaskarray(sst).any(axis=0)
    swv, _, _, _ = _load(F_MON, "swvl1")
    land = ~sea
    sept = {w.year: k for k, w in enumerate(when) if w.month == 9}
    print("SEA SURFACE TEMPERATURE, September (ERA5 monthly), since 1991")
    for name, box in SEA_BOXES.items():
        ser = {y: _box_mean(sst[k].filled(0), lat, lon, box, sea)[0] - 273.15 for y, k in sept.items()}
        clim = np.mean([ser[y] for y in range(1991, 2021)])
        r, n = _rank(ser)
        top = sorted(ser, key=lambda y: -ser[y])[:4]
        print(f"  {name:<56} {ser[2026]:.2f} C, {ser[2026]-clim:+.2f} vs 1991-2020, rank {r} of {n}; warmest: {top}")
        out.setdefault("sst_sept", {})[name] = {"c": ser[2026], "anom": ser[2026] - clim, "rank": [r, n],
                                                 "warmest": top}

    o, ow, olat, olon = _load(F_OCT, "sst")
    days26 = sorted({w.day for w in ow if w.year == 2026})
    osea = ~np.ma.getmaskarray(o).any(axis=0)
    print(f"\nSEA SURFACE TEMPERATURE, 1-{days26[-1]} October (ERA5 00 UTC), same days every year since 1991")
    for name, box in SEA_BOXES.items():
        ser = {}
        for y in sorted({w.year for w in ow}):
            ks = [k for k, w in enumerate(ow) if w.year == y and w.day in days26]
            if len(ks) != len(days26):
                print(f"  INCOMPLETE {y}: {len(ks)} of {len(days26)} days")
                continue
            ser[y] = np.mean([_box_mean(o[k].filled(0), olat, olon, box, osea)[0] for k in ks]) - 273.15
        clim = np.mean([ser[y] for y in range(1991, 2021)])
        r, n = _rank(ser)
        top = sorted(ser, key=lambda y: -ser[y])[:4]
        print(f"  {name:<56} {ser[2026]:.2f} C, {ser[2026]-clim:+.2f} vs 1991-2020, rank {r} of {n}; warmest: {top}")
        out.setdefault("sst_oct", {})[name] = {"c": ser[2026], "anom": ser[2026] - clim, "rank": [r, n],
                                                "days": f"1-{days26[-1]} Oct", "warmest": top}

    print("\nTOPSOIL MOISTURE, September (ERA5 layer 1, 0-7 cm), since 1991; rank 1 = wettest")
    for name, box in LAND_BOXES.items():
        ser = {y: _box_mean(swv[k], lat, lon, box, land)[0] for y, k in sept.items()}
        clim = np.mean([ser[y] for y in range(1991, 2021)])
        r, n = _rank(ser)
        print(f"  {name:<20} {ser[2026]:.3f} m3/m3, {100*(ser[2026]/clim-1):+.0f}% vs 1991-2020, rank {r} of {n}")
        out.setdefault("soil_sept", {})[name] = {"v": ser[2026], "anom_pct": 100 * (ser[2026] / clim - 1),
                                                  "rank": [r, n]}

    print("\nSEASONAL PRECIPITATION OUTLOOKS, 1 Oct 2026 runs, ensemble-mean anomaly, mm/day")
    for centre, system in CENTRES:
        f = f_seas(centre, system)
        if not os.path.exists(f):
            print(f"  {centre}: not retrieved")
            continue
        out.setdefault("seasonal", {})[centre] = _seasonal(f, centre)
    json.dump(out, open(os.path.join(HERE, "data", "europe_ingredients_2026-10.json"), "w"), indent=1)


def _seasonal(path, centre):
    import netCDF4
    d = netCDF4.Dataset(path)
    v = [k for k in d.variables if "tpara" in k or "tp" in k.lower()][0]
    a = np.array(d.variables[v][:]) * 86400 * 1000      # m/s to mm/day
    lat = np.array(d.variables["latitude"][:]); lon = np.array(d.variables["longitude"][:])
    dims = d.variables[v].dimensions
    d.close()
    mem = dims.index("number") if "number" in dims else None
    if mem is not None:
        a = a.mean(axis=mem)
    a = a.reshape(-1, len(lat), len(lon))[-3:]          # lead months 1..3
    allc = np.ones((len(lat), len(lon)), bool)
    res = {}
    for name, box in LAND_BOXES.items():
        vals = [_box_mean(a[k], lat, lon, box, allc)[0] for k in range(3)]
        res[name] = vals
    print(f"  {centre:<13} " + "  ".join(f"{n.split()[0][:8]:>8}" for n in LAND_BOXES))
    for k, mname in enumerate(("Oct", "Nov", "Dec")):
        print(f"    {mname:<11} " + "  ".join(f"{res[n][k]:+8.2f}" for n in LAND_BOXES))
    return res


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "report":
    report()
