#!/usr/bin/env python3
"""What El Nino usually does to rain, month by month: an animated calendar.

D-323, Kristjan 2026-10-12: "build, it would be interesting to see the
visual." The animation case the moving line was not: each region turns wet
or dry on its own calendar, and a still needs twelve maps nobody reads.

WE COMPUTE NOTHING (science's condition, binding). The pattern is Lenssen,
Goddard and Mason (2020), Weather and Forecasting 35(6), 2387-2406: the
odds that a 3-month season falls in the wet or dry third of its history,
given El Nino, CRU TS4.07 1951-2022, masked to signals significant at 85%.
Read from the 24 maps captured from IRI on 2026-10-12, because IRI's Data
Library is shutting down and the data now sits behind a sign-in. Nothing
here fetches.

WHAT THE IRI MAPS ARE USED FOR, AND WHAT THEY ARE NOT. They are 504x288
images: good enough to confirm a region is shaded in a season, not to draw a
border from (science). So:
  - the REGIONS are science's nine (research/enso_rain_signal.md), drawn as
    outlines on our own basemap and clipped to land, so they follow real
    coastlines;
  - the SEASONS each region is drawn in come from the IRI maps: a region is
    on in a season when enough of its land is shaded in the matching
    direction. That table is printed and saved so it can be checked;
  - a check image overlays our outlines on IRI's shading, region by region.

THE BASEMAP IS THE SITE'S. docs/world-map.svg, VD's 800x400 equirectangular
world in house colours, the projection the front-page map already uses. A
flip-book of IRI's own GIFs would be someone else's default styling in
motion, which is the generic look Kristjan keeps sending back.

  .venv/bin/python design/make_rain_calendar.py table    # region x season
  .venv/bin/python design/make_rain_calendar.py check    # outlines on IRI
  .venv/bin/python design/make_rain_calendar.py render   # the GIF
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

IRI = ROOT / "research/sources/iri_enso_prcp_2026-10-12"
OUT = Path("/private/tmp/claude-505/"
           "-Users-admin-Documents-Claude-Projects-El-Nino-Tracker/"
           "963b8065-d8cb-408a-9195-33d00aeda096/scratchpad/rain_out")

SEASONS = ["Jan-Mar", "Feb-Apr", "Mar-May", "Apr-Jun", "May-Jul", "Jun-Aug",
           "Jul-Sep", "Aug-Oct", "Sep-Nov", "Oct-Dec", "Nov-Jan", "Dec-Feb"]
LONG = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
        "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
        "Sep": "September", "Oct": "October", "Nov": "November",
        "Dec": "December"}

# Science's nine regions, research/enso_rain_signal.md. Each is one or more
# lon/lat boxes; what is drawn is the LAND inside them, so the shapes follow
# coastlines. (name, short label, signal, boxes, science's named seasons).
#
# THE SEASONS ARE SCIENCE'S, CONFIRMED ON IRI, NOT DERIVED FROM IRI. Read
# straight off the IRI maps with a share threshold, most regions are shaded
# in most seasons (northern Brazil in all twelve), so the seasons would be a
# product of a threshold design picked, which is computing, and science's
# condition is that we compute nothing. So each region is drawn in the
# seasons science names, and only where IRI confirms the signal there.
REGIONS = [
    ("Indonesia, Philippines, northern Australia", "Indonesia to N Australia",
     "dry", [(95, 141, -11, 20), (113, 150, -26, -11)],
     # Science: dry in BOTH CPC seasons (Jun-Aug and Dec-Feb), strongest
     # Aug-Nov: one continuous stretch, June to February. The first list
     # named only the anchor seasons, which drew the region on in Jun-Aug,
     # off in Jul-Sep, on again in Aug-Oct: a flicker that reads as noise.
     # IRI confirms every season in the stretch, 34% to 51%.
     ["Jun-Aug", "Jul-Sep", "Aug-Oct", "Sep-Nov", "Oct-Dec", "Nov-Jan",
      "Dec-Feb"]),
    ("Southeastern Africa", "Southeast Africa", "dry",
     [(25, 41, -27, -9)], ["Dec-Feb"]),
    ("Northern Brazil", "Northern Brazil", "dry",
     [(-63, -35, -10, 3)], ["Dec-Feb"]),
    ("India", "India", "dry", [(68, 88, 8, 30)], ["Jun-Aug", "Jul-Sep"]),
    ("Coastal Ecuador and northern Peru", "Ecuador and N Peru", "wet",
     [(-81.5, -78, -7, 1)], ["Jan-Mar", "Feb-Apr"]),
    ("Southern Brazil to central Argentina", "S Brazil to Argentina", "wet",
     [(-65, -48, -38, -25)], ["Sep-Nov"]),
    ("US Gulf Coast and southeast", "US Gulf Coast", "wet",
     [(-98, -76, 25, 35)], ["Dec-Feb"]),
    ("Horn of Africa", "Horn of Africa", "wet",
     [(34, 51, -5, 10)], ["Oct-Dec"]),
    ("Central America", "Central America", "dry",
     [(-92, -77, 7, 18)], ["Jun-Aug"]),
]
ON_SHARE = 0.20      # IRI confirms a named season when >= 20% of land shades

# Where each label sits relative to its region, so the summary frame, which
# shows all nine at once, does not stack labels on each other or on the
# region they name. (lon, lat, ha) of the label anchor.
LABEL_AT = {
    # South of Australia, over open ocean, directly under its own region.
    # Two earlier spots failed: east of the Philippines ran off the frame,
    # and the Indian Ocean put it beside Madagascar, where in Dec-Feb it
    # read as a second Southeast Africa label.
    "Indonesia, Philippines, northern Australia": (176, -38, "right"),
    "Southeastern Africa": (21, -22, "right"),
    "Northern Brazil": (-49, 9, "center"),
    "India": (78, 33, "center"),
    "Coastal Ecuador and northern Peru": (-86, -4, "right"),
    "Southern Brazil to central Argentina": (-44, -33, "left"),
    "US Gulf Coast and southeast": (-87, 38, "center"),
    "Horn of Africa": (55, 3, "left"),
    "Central America": (-96, 12, "right"),
}


# ---- the basemap ------------------------------------------------------------

def land_polygons():
    """docs/world-map.svg as lon/lat polygons. 800x400 equirectangular."""
    svg = (ROOT / "docs/world-map.svg").read_text()
    polys = []
    for d in re.findall(r'<path d="([^"]+)"', svg):
        for ring in re.split(r"(?=M)", d):
            pts = re.findall(r"(-?[\d.]+),(-?[\d.]+)", ring)
            if len(pts) >= 3:
                xy = np.array(pts, dtype=float)
                polys.append(np.column_stack([xy[:, 0] / 800 * 360 - 180,
                                              90 - xy[:, 1] / 400 * 180]))
    return polys


def land_path(polys):
    """One compound matplotlib Path of all land, for clipping and testing."""
    from matplotlib.path import Path as MPath
    verts, codes = [], []
    for p in polys:
        verts.extend(p.tolist() + [p[0].tolist()])
        codes.extend([MPath.MOVETO] + [MPath.LINETO] * (len(p) - 1)
                     + [MPath.CLOSEPOLY])
    return MPath(np.array(verts), codes)


# ---- reading IRI's maps -----------------------------------------------------

# GEOREFERENCED FROM THE AXIS TICKS, NOT THE FRAME. The first version took
# the black border (x 52-499, y 24-255) as 180W-180E and 90N-90S. It is not:
# the plot sits about 8 px inside it on every side, and drawing our
# coastlines over IRI's showed them drifting apart going south, with
# Antarctica and the tip of South America visibly lower on IRI's map. The
# coastal Ecuador region read 0% in all twelve seasons because IRI's red
# blob sat just outside our box.
#
# The ticks are the truth: one every 12 px on both axes, 10 degrees each,
# so 1.2 px per degree in both directions. 90N is y 32, 90S y 248; 180W is
# x 60, 180E x 492. Verified in every file, not trusted.
LON_PX = (60.0, 492.0)       # 180W, 180E
LAT_PX = (32.0, 248.0)       # 90N, 90S


def _ticks(black):
    def runs(v):
        out = []
        for i in v:
            if out and i - out[-1][-1] <= 1:
                out[-1].append(i)
            else:
                out.append([i])
        return [float(np.mean(r)) for r in out]
    ys = runs([y for y in range(26, 254) if black[y, 53:57].all()])
    xs = runs([x for x in range(54, 498) if black[250:254, x].all()])
    return xs, ys


def iri_shaded(season, anomaly):
    """(lon, lat, shaded) for one IRI map's pixels inside the plot area."""
    from PIL import Image
    a = np.asarray(Image.open(IRI / f"{season}_{anomaly}.gif").convert("RGB"),
                   dtype=int)
    black = a.sum(2) < 150
    xs, ys = _ticks(black)
    if (not xs or not ys or abs(xs[0] - LON_PX[0]) > 0.6
            or abs(xs[-1] - LON_PX[1]) > 0.6 or abs(ys[0] - LAT_PX[0]) > 0.6
            or abs(ys[-1] - LAT_PX[1]) > 0.6 or len(xs) != 37 or len(ys) != 19):
        raise SystemExit(f"{season} {anomaly}: axis ticks are not where they "
                         f"were measured ({len(xs)} x, {len(ys)} y). "
                         f"Re-calibrate before trusting any region.")
    x0, x1 = int(LON_PX[0]), int(LON_PX[1])
    y0, y1 = int(LAT_PX[0]), int(LAT_PX[1])
    sub = a[y0:y1 + 1, x0:x1 + 1]
    shaded = (sub.max(2) - sub.min(2)) > 60          # saturated = coloured
    ys_, xs_ = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    lon = (xs_ - LON_PX[0]) / (LON_PX[1] - LON_PX[0]) * 360 - 180
    lat = 90 - (ys_ - LAT_PX[0]) / (LAT_PX[1] - LAT_PX[0]) * 180
    return lon, lat, shaded


def table():
    """Share of each region's land shaded, per season, in its direction."""
    lp = land_path(land_polygons())
    anomaly = {"wet": "Above_Normal", "dry": "Below_Normal"}
    rows = {}
    for name, _short, signal, boxes, _named in REGIONS:
        shares = []
        for s in SEASONS:
            lon, lat, sh = iri_shaded(s, anomaly[signal])
            inbox = np.zeros_like(sh)
            for lo0, lo1, la0, la1 in boxes:
                inbox |= (lon >= lo0) & (lon <= lo1) & (lat >= la0) & (lat <= la1)
            pts = np.column_stack([lon[inbox], lat[inbox]])
            onland = lp.contains_points(pts) if len(pts) else np.array([])
            n = int(onland.sum())
            shares.append(float(sh[inbox][onland].sum() / n) if n else 0.0)
        rows[name] = {"signal": signal, "share": shares,
                      "on": [x >= ON_SHARE for x in shares]}
    return rows


def print_table(rows):
    print("%-40s %-4s " % ("region", "") + " ".join(s[:3] for s in SEASONS))
    for name, r in rows.items():
        cells = " ".join(("%3d" % round(x * 100)) + ("*" if on else " ")
                         for x, on in zip(r["share"], r["on"]))
        print("%-40s %-4s %s" % (name[:40], r["signal"], cells))
    print(f"\n% of region's land shaded at 85% significance; * = drawn "
          f"(>= {ON_SHARE:.0%})")


def plan(rows):
    """{season: [region]} to draw, and the named seasons IRI did NOT confirm."""
    on, unconfirmed = {s: [] for s in SEASONS}, []
    for reg in REGIONS:
        name, named = reg[0], reg[4]
        for sn in named:
            share = rows[name]["share"][SEASONS.index(sn)]
            if share >= ON_SHARE:
                on[sn].append(reg)
            else:
                unconfirmed.append((name, sn, share))
    return on, unconfirmed


def _spans(seasons):
    """Overlapping 3-month seasons as month spans: Jun-Aug, Aug-Oct and
    Sep-Nov are one stretch, June to November, and listing them separately
    read as four events and ran India's label into Indonesia's."""
    M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
         "Oct", "Nov", "Dec"]
    months = set()
    for sn in seasons:
        a, b = (M.index(x) for x in sn.split("-"))
        months |= set(range(a, b + 1) if a <= b else [*range(a, 12), *range(0, b + 1)])
    if len(months) == 12:
        return ["all year"]
    # walk the year from a month that is OFF, so a span crossing December
    # stays whole
    start = next(i for i in range(12) if i not in months)
    out, run = [], []
    for k in range(1, 13):
        i = (start + k) % 12
        if i in months:
            run.append(i)
        elif run:
            out.append(run); run = []
    if run:
        out.append(run)
    return [M[r[0]] if len(r) == 1 else f"{M[r[0]]}-{M[r[-1]]}" for r in out]


def _season_words(sn):
    a, b = sn.split("-")
    return f"{LONG[a]} to {LONG[b]}"


WET, DRY = "#417785", "#B8862E"     # proposal for VD; no house pair exists


def render(fps=5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # frames are grabbed and saved by hand below; see the palette note
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path as MPath
    import tokens as T

    rows = table()
    on, unconfirmed = plan(rows)
    polys = land_polygons()
    lpath = land_path(polys)

    fig = plt.figure(figsize=(12, 6.7), dpi=100)
    fig.patch.set_facecolor("#F5F4EE")
    ax = fig.add_axes([0.03, 0.19, 0.94, 0.62])
    ax.set_xlim(-170, 180); ax.set_ylim(-45, 62)
    ax.set_aspect("equal"); ax.axis("off")
    land = PathPatch(lpath, facecolor="#CFCDC2", edgecolor="#B8B6AB",
                     lw=0.4, zorder=1)
    ax.add_patch(land)

    # SOFT EDGES, NOT BOXES. The first render clipped hard rectangles to
    # land, so every inland edge was a ruler line (India's northern border,
    # southeast Africa's west), which looked like boxes because it was, and
    # claimed a precision the source does not have: science's rule is that
    # IRI's images can confirm a region, not draw its border. So each region
    # fades out over about three degrees, clipped to land: approximately
    # here, which is what the evidence supports.
    from matplotlib.colors import to_rgb
    glon = np.arange(-170, 180.01, 0.25)
    glat = np.arange(-45, 62.01, 0.25)
    GL, GA = np.meshgrid(glon, glat)

    def soft(boxes):
        # The fade scales with the region. A fixed 1.6 degree fade nearly
        # erased coastal Ecuador, which is only 3.5 degrees wide: it faded
        # out over about its own width and read as a smudge.
        f = np.zeros_like(GL)
        for lo0, lo1, la0, la1 in boxes:
            w = min(1.6, 0.15 * min(lo1 - lo0, la1 - la0))
            sx = (1 / (1 + np.exp(-(GL - lo0) / w))) * (1 / (1 + np.exp((GL - lo1) / w)))
            sy = (1 / (1 + np.exp(-(GA - la0) / w))) * (1 / (1 + np.exp((GA - la1) / w)))
            f = np.maximum(f, sx * sy)
        return f

    fills, labels = {}, {}
    for reg in REGIONS:
        name, short, sig, boxes, named = reg
        rgba = np.zeros(GL.shape + (4,))
        rgba[..., :3] = to_rgb(WET if sig == "wet" else DRY)
        rgba[..., 3] = 0.92 * soft(boxes)
        im = ax.imshow(rgba, origin="lower", extent=[glon[0], glon[-1],
                       glat[0], glat[-1]], interpolation="bilinear", zorder=2)
        im.set_clip_path(land)
        im.set_visible(False)
        fills[name] = im
        lx, ly, ha = LABEL_AT[name]
        labels[name] = ax.text(lx, ly, "", ha=ha, va="center", fontsize=10.5,
                               color=T.INK, zorder=4, linespacing=1.15,
                               visible=False)
        labels[name]._tls = (short, sig, named)

    empty = fig.text(0.5, 0.48, "", ha="center", va="center", fontsize=13,
                     color=T.INK_SOFT, style="italic")

    title = fig.text(0.05, 0.93, "", fontsize=22, color=T.INK)
    fig.text(0.05, 0.882, "What El Ni\u00f1o usually does to rain, from "
             "published research. Not a forecast for this year.",
             fontsize=12, color=T.INK_SOFT)
    # Legend: odds, not outcomes.
    for i, (c, t) in enumerate(((WET, "Tends to be wetter than normal in "
                                 "El Ni\u00f1o years"),
                                (DRY, "Tends to be drier"))):
        x = 0.05 + i * 0.36
        fig.patches.append(Rectangle((x, 0.828), 0.014, 0.024, transform=fig.transFigure,
                                     facecolor=c, edgecolor="none"))
        fig.text(x + 0.02, 0.84, t, fontsize=10.5, color=T.INK_SOFT, va="center")

    # THE MONTH STRIP. Twelve months along the bottom with the current
    # three-month season marked: this is what makes the motion read as a
    # calendar that repeats, rather than as this El Nino unfolding, which
    # science's conditions rule out.
    MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
            "Oct", "Nov", "Dec"]
    mx0, mw = 0.05, 0.9 / 12
    marks = []
    for i, m in enumerate(MON3):
        r = Rectangle((mx0 + i * mw + 0.002, 0.125), mw - 0.004, 0.007,
                      transform=fig.transFigure, facecolor="#D9D8D2",
                      edgecolor="none")
        fig.patches.append(r)
        marks.append(r)
        fig.text(mx0 + i * mw + mw / 2, 0.142, m, ha="center", fontsize=10,
                 color=T.INK_FAINT)

    fig.text(0.05, 0.03,
             "Source: Lenssen, Goddard and Mason (2020), Weather and Forecasting "
             "35(6). Rain-gauge records (CRU TS4.07), 1951-2022. Regions drawn "
             "only where the El Ni\u00f1o signal\nis significant at 85%, in the "
             "season the published research names. A tendency over many El Ni"
             "\u00f1os, not a prediction. The Long Swell.",
             fontsize=8.6, color=T.INK_FAINT, linespacing=1.45)

    def show(active, season):
        for name in fills:
            vis = name in active
            fills[name].set_visible(vis)
            lab = labels[name]
            short, sig, named = lab._tls
            word = "wetter" if sig == "wet" else "drier"
            if season is None:
                # The summary must stand alone as a still, so each label
                # carries its own season.
                lab.set_text(f"{short}\n{word}, "
                             f"{', '.join(_spans(drawn_seasons[name]))}")
            else:
                lab.set_text(f"{short}\n{word}")
            lab.set_visible(vis)
        # A season with nothing drawn says why, rather than showing an empty
        # map that reads as "El Nino does nothing to rain now". IRI shades
        # signals in those seasons too; these regions' PEAKS are elsewhere.
        empty.set_text("" if (active or season is None) else
                       "None of these nine regions has its main\n"
                       "El Ni\u00f1o rain season in these months.")
        if season is None:
            title.set_text("El Ni\u00f1o's rain year, at a glance")
            for r in marks:
                r.set_facecolor(T.INK)
        else:
            title.set_text(_season_words(season))
            a, b = season.split("-")
            i0, i1 = MON3.index(a), MON3.index(b)
            idx = ([*range(i0, i1 + 1)] if i0 <= i1
                   else [*range(i0, 12), *range(0, i1 + 1)])
            for i, r in enumerate(marks):
                r.set_facecolor(T.INK if i in idx else "#D9D8D2")

    drawn_seasons = {r[0]: [sn for sn in SEASONS if r in on[sn]] for r in REGIONS}

    seq = [(sn, {r[0] for r in on[sn]}) for sn in SEASONS]
    summary = {r[0] for sn in SEASONS for r in on[sn]}

    # WRITTEN FRAME BY FRAME WITH ONE SHARED PALETTE, DITHERED. matplotlib's
    # PillowWriter gave each frame its own 256-colour palette with no
    # dithering, and the soft region edges broke into visible concentric
    # bands in the GIF while the PNG still was smooth. One palette, taken
    # from the summary frame because it holds every region's gradient, then
    # Floyd-Steinberg onto it: smooth fades, and no colour shift between
    # frames. Durations are set per frame, so a held frame is one frame.
    from PIL import Image as PImage

    def grab():
        fig.canvas.draw()
        return PImage.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())

    shots = []
    for sn, act in seq:
        show(act, sn)
        shots.append(grab())
    show(summary, None)
    shots.append(grab())
    pal = shots[-1].quantize(colors=256, method=PImage.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=pal, dither=PImage.Dither.FLOYDSTEINBERG)
              for im in shots]
    durations = [1300] * len(seq) + [4000]

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "rain_calendar.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=False)
    show(summary, None)
    fig.savefig(OUT / "rain_calendar_final.png", facecolor="#F5F4EE")
    show(seq[9][1], seq[9][0])                       # Oct-Dec, for the check
    fig.savefig(OUT / "rain_calendar_octdec.png", facecolor="#F5F4EE")
    plt.close(fig)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    for sn, act in seq:
        print(f"  {sn}: {', '.join(sorted(act)) or '(no region)'}")
    for name, sn, sh in unconfirmed:
        print(f"  NOT DRAWN: {name} {sn}, named by science but IRI shades "
              f"only {sh:.0%} of it at 85%")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "table":
        rows = table()
        print_table(rows)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "season_table.json").write_text(json.dumps(rows, indent=1))
    elif cmd == "render":
        render()
    else:
        print(__doc__)
