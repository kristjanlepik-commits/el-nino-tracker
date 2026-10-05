#!/usr/bin/env python3
"""Four El Ninos on the same calendar week, March to now: a motion test.

Kristjan, 2026-10-04, on Ben Noll's four-panel 1 October SST map (2026,
2015, 1997, 1982): "is there a way for us to generate gif that compares
them - march til now?"

THIS IS THE USE CASE THE MOVING LINE WAS NOT. On 2026-09-01 the animated
analog line was parked as "too simple": a line growing left to right is a
still with a delay. Here the motion carries what no single frame can:
four oceans on the same week, the warm tongue forming at different speeds
and in different shapes.

THE METHOD IS SCIENCE'S, AND THE FIRST BUILD HAD IT WRONG TWICE.
(Science, 2026-10-04; their name goes on the method once built this way.)

  1. Raw anomaly against 1991-2020 mixes forty years of ocean warming into
     an El Nino comparison: 1982 reads cold and 2026 hot almost everywhere.
     But subtracting the tropical mean over the WHOLE GLOBE is false in the
     other direction: 2026's tropical mean is high partly BECAUSE of the
     tongue, so subtracting it paints the extratropics blue, and the South
     Pacific read deep cold on that frame and near normal on the raw one.
     That correction belongs to a tropical index (D-288). So: relative to
     the 20S-20N mean, and the map CROPPED to 30S-30N, where the El
     Nino-driven shift in tropical rainfall responds to that contrast
     rather than to absolute temperature, and where the story is.
  2. Single days flicker and carry frontal noise. Each frame is a 7-day
     mean on CPC's weekly convention, centred on Wednesday, so a frame
     matches the weekly series the brief and the notes quote.

  And BLOCK-AVERAGED, NOT POINT-SAMPLED: the full 0.25 deg field is averaged
  4x4 to 1 deg. The first build took every fourth point, which adds noise of
  its own.

SAME CALENDAR WEEK, NOT THE SAME STAGE OF THE EVENT. 2015 had begun the
previous year; 1982 and 1997 peaked in November to January. The windows are
2026's Wednesday weeks, applied to the same month-days in every year, so all
panels always show the same seven days of the calendar. Matching is by
calendar date throughout, so leap years (2020, 2024 in the eight-year set)
need nothing special: every window starts in March, after 29 February, and
the 365-day climatology is indexed by the 2026 calendar's day of year.

  .venv/bin/python design/make_sst_compare.py pull     # resumable, cached
  .venv/bin/python design/make_sst_compare.py render
"""
from __future__ import annotations

import sys
import time
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres"
CLIM = f"{BASE}/sst.day.mean.ltm.1991-2020.nc"
YEARS = (2026, 2015, 1997, 1982)          # Ben's order: current first
EIGHT = tuple(range(2026, 2018, -1))      # 2026 down to 2019
FIRST_WED = date(2026, 3, 4)
LAT = (-30.0, 30.0)                       # science: crop to 30S-30N
TROP = (-20.0, 20.0)                      # the band CPC's relative index uses
BLOCK = 4                                 # 0.25 deg -> 1 deg, averaged
CACHE = Path("/private/tmp/claude-505/"
             "-Users-admin-Documents-Claude-Projects-El-Nino-Tracker/"
             "963b8065-d8cb-408a-9195-33d00aeda096/scratchpad/sst_cache_v2")
MONTHS = range(3, 11)                     # March to October
# RENDERS GO OUTSIDE THE REPO. qa_check scans untracked files as well as
# tracked ones, so the first eight-year render left a 7.6 MB GIF in design/
# that failed the 5 MB limit and blocked EVERY chat's push, not just this
# one's; twelve outputs there came to about 30 MB. Same hazard as the heat
# builder writing previews into docs/ on 2026-08-30. A GIF is a deliverable
# handed to a person, not a source file, and it regenerates from this one.
OUT = CACHE.parent / "sst_out"


def _doy(d):
    return (date(2026, d.month, d.day) - date(2026, 1, 1)).days


def _block(a):
    """(t, 240, 1440) -> (t, 60, 360), mean over each 4x4 block of ocean.

    Averaging obs and climatology SEPARATELY and subtracting afterwards is
    exact here, not an approximation: both are linear, and OISST's land mask
    is identical in the observations and the climatology, with no sea ice
    anywhere in 30S-30N to make the mask vary by day. A block that is all
    land stays NaN; a coastal block averages its ocean cells only.
    """
    t, ny, nx = a.shape
    b = a.reshape(t, ny // BLOCK, BLOCK, nx // BLOCK, BLOCK)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(b, axis=(2, 4)).astype("float32")


def _path(src, month):
    return CACHE / f"{src}_{month:02d}.npy"


PIECE = 5          # days per request; see _fetch


def _valid(v):
    """True if a raw OISST block is real data rather than a zero-filled hole.

    WHY THIS EXISTS. PSL's OPeNDAP server truncates a large response, the
    client logs "DAP DATADDS packet is apparently too short", and xarray
    hands back an array of ZEROS with no exception. The first full-res pull
    asked for a month at a time (43 MB) and cached 39 of 40 chunks as pure
    zeros: no NaN over land, value 0.00 everywhere. It rendered three empty
    panels and a fourth that was raw temperature minus nothing.

    Measured on 2026-10-05: 1, 3 and 7 days (up to 9.7 MB) come back real;
    14 days (19.4 MB) comes back zeros. Shape, size and exit status are
    identical either way, so the only check that can tell them apart looks
    at the VALUES: OISST is NaN over land, so a real 30S-30N block is about
    a quarter missing, and ocean temperature is never exactly 0.00 over a
    whole field.
    """
    if not v.size:
        return False
    land = np.isnan(v).mean()
    zero = (v == 0).mean()
    return (0.15 < land < 0.6 and zero < 0.01
            and np.nanmax(v) < 40 and np.nanmin(v) > -3)


def _open(url, **kw):
    """open_dataset with retries. The fetch loop retried requests but not
    the OPEN before them, and on 2026-10-05 a transient NetCDF I/O failure
    on opening the 2015 file killed that process after four of eight months,
    silently, with no INCOMPLETE line. Opening is a network call too."""
    import xarray as xr
    for attempt in range(6):
        try:
            return xr.open_dataset(url, **kw)
        except OSError as e:
            print(f"    open {url.rsplit('/', 1)[-1]}: {e.__class__.__name__}, "
                  f"retry", flush=True)
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"INCOMPLETE: could not open {url}. Re-run to resume.")


def _fetch(get, start, end):
    """Days start..end inclusive, in PIECE-day requests, each validated.

    `get(a, b)` returns the raw array for days a..b. A piece that fails
    validation is retried, then split in half: a corrupt piece is never
    cached, because a zero array cached once is served forever.
    """
    out, a = [], start
    while a <= end:
        b = min(a + timedelta(days=PIECE - 1), end)
        n = (b - a).days + 1
        for attempt in range(6):
            try:
                v = get(a, b)
            except Exception as e:
                print(f"    {a}..{b}: {type(e).__name__}, retry", flush=True)
                time.sleep(3 * (attempt + 1))
                continue
            if _valid(v) and v.shape[0] == n:
                break
            print(f"    {a}..{b}: came back corrupt, retry", flush=True)
            if attempt >= 2 and n > 1:      # stop asking for this much
                b = a + timedelta(days=max(0, n // 2 - 1))
                n = (b - a).days + 1
            time.sleep(3 * (attempt + 1))
        else:
            raise SystemExit(f"INCOMPLETE: {a}..{b} never came back real. "
                             f"Re-run to resume.")
        out.append(v)
        a = b + timedelta(days=1)
    return np.concatenate(out)


def pull(only=None):
    """Fetch every month chunk not already cached.

    `only` restricts to some sources, so the four years can be pulled by
    four processes at once: each writes different files, and the cache makes
    any of them safe to kill and re-run. One stream on the first run took
    several minutes a chunk, and a single long job is what the end of a
    session cut off on 2026-10-04.
    """
    import xarray as xr
    CACHE.mkdir(parents=True, exist_ok=True)
    srcs = ("clim",) + YEARS
    if only:
        # Any year OISST covers, not only the four in YEARS, so the 8-year
        # set (2019-2026) pulls through the same validated path.
        srcs = tuple("clim" if x == "clim" else int(x) for x in only)
    todo = [(s, m) for s in srcs for m in MONTHS]
    print(f"{len(todo)} month chunks, "
          f"{sum(_path(*k).exists() for k in todo)} cached", flush=True)
    for src, m in todo:
        p = _path(src, m)
        if p.exists():
            continue
        start = date(2026, m, 1)
        end = (date(2026, m + 1, 1) if m < 12 else date(2027, 1, 1)) \
            - timedelta(days=1)
        if src == "clim":
            ds = _open(CLIM, decode_times=False)
            sub = ds.sst.sel(lat=slice(*LAT))
            get = (lambda a, b, sub=sub:
                   sub.isel(time=slice(_doy(a), _doy(b) + 1)).values)
        else:
            ds = _open(f"{BASE}/sst.day.mean.{src}.nc")
            sub = ds.sst.sel(lat=slice(*LAT))
            last = date(2026, *map(int, str(ds.time.values[-1])[5:10].split("-")))
            end = min(end, last) if src == 2026 else end
            get = (lambda a, b, sub=sub, y=src: sub.sel(time=slice(
                f"{y}-{a.month:02d}-{a.day:02d}",
                f"{y}-{b.month:02d}-{b.day:02d}")).values)
        if end < start:
            continue
        v = _fetch(get, start, end)
        np.save(p, _block(v))
        print(f"  {src} {m:02d}: {v.shape[0]} days, validated", flush=True)
    if only:
        print(f"done: {', '.join(map(str, srcs))}")
        return
    import xarray as xr
    g = xr.open_dataset(f"{BASE}/sst.day.mean.2026.nc").sst.sel(lat=slice(*LAT))
    lat = g.lat.values.reshape(-1, BLOCK).mean(1)
    lon = g.lon.values.reshape(-1, BLOCK).mean(1)
    np.savez(CACHE / "grid.npz", lat=lat, lon=lon)
    print("COMPLETE")


def _daily(src):
    """{date-in-2026-calendar: 1-deg field} for every cached day of src.

    Refuses a corrupt cache at the point of use as well as at the point of
    fetch, because the one place a zero-filled field must never reach is a
    rendered frame, and a cache can outlive the code that wrote it.
    """
    out = {}
    for m in MONTHS:
        p = _path(src, m)
        if not p.exists():
            continue
        a = np.load(p)
        if not _valid(a):
            raise SystemExit(f"CORRUPT CACHE: {p.name} is not real data "
                             f"(zero-filled OPeNDAP response). Delete it and "
                             f"re-run pull.")
        for i, f in enumerate(a):
            out[date(2026, m, 1) + timedelta(days=i)] = f
    return out


def weeks():
    """Wednesdays whose whole Sun-Sat window has 2026 data, oldest first.

    Self-extending: the last frame is the last COMPLETE CPC week, and a
    re-pull after NOAA adds days moves it forward without code changes.
    """
    have = set(_daily(2026))
    out, w = [], FIRST_WED
    while all(w + timedelta(days=k) in have for k in range(-3, 4)):
        out.append(w)
        w += timedelta(days=7)
    return out


def fields(years=YEARS):
    """{year: [relative weekly anomaly per frame]}, plus lat, lon, weeks."""
    g = np.load(CACHE / "grid.npz")
    lat, lon = g["lat"], g["lon"]
    clim = _daily("clim")
    wk = weeks()
    wts = np.cos(np.deg2rad(lat))[:, None]
    band = (lat >= TROP[0]) & (lat <= TROP[1])
    out = {}
    for y in years:
        obs = _daily(y)
        frames = []
        for w in wk:
            days = [w + timedelta(days=k) for k in range(-3, 4)]
            anom = np.mean([obs[d] - clim[d] for d in days], axis=0)
            b = anom[band]
            ww = np.broadcast_to(wts[band], b.shape)
            ok = np.isfinite(b)
            frames.append(anom - (b[ok] * ww[ok]).sum() / ww[ok].sum())
        out[y] = frames
    return out, lat, lon, wk


_MON = ("January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December")


def ramp(variant):
    """(cmap, norm, colorbar ticks) for the site ramp or the bold proposal.

    BOLD IS ALL THREE LEVERS, Kristjan 2026-10-04 ("make all 1-2-3"), after
    Ben Noll's map read more dramatic than ours on identical data. Measured,
    the gap came from three drawing choices, not the ocean:

      1. a near-black extreme, where ours tops out at deep red
      2. a continuous ramp, where ours rounds into nine legend steps
      3. small anomalies visibly coloured, where ours keeps +0.33 to +1 C
         pale on purpose (31% of 2026's ocean sits in that band)

    Design argued for the first lever alone, since 3 makes modest warmth look
    alarming and 2 gives up decoding a colour off the legend. Kristjan chose
    all three; this is that, built from the site's own teal-to-red hues so it
    still reads as ours.

    A PROPOSAL FOR VD. tokens.ANOMALY is not edited: it drives every SST
    surface on the site, and changing it for one graphic would move all of
    them. Whether this becomes the house ramp is VD's call.
    """
    import tokens as T
    from matplotlib.colors import (BoundaryNorm, LinearSegmentedColormap,
                                   ListedColormap, Normalize)
    s = T.OCEAN_SCALE
    if variant == "bold":
        # Anchors in degrees C. Zero is the only near-neutral point (lever 3:
        # colour starts immediately), and the ends run past the site's
        # darkest steps to near-black teal and near-black maroon (lever 1).
        anchors = [(-3.0, "#03222A"), (-2.0, "#0A4A57"), (-1.0, "#417785"),
                   (-0.25, "#A9C3C9"), (0.0, "#F1F0EC"), (0.25, "#F2BFAD"),
                   (1.0, "#D9785A"), (2.0, "#A8341A"), (2.6, "#6A1606"),
                   (3.0, "#2A0802")]
        cmap = LinearSegmentedColormap.from_list(
            "bold", [((v + s) / (2 * s), c) for v, c in anchors])  # lever 2
        cmap.set_over("#1A0501")
        cmap.set_under("#021519")
        norm = Normalize(-s, s)
    else:
        cmap = ListedColormap(T.ANOMALY)
        cmap.set_over(T.ANOMALY[-1])
        cmap.set_under(T.ANOMALY[0])
        norm = BoundaryNorm(np.linspace(-s, s, len(T.ANOMALY) + 1), cmap.N)
    cmap.set_bad("#B3B2AB")
    return cmap, norm


def render(variant="site", years=YEARS, tag="", fps=4):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    import tokens as T

    f, lat, lon, wk = fields(years)
    cmap, norm = ramp(variant)

    # LAID OUT IN INCHES, NOT FRACTIONS, so the figure grows with the number
    # of strips. The four-year version squeezed each 6:1 strip slightly;
    # eight strips in the same box would have halved them and flattened every
    # tongue. Each strip keeps the same height whatever the count.
    W, HEAD, STRIP, FOOT = 12.0, 1.15, (1.4 if len(years) <= 4 else 1.2), 1.0
    H = HEAD + STRIP * len(years) + FOOT
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(T.PAPER)
    left, right = 0.085, 0.90
    bottom, top = FOOT / H, (FOOT + STRIP * len(years)) / H
    h = STRIP / H
    pad = 0.06 / H
    current = max(years)
    ims = []
    for i, y in enumerate(years):
        ax = fig.add_axes([left, top - (i + 1) * h + pad, right - left,
                           h - 2 * pad])
        im = ax.imshow(np.ma.masked_invalid(f[y][0]), origin="lower",
                       extent=[lon[0], lon[-1], lat[0], lat[-1]],
                       cmap=cmap, norm=norm, aspect="auto",
                       interpolation="nearest")
        ax.axis("off")
        fig.text(left - 0.01, top - i * h - h / 2, str(y), ha="right",
                 va="center", fontsize=15 if len(years) <= 4 else 13,
                 color=T.INK,
                 fontweight="bold" if y == current else "normal")
        ims.append(im)

    title = fig.text(left, 1 - 0.45 / H, "", fontsize=20, color=T.INK)
    fig.text(left, 1 - 0.78 / H,
             "Sea surface temperature relative to the tropical average, "
             "30\u00b0S to 30\u00b0N", fontsize=11.5, color=T.INK_SOFT)
    cax = fig.add_axes([0.915, bottom + 0.05 * (top - bottom), 0.013,
                        0.9 * (top - bottom)])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                      ticks=[-3, 0, 3], extend="both")
    cb.ax.set_yticklabels(["-3 °C", "0", "+3 °C"], fontsize=10,
                          color=T.INK_SOFT)
    cb.outline.set_visible(False)

    # SCIENCE'S FOUR CAPTION ITEMS. Wording here is a working draft for the
    # test; the reader-facing sentence is the editor's before it publishes.
    cap = ("Colour: NOAA OISST v2.1, 7-day means centred on Wednesday, 1991-2020 "
           "baseline, minus that week's 20°S-20°N average, so forty "
           "years of warming does not paint\nrecent years warm everywhere. "
           "That also removes the tropics-wide warming El Niño itself "
           "causes: these maps show the shape and strength of the tongue, warm"
           "\nor cold, not total ocean warmth. Values read lower than the "
           "fixed-baseline "
           "weekly figures we quote. Same calendar week in every year, not the "
           "same stage of each event.")
    fig.text(left, 0.3 / H, cap, fontsize=8.6, color=T.INK_FAINT,
             linespacing=1.45, va="bottom")

    def draw(k):
        for y, im in zip(years, ims):
            im.set_data(np.ma.masked_invalid(f[y][k]))
        w = wk[k]
        a, b = w - timedelta(days=3), w + timedelta(days=3)
        title.set_text(f"Week of {a.day} {_MON[a.month - 1]}"
                       f" to {b.day} {_MON[b.month - 1]}")
        return ims + [title]

    n = len(wk)
    frames = [0] * 5 + list(range(n)) + [n - 1] * 10
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"sst_compare_{tag}{variant}.gif"
    FuncAnimation(fig, draw, frames=frames, interval=1000 / fps,
                  blit=False).save(out, writer=PillowWriter(fps=fps))
    draw(n - 1)
    fig.savefig(OUT / f"sst_compare_{tag}{variant}_final.png",
                facecolor=T.PAPER)
    plt.close(fig)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB),"
          f" {n} weeks centred {wk[0]} to {wk[-1]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pull":
        pull(sys.argv[2:] or None)
    elif cmd == "render":
        render("site")
        render("bold")
    elif cmd == "render8":
        # Kristjan, 2026-10-05: "the similar one for the last 8 years? 8
        # blocks". Current year on top, as in the four-year version.
        for v in ("site", "bold"):
            render(v, years=EIGHT, tag="8y_")
    else:
        print(__doc__)
