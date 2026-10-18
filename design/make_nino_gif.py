"""Social GIF: where this El Nino's warmth sits, against 1997 and 2015.

For LinkedIn and X, 18 Oct 2026. The same fields as the brief's Nino
regions map (docs/nino-map/, design/make_nino_map.py) and the same CPC
weekly numbers as its table, from fetchers.oisst_weekly: never values
recomputed from the grid. 2015, then 1997, then 2026, then the three
stacked on one colour scale.

Square 960 px, under 8 MB. Output goes to OUT (first argument), outside
the repo.

Run:  .venv/bin/python design/make_nino_gif.py OUT_DIR
"""
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T                                     # noqa: E402
from fetchers import oisst_weekly                      # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
S = 960
F = ROOT / "assets/fonts"
SERIF = "spectral/Spectral-Medium.ttf"
SERIF_I = "spectral/Spectral-Italic.ttf"
MONO = "ibm-plex-mono/IBMPlexMono-Regular.ttf"
MONO_M = "ibm-plex-mono/IBMPlexMono-Medium.ttf"
BOXES = (("nino4", "Niño 4", 160, 210, 5, -5), ("nino34", "Niño 3.4", 190, 240, 5, -5),
         ("nino3", "Niño 3", 210, 270, 5, -5), ("nino12", "Niño 1+2", 270, 280, 0, -10))


def font(name, size):
    return ImageFont.truetype(str(F / name), size)


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


PAPER, INK, SOFT = rgb(T.PAPER), rgb(T.INK), rgb(T.INK_FAINT)


def panel(png, ext, vals, width, records=()):
    """One map band with its boxes and CPC labels, on paper."""
    field = Image.open(png).convert("RGBA")
    h = int(width * field.height / field.width)
    field = field.resize((width, h), Image.LANCZOS)
    top_pad, bot_pad = 64, 70
    im = Image.new("RGB", (width, h + top_pad + bot_pad), PAPER)
    im.paste(field, (0, top_pad), field)
    d = ImageDraw.Draw(im)
    lw, le, ln, ls = ext["lon_west"], ext["lon_east"], ext["lat_north"], ext["lat_south"]
    X = lambda lo: (lo - lw) / (le - lw) * width
    Y = lambda la: top_pad + (ln - la) / (ln - ls) * h
    f = font(MONO_M, 21)
    for k, label, w0, w1, n, s in BOXES:
        d.rectangle([X(w0), Y(n), X(w1), Y(s)], outline=INK, width=2)
    for k, label, w0, w1, n, s in BOXES:
        txt = "%s %+.1f" % (label, vals[k]) + ("  record" if k in records else "")
        tw = d.textlength(txt, font=f)
        if k == "nino4":
            x, y = X(w0), Y(n) - 64
        elif k == "nino34":
            x, y = X(w1) - tw, Y(n) - 34
        elif k == "nino3":
            x, y = X(w0), Y(s) + 6
        else:
            x, y = width - tw - 8, Y(s) + 8
        d.rectangle([x - 6, y - 3, x + tw + 6, y + 27], fill=PAPER)
        d.text((x, y), txt, font=f, fill=INK)
    return im


def frame(title, kicker, body, foot):
    im = Image.new("RGB", (S, S), PAPER)
    d = ImageDraw.Draw(im)
    d.text((40, 36), kicker, font=font(MONO_M, 20), fill=SOFT)
    d.text((40, 66), title, font=font(SERIF, 50), fill=INK)
    im.paste(body, (20, (S - body.height) // 2 + 30))
    d.rectangle([0, S - 84, S, S], fill=PAPER)
    fs = 16
    while d.textlength(foot, font=font(MONO, fs)) > S - 80 and fs > 11:
        fs -= 1
    d.text((40, S - 76), foot, font=font(MONO, fs), fill=SOFT)
    d.text((40, S - 46), "thelongswell.com", font=font(MONO_M, 20), fill=INK)
    return im


def main():
    r = oisst_weekly.fetch()
    if not r.ok:
        raise SystemExit("CPC weekly fetch failed")
    week = str(r.issued)[:10]
    meta = json.loads((ROOT / "docs/nino-map" / f"{week}.json").read_text())
    ext = meta["extent"]
    reg = r.payload["regions"]
    an = r.payload["analogs_same_week"]
    vals = {"2026": {k: reg[k]["anom"] for k, *_ in BOXES}}
    for y in ("1997", "2015"):
        a = an[y]
        vals[y] = {"nino12": a["nino12"], "nino3": a["nino3"], "nino34": a["anom"], "nino4": a["nino4"]}
    rec = {k for k, *_ in BOXES
           if reg[k]["anom"] > (reg[k].get("prior_record") or {}).get("anom", 99)}
    png = {p["year"]: ROOT / "docs/nino-map" / p["png"] for p in meta["panels"]}
    wk = {p["year"]: date.fromisoformat(p["week"]) for p in meta["panels"]}
    foot = ("Sea surface vs 1991-2020, NOAA OISST · numbers: CPC weekly index · "
            "record: highest week since 1981")
    frames, durs = [], []

    # title card
    im = Image.new("RGB", (S, S), PAPER)
    d = ImageDraw.Draw(im)
    d.text((60, 300), "Where is", font=font(SERIF, 96), fill=INK)
    d.text((60, 410), "this El Niño hottest?", font=font(SERIF, 72), fill=INK)
    d.text((64, 540), "The equatorial Pacific, same week of October:", font=font(SERIF_I, 34), fill=SOFT)
    d.text((64, 588), "2015, 1997 and 2026", font=font(SERIF_I, 34), fill=SOFT)
    frames.append(im); durs.append(2200)

    order = ["2015", "1997", "2026"]
    for i, y in enumerate(order):
        body = panel(png[y], ext, vals[y], S - 40, rec if y == "2026" else ())
        when = "%s · week of %d %s" % (y, wk[y].day, wk[y].strftime("%B"))
        # What CPC's four numbers show, west to east. 2015 is not a central
        # peak (its Nino 1+2 +2.6 beats its Nino 3.4 +2.1); it is the flat
        # profile. 1997 and 2026 both climb toward South America, 2026 by
        # far the most steeply.
        title = {"2015": "Warmth spread along the equator",
                 "1997": "Warmer toward South America",
                 "2026": "Far hotter toward South America"}[y]
        f = frame(title, when.upper(), body, foot)
        if y == "2026" and rec:
            dd = ImageDraw.Draw(f)
            ty = (S - body.height) // 2 + 30 + body.height + 24
            for k, label, *_ in reversed(BOXES):
                if k in rec:
                    pr = reg[k]["prior_record"]
                    dd.text((40, ty), "%s %+.1f °C, previous record %+.1f (%s)" % (
                        label, reg[k]["anom"], pr["anom"],
                        date.fromisoformat(pr["week"][:10]).strftime("%B %Y")),
                        font=font(SERIF_I, 30), fill=INK)
                    ty += 44
        if frames and i > 0:
            prev = frames[-1]
            for t in (0.25, 0.5, 0.75):
                frames.append(Image.blend(prev, f, t)); durs.append(90)
        frames.append(f); durs.append(3200 if y != "2026" else 4200)

    # the three stacked, one scale
    stack = Image.new("RGB", (S, S), PAPER)
    d = ImageDraw.Draw(stack)
    d.text((40, 36), "SAME WEEK OF OCTOBER, ONE COLOUR SCALE", font=font(MONO_M, 20), fill=SOFT)
    d.text((40, 66), "2026 is hottest in the east", font=font(SERIF, 50), fill=INK)
    y0 = 140
    for y in order:
        b = panel(png[y], ext, vals[y], S - 200, rec if y == "2026" else ())
        b = b.resize((int(b.width * 0.74), int(b.height * 0.74)), Image.LANCZOS)
        d.text((40, y0 + b.height // 2 - 14), y, font=font(MONO_M, 26), fill=INK)
        stack.paste(b, (130, y0))
        y0 += b.height + 4
    d.rectangle([0, S - 84, S, S], fill=PAPER)
    fs = 16
    while d.textlength(foot, font=font(MONO, fs)) > S - 80 and fs > 11:
        fs -= 1
    d.text((40, S - 76), foot, font=font(MONO, fs), fill=SOFT)
    d.text((40, S - 46), "thelongswell.com", font=font(MONO_M, 20), fill=INK)
    # legend, in the footer row beside the site name: the stacked bands
    # leave no room under them at 960
    lx, ly = 520, S - 40
    d.text((lx - 40, ly - 6), "-%g" % meta["full_scale"], font=font(MONO, 16), fill=SOFT)
    for j, c in enumerate(T.ANOMALY):
        d.rectangle([lx + j * 28, ly, lx + j * 28 + 28, ly + 10], fill=rgb(c))
    d.text((lx + 9 * 28 + 8, ly - 6), "+%g °C" % meta["full_scale"], font=font(MONO, 16), fill=SOFT)
    for t in (0.25, 0.5, 0.75):
        frames.append(Image.blend(frames[-1], stack, t)); durs.append(90)
    frames.append(stack); durs.append(5000)

    q = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "nino_regions.gif"
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True)
    stack.save(OUT / "nino_regions_still.png")
    print(path, "%.1f MB" % (path.stat().st_size / 1e6), len(frames), "frames")


if __name__ == "__main__":
    main()
