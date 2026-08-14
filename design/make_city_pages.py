"""Every heat city page from one template.

Every page is a landing page: Kristjan's framing is that these get linked
in promotion and a reader arrives caring about their own city. So the
URL and the claim have to stand alone.

NO CITY LIST OR COUNT IS WRITTEN DOWN HERE. It was, three times, and it
went stale within a day each time as heat added cities: 21, then 22 with
Amsterdam, then 24 with Stockholm and Prague. Everything below is a flag
read per city at build time.

THE BRANCHES, each read from a payload field, none inferred:

  nights_metric_gated     Under two hot nights a year, so no ratio,
                          multiple or record may be quoted on nights.
  multiple_available      False where the 1961-1990 window is too short
                          to compare against. See below, because this is
                          the one that bit.
  peak IS a record        Where the hottest day of 2026 is also the
                          hottest on record, so "its hottest day was
                          still not a record" is FALSE and must not be
                          templated. Computed from the series, not a
                          flag, because it is a property of the chart
                          this file draws.

THE ABSENCE OF A FIELD IS NOT A PROHIBITION. This file believed for a
fortnight that heat omitting the day multiple was enough to stop the page
publishing one. It is not: an absent field cannot be printed, but it can
be RECOMPUTED, and this file recomputed it. Murcia's headline read "used
to get 2 hot days by this point. This year: 14" off a 1961-1990 window
holding 6 of 30 years, with a note underneath saying no multiple was
published. Bind to multiple_available, which says you may not.

A COUNT AND A PEAK ARE DIFFERENT CLAIMS AND NEITHER BORROWS THE OTHER'S
RANK. Nice has the most hot days on record and its twentieth hottest
single day. Both true; either sentence alone misleads.

A COUNT AND A PEAK ARE DIFFERENT CLAIMS AND NEITHER BORROWS THE OTHER'S
RANK. Paris is 1st of 77 on the count of hot days and 2nd on its hottest
single day. Both true; "the hottest Paris has ever been" is false.

Every figure is counted TO THE SAME CALENDAR DAY each year, so a
part-finished 2026 is never set against complete seasons. The payload's
b6190 is a WHOLE-YEAR mean and is deliberately unused: pairing it with a
part-season count understates the change and misdescribes the basis.
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
                       SITE_MASTHEAD_CSS, SITE_NAME, site_masthead)
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())["cities"]
C = N["cities"]
NO_MULT = set(N["cities_without_day_multiple"])
from design import copydeck  # noqa: E402
from templates.subscribe_band import band as _band, css as _bandcss
_SUB_BAND = _band()

CORRECTIONS = copydeck.load("heat_corrections")
MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]
slug = lambda n: n.lower().replace(" ", "-")


def series(yrs, key, sub=None):
    out = []
    for y, x in sorted(yrs.items(), key=lambda kv: int(kv[0])):
        if not x.get("usable_to_cut"):
            continue
        raw = x.get(key)
        v = raw.get(sub) if (sub and isinstance(raw, dict)) else raw
        if v is not None:
            out.append((int(y), v))
    return out


def bars(data, top, w=880, h=104, accent_last=True):
    if not data:
        return ""
    bw = w / len(data)
    out = []
    for i, (y, v) in enumerate(data):
        if not v:
            continue
        cur = accent_last and y == 2026
        out.append(f'<rect x="{i*bw:.1f}" y="{h-v/top*h:.1f}" width="{bw-1.2:.1f}" '
                   f'height="{v/top*h:.1f}" '
                   f'fill="{"var(--accent)" if cur else "var(--hist)"}"/>')
        if cur:
            # A SHAPE as well as a hue. Accent against ink is 1.86:1, so in
            # greyscale, in print, on a dim screen or with reduced colour
            # vision the one mark the chart exists to identify reads as one
            # more dark bar. The rule makes colour confirm rather than carry.
            out.append(f'<line x1="{i*bw + (bw-1.2)/2:.1f}" y1="0" '
                       f'x2="{i*bw + (bw-1.2)/2:.1f}" y2="{h:.1f}" '
                       f'stroke="var(--accent)" stroke-width="1"/>')
    # The fixed ticks are dropped when they collide with the record's own
    # first year. Lyon starts in 1975 and printed "1975" and "1976" on top of
    # each other; so would any station starting within a few years of 2000.
    _first = data[0][0]
    _want = [_first] + [y for y in (1976, 2000, 2026) if abs(y - _first) > 6]
    ticks = "".join(
        f'<text x="{i*bw:.1f}" y="{h+13}" class="ax" '
        f'text-anchor="{"end" if y == 2026 else "start"}">{y}</text>'
        for i, (y, _) in enumerate(data) if y in _want)
    # A Y AXIS, because the chart could not be read for magnitude. Kristjan:
    # it shows the shape of a record and not how many. Every bar was a
    # fraction of a maximum the reader was never told.
    #
    # Three lines rather than a full scale: the top, the middle and zero.
    # Two would leave a reader interpolating and a full set of gridlines
    # would compete with the bars, which are the subject. The middle tick is
    # dropped when the maximum is small enough that halving it lands between
    # whole days, since a chart of counts should not offer 3.5 of anything.
    # The middle tick is placed at its TRUE height for a rounded value, not
    # at half the pixel height for half the value. My first version only drew
    # it when the maximum was even, which is why Lugano at 41 and Paris at 37
    # had no middle tick at all: most maxima are odd.
    _gy = [(0, top), (h, 0)]
    if top >= 8:
        _mid = round(top / 2)
        if 0 < _mid < top:
            _gy.insert(1, (h - _mid / top * h, _mid))
    grid = []
    for gy, gv in _gy:
        dash = "" if gv == 0 else ' stroke-dasharray="2 4"'
        grid.append(f'<line x1="0" y1="{gy:.1f}" x2="{w}" y2="{gy:.1f}" '
                    f'stroke="var(--rule)" stroke-width="1"{dash}/>')
        grid.append(f'<text x="{w + 6}" y="{gy + (9 if gv == top else 3):.1f}" '
                    f'class="ax">{gv}</text>')
    grid = "".join(grid)
    # The axis sits in its own gutter so the bars keep the full plot width
    # and the three charts stay the same width as each other.
    # PROPORTIONAL, not stretched. Kristjan saw the axis numbers as a
    # different typeface from the label beside them. They are the same face
    # at nearly the same size: the SVG was scaling 0.47 horizontally against
    # 1.0 vertically, so every glyph inside it was condensed to under half
    # width while the HTML label next to it was untouched.
    #
    # Rectangles do not care and text does, which is why this went unnoticed
    # until an axis put numbers inside the plot. All three charts share one
    # viewBox width now, so they still render at identical heights to each
    # other, which is the property the stack needs. What changes is that the
    # height follows the width instead of being pinned.
    return (f'<svg viewBox="0 0 {w + 34} {h+18}" width="100%" '
            f'style="height:auto">{grid}{"".join(out)}{ticks}</svg>')


def line(data, w=880, h=104, mark_year=None, ring_year=None,
         mark_val=None, ring_val=None):
    """The two marked points carry their temperature.

    Kristjan's change. This is the only chart on the page whose y axis is a
    quantity rather than a count, and it had no axis at all, so a reader
    could see that 2026 sat below the 2019 peak and not by how much. The
    figures were in the caption underneath, which made the drawing depend on
    prose to be read.

    TWO THINGS THE FIRST VERSION GOT WRONG, both only visible in a browser.
    The previous best is usually the highest point on the chart, so a label
    placed above it fell outside the viewBox and did not render at all: hence
    PAD, which is headroom rather than plot area. And the SVG scaled
    non-uniformly to fit its column, which stretches rectangles harmlessly
    and text visibly, so this chart now scales proportionally while the bar
    charts keep the old behaviour.
    """
    PAD = 20
    lo = min(v for _, v in data) - .5
    hi = max(v for _, v in data) + .5
    px = lambda y: (y - data[0][0]) / (data[-1][0] - data[0][0]) * w
    py = lambda v: PAD + (h - PAD) - (v - lo) / (hi - lo) * (h - PAD)
    pts = " ".join(f"{px(y):.1f},{py(v):.1f}" for y, v in data)
    extra = ""
    d = dict(data)
    if ring_year and ring_year in d:
        # NOT a hollow ring. Hollow is the null convention, and this is the
        # one historical value the caption compares against, so it has to be
        # the second strongest mark rather than the faintest.
        extra += (f'<circle cx="{px(ring_year):.1f}" cy="{py(d[ring_year]):.1f}" '
                  f'r="3.4" fill="var(--ink)"/>'
                  f'<line x1="{px(ring_year):.1f}" y1="{py(d[ring_year]):.1f}" '
                  f'x2="{px(ring_year):.1f}" y2="{h:.1f}" stroke="var(--ink)" '
                  f'stroke-width="1" opacity="0.45"/>')
    if mark_year and mark_year in d:
        extra += (f'<circle cx="{px(mark_year):.1f}" cy="{py(d[mark_year]):.1f}" '
                  f'r="3.6" fill="var(--accent)"/>')
    # Labels last, so they sit over the line. Both read leftwards from their
    # own dot: 2026 is at the right edge and would otherwise overflow, and
    # the previous best is usually just left of it, so anchoring both the
    # same way keeps them from stacking on the same few pixels.
    if mark_year and mark_val is not None and mark_year in d:
        extra += (f'<text x="{px(mark_year) - 6:.1f}" y="{py(d[mark_year]) + 4:.1f}" '
                  f'class="vlab va" text-anchor="end">{mark_val}&#8202;&deg;C</text>')
    if ring_year and ring_val is not None and ring_year in d:
        extra += (f'<text x="{px(ring_year) - 6:.1f}" y="{py(d[ring_year]) - 7:.1f}" '
                  f'class="vlab" text-anchor="end">{ring_val}&#8202;&deg;C</text>')
    # SAME BOX AS THE BAR CHARTS, h+18 tall and fixed in pixels, because the
    # three only compare if they are the same height at every viewport. Left
    # to scale proportionally this one rendered two thirds as tall as the
    # others and the stack stopped reading as a stack.
    #
    # That puts preserveAspectRatio back to none, so text squashes to about
    # 84 per cent horizontally at the page's full width. The bar charts'
    # axis ticks have always done exactly that; matching the box means the
    # vertical scale is 1 on all three, so nothing is distorted differently
    # from anything else on the page.
    # The same 34-unit gutter as the bar charts, carrying this chart's own
    # axis: it is the only one whose height is a temperature rather than a
    # count, so the top and bottom of its range are the numbers a reader
    # needs to place any point on it.
    axis = (f'<line x1="0" y1="{PAD:.1f}" x2="{w}" y2="{PAD:.1f}" '
            f'stroke="var(--rule)" stroke-width="1" stroke-dasharray="2 4"/>'
            f'<text x="{w + 6}" y="{PAD + 9:.1f}" class="ax">{hi - .5:.0f}</text>'
            f'<line x1="0" y1="{h:.1f}" x2="{w}" y2="{h:.1f}" '
            f'stroke="var(--rule)" stroke-width="1"/>'
            f'<text x="{w + 6}" y="{h + 3:.1f}" class="ax">{lo + .5:.0f}</text>')
    return (f'<svg viewBox="0 0 {w + 34} {h+18}" width="100%" '
            f'style="height:auto" role="img">{axis}'
            f'<polyline points="{pts}" fill="none" stroke="var(--soft)" '
            f'stroke-width="1.2"/>{extra}</svg>')


def units(k, accent=False):
    cls = "u ua" if accent else "u"
    return "".join(f'<span class="{cls}"></span>' for _ in range(int(round(k))))


def words_n(n):
    """Small counts read better as words in prose. Only used where the number
    is one to twelve, which is every case the night baselines produce."""
    w = ["no nights", "one night", "two nights", "three nights", "four nights",
         "five nights", "six nights", "seven nights", "eight nights",
         "nine nights", "ten nights", "eleven nights", "twelve nights"]
    return w[n] if 0 <= n < len(w) else f"{n} nights"


def ordn(n):
    """11th, 12th, 13th are the cases a naive last-digit rule gets wrong, and
    ranks in the teens are common here. Two spellings existed before this:
    an inline dict that stopped at 3rd, and a bare "th" that shipped
    "2th of 87" on Barcelona and Cologne and "3th of 106" on Madrid."""
    n = int(n)
    suf = "th" if n % 100 in (11, 12, 13) else \
        {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def text_of(html):
    """Rendered words only.

    Two ways to get this wrong and both have bitten. Greping raw HTML finds
    nothing when a phrase is split across tags and reports that as proof of
    absence. And stripping tags WITHOUT first removing style and script
    leaves the whole stylesheet in the string, so a guard can match CSS, or
    quote it back in an error, or clear a banned word that is only present
    in a comment. I fixed that on the index and never carried it here.
    """
    body = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    # aria-label, alt and title survive the tag strip on purpose. They are
    # not decoration: they are what a screen reader user gets INSTEAD of the
    # graphic, so a claim published only there is published to a reader who
    # has no other route to it. Every guard built on text_of was checking
    # the sighted page and calling it the page.
    spoken = " ".join(m.group(1) for m in re.finditer(
        r'(?:aria-label|alt|title)="([^"]*)"', body, re.I))
    return re.sub(r"\s+", " ",
                  re.sub(r"<[^>]+>", " ", body) + " " + spoken).strip()


# D-112: a count over this city set may never be published in a form that
# reads as a fact about Europe, because the cities were chosen for where the
# heat was. Every city page footer said "36 European cities are measured
# this way" until this guard was written; the count is ours, the continent
# is not. Shared with make_heat_index.py by duplication rather than import,
# which is the wrong trade if a third surface ever needs it.
_NUM = (r"(?:\d[\d,]*|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|"
        r"ninety|ten|eleven|twelve|(?:thir|four|fif|six|seven|eigh|nine)"
        r"teen)(?:-\w+)?)")
_EUROPE = re.compile(
    rf"(?<!these )\b{_NUM}\s+(?:of\s+(?:the\s+)?{_NUM}\s+)?"
    rf"European\s+(?:\w+\s+)?"
    rf"(?:cities|capitals|countries|stations|towns)\b", re.I)


def _provisional_block(v):
    from html import escape as _esc
    """A season whose licence is unresolved says so, on the page.

    London is the only city whose history and current season arrive by
    different transports. Both are the same thermometer at Heathrow and
    heat validated every day of 2024 and 2025 to within 0.5 C, so the
    NUMBERS are sound. What is unresolved is the LICENCE: the Met Office
    has been asked whether we may republish the season and has not yet
    answered.

    The payload already carried this inside source.licence and no page
    rendered that field, so the notice existed and reached no reader.
    Heat said it was not optional and they are right: a figure whose
    right to be published is unsettled is a different thing from one
    that is, and only we can see the difference.

    Attribution is Met Office, never OGIMET. OGIMET is the transport for
    a one-time archival pull, not the source of the observations, and
    showing a transport as a source would credit the wrong body.
    """
    lic = ((v.get("source") or {}).get("licence") or "")
    if "PROVISIONAL" not in lic.upper():
        return ""
    _, _, tail = lic.partition("PROVISIONAL")
    return ('<span style="grid-column:1/-1"><strong>The 2026 season is '
            'provisional.</strong>' + _esc(tail.lstrip(":").rstrip(".")) +
            '. The history is Met Office MIDAS Open under the Open '
            'Government Licence, which is unambiguously ours to '
            'republish.</span>')


def _provisional_mark(v):
    """The provisional mark, ADJACENT TO THE FIGURE rather than at the foot.

    I put it in the source block first and product's instruction is that
    this is not enough, for a reason worth keeping: the page ships now
    BECAUSE people will look during a heatwave, and a page that gets
    looked at gets screenshotted. A screenshot does not get pulled. If the
    number can be lifted without the caveat, the caveat is not doing its
    job.

    Floods learned the same thing today about `cannot_say` travelling as
    "nothing happened", and heat learned it about the counts being floors.
    Three channels, one lesson: a qualifier that is not attached to the
    figure is a qualifier that will be separated from it.
    """
    lic = ((v.get("source") or {}).get("licence") or "")
    if "PROVISIONAL" not in lic.upper():
        return ""
    return ('<p class="provmark"><strong>2026 figures on this page are '
            'provisional.</strong> The Met Office has been asked whether we '
            'may republish this season and has not yet answered. The '
            'numbers are the same Heathrow thermometer as the history and '
            'were validated against it on every day of 2024 and 2025; it is '
            'the licence that is unsettled, not the measurement.</p>')


def _join_years(ys):
    """1997 / 1997 and 2003 / 1997, 2003 and 2018."""
    ys = [str(y) for y in sorted(ys)]
    return ys[0] if len(ys) == 1 else ", ".join(ys[:-1]) + " and " + ys[-1]


def _correction_block(name):
    """Editor's explanation of a claim this page used to make.

    The copy lives in copy/heat_corrections.md, which editor owns, for the
    same reason the index copy does: prose inside a Python f-string in a
    file design owns is prose editor cannot deliver. The FACTS in it are
    generated above; this is the part that explains, which no field can.
    """
    raw = CORRECTIONS.get(slug(name))
    if not raw:
        return ""
    paras = [copydeck._inline(x) for x in re.split(r"\n\s*\n", raw)
             if x.strip()]
    return ('<div class="corr"><p class="corr-k">Correction</p>'
            + "".join(f"<p>{x}</p>" for x in paras) + "</div>")


def check_no_silent_claim_reversal(name, head):
    """A published claim may not be withdrawn without the page saying so.

    Palma's live page says "The most hot days Palma has recorded by this
    date." Today's rebuild says "17 hot days so far, 2nd of Palma's 49
    summers." Both are correct: the threshold rose because the station
    starts in 1978 and cannot cover 1971-2000, so its baseline moved to a
    complete normal, the bar went up, and 2026 no longer clears the
    previous best. The 2026 figure never moved. The measuring stick did.

    That is a correction we found ourselves and should be pleased about.
    What it must not be is quiet. A reader who screenshotted the record
    sentence and comes back finds it gone with nothing on the page
    admitting it was ever there, and there is no way for them to tell a
    correction from a retraction we hoped nobody noticed.

    NOTHING WOULD HAVE CAUGHT THIS. The new page is internally consistent,
    every figure agrees with the payload, qa_check passes, and the only
    evidence of the reversal lives in a file the build overwrites. It is
    the two-artefact shape again: the defect is a relationship between the
    published page and the next one, and every guard we have inspects one
    page at a time.

    So this one compares. It reads the claim currently in docs/, which is
    what a reader last saw, and refuses when a record becomes a non-record
    with no correction field to render. Heat emits the fact and editor
    words it (D-030); until that field exists the build stops, which is
    the point. A correction nobody has written is not a correction.
    """
    live = R / f"docs/heat/{slug(name)}.html"
    if not live.exists():
        return                      # a new city has no previous claim
    prev = re.search(r'<meta name="description" content="([^"]+)"',
                     live.read_text())
    if not prev:
        return
    # MATCH THE CLAIM, NOT ONE PHRASING. This tested a single literal
    # prefix, "The most hot days", and Palma's page had since moved to the
    # tie wording, "equalling 2022 for the most in Palma's 49 summers". So
    # when heat's Spain refresh broke that tie and 2022 pulled ahead, the
    # page went from claiming a shared record to claiming none and THE
    # GUARD DID NOT FIRE, because the string it watches was not the string
    # on the page.
    #
    # That is heat's own August failure repeated in my file: a guard that
    # matches one literal while the claim it protects has three wordings.
    # The question is "did this page claim to lead its own record", so that
    # is what is asked.
    def _claims_record(txt):
        t = txt.lower()
        return ("the most hot days" in t or "the most on record" in t
                or "the most in " in t)

    was_record = _claims_record(prev.group(1))
    now_record = _claims_record(head)
    if was_record and not now_record:
        if not CORRECTIONS.get(slug(name)):
            raise SystemExit(
                f"{name}: this page claims a record today and would stop "
                f"claiming one.\n"
                f"  published: {prev.group(1)}\n"
                f"  rebuild  : {head}\n"
                f"  A withdrawn record must be visible on the page. Add a "
                f"'## {slug(name)}' block to copy/heat_corrections.md, which "
                f"editor owns. This build stops rather than swapping the "
                f"sentence in silence.")


def check_europe_scope(name, html):
    if N.get("selection", {}).get("is_representative_of_europe", True):
        return
    hit = _EUROPE.search(text_of(html))
    if hit:
        raise SystemExit(
            f"{name}: {hit.group(0)!r} counts European cities without scoping "
            f"the count to this set (D-112). Say 'these n', or drop the word "
            f"European and let the count be a count of our own cities.")


# Prohibitions the payload carries per city (D-104), checked against the
# rendered page rather than trusted. heat repeats them on every city
# "because a page renders one city and cannot be asked to read the headline
# object", so the renderer has no excuse for not reading them.
NIGHT_SUPERLATIVES = ["worst year", "worst summer", "worst on record",
                      "most on record", "more than any year",
                      "more hot nights than any"]


# A SUPERLATIVE MAY NOT LEAVE ITS DATE BEHIND. Editor's rule, generalised
# from four instances in one day: whenever a figure and the thing that
# calibrates it CAN be separated they will be, and the alarming half is the
# one that survives. The gloss and its summary, the promoted claim and its
# caveat, the count and its coverage, the rank and its headline.
#
# Most of that rule is not mechanically checkable. This part is: every
# figure on these pages is counted to one date, so any superlative about
# the record must say so or it reads as a season total.
#
# It exists because the sweep beat the fix twice today. VD reported one
# instance and there were four; editor reported two pages of loose night
# phrasing and the same fault was in the definition row on all 36. A
# reported defect is a sample, not the population, and a guard is the only
# thing that reads the population every time.
SUPERLATIVES = ("more than in any summer", "hottest this station has recorded",
                "hottest on this record", "most on record", "most hot days")
QUALIFIERS = ("by this date", "to the same date", "by this point")


def check_superlatives_dated(name, page_html):
    t = text_of(page_html)
    for m in re.finditer("|".join(map(re.escape, SUPERLATIVES)), t):
        # A WINDOW, not a sentence. Splitting on full stops walked back
        # through the masthead, which has none, and quoted a hundred
        # characters of nav before reaching the phrase. The qualifier sits
        # within a clause of the superlative or it is not attached to it.
        frag = t[max(0, m.start() - 90):m.end() + 90]
        if not any(q in frag for q in QUALIFIERS):
            raise SystemExit(
                f"{name}: a superlative with no date on it. Every figure here "
                f"is counted to one day, so this reads as a season total:\n"
                f"    ...{t[max(0, m.start() - 60):m.end() + 60]}...")


def check_no_baseline_comparison(name, day_html):
    """For a city whose day multiple is withheld, the DAY surfaces must not
    compare 2026 against a 1961-1990 normal in any form. Checked against
    rendered text because the defect was a drawing as much as a sentence:
    two rows of unit blocks say "nine times" without printing a number.

    Scoped to the day block, not the page. Run over the whole page it fired
    on Lyon, whose NIGHT baseline is published and comparable: nights have
    their own gate and the two are independent. A guard that fails on a
    correct page is one somebody eventually deletes."""
    # SCOPED TO THE 1961-1990 WINDOW, which is the thing heat withholds. It
    # banned the phrase "in a typical" outright, and that was right only
    # while these cities carried no comparison at all. They now carry a
    # 1991-2020 one, complete for every one of them, so a guard against
    # comparison as such would forbid the fix rather than the defect.
    t = text_of(day_html).lower()
    for p in ("used to get", "summer of 1961-1990", "typical 1961-1990"):
        if p in t:
            raise SystemExit(
                f"{name}: multiple_available is false and the page still says "
                f"{p!r}. Its 1961-1990 window is too short to compare against, "
                f"which is why heat withholds that figure. 1991-2020 is the "
                f"window this page may use.")


def check_constraints(name, page_html, night_html, pc):
    # Absent is a failure rather than a pass. A prohibition that quietly
    # stops arriving is indistinguishable from one that was never violated,
    # and the second is what the build would otherwise report.
    if not pc:
        raise SystemExit(f"{name}: no page_constraints in the payload. The "
                         f"page will not be built without them.")
    for w in pc.get("banned_words", []):
        if re.search(rf"\b{re.escape(w)}\b", text_of(page_html), re.I):
            raise SystemExit(f"{name}: the page uses the banned word "
                             f"{w!r}. {pc.get('banned_words_reason', '')}")
    if pc.get("nights", {}).get("may_not_say"):
        low = text_of(night_html).lower()
        for p in NIGHT_SUPERLATIVES:
            if p in low:
                raise SystemExit(
                    f"{name}: the nights block claims {p!r}, and the payload "
                    f"says it may not. {pc['nights']['may_not_say']}")


CSS = """
:root{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#8E240A}
@media(prefers-color-scheme:dark){:root{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#F0876A}}
/* The shared masthead expects these and a standalone page must set them.
   Fixed on the index and NOT propagated here, which is exactly VD's
   argument for a shared template before twenty more pages are built.
   Without them the product nav renders in Spectral instead of tracked
   mono, which is the mechanism section 7 uses INSTEAD of hue, every nav
   item collapses to one inherited colour, and the masthead runs 120px
   wider than the content on each side. */
:root{--mono:'IBM Plex Mono',ui-monospace,monospace;--serif:Spectral,Georgia,serif;
--nino:#173F9E;--fire:#B32E10;--crop:#2E5C16;--shell-max:940px;--shell-pad:24px;
--hist:#8E8E88}
@media(prefers-color-scheme:dark){:root{--nino:#6E97E8;--fire:#E8714E;--crop:#7CB84E;
--hist:#5A5A55}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}
main{max-width:940px;margin:0 auto;padding:0 24px 90px}
.mast{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}
.house{font-size:21px;font-weight:500;color:var(--ink)}
.prod{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}
.when{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}
h1{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.05;
letter-spacing:-.02em;color:var(--ink);margin:40px 0 16px;max-width:19ch;text-wrap:balance}
.stand{font-size:17.5px;line-height:1.62;max-width:62ch;margin:0}
/* A CORRECTION IS NOT A WARNING. It sits in ink on paper with a rule
   above it, the same weight as the page's own prose, because the page is
   explaining itself rather than apologising. D-043 in a different costume:
   the styling must not make a sound correction read as an incident. */
.corr{margin:22px 0 0;padding:15px 0 0;border-top:2px solid var(--ink)}
.corr p{margin:0 0 9px;max-width:60ch;font-size:15.5px;line-height:1.62;
 color:var(--ink-soft)}
.corr p:last-child{margin-bottom:0}
.corr .corr-k{font-family:var(--mono,ui-monospace,monospace);font-size:9.5px;
 letter-spacing:.2em;text-transform:uppercase;color:var(--ink-faint);
 margin-bottom:9px}
.rows{display:flex;flex-direction:column;gap:22px;margin:34px 0 0}
.urow{display:grid;grid-template-columns:196px 1fr 54px;gap:20px;align-items:center}
.uk{font-family:'IBM Plex Mono',monospace;font-size:11px;line-height:1.55;
color:var(--ink-faint);text-align:right}
.ug{display:flex;flex-wrap:wrap;gap:4px}
.u{width:19px;height:19px;background:var(--ink);display:block}
.ua{background:var(--accent)}
.un{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:500;
color:var(--ink);text-align:right}
.provmark{ font-size:15px; line-height:1.55; color:var(--ink);
  border-left:2.4px solid var(--ink); padding:2px 0 2px 15px; margin:18px 0 0;
  max-width:62ch; }
.provmark strong{ font-weight:500; }
.seclab{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:52px 0 14px}
.cap{font-size:15.5px;line-height:1.6;max-width:72ch;margin:12px 0 0}
/* 12 in viewBox units, not 9. The SVG scales to about 0.8 at full page
   width, so 9 rendered at 7.2px against the 10.5px HTML label beside
   it. Same family, same colour, and a third smaller, which is enough
   to read as a different typeface. This lands at 9.7px effective. */
.ax{font-family:'IBM Plex Mono',monospace;font-size:12px;fill:var(--ink-faint)}
.ay{fill:var(--ink-faint)}
.vlab{font-family:'IBM Plex Mono',monospace;font-size:10.5px;fill:var(--ink);
font-weight:500}
.vlab.va{fill:var(--accent)}
.grid{display:grid;grid-template-columns:136px minmax(0,1fr);gap:20px;align-items:end;
margin-top:16px}
.gk{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.5;
letter-spacing:.06em;text-transform:uppercase;color:var(--ink);padding-bottom:8px}
.gk em{display:block;font-style:normal;color:var(--ink-faint);letter-spacing:.03em}
.src{font-family:'IBM Plex Mono',monospace;font-size:12px;line-height:1.9;
color:var(--soft);display:grid;grid-template-columns:1fr auto;column-gap:30px;
margin-top:48px}
.src span{border-top:1px solid var(--rule);padding-top:9px}
.src span:nth-child(-n+2){border-top:2.4px solid #8E8E88}
.more{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent)}
.back{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-faint);text-decoration:none;
border-bottom:1px solid var(--rule)}
"""
CSS += _bandcss()

built, notes, pending = [], [], []

# SOCIALS' ASK, and their second constraint met structurally. Every page
# returned the same og:image, the El Nino weekly card, so a shared heat city
# page previewed with an ENSO chart: on-brand and off-subject, and the
# reader most affected is the one who never clicks.
#
# Generated HERE rather than on its own schedule. A card on a separate
# cadence is London's stale provisional notice with a longer fuse, because
# nobody looks at a preview image after it ships.
from design.make_city_cards import draw_all as _draw_cards  # noqa: E402
_cards = _draw_cards()
print("built %d share cards" % len(_cards))
for name, v in sorted(C.items()):
    yrs = S[name]["years"]
    D = series(yrs, "days_to_cut", "95")
    NI = series(yrs, "nights_to_cut")
    WD = series(yrs, "warmest_day_to_cut_c")
    th = v["days"]["thresholds_c"]["95"]
    now = v["days"]["days_2026"]["95"]
    # READ, never derived. The arithmetic here was right, and matched heat to
    # two decimals on all 24, which is exactly why deriving it looked safe for
    # a fortnight. The value is not the point: reading it means the flag that
    # travels with it cannot be bypassed.
    base = v["days"]["mean_1961_1990_to_cut"]
    # THE PROHIBITION, not the absence. Four cities have a 1961-1990 window too
    # short to compare against, so heat withholds the multiple. I had been
    # treating the missing multiple field as the guard, and an absent field
    # stops a value being printed without stopping it being recomputed, which
    # is what this page did: a headline reading "Murcia used to get 2 hot days
    # by this point. This year: 14", off a window holding 6 of 30 years, with
    # a note underneath saying no multiple is published.
    mult_ok = bool(v["days"]["multiple_available"])
    # THE COMPARISON ROW ALWAYS EXISTS. Kristjan's call, and he is right that
    # dropping it was a misreading: heat withholds the 1961-1990 MULTIPLE for
    # six cities because their record starts too late to fill that window,
    # and I turned that into showing no past at all. A single row of squares
    # is not a comparison, it is a decorative count of the number already in
    # the headline.
    #
    # 1991-2020 is COMPLETE for all six, because it is the window their late
    # start does not truncate. Lyon has 16 of 30 years in 1961-1990 and 30 of
    # 30 in 1991-2020; Murcia has 7 and 30. So the row keeps its job and the
    # label says which period it is, which is the honest version of a
    # difference rather than a hidden one.
    #
    # This does not touch heat's prohibition, which is on the 1961-1990
    # figure specifically. Told them what I did so they can overrule it.
    _b9120 = [x["days_to_cut"]["95"] for y, x in yrs.items()
              if 1991 <= int(y) <= 2020 and x.get("usable_to_cut")
              and x.get("days_to_cut")]
    if mult_ok:
        cmp_val, cmp_period = base, "1961-1990"
    elif len(_b9120) >= 28:
        cmp_val, cmp_period = st.mean(_b9120), "1991-2020"
    else:
        cmp_val, cmp_period = None, None
    nbase = st.mean([x for y, x in NI if 1961 <= y <= 1990]) if NI else 0
    gated = bool(v.get("nights_metric_gated"))
    peak = dict(WD).get(2026)
    prank = 1 + sum(1 for y, x in WD if x >= peak and y != 2026)
    pprev = max(x for y, x in WD if y != 2026)
    pprev_y = max(y for y, x in WD if x == pprev and y != 2026)
    # THE FIRST USABLE YEAR, not the first year the thermometer reported.
    # Nine cities have a partial first year excluded from the ranked series,
    # so record_from runs one to two years earlier than the window every
    # rank, axis and baseline on this page is computed on. Four live pages
    # said one thing in prose and drew another on the axis beneath it.
    #
    # Leipzig was the one that mattered. Its sentence justified WHICH
    # baseline the city gets, resting on a start year the chart underneath
    # refuted, so the reasoning did not survive a reader checking it. The
    # others read as a typo; that one read as an argument built on a wrong
    # number.
    #
    # record_scope.from_year is not a new field: it already is the window
    # the ranks use, and heat added record_from_note saying explicitly that
    # record_from is NOT the answer to how far back we can see.
    scope_from = str(v.get("record_scope", {}).get("from_year")
                     or v["record_from"])
    cut = S[name]["cut_at"]
    cut_txt = f"{int(cut.split('-')[1])} {MON[int(cut.split('-')[0]) - 1]}"
    dr = v["days"]["rank"]
    peak_promoted = (prank == 1 and dr["value"] != 1)
    # WHAT A TYPICAL SUMMER PEAKS AT. VD: 40.6 C is a number, and a reader
    # has no idea whether that is remarkable for Paris or a normal August
    # afternoon. "The previous best is 41.9" gives the ceiling and no floor.
    #
    # The MEDIAN of the whole record, not a baseline period, so it is safe on
    # the four cities whose 1961-1990 window is withheld: it needs no window
    # at all and cannot reintroduce the trap that was live this morning.
    typical_peak = st.median([x for y, x in WD if y != 2026])

    # THE RELOCATION NOTE SITS WITH THE RANK, not in the footer, because the
    # rank is what it undermines: "of 79" spans more than one site. D-081, a
    # qualifier lives at the level of the thing it qualifies. Four cities
    # carry one; the flag is read, never inferred from the move list.
    # THE NOTE GOVERNS THE STATION, not the count, and it sits above both
    # ranks. Editor promoted the peak line and then caught what the promotion
    # did: Berlin's peak record runs 1948 to 2026 and spans the move too, but
    # the note was written to qualify the COUNT and sat downstream, so the one
    # promoted sentence was the only record claim on the page with nothing
    # attached to it. The conclusion moved up and its qualifier stayed put,
    # which is this morning's failure in a different place.
    #
    # Composed from the payload's own relocation records rather than from
    # heat's generated string, because that string names 'of 79' and is
    # therefore about the count by construction.
    _rel = v.get("station_relocations") or []
    if v["rank"].get("requires_relocation_note") and _rel:
        _moves = " and ".join(f"{m['km']} km in {m['date'][:4]}" for m in _rel)
        station_note = (
            f'<p class="stand" style="margin-top:16px">{name}\'s records begin '
            f'in {scope_from}, but the station moved {_moves}, so they are '
            f'not one continuous site.</p>')
    else:
        station_note = ""
    reloc = ""
    rank_txt = ("the most on record by this date" if dr["value"] == 1
                else f'{ordn(dr["value"])} of {dr["of_years"]}')
    # NO RANK CAPTION. Editor's rule and it needed no judgement from me: a
    # caption never restates the number, the title or the source stamp,
    # because a caption repeating what the image should say is a caption doing
    # the image's job. Putting the rank in the headline made this one a repeat
    # four lines down. Anchoring is pointing at the mark, and 2026 already
    # carries an accent fill AND a full-height rule in bars(), so the bar
    # identifies itself without being described.

    # The headline must name its period: base is a TO-DATE mean and reading
    # it as a season total overstates the change. Where the baseline is not
    # comparable the headline leads on the count and its rank instead, which
    # are both published, rather than on a comparison that is not.
    # THE RANK IS IN THE HEADLINE, and the branch is on whether the baseline
    # exists, NEVER on how alarming the answer is. Editor's ruling, and the
    # reasoning is the part to keep: a separate shape for cities outside their
    # top five would be a template deciding which cities get calibrated, on the
    # criterion of how bad the number looks, and it breaks the moment a city
    # crosses the boundary.
    #
    # It was six cities, not one. Berlin's 8 days against a 1961-1990 mean of
    # 2.1 read as a near-quadrupling with 11th of 79 buried below the chart,
    # which is louder than Stockholm and was the same defect.
    # EVERY SUPERLATIVE CARRIES THE DATE. VD Main caught this on the
    # headline and the same drop was in four places: a figure counted to 3
    # August, stated as though it were a season total. The matched basis
    # again, in the sentence a reader is most likely to quote.
    # ONE TIER, TEN WORDS. VD Main's diagnosis: the headline and the squares
    # were the same sentence printed twice, eight inches apart, so shrinking
    # the first half only made the duplicate quieter. The squares already say
    # 1.7 against 37 better than words can, so the headline's job is what the
    # comparison MEANS.
    #
    # Their record form, taken as written. For a city NOT at a record their
    # form was "9 hot days so far, and the summer is not over", and that is
    # the same sentence for Hamburg at the 92nd percentile and Helsinki at
    # the 52nd. It would be the same for a city at 60th of 76. The only
    # qualifier in it is true everywhere and reads as a warning, so the calm
    # cities lead with an escalation and the rank is demoted to the line
    # below: the small-grey-line pattern VD themselves ruled out, inverted.
    #
    # THE RANK IS WHAT THE HEADLINE IS FOR ON THOSE CITIES. The squares show
    # a multiple, and a multiple alone always implies escalation. The rank is
    # the only thing that corrects it and it appears in no graphic on the
    # page. Same length, same structure, and it survives the boundary: at 8th
    # of 91 it reads as notable, at 28th of 56 as unremarkable, off one
    # template rather than two.
    # A TIE FOR FIRST IS NOT A DEMOTION, AND THE OLD BRANCHING CALLED IT ONE.
    # Two cases: rank 1, and everything else. So Palma at rank 2, tied with
    # 2022 and beaten by nobody, read "2nd of Palma's 49 summers", which
    # states that some year was hotter. None was.
    #
    # Editor caught it in their own draft ("second only to 2022" says 2022 was
    # hotter) and it is Hamburg's shape from this morning on a second city, so
    # it is a template branch rather than one page's copy.
    #
    # DERIVED FROM THE FIELDS, NOT RECOMPUTED. heat's tie_note is explicit
    # that recomputing the rank with a strict greater-than gives a different
    # and more alarming answer. So this never touches the series: rank counts
    # prior years AT OR ABOVE, so if the rank is exactly one more than the
    # number of tied years, every year keeping 2026 off first place is a tie
    # and nothing exceeds it.
    ties = list(dr.get("tied_with") or [])
    ties_for_first = dr["value"] == 1 + len(ties) and ties
    if dr["value"] == 1:
        head = f"The most hot days {name} has recorded by this date."
    elif ties_for_first:
        # "the most X has recorded" is a superlative with nothing under it.
        # Editor's wording merged with heat's: heat's carried the
        # denominator, editor's was shorter, and the denominator is the part
        # worth keeping. Same reason the rank never ships without its series.
        head = (f"{now} hot days so far this year, equalling "
                f"{_join_years(ties)} for the most in {name}'s "
                f"{dr['of_years']} summers.")
    else:
        head = (f"{now} hot days so far, {ordn(dr['value'])} of "
                f"{name}'s {dr['of_years']} summers.")

    # THE PEAK CARRIES ITS OWN RANK. Seven cities have peak == record, so
    # the sentence branches rather than being templated.
    if prank == 1 and dr["value"] == 1:
        peak_cap = (f"The hottest day of {name}'s year, to the same date. "
                    f"<strong>2026 is the hottest on this record too, by this "
                    f"date</strong>, at "
                    f"{peak}&nbsp;&deg;C. Both the count and the peak are records "
                    f"here, which is not true everywhere: a count and a peak are "
                    f"separate claims and each carries its own rank. The "
                    f"previous best was {pprev}&nbsp;&deg;C in {pprev_y}, the "
                    f"dot on the drop line, and a typical summer here peaks "
                    f"at {typical_peak:.1f}&nbsp;&deg;C.")
    elif peak_promoted:
        # Editor counted it: "11th of 79" three times and 39.9 C three times on
        # one page. I had told them this was fixed. It was changed and it still
        # said the same thing, which is not the same as fixed. The promoted
        # line above carries the claim; this caption describes the chart and
        # adds the one fact not stated anywhere else, the previous best.
        peak_cap = (f"The hottest day of {name}'s summer, to the same date, "
                    f"with 2026 marked. The previous best was "
                    f"{pprev}&nbsp;&deg;C in {pprev_y}, the dot on the drop "
                    f"line below it, and a typical summer here peaks at "
                    f"{typical_peak:.1f}&nbsp;&deg;C.")
    elif prank == 1:
        # "Both the count and the peak are records here" was rendering on
        # Barcelona, Berlin and Prague, whose counts are 2nd of 87, 11th of 79
        # and 4th of 56. The branch tested the PEAK being a record and then
        # asserted something about both, which is the same shape as the
        # Paris sentence published on six cities that contradicted it.
        # The disagreement now leads the page, so this caption states the
        # chart and points back rather than repeating it.
        peak_cap = (f"The hottest day of {name}'s year, to the same date, with "
                    f"2026 marked. <strong>It is the hottest this station has "
                    f"recorded by this date</strong>, at {peak}&nbsp;&deg;C, "
                    f"while the count "
                    f"of hot days is {rank_txt}.")
    else:
        # BOTH HALVES OF THIS SENTENCE WERE WRONG, and both in the way this
        # template keeps failing: prose written from one city, templated to
        # fifteen.
        #
        # "More hot days than any year on record" was Paris's day rank, and
        # it is FALSE on the six pages whose count is not first: Amsterdam
        # is 9th of 76, Hamburg 10th, Madrid 3rd, Seville 8th, Valencia 6th,
        # Cologne 2nd. The clause now reads the rank it is describing.
        #
        # "The open ring" named a mark VD had already removed. The previous
        # record is a filled dot on a drop line now, so the caption pointed
        # a reader at something that is not on the chart.
        if peak == pprev:
            # Hamburg, 39.1 against 39.1. Rendered as a comparison it reads
            # as a rendering error, and the reader's correction of it would
            # be the more alarming answer. The convention is standing and
            # holds across the channel: ties count against, and a tie is not
            # a record.
            # "here" read as a local quirk. It is the convention everywhere.
            versus = (f"It matches {pprev_y} exactly, the dot on the drop line. "
                      f"A tie is not a record: the rank counts earlier years at "
                      f"or above 2026, so a year that equals it keeps 2026 off "
                      f"first place.")
        else:
            versus = (f"The previous best is {pprev}&nbsp;&deg;C in {pprev_y}, "
                      f"the dot on the drop line.")
        # "2026 is the 18th hottest day" says a year is a day. The subject is
        # the day, so the sentence starts there.
        peak_cap = (f"{name}'s hottest day this year, {peak}&nbsp;&deg;C, is "
                    f"<strong>{ordn(prank)} on this record</strong>. {versus} "
                    f"A typical summer here peaks at {typical_peak:.1f}&nbsp;&deg;C. "
                    f"Its hot-day count is {rank_txt}: a count and a peak are "
                    f"different claims, and neither borrows the other's rank.")

    if gated:
        # "averages about 0.0 a year" is what the single template produced for
        # Amsterdam and Hamburg. It reads as a rounding artefact, and it
        # understates the case: the point of the gate is that the base is too
        # thin to divide by, and a base that rounds to zero makes that point
        # better stated as a total than as an average.
        nwin = [x for y, x in NI if 1961 <= y <= 1990]
        ntot = int(sum(nwin))
        if v["nights_2026"] == 0:
            # Zero this year is not a smaller version of two: the instrument
            # does not reach here. Editor's fix, and it puts the reason first
            # so the zero reads as a property of the measure rather than as a
            # blank. heat's own note says the same thing about the metric.
            #
            # THE FIGURE IS THE TO-CUT ONE, not nights_baseline_per_year.
            # That field reads 0.3 for Stockholm where the matched total is 1
            # night in thirty years, so it is on a wider basis than the count
            # beside it. Pairing them would be the b6190 trap again.
            base_clause = (f'The 20&nbsp;&deg;C night is a Mediterranean measure '
                           f'and {name} is outside its range. None this year, and '
                           f'{words_n(ntot)} in the whole of 1961-1990 by this '
                           f'date. No multiple is quoted, because dividing by a '
                           f'base that thin is arithmetic rather than evidence')
        elif ntot == 0:
            base_clause = (f'{name} did not record a single one in the whole of '
                           f'1961-1990 by this date, so there is no base to '
                           f'divide by')
        elif round(nbase, 1) == 0.0:
            base_clause = (f'{name} recorded {ntot} in the whole of 1961-1990 by '
                           f'this date, so a ratio against that base would be '
                           f'arithmetic rather than evidence')
        else:
            base_clause = (f'{name} averages about {nbase:.1f} a year, and '
                           f'dividing by a base that thin produces a large '
                           f'number and no evidence')
        night_block = (
            f'<p class="cap">'
            + ("" if v["nights_2026"] == 0 else
               f'{v["nights_2026"]} night{"" if v["nights_2026"] == 1 else "s"} so '
               f'far that never dropped below 20&nbsp;&deg;C. '
               f'<strong>No multiple is quoted here.</strong> ')
            + f'{base_clause}. '
            f'{sum(1 for c in C.values() if c.get("nights_metric_gated"))} of the '
            f'{len(C)} cities are gated this way.</p>')
    else:
        nrank = v["rank"]
        night_block = (
            # "at or above 20 C" drops the MINIMUM and reads as a night that
            # reached 20, which nearly every summer night does. The metric is
            # nights whose minimum never falls below it. The loose phrasing was
            # on the two pages that also quote a night rank, so it was where a
            # wrong reading cost most. And the night rank now uses the day
            # rank's grammar, four lines above it on the same page.
            f'<p class="cap">{v["nights_2026"]} night'
            f'{"" if v["nights_2026"] == 1 else "s"} so far that never dropped '
            f'below 20&nbsp;&deg;C'
            # THE WITHHELD BASELINE WAS BEING PUBLISHED HERE, on the same
            # screen as the note refusing it. VD Heat found it on Murcia:
            # "No 1961-1990 comparison is shown for Murcia", and four
            # paragraphs down, "against 9.4 in a typical 1961-1990 summer".
            #
            # It survived because the two prohibitions were checked
            # separately and this line sits in the overlap. multiple_available
            # is a flag on DAYS, the nights gate is a different flag, and I
            # had deliberately scoped the guard away from the night block on
            # the grounds that Lyon's nights were legitimately comparable.
            # They are not: Lyon's record starts in 1975, so its 1961-1990
            # night window holds 16 of 30 years for the same reason its day
            # window does. Murcia's holds 7.
            #
            # The window is short because the STATION started late. That is
            # not a property of days or of nights, so the flag governs every
            # 1961-1990 figure on the page.
            + (f', against {nbase:.1f} in a typical 1961-1990 summer by this '
               f'date' if mult_ok else '')
            + f'. That is {ordn(nrank["value"])} of its '
            f'{nrank["of_years"]} summers.</p>')

    # The unit rows ARE the comparison, drawn. Leaving the baseline row in
    # place and withholding only the arithmetic would have kept the defect
    # and hidden it better: two rows of blocks side by side say "nine times"
    # whether or not the page prints the number.
    unit_rows = ""
    if cmp_val is not None:
        unit_rows = (
            f'<div class="urow"><span class="uk">By this date in a typical<br>'
            f'summer of {cmp_period}</span>'
            f'<span class="ug">{units(cmp_val)}</span>'
            f'<span class="un">{cmp_val:.1f}</span></div>')
    unit_rows += (
        f'<div class="urow"><span class="uk">By this date<br>this summer</span>'
        f'<span class="ug">{units(now, True)}</span><span class="un">{now}</span></div>')

    # Sits with the unit rows, which is what it qualifies, rather than under
    # the chart three sections down. The year count in heat's own note is
    # theirs and I do not restate it; record_from is a field and says the
    # same thing without a second arithmetic.
    mult_note = ("" if mult_ok else
                 f'<p class="cap"><strong>{name} is compared against 1991-2020, '
                 f'not 1961-1990.</strong> This thermometer starts in '
                 f'{scope_from}, so the earlier window every other city uses '
                 f'would cover only its warmer final years here, and a figure '
                 f'against that would look like every other city\'s while meaning '
                 f'something weaker. 1991-2020 is complete for this station, so it '
                 f'is the one shown. The count and the rank are measured on the '
                 f'full record and stand.</p>')

    # TWO INSTRUMENTS, TWO ANSWERS, AND IT GOES SECOND. Where the hottest
    # single day is a record and the hot-day COUNT is not, the disagreement is
    # the most interesting thing on the page and it was the last paragraph on
    # it. Editor's call, and their framing: no "though", no "but", the
    # disagreement is the finding rather than an awkwardness to bury.
    #
    # Branched on the data disagreeing, not on which answer is louder. Three
    # cities today: Barcelona 2nd of 87, Berlin 11th of 79, Prague 4th of 56,
    # each with a record peak.
    peak_lead = ("" if not peak_promoted else
                 f'<p class="stand" style="margin-top:18px">Its hottest single '
                 f'day, {peak}&nbsp;&deg;C, is the hottest this station has '
                 f'recorded by this date. A count and a peak are different '
                 f'claims and neither '
                 f'borrows the other\'s rank.</p>')

    # The method moves out from under the headline and down to the chart it
    # describes, and "95th percentile" becomes a thing a reader can picture.
    # One summer day in twenty IS the 95th percentile, said so it can be used.
    # THE THRESHOLD STATES THE YEARS IT ACTUALLY RESTS ON. Heat sent the push
    # back on this and the diagnosis is theirs: they built MIN_BASELINE_YEARS
    # to withhold the 1961-1990 multiple where coverage is short, and never
    # applied the same test to the 1971-2000 threshold window, which is short
    # for the identical reason. One baseline guarded, the other not.
    #
    # "between 1971 and 2000" is factually wrong for Murcia, whose station
    # starts in 1984. That is a wrong statement rather than a caveat we chose
    # to omit, and withholding one figure for short coverage while printing
    # another in silence is the shape a reader with an atlas finds first.
    #
    # NOT WITHHELD, unlike the multiple, on heat's ruling: a per-city
    # threshold is a calibration against that city's own series and its rank
    # stays meaningful. The multiple is withheld because it invites
    # cross-city comparison; the threshold does not.
    #
    # THE SET IS NOT THE SAME as the withheld-multiple set, which is why this
    # is computed rather than reusing mult_ok. Prague and Helsinki have a
    # complete 1971-2000 window and a short 1961-1990 one. Three cities carry
    # this note: Lyon 26 of 30, Palma 23, Murcia 17.
    # READ THE PERIOD, NEVER ASSUME IT. This computed max(1971, ...) against
    # a hard 2001, which was true of every city until this afternoon and is
    # now false for Tallinn: product allowed a city whose record cannot cover
    # 1971-2000 to use another complete WMO normal, and Tallinn is on
    # 1991-2020 (D-151).
    #
    # Left alone, the arithmetic did not merely mislabel the window, it
    # INVENTED A SHORTFALL. Tallinn starts in 1980 and covers 1991-2020
    # completely, so there is no shortfall at all, and the old expression
    # would have printed "21 of the 30 years every other city's threshold
    # uses, so the level sits a little high" underneath a threshold that is
    # perfectly well founded. A caveat that is false is worse than a missing
    # one, because a reader discounts a sound number on our say-so.
    #
    # Same shape as record_scope and as the aria-labels on the crops map
    # this afternoon: a constant that quietly became a variable.
    bl_lo, bl_hi = (v.get("pctl_baseline") or [1971, 2000])
    bl_span = bl_hi + 1 - bl_lo
    thr_from = max(int(bl_lo), int(v["record_from"]))
    thr_years = bl_hi + 1 - thr_from
    thr_note = ("" if thr_years >= bl_span else
                f' That window is {thr_years} of the {bl_span} years this '
                f'city\'s threshold period runs to, because this thermometer '
                f'only starts in {scope_from}, so the level is set from its '
                f'warmer years and sits a little high. The count below is an '
                f'undercount rather than an overcount.')
    # A NON-DEFAULT PERIOD IS DISCLOSED, not silently substituted. Heat's
    # note carries why it matters: a later normal runs warmer, so the
    # threshold sits higher and the count understates.
    if v.get("pctl_baseline_is_default") is False and v.get("pctl_baseline_note"):
        # Heat's note is a fragment, not a sentence: it opens lower case
        # because it was written to follow a colon. Dropped in after a full
        # stop it read "between 1991 and 2020. the percentile thresholds",
        # so the capital is added here rather than asking them to rewrite a
        # field several surfaces consume.
        _n = str(v["pctl_baseline_note"]).strip()
        thr_note += " " + _n[:1].upper() + _n[1:]
    method = (f'<p class="cap">Hot here means {th}&nbsp;&deg;C or above, a level '
              f'about one summer day in twenty used to reach at this station '
              f'between {thr_from} and {bl_hi}.{thr_note} The bar has not moved; '
              f'the number of days clearing it has. Every year is counted to '
              f'{cut_txt}, so a part-finished summer is never set against '
              f'complete ones. '
              f'<strong>That threshold is {name}\'s own.</strong> It is not a '
              f'national standard and it is not comparable with another '
              f'city\'s: every figure on this page is measured against this '
              f'station and nothing else.</p>')

    top = max(max(x for _, x in D), 1)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} &middot; Heat &middot; The Long Swell</title>
<meta name="description" content="{head}">
<link rel="canonical" href="{PAGES_BASE_URL}/heat/{slug(name)}.html">
<!-- These pages are the promotion surface: Kristjan links a city and a
     reader arrives caring about that city. Without share metadata a
     promoted link renders as a bare URL with no title and no claim. The
     description IS the headline, so what a reader sees before clicking is
     the same sentence they see after. -->
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{name}: {now} hot days so far this summer">
<meta property="og:description" content="{head}">
<meta property="og:url" content="{PAGES_BASE_URL}/heat/{slug(name)}.html">
<!-- A page that declares summary_large_image and supplies no image is
     WORSE than one that declares nothing: the platform reserves the
     slot and renders it empty. Socials measured 136 channel pages
     sharing with no image at all, heat declaring the large card and
     showing a blank one. The house card is generic and beats an
     empty slot; per-page cards wait for the citable chart, and will
     have to carry their cut date so a stale one is visibly stale. -->
<meta property="og:image" content="{PAGES_BASE_URL}/heat/cards/{slug(name)}.png">
<meta name="twitter:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{name}: {now} hot days so far this summer">
<meta name="twitter:description" content="{head}">
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}{CSS}</style><!-- payload {PAYLOAD_STAMP} --></head><body><main>
{site_masthead("../", active="heat")}
<!-- THE HOUSE NAME IS NOT REPEATED HERE. This bar predates the shared
     masthead, which now sits directly above it and already carries the
     wordmark, so the page printed "The Long Swell" twice inside 100px.
     Kristjan spotted it. What this bar is for is the page's own
     identity: the channel, and which station and cut it reports. -->
<div class="mast"><span class="prod">Heat</span>
<span class="when">{name} &middot; {S[name]['station']} &middot; to {cut_txt} 2026</span></div>

<h1>{head}</h1>
{_provisional_mark(v)}
{_correction_block(name)}
{peak_lead}
{station_note}

<div class="rows">{unit_rows}</div>
{mult_note}

<!-- THE THREE CHARTS STACK WITH NOTHING BETWEEN THEM. Kristjan's change,
     and the reason is that they only become comparable when the eye can
     run down them: same width, same year span, same left label column, no
     paragraph resetting the reader between each one. The prose that used
     to sit in the gaps now sits below all three, in chart order. -->
<div class="seclab">Every summer on this thermometer</div>
<div class="grid"><span class="gk">Hot days<em>above {th} &deg;C</em></span>
<span>{bars(D, top)}</span></div>
<div class="grid"><span class="gk">Hot nights<em>never below 20 &deg;C</em></span>
<span>{bars(NI, max(x for _, x in NI) or 1)}</span></div>
<div class="grid"><span class="gk">Hottest day<em>{min(x for _, x in WD):.0f} to {max(x for _, x in WD):.0f} &deg;C</em></span>
<span>{line(WD, mark_year=2026, ring_year=pprev_y, mark_val=peak, ring_val=pprev)}</span></div>

{method}

{night_block}

<p class="cap">{peak_cap}</p>

<!-- The methodology link sits with the sources, not in the nav. The
     shared masthead takes a methodology_href and does not render it,
     so passing one there is silent and does nothing; this is the
     place a reader checking a number is already looking. -->
<!-- BUSINESS'S FINDING, measured on the first real week: ~47 of ~51
     social post URLs pointed at /heat or /heat/<city>, and the form lived
     only on the front page at line 470 of 485. So ~90% of 800 uniques
     landed where subscribing was IMPOSSIBLE. Four subscribers from eight
     hundred visitors is an absent ask, not a weak one.

     HERE rather than in the footer: a reader who has just seen their own
     city's record is at the only moment they will be interested, and the
     footer is where interest goes to die. That is exactly where the front
     page put it. -->
{_SUB_BAND}

<div class="src">
<span><a href="methodology.html">How these figures are built</a></span>
<span style="text-align:right">Heat methodology</span>
<span>{S[name]['source']}, {S[name]['station']}, daily minimum and maximum</span>
{_provisional_block(v)}
<span style="text-align:right">to {v['counted_to']}</span>
<!-- Kristjan's ruling, 2026-08-07: show the state per city rather than
     verify quietly or hedge across the set. Three different facts and the
     reader gets whichever is true of their city. Generated by heat from
     the station history, never typed here, so a city moving from unchecked
     to checked-and-clean improves the page with no copy change. -->
<span>{v['station_disclosure']}</span>
<span style="text-align:right">station history</span>
<!-- DERIVED, not typed. This row is the formal DEFINITION of the threshold
     and it carried the literal string "1971 to 2000" while the prose above
     it had already been corrected to the per-station window. Murcia's page
     therefore stated two different reference periods for the same number,
     two paragraphs apart, and the false one was the definition. -->
<span>Hot days, this station's own 95th percentile of July-August maxima, {thr_from} to {bl_hi}</span>
<span style="text-align:right">{th} &deg;C</span>
<!-- Same defect editor found in the prose, in the line that DEFINES the
     metric. 'At or above 20' drops the minimum and describes a night that
     reached 20, which nearly every summer night does. -->
<span>Hot nights, ETCCDI index TR, daily minimum never below 20.0 &deg;C</span>
<span style="text-align:right">not chosen by us</span>
<!-- VD Heat, reader's view: every figure is to 2 or 3 August and a reader
     arriving later cannot tell whether the summer ended, whether the page is
     stale, or when it changes. A returning reader sees the same 30 and
     assumes nothing happened. -->
<span>Updated weekly, each Monday</span>
<span style="text-align:right">counted to {v['counted_to']}</span>
</div>
<!-- THE WAY OUT. VD Heat: the city page is the promotion surface, so most
     readers arrive here first and this is the whole site to them. A Berliner
     sent the Paris link had a masthead link to the channel and nothing that
     said twenty-three other cities exist. The index has the map, and the map
     is the invitation. -->
<p class="stand" style="margin-top:34px;padding-top:22px;border-top:1px solid var(--rule)">
{len(C)} cities are measured this way, each against its own record.
<a class="more" href="index.html">See them on the map</a></p>
</main></body></html>"""
    check_constraints(name, html, night_block, v.get("page_constraints", {}))
    check_superlatives_dated(name, html)
    check_no_silent_claim_reversal(name, head)
    check_europe_scope(name, html)
    # The page may not claim a window the station did not cover. Derived, so
    # it cannot drift, and guarded anyway because this is the defect that
    # sent the push back and it was invisible for a fortnight.
    #
    # THE GUARD USED TO MATCH ONE PHRASING and that is why it missed. It
    # searched for the literal "between 1971 and 2000", which is how the
    # prose says it; the definitions row said "maxima, 1971 to 2000", the
    # same claim in different words. The prose was fixed, the guard went
    # green, and the false sentence sat in the row that DEFINES the number.
    #
    # Heat named this shape the same morning: a guard per surface, and no
    # guard on the question the surfaces share. So this one no longer asks
    # "does the page contain this sentence" but "does the page anywhere
    # claim a window that starts before the thermometer did", which is the
    # question, and it holds for any future wording.
    claimed = re.findall(r"(\d{4})\s*(?:to|and|-|–)\s*%d" % bl_hi, text_of(html))
    too_early = sorted({int(y) for y in claimed if int(y) < int(v["record_from"])})
    if too_early:
        raise SystemExit(
            f"{name}: the page claims a threshold window starting "
            f"{', '.join(str(y) for y in too_early)} and this station's record "
            f"starts in {v['record_from']}. A window the thermometer did not "
            f"cover cannot be stated as the period the level was set from.")
    if not mult_ok:
        check_no_baseline_comparison(name, head + unit_rows + mult_note + night_block)
    # BUFFERED, NOT WRITTEN. Every guard in this file raises SystemExit,
    # and the loop is alphabetical, so a city failing at P had already
    # overwritten twenty-five live pages by the time it stopped. The build
    # reported a failure and left docs/ half rebuilt: some pages on the new
    # payload, the rest on the old, and nothing on any page saying which.
    #
    # Found by tripping my own new guard on Palma. A guard that fires
    # mid-loop turns one refusal into a partially published site, which is
    # worse than the defect it was catching.
    #
    # So nothing reaches docs/ until every city has passed every check.
    pending.append((R / f"docs/heat/{slug(name)}.html", html))
    built.append(name)
    if gated:
        notes.append(f"{name}: night-gated")
    if name in NO_MULT:
        notes.append(f"{name}: no day multiple")
    if prank == 1:
        notes.append(f"{name}: peak is also a record")

# EVERY CORRECTION MUST HAVE REACHED A PAGE. copydeck.render() fails on a
# slot nothing uses; I called load() directly and so bypassed it, and
# promptly wrote a block that was never placed. Editor's prose sitting in a
# tracked file that no page renders is the same loss as prose deleted, and
# it looks like success from both ends.
_placed = {slug(n) for n in built}
_orphan = sorted(k for k in CORRECTIONS if k not in _placed)
if _orphan:
    raise SystemExit(
        "copy/heat_corrections.md has %d block(s) for cities that were not "
        "built: %s. A correction nobody renders is not a correction."
        % (len(_orphan), ", ".join(_orphan)))
for _n in built:
    if slug(_n) in CORRECTIONS:
        _h = dict(pending)[R / ("docs/heat/%s.html" % slug(_n))]
        if 'class="corr"' not in _h:
            raise SystemExit(
                "%s has a correction block in copy/heat_corrections.md that "
                "did not reach its page." % _n)

# The single write point. Reached only when every city has passed.
for _path, _html in pending:
    _path.parent.mkdir(parents=True, exist_ok=True)
    _path.write_text(_html)

print(f"built {len(built)} city pages")
for n in notes:
    print("  ", n)
