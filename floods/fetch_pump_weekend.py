"""ECMWF's forecast for the second DANA (16-20 Oct 2026), on the explainer's pump grid, so design can
carry the measured storm-1 sequence into the weekend. This is ECMWF's forecast, labelled with its run
time; FLO adds nothing to it.

Source: ECMWF IFS 0.25 deg (Open-Meteo model ecmwf_ifs025), taken at 1 deg points over 30-60N,
35W-20E, 00 and 12 UTC. Run time from Open-Meteo's own metadata for the model. Specific humidity at
850 hPa is computed from the forecast temperature and relative humidity (Magnus formula).

Writes floods/.era5_cache/pump_weekend_forecast.json (raw, gitignored); explainer_data.py builds
pump_weekend from it. Any point missing makes the run fail and write nothing.

Run:  .venv/bin/python floods/fetch_pump_weekend.py
"""
import datetime as dt
import json
import math
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, ".era5_cache", "pump_weekend_forecast.json")
LATS = [60 - k for k in range(31)]                 # 60..30 N, north to south like the ERA5 grids
LONS = [-35 + k for k in range(56)]                # 35W..20E
VARS = ["temperature_500hPa", "geopotential_height_500hPa", "temperature_850hPa",
        "relative_humidity_850hPa", "wind_speed_850hPa", "wind_direction_850hPa"]


def get(url, tries=6):
    """Open-Meteo weights a multi-point request by its points, so a 1,736-point grid trips the per-minute
    limit (HTTP 429). Batches are paced by the caller; a 429 here waits and retries."""
    import time
    for k in range(tries):
        try:
            return json.load(urllib.request.urlopen(url, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == tries - 1:
                raise
            time.sleep(70 * (k + 1))


def main():
    meta = get("https://api.open-meteo.com/data/ecmwf_ifs025/static/meta.json")
    run = dt.datetime.fromtimestamp(meta["last_run_initialisation_time"], dt.timezone.utc)
    pts = [(la, lo) for la in LATS for lo in LONS]
    res = {}
    for i in range(0, len(pts), 50):
        b = pts[i:i + 50]
        if i:
            time.sleep(65)
        url = ("https://api.open-meteo.com/v1/forecast?models=ecmwf_ifs025&timezone=GMT&wind_speed_unit=ms"
               "&start_date=2026-10-16&end_date=2026-10-20&hourly=" + ",".join(VARS)
               + "&latitude=" + ",".join(str(la) for la, _ in b) + "&longitude=" + ",".join(str(lo) for _, lo in b))
        r = get(url)
        r = r if isinstance(r, list) else [r]
        if len(r) != len(b):
            raise SystemExit(f"batch {i}: asked {len(b)} points, got {len(r)}; nothing written")
        for (la, lo), p in zip(b, r):
            res[(la, lo)] = p["hourly"]
    times = res[pts[0]]["time"]
    keep = [k for k, t in enumerate(times) if t.endswith("T00:00") or t.endswith("T12:00")]
    frames = []
    for k in keep:
        f = {"time": times[k] + "Z"}
        for v in VARS:
            f[v] = [[res[(la, lo)][v][k] for lo in LONS] for la in LATS]
        q = []
        for la in LATS:
            row = []
            for lo in LONS:
                t, rh = res[(la, lo)]["temperature_850hPa"][k], res[(la, lo)]["relative_humidity_850hPa"][k]
                if t is None or rh is None:
                    row.append(None); continue
                e = rh / 100 * 6.112 * math.exp(17.67 * t / (t + 243.5))       # hPa
                row.append(round(1000 * 0.622 * e / (850 - 0.378 * e), 1))     # g/kg
            q.append(row)
        f["q850_gkg"] = q
        frames.append(f)
    missing = sum(v is None for f in frames for r in f["temperature_500hPa"] for v in r)
    if missing:
        raise SystemExit(f"{missing} missing t500 values; nothing written")
    json.dump({"source": "ECMWF IFS 0.25 deg via Open-Meteo (ecmwf_ifs025)", "run_utc": run.isoformat(),
               "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
               "lat": LATS, "lon": LONS, "frames": frames}, open(OUT, "w"))
    print(f"run {run:%Y-%m-%d %H} UTC, {len(frames)} frames, {len(pts)} points")


if __name__ == "__main__":
    main()
