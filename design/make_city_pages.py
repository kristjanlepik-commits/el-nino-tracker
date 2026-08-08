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
import sys
sys.path.insert(0, str(R))
from run_brief import (ANALYTICS_SNIPPET, PAGES_BASE_URL,   # noqa: E402
                       SITE_MASTHEAD_CSS, SITE_NAME, site_masthead)
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())["cities"]
C = N["cities"]
NO_MULT = set(N["cities_without_day_multiple"])
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
    ticks = "".join(
        f'<text x="{i*bw:.1f}" y="{h+13}" class="ax" '
        f'text-anchor="{"end" if y == 2026 else "start"}">{y}</text>'
        for i, (y, _) in enumerate(data)
        if y in (data[0][0], 1976, 2000, 2026))
    return (f'<svg viewBox="0 0 {w} {h+18}" width="100%" style="height:{h+18}px" '
            f'preserveAspectRatio="none">{"".join(out)}{ticks}</svg>')


def line(data, w=880, h=104, mark_year=None, ring_year=None):
    lo = min(v for _, v in data) - .5
    hi = max(v for _, v in data) + .5
    px = lambda y: (y - data[0][0]) / (data[-1][0] - data[0][0]) * w
    py = lambda v: h - (v - lo) / (hi - lo) * h
    pts = " ".join(f"{px(y):.1f},{py(v):.1f}" for y, v in data)
    extra = ""
    d = dict(data)
    if ring_year and ring_year in d:
        # NOT a hollow ring. Hollow is the null convention, and this is the
        # one historical value the caption is comparing against, so it has
        # to be the second strongest mark on the chart rather than the
        # faintest. Same reasoning that removed the rings from the map.
        extra += (f'<circle cx="{px(ring_year):.1f}" cy="{py(d[ring_year]):.1f}" '
                  f'r="3.4" fill="var(--ink)"/>'
                  f'<line x1="{px(ring_year):.1f}" y1="{py(d[ring_year]):.1f}" '
                  f'x2="{px(ring_year):.1f}" y2="{h:.1f}" stroke="var(--ink)" '
                  f'stroke-width="1" opacity="0.45"/>')
    if mark_year and mark_year in d:
        extra += (f'<circle cx="{px(mark_year):.1f}" cy="{py(d[mark_year]):.1f}" '
                  f'r="3.6" fill="var(--accent)"/>')
    return (f'<svg viewBox="0 0 {w} {h+6}" width="100%" style="height:{h+6}px" '
            f'preserveAspectRatio="none"><polyline points="{pts}" fill="none" '
            f'stroke="var(--soft)" stroke-width="1.2"/>{extra}</svg>')


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
    """Rendered words only. A guard that greps raw HTML finds nothing when a
    phrase is split across tags, and reports that as proof of absence."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# Prohibitions the payload carries per city (D-104), checked against the
# rendered page rather than trusted. heat repeats them on every city
# "because a page renders one city and cannot be asked to read the headline
# object", so the renderer has no excuse for not reading them.
NIGHT_SUPERLATIVES = ["worst year", "worst summer", "worst on record",
                      "most on record", "more than any year",
                      "more hot nights than any"]


def check_no_baseline_comparison(name, day_html):
    """For a city whose day multiple is withheld, the DAY surfaces must not
    compare 2026 against a 1961-1990 normal in any form. Checked against
    rendered text because the defect was a drawing as much as a sentence:
    two rows of unit blocks say "nine times" without printing a number.

    Scoped to the day block, not the page. Run over the whole page it fired
    on Lyon, whose NIGHT baseline is published and comparable: nights have
    their own gate and the two are independent. A guard that fails on a
    correct page is one somebody eventually deletes."""
    t = text_of(day_html).lower()
    for p in ("used to get", "in a typical", "typical summer"):
        if p in t:
            raise SystemExit(
                f"{name}: multiple_available is false and the page still says "
                f"{p!r}. The 1961-1990 window is too short here to compare "
                f"against, which is why heat withholds it.")


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
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}
@media(prefers-color-scheme:dark){:root{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}
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
.rows{display:flex;flex-direction:column;gap:22px;margin:34px 0 0}
.urow{display:grid;grid-template-columns:196px 1fr 54px;gap:20px;align-items:center}
.uk{font-family:'IBM Plex Mono',monospace;font-size:11px;line-height:1.55;
color:var(--ink-faint);text-align:right}
.ug{display:flex;flex-wrap:wrap;gap:4px}
.u{width:19px;height:19px;background:var(--ink);display:block}
.ua{background:var(--accent)}
.un{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:500;
color:var(--ink);text-align:right}
.seclab{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:52px 0 14px}
.cap{font-size:15.5px;line-height:1.6;max-width:72ch;margin:12px 0 0}
.ax{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}
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
.back{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-faint);text-decoration:none;
border-bottom:1px solid var(--rule)}
"""

built, notes = [], []
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
    nbase = st.mean([x for y, x in NI if 1961 <= y <= 1990]) if NI else 0
    gated = bool(v.get("nights_metric_gated"))
    peak = dict(WD).get(2026)
    prank = 1 + sum(1 for y, x in WD if x >= peak and y != 2026)
    pprev = max(x for y, x in WD if y != 2026)
    pprev_y = max(y for y, x in WD if x == pprev and y != 2026)
    cut = S[name]["cut_at"]
    cut_txt = f"{int(cut.split('-')[1])} {MON[int(cut.split('-')[0]) - 1]}"
    dr = v["days"]["rank"]
    peak_promoted = (prank == 1 and dr["value"] != 1)

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
            f'in {v["record_from"]}, but the station moved {_moves}, so they are '
            f'not one continuous site.</p>')
    else:
        station_note = ""
    reloc = ""
    rank_txt = ("the most on record" if dr["value"] == 1
                else f'{ordn(dr["value"])} of {dr["of_years"]}')
    rank_cap = f"2026 is {rank_txt} for hot days.{reloc}"

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
    rank_clause = ("more than in any summer on its record" if dr["value"] == 1
                   else f"{ordn(dr['value'])} of its {dr['of_years']} summers")
    if mult_ok:
        head = (f"{name} used to get {base:.0f} hot day{'s' if round(base) != 1 else ''} "
                f"by this point in the summer. This year: {now}, "
                + ("more than in any summer on its record."
                   if dr["value"] == 1
                   else f"which is {rank_clause}."))
    else:
        head = (f"{name} has had {now} hot days by this point in the summer, "
                f"{rank_clause}.")

    # THE PEAK CARRIES ITS OWN RANK. Seven cities have peak == record, so
    # the sentence branches rather than being templated.
    if prank == 1 and dr["value"] == 1:
        peak_cap = (f"The hottest day of {name}'s year, to the same date. "
                    f"<strong>2026 is the hottest on this record too</strong>, at "
                    f"{peak}&nbsp;&deg;C. Both the count and the peak are records "
                    f"here, which is not true everywhere: a count and a peak are "
                    f"separate claims and each carries its own rank.")
    elif peak_promoted:
        # Editor counted it: "11th of 79" three times and 39.9 C three times on
        # one page. I had told them this was fixed. It was changed and it still
        # said the same thing, which is not the same as fixed. The promoted
        # line above carries the claim; this caption describes the chart and
        # adds the one fact not stated anywhere else, the previous best.
        peak_cap = (f"The hottest day of {name}'s summer, to the same date, "
                    f"with 2026 marked. The previous best was "
                    f"{pprev}&nbsp;&deg;C in {pprev_y}.")
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
                    f"recorded</strong>, at {peak}&nbsp;&deg;C, while the count "
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
            f'<div class="seclab">And the nights</div>'
            f'{bars(NI, max(x for _, x in NI) or 1)}'
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
            f'<div class="seclab">And the nights</div>'
            f'{bars(NI, max(x for _, x in NI) or 1)}'
            # "at or above 20 C" drops the MINIMUM and reads as a night that
            # reached 20, which nearly every summer night does. The metric is
            # nights whose minimum never falls below it. The loose phrasing was
            # on the two pages that also quote a night rank, so it was where a
            # wrong reading cost most. And the night rank now uses the day
            # rank's grammar, four lines above it on the same page.
            f'<p class="cap">{v["nights_2026"]} night'
            f'{"" if v["nights_2026"] == 1 else "s"} so far that never dropped '
            f'below 20&nbsp;&deg;C, against {nbase:.1f} in a typical 1961-1990 '
            f'summer by this date. That is {ordn(nrank["value"])} of its '
            f'{nrank["of_years"]} summers.</p>')

    # The unit rows ARE the comparison, drawn. Leaving the baseline row in
    # place and withholding only the arithmetic would have kept the defect
    # and hidden it better: two rows of blocks side by side say "nine times"
    # whether or not the page prints the number.
    if mult_ok:
        unit_rows = (
            f'<div class="urow"><span class="uk">By this date in a typical<br>'
            f'summer of 1961-1990</span>'
            f'<span class="ug">{units(base)}</span><span class="un">{base:.1f}</span></div>'
            f'<div class="urow"><span class="uk">By this date<br>this summer</span>'
            f'<span class="ug">{units(now, True)}</span><span class="un">{now}</span></div>')
    else:
        unit_rows = (
            f'<div class="urow"><span class="uk">By this date<br>this summer</span>'
            f'<span class="ug">{units(now, True)}</span><span class="un">{now}</span></div>')

    # Sits with the unit rows, which is what it qualifies, rather than under
    # the chart three sections down. The year count in heat's own note is
    # theirs and I do not restate it; record_from is a field and says the
    # same thing without a second arithmetic.
    mult_note = ("" if mult_ok else
                 f'<p class="cap"><strong>No 1961-1990 comparison is shown for '
                 f'{name}.</strong> This thermometer starts in '
                 f'{v["record_from"]}, so that baseline would cover only its warmer '
                 f'final years, and the figure would look like every other city\'s '
                 f'while meaning something weaker. The count and the rank are '
                 f'measured and stand.</p>')

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
                 f'recorded. A count and a peak are different claims and neither '
                 f'borrows the other\'s rank.</p>')

    # The method moves out from under the headline and down to the chart it
    # describes, and "95th percentile" becomes a thing a reader can picture.
    # One summer day in twenty IS the 95th percentile, said so it can be used.
    method = (f'<p class="cap">Hot here means {th}&nbsp;&deg;C or above, a level '
              f'about one summer day in twenty used to reach at this station '
              f'between 1971 and 2000. The bar has not moved; the number of days '
              f'clearing it has. Every year is counted to {cut_txt}, so a '
              f'part-finished summer is never set against complete ones.</p>')

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
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{name}: {now} hot days so far this summer">
<meta name="twitter:description" content="{head}">
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}{CSS}</style></head><body><main>
{site_masthead("../", active="heat")}
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">{name} &middot; {S[name]['station']} &middot; to {cut_txt} 2026</span></div>

<h1>{head}</h1>
{station_note}
{peak_lead}

<div class="rows">{unit_rows}</div>
{mult_note}

<div class="seclab">Every summer on this thermometer</div>
<div class="grid"><span class="gk">Hot days<em>above {th} &deg;C</em></span>
<span>{bars(D, top)}</span></div>
<p class="cap">{rank_cap}</p>
{method}

{night_block}

<div class="seclab">And the hottest day of each summer</div>
{line(WD, mark_year=2026, ring_year=None if prank == 1 else pprev_y)}
<p class="cap">{peak_cap}</p>

<div class="src">
<span>{S[name]['source']}, {S[name]['station']}, daily minimum and maximum</span>
<span style="text-align:right">to {v['counted_to']}</span>
<!-- Kristjan's ruling, 2026-08-07: show the state per city rather than
     verify quietly or hedge across the set. Three different facts and the
     reader gets whichever is true of their city. Generated by heat from
     the station history, never typed here, so a city moving from unchecked
     to checked-and-clean improves the page with no copy change. -->
<span>{v['station_disclosure']}</span>
<span style="text-align:right">station history</span>
<span>Hot days, this station's own 95th percentile of July-August maxima, 1971 to 2000</span>
<span style="text-align:right">{th} &deg;C</span>
<!-- Same defect editor found in the prose, in the line that DEFINES the
     metric. 'At or above 20' drops the minimum and describes a night that
     reached 20, which nearly every summer night does. -->
<span>Hot nights, ETCCDI index TR, daily minimum never below 20.0 &deg;C</span>
<span style="text-align:right">not chosen by us</span>
</div>
<p style="margin-top:26px"><a class="back" href="index.html">All {len(C)} cities</a></p>
</main></body></html>"""
    check_constraints(name, html, night_block, v.get("page_constraints", {}))
    if not mult_ok:
        check_no_baseline_comparison(name, head + unit_rows + mult_note + rank_cap)
    out = R / f"docs/heat/{slug(name)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    built.append(name)
    if gated:
        notes.append(f"{name}: night-gated")
    if name in NO_MULT:
        notes.append(f"{name}: no day multiple")
    if prank == 1:
        notes.append(f"{name}: peak is also a record")

print(f"built {len(built)} city pages")
for n in notes:
    print("  ", n)
