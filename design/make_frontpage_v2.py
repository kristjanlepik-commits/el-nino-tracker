"""Front page v2: VD's layout, real payloads, production coastline.

MOCKUP ONLY. Writes design/mockups/, never docs/.

VD's comp is the base and it earns it in three places: the evidence column
beside every number, El Nino pulled out of the readings table because a
forecast has no rank in its own history, and the channels footer carrying
cadence and in-development state. All three are kept.

What this changes, each for a stated reason:

1. THE LEDE. "Three channels measured this week. All three are outside
   their normal range" answers how many of our instruments are unusual,
   which is a sentence about us. It is also the largest type on the site
   and contains no place, no magnitude and no date. Replaced with one
   clause per channel in that channel's own units, fixed order, no
   comparison between them, generated. It stays true on a calm week
   because each clause simply states its negative.

2. EVERY COUNT IS GENERATED. The comp typed five that have moved or were
   wrong: 20 Yemen regions (19), 1.2 Bilbao nights (1.4), 37 heat cities
   (41), "23 more" fires (18 anomalous), "20 more" crops (36 countries).

3. THE ATTRIBUTION COLUMN COLLAPSES when no channel in the set runs
   attribution, instead of leaving two rows trailing into white space that
   reads as missing data.

4. THE EL NINO BAND IS TYPOGRAPHIC. The comp gives it a blue rule and blue
   label. D-101 retired channel hue, and the layered map's own case is
   that hue should return on the MAP only, so a hued band on the page
   contradicts the argument being made for it.

5. UNIFORM MARKS ON THE REAL COASTLINE, because that is the thing being
   ruled on and neither file shows it: the comp omits the coastline, the
   layered study has it but also reverses D-146.

6. THE HEAT ROW IS THE SET, not a lead city. The comp names Bilbao. Heat
   emits no lead, so choosing one means inventing a cross-city ranking,
   which is the exact move the page refuses everywhere else. Heat's own
   emitted headline is a set statement, so the row shows that.

Usage:  .venv/bin/python design/make_frontpage_v2.py
"""
import json
import sys
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

OUT = ROOT / "design" / "mockups"


def load():
    d = {}
    d["heat"] = json.load(open(ROOT / "heat/data/city_nights.json"))
    d["coords"] = json.load(open(ROOT / "heat/data/station_coords.json"))
    d["fires_week"] = json.load(open(ROOT / "fires/data/current_week.json"))
    d["events"] = json.load(open(ROOT / "data/events.json"))["events"]
    d["crops"] = json.load(open(ROOT / "crops/data/stress_current.json"))
    d["meta"] = json.load(open(ROOT / "docs/briefs/2026-08-10/meta.json"))
    # meta.json carries the buckets; the observed value lives in the
    # snapshot. Reading it off meta returned None and the band printed
    # "n/a" beside two live percentages, which reads as a broken figure
    # rather than an absent one.
    d["snap"] = json.load(open(ROOT / "snapshots/2026-08-10.json"))
    return d


# --------------------------------------------------------------------------
# Marks. Uniform, r=3.4, from real coordinates where a channel emits them.
#
# I reported to product that no payload carries a coordinate. That was
# wrong, and wrong about the two densest layers: heat emits lat/lon for all
# 41 cities in station_coords.json with a coord_source per city, and fires
# carries lat/lon on 90 of its 94 countries in current_week.json. Crops is
# the real gap: design/country_centroids.json holds five entries, which is
# the lit set and nothing else, so the rest are hand-placed below and crops
# should emit them.
# --------------------------------------------------------------------------
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


def project(lat, lon):
    return ((lon + 180.0) / 360.0 * 800.0, (90.0 - lat) / 180.0 * 400.0)


def marks(d):
    pts, seen = [], set()

    def add(lat, lon):
        if lat is None or lon is None:
            return
        x, y = project(float(lat), float(lon))
        k = (round(x, 1), round(y, 1))
        if k not in seen:
            seen.add(k)
            pts.append((x, y))

    rc = set(d["heat"]["day_headline"]["record_cities"])
    for city, c in d["coords"].items():
        if city in rc:
            add(c.get("lat"), c.get("lon"))
    anom = {e["region"] for e in d["events"] if e.get("anomalous")}
    for c in d["fires_week"]["countries"].values():
        if c.get("name") in anom:
            add(c.get("lat"), c.get("lon"))
    for p in d["crops"]["places"]:
        if any(r.get("rank") == 1 for r in (p.get("regions") or [])):
            xy = CROPS_XY.get(p["place"])
            if xy:
                add(*xy)
    add(0.0, -150.0)                       # the Nino 3.4 box
    return pts


# --------------------------------------------------------------------------
# The readings. One row per channel, each in its own units, fixed order.
# --------------------------------------------------------------------------
def readings(d):
    rows = []

    ev = sorted([e for e in d["events"] if e.get("anomalous")],
                key=lambda e: -float(str(e.get("stat", "0")).rstrip("x") or 0))
    top = ev[0]
    geo = None
    for c in d["fires_week"]["countries"].values():
        if c.get("name") == top["region"]:
            geo = c
    # THE DENOMINATOR IS OBSERVATIONS, NOT CALENDAR SLOTS, and the two
    # absences are different in kind. Georgia holds 12 prior years; 2022 is
    # missing from the archive and 2021 is excluded deliberately as not
    # comparable, which fires declares in the payload. Product proposed "of
    # 15, two absent"; that is better than 15 and still merges a gap with a
    # choice, so both are named.
    _hist = (geo or {}).get("hist") or {}
    n_obs = (len(_hist) if isinstance(_hist, (dict, list))
             else int(_hist)) + 1
    span = (geo or {}).get("hist_expected", 0) + 1
    excl = (geo or {}).get("hist_excluded_for_comparability") or []
    gap = span - n_obs - len(excl)
    ev_bits = "same-week mean &middot; heaviest of %d observed weeks" % n_obs
    tail = []
    if gap:
        tail.append("%d missing from the archive" % gap)
    if excl:
        tail.append("%s excluded as not comparable" % ", ".join(excl))
    rows.append(dict(
        ch="Fires", place=top["region"], claim=top.get("title", ""),
        fig=top.get("stat", ""),
        ev=ev_bits + ("<br>of a %d-year span: %s" % (span, "; ".join(tail))
                      if tail else ""),
        src="NASA FIRMS SNPP &middot; week to 10 Aug", tag="attribution pending"))

    dh = d["heat"]["day_headline"]
    floors = (d["heat"].get("coverage") or {}).get("counts_are_floors")
    rows.append(dict(
        ch="Heat", place="%d cities" % dh["of_cities"],
        claim="More hot days than in any year on record",
        fig="%d" % dh["records"],
        ev="each against its own 95th percentile &middot; %sof %d measured"
           % ("at least, " if floors else "", dh["of_cities"])
           + "<br>station records, counted to the same date each year",
        src="", tag=""))

    lit = ["Angola", "Chad", "Philippines", "Sudan", "Yemen"]
    best, best_rank = None, 99
    for p in d["crops"]["places"]:
        if p["place"] in lit:
            r = (p.get("severity") or {}).get("rank")
            if r and r < best_rank:
                best, best_rank = p, r
    regs = best.get("regions") or []
    n1 = [r for r in regs if r.get("rank") == 1]
    sev = best.get("severity") or {}
    rows.append(dict(
        ch="Crops", place=best["place"],
        claim="%d of its %d regions at a record low"
              % (len(n1), len(regs)),
        fig="%d of %d" % (len(n1), len(regs)),
        ev="%s most stressed of %d observations, 2001-2026"
           % (_ord(sev.get("rank", 0)), sev.get("of", 0))
           + "<br>five instruments read together &middot; dekad to 31 July",
        src="", tag=""))
    return rows


def _ord(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def lede(d):
    """One clause per channel, own units, fixed order, no comparison.

    The state line product specified is right to refuse a superlative and
    wrong to stop there: "three channels measured" has no place, no
    magnitude and no date in it, and it is the largest type on the site.
    This says the same thing without ranking anything, because each clause
    is measured against that channel's own record and the order is fixed
    and editorial rather than derived.

    On a calm week each clause states its negative, so the shape of the
    page does not change when the news does.
    """
    dh = d["heat"]["day_headline"]
    floors = (d["heat"].get("coverage") or {}).get("counts_are_floors")
    n_fire = sum(1 for e in d["events"] if e.get("anomalous"))
    recs = [(p["place"], [r for r in (p.get("regions") or [])
                          if r.get("rank") == 1]) for p in d["crops"]["places"]]
    recs = [(p, r) for p, r in recs if r]
    n_reg = sum(len(r) for _, r in recs)

    out = []
    out.append("<b>%s%d of %d cities</b> have had more hot days than in any "
               "year on record." % ("At least " if floors else "",
                                    dh["records"], dh["of_cities"]))
    out.append("<b>%d countries</b> are past their own record fire week."
               % n_fire)
    out.append("<b>%d crop regions</b> are at their worst for this point in "
               "the season." % n_reg)
    return " ".join(out)


def page(d):
    rs = readings(d)
    # The chip column exists only if something in the SET uses it. Two rows
    # trailing into an empty cell reads as missing data; a column that is
    # not there reads as a column that does not apply.
    any_tag = any(r["tag"] for r in rs)
    cols = "128px minmax(0,1fr) 104px 268px" + (" 150px" if any_tag else "")

    def row(r, first):
        top = ("3px solid var(--ink)" if first else "1px solid var(--rule)")
        tag = ('<div style="text-align:right"><span class="chip">%s</span></div>'
               % h(r["tag"])) if any_tag and r["tag"] else (
            '<div></div>' if any_tag else "")
        return (
            '<div class="rr" style="border-top:%s;grid-template-columns:%s">'
            '<div class="rch">%s</div>'
            '<div class="rcl"><b>%s</b> &nbsp;<span>%s</span></div>'
            '<div class="rfg">%s</div>'
            '<div class="rev">%s</div>%s</div>'
            % (top, cols, h(r["ch"]), h(r["place"]), h(r["claim"]),
               h(r["fig"]), r["ev"], tag))

    rows = "".join(row(r, i == 0) for i, r in enumerate(rs))
    mk = "".join('<circle class="mk" cx="%.1f" cy="%.1f" r="3.4"/>' % xy
                 for xy in marks(d))
    world = (ROOT / "docs" / "world-map.svg").read_text()
    body = world.split("</rect>")[-1]
    body = body[body.index("<g"):body.rindex("</svg>")]
    body = (body.replace('fill="#cfcdc2"', 'fill="var(--paper-sunk)"')
                .replace('stroke="#b8b6ab"', 'stroke="var(--rule)"'))

    hb = d["meta"]["headline_buckets"]
    nino = (d["snap"].get("physical_state") or {}).get(
        "nino34_weekly_traditional")

    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Front page v2 &middot; real payloads</title>
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
.nav{{margin-left:auto;display:flex;flex-wrap:wrap;gap:8px 20px;
 font-family:"{data}",monospace;font-size:11px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--ink-soft)}}
.nav a{{color:inherit;text-decoration:none}}
.asof{{padding:10px 0 0;display:flex;flex-wrap:wrap;gap:6px 18px;
 font-family:"{data}",monospace;font-size:10px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--ink-faint)}}
.asof .r{{margin-left:auto;display:flex;flex-wrap:wrap;gap:4px 14px;
 font-variant-numeric:tabular-nums}}
h1{{margin:30px 0 0;font-weight:400;font-size:31px;line-height:1.3;
 letter-spacing:-.012em;color:var(--ink-soft);max-width:46ch;text-wrap:pretty}}
h1 b{{font-weight:500;color:var(--ink)}}
.stand{{margin:15px 0 0;font-size:17px;line-height:1.62;max-width:58ch;
 color:var(--ink-faint);text-wrap:pretty}}
.seclab{{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 16px;
 border-bottom:1px solid var(--rule);padding-bottom:9px;margin-top:36px;
 font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink)}}
.seclab .r{{margin-left:auto;letter-spacing:.14em;color:var(--ink-faint)}}
.mapnote{{font-family:"{data}",monospace;font-size:11px;line-height:1.7;
 color:var(--ink-faint);padding-top:8px;max-width:108ch}}
.rr{{display:grid;gap:20px;align-items:baseline;padding:15px 0}}
.rch{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.2em;
 text-transform:uppercase;color:var(--ink)}}
.rcl{{font-size:19px;color:var(--ink)}}
.rcl b{{font-weight:500}}
.rcl span{{color:var(--ink-soft)}}
.rfg{{font-family:"{data}",monospace;font-size:18px;font-weight:500;
 font-variant-numeric:tabular-nums;color:var(--ink);text-align:right}}
.rev{{font-family:"{data}",monospace;font-size:11px;line-height:1.6;
 color:var(--ink-faint)}}
.chip{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.14em;
 text-transform:uppercase;background:var(--paper-sunk);color:var(--ink-faint);
 padding:5px 7px;white-space:nowrap}}
.rend{{border-top:3px solid var(--ink)}}
.more{{display:flex;justify-content:space-between;gap:20px;padding-top:12px;
 font-family:"{data}",monospace;font-size:11px;line-height:1.7;
 color:var(--ink-faint)}}
.more a{{color:var(--ink);text-decoration:none;
 border-bottom:1px solid var(--rule)}}
/* TYPOGRAPHIC, NOT HUED. The comp gives this band a blue rule and a blue
   label; D-101 retired channel hue and the case being made for its return
   is scoped to map markers. */
.wave{{margin-top:40px;background:var(--paper-sunk);border-left:3px solid
 var(--ink);padding:16px 20px;display:flex;flex-wrap:wrap;align-items:baseline;
 gap:8px 20px}}
.wave .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.2em;
 text-transform:uppercase;color:var(--ink)}}
.wave .v{{font-size:17px;color:var(--ink)}}
.wave .v b{{font-family:"{data}",monospace;font-weight:600;
 font-variant-numeric:tabular-nums}}
.wave .r{{margin-left:auto;font-family:"{data}",monospace;font-size:10.5px;
 color:var(--ink-faint);font-variant-numeric:tabular-nums}}
.note{{margin-top:44px;border-top:3px solid var(--ink);padding-top:18px;
 display:grid;grid-template-columns:176px minmax(0,1fr);gap:20px}}
.note .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink)}}
.note .sub{{font-family:"{data}",monospace;font-size:10px;line-height:1.7;
 color:var(--ink-faint);margin-top:6px}}
.note .pull{{font-weight:500;font-size:26px;line-height:1.32;color:var(--ink);
 max-width:44ch;text-wrap:pretty}}
.note .by{{font-family:"{data}",monospace;font-size:11px;color:var(--ink-faint);
 margin-top:10px}}
.chn{{margin-top:44px;border-top:1px solid var(--rule);padding-top:16px}}
.chn .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink-faint);padding-bottom:10px}}
.chn .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
 gap:0 48px;font-size:15px}}
.chn .row{{border-top:1px solid var(--rule);padding:9px 0;display:flex;
 align-items:baseline;gap:14px;color:var(--ink-faint)}}
.chn .row .n{{font-family:"{data}",monospace;font-size:11px;letter-spacing:.16em;
 text-transform:uppercase;width:92px;color:var(--ink)}}
.chn .row .c{{margin-left:auto;font-family:"{data}",monospace;font-size:10px}}
.foot{{margin-top:40px;border-top:1px solid var(--rule);padding:16px 0 40px;
 display:flex;justify-content:space-between;gap:20px;
 font-family:"{data}",monospace;font-size:11px;line-height:1.7;
 color:var(--ink-faint)}}
svg .mk{{fill:var(--ink)}}
@media (max-width:820px){{
 .shell{{padding:0 20px}}
 h1{{font-size:23px}}
 .rr{{grid-template-columns:1fr !important;gap:6px}}
 .rfg{{text-align:left;font-size:22px}}
 .note{{grid-template-columns:1fr}}
 .chn .grid{{grid-template-columns:1fr}}
 .foot,.more{{flex-direction:column}}
}}
</style></head><body><div class="shell">

<div class="mast"><span class="wm">The Long Swell</span>
<span class="nav"><a href="#">El Ni&ntilde;o</a><a href="#">Fires</a>
<a href="#">Heat</a><a href="#">Crops</a><a href="#">Notes</a>
<a href="#">About</a></span></div>

<div class="asof"><span style="color:var(--ink)">Week of 2026-08-10</span>
<span class="r"><span>Fires through 08-10, daily</span>
<span>Heat through 08-11</span><span>Crops dekad to 07-31</span>
<span>El Ni&ntilde;o issue 08-10</span></span></div>

<h1>{lede}</h1>
<p class="stand">Every reading is measured against its own place&rsquo;s
history, and each says whether El Ni&ntilde;o is involved; most are not.
Channels are never ranked against each other.</p>

<div class="seclab">Where, this week
<span class="r">uniform marks &middot; magnitude is in the readings below</span></div>
<svg viewBox="0 22 800 330" width="100%" style="height:auto;margin-top:12px"
 role="img" aria-label="World map of this week's readings across heat, fires
 and crops, every marker the same size. The map answers where; magnitude is in
 the readings below, each in its channel's own units.">
{world}{marks}
</svg>
<p class="mapnote">Every mark is the same size, per D-146: the map answers
WHERE, and magnitude lives in the readings below. A marker cannot carry its
own denominator, so a sized mark would make a cross-instrument claim with
none of the evidence attached. Positions are the channels&rsquo; own
coordinates where they emit them, which is heat for all 41 cities and fires
for 90 of 94 countries; crops centroids are still design-side and should
move to the payload. Coastline is the production world-map.svg.</p>

<div class="seclab" style="border-bottom:none;margin-top:40px">The readings
&nbsp;&middot;&nbsp; one slot per channel
<span class="r">each row is its channel&rsquo;s own selection, with its
evidence beside it</span></div>
{rows}
<div class="rend"></div>
<div class="more"><span style="max-width:74ch">Chips mark attribution where a
channel runs it. Fires does; Heat and Crops do not assess attribution, so the
column is absent rather than empty.</span>
<span style="white-space:nowrap"><a href="#">Fires, {n_fire} countries
&rarr;</a> &nbsp;&middot;&nbsp; <a href="#">Heat, {n_city} cities &rarr;</a>
&nbsp;&middot;&nbsp; <a href="#">Crops, {n_ctry} countries &rarr;</a></span></div>

<div class="wave"><span class="k">The wave &nbsp;&middot;&nbsp; El Ni&ntilde;o
2026-27</span>
<span class="v"><b>{p25}%</b> chance of a peak beyond +2.5&nbsp;&deg;C,
<b>{p35}%</b> beyond +3.5</span>
<span class="r">Ni&ntilde;o 3.4 {n34} &middot; issue 2026-08-10 &middot;
this week&rsquo;s issue &rarr;</span></div>

<div class="note">
<div><div class="k">Notes</div>
<div class="sub">Written by hand, about what the instruments are showing.</div></div>
<div><div class="pull">Paris had 31 hot days by 8 August. In a typical summer
between 1961 and 1990, it had two.</div>
<div class="by">How bad is it? &middot; 10 August 2026 &middot; read the note
&rarr;</div></div></div>

<div class="chn"><div class="k">Channels &nbsp;&middot;&nbsp; each reads one
domain against its own baselines</div>
<div class="grid">
<div class="row"><span class="n">El Ni&ntilde;o</span><span>the winter peak,
tracked</span><span class="c">weekly</span></div>
<div class="row"><span class="n">Fires</span><span>hotspots vs same-week
baselines</span><span class="c">daily</span></div>
<div class="row"><span class="n">Heat</span><span>city days and nights vs
station records</span><span class="c">weekly</span></div>
<div class="row"><span class="n">Crops</span><span>crop regions vs their own
record</span><span class="c">every 10 days</span></div>
<div class="row"><span class="n">Notes</span><span>written by
hand</span><span class="c">occasional</span></div>
<div class="row"><span class="n" style="color:var(--ink-faint)">Floods,
Econ</span><span>each needs its own baseline first</span>
<span class="c">in development</span></div>
</div></div>

<div class="foot"><span>Lepik, K. (2026). The Long Swell. thelongswell.com
&middot; every issue archived, immutable &middot; disagreements surfaced, not
averaged</span>
<span style="letter-spacing:.14em;text-transform:uppercase">one email a week
&middot; subscribe</span></div>

</div></body></html>""".format(
        faces=T.font_faces_css("../../docs/fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA, lede=lede(d), rows=rows,
        world=body, marks=mk,
        n_fire=sum(1 for e in d["events"] if e.get("anomalous")),
        n_city=len(d["heat"]["cities"]),
        n_ctry=sum(1 for p in d["crops"]["places"]
                   if any(r.get("rank") == 1 for r in (p.get("regions") or []))),
        p25=hb["9715_>2.5"]["mid"], p35=hb["record_>3.5"]["mid"],
        n34=("%+.1f&nbsp;&deg;C" % nino) if nino is not None else "n/a")


def main():
    d = load()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frontpage_v2.html").write_text(page(d))
    print("wrote design/mockups/frontpage_v2.html")
    print("  lede:", lede(d).replace("<b>", "").replace("</b>", ""))


if __name__ == "__main__":
    main()
