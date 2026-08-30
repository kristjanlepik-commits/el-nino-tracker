"""Emit the Latin America regional conditions payload for the LatAm page.

D-030 SEAM. This channel fetches, owns that the numbers are
methodologically correct, and emits validated JSON. Design renders it.
Nothing here draws anything.

WHAT IT IS. Seven regions of South America, each with the state of its
land surface now and the calendar window in which El Nino's teleconnection
reaches it. The point of the page element is that the windows are
STAGGERED: each region has one season that matters and they do not
coincide, so a map of current conditions alone implies the trouble is
where it is now, which is false.

WHAT IT IS NOT, AND THIS MUST SURVIVE INTO THE RENDER. It is not a fire
forecast or any other outcome forecast. Measured against 27 years of INPE
data, the best available predictor of Amazon dry-season fire explains 18%
of the variance; the other 82% is ignition, which is human. The payload
carries `skill_caveat` for exactly this reason and the renderer should
show it rather than dropping it as boilerplate.

BASELINE CHOICE, stated because it differs from the obvious one. Ranks are
computed against PRIOR years only, 1991-2025, never including the year
being reported. That matches the crops channel's convention
(`current_year_in_baseline: false`) so a percentile means the same thing
across the site. Including the current year would compress every rank
toward the middle by one observation and make cross-channel comparison
quietly wrong.

Run:
    .venv/bin/python scripts/build_latam_conditions.py

Writes data/latam_conditions.json. Reads a cached ERA5 monthly-means pull
(one small CDS request, cached on disk) so re-running is free.
"""

import calendar
import glob
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "latam_conditions.json"
CACHE = Path(tempfile.gettempdir()) / "tls_latam_conditions"
PAYLOAD_VERSION = "0.1"
BASE_FIRST, BASE_LAST = 1991, 2025

# lat_s, lat_n, lon_w, lon_e
REGIONS = [
    ("sesa",      "SESA / Pampas",             -38.0, -26.0, -64.0, -49.0,
     "wet", [10, 11, 12, 1, 2], [11, 12, 1],
     "floods, and an agricultural upside for rainfed systems"),
    ("n_amazon",  "N Amazon / Roraima",          0.0,   5.0, -64.0, -58.0,
     "dry", [12, 1, 2, 3, 4], [1, 2, 3],
     "fire"),
    ("venezuela", "Venezuela / Guianas",         2.0,  10.0, -75.0, -64.0,
     "dry", [12, 1, 2, 3, 4], [1, 2, 3],
     "fire"),
    ("altiplano", "Altiplano",                 -22.0, -14.0, -70.0, -62.0,
     "dry", [12, 1, 2], [],
     "its wet season fails"),
    ("coastal_pe", "Coastal Ecuador / N Peru",   -6.0,   2.0, -81.5, -78.0,
     "wet", [1, 2, 3, 4], [2, 3, 4],
     "floods"),
    ("nordeste",  "Nordeste",                  -15.0,  -4.0, -45.0, -35.0,
     "dry", [3, 4, 5], [3, 4, 5],
     "drought in its only rainy season"),
    ("s_amazon",  "S Amazon arc",              -12.0,  -5.0, -70.0, -46.0,
     "dry", [], [],
     "fire, but its window is Jul-Oct 2027 and falls outside this period"),
]


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "sa.nc"
    if not p.exists():
        import cdsapi
        cdsapi.Client(quiet=True, progress=False).retrieve(
            "reanalysis-era5-single-levels-monthly-means",
            {
                "product_type": ["monthly_averaged_reanalysis"],
                "variable": ["volumetric_soil_water_layer_3",
                             "total_precipitation", "2m_temperature"],
                "year": [str(y) for y in range(BASE_FIRST, 2027)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "time": ["00:00"],
                "data_format": "netcdf",
                "download_format": "unarchived",
                "area": [13, -82, -40, -34],
            },
            str(p),
        )
    return p


def open_vars(p):
    import xarray as xr
    out = {}
    if zipfile.is_zipfile(p):
        d = str(p) + ".x"
        if not os.path.isdir(d):
            with zipfile.ZipFile(p) as z:
                z.extractall(d)
        members = sorted(glob.glob(os.path.join(d, "*.nc")))
    else:
        members = [str(p)]
    for m in members:
        ds = xr.open_dataset(m)
        for v in ds.data_vars:
            out[v] = ds[v]
    return out


def series(da, box):
    s, n, w, e = box
    x = da.sel(latitude=slice(n, s), longitude=slice(w, e)).mean(
        dim=["latitude", "longitude"])
    o = {}
    for y, m, v in zip(x.valid_time.dt.year.values,
                       x.valid_time.dt.month.values, x.values):
        o.setdefault(int(y), {})[int(m)] = float(v)
    return o


def pctl(hist, cur):
    """Percentile of `cur` among PRIOR observations only. Low = dry."""
    return round(100.0 * sum(1 for h in hist if h < cur) / len(hist))


def main():
    V = open_vars(fetch())
    tname = "valid_time"
    last = V["swvl3"][tname].values[-1]
    obs_year = int(str(last)[:4])
    obs_month = int(str(last)[5:7])

    regions = []
    for key, name, s, n, w, e, sign, window, peak, hazard in REGIONS:
        box = (s, n, w, e)
        SM = series(V["swvl3"], box)
        P = series(V["tp"], box)
        T = series(V["t2m"], box)
        days = calendar.monthrange(obs_year, obs_month)[1]

        sm_hist = [SM[y][obs_month] for y in range(BASE_FIRST, BASE_LAST + 1)]
        p_hist = [P[y][obs_month] * 1000 * days
                  for y in range(BASE_FIRST, BASE_LAST + 1)]
        t_clim = np.mean([T[y][obs_month] for y in range(BASE_FIRST, 2021)])

        trail = []
        for back in (2, 1, 0):
            m = obs_month - back
            yy = obs_year if m >= 1 else obs_year - 1
            m = m if m >= 1 else m + 12
            h = [SM[y][m] for y in range(BASE_FIRST, BASE_LAST + 1)]
            trail.append(pctl(h, SM[obs_year][m]))

        regions.append({
            "key": key,
            "name": name,
            "box": {"lat_s": s, "lat_n": n, "lon_w": w, "lon_e": e},
            "sign": sign,
            "hazard": hazard,
            "window_months": window,
            "peak_months": peak,
            "window_in_period": bool(window),
            "soil_pctl": pctl(sm_hist, SM[obs_year][obs_month]),
            "rain_pctl": pctl(p_hist, P[obs_year][obs_month] * 1000 * days),
            "temp_anomaly_c": round(float(T[obs_year][obs_month] - t_clim), 2),
            "soil_pctl_trail": trail,
        })

    payload = {
        "_generated_from": "ERA5 monthly means via CDS, cached; no live fetch at render time",
        "_generator": "scripts/build_latam_conditions.py",
        "payload_version": PAYLOAD_VERSION,
        "observation_month": f"{obs_year}-{obs_month:02d}",
        "max_data_age_days": 75,
        "max_data_age_measured_from": (
            "the end of observation_month. ERA5 monthly means publish about "
            "five weeks after a month closes, so a payload older than this "
            "means the monthly pull has stopped rather than that the world "
            "went quiet."),
        "baseline": {
            "basis": f"{BASE_FIRST}-{BASE_LAST}, same calendar month of each year",
            "first": BASE_FIRST,
            "last": BASE_LAST,
            "n": BASE_LAST - BASE_FIRST + 1,
            "current_year_in_baseline": False,
            "means": (
                "every percentile in this file is computed against 35 PRIOR "
                "observations of the same calendar month, never including the "
                "year being reported. Matches the crops channel so a "
                "percentile means the same thing across the site. LOW is dry."),
        },
        "instrument_legend": {
            "soil_pctl": {
                "name": "Soil moisture, 28-100 cm",
                "unit": "percentile", "worse_is": "low",
                "summarises": "the water actually in the ground, which carries "
                              "seasonal memory rather than this month's weather"},
            "rain_pctl": {
                "name": "Rainfall", "unit": "percentile", "worse_is": "low",
                "summarises": "the observation month alone"},
            "temp_anomaly_c": {
                "name": "Temperature anomaly", "unit": "degrees C",
                "worse_is": "high", "summarises": "against the 1991-2020 mean "
                                                  "for the same month"},
            "soil_pctl_trail": {
                "name": "Soil moisture, last three months",
                "unit": "percentile, oldest first", "worse_is": "falling",
                "summarises": "direction of travel. A region can sit mid-range "
                              "and be collapsing: Roraima ran 69, 36, 6."},
        },
        "windows": {
            "means": "the months in which this region's El Nino teleconnection "
                     "reaches it. Seasonality, not a forecast of magnitude.",
            "source": "Cai et al. 2020, Nature Reviews Earth and Environment, "
                      "for the precipitation dipole and its seasonality; Chen "
                      "et al. 2017, Nature Climate Change, for the fire lag.",
            "note": "s_amazon carries an empty window on purpose. Its response "
                    "arrives about 15 months after onset, so its principal "
                    "window is Jul-Oct 2027 and falls outside this period. "
                    "That absence is a finding, not missing data.",
        },
        "skill_caveat": {
            "headline": "This is not a fire forecast and must not be rendered as one.",
            "detail": "Measured against 27 years of INPE Amazon fire counts, "
                      "the best available predictor (NDJ ONI) explains 18% of "
                      "the variance in dry-season fire. The other 82% is "
                      "ignition, which is human: 2025 paired the third-driest "
                      "wet-season recharge on record with the lowest fire year "
                      "on record.",
            "render_required": True,
        },
        "absence_reasons": {
            "window_not_in_period": "the region's exposure window falls outside "
                                    "the nine months this payload covers. Its "
                                    "conditions are still measured and shown.",
            "box_outside_domain": "the region sits outside the ERA5 box this "
                                  "payload requests and carries no values.",
        },
        "limits": [
            "Every value is a box average. It cannot see a state, a catchment "
            "or a city, and a regional mean can sit at the 50th percentile "
            "with half of it in drought.",
            "The SESA wet signal was cancelled outright by a strong positive "
            "Southern Annular Mode in 2015-16.",
            "Central Chile's teleconnection has measurably decayed since 2000 "
            "and is excluded from this payload for that reason.",
        ],
        "regions": regions,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}  ({len(regions)} regions, "
          f"observation month {payload['observation_month']})")
    for r in regions:
        w = "-" if not r["window_in_period"] else \
            f"{len(r['window_months'])}mo"
        print(f"  {r['name']:26} soil {r['soil_pctl']:>3}  rain {r['rain_pctl']:>3}"
              f"  {r['temp_anomaly_c']:+5.2f}C  trail {r['soil_pctl_trail']}  window {w}")


if __name__ == "__main__":
    main()
