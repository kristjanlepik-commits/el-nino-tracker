"""Context readings for the second DANA (17-20 Oct 2026), committed so other
desks cite a file, not a message (TLS News, 15 Oct). Neither is a claim
under floods/prereg/spain_dana2_2026-10.md; both are context.

1. ECMWF ensemble readout at the 21 pre-registered stations, 16-21 Oct:
   ecmwf_ifs025 (51 members) via the Open-Meteo ensemble API, daily
   precipitation summed per member. Each value is a ~25 km grid cell, so it
   understates point cloudbursts; stations in the same cell read the same.
   AEMET's own figures are the ones to quote.
2. ERA5 topsoil wetness, 8-10 Oct 2026, by named coastal area: layer 1
   (0-7 cm), mean of 00 UTC on 8, 9 and 10 Oct, land cells in each box,
   against the same three days in each year 1991-2025; normal = 1991-2020
   mean; rank 1 = wettest of 36 years (1991-2026). ERA5 2026 is preliminary.

Run:  .venv/bin/python floods/dana2_context.py
"""
import datetime as dt
import json
import os
import statistics as st
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STATIONS = ["0367", "0370B", "0200E", "0076", "0016A", "9981A", "8500A", "8414A", "8416", "8019",
            "8025", "7031", "7228", "7178I", "6155A", "6156X", "B954", "B957", "B278", "B228", "B893"]


def ecmwf():
    import verify_intensity as V
    inv = {s["indicativo"]: s for s in V._aemet("valores/climatologicos/inventarioestaciones/todasestaciones")}
    lat = [V.dms(inv[i]["latitud"]) for i in STATIONS]
    lon = [V.dms(inv[i]["longitud"]) for i in STATIONS]
    url = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=" + ",".join(f"{x:.4f}" for x in lat)
           + "&longitude=" + ",".join(f"{x:.4f}" for x in lon)
           + "&daily=precipitation_sum&models=ecmwf_ifs025&timezone=Europe%2FMadrid"
           "&start_date=2026-10-16&end_date=2026-10-21")
    fetched = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    r = json.load(urllib.request.urlopen(url, timeout=90))
    r = r if isinstance(r, list) else [r]
    if len(r) != len(STATIONS):
        raise SystemExit(f"expected {len(STATIONS)} points, got {len(r)}; not writing")
    out = {}
    for sid, p in zip(STATIONS, r):
        d = p["daily"]
        keys = [k for k in d if k.startswith("precipitation_sum")]
        tot = sorted(sum(x or 0 for x in d[k]) for k in keys)
        one = sorted(max((x or 0) for x in d[k]) for k in keys)
        n = len(tot)
        if n < 40:
            raise SystemExit(f"{sid}: only {n} members; not writing")
        q = lambda a, f: a[min(n - 1, int(f * n))]
        out[sid] = {"name": inv[sid]["nombre"], "lat": round(p["latitude"], 3), "lon": round(p["longitude"], 3),
                    "members": n, "total_16_21_median_mm": round(st.median(tot), 1),
                    "total_16_21_p90_mm": round(q(tot, .9), 1), "total_16_21_max_mm": round(tot[-1], 1),
                    "wettest_day_median_mm": round(st.median(one), 1), "wettest_day_p90_mm": round(q(one, .9), 1)}
    return {"source": "ECMWF IFS ensemble 0.25 deg (ecmwf_ifs025, 51 members) via Open-Meteo ensemble API",
            "run": "latest run Open-Meteo served at fetch time; the API does not return the run's start time",
            "fetched_utc": fetched, "days": "2026-10-16 to 2026-10-21, local days (Europe/Madrid)",
            "caveat": "Each value is a ~25 km grid cell; it understates point cloudbursts, and stations sharing a "
                      "cell read identically. AEMET's 150-250 mm 'en pocas horas' is the figure to quote.",
            "stations": out}


def soil():
    data = json.load(open(os.path.join(HERE, "data", "explainer_2026-10.json")))["ground"]
    return {"source": "ERA5 volumetric soil water layer 1 (0-7 cm), Copernicus CDS, 2026 preliminary",
            "method": "mean of 00 UTC on 8, 9 and 10 Oct over land cells in each box; same days every year "
                      "1991-2026; normal = 1991-2020 mean; rank 1 = wettest of 36 years",
            "built_by": "floods/explainer_data.py (ground)", "areas": data["areas"]}


def main():
    out = {"_about": __doc__.split("\n\n")[0].replace("\n", " "), "ecmwf_ensemble": ecmwf(), "topsoil": soil()}
    f = os.path.join(HERE, "data", "dana2_context_2026-10-15.json")
    json.dump(out, open(f, "w"), indent=1, ensure_ascii=False)
    e = out["ecmwf_ensemble"]["stations"]
    print("wrote", f, "| fetched", out["ecmwf_ensemble"]["fetched_utc"])
    for sid, v in e.items():
        print(f"  {sid:6} median {v['total_16_21_median_mm']:6.1f}  p90 {v['total_16_21_p90_mm']:6.1f}  max {v['total_16_21_max_mm']:6.1f}")


if __name__ == "__main__":
    main()
