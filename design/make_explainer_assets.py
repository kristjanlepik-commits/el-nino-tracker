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
import os
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
LON0, LON1, LAT0, LAT1 = -32.0, 18.0, 33.0, 58.0
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


def ramp(v, full=None):
    """Continuous blend along the nine site steps; clamps at `full`
    (OCEAN_SCALE for temperature)."""
    x = (np.clip(v / (full or T.OCEAN_SCALE), -1, 1) + 1) * 4          # 0..8
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
    h_lon0 = heat["lon"][0]
    sst = sample(heat["sst_anom_c"], heat["lat"], heat["lon"], LA, LO, grow=4)
    land, lines = coast_mask(w, h)
    img = np.empty((h, w, 3))
    img[:] = _rgb([T.ANOMALY_NEUTRAL])[0]
    ok = ~np.isnan(sst)
    img[ok] = ramp(sst[ok])
    # The September SST pull stops at 25W; the pump map runs to 32W for the
    # cold pool. Fade to neutral over the last 4 degrees rather than end in
    # a hard seam a reader would take for a front.
    fade = np.clip((LO - h_lon0) / 4.0, 0, 1)[..., None]
    img = img * fade + _rgb([T.ANOMALY_NEUTRAL])[0] * (1 - fade)
    # A sea cell the SST grid calls land but the coastline calls sea (the
    # 0.5 degree grid is coarser than the 50m coast) takes the nearest
    # neutral rather than a guess.
    img[land] = _rgb(["#D9D8D0"])[0]
    img[lines] = _rgb([T.INK_FAINT])[0]
    return Image.fromarray(img.astype(np.uint8)), float(np.nanmax(sst))


def cold_layers(d, w, h, LA, LO):
    p = d["pump"]
    g = p["grid"]
    cold = _rgb([T.COLD])[0]
    frames = []
    for k, f in enumerate(p["frames"]):
        a = sample(f["t500_anom_c"], g["lat"], g["lon"], LA, LO)
        alpha = np.clip((-a - COLD_FROM) / (COLD_FULL - COLD_FROM), 0, 1)
        alpha = np.nan_to_num(alpha) ** 0.8
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., :3] = cold
        rgba[..., 3] = (alpha * 235).astype(np.uint8)
        name = "pump_cold_%02d.png" % k
        Image.fromarray(rgba).resize((w // 2, h // 2), Image.BILINEAR) \
            .save(OUT / name, optimize=True)
        c = f["cold_core"]
        frames.append({
            "time": f["time"], "img": name,
            # FLO's interior core (b071bb8c), not a grid minimum: a minimum
            # on the grid edge is not a located core, which is how the
            # first version of this scene nearly mislabelled 30 September.
            "coldest": {"anom_c": c["anom_c"], "t_c": c["t_c"], "lat": c["lat"],
                        "lon": c["lon"], "on_edge": False}})
    return frames


def _rings(features):
    for f in features:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            for ring in poly:
                yield ring


COUNTRIES = None


def outline_map(field, lat, lon, ext, px, full, name, grow=0, land_fill=False, lines_only=False):
    """A flat anomaly map in the site's ramp, with hairline outlines.

    ext = (lon0, lon1, lat0, lat1). Longitude pixels are scaled by the
    cosine of the mid-latitude so the shapes are not stretched.
    Returns the image size.
    """
    global COUNTRIES
    if COUNTRIES is None:
        COUNTRIES = json.loads((ROOT / "fires/data/countries.geo.json").read_text())["features"]
    lo0, lo1, la0, la1 = ext
    kx = px * np.cos(np.radians((la0 + la1) / 2)) if (la1 - la0) < 120 else px
    w, h = int((lo1 - lo0) * kx), int((la1 - la0) * px)
    LO = lo0 + (np.arange(w) + 0.5) / kx
    LA = la1 - (np.arange(h) + 0.5) / px
    LA, LO = np.meshgrid(LA, LO, indexing="ij")
    v = sample(field, lat, lon, LA, LO, grow=grow)
    img = np.empty((h, w, 3)); img[:] = _rgb(["#D9D8D0"])[0]
    ok = ~np.isnan(v)
    img[ok] = ramp(v[ok], full)
    im = Image.fromarray(img.astype(np.uint8))
    if lines_only:          # a transparent overlay of the outlines alone
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    xy = lambda r: [((x - lo0) * kx, (la1 - y) * px) for x, y in r]
    for ring in _rings(COUNTRIES):
        if land_fill:
            dr.polygon(xy(ring), fill="#D9D8D0")
        dr.line(xy(ring), fill=T.INK_FAINT, width=1)
    im.save(OUT / name, optimize=True)
    return list(im.size)


def merge_heat(d):
    """Sea where the sea grid has a value, land air temperature elsewhere."""
    h = d["heat"]
    sea = [[np.nan if v is None else v for v in r] for r in h["sst_anom_c"]]
    land = [[np.nan if v is None else v for v in r] for r in h["land_t2m_anom_c"]]
    g = np.where(np.isnan(sea), land, sea)
    return [[None if np.isnan(x) else float(x) for x in r] for r in g]


def heat_months(nc_path):
    """May to September 2026, each against its own month's 1991-2020 mean.

    Kristjan, 16 Oct: the heat map should move, May to September. Built
    from design/fetch_heat_months.py's ERA5 pull (FLO's payload carries
    September only). Same box, same merge (sea where ERA5 has SST, 2 m air
    over land) and same scale as the September map, so the last frame and
    the static map agree. Returns the frame list, or None without the file.
    """
    import os
    if not nc_path or not os.path.exists(nc_path):
        return None
    import xarray as xr
    ds = xr.open_dataset(nc_path)
    tdim = "valid_time" if "valid_time" in ds.dims else "time"
    t = ds[tdim].dt
    lat = [float(v) for v in ds["latitude"].values]
    lon = [float(v) for v in ds["longitude"].values]
    names = {5: "May", 6: "June", 7: "July", 8: "August", 9: "September"}
    frames = []
    for m in range(5, 10):
        def anom(var):
            x = ds[var]
            clim = x.where((t.month == m) & (t.year >= 1991) & (t.year <= 2020), drop=True).mean(tdim)
            now = x.where((t.month == m) & (t.year == 2026), drop=True).isel({tdim: 0})
            return (now - clim).values
        sst, t2m = anom("sst"), anom("t2m")
        g = np.where(np.isnan(sst), t2m, sst)
        # A real field has values everywhere over land and sea in this box.
        if np.isnan(g).mean() > 0.02 or np.nanmax(np.abs(g)) > 25:
            raise SystemExit("REFUSING: %s 2026 field looks wrong (NaN %.2f, max %.1f)"
                             % (names[m], np.isnan(g).mean(), np.nanmax(np.abs(g))))
        field = [[None if np.isnan(v) else float(v) for v in row] for row in g]
        name = "heat_m%02d.png" % m
        size = outline_map(field, lat, lon, (-25, 45, 28, 72), 14, None, name)
        frames.append({"month": names[m], "img": name, "size": size,
                       "grid": [[None if np.isnan(v) else round(float(v), 1) for v in row] for row in g]})
    # The morph: grids the page interpolates between, plus the outlines as a
    # transparent overlay at the same projection, so the heat can flow
    # under fixed coastlines instead of cutting between stills (Kristjan).
    size = outline_map(frames[-1]["grid"], lat, lon, (-25, 45, 28, 72), 14, None,
                       "heat_lines.png", lines_only=True)
    morph = {"lat": lat, "lon": lon, "box": [-25, 45, 28, 72], "size": size,
             "full_c": T.OCEAN_SCALE, "ramp": T.ANOMALY, "lines": "heat_lines.png",
             "months": [{"month": f["month"], "grid": f.pop("grid")} for f in frames]}
    (OUT / "heat_morph.json").write_text(json.dumps(morph, separators=(",", ":")))
    return frames


def winds(d):
    p = d["pump"]
    g = p["grid"]
    lat, lon = g["wind_lat"], g["wind_lon"]
    keep_i = [i for i, la in enumerate(lat) if LAT0 - 1 <= la <= LAT1 + 1]
    keep_j = [j for j, lo in enumerate(lon) if LON0 - 1 <= lo <= LON1 + 1]
    cut = lambda q: [[round(q[i][j], 2) for j in keep_j] for i in keep_i]
    return {"lat": [lat[i] for i in keep_i], "lon": [lon[j] for j in keep_j],
            "frames": [{"time": f["time"], "u": cut(f["u850_ms"]),
                        "v": cut(f["v850_ms"]), "q": cut(f["q850_gkg"])}
                       for f in p["frames"]]}


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
        "story": d["pump"]["story"],
        "not_claimed": d["pump"]["not_claimed"],
    }
    (OUT / "pump.json").write_text(json.dumps(meta, separators=(",", ":")))

    # Scenes 2, 3, 4 and 7: flat maps and the series they sit beside.
    h, e, sg = d["heat"], d["evaporation"], d["sponge_global"]
    flat = {
        "heat": {"img": "heat_europe.png", "full_c": T.OCEAN_SCALE,
                 "size": outline_map(merge_heat(d), h["lat"], h["lon"],
                                     (-25, 45, 28, 72), 14, None, "heat_europe.png"),
                 "headline": h["headline"],
                 "what": "September 2026 vs 1991-2020: sea surface temperature "
                         "over the sea, air temperature at 2 m over land, ERA5"},
        "evap": {"img": "evap_med.png", "full_pct": 40,
                 "size": outline_map(e["pct_map"], e["lat"], e["lon"],
                                     (-6, 37, 30, 46), 30, 40, "evap_med.png",
                                     land_fill=True),
                 "unit": e["unit"], "normal": e["basin_mean_normal"],
                 "y2026": e["basin_mean_2026"], "pct": e["pct_vs_normal"],
                 "rank": e["rank_since_1991"],
                 "by_year": e["by_year"]},
        "vapour": {"img": "vapour_world.png", "full_pct": 30,
                   "size": outline_map(sg["map_pct_2026"], sg["map_lat"], sg["map_lon"],
                                       (-180, 180, -60, 75), 5, 30, "vapour_world.png"),
                   "unit": sg["unit"], "by_year_pct": sg["by_year_pct"],
                   "rank": sg["rank_2026"], "physics": sg["physics"]},
        "ground": d["ground"],
        "heat_months": heat_months(os.environ.get("HEAT_MONTHS_NC")),
    }
    (OUT / "flat.json").write_text(json.dumps(flat, separators=(",", ":")))
    for f in meta["cold"]["frames"]:
        c = f["coldest"]
        print(f["time"], c["anom_c"], c["lat"], c["lon"], "EDGE" if c["on_edge"] else "")
    print("wrote", OUT, "sea max %.1f C" % hottest)


if __name__ == "__main__":
    main()
