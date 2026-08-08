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
       "NL": (50.7, 53.6, 3.3, 7.3), "SE": (55.3, 69.1, 11.0, 24.2),
       "CZ": (48.5, 51.1, 12.1, 18.9)}
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
# Asymmetric padding, because every label now sits to the RIGHT of its
# marker without exception. The rightmost stations, Stockholm at 17.9E and
# Vienna at 16.4E, need their name to fit inside the frame or the constant
# offset breaks on exactly the cities a reader is least able to guess.
W, H, PAD = 900, 880, 52
PAD_R = 158
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
GAP, LH = 6.0, 15.0

def overlap(a, b):
    return (max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])) *
            max(0, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])))


placed = [{"x1": PX(d["lon"]) - radius(d) - 2, "x2": PX(d["lon"]) + radius(d) + 2,
           "y1": PY(d["lat"]) - radius(d) - 2, "y2": PY(d["lat"]) + radius(d) + 2}
          for d in rows]
marks, labels, leaders = [], [], []
for d in sorted(rows, key=lambda d: PY(d["lat"])):
    x, y, r = PX(d["lon"]), PY(d["lat"]), radius(d)
    marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                 f'fill="{FILL[state(d)]}" stroke="var(--ink)" '
                 f'stroke-width="1"/>')
    bw = len(d["name"]) * 7.1
    lx = x + r + GAP
    ly = y + 4
    # Down only, never up, so a reader scanning for a name never has to
    # look on the far side of the marker from where the rule says it is.
    for step in range(0, 9):
        cand = {"x1": lx, "x2": lx + bw, "y1": ly + step * LH - 11,
                "y2": ly + step * LH + 4}
        if cand["y2"] > H - 4:
            break
        if not any(overlap(p, cand) for p in placed):
            ly += step * LH
            break
    else:
        step = 0
    box = {"x1": lx, "x2": lx + bw, "y1": ly - 11, "y2": ly + 4}
    placed.append(box)
    if ly > y + 5:
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
    labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="cn">{d["name"]}</text>')

_nrec = len([d for d in rows if state(d) == "record"])
svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="height:auto" role="img" '
       f'aria-label="{NCITY} European weather stations in one of three states: '
       f'{_nrec} at a record for hot days, '
       f'{len([d for d in rows if state(d) == "near"])} among their own five '
       f'hottest summers without reaching a record, and '
       f'{len([d for d in rows if state(d) == "quiet"])} outside their own top '
       f'five. Record markers are drawn larger the further a city passed its '
       f'own previous best.">'
       + "".join(f'<path d="{d}" fill="var(--land)" stroke="var(--coast)" '
                 f'stroke-width="0.9" stroke-linejoin="round"/>' for d in coast)
       + "".join(leaders) + "".join(marks) + "".join(labels) + "</svg>")

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
              ("quiet", "Outside its top five")]


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
    return "".join(f'<span class="ks"><i style="background:{FILL[k]}"></i>'
                   f'{nm}</span>' for k, nm in STATE_ROWS) + size


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

CONTRAST_BLOCK = f"""<div class="seclab">Hot days and hot nights are different summers</div>
<div class="two">
<div><span class="tl">{DAY_LEAD_N}</span>Its most hot days on record, by
{words(_dl_days)} days. For hot nights, {ordinal(DAY_LEAD['rank']['value'])} of
{DAY_LEAD['rank']['of_years']}.</div>
<div><span class="tl">{NIGHT_LEAD_N}</span>{ordinal(NIGHT_LEAD['days']['rank']['value'])} of
{NIGHT_LEAD['days']['rank']['of_years']} for hot days. For hot nights,
{ordinal(NIGHT_LEAD['rank']['value'])} of {NIGHT_LEAD['rank']['of_years']}.</div>
</div>
<p class="subl" style="margin-top:16px">If one measure could stand in for the other,
these two would lean the same way. They lean opposite ways.
<strong style="color:var(--ink);font-weight:500">{sum(1 for d in rows if d['gated'])}
cities show no night figure at all.</strong> They average under two hot nights a year, and
dividing by a base that small gives you a big number and no evidence.</p>""" if CONTRAST_OK else ""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Heat &middot; The Long Swell</title>
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--coast:#C6C5C2;--accent:#173F9E;--bar:#D3D2CB;--land:#E4E3DC;
--f3:#8E240A;--f2:#C05B3D;--f0:#E8E7E2}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--coast:#43423C;
--accent:#6E97E8;--bar:#43423C;--land:#232321;
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
<p class="stand"><strong style="color:var(--ink);font-weight:500">{DH['records']} of these
{DH['of_cities']} European cities have had more hot days this summer than in any year on
record.</strong> In a typical year, that number is {words(DH['baseline']['median_year'])}.</p>
<p class="stand">A hot day means hot <em>for that city</em>: {HOT_HI[1]}&nbsp;&deg;C in
{HOT_HI[0]}, {HOT_LO[1]}&nbsp;&deg;C in {HOT_LO[0]}. Each is measured against its own
thermometer and its own history, never against the others.</p>

{svg}
<div class="key">{key_rows()}</div>
<p class="knote"><strong style="color:var(--ink);font-weight:400">This is {len(rows)}
thermometers, not a temperature map.</strong> Nothing between the marks means anything.
Bigger mark, bigger margin over that city's own record.</p>

<div class="seclab">How far from normal, city by city</div>
<p class="subl">Each row is one city's entire record, one mark per summer.
<strong style="color:var(--ink);font-weight:500">{LEAD['name']}'s {LEAD['now']} hot
days beat all {LEAD['of']} summers it has on file. {TAIL['name']}'s
{TAIL['now']} beat {TAIL['pct']:.0f} in 100 of its own.</strong> A crowded row is
just a longer record.</p>
{all_rows}

{CONTRAST_BLOCK}

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
      f"most unusual {LEAD['name']} at pct {LEAD['pct']:.1f}, "
      f"least {TAIL['name']} at pct {TAIL['pct']:.1f}, "
      f"{sum(1 for d in rows if d['rank'] == 1)} at a record")
