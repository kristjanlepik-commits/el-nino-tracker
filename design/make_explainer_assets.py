"""Assets for the flood explainer's 3D scenes (D-327), from FLO's payload.

Reads floods/data/explainer_2026-10.json from origin/main (the shared tree
lags origin) and writes, to OUT:

  pump_sea.png      the sea and land surface for scene 5: September 2026
                    sea surface temperature anomaly on the site's diverging
                    scale (tokens.ANOMALY, OCEAN_SCALE), land flat in
                    --land with the 50m coastline
  pump_cold_NN.png  one per t500 frame: the cold anomaly 5 km up as an
                    alpha layer, transparent where it is not colder than
                    normal by at least COLD_FROM
  pump.json         extent, frame times, the 850 hPa wind frames clipped to
                    the extent, and the per-frame coldest cell, so the page
                    labels what the data holds rather than what a sentence
                    says

The page never reads FLO's file directly and never converts units; this is
the one place the grids are touched, so it re-runs when FLO re-emits.

Run:  .venv/bin/python design/make_explainer_assets.py [OUT]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T                                     # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/tmp/el_nino_preview/explainer3d/assets")
LON0, LON1, LAT0, LAT1 = -20.0, 18.0, 33.0, 52.0
PX = 42                      # texture pixels per degree of longitude
COLD_FROM = 2.0              # degrees colder than normal before it shows
COLD_FULL = 10.0             # fully opaque at this anomaly


def payload():
    return json.loads(subprocess.run(
        ["git", "show", "origin/main:floods/data/explainer_2026-10.json"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout)


def _rgb(hexs):
    return np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in hexs],
                    dtype=float)


RAMP = _rgb(T.ANOMALY)


def ramp(v):
    """Continuous blend along the nine site steps; clamps at OCEAN_SCALE."""
    x = (np.clip(v / T.OCEAN_SCALE, -1, 1) + 1) * 4          # 0..8
    i = np.clip(np.floor(x).astype(int), 0, 7)
    f = (x - i)[..., None]
    return RAMP[i] * (1 - f) + RAMP[i + 1] * f


def _grow(g, n):
    """Extend values into NaN cells from their neighbours, n cells deep.

    For the SST grid only: at 0.5 degrees the last sea cell sits up to
    half a cell off the 50m coastline, and bilinear sampling against a
    NaN neighbour leaves a stepped pale band along every shore. Growing
    the sea a few cells under the land, which the coastline then covers,
    moves no value a reader can see onto any sea pixel that had one.
    """
    g = g.copy()
    for _ in range(n):
        nan = np.isnan(g)
        if not nan.any():
            break
        p = np.pad(g, 1, constant_values=np.nan)
        nb = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:],
                       p[:-2, :-2], p[:-2, 2:], p[2:, :-2], p[2:, 2:]])
        with np.errstate(all="ignore"):
            m = np.nanmean(nb, axis=0)
        g[nan] = m[nan]
    return g


def sample(grid, lat, lon, la, lo, grow=0):
    """Bilinear sample of a north-to-south grid at arrays la, lo; NaN gaps."""
    g = np.array([[np.nan if v is None else v for v in r] for r in grid])
    if grow:
        g = _grow(g, grow)
    lat, lon = np.array(lat), np.array(lon)
    fi = (lat[0] - la) / (lat[0] - lat[1])
    fj = (lo - lon[0]) / (lon[1] - lon[0])
    i0 = np.clip(np.floor(fi).astype(int), 0, len(lat) - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, len(lon) - 2)
    di, dj = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    out = (g[i0, j0] * (1 - di) * (1 - dj) + g[i0 + 1, j0] * di * (1 - dj) +
           g[i0, j0 + 1] * (1 - di) * dj + g[i0 + 1, j0 + 1] * di * dj)
    inside = ((la <= lat[0]) & (la >= lat[-1]) & (lo >= lon[0]) & (lo <= lon[-1]))
    return np.where(inside, out, np.nan)


def grid_px():
    w = int((LON1 - LON0) * PX)
    h = int((LAT1 - LAT0) * PX)
    lo = LON0 + (np.arange(w) + 0.5) / PX
    la = LAT1 - (np.arange(h) + 0.5) / PX
    return w, h, *np.meshgrid(la, lo, indexing="ij")


def coast_mask(w, h):
    coast = json.loads((ROOT / "design/data/europe_coast.json").read_text())
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    xy = lambda r: [((lo - LON0) * PX, (LAT1 - la) * PX) for lo, la in r]
    for ring in coast["rings"]:
        if len(ring) > 2:
            d.polygon(xy(ring), fill=255)
    lines = Image.new("L", (w, h), 0)
    dl = ImageDraw.Draw(lines)
    for ring in coast["rings"]:
        if len(ring) > 2:
            dl.line(xy(ring) + [xy(ring)[0]], fill=255, width=2)
    return np.array(m) > 127, np.array(lines) > 127


def sea_texture(d, w, h, LA, LO):
    heat = d["heat"]
    sst = sample(heat["sst_anom_c"], heat["lat"], heat["lon"], LA, LO, grow=4)
    land, lines = coast_mask(w, h)
    img = np.empty((h, w, 3))
    img[:] = _rgb([T.ANOMALY_NEUTRAL])[0]
    ok = ~np.isnan(sst)
    img[ok] = ramp(sst[ok])
    # A sea cell the SST grid calls land but the coastline calls sea (the
    # 0.5 degree grid is coarser than the 50m coast) takes the nearest
    # neutral rather than a guess.
    img[land] = _rgb(["#D9D8D0"])[0]
    img[lines] = _rgb([T.INK_FAINT])[0]
    return Image.fromarray(img.astype(np.uint8)), float(np.nanmax(sst))


def cold_layers(d, w, h, LA, LO):
    t = d["pump"]["t500_frames"]
    cold = _rgb([T.COLD])[0]
    frames = []
    for k, f in enumerate(t["frames"]):
        a = sample(f["t500_anom_c"], t["lat"], t["lon"], LA, LO)
        alpha = np.clip((-a - COLD_FROM) / (COLD_FULL - COLD_FROM), 0, 1)
        alpha = np.nan_to_num(alpha) ** 0.8
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., :3] = cold
        rgba[..., 3] = (alpha * 235).astype(np.uint8)
        name = "pump_cold_%02d.png" % k
        Image.fromarray(rgba).resize((w // 2, h // 2), Image.BILINEAR) \
            .save(OUT / name, optimize=True)
        g = np.array([[np.nan if v is None else v for v in r] for r in f["t500_anom_c"]])
        i, j = np.unravel_index(np.nanargmin(g), g.shape)
        frames.append({
            "time": f["time"], "img": name,
            "coldest": {"anom_c": round(float(g[i, j]), 1), "lat": t["lat"][i],
                        "lon": t["lon"][j],
                        # A minimum on the grid's edge is not a located core.
                        "on_edge": bool(i in (0, g.shape[0] - 1) or
                                        j in (0, g.shape[1] - 1))}})
    return frames


def winds(d):
    w = d["pump"]["winds_850"]
    keep_i = [i for i, la in enumerate(w["lat"]) if LAT0 - 1 <= la <= LAT1 + 1]
    keep_j = [j for j, lo in enumerate(w["lon"]) if LON0 - 1 <= lo <= LON1 + 1]
    cut = lambda g: [[round(g[i][j], 2) for j in keep_j] for i in keep_i]
    return {"lat": [w["lat"][i] for i in keep_i],
            "lon": [w["lon"][j] for j in keep_j],
            "frames": [{"time": f["time"], "u": cut(f["u850_ms"]),
                        "v": cut(f["v850_ms"]), "q": cut(f["q850_gkg"])}
                       for f in w["frames"]]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = payload()
    w, h, LA, LO = grid_px()
    sea, hottest = sea_texture(d, w, h, LA, LO)
    sea.save(OUT / "pump_sea.png", optimize=True)
    meta = {
        "_about": "Built by design/make_explainer_assets.py from "
                  "floods/data/explainer_2026-10.json. Do not edit.",
        "extent": {"lon": [LON0, LON1], "lat": [LAT0, LAT1]},
        "sea": {"img": "pump_sea.png", "what": "September 2026 sea surface "
                "temperature anomaly vs 1991-2020, ERA5", "max_c": round(hottest, 1),
                "scale_c": T.OCEAN_SCALE},
        "cold": {"what": "temperature 5 km up (500 hPa) vs the same hour "
                 "1991-2020, shown where colder by %g C or more" % COLD_FROM,
                 "frames": cold_layers(d, w, h, LA, LO)},
        "wind": winds(d),
        "barcelona": {"lat": 41.39, "lon": 2.17},
    }
    (OUT / "pump.json").write_text(json.dumps(meta, separators=(",", ":")))
    for f in meta["cold"]["frames"]:
        c = f["coldest"]
        print(f["time"], c["anom_c"], c["lat"], c["lon"], "EDGE" if c["on_edge"] else "")
    print("wrote", OUT, "sea max %.1f C" % hottest)


if __name__ == "__main__":
    main()
