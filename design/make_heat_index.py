"""The heat channel index. VD's design, built to ship.

Two changes from their canvas version, both implementation rather than
design:

  NO RUNTIME CDN. Theirs loads d3, topojson and the world topology from
  three CDNs at page load. A reader should not have to reach unpkg and
  jsdelivr to see our map, and the page should not break when one has a
  bad day. Projection and coastline are computed here; the page ships as
  plain SVG. design/data/europe_coast.json is Natural Earth's merged
  `land`, so it is coastline with no internal country borders, which is
  what their topojson.mesh(a === b) produces.

  THE LIST IS ORDERED AND CARRIES MAGNITUDE. VD ordered alphabetically,
  on the sound argument that most cities are tied at their own record so
  ranking would invent a winner. Kristjan read it and found it boring,
  and he is right: fourteen rows of "record, 88 years" tell you nothing
  about the fact that Marseille had 34 hot days and Berlin had 8.

  There IS a defensible order and I had accepted too quickly that there
  was not. Under a stationary climate the nth year of a record has
  probability 1/n of being a record, so rank r in an N-year series has
  plotting position r/N: the chance of landing this high by luck. That
  breaks the tie honestly, because a record in 88 years IS rarer than a
  record in 43, and it is the same arithmetic heat already uses for
  expected_no_trend. It also survives the set growing to 100 cities,
  which is what Kristjan was actually testing.

  Each row then shows the city's own count against its own normal, which
  carries magnitude without inviting a cross-city comparison the method
  refuses: every pair of numbers is on that city's own threshold.
"""
import json, math, statistics as st
from pathlib import Path

R = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(R))
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       site_masthead)
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())["cities"]
CO = json.loads((R / "design/city_coords.json").read_text())["cities"]
COAST = json.loads((R / "design/data/europe_coast.json").read_text())
C, DH = N["cities"], N["day_headline"]

BOX = {"ES": (36.0, 43.8, -9.3, 4.3), "FR": (41.3, 51.1, -5.2, 9.6),
       "DE": (47.2, 55.1, 5.8, 15.1), "AT": (46.3, 49.1, 9.5, 17.2)}
rows = []
for n, v in C.items():
    if n not in CO:
        raise SystemExit(f"{n} has no coordinate")
    la, lo = CO[n]["lat"], CO[n]["lon"]
    s, nn, w, e = BOX[v["country"]]
    if not (s <= la <= nn and w <= lo <= e):
        raise SystemExit(f"{n} at {la},{lo} is outside {v['country']}")
    r = v["days"]["rank"]
    yrs = S[n]["years"]
    base = st.mean([x["days_to_cut"]["95"] for y, x in yrs.items()
                    if 1961 <= int(y) <= 1990 and x.get("usable_to_cut")
                    and x.get("days_to_cut")])
    rows.append({"name": n, "lat": la, "lon": lo, "rank": r["value"],
                 "of": r["of_years"], "pct": r["percentile"],
                 "now": v["days"]["days_2026"]["95"], "base": base,
                 "p": r["value"] / (r["of_years"] + 1),
                 "gated": bool(v.get("nights_metric_gated"))})
rows.sort(key=lambda d: (d["p"], d["name"]))

# VD Main's ruling, amending section 7: hue marks a MEASURED QUANTITY,
# never a threshold on one. The record line is drawn by how long each
# station has been running rather than by how hot the summer was, so
# colouring it would give hue to the length of a record.
#
# What it replaced, and the defect is arithmetic rather than taste:
# Murcia is rank 1 of 43 and Barcelona rank 2 of 87. Their plotting
# positions are 1/44 and 2/88, which are THE SAME NUMBER. The old map
# drew Murcia as a filled disc and Barcelona as a smaller hollow ring in
# a different list. Identical events, opposite treatments.
#
# And the hollow ring broke D-043 on its own. A ring is the universal
# convention for absent or not-applicable, and drawn smaller than the
# filled state it carries under half the ink, so the map said nothing
# happened in Berlin, Hamburg, Seville, Valencia, Madrid, Barcelona and
# Cologne while the prose two screens down said the opposite.
#
# So: constant footprint, one INK hairline, fill from the anomaly ramp.
# Presence is constant, nobody is a null, and D-043 holds by
# construction rather than by caption.
BANDS = [(50, "#8E240A"), (25, "#C05B3D"), (10, "#DC957E"), (0, "#EFC9BD")]
BANDS_DARK = [(50, "#C05B3D"), (25, "#DC957E"), (10, "#EFC9BD"), (0, "#E8E7E2")]


def band(pp):
    """Fill for a plotting position, stepped rather than continuous.

    Stepped because the legend is discrete swatches: a gradient bar would
    let a reader decode a colour the map never draws.
    """
    one_in = 1 / pp if pp else 999
    for lo, col in BANDS:
        if one_in >= lo:
            return col
    return BANDS[-1][1]


# ---- projection: Mercator, fitted to the marks, as VD used -----------------
W, H, PAD = 900, 660, 52
# Mercator y, expressed in DEGREES so it shares units with longitude.
# Without the 180/pi the y range is ~0.35 radians against ~22 degrees of
# longitude, so a single shared scale collapsed the map to a horizontal
# line. Caught by looking at it.
merc = lambda la: math.degrees(
    math.log(math.tan(math.pi / 4 + math.radians(la) / 2)))
LO0, LO1 = min(d["lon"] for d in rows), max(d["lon"] for d in rows)
MY0, MY1 = merc(min(d["lat"] for d in rows)), merc(max(d["lat"] for d in rows))
sx = (W - 2 * PAD) / (LO1 - LO0)
sy = (H - 2 * PAD) / (MY1 - MY0)
k = min(sx, sy)                      # one scale, so the map is not stretched
ox = PAD + ((W - 2 * PAD) - (LO1 - LO0) * k) / 2
oy = PAD + ((H - 2 * PAD) - (MY1 - MY0) * k) / 2
PX = lambda lo: ox + (lo - LO0) * k
PY = lambda la: oy + (MY1 - merc(la)) * k

coast = []
for ring in COAST["rings"]:
    pts = [(PX(lo), PY(la)) for lo, la in ring if -180 < lo < 180 and -85 < la < 85]
    if len(pts) > 2:
        coast.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")

# ---- labels: VD's algorithm, eight positions at two distances --------------
placed = [{"x1": PX(d["lon"]) - 9, "x2": PX(d["lon"]) + 9,
           "y1": PY(d["lat"]) - 9, "y2": PY(d["lat"]) + 9} for d in rows]
def overlap(a, b):
    return (max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])) *
            max(0, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])))

marks, labels = [], []
for d in sorted(rows, key=lambda d: PY(d["lat"])):
    x, y = PX(d["lon"]), PY(d["lat"])
    marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{band(d["p"])}" '
                 f'stroke="var(--ink)" stroke-width="1"/>')
    bw = max(len(d["name"]) * 7.1, 66)
    opts = []
    for dd in (10, 22):
        opts += [(6 + dd, 4, "start"), (-(6 + dd), 4, "end"),
                 (6 + dd, -(6 + dd), "start"), (-(6 + dd), -(6 + dd), "end"),
                 (6 + dd, 6 + dd + 8, "start"), (-(6 + dd), 6 + dd + 8, "end"),
                 (0, -(6 + dd + 8), "middle"), (0, 6 + dd + 14, "middle")]
    best, bestbox, cost0 = None, None, float("inf")
    for dx, dy, anc in opts:
        x1 = x + dx if anc == "start" else (x + dx - bw if anc == "end" else x - bw / 2)
        box = {"x1": x1, "x2": x1 + bw, "y1": y + dy - 12, "y2": y + dy + 14}
        if box["x1"] < 4 or box["x2"] > W - 4 or box["y1"] < 4 or box["y2"] > H - 4:
            continue
        c = sum(overlap(p, box) for p in placed)
        if c == 0:
            best, bestbox = (dx, dy, anc), box
            break
        if c < cost0:
            cost0, best, bestbox = c, (dx, dy, anc), box
    if best is None:
        best, bestbox = opts[0], {"x1": x, "x2": x + bw, "y1": y, "y2": y + 26}
    placed.append(bestbox)
    dx, dy, anc = best
    sub = "record" if d["rank"] == 1 else f'{d["pct"]:.1f}th pct'
    labels.append(
        f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{anc}" class="cn">{d["name"]}'
        f'</text><text x="{x+dx:.1f}" y="{y+dy+12:.1f}" text-anchor="{anc}" '
        f'class="cs">{sub}</text>')

svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="height:auto" role="img" '
       f'aria-label="Twenty-one European weather stations, each marked as at its own '
       f'record for hot days or elevated but not a record">'
       + "".join(f'<path d="{d}" fill="var(--land)" stroke="var(--coast)" '
                 f'stroke-width="0.9" stroke-linejoin="round"/>' for d in coast)
       + "".join(marks) + "".join(labels) + "</svg>")

# ---- the list: ordered, and each row carries its own magnitude -------------
# every city has a page now, so nothing renders as a dead name
# Flat, matching the shipped shape: /heat/ is the index and /heat/<city>
# sits beside it, so a link is a bare filename from either direction.
PAGES = {n: f"{n.lower().replace(chr(32), chr(45))}.html" for n in C}
# NOT a shared scale. The previous version divided every count by the
# largest count in the set, so Marseille's 34 days at 33.9 C and Alicante's
# 21 at 33.8 C were drawn against each other. Different thresholds, not the
# same question, and the caption said so while the drawing denied it.
# Each bar is now the city's 2026 count as a fraction of its OWN highest
# summer, so a full bar means at its own record and the tie reads as a tie.
# Scale each bar to that city's own highest summer BEFORE 2026, so a full
# bar means "matched or beat its own record" and the tie is visible rather
# than silently rounded into the record group. Cologne's 16 equals its 1976
# high, which is why it is rank 2 and not 1: a tie is not a record. Scaling
# to a max that includes 2026 would have drawn it at full width and told a
# reader the opposite of what the rank says.
OWNMAX = {d["name"]: max(
    [x["days_to_cut"]["95"] for y, x in S[d["name"]]["years"].items()
     if int(y) < 2026 and x.get("usable_to_cut") and x.get("days_to_cut")] or [1])
    for d in rows}
_full = [d["name"] for d in rows if d["now"] >= OWNMAX[d["name"]]]
_rec = [d["name"] for d in rows if d["rank"] == 1]
if set(_full) - set(_rec) - {"Cologne"}:
    raise SystemExit(f"a city draws a full bar without being a record and is not the "
                     f"known tie: {sorted(set(_full) - set(_rec))}")

def city_row(i, d):
    nm = d["name"]
    # "record" under every name repeated what the grouping already says.
    lab = ("" if d["rank"] == 1 else f'{d["rank"]}th of {d["of"]} &middot; ')
    href = PAGES.get(nm)
    title = (f'<a href="{href}" class="cty">{nm}</a>' if href
             else f'<span class="cty dim">{nm}</span>')
    om = OWNMAX[nm] or 1
    w = min(100.0, d["now"] / om * 100)
    bw = min(100.0, d["base"] / om * 100)
    return (f'<div class="lrow"><span class="lnum">{i}</span>'
            f'<span class="lcty">{title}<span class="lsub">{lab}'
            f'{d["of"]} years of record</span></span>'
            f'<span class="lbar"><span class="bnow" style="width:{w:.1f}%"></span>'
            f'<span class="bbase" style="left:{bw:.1f}%"></span></span>'
            f'<span class="lval">{d["now"]}<span class="lbase">vs {d["base"]:.0f}</span>'
            f'</span></div>')

# ONE list. The two groups are what the ruling deletes: they split cities
# whose plotting positions are equal.
all_rows = "".join(city_row(i, d) for i, d in enumerate(rows, 1))

MAR, BER = C["Marseille"], C["Berlin"]
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat &middot; The Long Swell</title>
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--coast:#C6C5C2;--accent:#173F9E;--bar:#D3D2CB;--land:#E4E3DC}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--coast:#43423C;
--accent:#6E97E8;--bar:#43423C;--land:#232321}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:1020px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:52px;line-height:1.04;
letter-spacing:-.02em;color:var(--ink);margin:40px 0 14px;max-width:20ch;text-wrap:balance}}
.stand{{font-size:17.5px;line-height:1.62;max-width:60ch;margin:0}}
.cn{{font-family:Spectral,serif;font-size:13px;fill:var(--ink)}}
.cs{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint);
letter-spacing:.05em}}
.key{{display:flex;flex-wrap:wrap;gap:14px 30px;align-items:center;margin:14px 0 0;
font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--ink-faint)}}
.key i{{display:inline-block;width:12px;height:12px;border-radius:50%;
vertical-align:-2px;margin-right:8px}}
.ks i{{border:1px solid var(--ink)}}
.seclab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:54px 0 6px}}
.subl{{font-size:15.5px;line-height:1.6;color:var(--soft);max-width:70ch;margin:12px 0 18px}}
.lrow{{display:grid;grid-template-columns:26px 190px 1fr 76px;gap:16px;
align-items:center;padding:9px 0;border-bottom:1px solid var(--rule)}}
.lnum{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--ink-faint);
text-align:right}}
.cty{{font-size:17px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}}
.cty.dim{{color:var(--soft);border:0}}
.lcty{{display:flex;flex-direction:column;gap:2px}}
.lsub{{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--ink-faint)}}
.lbar{{position:relative;height:14px;background:var(--sunk)}}
.bnow{{position:absolute;left:0;top:0;bottom:0;background:var(--ink)}}
.bbase{{position:absolute;top:-3px;bottom:-3px;width:1.6px;background:var(--accent)}}
.lval{{font-family:'IBM Plex Mono',monospace;font-size:17px;color:var(--ink);
text-align:right;font-variant-numeric:tabular-nums;display:flex;flex-direction:column;
align-items:flex-end;line-height:1.25}}
.lbase{{font-size:9.5px;color:var(--ink-faint)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:0;margin-top:6px}}
.two>div{{border-top:1px solid var(--rule);padding:16px 30px 16px 0}}
.two>div+div{{border-left:1px solid var(--rule);padding:16px 0 16px 30px}}
.tl{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;
text-transform:uppercase;color:var(--ink-faint);display:block;margin-bottom:9px}}
.src{{font-family:'IBM Plex Mono',monospace;font-size:12px;line-height:1.9;
color:var(--soft);display:grid;grid-template-columns:1fr auto;column-gap:30px;
margin-top:50px}}
.src span{{border-top:1px solid var(--rule);padding-top:9px}}
.src span:nth-child(-n+2){{border-top:2.4px solid #8E8E88}}
</style></head><body><main>
{site_masthead("../", active="heat")}
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span><span class="when">Week of 3 August 2026</span></div>

<h1>How hot has the European summer been?</h1>
<p class="stand">Twenty-one cities, each measured against its own thermometer and its
own record rather than against each other. A hot day is one at or above that city's own
95th percentile for July and August, so {C['Seville']['days']['thresholds_c']['95']}&nbsp;&deg;C
in Seville and {C['Berlin']['days']['thresholds_c']['95']}&nbsp;&deg;C in Berlin.
<strong style="color:var(--ink);font-weight:500">{DH['records']} of the
{DH['of_cities']} have had more of them than in any year on record.</strong>
A typical year produces {DH['baseline']['median_year']}.</p>

{svg}
<div class="key">
<span class="ks"><i style="background:#8E240A"></i>1 in 50 years or rarer</span>
<span class="ks"><i style="background:#C05B3D"></i>1 in 25 to 49</span>
<span class="ks"><i style="background:#DC957E"></i>1 in 10 to 24</span>
<span class="ks"><i style="background:#EFC9BD"></i>more often than 1 in 10</span>
<span>Every city is the same disc. The fill is how rare this summer is against
that city's own record, so nothing between the marks is shaded and no city is
drawn as empty.</span></div>

<div class="seclab">How rare this is, against each city's own record</div>
<p class="subl">Ordered by rank divided by the length of the record: the chance of
landing this high without a trend. <strong style="color:var(--ink);font-weight:500">This
is not a league table and the top city is not the hottest.</strong> A record in
{rows[0]['of']} years is a rarer thing than a record in {min(d['of'] for d in rows)},
which is what separates cities that would otherwise sit tied at first, and it is why a
long record lifts a city here. The bar is that city's own count against its own highest
earlier summer, so a full bar means it matched or beat its own record; the blue tick is
its 1961-1990 normal. Bars are not comparable between cities: every one is on its own
threshold and its own history.</p>
{all_rows}

<div class="seclab">Why we publish two measurements and not one</div>
<div class="two">
<div><span class="tl">Marseille</span>Its most hot days on record, and
{MAR['rank']['value']}th of {MAR['rank']['of_years']} for hot nights. The days run
further than the nights.</div>
<div><span class="tl">Berlin</span>Hot days above {BER['days']['rank']['percentile']:.0f}
per cent of its own summers, and hot nights at the
{BER['rank']['percentile']:.0f}th percentile. Here it is the other way round.</div>
</div>
<p class="subl" style="margin-top:16px">If one measurement stood in for the other, those
two cities would lean the same way. They lean opposite ways, which is how you can tell
the instruments measure different things.
<strong style="color:var(--ink);font-weight:500">{sum(1 for d in rows if d['gated'])}
cities publish no night ratio at all</strong>, each averaging under two hot nights a
year: dividing by a base that thin produces a large number and no evidence. The gate is
a flag on each city rather than a threshold applied here.</p>

<div class="src">
<span>AEMET OpenData, Meteo-France, GeoSphere Austria, Deutscher Wetterdienst</span>
<span style="text-align:right">to 2 and 3 August 2026</span>
<span>Hot days, above each station's own 95th percentile of July-August maxima, 1971 to 2000</span>
<span style="text-align:right">{len(rows)} stations</span>
<span>Coastlines, Natural Earth 110m, merged land so no country borders are drawn</span>
<span style="text-align:right">public domain</span>
</div>
</main></body></html>"""
out = R / "docs/heat/index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"wrote {out} | {len(rows)} cities, {len(coast)} coast rings, "
      f"top is {rows[0]['name']} (p={rows[0]['p']:.3f}), "
      f"last is {rows[-1]['name']} (p={rows[-1]['p']:.3f})")
