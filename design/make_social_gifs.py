"""Social GIFs for "How a flood is made" (LinkedIn and X), Kristjan, 16 Oct.

  weekend      the coming weekend in ECMWF's forecast: the warm sea, the
               cold air 5 km up arriving, the wind 1.5 km up turning
               onshore at Valencia and Barcelona. Same layers as the page's
               forecast act, drawn flat and square for a feed.
  ingredients  the five ingredients in sequence, from the page's own data:
               the summer's heat May to September, the record sea, the
               water vapour record, the pump (27 Sep to 3 Oct), the ground.

Every figure comes from the explainer's assets (design/make_explainer_assets.py,
from FLO's payload); the forecast is labelled as ECMWF's with its run time.
Square 1080 px, under 8 MB each (LinkedIn's GIF ceiling; X allows 15).
Output goes to OUT (first argument), outside the repo.

Run:  .venv/bin/python design/make_social_gifs.py OUT_DIR [weekend|ingredients|all]
"""
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T                                     # noqa: E402

ASSETS = Path("/tmp/el_nino_preview/explainer3d/assets")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
WHICH = sys.argv[2] if len(sys.argv) > 2 else "all"
# "weekend-es": the Spanish edition of the weekend GIF (the explainer's
# Spanish page is for Spain, and so is this weekend's storm).
ES = {"kicker": "ESTE FIN DE SEMANA · PREVISIÓN DEL ECMWF",
      "sub": "previsión: aire frío a 5 km (azul), viento a 1,5 km · medido: mar, 8-12 oct. (ERA5)",
      "foot": "ECMWF IFS, pasada %s UTC · no es previsión nuestra · AEMET: «elevada incertidumbre»",
      "arrow": "hacia la costa · del %s · %s m/s",
      "days": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
      "mon": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
      "compass": ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]}
S = 960
F = ROOT / "assets/fonts"
def font(name, size):
    return ImageFont.truetype(str(F / name), size)
SERIF = "spectral/Spectral-Medium.ttf"
SERIF_I = "spectral/Spectral-Italic.ttf"
MONO = "ibm-plex-mono/IBMPlexMono-Regular.ttf"
MONO_M = "ibm-plex-mono/IBMPlexMono-Medium.ttf"
PAPER, INK, SOFT = T.PAPER, T.INK, T.INK_SOFT
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def save_gif(frames, path, ms, hold_last=0):
    """Adaptive palette per frame; the last frame held hold_last ms."""
    q = [f.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
         for f in frames]
    dur = [ms] * len(q)
    if hold_last:
        dur[-1] = hold_last
    q[0].save(path, save_all=True, append_images=q[1:], duration=dur, loop=0, optimize=True, disposal=1)
    return path.stat().st_size / 1e6


# --- the map, shared by both GIFs -----------------------------------------
P = json.loads((ASSETS / "pump.json").read_text())
LON0, LON1 = P["extent"]["lon"]
LAT0, LAT1 = P["extent"]["lat"]
TPX = 42                                     # texture pixels per degree (make_explainer_assets.PX)
BOX = (-10.5, 11.0, 34.0, 50.2)               # lon0, lon1, lat0, lat1 for the square map
COSL = math.cos(math.radians((BOX[2] + BOX[3]) / 2))


def crop(img, scale=1.0):
    """The BOX out of a full-extent texture, cos-corrected, to S x S."""
    lo0, lo1, la0, la1 = BOX
    k = TPX * scale
    box = (int((lo0 - LON0) * k), int((LAT1 - la1) * k), int((lo1 - LON0) * k), int((LAT1 - la0) * k))
    return img.crop(box).resize((S, S), Image.BICUBIC)


def MX(lo): return (lo - BOX[0]) / (BOX[1] - BOX[0]) * S
def MY(la): return (BOX[3] - la) / (BOX[3] - BOX[2]) * S


def set_box(b):
    """Change the map window. The measured pump needs the Atlantic: the cold
    pool sat at 15-31W, outside the Iberia window the weekend uses."""
    global BOX
    BOX = b


def wind_at(W, frames, t0, step, lo, la, tm):
    lat, lon = W["lat"], W["lon"]
    fi = (lat[0] - la) / (lat[0] - lat[1]); fj = (lo - lon[0]) / (lon[1] - lon[0])
    i, j = int(math.floor(fi)), int(math.floor(fj))
    if i < 0 or j < 0 or i >= len(lat) - 1 or j >= len(lon) - 1:
        return None
    di, dj = fi - i, fj - j
    ft = max(0.0, min(len(frames) - 1.0001, (tm - t0) / step))
    k = int(ft); dk = ft - k
    def s(g):
        return g[i][j] * (1 - di) * (1 - dj) + g[i + 1][j] * di * (1 - dj) + g[i][j + 1] * (1 - di) * dj + g[i + 1][j + 1] * di * dj
    a, b = frames[k], frames[min(k + 1, len(frames) - 1)]
    return (s(a["u"]) * (1 - dk) + s(b["u"]) * dk, s(a["v"]) * (1 - dk) + s(b["v"]) * dk)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class Flow:
    """Wind particles with fading trails, in lon/lat, drawn on an RGBA layer."""
    def __init__(self, n=1800, seed=3):
        self.r = random.Random(seed)
        self.p = [self.spawn({}) for _ in range(n)]
        self.trail = np.zeros((S, S), dtype=np.float32)
    def spawn(self, p):
        p.update(lo=self.r.uniform(BOX[0], BOX[1]), la=self.r.uniform(BOX[2], BOX[3]), age=0,
                 life=self.r.uniform(1.2, 3.0))
        return p
    def step(self, wind, dt):
        self.trail *= 0.80
        img = Image.fromarray(np.zeros((S, S), dtype=np.uint8))
        d = ImageDraw.Draw(img)
        for p in self.p:
            w = wind(p["lo"], p["la"])
            p["age"] += dt
            if w is None or p["age"] > p["life"] or not (BOX[0] <= p["lo"] <= BOX[1] and BOX[2] <= p["la"] <= BOX[3]):
                self.spawn(p); continue
            x0, y0 = MX(p["lo"]), MY(p["la"])
            p["lo"] += w[0] * 0.11 * dt / math.cos(math.radians(p["la"])); p["la"] += w[1] * 0.11 * dt
            sp = math.hypot(*w)
            d.line([(x0, y0), (MX(p["lo"]), MY(p["la"]))], fill=int(min(255, 90 + sp * 14)), width=2)
        self.trail = np.maximum(self.trail, np.asarray(img, dtype=np.float32))
    def layer(self, colour=INK, strength=0.85):
        a = (self.trail * strength).clip(0, 255).astype(np.uint8)
        lay = Image.new("RGBA", (S, S), rgb(colour) + (0,))
        lay.putalpha(Image.fromarray(a))
        return lay


def arrow(d, lo, la, u, v, label, scale=1.0):
    """A bold onshore arrow ending at (lo, la), pointing along the wind."""
    m = math.hypot(u, v) or 1
    ux, uy = u / m, -v / m                      # screen: y down
    L = (60 + m * 7) * scale
    hx, hy = MX(lo), MY(la)
    tx, ty = hx - ux * L, hy - uy * L
    d.line([(tx, ty), (hx - ux * 22, hy - uy * 22)], fill=INK, width=9)
    px, py = -uy, ux
    d.polygon([(hx, hy), (hx - ux * 30 + px * 15, hy - uy * 30 + py * 15),
               (hx - ux * 30 - px * 15, hy - uy * 30 - py * 15)], fill=INK)
    f = font(MONO_M, 22)
    w = d.textlength(label, font=f)
    bx, by = min(S - 24 - w, max(24, tx - w / 2)), max(hy, ty) + 26   # kept inside the frame
    d.rectangle([bx - 8, by - 6, bx + w + 8, by + 30], fill=INK)
    d.text((bx, by), label, font=f, fill=PAPER)


def onshore(w, lo_deg, hi_deg):
    if not w:
        return None
    sp = math.hypot(*w)
    frm = (math.degrees(math.atan2(-w[0], -w[1])) + 360) % 360
    return (sp, frm) if lo_deg <= frm <= hi_deg and sp >= 8 else None


def header(d, kicker, title, sub=None):
    d.rectangle([0, 0, S, 156], fill=PAPER)
    d.text((40, 30), kicker, font=font(MONO_M, 20), fill=SOFT)
    d.text((40, 56), title, font=font(SERIF, 52), fill=INK)
    if sub:
        d.text((40, 122), sub, font=font(MONO, 17), fill=SOFT)


def footer(d, text, size=None):
    z = size or S
    d.rectangle([0, z - 84, z, z], fill=PAPER)
    size = 16 if z == S else 18
    while size > 11 and d.textlength(text, font=font(MONO, size)) > z - 80:   # fit, never clip
        size -= 1
    d.text((40, z - 74), text, font=font(MONO, size), fill=SOFT)
    d.text((40, z - 44), "thelongswell.com", font=font(MONO_M, 20 if z == S else 22), fill=INK)


def cities(d):
    for name, lo, la, right in [("Barcelona", 2.17, 41.39, False), ("Valencia", -0.38, 39.47, False),
                                ("Madrid", -3.70, 40.42, False)]:
        x, y = MX(lo), MY(la)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=INK)
        f = font(SERIF, 26)
        w = d.textlength(name, font=f)
        d.text((x - 12 - w, y - 16) if not right else (x + 12, y - 16), name, font=f, fill=INK,
               stroke_width=3, stroke_fill=PAPER)


# --- GIF 1: the coming weekend ---------------------------------------------
def weekend(lang="en"):
    wk = P["weekend"]
    sea = crop(Image.open(ASSETS / wk["sea"]["img"]).convert("RGB"))
    colds = [crop(Image.open(ASSETS / f["img"]).convert("RGBA"), 0.5) for f in wk["cold"]["frames"]]
    times = [ts(f["time"]) for f in wk["cold"]["frames"]]
    W, WF = wk["wind"], wk["wind"]["frames"]
    t0w, stw = ts(WF[0]["time"]), ts(WF[1]["time"]) - ts(WF[0]["time"])
    start, end = ts("2026-10-16T00:00:00+00:00"), ts("2026-10-19T12:00:00+00:00")
    run = wk["run"][:16].replace("T", " ")
    flow = Flow()
    N, out = 56, []
    for fi in range(N + 12):                     # 12 warm-up frames, not kept
        f = max(0, fi - 12)
        tm = start + (end - start) * f / (N - 1)
        wind = lambda lo, la: wind_at(W, WF, t0w, stw, lo, la, tm)
        flow.step(wind, 1 / 10)
        if fi < 12:
            continue
        k = max(0, min(len(times) - 2, int((tm - times[0]) // (times[1] - times[0]))))
        a = (tm - times[k]) / (times[k + 1] - times[k])
        frame = sea.copy().convert("RGBA")
        cold = Image.blend(colds[k], colds[k + 1], max(0, min(1, a)))
        frame = Image.alpha_composite(frame, cold)
        frame = Image.alpha_composite(frame, flow.layer())
        d = ImageDraw.Draw(frame)
        cities(d)
        for (lo, la, lo_d, hi_d) in [(3.0, 41.0, 100, 165), (0.0, 39.0, 68, 140)]:
            o = onshore(wind(lo, la), lo_d, hi_d)
            if o:
                sp, frm = o
                w = wind(lo, la)
                lab = ("onshore · from the %s · %.0f m/s" % (COMPASS[round(frm / 45) % 8], sp) if lang == "en"
                       else ES["arrow"] % (ES["compass"][round(frm / 45) % 8], "%.0f" % sp))
                arrow(d, lo - 0.25, la + 0.1, w[0], w[1], lab)
        dt = datetime.fromtimestamp(round((tm - times[0]) / 43200) * 43200 + times[0], timezone.utc)
        if lang == "en":
            header(d, "THIS WEEKEND · ECMWF FORECAST", "%s %d %s, %02d:00 UTC" % (dt.strftime("%a"), dt.day, MON[dt.month - 1], dt.hour),
                   "forecast: cold air 5 km up (blue), wind 1.5 km up · measured: sea, 8-12 Oct (ERA5)")
            footer(d, "ECMWF IFS run %s UTC, not a forecast of ours · AEMET: “elevada incertidumbre”" % run)
        else:
            header(d, ES["kicker"], "%s %d %s, %02d:00 UTC" % (ES["days"][dt.weekday()], dt.day, ES["mon"][dt.month - 1], dt.hour),
                   ES["sub"])
            rd = datetime.fromisoformat(wk["run"])
            footer(d, ES["foot"] % ("%d %s %02d:%02d" % (rd.day, ES["mon"][rd.month - 1], rd.hour, rd.minute)))
        out.append(frame)
    return save_gif(out, OUT / ("weekend_forecast.gif" if lang == "en" else "prevision_fin_de_semana.gif"), 100, hold_last=2500)


# --- GIF 2: the ingredients over time --------------------------------------
C = 1080                                    # drawn panels are laid out at 1080, then scaled to S
def done(im):
    return im if im.size[0] == S else im.resize((S, S), Image.LANCZOS)


def card(word, n, question):
    im = Image.new("RGB", (C, C), PAPER)
    d = ImageDraw.Draw(im)
    d.text((80, 360), n, font=font(MONO_M, 30), fill=INK)
    d.text((72, 395), word, font=font(SERIF, 230), fill=INK)
    d.text((80, 680), question, font=font(SERIF_I, 44), fill=SOFT)
    footer(d, "How a flood is made · Barcelona, 3 October 2026")
    return im


def ingredients():
    frames, durs = [], []
    def add(im, ms):
        frames.append(done(im)); durs.append(ms)

    # 1. Rain
    add(card("Rain", "01", "How much is 159 millimetres?"), 1400)
    for i in range(10):
        f = i / 9
        im = Image.new("RGB", (C, C), PAPER); d = ImageDraw.Draw(im)
        mm = 159.1 * (1 - (1 - f) ** 2)
        d.text((80, 230), "%.1f mm" % mm, font=font(MONO_M, 120), fill=INK)
        d.text((84, 380), "%d litres on one square metre" % round(mm), font=font(MONO, 28), fill=SOFT)
        # the tray, to scale: 1 m square drawn 600 px, so 20 cm walls = 120 px
        x0, x1, base = 240, 840, 860
        d.rectangle([x0, base - int(120 * mm / 200), x1, base], fill=rgb(T.FLOOD))
        d.line([(x0, base - 120), (x0, base), (x1, base), (x1, base - 120)], fill=INK, width=4)
        d.text((x0, base + 18), "1 m square, 20 cm walls, to scale", font=font(MONO, 22), fill=SOFT)
        footer(d, "Barcelona, Fabra observatory, 3 October 2026 · AEMET", C)
        add(im, 120 if i < 9 else 1600)

    # 2. Heat, May to September
    add(card("Heat", "02", "How hot did the summer get?"), 1400)
    M = json.loads((ASSETS / "heat_morph.json").read_text())
    lines = Image.open(ASSETS / M["lines"]).convert("RGBA")
    ramp = np.array([rgb(h) for h in M["ramp"]], dtype=float)
    def colour(v):
        x = (np.clip(v / M["full_c"], -1, 1) + 1) * 4
        i = np.clip(np.floor(x).astype(int), 0, 7); fr = (x - i)[..., None]
        return ramp[i] * (1 - fr) + ramp[i + 1] * fr
    grids = [np.array([[np.nan if v is None else v for v in r] for r in m["grid"]], dtype=float) for m in M["months"]]
    land = np.array(rgb(T.PAPER_SUNK), dtype=float)
    steps = 4
    for k in range(len(grids) - 1):
        for s in range(steps if k < len(grids) - 2 else steps + 1):
            t = s / steps
            g = grids[k] + (grids[k + 1] - grids[k]) * t
            img = np.where(np.isnan(g)[..., None], land, colour(np.nan_to_num(g)))
            im = Image.fromarray(img.astype(np.uint8)).resize(lines.size, Image.BILINEAR).convert("RGBA")
            im = Image.alpha_composite(im, lines)
            canvas = Image.new("RGB", (C, C), PAPER)
            mp = im.resize((780, int(780 * im.height / im.width)), Image.BICUBIC)
            canvas.paste(mp, (150, 176), mp)
            d = ImageDraw.Draw(canvas)
            month = M["months"][round(k + t)]["month"]
            d.text((90, 60), "%s 2026" % month, font=font(MONO_M, 52), fill=INK)
            d.text((92, 128), "temperature against the same month, 1991-2020 · ERA5", font=font(MONO, 20), fill=SOFT)
            footer(d, "sea surface over the sea, 2 m air over land · scale ±3 °C")
            add(canvas, 150 if not (k == len(grids) - 2 and s == steps) else 1600)

    # 3. Sea
    add(card("Sea", "03", "Where did the water come from?"), 1400)
    wm_t = (23.6, 26.0)
    for i in range(8):
        im = Image.new("RGB", (C, C), PAPER); d = ImageDraw.Draw(im)
        for j, (t, top, deep, label) in enumerate([(wm_t[0], "#417785", "#0A4A57", "normal September"),
                                                    (wm_t[1], "#C05B3D", "#5E1806", "September 2026")]):
            x0 = 60 + j * 500
            for y in range(560, 960):
                c = np.array(rgb(top)) * (1 - (y - 560) / 400) + np.array(rgb(deep)) * ((y - 560) / 400)
                d.line([(x0, y), (x0 + 460, y)], fill=tuple(c.astype(int)))
            sky = (133, 167, 176) if j == 0 else (220, 149, 126)
            for y in range(300, 560):
                f2 = (y - 300) / 260
                c = np.array(rgb(PAPER)) * (1 - f2) + np.array(sky) * f2 * 0.7 + np.array(rgb(PAPER)) * f2 * 0.3
                d.line([(x0, y), (x0 + 460, y)], fill=tuple(c.astype(int)))
            r = random.Random(i * 7 + j)
            for _ in range(70 if j else 48):
                px, py = x0 + r.uniform(10, 450), r.uniform(310, 552)
                d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(250, 251, 251))
            d.text((x0, 180), "%.1f °C" % t, font=font(MONO_M, 72), fill=INK)
            d.text((x0, 140), label.upper(), font=font(MONO_M, 22), fill=SOFT)
        d.text((60, 70), "Western Mediterranean", font=font(SERIF, 48), fill=INK)
        footer(d, "September 2026: warmest in a record going back to 1940 · ERA5 · motion illustrative", C)
        add(im, 160 if i < 7 else 1600)

    # 4. Air: one dot per September since 1940
    add(card("Air", "04", "How much water can air hold?"), 1400)
    flat = json.loads((ASSETS / "flat.json").read_text())
    ser = sorted((int(y), v) for y, v in flat["vapour"]["by_year_pct"].items())
    lo_v, hi_v = min(v for _, v in ser) - 1, max(v for _, v in ser) + 1
    X = lambda y: 90 + (y - 1940) / (2026 - 1940) * 900
    Y = lambda v: 820 - (v - lo_v) / (hi_v - lo_v) * 520
    for n in list(range(4, len(ser) + 1, 4)) + [len(ser)]:
        im = Image.new("RGB", (C, C), PAPER); d = ImageDraw.Draw(im)
        d.text((90, 70), "Water vapour in the air", font=font(SERIF, 52), fill=INK)
        d.text((92, 140), "every September since 1940, % against 1991-2020 · global · ERA5", font=font(MONO, 20), fill=SOFT)
        for y, v in ser[:n]:
            if y == 2026:
                d.line([(90, Y(v)), (990, Y(v))], fill=INK, width=3)
                d.rectangle([X(y) - 10, Y(v) - 10, X(y) + 10, Y(v) + 10], fill=INK)
                d.text((X(y) - 210, Y(v) - 70), "2026: +%.1f%%" % v, font=font(MONO_M, 40), fill=INK)
            else:
                d.ellipse([X(y) - 6, Y(v) - 6, X(y) + 6, Y(v) + 6], outline=INK, width=2)
        d.text((90, 860), "1940", font=font(MONO, 22), fill=SOFT)
        d.text((950, 860), "2026", font=font(MONO, 22), fill=SOFT)
        if n == len(ser):
            d.text((90, 905), "No September in this record reaches it.", font=font(SERIF, 34), fill=INK)
        footer(d, "about 7% more water vapour per °C of warming (IPCC AR6)")
        add(im, 90 if n < len(ser) else 1800)

    # 5. Pump: 27 Sep to 3 Oct, measured
    add(card("Pump", "05", "What lifted it and set it off?"), 1400)
    keep_box = BOX
    set_box((-24.0, 9.6, 33.0, 58.0))
    sea = crop(Image.open(ASSETS / P["sea"]["img"]).convert("RGB"))
    colds = [crop(Image.open(ASSETS / f["img"]).convert("RGBA"), 0.5) for f in P["cold"]["frames"]]
    times = [ts(f["time"]) for f in P["cold"]["frames"]]
    W, WF = P["wind"], P["wind"]["frames"]
    t0w, stw = ts(WF[0]["time"]), ts(WF[1]["time"]) - ts(WF[0]["time"])
    start, end = ts("2026-09-28T00:00:00+00:00"), ts("2026-10-03T12:00:00+00:00")
    flow = Flow(seed=5)
    N = 20
    for fi in range(N + 10):
        f = max(0, fi - 10)
        tm = start + (end - start) * f / (N - 1)
        wind = lambda lo, la: wind_at(W, WF, t0w, stw, lo, la, tm)
        flow.step(wind, 1 / 10)
        if fi < 10:
            continue
        k = max(0, min(len(times) - 2, int((tm - times[0]) // (times[1] - times[0]))))
        a = (tm - times[k]) / (times[k + 1] - times[k])
        fr = Image.alpha_composite(sea.copy().convert("RGBA"), Image.blend(colds[k], colds[k + 1], max(0, min(1, a))))
        fr = Image.alpha_composite(fr, flow.layer())
        d = ImageDraw.Draw(fr)
        cities(d)
        o = onshore(wind(3.0, 41.0), 100, 165)
        if o:
            w = wind(3.0, 41.0)
            arrow(d, 2.75, 41.1, w[0], w[1], "onshore · from the %s · %.0f m/s" % (COMPASS[round(o[1] / 45) % 8], o[0]))
        dt = datetime.fromtimestamp(round((tm - times[0]) / 43200) * 43200 + times[0], timezone.utc)
        header(d, "MEASURED · ERA5", "%d %s, %02d:00 UTC" % (dt.day, MON[dt.month - 1], dt.hour),
               "cold air 5 km up (blue) · wind 1.5 km up · sea, September vs normal")
        footer(d, "ERA5, 2026 preliminary · every layer measured")
        add(fr.convert("RGB"), 160 if fi < N + 9 else 1800)
    set_box(keep_box)

    # 6. Ground, illustrative
    add(card("Ground", "06", "Why does wet ground matter?"), 1400)
    for i in range(10):
        im = Image.new("RGB", (C, C), PAPER); d = ImageDraw.Draw(im)
        t = i / 9
        for j, (label, s0) in enumerate([("dry ground", 0.12), ("already wet", 0.86)]):
            x0 = 70 + j * 500
            soil, wet = rgb("#C2B497"), rgb(T.FLOOD)
            d.rectangle([x0, 380, x0 + 330, 860], fill=soil)
            fill = min(1, s0 + t * (0.6 if j == 0 else 0.1))
            d.rectangle([x0, 380, x0 + 330, 380 + int(480 * fill)], fill=tuple(int(a * .45 + b * .55) for a, b in zip(wet, soil)))
            river = (0.04 + 0.05 * t) if j == 0 else min(0.95, 0.15 + 1.1 * t)
            d.rectangle([x0 + 350, 860 - int(400 * river), x0 + 440, 860], fill=wet)
            d.line([(x0 + 350, 460), (x0 + 350, 860), (x0 + 440, 860), (x0 + 440, 460)], fill=INK, width=3)
            d.text((x0 + 352, 870), "RIVER", font=font(MONO_M, 18), fill=INK)
            d.text((x0, 300), label.upper(), font=font(MONO_M, 26), fill=INK)
        d.text((70, 90), "Same rain on both", font=font(SERIF, 56), fill=INK)
        d.text((72, 168), "ground that is already wet takes in less of the next rain", font=font(MONO, 22), fill=SOFT)
        footer(d, "illustrative, not to scale · topsoil near the Ebro delta: 2nd wettest of 36 years (ERA5)", C)
        add(im, 140 if i < 9 else 1800)

    # close
    im = Image.new("RGB", (C, C), PAPER); d = ImageDraw.Draw(im)
    for word, x, y in [("Air", 200, 300), ("Pump", 640, 300), ("Sea", 200, 700), ("Ground", 600, 700)]:
        d.text((x, y), word, font=font(SERIF, 96), fill=INK)
    d.text((400, 500), "Heat", font=font(SERIF, 84), fill=rgb("#C05B3D"))
    for (a, b) in [((270, 690), (270, 430)), ((360, 360), (620, 360)), ((740, 430), (740, 690)), ((590, 760), (380, 760))]:
        d.line([a, b], fill=rgb(T.FLOOD), width=5)
    d.text((300, 900), "How a flood is made", font=font(SERIF_I, 44), fill=SOFT)
    footer(d, "The full explainer: thelongswell.com", C)
    add(im, 3000)
    q = [f.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    path = OUT / "ingredients.gif"
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True, disposal=1)
    return path.stat().st_size / 1e6


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if WHICH in ("weekend", "all"):
        print("weekend_forecast.gif %.1f MB" % weekend())
    if WHICH in ("weekend-es", "all"):
        print("prevision_fin_de_semana.gif %.1f MB" % weekend("es"))
    if WHICH in ("ingredients", "all"):
        print("ingredients.gif %.1f MB" % ingredients())
