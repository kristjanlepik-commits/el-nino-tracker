"""Front page mockup: one slot per channel, one map, Notes as its own element.

MOCKUP ONLY. Writes to design/mockups/, never to docs/. D-146 gates the build
on Kristjan seeing this first.

Emits three files from ONE component, which is the point of the exercise:

    frontpage.html          the five real payloads, 2026-08-11
    frontpage_quiet.html    every channel quiet
    frontpage_record.html   every channel at a record

The last two are product's acceptance test. A front page that only reads well
when the news is loud is advocacy, and the way that failure hides is that
nobody renders the calm case until the calm week arrives.

Usage:  .venv/bin/python design/make_frontpage_mockup.py
"""
import json
import sys
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

OUT = ROOT / "design" / "mockups"


# --------------------------------------------------------------------------
# Slot data. Each channel in ITS OWN UNITS. No cross-channel ranking anywhere:
# there is no score, no ordering by severity, no shared scale. The row order
# below is fixed and editorial, not a ranking.
# --------------------------------------------------------------------------
def live_slots():
    """Read the five real payloads. Nothing is fetched; these are on disk."""
    N = json.load(open(ROOT / "heat/data/city_nights.json"))
    dh = N["day_headline"]
    floor = "at least " if (N.get("coverage") or {}).get("counts_are_floors") else ""

    ev = json.load(open(ROOT / "data/events.json"))["events"]
    n_anom = sum(1 for e in ev if e.get("anomalous"))

    crops = json.load(open(ROOT / "crops/data/stress_current.json"))
    recs = [(p["place"], r) for p in crops["places"]
            for r in (p.get("regions") or []) if r.get("rank") == 1]
    n_reg, n_ctry = len(recs), len({p for p, _ in recs})

    meta = json.load(open(ROOT / "docs/briefs/2026-08-10/meta.json"))
    hb = meta["headline_buckets"]

    return [
        dict(ch="El Niño", href="elnino/", state="reporting",
             head="A peak above +2.0&nbsp;°C is settled. "
                  f"<b>{hb['record_>3.5']['mid']}%</b> for a peak beyond "
                  "+3.5&nbsp;°C.",
             unit="probability, consensus of four agencies",
             when="week of 10 August"),
        dict(ch="Heat", href="heat/", state="reporting",
             head=f"<b>{floor}{dh['records']}</b> of {dh['of_cities']} cities have "
                  "had more hot days than in any year on record.",
             unit="days above each city's own 95th percentile",
             when="to 11 August"),
        dict(ch="Fires", href="fires/", state="reporting",
             head=f"<b>{n_anom}</b> countries are clear of their own record week.",
             unit="detections against the same week, 13 earlier years",
             when="4 to 10 August"),
        dict(ch="Crops", href="crops/", state="reporting",
             head=f"<b>{n_reg}</b> crop regions in {n_ctry} countries are at their "
                  "worst on record for this point in the season.",
             unit="vegetation and water, each region against its own 26 years",
             when="ten days to 31 July"),
        dict(ch="Floods", href="floods/", state="cannot_say",
             head="Manila had its second wettest week in 27 years. Whether it "
                  "flooded, we cannot say.",
             unit="rainfall, and flood extent where the satellite can see it",
             when="2 to 8 August"),
    ]


CHANNELS = [("El Niño", "elnino/"), ("Heat", "heat/"), ("Fires", "fires/"),
            ("Crops", "crops/"), ("Floods", "floods/")]

QUIET_HEADS = {
    "El Niño": ("The four agencies agree on a peak near +1.1&nbsp;°C, "
                     "ordinary for an El Niño year.",
                     "probability, consensus of four agencies"),
    "Heat": ("No city in the set has had more hot days than in an earlier year.",
             "days above each city's own 95th percentile"),
    "Fires": ("No country is clear of its own record week.",
              "detections against the same week, 13 earlier years"),
    "Crops": ("No crop region is at its worst on record for this point in the "
              "season.",
              "vegetation and water, each region against its own 26 years"),
    "Floods": ("Nothing to report. Rainfall is within the usual range everywhere "
               "we watch.",
               "rainfall, and flood extent where the satellite can see it"),
}

RECORD_HEADS = {
    "El Niño": ("<b>99%</b> for a peak beyond +3.5&nbsp;°C, the highest "
                     "rung we publish.",
                     "probability, consensus of four agencies"),
    "Heat": ("<b>All 37</b> cities have had more hot days than in any year on "
             "record.", "days above each city's own 95th percentile"),
    "Fires": ("<b>94</b> countries are clear of their own record week.",
              "detections against the same week, 13 earlier years"),
    "Crops": ("<b>229</b> crop regions in 68 countries are at their worst on "
              "record for this point in the season.",
              "vegetation and water, each region against its own 26 years"),
    "Floods": ("<b>Six</b> regions are at their wettest week in 27 years.",
               "rainfall, and flood extent where the satellite can see it"),
}


def synthetic(state, heads):
    return [dict(ch=c, href=u, state=state, head=heads[c][0], unit=heads[c][1],
                 when="week of 10 August") for c, u in CHANNELS]


# --------------------------------------------------------------------------
# The component. ONE function, five instances, four states.
# --------------------------------------------------------------------------
STATE_TAG = {
    "reporting": "",
    "quiet": "quiet this week",
    "cannot_say": "one instrument cannot answer",
    "awaiting_data": "not yet reporting",
}


def slot(s):
    tag = STATE_TAG[s["state"]]
    tag_html = '<em>%s</em>' % h(tag) if tag else ""
    return (
        '<a class="slot slot-{st}" href="{href}">'
        '<span class="ch">{ch}{tag}</span>'
        '<span class="sh">{head}</span>'
        '<span class="su">{unit}</span>'
        '<span class="sw">{when}</span></a>'
    ).format(st=s["state"], href=h(s["href"]), ch=h(s["ch"]), tag=tag_html,
             head=s["head"], unit=h(s["unit"]), when=h(s["when"]))


# --------------------------------------------------------------------------
# The map. docs/world-map.svg is equirectangular on an 800x400 viewBox, so a
# mark is a two-line projection and needs no library.
#
# THE ONE THING THE BUILD NEEDS THAT DOES NOT EXIST YET: not one of the five
# payloads carries a coordinate. Heat has city names, fires and crops have
# region and country names, floods has a named region. The places below are
# real and are read from those payloads; their POSITIONS are a lookup I wrote
# by hand for the mockup. A real build needs each channel to emit lat/lon
# beside the name, because a design chat geocoding other people's science is
# exactly the seam D-030 exists to prevent.
# --------------------------------------------------------------------------
def project(lat, lon):
    return ((lon + 180.0) / 360.0 * 800.0, (90.0 - lat) / 180.0 * 400.0)


PLACES = {
    # heat, the 23 record cities (a legible subset; the rest overlap these)
    "London": (51.51, -0.13), "Paris": (48.86, 2.35), "Vienna": (48.21, 16.37),
    "Munich": (48.14, 11.58), "Zurich": (47.37, 8.54), "Lyon": (45.76, 4.84),
    "Marseille": (43.30, 5.37), "Bilbao": (43.26, -2.93),
    "Malaga": (36.72, -4.42), "Palma": (39.57, 2.65), "Cologne": (50.94, 6.96),
    "Bordeaux": (44.84, -0.58), "Toulouse": (43.60, 1.44),
    # fires
    "Georgia": (42.0, 43.4), "Serbia": (44.0, 20.9), "Spain": (40.4, -3.7),
    "United Kingdom": (54.0, -2.0), "France": (46.6, 2.4),
    "Germany": (51.0, 10.4), "Belgium": (50.8, 4.5), "Indonesia": (-2.0, 118.0),
    "India": (22.0, 79.0), "United States of America": (39.0, -98.0),
    "Venezuela": (7.0, -66.0), "Cuba": (21.5, -79.0), "Botswana": (-22.0, 24.0),
    "South Africa": (-29.0, 25.0), "Turkmenistan": (39.0, 59.0),
    # crops
    "Sudan": (15.0, 30.0), "Chad": (15.0, 19.0), "Niger": (17.0, 8.0),
    "Mali": (17.0, -4.0), "Ethiopia": (9.0, 40.0), "Uganda": (1.0, 32.0),
    "Rwanda": (-2.0, 30.0), "Burundi": (-3.0, 30.0),
    "Democratic Republic of the Congo": (-3.0, 23.0), "Congo": (-1.0, 15.0),
    "Angola": (-12.0, 17.0), "Namibia": (-22.0, 17.0),
    "United Republic of Tanzania": (-6.0, 35.0), "Egypt": (27.0, 30.0),
    "Libya": (27.0, 17.0), "Yemen": (15.0, 48.0), "Oman": (21.0, 57.0),
    "Iran (Islamic Republic of)": (32.0, 53.0), "Pakistan": (30.0, 70.0),
    "China": (35.0, 105.0), "Thailand": (15.0, 101.0), "Viet Nam": (16.0, 108.0),
    "Malaysia": (4.0, 102.0), "Philippines": (13.0, 122.0),
    "Papua New Guinea": (-6.0, 147.0), "Russian Federation": (60.0, 90.0),
    "Ukraine": (49.0, 32.0), "Türkiye": (39.0, 35.0), "Peru": (-10.0, -76.0),
    "Chile": (-33.0, -71.0), "Ecuador": (-1.0, -78.0), "Colombia": (4.0, -73.0),
    "Suriname": (4.0, -56.0), "Honduras": (15.0, -87.0),
    "Nicaragua": (13.0, -85.0),
    # floods, and the Niño 3.4 box the El Niño channel measures
    "Manila": (14.6, 121.0), "Niño 3.4": (0.0, -150.0),
}


def marks_for(names):
    """Uniform marks, deduped by position. Two channels reporting the same
    country is one place on a map that only says where."""
    seen, out = set(), []
    for n in names:
        if n in PLACES:
            xy = project(*PLACES[n])
            k = (round(xy[0], 1), round(xy[1], 1))
            if k not in seen:
                seen.add(k)
                out.append(xy)
    return out


def live_marks():
    N = json.load(open(ROOT / "heat/data/city_nights.json"))
    names = list(N["day_headline"]["record_cities"])
    ev = json.load(open(ROOT / "data/events.json"))["events"]
    names += [e["region"] for e in ev if e.get("anomalous")]
    crops = json.load(open(ROOT / "crops/data/stress_current.json"))
    names += [p["place"] for p in crops["places"]
              if any(r.get("rank") == 1 for r in (p.get("regions") or []))]
    names += ["Manila", "Niño 3.4"]
    return marks_for(names)


WORLD = (ROOT / "docs" / "world-map.svg").read_text()
_body = WORLD.split("</rect>")[-1]
_body = _body[_body.index("<g"):_body.rindex("</svg>")]
# The committed map ships hard-coded greys. Repoint them at the tokens so the
# mockup cannot drift from the palette the rest of the site renders in.
WORLD_BODY = (_body.replace('fill="#cfcdc2"', 'fill="var(--paper-sunk)"')
                   .replace('stroke="#b8b6ab"', 'stroke="var(--rule)"'))


def page(slots, marks, title, stand, note=True, invented=None):
    rows = "".join(slot(s) for s in slots)
    mk = "".join('<circle class="mk" cx="%.1f" cy="%.1f" r="3.4"/>' % xy
                 for xy in marks)
    # The calm week is not a broken map. An empty map under a heading that
    # promises marks reads as a rendering failure, which is the same class of
    # error as an absent qualifier: nothing is wrong, and nothing says so.
    # Found by rendering the quiet case, which is what the quiet case is for.
    if marks:
        map_head = "Where something is happening this week"
        map_note = ("Every mark is the same size. This map says WHERE, never how "
                    "much: sizing marks across five instruments would compare a "
                    "fire multiple with a heat percentile, which is a claim none "
                    "of them makes. Magnitude is in the rows below, each in its "
                    "own units.")
    else:
        map_head = "Nothing to mark this week"
        map_note = ("The map is empty because no channel is reporting anything "
                    "unusual, not because it failed to draw. Every instrument "
                    "reported; each is in its usual range.")

    # These files are now one click from the admin home page, which
    # discovers local boards by rule. A page carrying "All 37 cities" and
    # "99%" that someone opens cold reads as this week until they find the
    # small print, and "mockup, not published" does not say the FIGURES are
    # invented. The banner does, at the top, before anything numeric.
    banner = ('<div class="invented"><b>Invented numbers.</b> %s Nothing on '
              'this page is a measurement.</div>' % h(invented)) if invented else ""

    note_block = """
<div class="note">
<div class="k">Latest note</div>
<h2>How bad is it?</h2>
<div class="by">Kristjan Lepik &middot; 10 August 2026</div>
<p>This year a strong El Ni&ntilde;o started. Europe had its heatwaves and its
fires. I started to wonder - how bad is it?</p>
<span class="more">Read the note</span>
</div>""" if note else ""

    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} &middot; mockup</title>
<style>
{faces}
:root {{ {vars} }}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink-soft);
 font-family:"{prose}",Georgia,serif;font-size:17px;line-height:1.6;
 -webkit-font-smoothing:antialiased}}
main{{max-width:900px;margin:0 auto;padding:30px 26px 90px}}
.invented{{background:var(--ink);color:var(--paper);padding:11px 15px;
 margin:0 0 22px;font-family:"{data}",monospace;font-size:12px;line-height:1.55;
 letter-spacing:.02em}}
.invented b{{letter-spacing:.09em;text-transform:uppercase;font-size:11px}}
.eyebrow{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink-faint)}}
h1{{font-weight:400;font-size:38px;line-height:1.12;color:var(--ink);
 margin:14px 0 0;max-width:22ch;letter-spacing:-.01em}}
.stand{{margin:14px 0 0;max-width:60ch;font-size:18px}}
.maplab{{margin-top:40px}}
.mapnote{{font-family:"{data}",monospace;font-size:11px;color:var(--ink-faint);
 margin:10px 0 0;max-width:76ch;line-height:1.75}}
.slots{{margin-top:36px;border-top:3px solid var(--ink)}}
.slot{{display:grid;grid-template-columns:120px minmax(0,1fr) 148px;gap:20px;
 padding:18px 0 17px;border-bottom:1px solid var(--rule);text-decoration:none;
 color:inherit;align-items:baseline}}
.slot:hover .sh{{color:var(--nino)}}
.ch{{font-family:"{data}",monospace;font-size:10px;letter-spacing:.18em;
 text-transform:uppercase;color:var(--ink)}}
.ch em{{display:block;font-style:normal;letter-spacing:.11em;font-size:9px;
 line-height:1.5;color:var(--ink-faint);margin-top:6px}}
.sh{{font-size:18px;line-height:1.45;color:var(--ink-soft);text-wrap:pretty}}
.sh b{{color:var(--ink);font-weight:500;font-variant-numeric:tabular-nums}}
.su{{grid-column:2;font-family:"{data}",monospace;font-size:11px;
 color:var(--ink-faint);margin-top:-4px}}
.sw{{font-family:"{data}",monospace;font-size:11px;color:var(--ink-faint);
 text-align:right;white-space:nowrap}}
/* A channel that cannot answer keeps its full weight and its full space.
   Dimming it would make "we do not know" read as "nothing happened", and
   those are the two things this site most needs to keep apart. */
.slot-cannot_say .ch em{{color:var(--ink)}}
.note{{margin-top:46px;border-top:3px solid var(--ink);padding-top:17px}}
.note .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink-faint)}}
.note h2{{font-weight:400;font-size:26px;color:var(--ink);margin:10px 0 5px}}
.note .by{{font-family:"{data}",monospace;font-size:11px;letter-spacing:.13em;
 text-transform:uppercase;color:var(--ink-faint)}}
.note p{{margin:11px 0 0;max-width:62ch}}
.note .more{{display:inline-block;margin-top:11px;font-family:"{data}",monospace;
 font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
 color:var(--ink);border-bottom:1px solid var(--rule);padding-bottom:2px}}
svg .land{{fill:var(--paper-sunk)}}
svg .mk{{fill:var(--ink)}}
@media (max-width:640px){{
 h1{{font-size:29px}}
 .slot{{grid-template-columns:1fr;gap:7px}}
 .su,.sw{{grid-column:1;text-align:left;margin-top:0}}
 .ch em{{display:inline;margin-left:10px}}
}}
</style></head><body><main>

{banner}<div class="eyebrow">The Long Swell &middot; mockup, not published</div>
<h1>{title}</h1>
<p class="stand">{stand}</p>

<div class="eyebrow maplab">{map_head}</div>
<svg viewBox="0 22 800 330" width="100%" style="height:auto;margin-top:12px"
 role="img" aria-label="World map with uniform marks showing where each channel
 is reporting this week. Mark size carries no meaning; magnitude is in the rows
 below, in each channel's own units.">
{world}
{marks}
</svg>
<p class="mapnote">{map_note}</p>

<div class="slots">{rows}</div>
{note}

</main></body></html>""".format(
        banner=banner, title=h(title), stand=h(stand), rows=rows, marks=mk,
        note=note_block,
        world=WORLD_BODY, map_head=h(map_head), map_note=h(map_note),
        faces=T.font_faces_css("../../docs/fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "frontpage.html").write_text(page(
        live_slots(), live_marks(),
        "How big is this, actually?",
        "Five instruments, each measuring one thing against its own record. "
        "Nothing here is ranked against anything else."))

    # Acceptance test 1: the calm week. No map marks at all, because nothing is
    # happening, and the page still has to read as a finished object rather
    # than a broken one.
    (OUT / "frontpage_quiet.html").write_text(page(
        synthetic("quiet", QUIET_HEADS), [],
        "How big is this, actually?",
        "Five instruments, each measuring one thing against its own record. "
        "This week, none of them is unusual.",
        invented="An acceptance test: what the front page looks like in a week "
                 "when every channel is quiet."))

    # Acceptance test 2: everything at once. The test is that it does NOT
    # escalate: same type, same weights, no red, no exclamation.
    (OUT / "frontpage_record.html").write_text(page(
        synthetic("reporting", RECORD_HEADS), marks_for(PLACES),
        "How big is this, actually?",
        "Five instruments, each measuring one thing against its own record. "
        "Nothing here is ranked against anything else.",
        invented="An acceptance test: what the front page looks like if every "
                 "channel were at a record at once. It is not."))

    for f in ("frontpage.html", "frontpage_quiet.html", "frontpage_record.html"):
        print("wrote design/mockups/%s" % f)


if __name__ == "__main__":
    main()
