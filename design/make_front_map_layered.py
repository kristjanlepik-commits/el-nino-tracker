"""VD's layered front map, implemented on real payloads.

MOCKUP ONLY. Writes design/mockups/front_map_layered.html.

THIS ENACTS TWO REVERSALS, both of which VD flagged as needing Kristjan's
signature rather than theirs, and he has now asked for it twice:

    channel hue returns, on the map only     reverses D-101
    size returns, within a channel only      reverses D-146

Their case for each, kept here because a future chat will find this file
before it finds the study:

  HUE. Section 7 retired channel hue on the argument that colour spent on
  wayfinding is colour unavailable to data. On a map that argument
  inverts: WHICH INSTRUMENT DETECTED THIS is the datum, and type cannot
  carry it across ninety unlabelled marks. Scoped to map markers; pages
  stay typographic.

  SIZE. D-146's objection was that a sized mark makes a cross-instrument
  claim with no denominator attached. Hue separation answers half of it,
  since sizes now compare only inside one colour and each channel's
  measure is named in the legend. VD is straight that the other half
  stands: a reader will still compare a big red to a big green, and the
  caption carrying the never-across-colours line does not travel with a
  screenshot.

SHAPE IS THE PRIMARY SEPARATOR AND HUE IS REDUNDANT ON TOP. The first hue
set failed its first real reader: Kristjan is red-green colourblind and
could not tell fires from crops. Crops moved to teal and shape became the
separator. That books a cost forward, because teal is the retired FLOOD
token, so when Floods ships the set must be chosen again and CVD-tested as
a set.

TWO DEPARTURES FROM THE STUDY, both infrastructure rather than design:

1. NO CDN. The study loads d3 and topojson from unpkg and fetches the
   coastline from jsdelivr at render, with a catch() that prints "coastline
   could not be fetched". That makes the front page's main object depend on
   two third parties at read time, on a site that currently ships one
   static SVG and no third-party JS. The projection is eleven lines and the
   coastline is already in the repo, so this draws docs/world-map.svg
   directly and the page keeps working offline.

2. REAL PAYLOADS. The study hard-codes thirteen marks. This reads fires,
   crops and heat, so the calm denominator is the real one: ninety fires
   countries rather than six, which is the density the study says it is not
   showing.

Usage:  .venv/bin/python design/make_front_map_layered.py
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
        out.append(dict(ch="fires", name=name, x=xy(c["lat"], c["lon"])[0],
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

    dx, dy, anchor = (r + 6, 4, "start")
    if m.get("left"):
        dx, anchor = -(r + 6), "end"
    if m.get("nudge"):
        dx, dy = m["nudge"]
    cls = "" if labelled else ' class="hov"'
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


def page(d):
    ms = marks(d)
    # Biggest first so a small mark is never hidden under a large one.
    ms.sort(key=lambda m: -(HEAT_R if m["ch"] == "heat" else radius(m["sev"])))

    top = max((m for m in ms if m["ch"] == "fires"), key=lambda m: m["sev"])
    topc = max((m for m in ms if m["ch"] == "crops"), key=lambda m: m["sev"])
    labelled = {id(top), id(topc)}
    for m in ms:
        if m["ch"] == "heat":
            labelled.add(id(m))
            m["nudge"] = (-96, -34)
            m["left"] = True

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
    nino = (d["snap"].get("physical_state") or {}).get(
        "nino34_weekly_traditional")
    n34 = ("%+.1f&nbsp;&deg;C" % nino) if nino is not None else ""

    n_out = sum(1 for m in ms if m["ch"] != "heat" and m["sev"])
    n_in = sum(1 for m in ms if m["ch"] != "heat" and not m["sev"])

    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Front map, layered &middot; real payloads</title>
<style>
{faces}
:root {{ {vars} }}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink-soft);
 font-family:"{prose}",Georgia,serif;-webkit-font-smoothing:antialiased}}
.shell{{max-width:1180px;margin:0 auto;padding:0 40px}}
.mono{{font-family:"{data}",monospace}}
.mast{{padding:20px 0 12px;border-bottom:3px solid var(--ink);display:flex;
 flex-wrap:wrap;align-items:baseline;gap:8px 26px}}
.mast .wm{{font-weight:500;font-size:23px;color:var(--ink)}}
.mast .r{{margin-left:auto;font-family:"{data}",monospace;font-size:10.5px;
 letter-spacing:.18em;text-transform:uppercase;color:var(--ink-faint)}}
.lab{{padding:22px 0 4px;display:flex;flex-wrap:wrap;align-items:baseline;
 gap:6px 16px;font-family:"{data}",monospace;font-size:9.5px;
 letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.lab .r{{margin-left:auto;letter-spacing:.14em;color:var(--ink-faint);
 display:flex;flex-wrap:wrap;gap:2px 12px}}
.lgd{{display:flex;flex-wrap:wrap;align-items:center;gap:2px 26px;
 padding:10px 0 0}}
.lg{{background:none;border:none;padding:4px 0;margin:0;cursor:pointer;
 display:flex;align-items:center;gap:8px;font-family:"{data}",monospace;
 font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
 color:var(--ink-soft)}}
.lg:hover{{color:var(--ink)}}
.lg .ct{{letter-spacing:.04em;color:var(--ink-faint)}}
.lg[aria-pressed="false"]{{opacity:.35}}
.lg:focus-visible{{outline:2px solid var(--ink);outline-offset:3px}}
.cap{{font-family:"{data}",monospace;font-size:11px;line-height:1.7;
 color:var(--ink-faint);max-width:110ch;border-top:1px solid var(--rule);
 margin:12px 0 0;padding-top:12px}}
.cap b{{color:var(--ink);font-weight:400}}
svg a{{text-decoration:none}}
svg .hov{{opacity:0;transition:opacity 120ms}}
svg a:hover .hov,svg a:focus-visible .hov{{opacity:1}}
svg .ring{{fill:none;stroke:var(--ink);stroke-width:2;opacity:0}}
svg a:focus-visible .ring{{opacity:1}}
svg .mln{{font-family:"{prose}",Georgia,serif;font-size:13px;fill:var(--ink);
 stroke:var(--paper);stroke-width:3;paint-order:stroke}}
svg .mlc{{font-family:"{data}",monospace;font-size:9.5px;fill:var(--ink-soft);
 stroke:var(--paper);stroke-width:3;paint-order:stroke}}
svg .eq{{stroke:var(--rule);stroke-width:1}}
svg .sstw{{fill:none;stroke:var(--ink-faint);stroke-width:1;
 stroke-dasharray:4 4}}
svg .nb{{fill:none;stroke:{nino_col};stroke-width:1.8}}
svg .nbt{{font-family:"{data}",monospace;font-size:9.5px;font-weight:600;
 fill:{nino_col};stroke:var(--paper);stroke-width:3;paint-order:stroke}}
</style></head><body>

<div class="shell">
<div class="mast"><span class="wm">The Long Swell</span>
<span class="r">Front map, layered &middot; week of 2026-08-10 &middot;
mockup, not published</span></div>
<div class="lab">Where, this week
<span class="r"><span>{n_out} places outside their own range</span>
<span>{n_in} within it</span><span>{n_city} cities in one aggregate</span>
<span>derived from the marks</span></span></div>
</div>

<svg viewBox="0 20 800 336" width="100%" style="display:block" role="img"
 aria-label="World map of this week's readings. One colour and one shape per
 channel; a mark's size is that channel's own severity measure and sizes
 compare only within a channel. Fires are circles, crops are squares, heat is
 one dashed aggregate.">
{world}
<line class="eq" x1="0" y1="{eq:.1f}" x2="800" y2="{eq:.1f}"/>
<rect class="sstw" x="{wx:.1f}" y="{wy:.1f}" width="{ww:.1f}" height="{wh:.1f}"/>
<path class="nb" d="M{b1:.1f},{brk:.1f} v-7 h{bw:.1f} v7"/>
<text class="nbt" x="{b2:.1f}" y="{brt:.1f}">NI&Ntilde;O 3.4 &nbsp;{n34}</text>
{gs}
</svg>

<div class="shell">
{legend}
<p class="cap">One hue and one shape per channel; a mark&rsquo;s size is that
channel&rsquo;s own severity measure: fires by the multiple of its same-week
mean, crops by regions at a record low, heat as one unsized aggregate.
<b>Sizes compare within a channel, never across channels</b>, because the
channels measure different things against different records. Channels differ
by shape as well as hue, so the layer split survives colourblindness and
greyscale; hue never carries a distinction alone. Click a legend entry to hide
or show its layer. Every mark is a link; hover or focus shows its claim with
its denominator. Calm places stay drawn at the floor size, never removed. The
dashed window is the extent of the Pacific SST field, which is the matplotlib
PNG in production. Coastline is the repo&rsquo;s own world-map.svg, drawn
directly rather than fetched, so the page needs no third party at read
time.</p>
</div>
{script}
</body></html>""".format(
        faces=T.font_faces_css("../../docs/fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA, world=body, gs=gs,
        legend=legend(d, ms), script=SCRIPT, nino_col=T.NINO,
        eq=eq, wx=wtl[0] + 1, wy=wtl[1], ww=wbr[0] - wtl[0] - 1,
        wh=wbr[1] - wtl[1], b1=b1, b2=b2 + 9, bw=b2 - b1,
        brk=eq + 13, brt=eq + 11, n34=n34,
        n_out=n_out, n_in=n_in, n_city=len(d["heat"]["cities"]))


def main():
    d = {}
    d["heat"] = json.load(open(ROOT / "heat/data/city_nights.json"))
    d["coords"] = json.load(open(ROOT / "heat/data/station_coords.json"))
    d["fires_week"] = json.load(open(ROOT / "fires/data/current_week.json"))
    d["events"] = json.load(open(ROOT / "data/events.json"))["events"]
    d["crops"] = json.load(open(ROOT / "crops/data/stress_current.json"))
    d["snap"] = json.load(open(ROOT / "snapshots/2026-08-10.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "front_map_layered.html").write_text(page(d))
    ms = marks(d)
    print("wrote design/mockups/front_map_layered.html")
    print("  %d marks: %d fires, %d crops, 1 heat aggregate"
          % (len(ms), sum(1 for m in ms if m["ch"] == "fires"),
             sum(1 for m in ms if m["ch"] == "crops")))
    sized = [m for m in ms if m["ch"] != "heat"]
    print("  radius %.2f (floor) to %.2f, largest %s"
          % (FLOOR, max(radius(m["sev"]) for m in sized),
             max(sized, key=lambda m: radius(m["sev"]))["name"]))


if __name__ == "__main__":
    main()
