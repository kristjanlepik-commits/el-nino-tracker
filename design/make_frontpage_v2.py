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
# The form, the promise and its CSS all come from run_brief so the
# front page cannot drift from /subscribe/. One string, two
# surfaces, which is the reason EMAIL_CAPTURE_PROMISE lives there
# rather than in the subscribe template.
# ONE MAP, NOT TWO. The front page draws the same block as the layered
# study, imported rather than reimplemented, so the bar cannot be changed on
# one surface and left on the other.
from design.make_front_map_layered import map_block  # noqa: E402
from run_brief import (email_capture_form,  # noqa: E402
                       EMAIL_CAPTURE_PROMISE, EMAIL_FORM_CSS)

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


def map_svg(d, nino34):
    """VD's map, drawn. Uniform SIZE, everything else as designed.

    My first pass implemented the constraint and dropped the design: dots on
    a coastline, no labels, no bracket, no window, no state fill. Uniform
    marks is one rule from D-146; it was never the whole drawing.

    What VD has and this now has:

      the calm denominator   every fires country we watch, drawn open, so a
                             dozen filled marks read as a quiet week rather
                             than as a broken map. Our own rule, from
                             crops_map.py.
      state in the fill      filled = past its own record, open = within it.
                             Uniform size throughout: the fill says WHICH,
                             the size says nothing.
      heat as ONE mark       dashed and unfilled, a locator for the whole
                             city set. VD's answer to Q8 and the best thing
                             in the comp: a set-level fill would assert one
                             state for 41 cities at once, and the per-city
                             states live on the Heat page. My first pass
                             drew 23 separate city dots, which is a
                             different claim and buries Europe.
      the Nino 3.4 bracket   with its observed value, on the box it names
      the SST window         dashed, the extent of the Pacific field, which
                             is the matplotlib PNG in production
      three named labels     one per channel, the reading the row carries
    """
    def xy(lat, lon):
        return ((lon + 180.0) / 360.0 * 800.0, (90.0 - lat) / 180.0 * 400.0)

    anom = {e["region"] for e in d["events"] if e.get("anomalous")}
    open_marks, lit_marks = [], []
    for c in d["fires_week"]["countries"].values():
        if c.get("lat") is None:
            continue
        (lit_marks if c.get("name") in anom else open_marks).append(
            xy(c["lat"], c["lon"]))
    seen = set()
    for p_ in d["crops"]["places"]:
        if any(r.get("rank") == 1 for r in (p_.get("regions") or [])):
            g = CROPS_XY.get(p_["place"])
            if g:
                lit_marks.append(xy(*g))

    def dots(pts, cls):
        out, seen_ = [], set()
        for x, y in pts:
            k = (round(x, 1), round(y, 1))
            if k in seen_:
                continue
            seen_.add(k)
            out.append('<circle class="%s" cx="%.1f" cy="%.1f" r="3.4"/>'
                       % (cls, x, y))
        return "".join(out)

    eq = xy(0, 0)[1]
    w_tl, w_br = xy(28, -180), xy(-28, -70)
    b1, b2 = xy(0, -170)[0], xy(0, -120)[0]

    # Heat: one dashed aggregate over the city set's own centre, computed
    # from the coordinates heat emits rather than placed by eye.
    lats = [c["lat"] for c in d["coords"].values() if c.get("lat")]
    lons = [c["lon"] for c in d["coords"].values() if c.get("lon")]
    hx, hy = xy(sum(lats) / len(lats), sum(lons) / len(lons))

    ev = sorted([e for e in d["events"] if e.get("anomalous")],
                key=lambda e: -float(str(e.get("stat", "0")).rstrip("x") or 0))
    fx, fy = None, None
    for c in d["fires_week"]["countries"].values():
        if c.get("name") == ev[0]["region"]:
            fx, fy = xy(c["lat"], c["lon"])

    world = (ROOT / "docs" / "world-map.svg").read_text()
    body = world.split("</rect>")[-1]
    body = body[body.index("<g"):body.rindex("</svg>")]
    body = (body.replace('fill="#cfcdc2"', 'fill="var(--paper-sunk)"')
                .replace('stroke="#b8b6ab"', 'stroke="var(--rule)"'))

    lab = []

    def label(x, y, ch, name, anchor="start", dx=9, dy=-6):
        a = ' text-anchor="%s"' % anchor
        lab.append('<text class="mlk" x="%.1f" y="%.1f"%s>%s</text>'
                   % (x + dx, y + dy, a, h(ch)))
        lab.append('<text class="mln" x="%.1f" y="%.1f"%s>%s</text>'
                   % (x + dx, y + dy + 13, a, h(name)))

    if fx:
        label(fx, fy, "FIRES", ev[0]["region"])

    # The heat mark sits at the centroid of its own city set, which is the
    # middle of the densest cluster on the map, so its label cannot sit
    # beside it. Pulled into the Atlantic with a leader, the way the layered
    # study does for England.
    lx, ly = hx - 96, hy - 34
    lab.append('<line class="ldr" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
               % (hx - 10, hy - 3, lx + 4, ly + 4))
    label(lx, ly, "HEAT", "%d cities, aggregated" % len(d["heat"]["cities"]),
          anchor="end", dx=0, dy=0)

    # Anchored to run back over the map. At lon 122 a left-anchored label is
    # 120px from an edge 130px away, so it left the frame.
    cx, cy = xy(*CROPS_XY["Philippines"])
    label(cx, cy, "CROPS", "Philippines, its worst region",
          anchor="end", dx=-9, dy=15)

    return ('<svg viewBox="0 22 800 330" width="100%%" '
            'style="height:auto;margin-top:12px" role="img" aria-label="World '
            'map of this week\u2019s readings. Every marker is the same size: '
            'a filled mark is a place past its own record, an open mark is a '
            'place within it, and heat is one dashed aggregate for its whole '
            'city set. The dashed box is the Pacific sea surface temperature '
            'window and the bracket marks the Nino 3.4 region.">'
            '%s'
            '<line class="eq" x1="0" y1="%.1f" x2="800" y2="%.1f"/>'
            '<rect class="sstw" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
            '<path class="nb" d="M%.1f,%.1f v-7 h%.1f v7"/>'
            '<text class="nbt" x="%.1f" y="%.1f">NI\u00d1O 3.4 &nbsp;%s</text>'
            '%s%s'
            '<circle class="agg" cx="%.1f" cy="%.1f" r="9"/>'
            '%s</svg>'
            % (body, eq, eq,
               w_tl[0] + 1, w_tl[1], w_br[0] - w_tl[0] - 1, w_br[1] - w_tl[1],
               b1, eq + 13, b2 - b1, b2 + 9, eq + 11,
               nino34,
               dots(open_marks, "mo"), dots(lit_marks, "mk"),
               hx, hy, "".join(lab)))


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
    # THE GAP COMES FROM hist_due, NOT FROM SUBTRACTION. Fires emits
    # hist_due as expected minus the deliberate exclusions, so the archive
    # gap is due minus held and needs no arithmetic here. My version
    # recomputed it from expected and the exclusion list, which agrees with
    # theirs this week and would drift the moment they add a second kind of
    # exclusion, which they did today: years_excluded_defective now sits
    # beside years_excluded_no_archive.
    #
    # Same rule I have been applying to other people's constants all day.
    # A number derived in two places is a number that will disagree in one.
    due = (geo or {}).get("hist_due")
    held = len(_hist) if isinstance(_hist, (dict, list)) else int(_hist or 0)
    gap = (due - held) if due is not None else (span - n_obs - len(excl))
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
    """Editor's sentence if there is one, the generated clauses if not.

    PRODUCT'S RULING, 2026-08-11, reversing the emphasis in D-123 rather
    than the mechanism: editor writes the lede most weeks, and the
    generated form is the fallback for the week nobody does.

    They refused the rule I proposed, that the page lead with the channel
    holding the largest count of places past their own record, and the
    reason is better than the ranking objection I expected. The rule
    compares 22 cities with 18 countries with 69 crop regions. Those are
    different units, crop regions are sub-national and outnumber cities by
    construction, so it would pick crops nearly every week whatever
    happened in the world: not the biggest story, the smallest unit. Any
    count-based rule has that shape, and a share-based one swaps it for a
    claim about our own coverage.

    And no fixed rule repairs it, because leading with something IS the
    claim. A stated rule makes the choice predictable rather than neutral.

    WHICH MODE RAN IS PRINTED AT BUILD. An empty copy block and a copy
    block nobody wrote look identical from here, and "generated because
    editor was busy" must not be indistinguishable from "generated because
    that was the right call".
    """
    written = _editor_lede()
    if written:
        return written, "editor"
    return _generated_lede(d), "generated"


def _editor_lede():
    """The `## lede` block from copy/frontpage.md, or None if left empty."""
    from design import copydeck
    # THE GUIDANCE LIVES ABOVE THE FIRST HEADING, where copydeck treats it
    # as the file's own notes and never renders it. My first version put it
    # inside the block with a marker string, and a test writing one sentence
    # above the notes rendered the sentence AND the notes into the headline.
    # Instructions in a slot are copy, whatever they say about themselves.
    raw = (copydeck.load("frontpage").get("lede") or "").strip()
    return copydeck._inline(raw) if raw else None


def _generated_lede(d):
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

    # EVERY CLAUSE HAS A ZERO FORM, and until editor checked it none did.
    # This docstring said each clause states its negative on a calm week and
    # then never built it, so a quiet week would have printed "At least 0 of
    # 41 cities have had more hot days than in any year on record", which is
    # not flat, it is a sentence we would not publish. Same failure heat made
    # in August: describing what a guard was meant to do and calling that
    # coverage. I described the fallback I meant to write.
    out = []
    if dh["records"]:
        out.append("<b>%s%d of %d cities</b> have had more hot days than in "
                   "any year on record." % ("At least " if floors else "",
                                            dh["records"], dh["of_cities"]))
    else:
        out.append("<b>No city</b> of the %d measured has had more hot days "
                   "than in an earlier year." % dh["of_cities"])

    if n_fire == 1:
        # The singular is not a plural with the s removed: "1 country is
        # past their own record fire week" needs "its". Exercised below,
        # because one is the count this clause will most often carry in a
        # normal week and the one nobody renders while building.
        out.append("<b>1 country</b> is past its own record fire week.")
    elif n_fire:
        out.append("<b>%d countries</b> are past their own record fire week."
                   % n_fire)
    else:
        out.append("<b>No country</b> is past its own record fire week.")

    # THE CROPS COUNT NEVER SHIPS WITHOUT ITS DISTRIBUTION. Editor's catch,
    # and the sharper of the two: 69 regions at a record low reads as
    # alarming and is an ordinary number. The crops page exists partly to
    # say so, with 81 as the even-spread expectation and 24 to 104 as the
    # last twelve years. The bare count in the largest type on the site, one
    # link above the page that calibrates it, is the exact error that page
    # was built to prevent.
    cb = d["crops"].get("chance_baseline_aggregate") or {}
    lo, hi = cb.get("recent_min"), cb.get("recent_max")
    if not n_reg:
        out.append("<b>No crop region</b> is at its worst for this point in "
                   "the season.")
    elif lo is not None and hi is not None and n_reg <= hi:
        out.append("<b>%d crop regions</b> are at their worst for this point "
                   "in the season, an ordinary number: the last twelve years "
                   "ran %d to %d." % (n_reg, lo, hi))
    else:
        out.append("<b>%d crop regions</b> are at their worst for this point "
                   "in the season, more than in any of the last twelve "
                   "years." % n_reg)
    return " ".join(out)



def _spread(hb):
    """The disagreement, beside the figure it governs.

    EDITOR'S RULING, D-051 applied: a headline probability may not appear
    bare in large type, because the qualifier travels with the datum and
    nothing else on the page will carry it once the band is screenshotted.

    This band printed 98% and 70% side by side with nothing attached, which
    is worse than it looks: the two numbers have completely different
    standing. The models agree within 11 points on +2.5 and disagree by 71
    on +3.5, which is the widest spread the site publishes. A reader given
    both bare would reasonably take them as equally settled.

    Nobody flagged this. It predates the ruling and I found it while fixing
    the lede, which is the only reason it is here rather than live.

    Surfacing the disagreement rather than averaging it away is the house
    rule (T-thesis, and CLAUDE.md's editorial constraints), so this prints
    the range rather than a confidence adjective.
    """
    b = hb.get("record_>3.5") or {}
    vals = [b.get("anchor"), b.get("consensus"), b.get("seas5")]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    return ("the +3.5 figure spans %d to %d across the six models, "
            "the widest disagreement on the site" % (lo, hi))


def page(d):
    _mb = map_block(d)
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
    hb = d["meta"]["headline_buckets"]
    nino = (d["snap"].get("physical_state") or {}).get(
        "nino34_weekly_traditional")
    n34 = ("%+.1f&nbsp;&deg;C" % nino) if nino is not None else "n/a"

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
.wave .spread{{font-family:"{data}",monospace;font-size:10.5px;
 line-height:1.6;color:var(--ink-faint);flex-basis:100%;max-width:74ch}}
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
.sub{{margin-top:44px;border-top:3px solid var(--ink);padding-top:18px;
 display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px 48px;
 align-items:start}}
.sub .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink)}}
.sub .p{{margin:9px 0 0;font-size:19px;line-height:1.45;color:var(--ink);
 max-width:34ch;text-wrap:pretty}}
.sub .fine{{margin:9px 0 0;font-family:"{data}",monospace;font-size:10.5px;
 line-height:1.7;color:var(--ink-faint);max-width:52ch}}
{ecss}
.foot{{margin-top:40px;border-top:1px solid var(--rule);padding:16px 0 40px;
 display:flex;justify-content:space-between;gap:20px;
 font-family:"{data}",monospace;font-size:11px;line-height:1.7;
 color:var(--ink-faint)}}
/* The layered map's own styles, so the imported block renders the same on
   both surfaces. */
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

/* THE CALM DENOMINATOR, drawn. Every fires country we watch is on the map;
   open means within its own range. Without them a dozen filled marks read
   as a broken map rather than as a quiet week, which is crops_map.py's own
   rule arriving on a second surface. Same size as a filled mark: the fill
   says which, the size says nothing. */
/* Heat is ONE mark for its whole set, dashed and unfilled, because it
   carries no state: a set-level fill would assert one for 41 cities at
   once and the per-city states live on the Heat page. VD's answer to Q8. */
svg .eq{{stroke:var(--rule);stroke-width:1}}
svg .sstw{{fill:none;stroke:var(--ink-faint);stroke-width:1;
 stroke-dasharray:4 4}}
svg .nb{{fill:none;stroke:var(--ink);stroke-width:1.6}}
svg .nbt{{font-family:"{data}",monospace;font-size:9.5px;font-weight:600;
 fill:var(--ink);stroke:var(--paper);stroke-width:2.5;paint-order:stroke}}
svg .mln{{font-family:"{prose}",Georgia,serif;font-size:12px;fill:var(--ink);
 stroke:var(--paper);stroke-width:2.5;paint-order:stroke}}
@media (max-width:620px){{
 /* 390px. THE MAP IS THE PART THAT BREAKS: an 800-unit viewBox at 350
    real pixels draws a 3.4 radius as 1.5px and stacks every label into a
    heap. Marks grow in viewBox units through the CSS geometry property so
    they stay tappable, and the labels come off, because the two named
    places are unreadable at this width and the claim is on the mark
    itself, reachable by tap. The state line above still carries the
    counts, so nothing that was said is lost. */
 svg .mln,svg .mlc,svg .nbt{{display:none}}
 svg circle.ring{{r:11}}
 .lgd{{gap:2px 16px}}
 .rfg{{font-size:20px}}
}}
@media (max-width:1000px){{
 .shell{{padding:0 20px}}
 h1{{font-size:23px}}
 .rr{{grid-template-columns:1fr !important;gap:6px}}
 .rfg{{text-align:left;font-size:22px}}
 .note{{grid-template-columns:1fr}}
 .chn .grid{{grid-template-columns:1fr}}
 .foot,.more{{flex-direction:column}}
 .sub{{grid-template-columns:1fr}}
 .sub{{grid-template-columns:1fr}}
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
<span class="r">{mb_state}</span></div>
{mb_svg}
{mb_legend}
<p class="mapnote"><b>The map draws only what clears a stated bar: fires at
{mb_bar_f}, crops with {mb_bar_c}.</b> {mb_below} more places passed their own
record this week and not the bar; every one is counted by its channel and on
its channel page, so the bar decides what is DRAWN, never what is measured.
It is a fixed number rather than one tuned each week to keep the map tidy.
One hue and one shape per channel, sized by that channel&rsquo;s own measure:
<b>sizes compare within a channel, never across channels</b>. Shape carries
the channel and hue repeats it, so the split survives greyscale and
colourblindness. Every mark is a link; hover or focus shows its claim with its
denominator.</p>

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
<span class="spread">{spread}</span>
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

<div class="sub">
<div><div class="k">One email a week</div>
<p class="p">{promise}</p></div>
<div>{form}<p class="fine">Confirmation email required. No spam, and the
archive stays free and public whether you subscribe or not.</p></div></div>

<div class="foot"><span>Lepik, K. (2026). The Long Swell. thelongswell.com
&middot; every issue archived, immutable &middot; disagreements surfaced, not
averaged</span></div>

</div>{script}</body></html>""".format(
        faces=T.font_faces_css("../../docs/fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA, lede=lede(d)[0], rows=rows,
        nino_col=T.NINO,

        n_fire=sum(1 for e in d["events"] if e.get("anomalous")),
        n_city=len(d["heat"]["cities"]),
        n_ctry=sum(1 for p in d["crops"]["places"]
                   if any(r.get("rank") == 1 for r in (p.get("regions") or []))),
        p25=hb["9715_>2.5"]["mid"], p35=hb["record_>3.5"]["mid"],
        spread=_spread(hb),
        n34=n34,
        mb_svg=_mb["svg"], mb_legend=_mb["legend"],
        mb_bar_f=_mb["bar_f"], mb_bar_c=_mb["bar_c"], mb_below=_mb["n_below"],
        mb_state="%d past their own record &middot; %d past the bar"
                 % (_mb["n_rec"], _mb["n_shown"]),
        script=_mb["script"],
        form=email_capture_form(label="Subscribe"),
        promise=h(EMAIL_CAPTURE_PROMISE), ecss=EMAIL_FORM_CSS)


def main():
    d = load()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frontpage_v2.html").write_text(page(d))
    print("wrote design/mockups/frontpage_v2.html")
    text, mode = lede(d)
    print("  lede [%s]: %s" % (mode, text.replace("<b>", "").replace("</b>", "")))
    if mode == "generated":
        print("  (fallback. Editor writes the lede most weeks; copy/"
              "frontpage.md '## lede' is unwritten.)")


if __name__ == "__main__":
    main()
