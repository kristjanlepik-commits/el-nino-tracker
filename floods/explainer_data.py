"""Data for the "how a flood is made" explainer (Kristjan's brief, 15 Oct 2026),
so that every scene runs on measured ERA5 fields rather than illustration.

  heat     September 2026 anomaly vs 1991-2020: sea surface temperature and
           2 m air temperature over land, Europe and the Mediterranean.
  evap     September evaporation over the Mediterranean, 1991-2026, as a
           basin mean and a % anomaly map: "it starts from the sea".
  coldpool 500 hPa temperature at 12 UTC on 3 Oct 2026 (Barcelona's record
           day) against the same hour and day 1991-2020, with that day's
           sea surface temperature: cold air aloft over warm sea.

Run:  .venv/bin/python floods/explainer_data.py fetch
      .venv/bin/python floods/explainer_data.py build
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".era5_cache")
EUROPE = [72, -25, 28, 45]
MED = [46, -6, 30, 37]
BASE = [str(y) for y in range(1991, 2021)]
F_T2M = os.path.join(CACHE, "eu_t2m_sep_1991_2026.nc")
F_EVAP = os.path.join(CACHE, "med_evap_sep_1991_2026.nc")
F_T500 = os.path.join(CACHE, "t500_1003_12utc_1991_2020_2026.nc")
F_SST3 = os.path.join(CACHE, "sst_20261003_12utc.nc")


def fetch():
    import cdsapi
    c = cdsapi.Client(quiet=True, progress=False)
    mon = "reanalysis-era5-single-levels-monthly-means"
    jobs = [
        (F_T2M, mon, {"product_type": ["monthly_averaged_reanalysis"], "variable": ["2m_temperature"],
                      "year": BASE + [str(y) for y in range(2021, 2027)], "month": ["09"], "time": ["00:00"],
                      "area": EUROPE, "grid": [0.5, 0.5]}),
        (F_EVAP, mon, {"product_type": ["monthly_averaged_reanalysis"], "variable": ["evaporation"],
                       "year": BASE + [str(y) for y in range(2021, 2027)], "month": ["09"], "time": ["00:00"],
                       "area": MED, "grid": [0.5, 0.5]}),
        (F_T500, "reanalysis-era5-pressure-levels",
         {"product_type": ["reanalysis"], "variable": ["temperature"], "pressure_level": ["500"],
          "year": BASE + ["2026"], "month": ["10"], "day": ["03"], "time": ["12:00"],
          "area": [50, -15, 30, 20], "grid": [0.5, 0.5]}),
        (F_SST3, "reanalysis-era5-single-levels",
         {"product_type": ["reanalysis"], "variable": ["sea_surface_temperature"],
          "year": ["2026"], "month": ["10"], "day": ["03"], "time": ["12:00"],
          "area": [50, -15, 30, 20], "grid": [0.5, 0.5]}),
    ]
    for f, ds, req in jobs:
        if os.path.exists(f):
            continue
        print("fetching", os.path.basename(f), flush=True)
        req.update({"data_format": "netcdf", "download_format": "unarchived"})
        c.retrieve(ds, req, f)


if __name__ == "__main__" and sys.argv[1:] == ["fetch"]:
    fetch()


def _nc(path, var):
    import netCDF4
    import datetime as dt
    d = netCDF4.Dataset(path)
    a = d.variables[var][:]
    t = d.variables["valid_time"][:]
    lat = np.array(d.variables["latitude"][:]); lon = np.array(d.variables["longitude"][:])
    d.close()
    yrs = [(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x))).year for x in t]
    return a, yrs, lat, lon


def _grid(a, nd=2):
    """2-D masked array to a list of rows, None where masked (land for SST, sea for land fields)."""
    m = np.ma.getmaskarray(a)
    v = np.round(np.ma.filled(a.astype(float), np.nan), nd)
    return [[None if (m[i, j] or not np.isfinite(v[i, j])) else float(v[i, j]) for j in range(v.shape[1])]
            for i in range(v.shape[0])]


def _anom(path, var, kelvin=False):
    a, yrs, lat, lon = _nc(path, var)
    base = np.ma.mean(np.ma.stack([a[k] for k, y in enumerate(yrs) if 1991 <= y <= 2020]), axis=0)
    now = a[yrs.index(2026)]
    return now, base, lat, lon


def build():
    out = {"_about": "Explainer data, FLO, ERA5 (2026 preliminary). Grids: rows north to south, "
                     "columns west to east, None where not applicable. Anomalies vs 1991-2020.",
           "bathtub": {"station": "Barcelona Fabra (AEMET 0200E)", "date": "2026-10-03", "mm": 159.1,
                       "litres_per_m2": 159.1, "claim": "wettest day in its complete record since 1978"}}
    # 1. heat: SST (sea) + t2m (land), September 2026 anomaly, Europe
    sst_f = os.path.join(CACHE, "eu_sst_swvl1_augsep_1991_2026.nc")
    import netCDF4
    import datetime as dt
    d = netCDF4.Dataset(sst_f); s = d.variables["sst"][:]; tt = d.variables["valid_time"][:]
    lat = np.array(d.variables["latitude"][:]); lon = np.array(d.variables["longitude"][:]); d.close()
    when = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x)) for x in tt]
    sep = {w.year: k for k, w in enumerate(when) if w.month == 9}
    sst_base = np.ma.mean(np.ma.stack([s[sep[y]] for y in range(1991, 2021)]), axis=0)
    sst_anom = s[sep[2026]] - sst_base
    t2m_now, t2m_base, lat2, lon2 = _anom(F_T2M, "t2m")
    assert np.allclose(lat, lat2) and np.allclose(lon, lon2), "SST and t2m grids differ"
    sea = ~np.ma.getmaskarray(s[sep[2026]])
    land_anom = np.ma.masked_where(sea, t2m_now - t2m_base)
    out["heat"] = {"lat": [float(x) for x in lat], "lon": [float(x) for x in lon],
                   "sst_anom_c": _grid(sst_anom), "land_t2m_anom_c": _grid(land_anom),
                   "headline": "Western and central Mediterranean: warmest September in a record going back "
                               "to 1940, +2.4 and +2.8 C (floods/data/europe_ingredients_2026-10.json, sst_sept)"}
    # 2. evaporation, Mediterranean sea cells, September
    if os.path.exists(F_EVAP):
        e, yrs, la, lo = _nc(F_EVAP, "e")
        e = -e * 1000.0                                   # ERA5: m/day, negative = evaporation; to mm/day upward
        w = np.cos(np.radians(la))[:, None] * np.ones(e.shape[1:])
        seam = ~np.ma.getmaskarray(e).any(axis=0) & (np.ma.filled(e, 0).mean(axis=0) > 0)
        basin = {y: float((np.ma.filled(e[k], 0) * w * seam).sum() / (w * seam).sum()) for k, y in enumerate(yrs)}
        clim = np.mean([basin[y] for y in range(1991, 2021)])
        rank = 1 + sum(1 for y, v in basin.items() if v > basin[2026])
        base = np.ma.mean(np.ma.stack([e[k] for k, y in enumerate(yrs) if 1991 <= y <= 2020]), axis=0)
        pct = np.ma.masked_where(~seam, 100 * (e[yrs.index(2026)] / base - 1))
        out["evaporation"] = {"unit": "mm of water per day, Mediterranean sea cells, September",
                              "basin_mean_2026": round(basin[2026], 2), "basin_mean_normal": round(clim, 2),
                              "pct_vs_normal": round(100 * (basin[2026] / clim - 1), 1),
                              "rank_since_1991": [rank, len(basin)],
                              "by_year": {str(y): round(v, 3) for y, v in sorted(basin.items())},
                              "lat": [float(x) for x in la], "lon": [float(x) for x in lo], "pct_map": _grid(pct, 1)}
    # 3. cold pool over warm sea, 3 Oct 2026 12 UTC
    if os.path.exists(F_T500) and os.path.exists(F_SST3):
        t5, yrs, la, lo = _nc(F_T500, "t")
        t5 = t5.reshape(len(yrs), len(la), len(lo)) if t5.ndim == 4 else t5
        base = np.ma.mean(np.ma.stack([t5[k] for k, y in enumerate(yrs) if 1991 <= y <= 2020]), axis=0)
        now = t5[yrs.index(2026)]
        s3, _, la3, lo3 = _nc(F_SST3, "sst")
        out["coldpool"] = {"when": "2026-10-03 12 UTC", "lat": [float(x) for x in la], "lon": [float(x) for x in lo],
                           "t500_c": _grid(now - 273.15, 1), "t500_anom_c": _grid(now - base, 1),
                           "sst_c": _grid(s3[0] - 273.15, 1),
                           "coldest_t500_c": round(float(now.min()) - 273.15, 1),
                           "coldest_t500_anom_c": round(float((now - base).min()), 1)}
    out.pop("coldpool", None)   # superseded by "pump": no cold pool sat over Barcelona at 12 UTC on 3 Oct
    # 4. the sponge, GLOBAL: every September 1940-2026 and the Sept 2026 map (Kristjan: show it globally)
    import glob
    F, YR = [], []
    for f in sorted(glob.glob(os.path.join(CACHE, "tcwv_*.nc"))):
        a, yrs, gla, glo = _nc(f, "tcwv")
        d2 = netCDF4.Dataset(f); tt2 = d2.variables["valid_time"][:]; d2.close()
        for k in range(len(tt2)):
            w = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(tt2[k]))
            if w.month == 9:
                F.append(a[k]); YR.append(w.year)
    F = np.stack(F); wt = np.cos(np.radians(gla))[:, None] * np.ones(F.shape[1:])
    gm = {y: float((F[k] * wt).sum() / wt.sum()) for k, y in enumerate(YR)}
    cl = np.mean([gm[y] for y in range(1991, 2021)])
    base = np.mean([F[k] for k, y in enumerate(YR) if 1991 <= y <= 2020], axis=0)
    pct = 100 * (F[YR.index(2026)] / base - 1)
    order = np.argsort(np.where(glo > 180, glo - 360, glo))
    out["sponge_global"] = {"unit": "% vs 1991-2020 September, global total column water vapour, area-weighted",
                            "by_year_pct": {str(y): round(100 * (gm[y] / cl - 1), 2) for y in sorted(gm)},
                            "rank_2026": [1 + sum(1 for v in gm.values() if v > gm[2026]), len(gm)],
                            "physics": "about 7% more water vapour per degree C of warming (Clausius-Clapeyron; IPCC AR6 WG1 ch. 8)",
                            "map_lat": [float(x) for x in gla], "map_lon": [float(x) for x in np.sort(np.where(glo > 180, glo - 360, glo))],
                            "map_pct_2026": _grid(np.ma.masked_invalid(pct[:, order]), 1)}
    # 5. the pump: storm 1, 27 Sep to 4 Oct 12 UTC, 500 hPa temperature anomaly; 30 Sep to 3 Oct 850 hPa winds
    f5 = os.path.join(CACHE, "t500_0927_1004_12utc_1991_2020_2026.nc")
    f8 = os.path.join(CACHE, "storm1_pump_2026.nc")
    if os.path.exists(f5) and os.path.exists(f8):
        d5 = netCDF4.Dataset(f5); t5 = d5.variables["t"][:]; tt5 = d5.variables["valid_time"][:]
        l5a = np.array(d5.variables["latitude"][:]); l5o = np.array(d5.variables["longitude"][:]); d5.close()
        t5 = t5.reshape(len(tt5), len(l5a), len(l5o))
        W5 = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x)) for x in tt5]
        valid = [(9, d) for d in (27, 28, 29, 30)] + [(10, d) for d in (1, 2, 3, 4)]
        frames = []
        for (m_, d_) in valid:
            for h in (0, 12):
                k26 = [k for k, w in enumerate(W5) if w.year == 2026 and (w.month, w.day, w.hour) == (m_, d_, h)]
                kb = [k for k, w in enumerate(W5) if 1991 <= w.year <= 2020 and (w.month, w.day, w.hour) == (m_, d_, h)]
                if not k26 or len(kb) < 25:
                    continue
                an = t5[k26[0]] - np.mean([t5[k] for k in kb], axis=0)
                frames.append({"time": f"2026-{m_:02d}-{d_:02d}T{h:02d}:00Z", "t500_anom_c": _grid(an, 1),
                               "coldest_anom_c": round(float(an.min()), 1)})
        d8 = netCDF4.Dataset(f8); pl = [float(x) for x in d8.variables["pressure_level"][:]]
        i8 = pl.index(850.0); tt8 = d8.variables["valid_time"][:]
        u8 = d8.variables["u"][:, i8]; v8 = d8.variables["v"][:, i8]; q8 = d8.variables["q"][:, i8]
        l8a = np.array(d8.variables["latitude"][:]); l8o = np.array(d8.variables["longitude"][:]); d8.close()
        W8 = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x)) for x in tt8]
        winds = [{"time": w.strftime("%Y-%m-%dT%H:00Z"), "u850_ms": _grid(np.ma.masked_invalid(u8[k][::2, ::2]), 1),
                  "v850_ms": _grid(np.ma.masked_invalid(v8[k][::2, ::2]), 1),
                  "q850_gkg": _grid(np.ma.masked_invalid(1000 * q8[k][::2, ::2]), 1)}
                 for k, w in enumerate(W8) if (w.month, w.day) in valid]
        out["pump"] = {"story": "A cold pool from the Atlantic (500 hPa, about 5 km up: -25.9 C on 30 Sep 12 UTC "
                                "near 46N 15W, 11.7 C colder than normal) pushed east; by 3 Oct its centre was over "
                                "NW France and the 850 hPa wind off Barcelona blew from the south-east (123 deg) at "
                                "10.4 m/s, onshore from the record-warm sea. Not claimed: unusually cold air directly "
                                "over Barcelona (it was not).",
                       "t500_frames": {"lat": [float(x) for x in l5a], "lon": [float(x) for x in l5o],
                                       "baseline": "same hour and day, 1991-2020", "frames": frames},
                       "winds_850": {"lat": [float(x) for x in l8a[::2]], "lon": [float(x) for x in l8o[::2]],
                                     "resolution_deg": 1.0, "frames": winds}}
    # 7. ground: topsoil 8-10 Oct by named area, rank of 36 years (1 = wettest)
    fs = os.path.join(CACHE, "spain_swvl1_oct_1991_2026.nc")
    if os.path.exists(fs):
        ds = netCDF4.Dataset(fs); sw = ds.variables["swvl1"][:]; tts = ds.variables["valid_time"][:]
        sla = np.array(ds.variables["latitude"][:]); slo = np.array(ds.variables["longitude"][:]); ds.close()
        WS = [dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(x)) for x in tts]
        areas = {"Barcelona, Maresme, Girona coast": (41.2, 42.4, 1.9, 3.3), "Southern Catalonia, Ebro delta": (40.5, 41.2, 0.3, 1.2),
                 "Castellon coast": (39.7, 40.5, -0.4, 0.4), "Valencia, central coast": (38.9, 39.7, -0.6, 0.0),
                 "La Safor, Marina Alta": (38.6, 39.1, -0.3, 0.2), "Alicante, Vega Baja": (37.9, 38.6, -1.0, -0.3),
                 "Murcia coast": (37.4, 38.0, -1.6, -0.6), "Malaga, Costa del Sol": (36.4, 36.9, -5.0, -4.0),
                 "Ibiza": (38.8, 39.2, 1.1, 1.6), "Mallorca": (39.3, 40.0, 2.3, 3.5)}
        soil = {}
        for nm, (s_, n_, w_, e_) in areas.items():
            m = ((sla >= s_) & (sla <= n_))[:, None] & ((slo >= w_) & (slo <= e_))[None, :] & ~np.ma.getmaskarray(sw[0])
            ser = {y: float(np.mean([sw[k][m].mean() for k, w in enumerate(WS) if w.year == y])) for y in range(1991, 2027)}
            c_ = np.mean([ser[y] for y in range(1991, 2021)])
            soil[nm] = {"box_s_n_w_e": [s_, n_, w_, e_], "pct_vs_normal": round(100 * (ser[2026] / c_ - 1), 1),
                        "wettest_rank": [1 + sum(1 for v in ser.values() if v > ser[2026]), len(ser)]}
        out["ground"] = {"what": "ERA5 topsoil (0-7 cm) 8-10 Oct 2026 vs the same days 1991-2020; rank 1 = wettest",
                         "areas": soil}
    out["weekend_layers"] = {"aemet_zones": "AEMET OpenData warnings (CAP, with polygons): opendata.aemet.es "
                                            "api/avisos_cap; cite AEMET's Friday 16 Oct note for named areas. TLS News "
                                            "tracks the update (research/news/).",
                             "past_floods": "Requested from Aftereffects (HANZE to 2020 plus named recent events)."}
    json.dump(out, open(os.path.join(HERE, "data", "explainer_2026-10.json"), "w"), separators=(",", ":"))
    print("wrote", os.path.getsize(os.path.join(HERE, "data", "explainer_2026-10.json")) // 1024, "KB;",
          {k: (v.get("pct_vs_normal") if isinstance(v, dict) else None) for k, v in out.items()})


if __name__ == "__main__" and sys.argv[1:] == ["build"]:
    build()
