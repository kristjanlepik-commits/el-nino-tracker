"""Reproduce the IMERG intensity calibration from scratch.

Exists because product could not verify the finding: D-195 accepted the
binning on this channel's working, since the paired data lived only in a
scratchpad. A measurement only its author can reproduce has the same
defect as a decision that lives only in a chat.

Run:  .venv/bin/python floods/verify_intensity.py

Fetches AEMET station rainfall for the Valencia DANA (2024-10-29) and
IMERG for the same day and box, pairs them AT STATION LOCATIONS, and
writes floods/data/intensity_dana_2024-10-29.json.

Pairing at stations rather than max against max is the point of the
method: a box maximum against a gauge maximum folds position error into
the magnitude answer, and would overstate the gap if IMERG placed the
cell correctly but a few kilometres off.

Needs ~/.aemet_key (free, opendata.aemet.es) and ~/.earthdata_token.
AEMET serves LATIN-1; decoding as UTF-8 presents as "no data".
"""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import fetch_imerg_baseline as F

DAY = "2024-10-29"
BOX = {"lon": (-2.0, 0.6), "lat": (38.4, 40.4)}
AEMET = "https://opendata.aemet.es/opendata/api"


def _get(url, hdr=None):
    cmd = ["curl", "-sS", "-L", "--max-time", "90"]
    if hdr:
        cmd += ["-H", hdr]
    return subprocess.run(cmd + [url], capture_output=True).stdout.decode("latin-1")


def _aemet(path, tries=4):
    """Two-step: metadata gives a URL, the file appears there shortly after.

    RETRIED ON CONTENT, not on status. AEMET generates the data file
    asynchronously, so a fetch a second after the metadata call can return
    something that is not yet the array. A single sleep was enough most of
    the time and not always, and the failure arrives as unparseable text
    rather than as an error.

    Checking that the body actually starts a JSON array is the same rule
    heat and this channel converged on independently against CEDA on
    2026-08-18: an HTTP status is a property of the client (following the
    redirect turned 302 with 15 bytes into 200 with a full login page),
    so only the CONTENT distinguishes an answer from a failure."""
    key = open(os.path.expanduser("~/.aemet_key")).read().strip()
    meta = json.loads(_get(f"{AEMET}/{path}", f"api_key: {key}"))
    if "datos" not in meta:
        raise SystemExit(f"AEMET refused: {meta.get('descripcion','?')}")
    for attempt in range(tries):
        time.sleep(1.5 * (attempt + 1))     # be polite to a free public API
        body = _get(meta["datos"])
        if body.lstrip().startswith("["):
            return json.loads(body)
        print(f"    AEMET data file not ready (attempt {attempt+1}/{tries}, "
              f"{len(body)} bytes)", file=sys.stderr)
    raise SystemExit("AEMET: data file never became a JSON array. NOT an "
                     "empty result: refusing to report zero stations as an "
                     "answer.")


def dms(s):
    """AEMET gives DDMMSSH, e.g. 394924N."""
    h, v = s[-1], s[:-1]
    x = int(v[:-4]) + int(v[-4:-2]) / 60 + int(v[-2:]) / 3600
    return -x if h in "SW" else x


def main():
    obs = _aemet(f"valores/climatologicos/diarios/datos/fechaini/{DAY}T00:00:00UTC"
                 f"/fechafin/{DAY}T23:59:59UTC/todasestaciones")
    inv = {r["indicativo"]: r for r in
           _aemet("valores/climatologicos/inventarioestaciones/todasestaciones")}
    st = []
    for r in obs:
        m = inv.get(r["indicativo"])
        if not m:
            continue
        p = r.get("prec", "")
        p = 0.0 if p in ("", "Ip") else float(str(p).replace(",", "."))
        try:
            st.append({"id": r["indicativo"], "name": r.get("nombre", ""),
                       "prec": p, "lat": dms(m["latitud"]), "lon": dms(m["longitud"])})
        except Exception:
            continue
    print(f"  {len(st)} stations with coordinates")

    lon0, lon1 = BOX["lon"]; lat0, lat1 = BOX["lat"]
    tok = F.token()
    out = {"event": "Valencia DANA", "day": DAY, "box": BOX, "products": {}}
    for prod in ("GPM_3IMERGDL", "GPM_3IMERGDF"):
        r = F.fetch_day(DAY, BOX, tok, short=prod)
        if r is None:
            continue
        a = np.asarray(r[0], float)
        a = np.where(np.isfinite(a) & (a >= 0), a, np.nan)
        nlon, nlat = a.shape
        pairs = []
        for s in st:
            if not (lat0 < s["lat"] < lat1 and lon0 < s["lon"] < lon1):
                continue
            i = int((s["lon"] - lon0) / (lon1 - lon0) * nlon)
            j = int((s["lat"] - lat0) / (lat1 - lat0) * nlat)
            if 0 <= i < nlon and 0 <= j < nlat and np.isfinite(a[i, j]):
                pairs.append({"station": s["name"], "gauge_mm": round(s["prec"], 1),
                              "imerg_mm": round(float(a[i, j]), 1)})
        g = np.array([p["gauge_mm"] for p in pairs])
        m = np.array([p["imerg_mm"] for p in pairs])
        bins = []
        for lo, hi, lbl in [(0, 10, "under 10mm"), (10, 50, "10-50mm"),
                            (50, 150, "50-150mm"), (150, 1e9, "over 150mm")]:
            sel = (g >= lo) & (g < hi)
            if sel.sum():
                bins.append({"band": lbl, "n": int(sel.sum()),
                             "gauge_mean": round(float(g[sel].mean()), 1),
                             "imerg_mean": round(float(m[sel].mean()), 1),
                             "ratio": round(float(m[sel].mean() / max(g[sel].mean(), .01)), 2)})
        out["products"][prod] = {
            "n_pairs": len(pairs), "imerg_max_cell": round(float(np.nanmax(a)), 1),
            "gauge_max": round(float(g.max()), 1),
            "ratio_at_wettest_gauge": round(float(m[g.argmax()] / g.max()), 2),
            "bins": bins, "pairs": pairs}
        print(f"\n  {prod}: {len(pairs)} pairs, gauge max {g.max():.1f}, "
              f"IMERG there {m[g.argmax()]:.1f}, ratio {m[g.argmax()]/g.max():.2f}")
        for b in bins:
            print(f"    {b['band']:12} n={b['n']:3d}  gauge {b['gauge_mean']:7.1f}"
                  f"  IMERG {b['imerg_mean']:7.1f}  ratio {b['ratio']:.2f}")
    p = os.path.join(os.path.dirname(__file__), "data",
                     f"intensity_dana_{DAY}.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\n  wrote {p}")


if __name__ == "__main__":
    sys.exit(main())
