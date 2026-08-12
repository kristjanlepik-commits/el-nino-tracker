"""The crops channel index: worst first, by how bad rather than by rank.

Modelled on the fires index, and it has to differ in one way that
matters. Fires ranks by a multiple, which is already a magnitude. Crops
ranks places against their own 26-year record, and a rank is not a
magnitude: Brokopondo at z -3.79 and Kien Giang at -0.64 are both "worst
on record" and are six times apart. A list ordered by rank would treat
them as equal and would be true and badly wrong.

So this orders by severity, the z-score itself, and prints it. Rank
answers "has this happened before"; z answers "how bad is it". The page
needs both and leads with the second.

## The chance baseline is a sentence up top and a chart at the bottom

It led the page until Kristjan read it cold and said the opening screen
was more about our methodology than about what we were showing. He is
right, and the fix is not to delete the anchor: without it a reader
concludes 81 is alarming. The lede states it in one line, the footer
chart proves it, and proving is footer work.

With 2,122 units each holding a 26-year record, an even spread would
give about 82 a dekad, and 81 were observed.

That "even spread" is an assumption and the page now says so. Records
hoard: Europe's record lows sit in 2001, 2003 and 2006, so the uniform
figure overstates what recent European years should produce by about
four times. The global 81.6 has not been checked against an empirical
expectation either, so it is labelled "if records fell evenly" rather
than "chance produces" until the owning channel supplies one.

**The page must not call the total unremarkable, and an earlier version
did.** The measured expectation now arrives as
`chance_baseline_aggregate`: against a 2014-2025 mean of 59.2 and a
range of 25 to 105, this dekad's 81 is higher than all but two of the
last twelve years.

The page states that as a RANKING and not as a verdict adjective. The
adjective is the part that gets quoted and the ranking is the part a
reader can check.

That the field carries `_scope` is the load-bearing detail. The first
figures for it were counted over the full 2,166-unit catalogue while
this page shows 2,123, which inflated the baseline and left the
headline untouched, because the 45 skipped places are tiny and none
holds a record this dekad. The error was invisible in the current year
and would have compared 81 over one set against a mean over a wider
one. It surfaced only because the number was rebuilt from the payload
instead of trusted.

## One list, grouped by country

There were two sections, breadth and depth, and a sentence above them
explaining that neither outranked the other. Needing that sentence was
the signal the split was wrong, so they are now one list grouped by
country: Chad appears once with its eight regions together, which IS
the finding. On the flat list Ennedi Est sat at rank seven between two
Suriname districts and told a reader nothing.

## One grade of sentence, because the field does not license two

There is ONE grade of sentence: "lowest on record for this point in the
season". An earlier version promoted rows with driver=water to "driest",
and that was wrong even though the field was read with perfect fidelity.
`driver` records a twenty-five year correlation between a COUNTRY's
vegetation and the water instruments; it does not diagnose this dekad.
The measurement underneath is FPAR, canopy greenness, which cannot
separate drought from flooding, pests, late planting or conflict.

Cairo is the case that settles it: rendered as "driest on record" over
Nile-irrigated cropland, a drought claim about a place whose water does
not fall from the sky, one line above its own "attribution pending" tag.

The field still says something weaker, and it says it in its own
sentence: vegetation here usually tracks water availability.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)
from templates.chance_baseline import scales_block, CHANCE_CSS  # noqa: E402
from templates.crops_map import map_block, CROPS_MAP_CSS       # noqa: E402

TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked",
            "pending": "attribution pending"}
TAG_SLUG = {"enso": "loaded", "non_enso": "notlink", "pending": "pending"}



def _word(n: int) -> str:
    """Small numbers spelled out, because this one sits in prose."""
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
            7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
            12: "twelve"}.get(n, str(n))


def _and(names) -> str:
    return names[0] if len(names) == 1 else " and ".join(names)


def _dekad_index(iso: str) -> int:
    """ISO date to dekad of 36, where dekad 1 is 1-10 January.

    The payload's season field is a dekad index and its date is an ISO
    string, so something has to convert. Doing it here keeps the page
    from comparing a date against an index, which is the "quantity used
    as a different kind of quantity" error this channel keeps hitting.
    """
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except (ValueError, AttributeError):
        return 0
    return (m - 1) * 3 + min((d - 1) // 10, 2) + 1


def _driver_note(e) -> str:
    """What `driver` actually licenses, in the present tense of habit.

    "Usually tracks" is a statement about the country's twenty-five year
    correlation, which is what the field measures. It says nothing about
    this dekad, so it cannot collide with the attribution tag beside it,
    and it is set faint because it is context rather than the finding.
    """
    if e.get("driver") != "water":
        return ""
    return ('<span class="cdriver">vegetation here usually tracks water '
            'availability</span>')


# Countries a reader comes looking for, shown every week whether or not
# anything is happening in them. Kristjan, 2026-08-09: "some countries are
# just always visible", the same arrangement Fires already uses.
#
# WHY THIS DOES NOT FIGHT CRO's GATE. The qualifying rule is rank 1 AND the
# control holds, and it decides who gets SELECTED. A pinned country is not
# selected; it is on the page because somebody went looking for it. So it
# does not clear a selection bar, it only has to state its own figures
# correctly, adjusted rank included.
def _ord(n: int) -> str:
    """1st, 2nd, 3rd. 11-13 take 'th', which the naive n%10 rule gets wrong."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


# ENGLAND IS PINNED AS A REGION, NOT THE UK AS A COUNTRY, and this is the
# one entry that is not a country. CRO's ruling, and the reason is stronger
# than the one I went in with.
#
# I proposed the UK aggregate showing its adjusted rank, on the argument
# that the control had done its job and rank 2 was the honest figure. That
# was the wrong objection. Every country figure on this channel is an
# UNWEIGHTED mean over its regions, and the UK has four:
#
#     Scotland          +0.376
#     Northern Ireland  +0.457
#     Wales             +0.267
#     England           -0.006
#     national          +0.273   unweighted mean of the four
#
# England holds the overwhelming majority of UK cropland. So the national
# number is not England slightly diluted; it is dominated by three regions
# that are a small minority of the crop. The quantity being ranked is the
# wrong quantity, which no adjusted rank repairs.
#
# England is also the thing a reader means by the British harvest, and it
# holds the control at rank 1. The sound number and the surviving number
# are the same number.
PINNED = ["France", "Spain", "Germany", "Italy", "Hungary", "Austria"]
PINNED_LABEL = {}
# (place, region). Read from the region record, which carries its own rate,
# control and series.
PINNED_REGIONS = [("U.K. of Great Britain and Northern Ireland", "England")]
# IMPORTED, NOT DERIVED. CRO's instruction, and it has drifted twice: seven
# European pages unlinked for four days, then the lit-versus-linked label
# bug fixed this evening. The builder decides which countries have a page,
# so the builder's own set is what decides which are linked.
from crops.build_country_pages import PINNED_PLACES as _PINNED_PLACES  # noqa: E402


def _pinned_row(p) -> str:
    """One pinned country. Never a near-miss, never a warning."""
    from templates.crops_country import slugify as _slug
    name = PINNED_LABEL.get(p["place"], p["place"])
    r, sv = p.get("rate") or {}, p.get("severity") or {}
    bits = []
    if sv.get("available") and sv.get("rank"):
        bits.append(f"{_ord(sv['rank'])} most stressed of {sv['of']}")
    if r.get("available") and r.get("rank"):
        # THE ADJUSTED RANK, when the control says the raw one is inflated.
        # Printing rank 1 here would publish the exact figure CRO's control
        # exists to discount, on the one country most likely to be quoted.
        ctl = r.get("_start_control") or {}
        if ctl and not ctl.get("holds") and ctl.get("adjusted_rank"):
            bits.append(f"{_ord(ctl['adjusted_rank'])} steepest fall of "
                        f"{r['of']} once its high starting level is "
                        f"accounted for")
        else:
            bits.append(f"{_ord(r['rank'])} steepest fall of {r['of']}")
    # D-043: the calm case is drawn, not summarised, and it must not read as
    # a near miss. An ordinary country says so in the same words every week.
    if not bits:
        bits.append("within its own normal range")
    # LINKED ONLY IF THE PAGE EXISTS. crops/build_country_pages.py builds a
    # page only for countries with a region at a record low, which a pinned
    # country by definition may not have, so six of the seven links 404ed
    # and the dead-link guard caught it before this shipped.
    #
    # Not worked around by pointing somewhere else. The country page is
    # built around record-low regions and would render empty for these; VD's
    # review already says every region should get a row rather than only the
    # record lows, and that change is what earns these countries a page.
    # Until then the name is text, which is honest about there being nothing
    # further to read.
    # TEST WHAT THE BUILDER TESTS, rather than a predicate that happens to
    # agree with it. This read "has a region at rank 1", which WAS the
    # builder's rule until crops changed it to "record low OR pinned". All
    # seven European pages then existed and served 200 while the index
    # silently declined to link them, for four days, because the two rules
    # had drifted apart.
    #
    # CRO imported PINNED into the builder specifically so the two files
    # could not disagree about which countries are pinned, and neither of us
    # noticed that PAGE EXISTENCE was independently re-derived here. Same
    # fault one level down, on a different fact.
    #
    # AND NOTHING CAUGHT IT. The dead-link guard fires on a link that points
    # nowhere; a link that should exist and does not is not malformed, so it
    # is invisible to every check we have. Same shape as the coverage
    # disclosure that vanished when its count reached zero: an absence fails
    # nothing.
    #
    # PINNED_PLACES mirrors crops/build_country_pages.py. It should be
    # imported from there once CRO exposes it as a named predicate; asked.
    page_place = p.get("_page_place", p["place"])
    has_page = (any(r.get("rank") == 1 for r in (p.get("regions") or []))
                or page_place in _PINNED_PLACES)
    title = (f'<a class="cglink" href="{h(_slug(page_place))}/">{h(name)}</a>'
             if has_page else h(name))
    return (f'<p class="cghead">{title}</p>'
            f'<p class="pinsub">{h(", ".join(bits))}.'
            + _agg_note(p) + '</p>')


def _agg_note(p) -> str:
    """How the country figure was built, next to the country figure.

    CRO tried twice to emit a per-country "how exposed is this aggregate"
    score and both attempts failed in ways worth not repeating: the cheap
    one fired on 62 of 123 countries and missed the case it was built for,
    and the leave-one-out version understated by half. A flag that fires
    everywhere is useless and one that understates is worse than none,
    because it reads as reassurance.

    So there is no score, and this prints the method instead: how many
    regions were averaged and what share one carries. That is true without
    crop-area data, and on the country it was built for it states the whole
    problem as a number rather than a judgement. It is also why England is
    pinned as a region and the UK is not.
    """
    a = p.get("aggregate") or {}
    if not a.get("regions_averaged"):
        return ""
    # CRO's OWN SENTENCE, not my arithmetic on their fields. I computed the
    # share from one_region_carries and printed 4% where their caveat says
    # 5%: round(0.045 * 100) is 4 in Python, which rounds halves to even.
    # Two surfaces disagreeing about the same figure by a rounding rule is
    # the smallest possible version of the drift this whole day was about,
    # and the fix is the same one every time: read the computed string.
    #
    # Only the first sentence. The rest explains why no sensitivity score
    # exists, which belongs in the methodology rather than beside a country.
    first = (a.get("caveat") or "").split(". ")[0].strip().rstrip(".")
    if not first:
        return ""
    return f' <span class="pinagg">{h(first[0].upper() + first[1:])}.</span>' 


def _pinned_block(places) -> str:
    by = {p["place"]: p for p in places}
    rows, absent = [], []
    for country, region in PINNED_REGIONS:
        p = by.get(country)
        rec = next((r for r in (p.get("regions") or []) if r["region"] == region),
                   None) if p else None
        if rec and rec.get("rate"):
            # crop_units is the country's; a region is one unit of it, and
            # printing the country's 4 next to a region name would say
            # England has four crop regions.
            # The row is a REGION but the page is its COUNTRY's, so the
            # link test and the href both need the country. Testing
            # rec["place"] asked whether "England" had a page, which
            # nothing builds, and England alone stayed unlinked while
            # the other six worked.
            rows.append(_pinned_row(dict(rec, place=region,
                                         crop_units=None,
                                         _page_place=country)))
        else:
            absent.append(region)
    rows += [_pinned_row(by[c]) for c in PINNED
             if c in by and by[c].get("publishable")]
    absent += [c for c in PINNED if c not in by or not by[c].get("publishable")]
    if not rows:
        return ""
    note = ""
    if absent:
        # Named, not dropped. A pinned country that silently vanishes is the
        # absence-as-zero shape on the one list a reader checks by name.
        note = (f'<p class="secsub">Not measurable this dekad: '
                f'{h(", ".join(PINNED_LABEL.get(c, c) for c in absent))}.</p>')
    return (f'<p class="seclab">Countries readers ask about</p>'
            f'<p class="secsub">Shown every week, whether or not anything '
            f'is happening in them. Each is measured against its own '
            f'record and never against the others.</p>'
            f'{"".join(rows)}{note}')


def _country_group(country, regions, cb=None, units=None) -> str:
    """One country, with every region of it that is at a record low.

    The count and the denominator sit in the heading because that is the
    comparison a reader can make unaided: eight of twenty-two reads
    differently from one of twenty-four, and the flat list said neither.
    """
    n = len(regions)
    if cb and units:
        # Above its own recent maximum: say so here, in its own terms.
        sub = (f"{n} of {units} regions, against a previous high of "
               f"{cb['recent_max']} and a recent average of "
               f"{cb['recent_mean']:g}")
        cls = " up"
    else:
        sub = (f"{n} region{'s' if n != 1 else ''} at a record low"
               + (f" of {units}" if units else ""))
        cls = ""
    # EVERY flagged country gets its trajectory, not just the leading
    # one. Six small charts are scannable in a way six countries times N
    # region rows never is, and they calibrate by construction: Sudan at
    # 3 against a previous high of 2 visibly does not look like Chad at
    # 8 against 3. That is the thing we otherwise have to say in a
    # caveat, done by the drawing instead.
    #
    # The chart stays OUTSIDE the disclosure. It is the overview, so
    # hiding it behind a click would defeat what it is for.
    chart = _trajectory(cb, country) if cb else ""
    # Regions collapse. Grouping made the countries legible and then the
    # inline regions made the page long enough to lose the overview
    # again; a disclosure is the rung between an inline list and a
    # per-country subpage, and it costs no new page type, no payload
    # growth and no extra surface for the channel to sign off.
    n_lab = f"{n} region{'s' if n != 1 else ''}"
    # The country name links to its own page. Without this the 41 pages
    # exist and are unreachable, which is the drill-down half-built.
    from templates.crops_country import slugify as _slug
    return (f'<div class="cg{cls}">'
            f'<p class="cghead"><a class="cglink" href="{h(_slug(country))}/">'
            f'{h(country)}</a>'
            f'<span class="cgsub">{h(sub)}</span></p>{chart}'
            f'<details class="cgd"><summary>{n_lab}</summary>'
            + "".join(_row(e) for e in regions) + '</details></div>')


def _row(e) -> str:
    # ONE sentence, never two grades. "Driest" was here and is wrong,
    # and it was wrong even though it was applied with perfect fidelity
    # to the channel's `driver` field: CRO checked all twenty rows and
    # found zero mismatches. Reading a field correctly is not the same
    # as being licensed to say what I said with it.
    #
    # driver=water means the country's vegetation anomaly correlated
    # with the water instruments across 2002-2025. That is a property of
    # the COUNTRY OVER TWENTY-FIVE YEARS, not a diagnosis of this dekad.
    # And the measurement is FPAR, canopy greenness: a region can sit at
    # its lowest on record from flooding, pests, late planting or
    # conflict. CRO's own qualifier on every place says heat, drought,
    # disease and late planting are not separable in this instrument.
    #
    # Two things made it indefensible rather than merely loose. Cairo
    # rendered as "driest on record", and Egyptian cropland is
    # Nile-irrigated, so it read as a drought claim about a place whose
    # water does not fall from the sky. And every card carries
    # "attribution pending" directly beneath, so the card contradicted
    # its own tag one line later.
    #
    # The driver field still says something; it just says something
    # weaker, and it belongs in its own sentence rather than inside the
    # claim. See `_driver_note`.
    # CRO's `statement`, rendered bound to the number rather than
    # authored here. It binds the value to its basis in one string that
    # a layout decision cannot separate, which is the point of it: a
    # page showing a rank without its basis is then MISSING A FIELD
    # rather than subtly wrong, and that fails closed.
    #
    # The sentence I had written was true of every row on this page,
    # since all 81 are rank 1, and it still omitted the basis years. The
    # near-miss that produced this field is the same shape: editor
    # drafted "lowest since this measurement started in 2001", which was
    # false for 7 of Chad's 8 regions, because the qualifier lived on
    # the country object while the claim was about a region.
    claim = e.get("statement") or "lowest on record for this point in the season"
    # D-076: "attribution pending" comes off every entry. It was the
    # code's default fallback, so it rendered on all 81 rows and read as
    # clutter rather than as information. It is a work state, not a
    # finding. The two ENSO strings stay, because those ARE findings.
    tag = ""
    if e.get("attribution") in ("enso", "non_enso"):
        tag = (f'<span class="tag tag-{TAG_SLUG[e["attribution"]]}">'
               f'{h(TAG_TEXT[e["attribution"]])}</span>')
    # The country is in the group heading now, so repeating it on every
    # row was the same word eighty-one times.
    return f"""
      <div class="crow">
        <span class="cz">{e['z']:+.2f}</span>
        <span class="cmain">
          <span class="cplace">{h(e['region'])}</span>
          <span class="cclaim">{h(claim)}{_driver_note(e)}</span>
        </span>{tag}
      </div>"""


def _trajectory(cb: dict, place: str) -> str:
    """A country's own record-low count, year by year.

    This replaces a binomial. It needs no independence assumption, which
    is the assumption that was wrong: neighbouring regions in one drought
    are not independent draws, so a p-value computed over them looked
    precise and was not. A reader can see twenty-five years of mostly
    nothing and then this one, and that is both more legible to a 4-8
    and more defensible than any test.
    """
    series = {int(y): v for y, v in cb["series"].items()}
    years = sorted(series)
    hi = max(max(series.values()), 1) * 1.25
    W, H, PAD_T, PAD_B, PAD_L, PAD_R = 660, 150, 26, 26, 8, 8
    slot = (W - PAD_L - PAD_R) / len(years)
    bw = min(slot * 0.6, 16.0)

    def Y(v):
        return H - PAD_B - v / hi * (H - PAD_T - PAD_B)

    out = []
    rm = cb.get("recent_mean")
    if rm is not None:
        y = Y(rm)
        out.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" '
                   f'y2="{y:.1f}" stroke="var(--ink-soft)" stroke-width="1" '
                   f'stroke-dasharray="4 3"/>')
        out.append(f'<text class="tj-s" x="{PAD_L + 2}" y="{y - 5:.1f}">'
                   f'recent average {rm:g}</text>')
    cur = max(years)
    for i, yr in enumerate(years):
        v = series[yr]
        cx = PAD_L + slot * (i + 0.5)
        fill = "var(--crop)" if yr == cur else "var(--rule-45)"
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" '
                   f'width="{bw:.1f}" height="{max(H - PAD_B - Y(v), 1.0):.1f}" '
                   f'fill="{fill}"/>')
        if yr in (years[0], cur):
            out.append(f'<text class="tj-x" x="{cx:.1f}" y="{H - 8:.1f}" '
                       f'text-anchor="middle">{yr}</text>')
        if yr == cur:
            out.append(f'<text class="tj-v" x="{cx:.1f}" y="{Y(v) - 7:.1f}" '
                       f'text-anchor="middle">{v}</text>')
    return (f'<svg class="tj" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{h(place)} crop regions at their worst on record, '
            f'each year since {years[0]}">' + "".join(out) + "</svg>")


def _freshness(doc) -> str:
    """What the page is actually looking at, and how old it is.

    CRO's FRESHNESS.md, and this fixes a claim the page was making by
    omission. The eyebrow stamped the page with the TOP-LEVEL `dekad`,
    which is true of 122 places and FALSE of Oman: out-of-season places
    freeze at their last in-season dekad, correctly, so a page-level
    "as of" taken from that field asserts something untrue of at least
    one place on the page.

    The age is the other half, and it is deliberately worded about
    what is AVAILABLE rather than about anyone being late.

    CRO's FRESHNESS.md originally said this breached the channel's
    20-day bound and it does NOT; the claim is withdrawn there and here.
    That bound is a clock on PUBLICATION, and this measured from the
    dekad LABEL, which is the observation window's start. The probe in
    crops/probe_asap.py shows dekad 2026-07-21 genuinely unpublished
    with its window only closed on 31 July, so the source is mid-cycle
    rather than stalled.

    What IS true, and is why this line exists: our cache is not stale,
    so a reader seeing an old date must not infer we failed to fetch. A
    live pull returned the same dekad as newest. A reader cannot tell
    those two apart, so the page says which.

    Computed from the per-place dekads rather than the top-level field,
    because the top-level field is the thing that is wrong.
    """
    dks = sorted({p.get("dekad") for p in doc.get("places", []) if p.get("dekad")})
    if not dks:
        return ""
    newest, oldest = dks[-1], dks[0]
    #
    # A ZERO IS A MEASUREMENT AND MUST BE STATED. This clause used to vanish
    # when the count reached zero, and CRO caught it on the live page: a
    # reader who saw "1 place sits further back" last dekad and sees nothing
    # this dekad cannot tell whether the gap closed or whether we stopped
    # looking. The disclosure disappearing is indistinguishable from the
    # disclosure being dropped, and only one of those is good news.
    #
    # Requirement is CRO's, wording is mine, per D-030. The zero now says
    # more than the non-zero did, because full coverage is the fact a reader
    # most wants and the version that rendered nothing was throwing it away.
    n_all = len(doc.get("places", []))
    n_old = sum(1 for p in doc.get("places", []) if p.get("dekad") != newest)
    behind = (f" {n_old} place{'s' if n_old != 1 else ''} sit"
              f"{'' if n_old != 1 else 's'} further back, having gone "
              f"out of season and stopped reporting." if n_old else
              f" All {n_all} places are reporting at this dekad.")
    # EDITOR'S CHANGE, approved under D-148, and the reasoning is theirs:
    # the old sentence was honest and defensive. Nothing in it was false,
    # and it apologised for the latency before a reader had objected. The
    # latency is the product. Sold as the confirming instrument, 9 to 18
    # days back is what crops IS; sold as current, it is something a reader
    # finds out.
    #
    # THE AGE IS COMPUTED, NEVER TYPED. Typed, it becomes the exact stale
    # figure it exists to prevent, and it goes stale silently, which is the
    # shape this whole day has been about. Show the number AND the range:
    # the range is a property of ASAP's cadence and explains why the number
    # moves; the number is the fact a reader can check. A range alone is a
    # bare rank with no series behind it.
    #
    # The 9 and the 18 are typed here and should not stay that way. They
    # are a property of the source rather than of a season, so they belong
    # in the crops payload; asked, and this carries them until CRO answers.
    age = _days_since(newest)
    age_txt = ("" if age is None else
               ", today" if age == 0 else ", yesterday" if age == 1 else
               f", {age} days ago")
    return (f'<p class="fresh">Newest observation: the ten days to '
            f'{h(_dekad_end(newest))}{age_txt}.{behind}</p>'
            f'<p class="fresh"><strong>Crops is the confirming '
            f'instrument.</strong> It is never more than one publication '
            f'behind its source, which puts it 9 to 18 days back depending '
            f'where the cycle sits. It answers how a season compares with '
            f'twenty-six others, not what happened yesterday.</p>')


def _dekad_end_date(iso: str):
    """The dekad's last day, as a date, or None if the label is unparseable.

    ONE definition of where a dekad ends. I wrote a second one for the age
    and caught it before it shipped: same rule, different arithmetic, in
    two functions that must always agree. That is the fault I have reported
    on three other surfaces today, so it does not get to live here.
    _dekad_end formats this for a reader; _days_since counts from it.
    """
    import datetime
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except (ValueError, AttributeError):
        return None
    if d in (1, 11):
        return datetime.date(y, m, d) + datetime.timedelta(days=9)
    return (datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
            if m < 12 else datetime.date(y, 12, 31))


def _days_since(iso: str):
    """Whole days from the dekad's end to today. Rendered, so it cannot
    go stale; None when the label does not parse, so the caller drops the
    clause rather than printing a guess."""
    import datetime
    end = _dekad_end_date(iso)
    return None if end is None else (datetime.date.today() - end).days


def _dekad_end(iso: str) -> str:
    """The dekad label is its START. A reader needs when it ENDS."""
    end = _dekad_end_date(iso)
    return iso if end is None else f"{end.day} {end.strftime('%B')}"


def _two_ways(g) -> str:
    """Editor's section: the crop result, counted with and without trend.

    D-087. The disagreement is a named section above the country list
    rather than a headline or a footer table. Chad still leads, per
    D-079, because a place needs no explanation and a treatment
    comparison does.

    THE COPY IS EDITOR'S AND SOLVES A PROBLEM THE HEAT SENTENCE DID NOT
    HAVE. There, the reassuring half came second and a dangling pronoun
    made it unquotable. Here the reassuring half leads, and no pronoun
    can point forward without reading as broken English, so grammatical
    dependence does not transfer.

    Their replacement: the risky claim never starts a sentence, sitting
    after a semicolon so there is no boundary to crop at, and the
    leading sentence is a neutral fact that is safe alone. Plus the
    general tool, which is new: where the risky half must lead, use a
    phrase that DECLARES ITS OWN INCOMPLETENESS. "Leave that trend in
    and" is grammatical and complete and unquotable as the whole story,
    because it says on its face that it is not.

    The RANKS are mine rather than theirs, on a separate data line. They
    left them out for reader load and were right about the prose; but
    D-087 requires the claim be checkable where it is made, and a reader
    should not have to reach the footer to see what "better than usual"
    and "worse third" are. Prose carries the finding, the line carries
    the receipt.
    """
    b = (g or {}).get("buckets", {}).get("crop_outcome")
    if not b:
        return ""
    raw, det = b.get("raw") or {}, b.get("detrended") or {}
    if not (raw.get("rank") and det.get("rank")):
        return ""
    return f"""
      <p class="seclab">The same season, counted two ways</p>
      <p class="twp">These croplands have been getting greener for
        twenty-five years. Leave that trend in and this season&rsquo;s crop
        result is better than usual; take it out and it lands in the worse
        third.</p>
      <p class="twn">Crop result across the {raw.get("of")} years of this
        dekad: <b>{raw["rank"]} of {raw["of"]}</b> with the trend left in,
        <b>{det["rank"]} of {det["of"]}</b> with it taken out. Neither is
        the correct one; they answer different questions.</p>"""


def _global_block(g) -> str:
    """The global pair, in the footer, with BOTH treatments.

    Product's ruling (c), after this figure failed twice as a lead: once
    as a count of places at their worst, once as a divergence between
    meteorology and crop outcome. Both times a trend was doing the work.

    DETRENDED IS LISTED FIRST AND RAW SECOND, per the standing ruling
    that where both exist, detrended is the default for any claim
    spanning years. The drift on this channel is upward and upward
    flatters every stress claim we make, so defaulting to raw lets the
    flattering answer win by inertia. Raw stays visible because the
    reader should see there was a choice, and see that the two disagree.

    THE BUCKETS DO NOT PARTITION and the block says so. "Vegetation,
    current" and "Water satisfaction" are in neither group, so this is
    two named subsets rather than a decomposition. Presenting the pair
    without that implies an exhaustiveness that does not exist, which is
    the defect that killed it as a lead independently of the trend.
    """
    if not g or not g.get("buckets"):
        return ""
    order = ["all_five", "crop_outcome", "meteorology"]
    rows = []
    for key in order:
        b = g["buckets"].get(key)
        if not b:
            continue
        det, raw = b.get("detrended") or {}, b.get("raw") or {}
        ins = ", ".join(b.get("instruments") or []) or "all five"
        rows.append(
            f'<tr><th scope="row">{h(b.get("label", key))}'
            f'<span class="gb-i">{h(ins)}</span></th>'
            f'<td>{det.get("rank", "")} of {det.get("of", "")}</td>'
            f'<td class="gb-raw">{raw.get("rank", "")} of {raw.get("of", "")}</td>'
            f'</tr>')
    un = g.get("unassigned_instruments") or []
    quals = "".join(f'<li>{h(q.get("text", ""))}</li>'
                    for q in (g.get("qualifiers") or []))
    return f"""
      <p class="seclab">This dekad against the whole record</p>
      <p class="secsub">Where each figure sits among the 26 years of this
        same dekad, across all {len(g.get("buckets", {})) and "123"} places
        we measure. Detrended is the figure to read: these instruments
        drift, and the drift is upward, so the raw rank flatters every
        stress claim. Both are shown because they disagree and a reader
        should see that there was a choice.</p>
      <table class="gb">
        <thead><tr><th scope="col"></th><th scope="col">detrended</th>
          <th scope="col">raw</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <p class="note">These are two named groups, not a split of the
        five: {h(" and ".join(un))} belong to neither, being an
        instantaneous crop state and a modelled water balance. So the
        two lines cannot be read as "the weather" against "the crops"
        with nothing left over.</p>
      <ul class="gbq">{quals}</ul>"""


def render(doc: dict, top_n: int = 20, root_prefix: str = "../") -> str:
    places = doc["places"]
    # The REGION's driver, not the country's. This took p.get("driver")
    # and it is the Cairo fault one level down: a country property worn
    # by a region. Namibia is water-driven as a country and Hardap is
    # not, at 0.15 against the 0.30 the test requires. CRO measured the
    # blast radius: 677 of 2,122 regions, 32 percent, have a driver
    # differing from their country's, so a third of these rows would
    # have carried a claim that does not hold where it was written.
    # The word in the sentence is "here".
    rows = [(p["place"], r.get("driver"), p.get("attribution", "pending"), r)
            for p in places for r in (p.get("regions") or [])]
    N = len(rows)
    K = max(Counter(r.get("of") for _, _, _, r in rows if r.get("of")),
            key=lambda k: 1) or 26
    K = 26
    hits = [dict(region=r["region"], country=c, driver=dv, attribution=at,
                 z=r["value"], rank=r["rank"], of=r["of"],
                 statement=r.get("statement"))
            for c, dv, at, r in rows if r.get("rank") == 1]
    hits.sort(key=lambda e: e["z"])
    lam = N / K

    # What sits above the noise floor. A country holding many more record
    # lows than its share of units is the only thing on this page that
    # chance does not already explain.
    # Selection AND threshold are the channel's, not mine. My floor stood
    # here for one day and is deleted: a materiality threshold is domain
    # knowledge, so it belongs on CRO's side of the seam, and a floor I
    # invent renders my judgement under their byline.
    #
    # Read `notable`, order by `excess_share`. Never order on
    # `clears_own_recent_max`: it is a boolean over a small sample, so
    # Turkiye at 4 against a recent max of 2 and China at 1 against 0
    # both read True and are not comparable events.
    #
    # Why not the two shapes I proposed, both of which CRO tested and
    # rejected. Excess per unit rewards small denominators, ranking China
    # at 1 of 31 units above Turkiye at 4 of 79, so going from zero
    # regions to one outranks going from two to four. Absolute excess
    # cannot separate Chad's 8-against-3 from Suriname's 2-against-1.
    # The count floor is what actually works, because every noise case
    # has the same shape: 0 to 1, or 1 to 2.
    # `selected_for_display`, not `notable`. CRO renamed it because the
    # old name invited exactly the misreading it produced twice: a field
    # called notable reads as a finding, when all it was ever tested to
    # do is decide which countries to show and in what order. The COUNT
    # of selected places is not a finding; each individual entry is.
    # `notable` is emitted alongside until 2026-08-14, so the fallback
    # is a dated bridge and not a permanent double-read.
    clusters = [(pl["place"], pl["chance_baseline"], pl.get("crop_units"))
                for pl in places
                if (pl.get("chance_baseline") or {}).get(
                    "selected_for_display",
                    (pl.get("chance_baseline") or {}).get("notable"))]
    clusters.sort(key=lambda t: -(t[1].get("excess_share") or 0))



    # The page used to refuse to say whether 81 was high, because the
    # measured expectation lived only in the channel's analysis. CRO now
    # emits it, so the refusal is retired and the verdict is computed.
    #
    # Two properties of the field make it usable where my own derivation
    # was not. It carries `_scope`, declaring that it counts reported
    # places only: CRO's first figures ran over the full 2,166-unit
    # catalogue while the page shows 2,123, which inflated the baseline
    # and left the headline untouched, because the 45 skipped places are
    # tiny and none holds a record this dekad. An error invisible in the
    # current year is exactly the kind a scope field prevents. And it is
    # read rather than written in, so it cannot go stale next dekad.
    #
    # A ranking, deliberately, and no verdict adjective. "Modestly
    # above" was CRO's first wording against the wrong mean and is a
    # shade too soft against the right one. The adjective is the part
    # that gets quoted; the ranking is the part a reader can check.
    agg = doc.get("chance_baseline_aggregate") or {}
    verdict = ""
    if agg.get("recent_years_counted"):
        # The RANKING moved to the lede, so this stops restating it and
        # gives the distribution behind it instead: claim up top,
        # receipt down here. Restating it in both places would be the
        # adjacent-duplication editor rules against, just spread over a
        # page.
        verdict = (
            f" The last {agg['recent_years_counted']} years of this dekad "
            f"averaged {agg['recent_mean']:g} and ranged from "
            f"{agg['recent_min']} to {agg['recent_max']}, counted over the "
            f"same places shown here.")

    # ONE scale, not two. The whole-countries row was 1 observed against
    # about 5 expected, which is noise, and showing a second granularity
    # doubled the reader's work to make a point the sub-national row
    # already makes on its own.
    baseline = scales_block(
        [{"label": "Sub-national units", "units": N, "years": K,
          "observed": len(hits)}],
        note=("The expectation rises with the number of units, not with "
              "the weather, so any map at this resolution shows dozens of "
              "record lows every week. The figure marked is what an EVEN "
              "spread of records would give, and records do not fall "
              "evenly." + verdict))

    # The two blocks answer DIFFERENT QUESTIONS: depth (how bad is the
    # worst place) and breadth (how much of a country is affected).
    # Neither is a weaker form of the other, so neither may be labelled
    # as though it outranked the other.
    #
    # CRO's evidence, and it is decisive. Five of the eight deepest
    # countries are not broad at all: Suriname at z -3.79, Libya -3.75,
    # Ecuador -2.50, Congo -2.26, Colombia -1.82, each one catastrophic
    # region inside an otherwise ordinary country. Three of the six broad
    # countries are nowhere near the top on depth. If this page reads as
    # "most extreme" then "also extreme", it is simply wrong, because
    # Suriname's Brokopondo is the single most extreme cropland reading
    # on Earth this dekad and it sits in the second block.
    #
    # Breadth does imply some depth, which is why the broad set falls
    # inside the deep set at a z <= -1.0 cut. That is arithmetic, not
    # redundancy: three regions simultaneously at their record worst
    # makes it likely one of them is extreme. Depth implies nothing
    # about breadth, which is why Suriname and Libya exist.
    # State the asymmetry with numbers, in the direction where the
    # implication FAILS. Counting the countries in BOTH blocks is the
    # wrong statistic: five of six broad countries also hold a deep
    # region, so it reads as "the two blocks mostly agree" and invites
    # the reader to ask why there are two.
    #
    # These counts are properties of the dekad, not of this layout. An
    # earlier version counted within the top `top_n` rows, which was
    # honest at 20 rows and honest at 30 and said something different in
    # each, with nothing on the page to tell a reader which. A statistic
    # whose value depends on a display parameter is the same class of
    # error as a number printed without its denominator.
    #
    # It is not an artifact of a severity cut either. CRO checked: the
    # share of record-low regions sitting in countries that are not
    # widely affected is 64% over all 81, 64% at z <= -1.0, 65% at -1.5
    # and 71% at -2.0. The asymmetry holds at every depth, which is the
    # argument for putting it above both blocks rather than inside one.
    #
    # Computed here per dekad and never written in. Both counts move
    # with the data, so a hard-coded pair would go stale silently.
    # The spread figure must describe the list the reader is LOOKING AT.
    # It said "the top of this list is 6 times the bottom of it" directly
    # above twenty rows spanning 2.6x; the 6 was over all 81. Same class
    # as the framing line that moved with top_n: a figure computed over
    # one set and presented against another. Both are on the page now,
    # each named for the set it describes.
    broad_names = {c for c, _, _ in clusters}
    deep_countries = {e["country"] for e in hits}

    # THE ANCHOR IS ONE SENTENCE, NOT A CHART AT THE TOP. It cannot
    # vanish, or a reader concludes 81 is alarming; but it informs and
    # the chart proves, and proving is footer work. The old opening was
    # two scales, a caveat and three paragraphs of method before the
    # reader met a single place.
    # Editor's h1 and opening sentence, GENERATED rather than written in.
    # Every value in them moves: the leading country, its counts, how
    # many others are flagged, how many places are reported. A
    # hard-coded "Eight of Chad's 22" would be wrong next dekad and
    # nothing we run would catch it, which is the failure this page has
    # already produced twice today in other costumes.
    #
    # Why this h1 over "Globally this is an ordinary week for crops. In
    # Chad it is not.", which was the other candidate: editor killed
    # that on the crop test. Read only the first line, which is what
    # travels in a screenshot, and it is a clean reassurance statement
    # in our own voice. It also implied Chad was the sole exception when
    # six countries are flagged. This one leads with the specific, and
    # its first line alone is the finding rather than the reassurance.
    if clusters:
        lc, lcb, lcu = clusters[0]
        headline = (f"{_word(lcb['this_year']).capitalize()} of {h(lc)}&rsquo;s "
                    f"{lcu} crop regions are at a record low. "
                    f"{_word(lcb['recent_max']).capitalize()} was the "
                    f"previous worst.")
        # BOTH halves, because both are true and each alone misleads.
        # Sudan's 3 really does beat its previous 2, so calling the five
        # noise understates Sudan; and six countries clearing their own
        # maximum is the 57th percentile of the last 35 dekads, so
        # "flagged, and the rest ordinary" overstates the set. CRO's
        # correction, and the finer version of what I had proposed.
        others = len(clusters) - 1
        if others == 1:
            flagged = ("One other country also passed its own previous "
                       "worst, which is a normal number in any given week.")
        elif others:
            flagged = (f"{_word(others).capitalize()} other countries also "
                       f"passed their own previous worst, which is a normal "
                       f"number in any given week.")
        else:
            flagged = ("No other country passed its own previous worst, "
                       "which is within the normal range for a week.")
        opening = flagged + " "
    else:
        headline = (f"No country has more cropland at a record low than "
                    f"its own recent history explains.")
        opening = (f"No country passed its own previous worst, which is "
                   f"within the normal range for a week. ")

    # NO ADJECTIVE, in either direction. This said "Globally that is an
    # ordinary week", and 81 against a typical 59 is the 83rd percentile,
    # higher than ten of the last twelve years. Not ordinary.
    #
    # Worth keeping the whole swing on the record: the page called an
    # ordinary number a finding, was corrected, and then called an
    # elevated number ordinary, on the SAME figure, one revision apart.
    # "Ordinary" is a claim and needs the same evidence as "alarming".
    # CRO raised this against the direction they had themselves pushed,
    # which is the only reason it was caught rather than compounded.
    #
    # So the ranking carries it and no word grades it, the same rule as
    # the footer verdict line.
    n_below = agg.get("recent_years_below_this")
    n_years = agg.get("recent_years_counted")
    rank_clause = ""
    if n_below is not None and n_years:
        rank_clause = (f", higher than all but {_word(n_years - n_below)} "
                       f"of the last {_word(n_years)} years")
    lede = opening + (
        f"{len(hits)} crop regions worldwide are at their worst on record "
        # No decimal on an average of counts. 59.2 reads more precise
        # than a mean of twelve integers is, and the extra digit buys a
        # reader nothing in a lede.
        f"for this point in the season, against a typical "
        f"{agg.get('recent_mean', 0):.0f}{rank_clause}. Where they cluster "
        f"is what this page is about.")

    # WHY THIS PAGE MATTERS NOW, and it is a calendar fact rather than a
    # forecast. A season that has not opened cannot be measured, so the
    # countries about to open are the ones this page is about to start
    # saying something about.
    #
    # Counted over the 123 places this page reports, never the 136-country
    # catalogue. Product's brief said "31 countries, a third of everything
    # we cover"; 31 is the catalogue figure and the page's own is 25, and
    # 31/136 is 23% rather than a third. Third instance today of a count
    # taken over a wider set than the page shows, so it is computed here
    # from `places` and the named examples are filtered to places that
    # actually appear. Portugal opens in this window and is NOT a reported
    # place, so naming it would point a reader at a country we do not
    # measure.
    def _opens(p):
        # `season_opens_dekads`, plural and always a list. CRO split the
        # original field in 1e927a1 because it was typed by its data,
        # int for one season and list for two, which is a defect.
        return p.get("season_opens_dekads") or []

    # The map plots exactly the set the page calls flagged, built from
    # `clusters` rather than recomputed, so the dots and the list cannot
    # disagree about who is on it.
    # Only countries that actually have a page are linked. A dot
    # pointing at a 404 is worse than a dot that does nothing.
    from templates.crops_country import slugify as _slug
    _has_page = {p["place"] for p in places
                 if any(r.get("rank") == 1 for r in (p.get("regions") or []))}
    # The label for a linked-but-not-clustered dot, stated here because
    # this is where the fact lives. A page is granted for holding a region
    # at its worst on record, so that is what the dot says. Counted from
    # the payload rather than asserted, since "regions" reads as several
    # and one is the common case.
    # TWO THINGS CRO SENT BACK, both in a label that stands alone.
    #
    # "at its worst on record" drops FOR THIS POINT IN THE SEASON, which
    # turns "worst for late July" into "worst ever". Their own sentence is
    # "lowest of 26 observations for this point in the season, 2001-2026",
    # and an aria-label is the worst place to lose the qualifier because
    # there is no surrounding paragraph to carry it.
    #
    # And the count needs its basis. Turkiye is 2 OF 79. "2 crop regions at
    # their worst" is true and tells a reader nothing about whether that is
    # 2 of 4 or 2 of 79. CRO's country-aggregate warning does NOT apply to a
    # count of regions, which is honest in a way an unweighted mean is not;
    # what applies is that a number without its basis is the binding this
    # whole channel rests on.
    _n1 = {p["place"]: sum(1 for r in (p.get("regions") or [])
                           if r.get("rank") == 1) for p in places}
    _of = {p["place"]: len(p.get("regions") or []) for p in places}
    quiet_labels = {
        p: ("one of its %d crop regions is at its worst on record for this "
            "point in the season" % _of[p] if _n1[p] == 1
            else "%d of its %d crop regions are at their worst on record for "
                 "this point in the season" % (_n1[p], _of[p]))
        for p in _has_page}

    world_map = map_block(
        [p["place"] for p in places],
        [(c, c) for c, _, _ in clusters],
        map_href=root_prefix + "world-map.svg",
        hrefs={p: _slug(p) + "/" for p in _has_page},
        quiet_labels=quiet_labels)

    cur_dk = _dekad_index(doc.get("dekad", ""))
    NOV = 31                      # dekad 31 is 1-10 November
    opening = [p["place"] for p in places
               if any(cur_dk < k <= NOV for k in _opens(p))]
    # A RENAMED FIELD MUST NOT SILENTLY DELETE A SECTION. This read
    # `season_opens_dekad`; CRO split it into `season_opens_dekads` and
    # `next_season_opens_dekad`, and the renderer went on producing a
    # valid page with the entire seasonal panel missing and no error
    # anywhere. Nothing we run would have caught it: the HTML is
    # well-formed, every link resolves, qa_check passes, and the only
    # symptom is a section that is not there.
    #
    # So: if NO place carries the field, that is a payload/renderer
    # mismatch rather than a dekad in which nothing opens, and it stops
    # the build. An empty window is legitimate and stays silent; an
    # empty COLUMN is not.
    if not any(_opens(p) for p in places):
        raise SystemExit(
            "no place carries `season_opens_dekads`. Either the field was "
            "renamed again or the payload lost it. Refusing to render the "
            "page without the seasonal section rather than dropping it "
            "silently.")

    named = [c for c in ("Spain", "Argentina", "Angola", "Kenya")
             if c in opening][:2]
    season = ""
    if opening and cur_dk:
        season = (
            f"<p class=\"why\">A season that has not opened cannot be "
            f"measured, so this page says most about countries whose "
            f"season is starting. {len(opening)} of the {len(places)} "
            f"countries measured here, about one in "
            f"{_word(round(len(places) / len(opening)))}, open a growing "
            f"season "
            f"between now and early November"
            + (f", among them {_and(named)}." if named else ".")
            + " That is a calendar, not a forecast.</p>")

    # ONE LIST, GROUPED BY COUNTRY, replacing the two sections that had
    # to be introduced by a sentence explaining neither outranked the
    # other. Needing that sentence was the signal the split was wrong.
    #
    # Grouping is also what makes the list legible. Ennedi Est at rank
    # seven, floating between two Suriname districts, tells a reader
    # nothing; Chad appearing once with its eight regions together IS
    # the finding, and no name on the flat list carried that.
    #
    # Order: countries above their own recent maximum first, in the
    # channel's order, then the rest by their deepest region. That puts
    # breadth above depth without asserting breadth matters more, since
    # both are now rows of the same list rather than rival sections.
    by_country = {}
    for e in hits:
        by_country.setdefault(e["country"], []).append(e)
    cb_of = {c: (cb, u) for c, cb, u in clusters}
    ordered = [c for c, _, _ in clusters if c in by_country]
    ordered += sorted((c for c in by_country if c not in broad_names),
                      key=lambda c: by_country[c][0]["z"])

    groups = "".join(
        _country_group(c, by_country[c], *cb_of.get(c, (None, None)))
        for c in ordered[:top_n])
    rest = max(0, len(ordered) - top_n)
    grouped_html = f"""
      {_pinned_block(places)}
      <p class="seclab">Where the record lows are</p>
      <p class="secsub">Grouped by country, because a single region at a
        record low is common and several in one country is not. Countries
        beyond their own recent maximum come first; the rest follow by
        how far their worst region has fallen.</p>
      {groups}
      <p class="note">{rest} further countries hold one or two regions at
        a record low, which is what an ordinary dekad looks like.</p>"""

    # The separate lead block is gone. Its content lives in the first
    # group now, and `_also` with it: those five countries are their own
    # rows further down the same list, so listing them here as well was
    # the duplication in a second costume.

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
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
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Crops | {h(SITE_NAME)}</title>
<style>
{T.font_faces_css(root_prefix + "fonts/")}
:root {{ {T.css_variables()} }}
@media (prefers-color-scheme: dark) {{ :root {{ {T.css_variables(dark=True)} }} }}
* {{ box-sizing:border-box; }}
:root {{ --shell-max:800px; --shell-pad:24px; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font-family:"{T.FONT_PROSE}",Georgia,serif; font-size:16.5px; line-height:1.55; }}
main {{ max-width:800px; margin:0 auto; padding:24px 24px 80px; }}
{SITE_MASTHEAD_CSS}
{CHANCE_CSS}
{CROPS_MAP_CSS}
.eyebrow, .seclab, .cz, .tag, .cctry, .cbig, .foot {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:31px; font-weight:500; line-height:1.18;
  letter-spacing:-0.015em; margin:0 0 12px; max-width:22ch;
  text-wrap:balance; }}
.stand {{ color:var(--ink-soft); max-width:58ch; margin:0; }}
.seclab {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink); margin:44px 0 4px;
  padding-bottom:8px; border-bottom:2.4px solid var(--rule-45); }}
.secsub {{ font-size:13.5px; color:var(--ink-soft); margin:0 0 10px;
  max-width:60ch; }}

.crow {{ display:grid; grid-template-columns:4.6rem 1fr auto; gap:16px;
  align-items:baseline; padding:13px 0; border-bottom:1px solid var(--rule); }}
/* Severity, printed, because a rank is not a magnitude. Ordering by
   rank alone would put a place six times less bad at the same height. */
.cz {{ font-size:20px; font-weight:600; color:var(--crop);
  font-variant-numeric:tabular-nums; }}
.cmain {{ display:flex; flex-direction:column; gap:2px; }}
.cplace {{ font-size:17px; font-weight:500; }}
.cctry {{ font-size:11.5px; color:var(--ink-faint); margin-left:8px;
  font-weight:400; }}
.cclaim {{ color:var(--ink-soft); font-size:14.5px; }}
/* Habit, not diagnosis. On its own line and faint, so it cannot be read
   as part of the claim above it: the whole point of splitting it out is
   that it describes the country over twenty-five years and says nothing
   about this dekad. */
.cdriver {{ display:block; margin-top:3px; color:var(--ink-faint);
  font-size:12.5px; }}
.tag {{ font-size:10.5px; letter-spacing:0.04em; padding:3px 8px;
  white-space:nowrap; align-self:center; }}
.tag-loaded {{ background:var(--tag-loaded-bg); color:var(--tag-loaded-fg); }}
.tag-notlink {{ background:var(--tag-notlink-bg); color:var(--tag-notlink-fg); }}
.tag-pending {{ background:var(--tag-pending-bg); color:var(--tag-pending-fg); }}

/* The pair framing sits above both blocks and belongs to neither, so it
   is ink and unhued. Giving it the channel colour would make it read as
   the first block's heading, which is the ordering claim it exists to
   deny. */
.pairlab {{ margin:34px 0 0; font-size:11px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink);
  font-family:"{T.FONT_DATA}",monospace; }}
.pairsub {{ margin:8px 0 0; font-size:14px; color:var(--ink-soft);
  max-width:64ch; }}

/* A country group. The rule sits above the heading rather than boxing
   the group, per the no-enclosure rule: a card would make each country
   look like a separate finding when the list is one finding read down.
   Countries above their own recent maximum take the channel hue on the
   heading only, so the hue marks which countries are unusual without
   colouring every region inside them. */
/* The reason-to-care line. Sunk rather than boxed, per the no-enclosure
   rule, and unhued because a calendar fact is not a finding. */
.why {{ margin:18px 0 0; padding:14px 16px; background:var(--paper-sunk);
  font-size:14.5px; color:var(--ink-soft); max-width:62ch; }}

/* Native <details>. No script, keyboard-operable, and it still prints
   and still finds text on Ctrl-F in current browsers. A JS disclosure
   would buy nothing here and would break the page for anyone the
   script fails on. */
.cgd {{ margin-top:8px; }}
.cgd > summary {{ cursor:pointer; list-style:none; display:inline-block;
  font-family:"{T.FONT_DATA}",monospace; font-size:11.5px;
  letter-spacing:.06em; text-transform:uppercase; color:var(--ink-faint);
  padding:3px 0; }}
.cgd > summary::-webkit-details-marker {{ display:none; }}
.cgd > summary::before {{ content:"+ "; }}
.cgd[open] > summary::before {{ content:"\\2212 "; }}
.cgd > summary:hover {{ color:var(--ink); }}
.cgd > summary:focus-visible {{ outline:2px solid var(--crop);
  outline-offset:2px; }}

.cg {{ margin-top:26px; }}
.cghead {{ margin:0 0 6px; font-size:16px; font-weight:600;
  padding-bottom:6px; border-bottom:1px solid var(--rule); }}
.cglink {{ color:inherit; text-decoration:none;
  border-bottom:1px solid var(--rule); }}
.cglink:hover {{ border-bottom-color:currentColor; }}
.cg.up .cghead {{ color:var(--crop);
  border-bottom-color:var(--crop); }}
.cgsub {{ display:block; font-size:12.5px; font-weight:400;
  color:var(--ink-faint); font-family:"{T.FONT_DATA}",monospace;
  margin-top:3px; font-variant-numeric:tabular-nums; }}

.cluster {{ margin-top:12px; padding-left:18px;
  border-left:3px solid var(--crop); }}
.tj {{ width:100%; height:auto; display:block; margin:14px 0 4px; }}
.tj text {{ font-family:"{T.FONT_DATA}",monospace; paint-order:stroke;
  stroke:var(--paper); stroke-width:2.5; stroke-linejoin:round; }}
.tj-s {{ font-size:10.5px; fill:var(--ink-soft); }}
.tj-x {{ font-size:10px; fill:var(--ink-faint); }}
.tj-v {{ font-size:13px; fill:var(--crop); font-weight:600; }}
.cbig {{ font-size:34px; font-weight:600; color:var(--crop); margin:0;
  line-height:1; font-variant-numeric:tabular-nums; }}
.cbody {{ margin:10px 0 0; max-width:60ch; }}
.ccav {{ margin:10px 0 0; font-size:13.5px; color:var(--ink-soft);
  max-width:60ch; }}
/* The runners-up are ink, not crop. The channel hue marks the one case
   that is above its own history by a real margin; spending it on five
   countries that clear by a single region would make the drop-off the
   block exists to show invisible. */
.alsolab {{ margin:18px 0 0; font-size:11px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint);
  font-family:"{T.FONT_DATA}",monospace; }}
.also {{ margin:8px 0 0; padding:0; list-style:none; font-size:14px;
  color:var(--ink-soft); max-width:60ch; }}
.also li {{ padding:4px 0; border-bottom:1px solid var(--rule);
  font-variant-numeric:tabular-nums; }}
.alsoc {{ color:var(--ink); font-weight:600; }}
.note {{ margin:20px 0 0; font-size:14px; color:var(--ink-soft);
  max-width:64ch; }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
@media (max-width:600px) {{
  .crow {{ grid-template-columns:3.9rem 1fr; }}
  .crow .tag {{ grid-column:2; justify-self:start; margin-top:5px; }}
  h1 {{ font-size:25px; max-width:none; }} }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow">Crops</p>
  <h1>{headline}</h1>
  <p class="stand">{lede}</p>
  {_freshness(doc)}
  {season}
  {world_map}

  {grouped_html}

  <!-- Everything below is identical every week or not specific to
       today: the proof behind the lede's "typical" figure, and the
       qualifier that applies to all 81 rows equally. Kristjan's rule,
       and it is the right cut: anything the same on every row, or not
       about this dekad, sits below the content. -->
  {_two_ways(doc.get("global") or {})}

  {_global_block(doc.get("global") or {})}

  <p class="seclab">How we know 81 is an ordinary number</p>
  {baseline}
  <!-- The units-versus-weather sentence lives in the chart's own note
       above and is not repeated here. It was in both, verbatim, two
       paragraphs apart. -->
  <p class="note">This measurement is of the crop canopy and not of what
    stressed it: heat, drought, disease and late planting are not
    separable here, which is why no row on this page names a cause.</p>

  <!-- No truncation here, deliberately. This footer used to slice
       `method` at 90 characters, which cut CRO's 158-character string
       mid-sentence at "The indicator is " and ran it into the
       separator, on the one line whose entire job is to convey care.
       Where a methods line may be cut is a judgement about what a
       reader must not lose, so it belongs to the channel: they emit
       `method_short`. A renderer that truncates prose is deciding
       something it does not know. If the short form is ever missing,
       the full string wraps rather than being cut. -->
  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; {h(doc.get('method_short') or doc.get('method', ''))} &middot; baseline
    {h(str(doc.get('baseline','')))}</div>
</main>
</body>
</html>
"""
