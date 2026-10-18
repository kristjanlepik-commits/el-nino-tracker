"""The Nino regions map: where along the equator the warmth sits.

Science, 2026-10-18, for Kristjan: this El Nino is east-based, and Nino
3.4 alone understates it. Week of 7 October: Nino 1+2 +5.2 against a
prior record of +4.5, Nino 3 +4.1 against +3.3, Nino 3.4 +3.3 against
+3.0, Nino 4 +1.3 and no record. The map's job is one sentence: the
hottest water is against South America, not in the central Pacific.

WHAT THIS WRITES, AND WHAT IT DOES NOT. Only the field. One PNG per
panel, the tropical Pacific SST anomaly averaged over one CPC week, plus
a JSON naming the weeks. The four Nino boxes and their labels are drawn
by the page, from the same CPC weekly numbers as the table
(physical_state.nino_regions), never from this grid. A box mean off the
0.25 degree grid differs from CPC's index by a tenth or two, and a
reader comparing map and table would conclude one is wrong.

THE WEEK IS CPC'S. CPC's weekly index is labelled by the Wednesday at
the centre of a Sunday-to-Saturday week, so the field is the mean of the
seven days centred on that date, for 2026 and for the same-week analogs
the table compares against (1997 and 2015, from the same fetcher). The
page shows the map only when its week matches the table's week.

FILES ARE DATED AND NEVER REWRITTEN AFTER PUBLISH. docs/nino-map/
<week>.png per panel, so a frozen issue keeps pointing at the field it
was published with (invariant 5). Re-running for an unpublished week
overwrites it, which is how Monday's run replaces a hand preview.

Source: NOAA OISST v2.1, 0.25 degree daily, against its own 1991-2020
daily climatology, from PSL's OPeNDAP server, the same product and base
as design/make_pacific_sst.py.

    .venv/bin/python design/make_nino_map.py            CPC's current week
    .venv/bin/python design/make_nino_map.py 2026-10-07 a given CPC week
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres"
CLIM = f"{BASE}/sst.day.mean.ltm.1991-2020.nc"
OUT = ROOT / "docs" / "nino-map"

# 130E to 70W, 20S to 20N: the four boxes run 160E to 80W and 5N to 10S,
# and the margin above and below is where the page sets their labels.
LON_W, LON_E = 130.0, 290.0
LAT_S, LAT_N = -20.0, 20.0
# Below this the cell draws as paper: VD's ruling 13a for the front-page
# field, the same rule here so the two maps read alike.
FILL_FLOOR = 1.0
UPSCALE = 3


def _rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _connected(water, lats, lons, seed_lat, seed_lon):
    """Water reachable from a central-Pacific seed: drops the Caribbean."""
    i = int(np.argmin(np.abs(lats - seed_lat)))
    j = int(np.argmin(np.abs(lons - seed_lon)))
    seen = np.zeros_like(water, dtype=bool)
    seen[i, j] = True
    stack = [(i, j)]
    h, w = water.shape
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and water[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                stack.append((ny, nx))
    return seen


def week_field(centre: date, clim):
    """Mean SST anomaly over the 7 days centred on `centre`, 1991-2020 base."""
    days = [centre + timedelta(days=k) for k in range(-3, 4)]
    obs = xr.open_dataset(f"{BASE}/sst.day.mean.{centre.year}.nc")
    if days[-1].year != centre.year or days[0].year != centre.year:
        raise SystemExit("week crosses a year boundary; not handled")
    sel = dict(lat=slice(LAT_S, LAT_N), lon=slice(LON_W, LON_E))
    got = obs.sst.sel(time=slice(str(days[0]), str(days[-1])))
    have = [str(t)[:10] for t in got.time.values]
    sst = got.sel(**sel).mean("time").values
    doy = [d.timetuple().tm_yday for d in days]
    # The climatology has 365 days; in a leap year day 60 onward shifts.
    if centre.year % 4 == 0:
        doy = [d - 1 if d > 59 else d for d in doy]
    base = clim.sst.isel(time=[d - 1 for d in doy]).sel(**sel).mean("time").values
    # PSL truncates a large reply into ZEROS with exit 0 (see
    # make_pacific_sst.py). A real field here always has land as NaN and
    # never sits at exactly 0.00 C.
    for name, v in (("observations", sst), ("climatology", base)):
        if not np.isnan(v).any() or (v == 0).mean() > 0.01:
            raise SystemExit(f"REFUSING: {name} for {centre} came back zero-filled.")
    lats = got.sel(**sel).lat.values
    lons = got.sel(**sel).lon.values
    anom = sst - base
    if lats[0] < lats[-1]:
        anom, lats = anom[::-1], lats[::-1]
    return anom, lats, lons, have


def render(anom, lats, lons, scale):
    water = np.isfinite(anom)
    pac = _connected(water, lats, lons, 0.0, 200.0)
    edges = np.linspace(-scale, scale, len(T.ANOMALY) + 1)[1:-1]
    idx = np.digitize(np.nan_to_num(anom), edges)
    pal = np.array([_rgb(c) for c in T.ANOMALY], dtype=np.uint8)
    rgba = np.zeros(anom.shape + (4,), dtype=np.uint8)
    drawn = pac & (np.abs(np.nan_to_num(anom)) >= FILL_FLOOR) & (idx != len(T.ANOMALY) // 2)
    rgba[..., :3] = pal[idx]
    rgba[..., 3] = np.where(drawn, 255, 0)
    land = ~water
    # Land is left transparent so the page's own background shows, light or
    # dark; only its edge is drawn.
    rgba = np.repeat(np.repeat(rgba, UPSCALE, axis=0), UPSCALE, axis=1)
    # Land filled in PAPER_SUNK is 1.05:1 on PAPER, so it did not read and the
    # one thing the map has to show, warmth against the South American
    # coast, had no coast. A one-pixel line at the land's edge does it.
    big = np.repeat(np.repeat(land, UPSCALE, axis=0), UPSCALE, axis=1)
    edge = big & ~(np.roll(big, 1, 0) & np.roll(big, -1, 0)
                   & np.roll(big, 1, 1) & np.roll(big, -1, 1))
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = False
    rgba[edge, :3] = _rgb(T.INK_FAINT)
    rgba[edge, 3] = 255
    return Image.fromarray(rgba, "RGBA")


def main():
    from fetchers import oisst_weekly
    r = oisst_weekly.fetch()
    if not r.ok:
        raise SystemExit(f"CPC weekly fetch failed: {r.error}")
    week = sys.argv[1] if len(sys.argv) > 1 else str(r.issued)[:10]
    if week != str(r.issued)[:10]:
        print(f"note: CPC's current week is {r.issued}, rendering {week}")
    analogs = r.payload.get("analogs_same_week") or {}
    panels = [("2026", week)] + [(y, analogs[y]["week"]) for y in ("1997", "2015")
                                 if y in analogs]
    clim = xr.open_dataset(CLIM, decode_times=False)
    OUT.mkdir(parents=True, exist_ok=True)
    scale = T.OCEAN_SCALE
    out = []
    for year, wk in panels:
        anom, lats, lons, have = week_field(date.fromisoformat(wk), clim)
        if len(have) < 7:
            print(f"  {year}: only {len(have)} of 7 days available ({have[-1]} last)")
        render(anom, lats, lons, scale).save(OUT / f"{wk}.png", optimize=True)
        fin = anom[np.isfinite(anom)]
        print(f"  {year} week of {wk}: {len(have)} days, "
              f"{fin.min():+.1f} to {fin.max():+.1f} C -> docs/nino-map/{wk}.png")
        out.append({"year": year, "week": wk, "png": f"{wk}.png",
                    "days": [have[0], have[-1]], "n_days": len(have),
                    "max_c": round(float(fin.max()), 1)})
    (OUT / f"{week}.json").write_text(json.dumps({
        "cpc_week": week,
        "extent": {"lon_west": LON_W, "lon_east": LON_E,
                   "lat_south": LAT_S, "lat_north": LAT_N},
        "full_scale": scale, "fill_floor": FILL_FLOOR,
        "panels": out,
        "source": "NOAA OISST v2.1 (0.25 deg daily), 7-day mean centred on "
                  "the CPC week, against 1991-2020",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "design/make_nino_map.py",
    }, indent=2) + "\n")
    print(f"wrote docs/nino-map/{week}.json")


if __name__ == "__main__":
    main()
