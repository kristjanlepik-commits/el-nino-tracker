"""Render docs/pacific-sst.png, the El Nino field under the front-page map.

MANUAL, and deliberately not wired into run_brief.py. Nothing in the
weekly pipeline runs this and nothing imports it. It pulls live data,
writes two committed assets, and stops:

    docs/pacific-sst.png    the field, transparent outside the band
    docs/pacific-sst.json   what the PNG shows, so the page can label it

That split is the point. The map needs a gridded SST field, no fetcher
returns one, and promoting this into the weekly run is the ENSO
tracker's call on their surface rather than something design should
smuggle in. Until they do, the asset is refreshed by running this by
hand and committing the result, and the JSON carries the observation
date so the page can say how old the picture is instead of implying it
is current.

    .venv/bin/python design/make_pacific_sst.py

Why this product. The 1 degree weekly OISST v2 that the obvious spec
reaches for stopped updating on 2023-01-29, so it would have rendered a
map three and a half years stale. This uses the live 0.25 degree v2.1
daily product, subset over OPeNDAP before transfer, so the 271 MB and
1.4 GB whole-file sizes are not what moves.

Extent is the eastern Pacific only, dateline to the South American
coast. The western half of the basin sits on the far side of the
map's antimeridian seam and rendering it too put a second, disconnected
copy of the same event against Australia. One side reads as a crop that
continues past the edge, which is the intent: this is an intrigue
generator on a global map, not the full picture. The full picture
belongs on the El Nino page.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.image as mpimg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres"
OBS = f"{BASE}/sst.day.mean.2026.nc"
CLIM = f"{BASE}/sst.day.mean.ltm.1991-2020.nc"

LON_W, LON_E = -180.0, -70.0
LAT_S, LAT_N = -22.0, 22.0
DAYS = 7
UPSCALE = 3          # keeps the nine steps crisp once the browser scales it
FADE_FRAC = 0.28     # share of the band's height that ramps out, each side

PNG = ROOT / "docs" / "pacific-sst.png"
META = ROOT / "docs" / "pacific-sst.json"


def _hex_to_rgb(s: str) -> tuple:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main() -> None:
    obs = xr.open_dataset(OBS)
    clim = xr.open_dataset(CLIM, decode_times=False)

    last = obs.sst.isel(time=slice(-DAYS, None))
    when = str(last.time.values[-1])[:10]
    doys = [np.datetime64(str(t)[:10]).astype("datetime64[D]").astype(object)
            .timetuple().tm_yday for t in last.time.values]

    lat = obs.lat.values
    lat_slice = (slice(LAT_S, LAT_N) if lat[0] < lat[-1]
                 else slice(LAT_N, LAT_S))
    sel = dict(lat=lat_slice, lon=slice(LON_W % 360, LON_E % 360))

    week = last.sel(**sel).mean("time")
    base = clim.sst.isel(time=[d - 1 for d in doys]).sel(**sel).mean("time")
    anom = (week.values - base.values).astype("float64")
    lats = week.lat.values
    if lats[0] < lats[-1]:                 # north must be row 0 for the PNG
        anom, lats = anom[::-1, :], lats[::-1]

    finite = np.isfinite(anom)
    clipped = float(np.mean(np.abs(anom[finite]) > T.OCEAN_SCALE)) if finite.any() else 0.0
    print(f"week to {when}: {anom.shape}, "
          f"{np.nanmin(anom):+.2f} to {np.nanmax(anom):+.2f} C, "
          f"{clipped * 100:.2f}% beyond +/-{T.OCEAN_SCALE}")

    # Nine discrete steps, the same ones tokens.ANOMALY prints in the
    # legend, so every colour on the map can be decoded off it. The fade
    # is alpha only and never touches the colour, so it cannot move a
    # value into a neighbouring step.
    edges = np.linspace(-T.OCEAN_SCALE, T.OCEAN_SCALE, len(T.ANOMALY) + 1)[1:-1]
    idx = np.digitize(np.nan_to_num(anom, nan=0.0), edges)
    palette = np.array([_hex_to_rgb(c) for c in T.ANOMALY], dtype=np.uint8)

    rgba = np.zeros(anom.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = palette[idx]

    n = anom.shape[0]
    k = max(1, int(n * FADE_FRAC))
    ramp = np.linspace(0.0, 1.0, k) ** 1.5
    col = np.ones(n)
    col[:k], col[-k:] = ramp, ramp[::-1]
    alpha = np.repeat(col[:, None], anom.shape[1], axis=1)
    alpha[~finite] = 0.0                   # land and gaps stay transparent
    rgba[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)

    if UPSCALE > 1:
        rgba = np.repeat(np.repeat(rgba, UPSCALE, axis=0), UPSCALE, axis=1)

    PNG.parent.mkdir(parents=True, exist_ok=True)
    mpimg.imsave(PNG, rgba)

    # The extent is written next to the image so the page positions it
    # from the data rather than from numbers retyped into a template. A
    # map that draws the field half a basin off is worse than no field.
    META.write_text(json.dumps({
        "observation_date": when,
        "days_averaged": DAYS,
        "lon_west": LON_W, "lon_east": LON_E,
        "lat_south": float(min(lats)), "lat_north": float(max(lats)),
        "anomaly_min": round(float(np.nanmin(anom)), 2),
        "anomaly_max": round(float(np.nanmax(anom)), 2),
        "full_scale": T.OCEAN_SCALE,
        "fraction_beyond_scale": round(clipped, 4),
        "source": "NOAA OISST v2.1 (0.25 deg daily) vs 1991-2020 climatology",
        "source_url": OBS,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "design/make_pacific_sst.py, run by hand",
    }, indent=2) + "\n")
    print(f"wrote {PNG.relative_to(ROOT)} ({PNG.stat().st_size:,} bytes)")
    print(f"wrote {META.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
