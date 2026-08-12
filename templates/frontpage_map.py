"""The front page map: one layer per channel, above a stated bar.

PRODUCTION MODULE. design/make_front_map_layered.py renders it as a study;
this is the source both use, so the bar cannot be changed on one surface
and left on the other.

Ratified in D-155, scoped to map markers and nowhere else: channel hue
returns (reversing D-101) and marks are sized within a channel (reversing
D-146). Shape is the PRIMARY separator and hue only repeats it, because the
first palette failed its first reader, who is red-green colourblind and
could not tell fires from crops.

The bar is a DISPLAY threshold, never a finding threshold. A place below it
is still measured, still counted by its channel and still on its channel
page. What it excludes is printed where the reader is, because a map that
omits places without saying so is a silent top-N.
"""
import json
import math
import sys
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

OUT = ROOT / "design" / "mockups"

# Crops takes FLOOD, heat takes VD's purple. Purple is not in tokens.py and
# heat cannot take NINO, because the front page carries an El Nino band a
# few centimetres below the map. If this direction is ratified, the values
# belong in tokens.py.
HUE = {"fires": T.FIRE, "crops": T.FLOOD, "heat": "#5C2C96"}

# The study is drawn at W=1400; docs/world-map.svg is an 800x400 equirect
# viewBox. Radii are scaled rather than retuned so the geometry stays VD's.
S = 800.0 / 1400.0
FLOOR = 5.5 * S
COEF = 6.2 * S
HEAT_R = 12.0 * S

CROPS_XY = {
    "Sudan": (15.0, 30.0), "Chad": (15.0, 19.0), "Niger": (17.0, 8.0),
    "Mali": (17.0, -4.0), "Ethiopia": (9.0, 40.0), "Uganda": (1.0, 32.0),
    "Rwanda": (-2.0, 30.0), "Burundi": (-3.0, 30.0), "Congo": (-1.0, 15.0),
    "Democratic Republic of the Congo": (-3.0, 23.0), "Angola": (-12.0, 17.0),
    "Namibia": (-22.0, 17.0), "United Republic of Tanzania": (-6.0, 35.0),
    "Egypt": (27.0, 30.0), "Libya": (27.0, 17.0), "Yemen": (15.0, 48.0),
    "Oman": (21.0, 57.0), "Iran (Islamic Republic of)": (32.0, 53.0),
    "Pakistan": (30.0, 70.0), "China": (35.0, 105.0), "Thailand": (15.0, 101.0),
    "Viet Nam": (16.0, 108.0), "Malaysia": (4.0, 102.0),
    "Philippines": (13.0, 122.0), "Papua New Guinea": (-6.0, 147.0),
    "Russian Federation": (60.0, 90.0), "Ukraine": (49.0, 32.0),
    "Türkiye": (39.0, 35.0), "Peru": (-10.0, -76.0), "Chile": (-33.0, -71.0),
    "Ecuador": (-1.0, -78.0), "Colombia": (4.0, -73.0), "Suriname": (4.0, -56.0),
    "Honduras": (15.0, -87.0), "Nicaragua": (13.0, -85.0),
    "United States of America": (39.0, -98.0),
}
SLUG = {"United States of America": "united-states-of-america",
        "Republic of Serbia": "republic-of-serbia",
        "United Kingdom": "united-kingdom",
        "Democratic Republic of the Congo":
            "democratic-republic-of-the-congo",
        "United Republic of Tanzania": "united-republic-of-tanzania",
        "Iran (Islamic Republic of)": "iran-islamic-republic-of",
        "Papua New Guinea": "papua-new-guinea", "Viet Nam": "viet-nam"}


def slug(n):
    return SLUG.get(n, n.lower().replace(" ", "-"))


def xy(lat, lon):
    return ((lon + 180.0) / 360.0 * 800.0, (90.0 - lat) / 180.0 * 400.0)


def radius(sev):
    """Sized within a channel, floored so a calm place is never removed.

    The floor is D-043 arriving on a mark: severity sizing shrinks quiet
    places, and a quiet place that shrinks to nothing has been deleted from
    the record by a drawing. VD holds it with a floor size and a
    full-strength stroke, and says plainly that if calm marks read as noise
    once real payloads land, that is the evidence this grammar fails.
    """
    if not sev:
        return FLOOR
    return max(FLOOR, COEF * math.sqrt(sev))



# --------------------------------------------------------------------------
# THE BAR. Kristjan, 2026-08-11: "let's not show all, show only the most
# extreme, then we need to think what is the bar."
#
# It is a DISPLAY threshold, not a finding threshold. A place below it is
# still measured, still reported, still on its channel page and still in the
# channel's own count. What changes is whether it is drawn here. That
# distinction is the whole reason this can be done at all: a map that omits
# places without saying so is a silent top-N, which is the thing this
# project refuses everywhere else.
#
# Three rules it has to keep:
#
# 1. IN EACH CHANNEL'S OWN UNITS, never a shared score. Fires speaks in
#    multiples of its own same-week mean; crops speaks in regions at a
#    record low. There is no bar that means the same thing to both.
#
# 2. A FIXED NUMBER, never tuned to a target count. 3x yields six countries
#    this week and may yield twenty in September. If it is moved then to
#    keep the map tidy, it has stopped being a threshold and become a top-N
#    wearing a threshold's clothes, and nobody outside this file would be
#    able to tell.
#
# 3. WHAT IT EXCLUDES IS COUNTED ON THE PAGE. Not logged to a terminal:
#    printed where the reader is, because the gap between "nothing else
#    happened" and "twelve more places cleared their own record but not this
#    bar" is exactly what a reader cannot infer from an empty map.
#
# Why these two values. Both are round, both are sayable in one clause, and
# both sit at a natural step in this week's distribution rather than in the
# middle of a run. Fires: one country at 6.2x, then 4.5, 4.0, 3.8, 3.8, 3.1,
# and then a long tail from 2.7 down to 1.5, so 3x is a shelf rather than a
# slice. Crops: seventeen countries have exactly one region at a record low
# and one region is a common event, nine have two, ten have three or more,
# so three is where "a region had a bad year" becomes "this country is
# having one".
BAR = {
    "fires": ("multiple", 3.0,
              "three times its own same-week mean or more"),
    "crops": ("regions", 3,
              "three or more regions at a record low"),
}


def clears_bar(m):
    """Above the bar, in that channel's own units. Heat is one aggregate and
    is not a candidate for a threshold: it is a locator, not a reading."""
    if m["ch"] == "heat":
        return True
    return (m["sev"] or 0) >= BAR[m["ch"]][1]


def marks(d):
    """Every mark, from the payloads, with its claim and its denominator."""
    out = []

    anom = {e["region"]: e for e in d["events"] if e.get("anomalous")}
    for c in d["fires_week"]["countries"].values():
        if c.get("lat") is None:
            continue
        name = c["name"]
        e = anom.get(name)
        hist = c.get("hist") or {}
        n_obs = (len(hist) if isinstance(hist, (dict, list)) else int(hist)) + 1
        if e:
            sev = float(str(e.get("stat", "0")).rstrip("x") or 0)
            claim = ("%s its average week &middot; heaviest of %d observed "
                     "weeks" % (e.get("stat", ""), n_obs))
        else:
            sev, claim = 0, "within its own normal range"
        out.append(dict(ch="fires", name=name,
                        is_record=bool(e and "record" in (e.get("qualifies_on") or [])), x=xy(c["lat"], c["lon"])[0],
                        y=xy(c["lat"], c["lon"])[1], sev=sev, claim=claim,
                        href="fires/%s/" % slug(name)))

    for p in d["crops"]["places"]:
        g = CROPS_XY.get(p["place"])
        if not g:
            continue
        n1 = [r for r in (p.get("regions") or []) if r.get("rank") == 1]
        if not n1:
            continue
        x, y = xy(*g)
        out.append(dict(
            ch="crops", name=p["place"], x=x, y=y, sev=len(n1),
            claim="%d of %d regions at a record low &middot; each lowest of "
                  "26" % (len(n1), len(p.get("regions") or [])),
            href="crops/%s/" % slug(p["place"])))

    lats = [c["lat"] for c in d["coords"].values() if c.get("lat")]
    lons = [c["lon"] for c in d["coords"].values() if c.get("lon")]
    hx, hy = xy(sum(lats) / len(lats), sum(lons) / len(lons))
    out.append(dict(ch="heat", name="%d cities" % len(d["heat"]["cities"]),
                    x=hx, y=hy, sev=None,
                    claim="aggregated &middot; city records live on the Heat "
                          "page", href="heat/"))
    return out



# --------------------------------------------------------------------------
# LABEL PLACEMENT, COMPUTED. VD's open item, and the reason it cannot stay
# hand-placed: I nudged Chad upward this afternoon because its name landed on
# Sudan's square, and that nudge is correct for one week's data. Next week
# Chad may not qualify, Sudan may be larger, and the nudge silently becomes
# a label sitting on a different neighbour. A hand-placed label is a constant
# pretending to be a layout.
#
# Deliberately simple: four candidate positions, each tested against every
# drawn mark, first clear one wins. Not an optimiser. It only has to beat a
# fixed offset, and it has to be legible to whoever reads it next.
#
# Text width is ESTIMATED rather than measured, because there is no browser
# here. Both faces are metrically stable enough at these sizes that a 0.55em
# advance is within a few pixels over a country name, and the box is padded
# to absorb the error. An estimate that is slightly wide costs a candidate;
# one that is slightly narrow costs a collision, so it errs wide.
def _text_w(txt, size):
    return len(txt) * size * 0.55


def place_label(m, others, r):
    """Return (dx, dy, anchor) for m's label, avoiding every other mark."""
    name_w = _text_w(m["name"], 13)
    h_ = 30                                    # name plus claim line
    cands = [
        (r + 6, 4, "start"), (-(r + 6), 4, "end"),
        (0, -(r + 8), "middle"), (0, r + 18, "middle"),
    ]
    for dx, dy, anchor in cands:
        x0 = m["x"] + dx
        if anchor == "end":
            box = (x0 - name_w, x0)
        elif anchor == "middle":
            box = (x0 - name_w / 2, x0 + name_w / 2)
        else:
            box = (x0, x0 + name_w)
        top = m["y"] + dy - 12
        clash = False
        for o in others:
            if o is m:
                continue
            orr = HEAT_R if o["ch"] == "heat" else radius(o["sev"])
            if (box[0] - orr < o["x"] < box[1] + orr
                    and top - orr < o["y"] < top + h_ + orr):
                clash = True
                break
        if not clash:
            return dx, dy, anchor
    # Every candidate collides, which is information rather than a failure:
    # take the default and let it be visibly crowded rather than silently
    # moved somewhere arbitrary.
    return cands[0]


def draw(m, labelled):
    r = HEAT_R if m["ch"] == "heat" else radius(m["sev"])
    col = HUE[m["ch"]]
    a = ['<a class="mk" href="https://thelongswell.com/%s" '
         'aria-label="%s, %s: %s">'
         % (h(m["href"]), h(m["ch"].title()), h(m["name"]),
            h(re_plain(m["claim"])))]
    a.append('<circle class="ring" cx="%.1f" cy="%.1f" r="%.1f"/>'
             % (m["x"], m["y"], r + 2.5))
    if m["ch"] == "crops":
        side = r * 1.772
        a.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                 'fill="%s" stroke="%s" stroke-width="1"/>'
                 % (m["x"] - side / 2, m["y"] - side / 2, side, side, col, col))
    elif m["ch"] == "heat":
        a.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                 'stroke="%s" stroke-width="1.4" stroke-dasharray="3 2.5"/>'
                 % (m["x"], m["y"], r, col))
    else:
        fill = col if m["sev"] else "var(--paper)"
        a.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
                 'stroke-width="1.2"/>' % (m["x"], m["y"], r, fill, col))

    dx, dy, anchor = m.get("place") or (r + 6, 4, "start")
    cls = "" if labelled else ' class="hov"'
    if anchor != "start" or abs(dy) > 8:
        a.append('<line class="ldr" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 % (m["x"] + (dx / abs(dx) * r if dx else 0),
                    m["y"] + (dy / abs(dy) * r if abs(dy) > r else 0),
                    m["x"] + dx - (4 if dx > 0 else -4 if dx < 0 else 0),
                    m["y"] + dy - 4))
    a.append('<text%s x="%.1f" y="%.1f" text-anchor="%s" class="mln%s">%s</text>'
             % ("", m["x"] + dx, m["y"] + dy, anchor,
                "" if labelled else " hov", h(m["name"])))
    a.append('<text x="%.1f" y="%.1f" text-anchor="%s" class="mlc hov">%s</text>'
             % (m["x"] + dx, m["y"] + dy + 13, anchor, m["claim"]))
    a.append("</a>")
    return "".join(a)


def re_plain(s):
    return s.replace("&middot;", "-").replace("&nbsp;", " ")


def legend(d, ms):
    n = {}
    for m in ms:
        n[m["ch"]] = n.get(m["ch"], 0) + 1
    rows = [
        ("fires", "Fires", "sized by the multiple of its own same-week mean",
         '<circle cx="7" cy="7" r="5.5" fill="%s" stroke="%s"/>'
         % (HUE["fires"], HUE["fires"])),
        ("crops", "Crops", "sized by regions at a record low",
         '<rect x="2" y="2" width="10" height="10" fill="%s" stroke="%s"/>'
         % (HUE["crops"], HUE["crops"])),
        ("heat", "Heat", "one aggregate, %d cities" % len(d["heat"]["cities"]),
         '<circle cx="7" cy="7" r="5.5" fill="none" stroke="%s" '
         'stroke-width="1.6" stroke-dasharray="2.5 2"/>' % HUE["heat"]),
    ]
    out = ['<div class="lgd">']
    for key, name, measure, sw in rows:
        out.append('<button class="lg" aria-pressed="true" data-layer="%s" '
                   'title="%s"><svg width="14" height="14" aria-hidden="true">'
                   '%s</svg>%s<span class="ct">%d</span></button>'
                   % (key, h(measure), sw, h(name), n.get(key, 0)))
    out.append("</div>")
    return "".join(out)


SCRIPT = """<script>
document.querySelectorAll('.lg').forEach(function (b) {
  b.addEventListener('click', function () {
    var on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    var g = document.getElementById('L-' + b.dataset.layer);
    if (g) g.style.display = on ? 'none' : '';
  });
});
</script>"""


def map_block(d, root_prefix=""):
    """The map, its legend and its state-line counts, for any page.

    Returned as a block rather than inlined so the front page and this
    study draw the SAME map. Two copies of a map is how a bar gets changed
    on one surface and not the other, which is the drift this whole day has
    been about.
    """
    allm = marks(d)
    ms = [m for m in allm if clears_bar(m)]
    # Counted BEFORE the filter, so the page can say what it is not showing.
    below = {}
    for m in allm:
        if m["ch"] != "heat" and m["sev"] and not clears_bar(m):
            below[m["ch"]] = below.get(m["ch"], 0) + 1
    watched = sum(1 for m in allm if m["ch"] == "fires")
    # Biggest first so a small mark is never hidden under a large one.
    ms.sort(key=lambda m: -(HEAT_R if m["ch"] == "heat" else radius(m["sev"])))

    top = max((m for m in ms if m["ch"] == "fires"), key=lambda m: m["sev"])
    topc = max((m for m in ms if m["ch"] == "crops"), key=lambda m: m["sev"])
    heat = next(m for m in ms if m["ch"] == "heat")
    labelled = {id(top), id(topc), id(heat)}
    for m in ms:
        r = HEAT_R if m["ch"] == "heat" else radius(m["sev"])
        m["place"] = place_label(m, ms, r)

    layers = {}
    for m in ms:
        layers.setdefault(m["ch"], []).append(draw(m, id(m) in labelled))
    gs = "".join('<g id="L-%s">%s</g>' % (k, "".join(v))
                 for k, v in layers.items())

    world = (ROOT / "docs" / "world-map.svg").read_text()
    body = world.split("</rect>")[-1]
    body = body[body.index("<g"):body.rindex("</svg>")]
    body = (body.replace('fill="#cfcdc2"', 'fill="var(--paper-sunk)"')
                .replace('stroke="#b8b6ab"', 'stroke="var(--rule)"'))

    eq = xy(0, 0)[1]
    wtl, wbr = xy(28, -180), xy(-28, -70)
    b1, b2 = xy(0, -170)[0], xy(0, -120)[0]
    bn, bs = xy(5, -170)[1], xy(-5, -170)[1]
    nino = (d["snap"].get("physical_state") or {}).get(
        "nino34_weekly_traditional")
    n34 = ("%+.1f&nbsp;&deg;C" % nino) if nino is not None else ""

    n_shown = sum(1 for m in ms if m["ch"] != "heat")
    n_below = sum(below.values())
    # RECORDS, NOT THE GATE. A fires country can clear the anomaly gate on
    # multiple or z alone without being at rank 1, so summing the gated set
    # overstated "past their own record" by five.
    n_rec = sum(1 for m in allm if m["ch"] == "crops" and m["sev"]) + \
        sum(1 for m in allm if m["ch"] == "fires" and m.get("is_record"))

    # THE PACIFIC SST FIELD IS THE GROUND LAYER, not an outline. VD's study
    # says so explicitly and the previous front page drew it; my rebuild
    # kept only the dashed extent, which is a box where the ocean should be.
    # Kristjan asked for the visual back.
    #
    # It carries its own observation date, because it is a static picture of
    # a moving field refreshed out of band, and a picture that does not say
    # how old it is goes quietly wrong. The date comes from the JSON beside
    # the PNG rather than from the issue date; those are different facts and
    # the asset can be older than the issue around it.
    sst = ""
    sst_date = ""
    try:
        meta_p = ROOT / "docs" / "pacific-sst.json"
        png = ROOT / "docs" / "pacific-sst.png"
        if meta_p.exists() and png.exists():
            sm = json.loads(meta_p.read_text())
            need = ("lon_west", "lon_east", "lat_south", "lat_north",
                    "observation_date")
            if all(sm.get(k) is not None for k in need):
                tl = xy(sm["lat_north"], sm["lon_west"])
                br = xy(sm["lat_south"], sm["lon_east"])
                sst = ('<image class="sstfield" href="%spacific-sst.png" '
                       'x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                       'preserveAspectRatio="none" aria-hidden="true"/>'
                       % (root_prefix, tl[0], tl[1], br[0] - tl[0],
                          br[1] - tl[1]))
                sst_date = sm["observation_date"]
    except (OSError, ValueError):
        sst = ""

    svg = (
        '<svg viewBox="0 20 800 336" width="100%" style="display:block" '
        'role="img" aria-label="World map of this week\u2019s readings. One '
        'colour and one shape per channel; a mark\u2019s size is that '
        'channel\u2019s own severity measure and sizes compare only within a '
        'channel. Fires are circles, crops are squares, heat is one dashed '
        'aggregate. Only places past a stated bar are drawn.">'
        + sst + body
        + '<line class="eq" x1="0" y1="%.1f" x2="800" y2="%.1f"/>' % (eq, eq)
        + '<rect class="sstw" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
          % (wtl[0] + 1, wtl[1], wbr[0] - wtl[0] - 1, wbr[1] - wtl[1])
        + '<rect class="nbh" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
          % (b1, bn, b2 - b1, bs - bn)
        + '<rect class="nb" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
          % (b1, bn, b2 - b1, bs - bn)
        + '<text class="nbt" x="%.1f" y="%.1f">NI\u00d1O 3.4 &nbsp;%s</text>'
          % (b2 + 8, bs + 9, n34)
        + gs + '</svg>')
    return dict(svg=svg, legend=legend(d, ms), script=SCRIPT,
                sst_date=sst_date,
                n_rec=n_rec, n_shown=n_shown, n_below=n_below,
                bar_f=BAR["fires"][2], bar_c=BAR["crops"][2])


