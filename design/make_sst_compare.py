#!/usr/bin/env python3
"""Four El Ninos on the same calendar date, March to October: a motion test.

Kristjan, 2026-10-04, on Ben Noll's four-panel Oct 1 map (2026, 2015,
1997, 1982): "is there a way for us to generate gif that compares them -
march til now?"

THIS IS THE USE CASE THE MOVING LINE WAS NOT. On 2026-09-01 the animated
analog line was parked as "too simple": a line growing left to right is a
still with a delay, the reader ends at the same picture. Here the motion
carries what no single frame can: four oceans on the same date, warming
at different speeds and in different shapes, so WHEN each tongue forms and
HOW FAST it widens is watched rather than inferred from four stills.

TWO STEPS, deliberately separate:
  pull    OISST v2.1 daily over OPeNDAP, cached per slice in the scratch
          dir, resumable. ~155 slices at 3-5 s each. Re-running skips
          everything already cached, so a dropped connection costs one
          slice, not the job.
  render  matplotlib + PillowWriter, no new dependencies (Kristjan's
          ruling: stay in matplotlib, no ffmpeg).

    .venv/bin/python design/make_sst_compare.py pull
    .venv/bin/python design/make_sst_compare.py render

THE ANOMALY BASELINE IS A METHOD CHOICE, AND IT IS SCIENCE'S. A raw
anomaly against 1991-2020 makes 1982 look cold and 2026 hot almost
everywhere, partly because the whole ocean has warmed since 1982 and not
because of El Nino. That is the same inflation RONI exists to remove on
this site. So `render` produces both: RAW (what Ben's figure shows) and
RELATIVE (each frame minus that day's 20S-20N mean anomaly, the RONI
idea applied to the map). Which one publishes is not design's call.
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres"
CLIM = f"{BASE}/sst.day.mean.ltm.1991-2020.nc"
YEARS = (2026, 2015, 1997, 1982)        # Ben's order: current first
END = date(2026, 10, 1)                  # Ben's frame, so the last one matches
STEP = 7                                 # weekly
STRIDE = 4                               # 0.25 deg -> 1 deg: legible, 16x less
CACHE = Path("/private/tmp/claude-505/"
             "-Users-admin-Documents-Claude-Projects-El-Nino-Tracker/"
             "963b8065-d8cb-408a-9195-33d00aeda096/scratchpad/sst_cache")


def frame_days():
    """Month-days ending on END, back to March, weekly."""
    out, d = [], END
    while d >= date(END.year, 3, 1):
        out.append((d.month, d.day))
        d -= timedelta(days=STEP)
    return out[::-1]


def _doy(month, day):
    # All four years are non-leap, so one day-of-year index serves all of
    # them and the climatology's 365-day axis lines up without adjustment.
    return (date(2026, month, day) - date(2026, 1, 1)).days


def pull():
    import xarray as xr
    CACHE.mkdir(parents=True, exist_ok=True)
    days = frame_days()
    todo = ([("clim", m, d) for m, d in days]
            + [(y, m, d) for y in YEARS for m, d in days])
    have = sum(1 for k in todo if _path(*k).exists())
    print(f"{len(days)} frames x {len(YEARS)} years + climatology: "
          f"{len(todo)} slices, {have} cached", flush=True)
    sources = {}
    for k in todo:
        p = _path(*k)
        if p.exists():
            continue
        y, m, d = k
        for attempt in range(4):
            try:
                if y == "clim":
                    ds = sources.setdefault("clim", xr.open_dataset(
                        CLIM, decode_times=False))
                    v = ds.sst.isel(time=_doy(m, d),
                                    lat=slice(None, None, STRIDE),
                                    lon=slice(None, None, STRIDE)).values
                else:
                    ds = sources.setdefault(y, xr.open_dataset(
                        f"{BASE}/sst.day.mean.{y}.nc"))
                    v = ds.sst.sel(time=f"{y}-{m:02d}-{d:02d}").isel(
                        lat=slice(None, None, STRIDE),
                        lon=slice(None, None, STRIDE)).values
                np.save(p, v.astype("float32"))
                break
            except Exception as e:                       # network: retry
                print(f"  retry {k}: {type(e).__name__}", flush=True)
                sources.pop(y, None)
                time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"INCOMPLETE: gave up on {k}. Re-run to resume.")
        have += 1
        if have % 10 == 0:
            print(f"  {have}/{len(todo)}", flush=True)
    if not (CACHE / "grid.npz").exists():
        import xarray as xr
        ds = xr.open_dataset(f"{BASE}/sst.day.mean.2026.nc")
        np.savez(CACHE / "grid.npz",
                 lat=ds.lat.values[::STRIDE], lon=ds.lon.values[::STRIDE])
    missing = [k for k in todo if not _path(*k).exists()]
    print("COMPLETE" if not missing else f"INCOMPLETE: {len(missing)} missing")


def _path(y, m, d):
    return CACHE / f"{y}_{m:02d}{d:02d}.npy"


_MON = ("January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December")


def _fields(relative):
    """{year: [anomaly array per frame]}, cropped, in the frame order."""
    g = np.load(CACHE / "grid.npz")
    lat, lon = g["lat"], g["lon"]
    keep = (lat >= -60) & (lat <= 65)
    w = np.cos(np.deg2rad(lat))[:, None]
    trop = (lat >= -20) & (lat <= 20)
    out = {y: [] for y in YEARS}
    for m, d in frame_days():
        clim = np.load(_path("clim", m, d))
        for y in YEARS:
            a = np.load(_path(y, m, d)) - clim
            if relative:
                # THE RONI IDEA ON A MAP. Subtract that day's area-weighted
                # 20S-20N mean anomaly, so a frame shows where the ocean is
                # warm RELATIVE TO THE TROPICS THAT DAY rather than relative
                # to a 1991-2020 world. Without it, 1982 reads cold and 2026
                # hot almost everywhere, and most of that is warming, not El
                # Nino. Science's call which version publishes.
                band = a[trop]
                ww = np.broadcast_to(w[trop], band.shape)
                ok = np.isfinite(band)
                a = a - (band[ok] * ww[ok]).sum() / ww[ok].sum()
            out[y].append(a[keep])
    return out, lat[keep], lon


def render(relative=False, fps=4):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.colors import BoundaryNorm, ListedColormap
    import tokens as T

    fields, lat, lon = _fields(relative)
    days = frame_days()
    # The site's nine-step anomaly ramp over +/-OCEAN_SCALE, the same steps
    # the front-page field and its legend use, so a colour here decodes the
    # same way as a colour there.
    edges = np.linspace(-T.OCEAN_SCALE, T.OCEAN_SCALE, len(T.ANOMALY) + 1)
    cmap = ListedColormap(T.ANOMALY)
    # LAND IS A HUELESS MID-GREY THAT NO STEP USES. The first render had
    # land at #D9D8D2 against the neutral step at #E8E7E2, and in the
    # March frames, where most of the ocean is near zero, whole basins of
    # quiet Pacific read as continent. Darker, and with no hue, so it
    # cannot be mistaken for the pale blue or pale red flanking zero.
    cmap.set_bad("#B3B2AB")
    cmap.set_over(T.ANOMALY[-1])
    cmap.set_under(T.ANOMALY[0])
    norm = BoundaryNorm(edges, cmap.N)

    fig = plt.figure(figsize=(8.4, 12.6), dpi=100)
    fig.patch.set_facecolor(T.PAPER)
    top, left, right = 0.905, 0.10, 0.87
    h = (top - 0.06) / len(YEARS)
    ims = []
    for i, y in enumerate(YEARS):
        ax = fig.add_axes([left, top - (i + 1) * h + 0.008, right - left,
                           h - 0.016])
        im = ax.imshow(np.ma.masked_invalid(fields[y][0]), origin="lower",
                       extent=[lon[0], lon[-1], lat[0], lat[-1]],
                       cmap=cmap, norm=norm, aspect="auto",
                       interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        fig.text(left - 0.012, top - i * h - h / 2, str(y), ha="right",
                 va="center", fontsize=15, color=T.INK,
                 fontweight="bold" if y == 2026 else "normal")
        ims.append(im)

    title = fig.text(left, 0.945, "", fontsize=19, color=T.INK)
    fig.text(left, 0.922,
             ("Each map relative to that day's tropical average"
              if relative else
              "Sea temperature anomaly against 1991-2020"),
             fontsize=11, color=T.INK_SOFT)
    cax = fig.add_axes([0.895, 0.30, 0.018, 0.40])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                      ticks=[-3, 0, 3], extend="both")
    cb.ax.set_yticklabels(["-3 °C", "0", "+3 °C"], fontsize=10,
                          color=T.INK_SOFT)
    cb.outline.set_visible(False)
    # THE VINTAGE, because this is built to travel: a GIF on X carries no
    # dateline, and is reposted long after the ocean has moved.
    fig.text(left, 0.022,
             "NOAA OISST v2.1, daily, 1 degree. The Long Swell. "
             "Last frame 1 October 2026.", fontsize=9, color=T.INK_FAINT)

    def draw(k):
        for y, im in zip(YEARS, ims):
            im.set_data(np.ma.masked_invalid(fields[y][k]))
        m, d = days[k]
        title.set_text(f"{d} {_MON[m - 1]}")
        return ims + [title]

    n = len(days)
    # A beat on the first date, then the run, then a long hold on 1 October
    # so a screenshot taken any time after the motion is Ben's frame.
    frames = [0] * 5 + list(range(n)) + [n - 1] * 10
    tag = "relative" if relative else "raw"
    out = ROOT / f"design/sst_compare_{tag}.gif"
    FuncAnimation(fig, draw, frames=frames, interval=1000 / fps,
                  blit=False).save(out, writer=PillowWriter(fps=fps))
    draw(n - 1)
    fig.savefig(ROOT / f"design/sst_compare_{tag}_final.png",
                facecolor=T.PAPER)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB),"
          f" {n} dates, {days[0][1]} {_MON[days[0][0] - 1]} to "
          f"{days[-1][1]} {_MON[days[-1][0] - 1]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pull":
        pull()
    elif cmd == "render":
        render(relative=False)
        render(relative=True)
    else:
        print(__doc__)
