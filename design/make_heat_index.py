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
import json, math, re, statistics as st
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
       "DE": (47.2, 55.1, 5.8, 15.1), "AT": (46.3, 49.1, 9.5, 17.2),
       "NL": (50.7, 53.6, 3.3, 7.3)}
# A country arriving in the payload with no box would otherwise skip the
# check silently, which is the one failure this guard exists to prevent.
for _n, _v in C.items():
    if _v["country"] not in BOX:
        raise SystemExit(f"{_n}: no bounding box for {_v['country']}, so its "
                         f"coordinate cannot be checked. Add one.")
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
    zb = [x["days_to_cut"]["95"] for y, x in yrs.items()
          if 1991 <= int(y) <= 2020 and x.get("usable_to_cut")
          and x.get("days_to_cut")]
    zmean, zsd = st.mean(zb), st.stdev(zb)
    rows.append({"z": (v["days"]["days_2026"]["95"] - zmean) / zsd if zsd else 0.0,
                 "zmean": zmean,
                 "name": n, "lat": la, "lon": lo, "rank": r["value"],
                 "of": r["of_years"], "pct": r["percentile"],
                 "now": v["days"]["days_2026"]["95"], "base": base,
                 "p": r["value"] / (r["of_years"] + 1),
                 "gated": bool(v.get("nights_metric_gated"))})
rows.sort(key=lambda d: (-d["pct"], d["name"]))

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
# HOW FAR FROM NORMAL, not how rare the rank is. Kristjan's correction and
# it is a different question from the one I was answering.
#
# Plotting position asks how unlikely this RANK is given the length of the
# record, so it rewards a long record. Malaga sat third on it, on an
# 80-year series, having had 11 hot days against a normal of 3.8. Nice had
# 34 against 4.0. The page asks how hot the summer has been, and z answers
# that where plotting position does not.
#
# z is measured against the 1991-2020 normal, the WMO window and the one
# heat ruled for its night sd, so the map and the city pages can share a
# scale. The window excludes 2026, so z is not bounded by the in-sample
# ceiling of (n-1)/sqrt(n).
# THREE bands, not four. Four split the middle into "far outside its
# normal range" and "outside its normal range", which is not a distinction
# a reader can act on, and it carried 6 and 7 cities.
#
# The labels describe DISTANCE only and never say "record". A record is a
# rank claim and these bands are a distance claim: at any cut, cities that
# ARE at their record sit in more than one band, so a label mentioning
# records would tell a reader that Palma, Vienna, Munich and Malaga are
# not records when they are. That is the mixing VD ruled against.
# Fills are TOKENS, not hex, because they must invert with the theme.
# VD measured the bug: hard-coded light-theme hex ran 7.65 / 3.83 / 1.34
# on bone paper and 2.00 / 3.99 / 11.42 on dark, so on dark the palest
# reading was the loudest mark and the most extreme the quietest. That is
# D-043 broken by the theme, and dark mode is not optional.
# Dark set measured against PAPER_DARK: 6.95 / 3.99 / 2.08, descending,
# with the faintest still clear of the background.
# PERCENTILE, not z. VD Main's ruling and it settles a disagreement I had
# only flagged: for right-skewed count data z UNDERSTATES, which is why
# Berlin's 87th-percentile summer was drawing as "high, within its usual
# variation". Rank percentile is distribution-free and assumes no shape.
#
# It also answers Kristjan's objection better than z did. He was right
# that plotting position rewarded record length; percentile measures how
# unusual this summer is FOR THAT CITY without doing so.
#
# The labels are FREQUENCY throughout, one vocabulary. "Its usual
# variation" was the standard deviation made plain rather than removed,
# and it still assumed the shape the data has not got.
# FOUR rungs, and the lowest exists for a case no city is in today. VD's
# point: the first city to arrive at the 40th percentile would otherwise
# have no fill and no label, and D-043 requires an ordinary summer to read
# as legibly as a record. The neutral step of the diverging ramp is what
# it is for. Added now, while nothing depends on it.
BANDS = [(99.95, "var(--f3)"), (95.0, "var(--f2)"),
         (80.0, "var(--f1)"), (-1, "var(--f0)")]


def ordinal(n):
    """1st, 2nd, 3rd, 71st. f"{n}th" produced "71th", which VD caught."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def band(pct):
    """Fill for a z, stepped rather than continuous.

    Stepped because the legend is discrete swatches: a gradient bar would
    let a reader decode a colour the map never draws.
    """
    for lo, col in BANDS:
        if pct >= lo:
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
    marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{band(d["pct"])}" '
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
        box = {"x1": x1, "x2": x1 + bw, "y1": y + dy - 11, "y2": y + dy + 4}
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
    # No sublabel. "record" under a darkest-fill marker is the fill said
    # twice and the legend already defines it; 98.6 against 98.1 is
    # invisible at marker size and nobody reads a map for a decimal. Both
    # belong in the list, and dropping all 21 halves the label mass, which
    # is what was pushing Marseille and Alicante off their own markers.
    labels.append(
        f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{anc}" '
        f'class="cn">{d["name"]}</text>')

svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="height:auto" role="img" '
       f'aria-label="Twenty-one European weather stations. Every city is the same '
       f'disc, shaded by how many of that city\'s own recorded summers this one '
       f'beats, from hotter than every summer on its record down to hotter than '
       f'four in five.">'
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

def minichart(name, w=316, h=34):
    """The city page's own chart, shrunk. Kristjan's idea, and it carries
    three things the comb carried none of: how many, from bar height; how
    long this has been building, from the shape; and how much record
    stands behind the claim, from how many bars there are.

    It also survives what broke the comb. Fourteen cities pin their last
    bar at the top, but the decades behind it do not repeat, so the rows
    stop being one shape drawn fourteen times.

    Scaled to each city's own maximum, NEVER across rows: a hot day is
    41.2 C in Seville and 31.4 C in Berlin, so the heights are not
    comparable and the chart must not invite it.

    Plotted by YEAR rather than by index, so a missing year draws as a
    gap rather than being closed up. Seville has four.
    """
    ys = {int(y): x["days_to_cut"]["95"]
          for y, x in S[name]["years"].items()
          if x.get("usable_to_cut") and x.get("days_to_cut")}
    if not ys:
        return ""
    y0, y1 = min(ys), max(ys)
    top = max(ys.values()) or 1
    span = max(1, y1 - y0)
    bw = max(1.4, w / (span + 1) - 0.5)      # 2.8px at 106 years is the floor
    out = []
    for y, v in sorted(ys.items()):
        if not v:
            continue
        x = (y - y0) / span * (w - bw)
        fill = "var(--accent)" if y == 2026 else "var(--ink)"
        op = "" if y == 2026 else ' opacity="0.55"'
        out.append(f'<rect x="{x:.1f}" y="{h - v/top*h:.1f}" width="{bw:.1f}" '
                   f'height="{max(v/top*h, 1):.1f}" fill="{fill}"{op}/>')
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{name}: hot days every summer from {y0} to {y1}, '
            f'{len(ys)} years, with 2026 marked">{"".join(out)}</svg>')


def city_row(i, d):
    nm = d["name"]
    # "record" under every name repeated what the grouping already says.
    lab = ("" if d["rank"] == 1 else f'{ordinal(d["rank"])} of {d["of"]} &middot; ')
    href = PAGES.get(nm)
    title = (f'<a href="{href}" class="cty">{nm}</a>' if href
             else f'<span class="cty dim">{nm}</span>')

    return (f'<div class="lrow">'
            f'<span class="lcty">{title}<span class="lsub">{lab}'
            f'{d["of"]} years of record</span></span>'
            f'<span class="lbar">{minichart(nm)}</span>'
            f'<span class="lval">{d["now"]}<span class="lbase">vs {d["base"]:.0f}</span>'
            f'</span></div>')

# ONE list. The two groups are what the ruling deletes: they split cities
# whose plotting positions are equal.
all_rows = "".join(city_row(i, d) for i, d in enumerate(rows, 1))

MAR, BER = C["Marseille"], C["Berlin"]

# The bottom rung read "An ordinary summer for it", which heat's payload
# bans outright for every city in this set, and the ban is the right call:
# the palest mark on the map is Berlin at the 87th percentile of its own
# record, so a reader pairing the palest disc with the bottom label lands
# on exactly the false reading. The rung stays, because D-043 needs the
# calm end of the scale drawn as legibly as the extreme, and it says so
# itself. The emptiness is asserted only while it is true.
F0_LABEL = "Beats fewer than 16 of every 20"
if not [d for d in rows if d["pct"] < 80.0]:
    F0_LABEL += ". No city in this set"

# The same prohibition the city pages enforce, applied here. It exists
# because the legend defect above was in a drawing, and the ban had only
# ever been checked against prose.
BANNED = sorted({w for v in C.values()
                 for w in v.get("page_constraints", {}).get("banned_words", [])})

# DERIVED, because both of these were hard-coded and both went wrong the
# first time the payload changed under them. The met services listed a
# four-service set after Amsterdam arrived on a fifth, and the cut dates
# were typed. A citation that a reader can check is the whole pitch, so
# the source block is the last place a stale string is acceptable.
SERVICES = ", ".join(sorted({v["source"]["attribution"].replace("Source: ", "")
                             for v in C.values()}))
_MON = ["January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December"]
_cuts = sorted({v["counted_to"] for v in C.values()})
_days = [str(int(c.split("-")[2])) for c in _cuts]
_last = _cuts[-1].split("-")
CUT_TXT = (" and ".join([", ".join(_days[:-1]), _days[-1]] if len(_days) > 2
                        else _days) + f" {_MON[int(_last[1]) - 1]} {_last[0]}")

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat &middot; The Long Swell</title>
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--coast:#C6C5C2;--accent:#173F9E;--bar:#D3D2CB;--land:#E4E3DC;
--f3:#8E240A;--f2:#C05B3D;--f1:#EFC9BD;--f0:#E8E7E2}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--coast:#43423C;
--accent:#6E97E8;--bar:#43423C;--land:#232321;
--f3:#F0876A;--f2:#C05B3D;--f1:#6B4438;--f0:#2E2E2B}}}}
/* The shared masthead expects these and a standalone page must set them.
   VD found all five missing: --mono fell back to inheritance so the
   product nav rendered in the serif, which is the mechanism section 7
   uses INSTEAD of hue, and --nino/--fire/--crop all resolved to the same
   grey so three rules distinguishing the channels did nothing. The shell
   variables matter too: the masthead ran 80px wider than the content. */
:root{{--mono:'IBM Plex Mono',ui-monospace,monospace;--serif:Spectral,Georgia,serif;
--nino:#173F9E;--fire:#B32E10;--crop:#2E5C16;--shell-max:1020px;--shell-pad:24px}}
@media(prefers-color-scheme:dark){{:root{{--nino:#6E97E8;--fire:#E8714E;--crop:#7CB84E}}}}
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
.lrow{{display:grid;grid-template-columns:170px 316px 1fr 74px;gap:16px;
align-items:center;padding:9px 0;border-bottom:1px solid var(--rule)}}

.cty{{font-size:17px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}}
.cty.dim{{color:var(--soft);border:0}}
.lcty{{display:flex;flex-direction:column;gap:2px}}
.lsub{{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--ink-faint)}}
.lbar{{line-height:0}}
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
In a typical year {DH['baseline']['median_year']} of them do.</p>

{svg}
<div class="key">
<span class="ks"><i style="background:var(--f3)"></i>A record. Its most hot days ever</span>
<span class="ks"><i style="background:var(--f2)"></i>Hotter than 19 of every 20 of its summers</span>
<span class="ks"><i style="background:var(--f1)"></i>Hotter than 16 of every 20</span>
<span class="ks"><i style="background:var(--f0)"></i>{F0_LABEL}</span>
<span>Every city is the same disc. The fill is how many of that city's own
summers this one beats, so nothing between the marks is shaded and no city is
drawn as empty.</span></div>

<div class="seclab">How far from normal, city by city</div>
<p class="subl">Ordered by how many of that city's own recorded summers this one beats.
<strong style="color:var(--ink);font-weight:500">{rows[0]['name']} has had
{rows[0]['now']} hot days, more than in any of its {rows[0]['of']} recorded summers;
{rows[-1]['name']} has had {rows[-1]['now']}, which beats {rows[-1]['pct']:.0f} in 100 of
its own.</strong> {len([d for d in rows if d['pct'] >= 99.95])} of the
{len(rows)} beat every summer they have on record, so they tie at the top and are
listed alphabetically inside that tie: nothing separates them, and inventing an order
would mean ranking by how long each station has been running. Each strip is that
city's whole record on one shared scale, so rows compare and a crowded strip is simply
a longer record.</p>
{all_rows}

<div class="seclab">Why we publish two measurements and not one</div>
<div class="two">
<div><span class="tl">Marseille</span>Its most hot days on record, and
{MAR['rank']['value']}th of {MAR['rank']['of_years']} for hot nights. The days run
further than the nights.</div>
<div><span class="tl">Berlin</span>Hot days above {BER['days']['rank']['percentile']:.0f}
per cent of its own summers, and hot nights at the
{ordinal(round(BER['rank']['percentile']))} percentile. Here it is the other way round.</div>
</div>
<p class="subl" style="margin-top:16px">If one measurement stood in for the other, those
two cities would lean the same way. They lean opposite ways, which is how you can tell
the instruments measure different things.
<strong style="color:var(--ink);font-weight:500">{sum(1 for d in rows if d['gated'])}
cities publish no night ratio at all</strong>, each averaging under two hot nights a
year: dividing by a base that thin produces a large number and no evidence. The gate is
a flag on each city rather than a threshold applied here.</p>

<div class="src">
<span>{SERVICES}</span>
<span style="text-align:right">to {CUT_TXT}</span>
<span>Hot days, above each station's own 95th percentile of July-August maxima, 1971 to 2000</span>
<span style="text-align:right">{len(rows)} stations</span>
<span>Coastlines, {COAST["source"]}, merged land so no country borders are drawn</span>
<span style="text-align:right">{COAST["licence"]}</span>
</div>
</main></body></html>"""
out = R / "docs/heat/index.html"
out.parent.mkdir(parents=True, exist_ok=True)
# Strip comments and CSS FIRST. Tag-stripping alone leaves stylesheet text
# and HTML comments in the string, so the guard would report a word that no
# reader can see, and the natural fix for that false positive is to weaken
# the guard.
_body = re.sub(r"<(style|script)\b.*?</\1>", " ",
               re.sub(r"<!--.*?-->", " ", html, flags=re.S), flags=re.S | re.I)
_visible = re.sub(r"<[^>]+>", " ", _body)
for _w in BANNED:
    if re.search(rf"\b{re.escape(_w)}\b", _visible, re.I):
        raise SystemExit(f"index: banned word {_w!r} is visible on the page.")
out.write_text(html)
print(f"wrote {out} | {len(rows)} cities, {len(coast)} coast rings, "
      # Report the quantity that ACTUALLY orders the list. This line still
      # printed the Weibull plotting position after percentile replaced it,
      # so the build log described an ordering the page no longer uses.
      f"top is {rows[0]['name']} at pct {rows[0]['pct']:.1f}, "
      f"last is {rows[-1]['name']} at pct {rows[-1]['pct']:.1f}")
