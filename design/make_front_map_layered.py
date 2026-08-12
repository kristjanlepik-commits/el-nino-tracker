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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# THE MAP LIVES IN templates/ NOW. This file renders the study;
# the page renders the same block. Two copies of a map is how a
# bar gets changed on one surface and not the other.
from templates.frontpage_map import (  # noqa: E402
    BAR, CROPS_XY, FLOOR, HEAT_R, SCRIPT, clears_bar, legend,
    map_block, marks, radius, place_label, xy)
import tokens as T  # noqa: E402

OUT = ROOT / "design" / "mockups"


def page(d):
    b = map_block(d)
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
svg .halo{{fill:none;stroke:var(--paper);stroke-width:2.4}}
svg .ring{{fill:none;stroke:var(--ink);stroke-width:2;opacity:0}}
/* BREACH 4, and it is what makes the field look like it runs onto the
   land. The ocean does stop at the coast and the field stops with it, but
   the land is nearly the same value as the page, so the boundary reads as
   a bleed rather than as a shore. A visible coastline turns the honest
   edge into an edge a reader can see, which is the whole of VD's point:
   the crop edges and the coast must not look identical. */
svg .landline path{{stroke:{rule_dark};stroke-width:.5;stroke-opacity:.45}}
svg a:focus-visible .ring{{opacity:1}}
svg .mln{{font-family:"{prose}",Georgia,serif;font-size:13px;fill:var(--ink);
 stroke:var(--paper);stroke-width:3;paint-order:stroke}}
svg .mlc{{font-family:"{data}",monospace;font-size:9.5px;fill:var(--ink-soft);
 stroke:var(--paper);stroke-width:3;paint-order:stroke}}
svg .ldr{{stroke:var(--ink-faint);stroke-width:1}}
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
<span class="r"><span>{n_rec} places past their own record</span>
<span>{n_shown} past the bar, drawn</span>
<span>{n_city} cities in one aggregate</span></span></div>
</div>

{svg}

<div class="shell">
{legend}
<p class="cap"><b>The map draws only what clears a stated bar: fires at
{bar_f}, crops with {bar_c}.</b> {n_below} more places passed their own
record this week and not the bar, and every one of them is counted by its
channel and on its channel page; the bar decides what is DRAWN, never what
is measured. It is a fixed number rather than one tuned each week to keep
the map tidy, so a busy week draws a busy map. One hue and one shape per
channel; a mark&rsquo;s size is that
channel&rsquo;s own severity measure: fires by the multiple of its same-week
mean, crops by regions at a record low, heat as one unsized aggregate.
<b>Sizes compare within a channel, never across channels</b>, because the
channels measure different things against different records: on this week's
data Chad at five record-low regions draws larger than every fire mark but
Georgia, and those two numbers share no scale at all. Channels differ
by shape as well as hue, so the layer split survives colourblindness and
greyscale; hue never carries a distinction alone. Click a legend entry to hide
or show its layer. Every mark is a link; hover or focus shows its claim with
its denominator. Places within their own normal range are counted in the line above rather
than drawn, which is what makes the map legible; the floor size still
applies to everything on it. The
dashed window is the extent of the Pacific SST field, which is the matplotlib
PNG in production. Coastline is the repo&rsquo;s own world-map.svg, drawn
directly rather than fetched, so the page needs no third party at read
time.</p>
</div>
{script}
</body></html>""".format(
        faces=T.font_faces_css("../../docs/fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA, nino_col=T.NINO,
        rule_dark=T.RULE_DARK,
        svg=b["svg"], legend=b["legend"], script=b["script"],
        n_rec=b["n_rec"], n_shown=b["n_shown"], n_below=b["n_below"],
        bar_f=b["bar_f"], bar_c=b["bar_c"],
        n_city=len(d["heat"]["cities"]))


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
