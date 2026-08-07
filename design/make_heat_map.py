"""The heat index map. 21 marks, no surface, no geography claimed in prose.

Constraints, all ratified rather than chosen here:

  colour by percentile within each city's own record, never absolute
  temperature, or the map just redraws the Mediterranean climate map
  quiet cities visibly quiet, NEVER absent: their presence is what makes
  this evidence rather than decoration
  21 marks, not a surface. We measured 21 stations. Colouring a landmass
  would claim we measured the landmass, and there is no gridded product
  behind this metric
  no band, no latitude, no direction stated anywhere in prose. Two of
  five outside the band being records is not evidence of concentration,
  it is a sample of five. The map shows what it shows

THE ENCODING PROBLEM, and it is the whole design.

Every city sits between the 87th and 100th day percentile. Mapping that
range onto area or tone makes all 21 marks look identical, which is
false in the other direction: it would say nothing distinguishes them.

So the mark carries the RECORD, not the percentile: filled where 2026 is
that city's hottest on record for days, open ring where it is not. That
is a real distinction, 14 against 7, and it matches the fires map
convention so the two channels read alike. The percentile is on the
label, where a number belongs.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())
CO = json.loads((R / "design/city_coords.json").read_text())["cities"]
C, DH = N["cities"], N["day_headline"]
RECORDS = set(DH["record_cities"])

BOX = {"ES": (36.0, 43.8, -9.3, 4.3), "FR": (41.3, 51.1, -5.2, 9.6),
       "DE": (47.2, 55.1, 5.8, 15.1), "AT": (46.3, 49.1, 9.5, 17.2)}
for n, v in C.items():
    if n not in CO:
        raise SystemExit(f"{n} has no coordinate in design/city_coords.json")
    la, lo = CO[n]["lat"], CO[n]["lon"]
    s, nn, w, e = BOX[v["country"]]
    if not (s <= la <= nn and w <= lo <= e):
        raise SystemExit(f"{n} at {la},{lo} is outside {v['country']}; "
                         f"check for a transposed pair")

W, H, PAD = 760, 660, 58
LATS = [CO[n]["lat"] for n in C]
LONS = [CO[n]["lon"] for n in C]
LA0, LA1, LO0, LO1 = min(LATS) - 1.4, max(LATS) + 1.4, min(LONS) - 2.2, max(LONS) + 2.2
# Equirectangular with a cos(lat) correction, so Spain is not stretched
# sideways relative to Germany. Not a projection anyone would defend for
# a real atlas; correct enough for 21 labelled marks.
import math
KX = math.cos(math.radians((LA0 + LA1) / 2))
px = lambda lo: PAD + (lo - LO0) * KX / ((LO1 - LO0) * KX) * (W - 2 * PAD)
py = lambda la: PAD + (LA1 - la) / (LA1 - LA0) * (H - 2 * PAD)

# Label placement, per city, chosen by eye against a render. Cartography
# rather than data: the marks are computed, the labels are hand-placed
# because 21 stations in western Europe crowd in three known clusters
# (the Riviera, the south-east Spanish coast, and Andalusia) and no
# generic rule resolves all three. (dx, dy, anchor).
#
# The crude left/right rule this replaces put "Nice" on top of
# "Marseille record" and ran "Seville 8 of 76" through "Malaga record".
PLACE = {
    "Hamburg":     (13,   4, "start"),
    "Berlin":      (13,   4, "start"),
    "Cologne":     (-13,  4, "end"),
    "Frankfurt":   (13,   4, "start"),
    "Paris":       (13,   4, "start"),
    "Munich":      (13,   4, "start"),
    "Vienna":      (13,   4, "start"),
    "Lyon":        (13,   4, "start"),
    "Bilbao":      (-13,  4, "end"),
    "Montpellier": (-13, -6, "end"),
    "Marseille":   (-6,  26, "end"),      # below, clear of Nice
    "Nice":        (13,   8, "start"),
    "Zaragoza":    (-13,  4, "end"),
    "Barcelona":   (13,  10, "start"),
    "Madrid":      (-13,  4, "end"),
    "Valencia":    (-13,  4, "end"),
    "Palma":       (13,   4, "start"),
    "Alicante":    (13,   8, "start"),
    "Murcia":      (-13,  0, "end"),
    "Seville":     (-13, -8, "end"),      # up-left, clear of Malaga
    "Malaga":      (-13, 14, "end"),      # down-left
}

marks, labels = [], []
for n, v in sorted(C.items(), key=lambda kv: -CO[kv[0]]["lat"]):
    x, y = px(CO[n]["lon"]), py(CO[n]["lat"])
    r = v["days"]["rank"]
    rec = n in RECORDS
    if rec:
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7.5" fill="var(--accent)"/>')
    else:
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="var(--paper)" '
                     f'stroke="var(--ink)" stroke-width="1.8"/>')
    if n not in PLACE:
        raise SystemExit(f"{n} has no label placement in PLACE")
    dx, dy, anc = PLACE[n]
    sub = "record" if rec else f"{r['value']} of {r['of_years']}"
    labels.append(
        f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{anc}" class="cn">{n}</text>'
        f'<text x="{x+dx:.1f}" y="{y+dy+11:.1f}" text-anchor="{anc}" class="cs">{sub}</text>')

svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;height:auto" '
       f'role="img" aria-label="21 European cities, days above each city\'s own 95th '
       f'percentile">{"".join(marks)}{"".join(labels)}</svg>')

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat &middot; The Long Swell</title><style>
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:900px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.06;
letter-spacing:-.02em;color:var(--ink);margin:38px 0 14px;max-width:18ch;text-wrap:balance}}
.stand{{font-size:17.5px;line-height:1.62;max-width:62ch;margin:0}}
.key{{display:flex;gap:26px;align-items:center;margin:30px 0 6px;
font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-faint)}}
.key i{{display:inline-block;width:13px;height:13px;border-radius:50%;
vertical-align:-2px;margin-right:8px}}
.k1 i{{background:var(--accent)}}
.k2 i{{background:var(--paper);border:1.8px solid var(--ink)}}
.cn{{font-family:Spectral,serif;font-size:13.5px;fill:var(--ink)}}
.cs{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;fill:var(--ink-faint);
letter-spacing:.06em}}
.cap{{font-size:15.5px;line-height:1.6;max-width:70ch;margin:18px 0 0}}
</style></head><body><main>
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">21 cities &middot; to early August 2026</span></div>

<h1>How hot has the European summer been?</h1>
<p class="stand">Every city measured against its own record, never against
each other. A hot day is one at or above that city's own 95th percentile
for July and August, so {C['Seville']['days']['thresholds_c']['95']}&nbsp;&deg;C
in Seville and {C['Berlin']['days']['thresholds_c']['95']}&nbsp;&deg;C in Berlin.
<strong style="color:var(--ink);font-weight:500">{DH['records']} of the
{DH['of_cities']} have had more of them than in any year on record.</strong>
A typical year produces {DH['baseline']['median_year']}.</p>

<div class="key"><span class="k1"><i></i>Most on record</span>
<span class="k2"><i></i>Not a record, and still in its own top tenth</span></div>
{svg}
<p class="cap">Twenty-one weather stations, not a region: the marks are the
places we measured and the space between them is not shaded because we did
not measure it. Every city here is in the warmest tenth of its own history;
the open rings are the ones that are elevated without being the most extreme
they have ever been.</p>
</main></body></html>"""
out = R / "design/review/heat-map.html"
out.write_text(html)
print(f"wrote {out} | {len(C)} marks, {len(RECORDS)} filled, "
      f"{len(C)-len(RECORDS)} open | lat {LA0:.1f}-{LA1:.1f} lon {LO0:.1f}-{LO1:.1f}")
