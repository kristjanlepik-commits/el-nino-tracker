"""The front page.

PRODUCTION TEMPLATE. design/make_frontpage_v2.py renders it to
design/mockups/ against the same payloads, so the mockup and the live page
cannot drift.

Structure, and who owns each part:

    standing question   above the map, never changes, product's D-155.
                        A LABEL rather than a claim, which is why it
                        survives a quiet week without changing shape, and
                        it may never carry a number. Wording is editor's.
    weekly lede         editor writes it (D-154). The generated three
                        clauses are the FALLBACK for a week nobody does.
    the map             one layer per channel, above a stated bar.
    the readings        one row per channel, its own selection, its own
                        units, its evidence beside it.
    the wave            El Nino, outside the readings table because a
                        forecast has no rank in its own history.
    the note            Kristjan's, D-093.
    the channels        every channel with its cadence, including the
                        ones still in development.
    subscribe           the same form and promise as /subscribe/.
"""
import json
import sys


from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402
from templates.frontpage_map import map_block  # noqa: E402
from run_brief import (email_capture_form, site_masthead,  # noqa: E402
                       EMAIL_CAPTURE_PROMISE, EMAIL_FORM_CSS,
                       ANALYTICS_SNIPPET, PAGES_BASE_URL, SITE_NAME,
                       SITE_MASTHEAD_CSS)


def load(issue):
    """Every payload the page reads. Nothing is fetched."""
    d = {}
    d["heat"] = json.load(open(ROOT / "heat/data/city_nights.json"))
    d["coords"] = json.load(open(ROOT / "heat/data/station_coords.json"))
    d["fires_week"] = json.load(open(ROOT / "fires/data/current_week.json"))
    _ev = json.load(open(ROOT / "data/events.json"))
    d["events"] = _ev["events"]
    # Every count fires consider defensible, each next to its population.
    # Read, never recomputed: a number that lives only in a message gets
    # recomputed by whoever needs it next, and they get a defensible
    # different answer.
    d["events_counts"] = _ev.get("counts") or {}
    d["crops"] = json.load(open(ROOT / "crops/data/stress_current.json"))
    d["meta"] = json.load(open(
        ROOT / ("docs/briefs/%s/meta.json" % issue)))
    # meta.json carries the buckets; the observed value lives in the
    # snapshot. Reading it off meta returned None and the band printed
    # "n/a" beside two live percentages, which reads as a broken figure
    # rather than an absent one.
    d["snap"] = json.load(open(ROOT / ("snapshots/%s.json" % issue)))
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
        # House rule: every figure is typeset. Fires emits "6.2x".
        fig=str(top.get("stat", "")).replace("x", "\u00d7"),
        ev=ev_bits + ("<br>of a %d-year span: %s" % (span, "; ".join(tail))
                      if tail else ""),
        # D-076: "pending" comes OFF reader-facing surfaces as a NULL, not
        # as a softer word. It is a work state rather than a finding and
        # carries nothing to a reader; Kristjan's reasoning was that it
        # reads as researcher design rather than reader design. The null IS
        # the finding, and its correct render is no chip, exactly as heat
        # and crops get no column. I turned the null back into the word the
        # decision removed, on the most-read surface we have.
        src="NASA FIRMS SNPP &middot; week to 10 Aug",
        tag={"enso": "ENSO-loaded window",
             "non_enso": "not ENSO-linked"}.get(top.get("attribution"), "")))

    dh = d["heat"]["day_headline"]
    floors = (d["heat"].get("coverage") or {}).get("counts_are_floors")
    # THE SUBJECT IS THE SUBSET, NOT THE SET. VD: this read "41 cities /
    # More hot days than in any year on record" with 22 in the figure
    # column, so the sentence's subject was the whole set and the number was
    # a part of it. D-141's label-from-set defect, on the row a reader is
    # most likely to quote.
    rows.append(dict(
        ch="Heat", place="%d of %d cities" % (dh["records"], dh["of_cities"]),
        claim="More hot days than in any year on record",
        fig="%d" % dh["records"],
        ev="each against its own 95th percentile &middot; %s%d of %d measured"
           % ("at least ", dh["records"], dh["of_cities"]) if floors else
           "each against its own 95th percentile &middot; %d of %d measured"
           % (dh["records"], dh["of_cities"])
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
    # FOUR VALUES FOR ONE SENTENCE, so the sentence is the defect. Fires
    # count 18 clearing the anomaly gate and 13 at rank 1; product,
    # recomputing, got 13 at >=2x their own mean and 17 above every prior
    # year. "Past their own record fire week" reads as rank 1 to a reader,
    # and whether ties count against, and where the gate sits, both change
    # the answer. Neither is in the sentence or reachable from it.
    #
    # I shipped 13 as though fires' number settled it. It does not: it
    # settles what FIRES mean, which is the right authority, but the page
    # was deriving the count here rather than reading one they publish.
    # Same rule as heat's ranks, which I have enforced on other people all
    # week: read the field, never re-derive.
    #
    # So this prefers a field and refuses to invent one. Until fires emit
    # it, the clause states the fact the page itself defines two inches
    # below the map, which no reader has to take on trust.
    # READ THE FIELD. Fires now publish a `counts` block with every
    # defensible count beside the population and rule that produced it, so
    # nothing here recomputes one.
    #
    # `record` (17) rather than `record_among_anomalous` (14) is the key
    # this sentence wants. The gated one is a fact about the MARKER SET
    # rather than about the world: the 150-detection noise floor removes
    # real records in small countries, which is what turned 17 into 14.
    #
    # MY REPLACEMENT SENTENCE WAS FALSE IN THE OTHER DIRECTION and fires
    # caught it. "6 countries burned at three times their own same-week
    # average or more" counted MARKS ON A MAP and claimed something about
    # COUNTRIES. Eight did. Lebanon at 5.4x is the highest multiple on the
    # board and appears nowhere on the page, because it sits under the
    # noise floor. Same defect as the one I had just fixed, pointing the
    # other way, and it UNDERSTATED, which is the harder direction to
    # notice because nothing looks exaggerated.
    _counts = (d["events_counts"] or {})
    n_fire = _counts.get("record")

    recs = [(p["place"], [r for r in (p.get("regions") or [])
                          if r.get("rank") == 1]) for p in d["crops"]["places"]]
    recs = [(p, r) for p, r in recs if r]
    n_reg = sum(len(r) for _, r in recs)

    out = []
    if dh["records"]:
        out.append("<b>%s%d of %d cities</b> have had more hot days than in "
                   "any year on record." % ("At least " if floors else "",
                                            dh["records"], dh["of_cities"]))
    else:
        out.append("<b>No city</b> of the %d measured has had more hot days "
                   "than in an earlier year." % dh["of_cities"])

    # THE FIRES CLAUSE IS WITHHELD, editor's instruction and product's
    # arithmetic. A place at rank 1 of n observations is rank 1 by chance
    # with probability 1/n, so the count expected by chance is places
    # divided by observations per place:
    #
    #     heat    42 cities  / 77 years = 0.5 expected, 22 observed   40x
    #     fires   94 places  / 14 years = 6.7 expected, 17 observed  2.5x
    #
    # Fires' record is only fourteen years deep, so roughly two in five of
    # those countries could be chance. The sentence reads EXACTLY like
    # heat's and is a far weaker claim, and two clauses side by side in
    # identical grammar assert an equivalence the numbers do not support.
    #
    # This is not the fires count being wrong. It is a count published
    # without its null distribution, one level up from a figure published
    # without its denominator, and we have now shipped without each of
    # those once. Filed as #21 for fires to null it against its own
    # history, as crops did.
    #
    # Withheld LOUDLY. A clause that quietly stops appearing is the absence
    # that fails nothing.
    if n_fire:
        print("  lede: fires clause WITHHELD (#21). %d records against ~%.1f "
              "expected by chance on a 14-year record; needs a null "
              "distribution before it can sit beside heat's." % (n_fire, 6.7))

    # THE CROPS COUNT NEVER SHIPS WITHOUT ITS DISTRIBUTION. Editor's catch,
    # and the sharper of the two: 69 regions at a record low reads as
    # alarming and is an ordinary number. The crops page exists partly to
    # say so, with 81 as the even-spread expectation and 24 to 104 as the
    # last twelve years. The bare count in the largest type on the site, one
    # link above the page that calibrates it, is the exact error that page
    # was built to prevent.
    # CRO'S WORDING, and their objection was to the ROUTE rather than the
    # conclusion. Editor's reasoning was that 69 sits below the even-spread
    # expectation of 81, and 81 is regions divided by 26: the uniform
    # baseline, which "never a uniform 1/26 baseline" is the oldest standing
    # rule on this channel. It fails in different directions in different
    # places and cannot be corrected, only counted.
    #
    # Against the EMPIRICAL baseline the picture is close to the opposite:
    # nine of the last twelve years sit below 69, so it is above average and
    # comfortably inside the range. "An ordinary number" was defensible on
    # the range and wrong on the reason, and CRO's point is that the wrong
    # reason is the dangerous half, because the next call made that way will
    # not be lucky.
    cb = d["crops"].get("chance_baseline_aggregate") or {}
    lo, hi = cb.get("recent_min"), cb.get("recent_max")
    series = cb.get("series") or {}
    recent = sorted(series.items())[-13:-1]        # the twelve prior years
    n_under = sum(1 for _, v in recent if v < n_reg)
    if not n_reg:
        out.append("<b>No crop region</b> is at its worst for this point in "
                   "the season.")
    elif recent and lo is not None and hi is not None:
        out.append("<b>%d crop regions</b> are at their worst for this point "
                   "in the season: more than in %s of the last %s years, and "
                   "well inside a range that has run %d to %d."
                   % (n_reg, _word(n_under), _word(len(recent)), lo, hi))
    else:
        out.append("<b>%d crop regions</b> are at their worst for this point "
                   "in the season." % n_reg)
    return " ".join(out)



def _spread(hb):
    """The disagreement, beside the figure it governs, in the shape it has.

    EDITOR'S RULING, D-051 applied: a headline probability may not appear
    bare in large type, because the qualifier travels with the datum and
    nothing else survives a screenshot of the band.

    MY FIRST VERSION RENDERED "27 to 98 across the six models" AND SCIENCE
    CORRECTED BOTH HALVES. 27 is the CPC anchor, their published table
    fitted with a skew-normal, and it is the one figure in the set that is
    not a model run. And the models do not span a range: this week four sit
    at 98 or above, two at 40 or below, and none between. It is a SPLIT.

    That version was a worse failure than the bare number it replaced.
    "Somewhere between 27 and 98" tells a reader we are unsure; the truth is
    that two camps are each quite sure and disagree, and 70% is a value no
    model produces. A qualifier that removes the finding is a new shape:
    every other defect this week was an ABSENCE, which is at least neutral,
    and this one installs a false structure while wearing the costume of
    diligence.

    SO THE DATA DECIDES THE SHAPE, NOT ME. The split is taken at the largest
    gap between adjacent models. If that gap is wide the set is bimodal and
    the sentence says so; if it is narrow the models really do spread and
    the sentence says that instead. Hard-coding "it is a split" would be
    the same error one level up: true this week, and silently wrong the week
    the models converge.

    n_members travels with the percentages because it must. Two of the six
    run ten-member ensembles, so their figures move in ten-point steps and a
    bare 30 beside a 32-member 100 invites a precision neither has.

    per_model lands with the 2026-08-17 issue. Until then this falls back to
    the three figures meta.json does carry, each on its own footing, with no
    range claim.
    """
    b = hb.get("record_>3.5") or {}
    anchor = ("CPC&rsquo;s own table implies %d%%" % b["anchor"]
              if b.get("anchor") is not None else "")

    pm = b.get("per_model") or {}
    if pm:
        vals = sorted(((v.get("pct"), v.get("n_members"), k)
                       for k, v in pm.items() if v.get("pct") is not None),
                      reverse=True)
        if len(vals) >= 3:
            gaps = [(vals[i][0] - vals[i + 1][0], i)
                    for i in range(len(vals) - 1)]
            gap, at = max(gaps)
            hi, lo = vals[:at + 1], vals[at + 1:]
            small = min((n for _, n, _ in vals if n), default=None)
            step = (" The smallest ensembles carry %d members, so those "
                    "figures move in %d-point steps." % (small, round(100 / small))
                    if small and small <= 12 else "")
            if gap >= 20:
                body = ("%s of %s models put it at %g%% or above and %s at "
                        "%g%% or below, with none in between"
                        % (_word(len(hi)), _word(len(vals)), hi[-1][0],
                           _word(len(lo)), lo[0][0]))
            else:
                body = ("the %s models run from %g%% to %g%%"
                        % (_word(len(vals)), vals[-1][0], vals[0][0]))
            return ("The +3.5 figure is ours, and no model produces it: "
                    + body + ". " + anchor + "." + step)

    bits = [x for x in (
        anchor,
        "the model consensus is %d%%" % b["consensus"]
        if b.get("consensus") is not None else "",
        "ECMWF SEAS5 alone is %d%%" % b["seas5"]
        if b.get("seas5") is not None else "") if x]
    if not bits:
        return ""
    return ("The +3.5 figure is ours, and no single model produces it: "
            + "; ".join(bits) + ".")


def _word(n):
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
            7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
            12: "twelve"}.get(n, str(n))


# PRODUCT'S D-155, and editor owns the wording. A STANDING question above
# the map that never changes, with the weekly lede beneath it. It is a
# LABEL rather than a claim, which is why it survives a quiet week without
# changing shape, and product has ruled it may never carry a number.
#
# It replaces "how big is this, actually?", which Kristjan killed: "actually
# is a bad word to use there, kind of garbage." That string was in three
# places that had to agree, because the title and og:title are what a reader
# sees in a browser tab and in every link preview, and two different
# standing questions means clicking one and arriving at another.
STANDING_QUESTION = "Where is the climate abnormal this week, and how bad?"


def page(d, canonical, og_image_url, root_prefix, desc, brief_date_iso):
    _mb = map_block(d, root_prefix)
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
    _cuts = [v.get('counted_to') for v in d['heat']['cities'].values()
             if v.get('counted_to')]
    _cut = max(_cuts) if _cuts else None
    n34 = ("%+.1f&nbsp;&deg;C" % nino) if nino is not None else "n/a"

    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{sitename} &middot; {standing}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{sitename}">
<meta property="og:title" content="{sitename} &middot; {standing}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{ogimage}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{sitename} &middot; {standing}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{ogimage}">
{analytics}
<style>
{faces}
{mastcss}
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
/* THE STANDING QUESTION SITS ABOVE THE LEDE, per D-155: a label the page
   always carries, then this week's finding beneath it. Set as a label
   rather than a headline, because product ruled it is not a claim and may
   never carry a number: if it competed with the lede for weight, a reader
   would meet two headlines and neither would land. */
.standing{{margin:22px 0 0;font-family:"{data}",monospace;font-size:11px;
 letter-spacing:.2em;text-transform:uppercase;color:var(--ink-faint)}}
h1{{margin:14px 0 0;font-weight:400;font-size:31px;line-height:1.3;
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
 border-bottom:1px solid var(--rule);white-space:nowrap}}
/* The channel row wraps between its links and never inside one. On a
   phone it stacks; the separators go with the line above them. */
.chl{{display:inline-block}}
/* TYPOGRAPHIC, NOT HUED. The comp gives this band a blue rule and a blue
   label; D-101 retired channel hue and the case being made for its return
   is scoped to map markers. */
.wave{{text-decoration:none;color:inherit;margin-top:40px;background:var(--paper-sunk);border-left:3px solid
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
.pullwrap{{text-decoration:none;color:inherit;display:block}}
.pullwrap:hover .pull{{color:var(--nino)}}
.note .pull{{display:block;font-weight:500;font-size:26px;line-height:1.32;color:var(--ink);
 max-width:44ch;text-wrap:pretty}}
.note .by{{display:block;font-family:"{data}",monospace;font-size:11px;color:var(--ink-faint);
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
.ebd{{margin-top:44px;border-top:3px solid var(--ink);padding-top:18px;
 display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px 48px;
 align-items:start}}
.ebd .k{{font-family:"{data}",monospace;font-size:9.5px;letter-spacing:.22em;
 text-transform:uppercase;color:var(--ink)}}
.ebd .p{{margin:9px 0 0;font-size:19px;line-height:1.45;color:var(--ink);
 max-width:34ch;text-wrap:pretty}}
.ebd .fine{{margin:9px 0 0;font-family:"{data}",monospace;font-size:10.5px;
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
/* FULL OPACITY. VD: the field carries data and attenuation is for
   furniture only. The weight problem was solved by thresholding the
   fill, not by fading it. */
svg .sstfield{{opacity:1}}
svg .ldr{{stroke:var(--ink-faint);stroke-width:1}}
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
/* FULL OPACITY. VD: the field carries data and attenuation is for
   furniture only. The weight problem was solved by thresholding the
   fill, not by fading it. */
svg .sstfield{{opacity:1}}
svg .ldr{{stroke:var(--ink-faint);stroke-width:1}}
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
 .ebd{{grid-template-columns:1fr}}
 .ebd{{grid-template-columns:1fr}}
}}
</style></head><body><div class="shell">

{masthead}

<div class="asof"><span style="color:var(--ink)">Updated {updated}</span></div>

<p class="standing">{standing}</p>
<h1>{lede}</h1>
<div class="seclab">Where, this week
<span class="r">{mb_state}{mb_sst}</span></div>
{mb_svg}
{mb_legend}
<p class="mapnote"><b>Only what clears a stated bar is drawn: fires at
{mb_bar_f}, crops with {mb_bar_c}.</b> {mb_below} more crop countries and {mb_below_f} more
fire countries passed their own record without clearing it; each is counted
on its channel page. Marks are
sized within a channel, never across. <a href="{rp}about.html">How this is
built &rarr;</a></p>

<div class="seclab" style="border-bottom:none;margin-top:40px">The readings
&nbsp;&middot;&nbsp; one slot per channel
<span class="r">each row is its channel&rsquo;s own selection, with its
evidence beside it</span></div>
{rows}
<div class="rend"></div>
<div class="more"><span style="max-width:74ch">Chips mark attribution where a
channel runs it. Fires does; Heat and Crops do not assess attribution, so the
column is absent rather than empty.</span>
<!-- NOWRAP ON EACH LINK, NEVER ON THE ROW. Holding all three together
     made the row 129px wider than a 390px phone, so the whole front page
     scrolled sideways: the one layout fault a reader cannot ignore and
     the one no desktop check sees. Each link still refuses to break its
     own label; the row breaks between them. -->
<span class="chl"><a href="{rp}fires/">Fires, {n_fire} countries &rarr;</a> &nbsp;&middot;&nbsp; <a href="{rp}heat/">Heat,
{n_city} cities &rarr;</a> &nbsp;&middot;&nbsp; <a href="{rp}crops/">Crops,
{n_ctry} countries &rarr;</a></span></div>

<a class="wave" href="{rp}elnino/"><span class="k">The wave &nbsp;&middot;&nbsp; El Ni&ntilde;o
2026-27</span>
<span class="v"><b class="ws-num num">{p25}</b>% chance of a peak beyond
+2.5&nbsp;&deg;C,
<b>{p35}%</b> beyond +3.5</span>
<span class="spread">{spread}</span>
<span class="r">Ni&ntilde;o 3.4 {n34} &middot; issue {issue} &middot;
the El Ni&ntilde;o tracker &rarr;</span></a>

<div class="note">
<div><div class="k">Notes</div>
<div class="sub">Written by hand, about what the instruments are showing.</div></div>
<div><a class="pullwrap" href="{rp}notes/"><span class="pull">There is a great
amount of data sitting in different databases, and getting an answer out of
it is another thing entirely. So I started building that.</span>
<span class="by">How bad is it? &middot; 10 August 2026 &middot; read the
note &rarr;</span></a></div></div>

<!-- AFTER THE READINGS AND THE NOTE, BEFORE THE DIRECTORY. It was at
     96% of the page, under the channel table, which is the same defect
     this whole unit was built to fix: a form at line 470 of 485. A reader
     who has met the map, the three readings, the wave and the note has
     had the week; the channel table is a directory of where to go next
     and belongs on the far side of the ask. -->
<div class="ebd">
<div><div class="k">One email a week</div>
<p class="p">{promise}</p></div>
<div>{form}<p class="fine">Confirmation email required. No spam, and the
archive stays free and public whether you subscribe or not.</p></div></div>

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
averaged</span></div>

</div>{script}</body></html>""".format(
        faces=T.font_faces_css(root_prefix + "fonts/"), vars=T.css_variables(),
        prose=T.FONT_PROSE, data=T.FONT_DATA, lede=lede(d)[0], rows=rows,
        nino_col=T.NINO,

        n_fire=d["events_counts"].get("anomalous",
               sum(1 for e in d["events"] if e.get("anomalous"))),
        n_city=len(d["heat"]["cities"]),
        n_ctry=sum(1 for p in d["crops"]["places"]
                   if any(r.get("rank") == 1 for r in (p.get("regions") or []))),
        p25=hb["9715_>2.5"]["mid"], p35=hb["record_>3.5"]["mid"],
        spread=_spread(hb),
        n34=n34, rp=root_prefix, masthead=site_masthead(root_prefix), issue=brief_date_iso,
        updated=max([x for x in (brief_date_iso, _cut) if x]), standing=h(STANDING_QUESTION), sitename=h(SITE_NAME),
        desc=h(desc), canonical=h(canonical), ogimage=h(og_image_url),
        analytics=ANALYTICS_SNIPPET, mastcss=SITE_MASTHEAD_CSS,
        rule_dark=T.RULE_DARK, root_prefix=root_prefix,
        mb_svg=_mb["svg"], mb_legend=_mb["legend"],
        mb_bar_f=_mb["bar_f"], mb_bar_c=_mb["bar_c"],
        mb_below=_mb["below_crops"], mb_below_f=_mb["below_fires"],
        # "past the bar" was defined in the caption BELOW the map, so a
        # first-time reader met the term before its definition. Says what
        # it means instead.
        # SPLIT, NOT SUMMED. CRO's send-back, and the evidence is blunt:
        # 17 of the 36 crops countries qualify on a SINGLE region, one of
        # them 1 of 82. Fires' 17 is a country past its own record WEEK;
        # crops' 36 counts a country where one region of eighty-two hit a
        # record. Those are not the same event, and adding them made 53 a
        # count of nothing in particular.
        #
        # D-090's first constraint, never rank across instrument types,
        # arriving as a SUM rather than a table. A sum is a table with one
        # row. Each channel's count beside its own name needs no extra
        # words to be honest.
        mb_state="%d drawn &middot; %d fire countries past their own record "
                 "week &middot; %d crop countries with a region at a record "
                 "low" % (_mb["n_shown"], _mb["n_fires_rec"],
                          _mb["n_crops_rec"]),
        mb_sst=(" &middot; ocean field observed 7 days to %s"
                % _mb["sst_date"]) if _mb.get("sst_date") else "",
        script=_mb["script"],
        form=email_capture_form(label="Subscribe"),
        promise=h(EMAIL_CAPTURE_PROMISE), ecss=EMAIL_FORM_CSS)




def render(meta, brief_date_iso, canonical_url, og_image_url,
           root_prefix=""):
    """The front page. Called from run_brief.build_public_html(is_front=True).

    Reads the channel payloads itself rather than taking them as arguments,
    the same way the mockup does, so the two cannot render different data.
    Nothing here fetches.
    """
    d = load(brief_date_iso)
    hb = d["meta"]["headline_buckets"]
    magn = hb.get("9715_>2.5", {}).get("mid")
    desc = ("Where the climate is abnormal this week, measured against each "
            "place's own record. %s%% chance of a 1997/2015-magnitude El "
            "Niño peak." % magn)
    return page(d, canonical_url, og_image_url, root_prefix, desc,
                brief_date_iso)
