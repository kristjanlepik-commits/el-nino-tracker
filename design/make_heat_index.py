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
  was not. It took three attempts and the reasoning is worth keeping,
  because the first two are the ones a future chat would try again.

  Plotting position r/(N+1), the chance of landing this high by luck,
  breaks ties honestly but answers how UNLIKELY the rank is, which
  rewards a long record. Kristjan's correction: the page asks how far
  from normal this year is.

  z against the 1991-2020 normal answers that question, and is wrong for
  this data. Hot-day counts are right-skewed, so z understates the tail
  and Berlin's 87th-percentile summer drew as ordinary variation.

  Percentile, read from heat's payload and never derived here, is what
  ships. It survives the set growing to 100 cities, which is what
  Kristjan was actually testing.

  Each row then shows the city's own count against its own normal, which
  carries magnitude without inviting a cross-city comparison the method
  refuses: every pair of numbers is on that city's own threshold.
"""
import json, math, re, statistics as st
from pathlib import Path

R = Path(__file__).resolve().parent.parent
# THE PAGE CARRIES THE PAYLOAD IT WAS BUILT FROM. Editor found two city
# pages a night stale, and found them by cross-checking heat's social
# figures against the page copy: both numbers had been right when written
# and the cut moved between them. A page carrying a stale count looks
# exactly like a page carrying a correct one, which is why nothing caught
# it and why the catch was luck rather than process.
#
# A short hash of the payload, stamped into every page, makes staleness a
# thing that can be checked instead of noticed.
import hashlib  # noqa: E402
PAYLOAD_STAMP = hashlib.sha256(
    (R / "heat/data/city_nights.json").read_bytes()).hexdigest()[:12]

import sys
sys.path.insert(0, str(R))
from run_brief import (ANALYTICS_SNIPPET, PAGES_BASE_URL,   # noqa: E402
                       SITE_MASTHEAD_CSS,
                       site_masthead)
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())["cities"]
# COORDINATES COME FROM THE PAYLOAD. design/city_coords.json is deleted.
#
# I built it on the argument that placing a mark is cartography rather than
# science, so it did not belong in heat's data. That was wrong in the only
# way that matters: heat already emitted geography.map.points and had since
# they wrote the map spec, so my file was a SECOND COPY of something that
# existed, and a second copy drifts. It drifted the moment the set grew to
# 36 and mine held 26, which rolled the whole channel back on a build.
#
# Same fix as legend_band and for the same reason: one definition, emitted
# once, never re-derived. A check that two copies agree only makes the
# duplication survivable, which is not the same as removing it.
#
# Theirs and mine agreed to a median of 4.1 km and a worst case of 13, which
# is under a marker radius at this scale, so nothing moved visibly.
CO = {p["city"]: {"lat": p["lat"], "lon": p["lon"]}
      for p in N["geography"]["map"]["points"]}
COAST = json.loads((R / "design/data/europe_coast.json").read_text())
C, DH = N["cities"], N["day_headline"]

BOX = {"ES": (36.0, 43.8, -9.3, 4.3), "FR": (41.3, 51.1, -5.2, 9.6),
       "DE": (47.2, 55.1, 5.8, 15.1), "AT": (46.3, 49.1, 9.5, 17.2),
       "NL": (50.7, 53.6, 3.3, 7.3), "SE": (55.3, 69.1, 11.0, 24.2),
       "CZ": (48.5, 51.1, 12.1, 18.9), "FI": (59.7, 70.1, 20.5, 31.6),
       "CH": (45.8, 47.8, 5.9, 10.5),
       # Great Britain and Northern Ireland, including the islands, so a
       # future Scottish or Northern Irish station passes without another
       # edit here. The guard's whole value is that a new country stops
       # the build rather than skipping the check.
       "UK": (49.8, 60.9, -8.7, 1.9)}
# A country arriving in the payload with no box would otherwise skip the
# check silently, which is the one failure this guard exists to prevent.
for _n, _v in C.items():
    if _v["country"] not in BOX:
        raise SystemExit(f"{_n}: no bounding box for {_v['country']}, so its "
                         f"coordinate cannot be checked. Add one.")
rows = []
for n, v in C.items():
    if n not in CO:
        raise SystemExit(
            f"{n} is in the payload's cities but not in "
            f"geography.map.points, so heat is emitting a city it cannot "
            f"place. That is theirs to fix, not a coordinate to add here.")
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
    # HOW FAR PAST ITS OWN PREVIOUS BEST, which is the quantity VD's sizing
    # encodes. Percentile cannot do it: fourteen cities sit at 100 and would
    # all draw the same, which is the problem. Raw hot days cannot either,
    # because it ranks Marseille's 34 above Alicante's 21 when Marseille
    # normally has 1 and Alicante 4, so the largest marks would land on
    # whichever cities have the mildest climates.
    #
    # Read off the same per-year series the row chart already draws, not
    # reconstructed from anything withheld. Every record city has a previous
    # best by definition, and a non-record has no honest margin at all, so
    # it draws at the floor and the fill carries it.
    dser = [(int(y), x["days_to_cut"]["95"]) for y, x in yrs.items()
            if x.get("usable_to_cut") and x.get("days_to_cut")]
    now = v["days"]["days_2026"]["95"]
    prev_best = max(x for y, x in dser if y != 2026)
    rows.append({"z": (now - zmean) / zsd if zsd else 0.0,
                 "zmean": zmean,
                 "name": n, "lat": la, "lon": lo, "rank": r["value"],
                 "of": r["of_years"], "pct": r["percentile"],
                 "now": now, "base": base,
                 "prev_best": prev_best,
                 "margin": (now - prev_best) / prev_best if prev_best else 0.0,
                 "cut": v["counted_to"],
                 "gated": bool(v.get("nights_metric_gated"))})
# ALPHABETICAL INSIDE BOTH GROUPS, records first. Editor's call and the
# argument is the page's own thesis turned on the list: this is 24
# thermometers and nothing between the marks means anything, so ordering
# ten of them by extremity quietly asserts the cross-city scale the first
# paragraph denies. The group split still carries the honest amount of
# ordering, at a record or not, and the alphabet restarting at Amsterdam
# marks the boundary without a divider.
#
# What forced it was showing the rank. Ordering by percentile while
# printing a rank produces inversions by construction: Hamburg at 10th of
# 91 sat above Amsterdam at 9th of 76, correctly, and read backwards. One
# inverted pair in nine this week. The count is not stable, and at four it
# stops looking like a subtlety and starts looking like a broken sort,
# with nobody having changed a line of code.
#
# This is not the alphabetical list Kristjan rejected as boring. That one
# was fourteen rows reading "record, 88 years" and nothing else. The
# magnitude he wanted is now in the row, in the count, the chart and the
# rank, rather than in the sort.
rows.sort(key=lambda d: (d["rank"] != 1, d["name"]))

# The extremes are NAMED, not taken from the ends of the list. Editor's
# strip copy reads off the most and least unusual city, and with the sort
# alphabetical rows[-1] is Valencia rather than Stockholm. Two sentences
# that had quietly depended on the sort order, which is the same defect as
# a typed city name and harder to see.
# NOT MEASURED IS NOT THE SAME AS MEASURED AND ORDINARY. Editor's call and
# it is the same defect as the fourteen tied cities: an absence used to
# mean something, with no way for a reader to tell it from a value.
#
# The set is ragged. Fifteen cities are counted to 8 August and twenty-one
# stop earlier, the Spanish ten on the 2nd or 3rd. The event peaked on the
# 4th and 5th. So for those days Spain is NOT MEASURED, and drawing it in
# the same fill as a city that was measured and came in unremarkable makes
# the map assert the one thing we are declining to say. No caption fixes
# that, and a caption trying to would be doing the drawing's job.
#
# THE RULE HERE IS THE OBSERVABLE FACT, not a judgement about which days
# mattered: a city whose window ends before the set's latest cut has
# unmeasured days at the end of it. That is conservative, it flags Paris at
# the 4th as well as Seville at the 3rd, and it needs no threshold I would
# have had to invent. Heat owns the methodological version and I have asked
# for it; when they emit a flag this reads that instead.
CUT_LATEST = max(d["cut"] for d in rows)
for _d in rows:
    _d["short"] = _d["cut"] < CUT_LATEST
NSHORT = sum(1 for d in rows if d["short"])

LEAD = min(rows, key=lambda d: (-d["pct"], d["name"]))
TAIL = min(rows, key=lambda d: (d["pct"], d["name"]))

# Spelled out because the standfirst is prose, but DERIVED, because it was
# typed. "Twenty-one cities" sat two clauses away from "14 of the 22" in the
# same sentence when Amsterdam arrived, and the screen-reader label on the
# map said twenty-one too, where nobody would have seen it.
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def words(n):
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + (f"-{_ONES[o]}" if o else "")


NCITY = words(len(rows)).capitalize()

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
#
# AND THEN PERCENTILE REPLACED z, which is where this actually landed. The
# ordering was wrong three times and each party caught a different fault:
# plotting position rewarded a long record (Kristjan), z was the right
# question but the wrong statistic, and z understates on right-skewed count
# data, so Berlin's 87th-percentile summer drew as "high, within its usual
# variation" (VD Main). Percentile is read from the payload, never derived.
# The z fields above are kept because the rows carry them, not because they
# order anything; the sort key is pct.
#
# FOUR bands. An earlier cut had three, on the argument that splitting the
# middle was not a distinction a reader could act on. The fourth is the
# calm end, and it is the one D-043 is about: the scale has to show what an
# unremarkable summer looks like even when no city is drawing one. No city
# is in it, and the legend says so rather than leaving a reader to pair the
# palest mark on the map with the bottom label.
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
# THREE STATES, not four rungs. VD's ruling, and the payload argued it
# harder than they did: the two middle rungs were splitting Barcelona at
# the 98.9th percentile from Berlin at the 87.3rd, and both are near the
# top of their own record and neither is a record. A whole colour step was
# being spent on a distinction no reader can act on.
#
# What replaces it is not less information, it is the information moved to
# the channel that can carry it. Colour now says WHICH OF THREE STATES,
# and size says how far past its own previous best a record went, which is
# the variable percentile cannot express because fourteen cities are tied
# at its ceiling.
#
# THE THIRD STATE STAYS DRAWN WHETHER OR NOT ANYONE IS IN IT. That is
# D-043 rather than tidiness: a reader has to be able to see that the
# scale has a calm end. It was empty when VD specified it and Stockholm
# occupies it now, which is the argument for having drawn it early.
#
# NEAR RECORD IS A RANK, NOT A PERCENTILE. Kristjan's call: a city is near
# its record if this summer is among its five hottest, full stop. The 80th
# percentile it replaced meant something different in every city, because a
# percentile cut is a rank cut whose position moves with the length of the
# record: 80 per cent of Madrid's 106 years leaves 21 summers above the
# line and 80 per cent of Murcia's 43 leaves 8. Top five is the same
# statement everywhere and a reader already knows what it means.
#
# The thresholds are FIXED, not fitted. A domain stretched to this summer's
# spread would look better this week and break in February, and picking a
# cut on the size of the group it produces is the thing we do not do in any
# channel.
NEAR_RANK = 5
FILL = {"record": "var(--f3)", "near": "var(--f2)", "quiet": "var(--f0)"}


def state(d):
    if d["rank"] == 1:
        return "record"
    return "near" if d["rank"] <= NEAR_RANK else "quiet"


# Sizing. Area, not radius, carries the margin, so radius goes as its
# square root and the eye compares the discs correctly.
#
# R_FLOOR is what every mark on this map is today, so nothing shrinks:
# non-records draw at the floor rather than being made small, because a
# non-record has no margin and inventing one would be the map telling a
# reader something the data does not say.
#
# M_REF is where the area has doubled, and it is a judgement stated in
# advance rather than fitted to this week: beating your own record by a
# quarter is a materially different event from scraping it by a few per
# cent, and that is where the mark should have visibly grown. R_CAP stops
# one enormous record swallowing its neighbours; anything past it draws at
# the cap and carries its true figure in the list below.
R_FLOOR, R_CAP, M_REF = 7.0, 14.0, 0.25


def radius(d):
    if state(d) != "record":
        return R_FLOOR
    return min(R_CAP, R_FLOOR * math.sqrt(1 + max(0.0, d["margin"]) / M_REF))


def ordinal(n):
    """1st, 2nd, 3rd, 71st. f"{n}th" produced "71th", which VD caught."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


# band() lived here and read BANDS, which the three-state collapse deleted.
# Nothing called it, so the build passed and a function referencing a global
# that no longer exists sat one call away from a NameError. Removed rather
# than left for whoever adds the next fill.


# ---- projection: Mercator, fitted to the marks, as VD used -----------------
# THE BOX IS FITTED TO THE DATA, so the map never letterboxes and never
# frames water. VD Main's diagnosis after Helsinki arrived: this is the one
# element on the page whose HEIGHT IS SET BY ITS WIDTH, so it is the one
# element that must not be full-bleed. At full content width the frame
# wanted about 870px of height on its own and nothing above it could share
# a screen with the first row of the list.
#
# Helsinki to Malaga is 36.3 degrees of Mercator latitude against 30.9 of
# longitude, so the cities are 1.17 times taller than wide and the map is
# portrait by geography rather than by choice. Deriving the box from that
# ratio means no empty ocean is framed to make the aspect work, and it
# re-derives itself when the set grows.
#
# The height is a CHOICE and the width follows, which is the way round that
# keeps the map inside the fold. Paired with the two-column hero below, the
# map sits beside the lead rather than under it.
PAD, PAD_R = 52, 158
_merc0 = lambda la: math.degrees(
    math.log(math.tan(math.pi / 4 + math.radians(la) / 2)))
_dlon = max(d["lon"] for d in rows) - min(d["lon"] for d in rows)
_dmerc = (_merc0(max(d["lat"] for d in rows))
          - _merc0(min(d["lat"] for d in rows)))
IH_TARGET = 600
W = round(_dlon / _dmerc * IH_TARGET) + PAD + PAD_R
H = IH_TARGET + 2 * PAD
# Height, because height is what binds: 24 degrees of longitude against 30
# of Mercator latitude, so the shared scale comes from sy and the frame was
# giving the Iberian cluster no room. Eight cities inside four degrees, each
# with a name beside it, is the constraint the whole label rule lives or
# dies on, and at 660 every one of them was displaced onto a leader.
# Mercator y, expressed in DEGREES so it shares units with longitude.
# Without the 180/pi the y range is ~0.35 radians against ~22 degrees of
# longitude, so a single shared scale collapsed the map to a horizontal
# line. Caught by looking at it.
merc = lambda la: math.degrees(
    math.log(math.tan(math.pi / 4 + math.radians(la) / 2)))
LO0, LO1 = min(d["lon"] for d in rows), max(d["lon"] for d in rows)
MY0, MY1 = merc(min(d["lat"] for d in rows)), merc(max(d["lat"] for d in rows))
IW, IH = W - PAD - PAD_R, H - 2 * PAD
sx, sy = IW / (LO1 - LO0), IH / (MY1 - MY0)
k = min(sx, sy)                      # one scale, so the map is not stretched
ox = PAD + (IW - (LO1 - LO0) * k) / 2
oy = PAD + (IH - (MY1 - MY0) * k) / 2
PX = lambda lo: ox + (lo - LO0) * k
PY = lambda la: oy + (MY1 - merc(la)) * k

coast = []
for ring in COAST["rings"]:
    pts = [(PX(lo), PY(la)) for lo, la in ring if -180 < lo < 180 and -85 < la < 85]
    if len(pts) > 2:
        coast.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")

# ---- labels: ONE RULE, right of the marker at a constant gap ---------------
# What this replaces searched eight positions at two distances and took the
# first that did not collide. Every individual placement was defensible and
# the set was unreadable: most names ended up right, a substantial minority
# left, Marseille below. VD's diagnosis, and it is the right one: the eye
# cannot form a rule, so every name has to be hunted rather than glanced at.
#
# So the side is never negotiable. A label that would collide keeps the
# side and moves DOWN, and earns a hairline leader back to its marker. The
# rule holds for all of them and the exceptions announce themselves.
GAP, LH, MAX_STEPS = 6.0, 15.0, 2

def overlap(a, b):
    return (max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])) *
            max(0, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])))


placed = [{"x1": PX(d["lon"]) - radius(d) - 2, "x2": PX(d["lon"]) + radius(d) + 2,
           "y1": PY(d["lat"]) - radius(d) - 2, "y2": PY(d["lat"]) + radius(d) + 2}
          for d in rows]
# Kristjan: the cities on the map should be clickable. The list rows have
# linked to the city pages since they were built; the marks never did, and
# the map is the part of the page that invites a reader to look for their
# own city. Moved above the map because the map now needs it.
PAGES = {n: f"{n.lower().replace(chr(32), chr(45))}.html" for n in C}

# PLACEMENT ORDER IS PRIORITY ORDER, because the last cities placed are the
# ones that find no room. Records first and the biggest margin first inside
# that, so if a name has to go it is the least remarkable city on the map.
# The marks themselves never move and never drop: every city is still drawn,
# still clickable, and still carries its name in a <title> on hover.
_PRIO = {"record": 0, "near": 1, "quiet": 2}
marks, labels, leaders, label_boxes, dropped = [], [], [], [], []
for d in sorted(rows, key=lambda d: (_PRIO[state(d)], -d["margin"], PY(d["lat"]))):
    x, y, r = PX(d["lon"]), PY(d["lat"]), radius(d)
    href = PAGES[d["name"]]
    # A DASHED EDGE, not a fourth fill. The fill answers how unusual this
    # summer was and that question is still answered: the rank is computed
    # to this city's own cut, matched across every year, so it is correct
    # rather than provisional. What the dash says is that the window ends
    # earlier than the rest of the set, so the days at the end of it are
    # not measured here at all. Composing it with the fill keeps both facts
    # rather than letting one hide the other.
    _edge = ' stroke-dasharray="2.5 2"' if d["short"] else ''
    _cut = f', measured to {d["cut"]}' if d["short"] else ''
    marks.append(f'<a href="{href}" class="mk"><title>{d["name"]}{_cut}</title>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                 f'fill="{FILL[state(d)]}" stroke="var(--ink)" '
                 f'stroke-width="1"{_edge}/></a>')
    # 7.1 per character underestimated Spectral at 13px, so the placer
    # believed Zaragoza and Alicante were clear of each other and they
    # overlapped on the page. Measured against the rendered widths: 7.9
    # plus a two-unit pad covers every name in the set, and erring wide
    # costs a displaced label where erring narrow costs a collision.
    bw = len(d["name"]) * 7.9 + 2
    lx = x + r + GAP
    ly = y + 4
    # Down only, never up, so a reader scanning for a name never has to
    # look on the far side of the marker from where the rule says it is.
    # BOTH EXITS USED TO PLACE THE LABEL ANYWAY. Running past the frame
    # broke out of the loop without moving ly, and exhausting the steps hit
    # the else and did the same, so a name that could not find a slot was
    # dropped on top of whatever was already there. That is how Zaragoza
    # came to sit on Alicante, and nothing said so: the failure path and the
    # success path produced identical-looking output.
    #
    # Now it searches the whole frame, and if it genuinely cannot fit it
    # says so rather than overlapping. The guard below is the backstop.
    # DOWN FIRST, ALWAYS, then up only when the frame below is exhausted.
    # VD's rule is that the offset must be predictable, and it is: down is
    # the rule and up is the documented exception, both carrying a leader
    # back to the marker.
    #
    # A rule with no defined fallback is not a rule, it is a rule plus a
    # silent failure. Alicante sits low enough that nothing fits below it,
    # and the previous code responded by placing the name on top of
    # Zaragoza's and saying nothing.
    # Kristjan's rule: if there is no room for a name, drop it. A label three
    # rows from its own marker, on a leader threading past four others, is
    # not a label a reader can use, and at 36 cities twenty-six of them were
    # in that state. Two steps is as far as a leader stays followable.
    fitted = False
    for direction in (1, -1):
        for step in range(0 if direction == 1 else 1, MAX_STEPS + 1):
            dy = direction * step * LH
            cand = {"x1": lx, "x2": lx + bw,
                    "y1": ly + dy - 11, "y2": ly + dy + 4}
            if cand["y2"] > H - 4 or cand["y1"] < 4:
                break
            if not any(overlap(p, cand) for p in placed):
                ly += dy
                fitted = True
                break
        if fitted:
            break
    if not fitted:
        dropped.append(d["name"])
        continue
    box = {"x1": lx, "x2": lx + bw, "y1": ly - 11, "y2": ly + 4}
    placed.append(box)
    if abs(ly - (y + 4)) > 1:
        # Out from the marker's edge, along, then to the name. A displaced
        # label without a leader is a name floating beside the wrong city.
        # var(--ink-faint), not var(--coast). Drawn in the coastline's grey
        # the leader was invisible against the land it crosses, which makes
        # a displaced label worse than no leader: the reader sees a name
        # sitting beside a city it does not belong to and no thread back.
        leaders.append(f'<path d="M{x + r:.1f},{y:.1f} H{lx - 4:.1f} '
                       f'V{ly - 4:.1f}" fill="none" stroke="var(--ink-faint)" '
                       f'stroke-width="0.9"/>')
    # No sublabel. "record" under a darkest-fill marker is the fill said
    # twice and the legend already defines it; 98.6 against 98.1 is
    # invisible at marker size and nobody reads a map for a decimal. Both
    # belong in the list. Dropping them also halves the label mass, which
    # is what makes room for the larger record markers.
    labels.append(f'<a href="{href}" class="mk">'
                  f'<text x="{lx:.1f}" y="{ly:.1f}" class="cn">{d["name"]}</text></a>')
    label_boxes.append((d["name"], box))

# NO TWO NAMES MAY OVERLAP. Zaragoza sat on top of Alicante on the live
# page, and both of my browser checks for it reported zero collisions
# because they compared `{...el.getBBox()}`, which copies NOTHING: an
# SVGRect keeps its properties on the prototype, so every comparison was
# undefined against undefined and the check passed by never running.
#
# That is the third check this week to fail by not reaching the thing it
# tested. So it moves into the build, where it is arithmetic on the boxes
# the placer actually used rather than a measurement of the result.
def _ov(a, b):
    return (max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])) *
            max(0, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])))


_clash = [(label_boxes[i][0], label_boxes[j][0])
          for i in range(len(label_boxes))
          for j in range(i + 1, len(label_boxes))
          if _ov(label_boxes[i][1], label_boxes[j][1]) > 0]
if _clash:
    raise SystemExit("map labels overlap: "
                     + "; ".join(f"{a} on {b}" for a, b in _clash))

# A FINDING COUNT IS A FLOOR WHILE ANY CITY IS SHORT OF THE CUT. Heat emits
# the rule and the page was not reading it: "22 of these 36" is a census
# where the payload says floor. Twenty-one windows end before the latest
# cut and eleven cities have no observation on the peak day, so they could
# not register a record on it. More data can only raise the number.
#
# THE PREFIX IS READ, NOT TYPED, and it is applied only to the counts heat
# names. cities_short_of_it sits in the same object and moves the OTHER
# way: it falls as late data lands, so "at least 21 short" would be
# backwards. Editor caught that before anyone wired it.
_COV = N.get("coverage", {})
_FLOOR = "at least " if _COV.get("counts_are_floors") else ""


def floor(n):
    """A finding count with its qualifier attached, or bare once coverage
    is complete. Never call this on a coverage counter."""
    return f"{_FLOOR}{n}"

_CR = N["geography"]["map"].get("coord_resolution", {"resolved": 0, "total": len(rows)})
_nrec = len([d for d in rows if state(d) == "record"])
svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="height:auto" role="img" '
       # "These", and the clause after it, are load-bearing rather than
       # padding. A sighted reader is told twice that the set is not a
       # sample of Europe: once in the lead, once in the note under the
       # map. Both are visual text, so a screen reader user reaching this
       # description was getting the count with neither. Same figures,
       # weaker claim, purely by route (D-112).
       f'aria-label="These {NCITY.lower()} European weather stations, chosen '
       f'for where heat was expected rather than as a sample of the '
       f'continent, in one of three states: '
       f'{floor(_nrec)} at a record for hot days, '
       f'{len([d for d in rows if state(d) == "near"])} among their own five '
       f'hottest summers without reaching a record, and '
       f'{len([d for d in rows if state(d) == "quiet"])} outside their own top '
       f'five. Record markers are drawn larger the further a city passed its '
       f'own previous best.'
       + (f' {len(dropped)} marks are drawn without a printed name because '
          f'there was no room beside them; every city is listed below.'
          if dropped else '') + '">'
       + "".join(f'<path d="{d}" fill="var(--land)" stroke="var(--coast)" '
                 f'stroke-width="0.9" stroke-linejoin="round"/>' for d in coast)
       + "".join(leaders) + "".join(marks) + "".join(labels) + "</svg>")

# ---- the list: ordered, and each row carries its own magnitude -------------
# every city has a page now, so nothing renders as a dead name
# Flat, matching the shipped shape: /heat/ is the index and /heat/<city>
# sits beside it, so a link is a bare filename from either direction.
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
# THE TIE IS READ, not named. This said `- {"Cologne"}`, a city typed into
# the guard because it was the only tie the day the guard was written. The
# cut advanced, Alicante drew level with its own 1964 at 21 days, and the
# build stopped on a city that was behaving exactly as intended.
#
# A hard-coded exception is a guard that expires. tied_with is in the
# payload and says which years match, so a full bar is legitimate whenever
# the rank is 1 or the payload names a tie, and illegitimate otherwise.
_full = {d["name"] for d in rows if d["now"] >= OWNMAX[d["name"]]}
_ok = {d["name"] for d in rows
       if d["rank"] == 1 or C[d["name"]]["days"]["rank"].get("tied_with")}
if _full - _ok:
    raise SystemExit(
        f"a city draws a full bar while its rank is not 1 and the payload "
        f"names no tie: {sorted(_full - _ok)}. Either the bar is scaled "
        f"wrong or the rank is.")

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
    # width 100% with a 316-wide viewBox, so the chart fills the flexible
    # column instead of leaving the gap Kristjan found. It must STRETCH
    # rather than letterbox, and it carries no text, so nothing distorts:
    # the bars simply get wider.
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" '
            f'preserveAspectRatio="none" role="img" '
            f'aria-label="{name}: hot days every summer from {y0} to {y1}, '
            f'{len(ys)} years, with 2026 marked">{"".join(out)}</svg>')


def city_row(i, d):
    nm = d["name"]
    # EVERY ROW SAYS ITS RANK, including the fourteen firsts. Editor's fix and
    # it dissolves two separate defects at once.
    #
    # Before, a record row read "88 years of record" and a non-record read
    # "2nd of 87", so the ABSENCE of a rank was the record signal. An absence
    # cannot be read. It also left the block looking ordered while fourteen
    # cities were level, so a reader could conclude Alicante beat Zaragoza
    # when nothing separates them.
    #
    # Fourteen consecutive rows reading "1st of N" ARE the tie, visibly, with
    # nothing to explain. It is also strictly more informative in the same
    # space: the record length that "88 years of record" carried, plus the
    # rank it omitted.
    #
    # READ, NEVER DERIVED. Ties count against throughout, so a year tied with
    # 2026 keeps it off first place and a city can sit in the record group of
    # the map's colouring while its rank value is not 1. The label says what
    # days.rank.value says.
    lab = f'{ordinal(d["rank"])} of {d["of"]} summers &middot; '
    href = PAGES.get(nm)
    title = (f'<a href="{href}" class="cty">{nm}</a>' if href
             else f'<span class="cty dim">{nm}</span>')

    return (f'<div class="lrow">'
            f'<span class="lcty">{title}<span class="lsub">'
            f'{lab.rstrip(" &middot; ")}</span></span>'
            f'<span class="lbar">{minichart(nm)}</span>'
            f'<span class="lval">{d["now"]}<span class="lbase">vs {d["base"]:.0f}</span>'
            f'</span></div>')

# THE TIE IS SHOWN BY THE ROWS THEMSELVES, see city_row. A banded heading
# over each group did this for an hour and is gone: once every row states
# its rank, fourteen consecutive firsts are the tie, and a band saying so
# is a caption for a drawing that has started explaining itself.
_recs = [d for d in rows if state(d) == "record"]
_rest = [d for d in rows if state(d) != "record"]
all_rows = "".join(city_row(i, d) for i, d in enumerate(rows, 1))

# THE DAY-NIGHT PAIR IS ASSEMBLED, and the typed one was false.
#
# Marseille and Berlin were the two cards under a sentence reading "they
# lean opposite ways". They do not. Marseille is +7.8 toward days and
# Berlin is +16.4, so Berlin leans toward days HARDER, and the page said
# the opposite of what its own payload says. Editor caught it by going to
# the numbers when I pushed to assemble the pair.
#
# Worth recording what made it survive: the two glosses that carried the
# figures, "the days ran further" and "the other way round", were cut this
# morning for being fragile relational phrasing. They were not fragile,
# they were false, and cutting them removed the evidence a reader could
# have checked while leaving the conclusion standing.
#
# UNGATED ONLY, and the restriction is doing real work rather than being
# tidy. A naive argmax over the whole set picks Stockholm at +75.0, which
# is a story about its nights being unremarkable rather than about the two
# instruments disagreeing, and which we may not give a night rank to at
# all because it is gated.
_ung = [(v["days"]["rank"]["percentile"] - v["rank"]["percentile"], n)
        for n, v in C.items() if not v.get("nights_metric_gated")]
DAY_LEAD, NIGHT_LEAD = C[max(_ung)[1]], C[min(_ung)[1]]
DAY_LEAD_N, NIGHT_LEAD_N = max(_ung)[1], min(_ung)[1]
# THE SECTION DROPS, the build does not fail. Whether any city leans toward
# days while another leans toward nights is a property of the weather, not a
# defect, and a summer where it is not true is one the page still has to
# render. Failing the build here was my first version and the extremes test
# caught it inside a minute: with every city forced to the same rank there
# is no contrast to show, which is correct, and the page must still exist.
CONTRAST_OK = max(_ung)[0] > 0 > min(_ung)[0]
_dl_days = next(d["now"] - d["prev_best"] for d in rows if d["name"] == DAY_LEAD_N)

# The hero named Seville and Berlin to teach that the bar is per-city. Editor
# is right that a typed example goes false in silence: Berlin stops being the
# coolest threshold the moment a colder station joins, and nothing re-proves
# it. These two are the highest and lowest threshold in the set, so the
# sentence stays true whoever arrives, and the pair is as far apart as the
# set allows, which is what makes the point.
_th = sorted(((v["days"]["thresholds_c"]["95"], n) for n, v in C.items()))
HOT_LO, HOT_HI = (_th[0][1], _th[0][0]), (_th[-1][1], _th[-1][0])

# The legend is now three named states with their counts, not four rungs of
# arithmetic. What it replaces read:
#
#     Hotter than 19 of every 20 of its summers
#     Hotter than 16 of every 20
#     Beats fewer than 16 of every 20
#
# Three of four rungs in the same sentence shape, so telling them apart
# meant comparing fractions, and the verb changed from "hotter than" to
# "beats" for no reason. Precise and not how anyone speaks. A name a reader
# already owns does the work: record, near record, within range.
#
# "Ordinary" is VD's word for the third state and it cannot be used. Heat
# bans it outright and the build fails on it, which is correct: their least
# extreme readings sit in the 76th to 90th percentile of their own records,
# and those are not ordinary summers, they are simply not the most extreme.
# Swatch and name, nothing else. Kristjan's call, and the gloss and the count
# were both saying something a reader already had: the counts are in the
# standfirst two lines above ("14 of the 24 have had more of them than in any
# year on record") and the names carry their own meaning. A legend that
# explains three words it did not need to explain is a legend a reader stops
# reading.
# The third label was "near average" and the top-five rule made it false.
# The states are complementary, so moving the near-record boundary moves
# this one too, and top five leaves Valencia here at 6th of 89, which is
# the 94th percentile of its own record. Calling that near average is the
# same class of error as calling Marseille's 91st-percentile summer
# ordinary. Named by what it is instead, which is also the only one of the
# three that stays true however the set grows.
# All three read off the same scale, which is rank in that city's own
# record. Mixing a rank term with a distance term is how the four-rung
# legend got unreadable in the first place.
STATE_ROWS = [("record", "Record"), ("near", "Near record"),
              ("quiet", "Further from a record")]


def key_rows():
    # The size cue is a SWATCH, not a sentence. Editor cut the 45-word
    # explanation and sent the meaning back rather than writing a tighter
    # version, which is the right call: "bigger mark equals hotter city" is
    # what every reader assumes and it is wrong, so the correction belongs
    # where they are already decoding marks. Two discs at the real floor and
    # cap radii show the range and the words name the quantity.
    size = (f'<span class="ks kz">'
            f'<svg width="34" height="18" aria-hidden="true">'
            f'<circle cx="6" cy="9" r="4" fill="{FILL["record"]}" '
            f'stroke="var(--ink)" stroke-width="1"/>'
            f'<circle cx="23" cy="9" r="8" fill="{FILL["record"]}" '
            f'stroke="var(--ink)" stroke-width="1"/></svg>'
            f'Size: margin over its own record</span>')
    # Its own key entry, per editor: not a gap and not a default fill. An
    # absence a reader cannot tell from a value is the same defect as the
    # fourteen tied cities showing no rank.
    short = "" if not NSHORT else (
        f'<span class="ks kz">'
        f'<svg width="20" height="18" aria-hidden="true">'
        f'<circle cx="10" cy="9" r="6.5" fill="none" stroke="var(--ink)" '
        f'stroke-width="1" stroke-dasharray="2.5 2"/></svg>'
        f'Dashed: not measured to {CUT_LATEST[8:].lstrip("0")} '
        f'{_MON[int(CUT_LATEST[5:7]) - 1]}</span>')
    return "".join(f'<span class="ks"><i style="background:{FILL[k]}"></i>'
                   f'{nm}</span>' for k, nm in STATE_ROWS) + size + short


# The caption named Marseille and Nice, copied from VD's canvas where the
# margins were explicitly illustrative rather than data. On the real series
# Marseille cleared its record by 26 per cent and is a middling mark; the two
# largest are Nice at 100 and Paris at 76. Exactly the hardcoded framing
# product warned about, introduced by me twenty minutes after the warning,
# and found by looking at the picture rather than by any check.
_big = sorted((d for d in rows if state(d) == "record"),
              key=lambda d: -d["margin"])[:2]
BIGGEST = (" and ".join(d["name"] for d in _big) if len(_big) > 1
           else (_big[0]["name"] if _big else "the largest records"))

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


def _phrase(items):
    items = list(items)
    if len(items) < 3:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


# GROUPED BY MONTH. This read "to 31, 2 and 3 August 2026" the moment Prague
# arrived with a 31 July cut, because it took the month from the last date
# and applied it to all of them. A source line that misdates the data by a
# month is the worst place in the page to be approximately right.
_by_month = {}
for _c in _cuts:
    y, m, dd = _c.split("-")
    _by_month.setdefault((y, m), []).append(str(int(dd)))
# Months joined with a comma, days inside a month with "and". Joining both
# levels the same way gave "31 July and 2 and 3 August".
CUT_TXT = ", ".join(f"{_phrase(ds)} {_MON[int(m) - 1]}"
                    for (y, m), ds in sorted(_by_month.items())) + \
    f" {_cuts[-1][:4]}"

# Reader-facing prose lives in copy/heat_index.md, which editor owns. The
# figures are assembled here and named; the sentences around them are not
# ours to write. See design/copydeck.py for what the build refuses to do
# silently. (The module is copydeck, not copy, because design/ goes on
# sys.path and a file named copy.py there would shadow the stdlib module
# for everything imported afterwards.)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import copydeck  # noqa: E402

_CONTRAST_SLOTS = ["contrast_label", "two_instruments"]
COPY = copydeck.render(
    "heat_index",
    {
        "records": floor(DH["records"]).capitalize(),
        "of_cities": DH["of_cities"],
        "typical_year": words(DH["baseline"]["median_year"]),
        "hot_hi_c": HOT_HI[1], "hot_hi": HOT_HI[0],
        "hot_lo_c": HOT_LO[1], "hot_lo": HOT_LO[0],
        "n_cities": len(rows),
        "lead_city": LEAD["name"], "lead_days": LEAD["now"],
        "lead_years": LEAD["of"],
        "tail_city": TAIL["name"], "tail_days": TAIL["now"],
        "tail_pct": f"{TAIL['pct']:.0f}",
        "gated": sum(1 for d in rows if d["gated"]),
    },
    wanted=(["headline", "lead", "method", "map_note", "strip_label",
             "strip_intro"] + (_CONTRAST_SLOTS if CONTRAST_OK else [])),
    withheld=({} if CONTRAST_OK else
              {s: "no city leans both ways this week"
               for s in _CONTRAST_SLOTS}),
)

CONTRAST_BLOCK = f"""<div class="seclab">{COPY['contrast_label']}</div>
<div class="two">
<div><span class="tl">{DAY_LEAD_N}</span>Its most hot days on record, by
{words(_dl_days)} days. For hot nights, {ordinal(DAY_LEAD['rank']['value'])} of
{DAY_LEAD['rank']['of_years']}.</div>
<div><span class="tl">{NIGHT_LEAD_N}</span>{ordinal(NIGHT_LEAD['days']['rank']['value'])} of
{NIGHT_LEAD['days']['rank']['of_years']} for hot days. For hot nights,
{ordinal(NIGHT_LEAD['rank']['value'])} of {NIGHT_LEAD['rank']['of_years']}.</div>
</div>
<p class="subl" style="margin-top:16px">{COPY['two_instruments']}</p>""" if CONTRAST_OK else ""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<!-- A page that declares summary_large_image and supplies no image is
     WORSE than one that declares nothing: the platform reserves the
     slot and renders it empty. Socials measured 136 channel pages
     sharing with no image at all, heat declaring the large card and
     showing a blank one. The house card is generic and beats an
     empty slot; per-page cards wait for the citable chart, and will
     have to carry their cut date so a stale one is visibly stale. -->
<meta property="og:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat &middot; The Long Swell</title>
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--coast:#C6C5C2;--accent:#8E240A;--bar:#D3D2CB;--land:#E4E3DC;
--f3:#8E240A;--f2:#C05B3D;--f0:#E8E7E2}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--coast:#43423C;
--accent:#F0876A;--bar:#43423C;--land:#232321;
--f3:#F0876A;--f2:#C05B3D;--f0:#2E2E2B}}}}
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
/* The map column is sized so the whole instrument clears the fold. Its
   height follows its width, so the width is the thing that gets decided. */
/* 620 rather than 560: the label size is fixed in viewBox units, so a
   wider column renders the 26 city names larger without changing the
   crowding. Enlarging the viewBox instead does the opposite, it makes
   the names smaller to fit more of them, which is the wrong trade on a
   map whose whole job is letting a reader find their own city. */
.hero{{display:grid;grid-template-columns:minmax(0,1fr) 620px;gap:40px;
align-items:start;margin-bottom:10px}}
.mapcol{{min-width:0}}
.mapcol svg{{max-height:64vh}}
@media(max-width:900px){{.hero{{grid-template-columns:minmax(0,1fr);gap:26px}}
.mapcol svg{{max-height:none}}}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:52px;line-height:1.04;
letter-spacing:-.02em;color:var(--ink);margin:40px 0 14px;max-width:20ch;text-wrap:balance}}
.stand{{font-size:17.5px;line-height:1.62;max-width:60ch;margin:0}}
/* The hero is two paragraphs now, the finding and then the method, and at
   margin:0 they set as one block and the split does nothing. The gap is
   larger than a paragraph break because the second one changes register:
   it stops telling the reader what happened and starts telling them how it
   was measured. Editor asked for air and this is the amount that reads as
   deliberate rather than as a loose line. The first paragraph also carries
   the finding, so it takes the larger size. */
.stand + .stand{{margin-top:22px;font-size:16.5px;color:var(--ink-faint)}}
.cn{{font-family:Spectral,serif;font-size:13px;fill:var(--ink)}}
/* The whole mark is the target, disc and name together, so a reader
   aiming at a 7px circle does not have to hit it. */
.mk{{cursor:pointer}}
.mk:hover circle{{stroke-width:2.4}}
.mk:hover .cn{{fill:var(--accent);text-decoration:underline}}
.cs{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint);
letter-spacing:.05em}}
.key{{display:flex;flex-wrap:wrap;gap:14px 30px;align-items:center;margin:14px 0 0;
font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--ink-faint)}}
.key i{{display:inline-block;width:12px;height:12px;border-radius:50%;
vertical-align:-2px;margin-right:8px}}
.ks i{{border:1px solid var(--ink)}}
/* The size swatch needs the discs vertically centred on the text and a
   little more room than a 12px dot, so it sits apart from .ks i. */
.kz{{display:inline-flex;align-items:center;gap:8px}}
.kz svg{{flex:none}}
.knote{{margin:14px 0 0;font-family:'IBM Plex Mono',monospace;font-size:11px;
line-height:1.8;color:var(--ink-faint);max-width:74ch}}
.seclab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:54px 0 6px}}
.subl{{font-size:15.5px;line-height:1.6;color:var(--soft);max-width:70ch;margin:12px 0 18px}}
/* Emphasis comes from copy/heat_index.md as a bare <strong>, so the weight
   is decided here rather than typed into a sentence editor owns. */
.stand strong,.subl strong{{color:var(--ink);font-weight:500}}
.knote strong{{color:var(--ink);font-weight:400}}
/* THREE cells, and this declared FOUR columns, so the empty 1fr sat
   between the chart and the number and swallowed every pixel of slack.
   Kristjan spotted the gap in the browser. The chart takes the
   flexible column now, which is also the better use of it: the
   minichart carries no text, so filling the width just makes the bars
   wider rather than distorting anything. */
.lrow{{display:grid;grid-template-columns:170px minmax(0,1fr) 74px;gap:16px;
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
</style><!-- payload {PAYLOAD_STAMP} --></head><body><main>
{site_masthead("../", active="heat")}
<!-- THE HOUSE NAME IS NOT REPEATED HERE. This bar predates the shared
     masthead, which now sits directly above it and already carries the
     wordmark, so the page printed "The Long Swell" twice inside 100px.
     Kristjan spotted it. What this bar is for is the page's own
     identity: the channel, and which station and cut it reports. -->
<div class="mast"><span class="prod">Heat</span><span class="when">Week of 3 August 2026</span></div>

<!-- TEXT LEFT, MAP RIGHT. VD Main, after Helsinki pushed the frame north:
     the map is the only element whose height is set by its width, so it is
     the only one that must not be full-bleed. Stacked, it ran about 870px
     tall, so the lead and the instrument could not share a screen and
     neither could the map and the first row of the list. Collapses to one
     column under 900px, where stacking is the honest layout anyway. -->
<div class="hero">
<div>
<h1>{COPY['headline']}</h1>
<p class="stand">{COPY['lead']}</p>
<p class="stand">{COPY['method']}</p>
</div>
<div class="mapcol">
{svg}
<div class="key">{key_rows()}</div>
<p class="knote">{COPY['map_note']}</p>
</div>
</div>

<div class="seclab">{COPY['strip_label']}</div>
<p class="subl">{COPY['strip_intro']}</p>
{all_rows}

{CONTRAST_BLOCK}

<!-- The methodology link sits with the sources, not in the nav. The
     shared masthead takes a methodology_href and does not render it,
     so passing one there is silent and does nothing; this is the
     place a reader checking a number is already looking. -->
<div class="src">
<span><a href="methodology.html">How these figures are built</a></span>
<span style="text-align:right">Heat methodology</span>
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
#
# Tag-stripping alone also deletes every aria-label, alt and title, which is
# the text a screen reader user gets INSTEAD of the graphic rather than in
# addition to it. So the checks below ran on the sighted reader's page only,
# and the one route where a claim arrives unaccompanied by the surrounding
# prose was the one route nothing checked. The map's aria-label was in fact
# unscoped (fixed above); this guard did not find it and could not have.
_visible = re.sub(r"<[^>]+>", " ", _body)
_spoken = " ".join(m.group(1) for m in re.finditer(
    r'(?:aria-label|alt|title)="([^"]*)"', _body, re.I))
_readable = _visible + " " + _spoken
for _w in BANNED:
    if re.search(rf"\b{re.escape(_w)}\b", _readable, re.I):
        raise SystemExit(f"index: banned word {_w!r} is published on the page "
                         f"(check aria-labels too, not just visible text).")

# D-112: no count over this city set may be published in a form that reads
# as a fact about Europe. The cities were chosen BECAUSE they sit in the hot
# part of the forecast map, so a proportion across them says nothing about a
# continent nobody sampled. The test that settles it, from the ledger: a
# real fact about Europe does not change when you add thermometers. Ours
# moved the same day ten cities landed.
#
# What makes the lead legal is one word. "22 of these 36 European cities" is
# scoped to the set; "22 of 36 European cities" is a claim about Europe.
# Socials lost that word in five consecutive drafts, which is the whole
# argument for a guard rather than a note: it is a single unstressed
# syllable, it survives no rewrite, and its absence changes what the
# sentence means without changing how it reads.
#
# The prose is editor's now (copy/heat_index.md), so this cannot be enforced
# by design being careful. It has to fail the build.
#
# The count is matched in digits AND in words. The live defect was a
# spelled-out one, in the map's aria-label: "Thirty-six European weather
# stations", no scoping, while the sighted reader was told twice. A guard
# reading only digits, or only visible text, calls that page clean on two
# separate counts.
if not N.get("selection", {}).get("is_representative_of_europe", True):
    _NUM = (r"(?:\d[\d,]*|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|"
            r"ninety|ten|eleven|twelve|(?:thir|four|fif|six|seven|eigh|nine)"
            r"teen)(?:-\w+)?)")
    _EUROPE = re.compile(
        # \b matters more than it looks: without it the alternation happily
        # starts at the "6" inside "these 36", the lookbehind sees "3 " and
        # passes, and the guard reports the one sentence that is correct.
        rf"(?<!these )\b{_NUM}\s+(?:of\s+(?:the\s+)?{_NUM}\s+)?"
        # One optional word between "European" and the noun. The live defect
        # read "European WEATHER stations", and a pattern demanding the two
        # be adjacent missed it while looking like it covered the case.
        rf"European\s+(?:\w+\s+)?"
        rf"(?:cities|capitals|countries|stations|towns)\b", re.I)
    _hit = _EUROPE.search(re.sub(r"\s+", " ", _readable))
    if _hit:
        raise SystemExit(
            f"index: {_hit.group(0)!r} counts European cities without scoping "
            f"the count to this set (D-112). The payload says "
            f"is_representative_of_europe is false. Write 'of THESE n "
            f"European cities', or drop the count.")
out.write_text(html)
print(f"wrote {out} | {len(rows)} cities, {len(coast)} coast rings, "
      # Report the quantity that ACTUALLY orders the list. This line still
      # printed the Weibull plotting position after percentile replaced it,
      # so the build log described an ordering the page no longer uses.
      f"most unusual {LEAD['name']} at pct {LEAD['pct']:.1f}, "
      f"least {TAIL['name']} at pct {TAIL['pct']:.1f}, "
      f"{sum(1 for d in rows if d['rank'] == 1)} at a record, "
      f"{len(dropped)} name(s) dropped for room"
      + (" (" + ", ".join(sorted(dropped)) + ")" if dropped else "")
      # Heat emits coord_resolution so the state is readable from the
      # payload rather than by opening station_coords.json. 27 marks are
      # still hand-typed and off by 3 to 15 km, which is under a marker
      # radius here but is not where the disclosure says the station is.
      + f", {_CR['resolved']}/{_CR['total']} marks at their resolved station")
