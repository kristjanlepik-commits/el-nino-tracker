"""A crops country page: every region of it that is at a record low.

Kristjan asked for "country sub-pages for crops" and the index is
already grouped by country, so one page per country holding its regions'
detail satisfies that literally and gives the index one link per group
rather than one per row. 41 pages this dekad rather than 81.

## What is on it that the index cannot carry

The index shows a country's regions as a collapsed list of names and
z-scores, because eighty-one rows of chart would be unreadable. This
page is where the detail goes:

- **Each region against its own 26 years.** `series` is emitted per
  region as of b809f28, which is the thing this page was blocked on. It
  was built once without it and said so on its face rather than
  inventing a history to decorate a five-field row.
- **Every region of the country on one axis**, the marked one included,
  which is the only comparison the payload supports and the one that
  answers "is this region an outlier here, or is the whole country
  like this".

## The claim shapes are enumerated, not sampled

CRO signs off on the template plus every distinct claim shape it can
emit, and a new shape inside an approved template is a new sign-off
rather than a variation. That rule exists because "driest" reached a
live page inside a template that had already been approved.

This page emits: two `statement` shapes (rank-1 and not-rank-1), times
a driver line present or absent, times a qualifiers list empty or not.
Eight in total, and `claim_shapes()` prints them so the sign-off
conversation is a list rather than a page-by-page read.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)
from templates.crops_region import _fmt                        # noqa: E402
from templates.crops_severity import (severity_block,          # noqa: E402
                                      SEVERITY_CSS)


def slugify(name: str) -> str:
    import re
    s = re.sub(r"[^\w\s-]", "", name.lower().replace("'", "")).strip()
    return re.sub(r"[-\s]+", "-", s)


def _series_chart(series: dict, this_year: str = "2026") -> str:
    """One region against its own record, year by year.

    Bars rather than a line: these are discrete annual observations of
    the same dekad, not a continuous signal, and a line would imply
    values between them that were never measured.

    The current year takes the channel hue ONLY when it is the lowest in
    the series. A record year drawn in crop and an ordinary year drawn
    in ink is the calibration rule applied to a bar, and it means the
    colour carries the finding rather than the recency.
    """
    if not series:
        return ""
    years = sorted(series)
    vals = [series[y] for y in years]
    lo, hi = min(vals + [0.0]), max(vals + [0.0])
    span = max(hi - lo, 0.6)
    W, H, PAD_T, PAD_B, PAD_L, PAD_R = 660, 132, 16, 24, 8, 8
    slot = (W - PAD_L - PAD_R) / len(years)
    bw = min(slot * 0.62, 15.0)
    worst = min(vals)

    def Y(v):
        return PAD_T + (hi - v) / (hi - lo + span * 0.12) * (H - PAD_T - PAD_B)

    zero = Y(0.0)
    out = [f'<line x1="{PAD_L}" y1="{zero:.1f}" x2="{W - PAD_R}" '
           f'y2="{zero:.1f}" stroke="var(--rule)" stroke-width="1"/>']
    for i, y in enumerate(years):
        v = series[y]
        cx = PAD_L + slot * (i + 0.5)
        top, bot = (Y(v), zero) if v < 0 else (zero, Y(v))
        is_now = (y == this_year)
        hue = ("var(--crop)" if (is_now and v <= worst) else
               "var(--ink)" if is_now else "var(--ink-faint)")
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{min(top, bot):.1f}" '
                   f'width="{bw:.1f}" height="{abs(bot - top):.1f}" '
                   f'fill="{hue}"/>')
    for i, y in enumerate(years):
        if y in (years[0], years[-1]):
            cx = PAD_L + slot * (i + 0.5)
            anchor = "start" if y == years[0] else "end"
            out.append(f'<text class="sc-x" x="{cx:.1f}" y="{H - 6}" '
                       f'text-anchor="{anchor}">{h(y)}</text>')
    return (f'<svg class="sc" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="This region in every year of the record for the '
            f'same point in the season">' + "".join(out) + '</svg>')


# Instruments are ordered so the two that actually dissent sit together
# and temperature does not read as an equal fifth voice. CRO measured
# it across the 80 rendered rank-1 regions: temperature is in the worst
# third 55 times and the best third 4 times, so it mostly moves with
# vegetation and will rarely disagree. The disagreement lives in water
# satisfaction and rainfall, which is the only thing that justifies
# showing five layers rather than one.
LAYER_ORDER = ["Vegetation, cumulative", "Vegetation, current",
               "Water satisfaction", "Rainfall, 3-month",
               "Soil moisture", "Temperature"]


def _tercile(rank, of):
    """Where a reading sits in its own record, in thirds.

    Thirds rather than a percentile because the sentence has to be
    readable, and because 26 observations do not support finer.
    """
    if not rank or not of:
        return None
    f = (rank - 1) / max(of - 1, 1)
    return "worst" if f < 1 / 3 else ("middle" if f < 2 / 3 else "best")


def _pattern_sentence(instruments) -> str:
    """What the layers say TOGETHER, which is the only reason to show five.

    Descriptive and never causal. "Vegetation at its lowest while
    rainfall sits in its best third" states a relationship between two
    measurements; anything with "because" in it is the line "driest"
    crossed, and five instruments on one page is precisely the invitation
    to assemble a cause from them.

    Built from ranks only. It says where each instrument sits in its own
    record and stops.
    """
    by = {i["name"]: i for i in instruments if i.get("available")}
    veg = by.get("Vegetation, cumulative") or by.get("Vegetation, current")
    if not veg:
        return ""
    water = [by[n] for n in ("Water satisfaction", "Rainfall, 3-month")
             if n in by]
    if veg.get("rank") == 1:
        lead = "The canopy is at its lowest on record here"
    else:
        t = _tercile(veg.get("rank"), veg.get("of"))
        lead = {"worst": "The canopy is in its worst third",
                "middle": "The canopy is in the middle of its range",
                "best": "The canopy is in its best third"}.get(
                    t, "The canopy is measured")
    if not water:
        return lead + "."
    ts = {_tercile(w.get("rank"), w.get("of")) for w in water}
    names = " and ".join(w["name"].split(",")[0].lower() for w in water)
    if ts == {"worst"}:
        # The Chad case: everything poor, but only the canopy at a
        # record. Saying "all bad" would lose that distinction.
        tail = (f", while {names} are also in their worst third without "
                f"being records" if veg.get("rank") == 1
                else f", as are {names}")
    elif ts == {"best"}:
        tail = f", while {names} sit in their best third"
    elif ts == {"middle"}:
        tail = f", while {names} sit mid-range"
    else:
        parts = [f"{w['name'].split(',')[0].lower()} is in its "
                 f"{_tercile(w.get('rank'), w.get('of'))} third"
                 for w in water]
        tail = ", while " + " and ".join(parts)
    return lead + tail + "."


def _rank_track(rank, of, record=False) -> str:
    """Where this reading sits in its own record, drawn rather than said.

    Kristjan's ask: "how bad is it" for the five layers, visually. The
    numbers alone do not answer it, because 6th of 26 requires a reader
    to do arithmetic before it means anything, and five rows of that is
    five sums.

    Country instruments carry no series, so this cannot draw a history
    the way the region rows do. What it can draw is POSITION: the track
    is the instrument's own 26 observations, worst at the left, and the
    mark is where this year falls. That is honest about being a rank
    rather than a magnitude, which matters because this channel has
    already confused the two once.

    Direction comes from `rank`, which is rank-by-worseness, so it is
    correct for temperature where high is bad even while the statement
    text beside it currently is not.
    """
    if not rank or not of or of < 2:
        return ""
    W, H = 96, 12
    x = 2 + (rank - 1) / (of - 1) * (W - 4)
    hue = "var(--crop)" if record else "var(--ink)"
    return (f'<svg class="rt" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{rank} of {of}, worst at left">'
            f'<line x1="2" y1="{H/2}" x2="{W-2}" y2="{H/2}" '
            f'stroke="var(--rule)" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="{x:.1f}" cy="{H/2}" r="3.6" fill="{hue}" '
            f'stroke="var(--paper)" stroke-width="1.4"/></svg>')


def _layers_block(instruments) -> str:
    """All five, plus any absent one, as a grid under the pattern.

    Kristjan asked for all five visible. Showing everything and
    weighting everything equally are different decisions, so the
    pattern sentence above carries the finding and this is the receipt.

    An ABSENT instrument is rendered with the channel's own
    `absent_because` verbatim, never a string mapped from a code here.
    "Has not reported for this dekad yet" and "is not defined for this
    region at this point in the season" are opposite claims about
    whether the number will ever arrive, and a reader given the wrong
    one concludes something about the instrument rather than the place.
    """
    if not instruments:
        return ""
    order = {n: i for i, n in enumerate(LAYER_ORDER)}
    rows = []
    for ins in sorted(instruments, key=lambda i: order.get(i["name"], 99)):
        name = h(ins["name"])
        if not ins.get("available"):
            rows.append(
                f'<div class="ly ly-out"><span class="lyn">{name}</span>'
                f'<span class="lyv">not reported</span><span></span>'
                f'<span class="lys">{h(ins.get("absent_because", ""))}</span>'
                f'</div>')
            continue
        val = _fmt(ins.get("value"), ins.get("unit"))
        # The channel hue marks a record, nothing else. A rank of 6 of
        # 26 is poor and is not news, and colouring it would spend the
        # hue on the thing the page spent all day learning not to.
        cls = " ly-rec" if ins.get("rank") == 1 else ""
        rows.append(
            f'<div class="ly{cls}"><span class="lyn">{name}</span>'
            f'<span class="lyv">{h(val)}</span>'
            f'{_rank_track(ins.get("rank"), ins.get("of"), ins.get("rank") == 1)}'
            f'<span class="lys">{h(ins.get("statement", ""))}</span></div>')
    return ('<p class="lyleg">Each track is that instrument&rsquo;s own 26 '
            'years, worst on the left.</p>'
            '<div class="lys-wrap">' + "".join(rows) + '</div>')


def _range_rows(regions, unit="z-score") -> str:
    """Every region: its own 26-year range, with this year marked on it.

    REPLACES a single-axis dot strip that Kristjan could not read, and
    he was right about all three faults. It had no axis, so the numbers
    meant nothing. It used filled versus open dots to carry rank-1
    membership with nothing on the page saying so. And it answered
    "which region is lowest" when the question a reader actually has is
    "how bad is that".

    So each region gets its own row: the light bar is the full spread of
    its 25 previous years, and the mark is this year against it. A mark
    sitting at the left end of a wide bar and a mark at the left end of a
    narrow bar are different findings, and the old strip could not show
    the difference because it drew no history at all.

    Same device as the null envelope and the chance baseline: draw the
    range, then put the observation inside it. Without the range a value
    is a magnitude; inside it, it is a result.
    """
    rows = []
    for r in regions:
        ser = r.get("series") or {}
        if not ser:
            continue
        prior = [v for y, v in ser.items() if y != "2026"]
        if not prior:
            continue
        rows.append((r, min(prior), max(prior), r.get("value")))
    if not rows:
        return ""
    lo = min(min(x[1] for x in rows), min(x[3] for x in rows))
    hi = max(max(x[2] for x in rows), max(x[3] for x in rows))
    pad = max((hi - lo) * 0.06, 0.15)
    lo, hi = lo - pad, hi + pad

    W, RH, PAD_L, PAD_R, TOP = 660, 21.0, 150, 16, 26
    H = TOP + RH * len(rows) + 26

    def X(v):
        return PAD_L + (v - lo) / (hi - lo) * (W - PAD_L - PAD_R)

    out = []
    # Axis first, and labelled, because the old one had none.
    zx = X(0.0)
    if lo <= 0 <= hi:
        out.append(f'<line x1="{zx:.1f}" y1="{TOP - 8:.1f}" x2="{zx:.1f}" '
                   f'y2="{H - 22:.1f}" stroke="var(--rule)" stroke-width="1"/>')
        out.append(f'<text class="rr-ax" x="{zx:.1f}" y="{TOP - 13:.1f}" '
                   f'text-anchor="middle">its normal</text>')
    out.append(f'<text class="rr-ax" x="{PAD_L}" y="{H - 6:.1f}">worse</text>')
    out.append(f'<text class="rr-ax" x="{W - PAD_R}" y="{H - 6:.1f}" '
               f'text-anchor="end">better</text>')

    for i, (r, mn, mx, v) in enumerate(rows):
        y = TOP + RH * i + RH / 2
        out.append(f'<text class="rr-n" x="0" y="{y + 3.5:.1f}">'
                   f'{h(r["region"])}</text>')
        out.append(f'<rect x="{X(mn):.1f}" y="{y - 4:.1f}" '
                   f'width="{max(X(mx) - X(mn), 1.5):.1f}" height="8" '
                   f'fill="var(--paper-sunk)"/>')
        rec = (r.get("rank") == 1)
        hue = "var(--crop)" if rec else "var(--ink)"
        out.append(f'<circle cx="{X(v):.1f}" cy="{y:.1f}" r="4.2" '
                   f'fill="{hue}" stroke="var(--paper)" stroke-width="1.6"/>')
    return (f'<svg class="rr" viewBox="0 0 {W} {H:.0f}" role="img" '
            f'aria-label="Each region of this country: the spread of its '
            f'previous 25 years, with this year marked">'
            + "".join(out) + '</svg>')


def claim_shapes(country: dict) -> list:
    """Every distinct sentence shape this page can emit, for sign-off.

    CRO's gate is the template plus every claim shape, and showing them
    a list is both cheaper and closer to where the failure lives than
    showing them pages. "Driest" was a shape, not a page.
    """
    import re
    seen = {}
    # ONLY the regions this page actually renders. It iterated every
    # region of the country, including the ones the page never shows,
    # and reported "Nth lowest of N" as an emitted shape when these
    # pages carry rank-1 regions exclusively and therefore only ever
    # emit "lowest of N". That sent CRO a gate covering sentences the
    # template cannot produce, which is the opposite failure to the one
    # the gate exists for and just as useless: a sign-off is worthless
    # if it is not on the thing that ships.
    for r in [x for x in (country.get("regions") or []) if x.get("rank") == 1]:
        # Collapse the ordinal suffix too. "1st", "2nd" and "4th lowest"
        # are one shape, and leaving them distinct inflated the list
        # from four shapes to ten, which would have sent CRO a longer
        # sign-off than the template actually needs.
        st = re.sub(r"\bN(?:st|nd|rd|th)\b", "Nth",
                    re.sub(r"[-+]?\d[\d,.]*", "N",
                           re.sub(r"\b(?:19|20)\d\d\b", "YYYY",
                                  r.get("statement") or "")))
        key = (st, bool(r.get("driver") == "water"),
               bool(r.get("qualifiers")))
        seen.setdefault(key, r.get("region"))
    out = [{"statement": k[0], "driver_line": k[1], "qualifiers": k[2],
            "example": v} for k, v in seen.items()]

    # The instrument layers add their own shapes and they must be in
    # this list, because CRO verifies MY enumeration rather than
    # supplying one: a list they write is a list of what the data can
    # do, and the point of the last correction was that those differ
    # from what the page emits.
    #
    # Two, per CRO. An instrument statement, identical in construction
    # across all five layers, and an absence sentence rendered verbatim.
    for ins in (country.get("instruments") or []):
        if ins.get("available"):
            st = re.sub(r"\bN(?:st|nd|rd|th)\b", "Nth",
                        re.sub(r"[-+]?\d[\d,.]*", "N",
                               re.sub(r"\b(?:19|20)\d\d\b", "YYYY",
                                      ins.get("statement") or "")))
            key = ("instrument: " + st, False, False)
        else:
            key = ("absence: " + (ins.get("absent_because") or ""), False, False)
        if key not in seen:
            seen[key] = ins.get("name")
            out.append({"statement": key[0], "driver_line": False,
                        "qualifiers": False, "example": seen[key]})
    return out


def _region_block(r: dict, all_regions: list, driver: str) -> str:
    """One region. `driver` is the REGION's, never the country's.

    This read the country field and it is the Cairo fault one level
    down: a country property worn by a region. Namibia is water-driven
    as a country; Hardap is not, at 0.15 against the 0.30 the test
    requires, and Hardap was one of my own two named examples for this
    shape, which is how CRO found it.

    Not a stray case either: 677 of 2,122 regions, 32 percent, have a
    driver differing from their country's. A third of every region row
    would have carried a claim that does not hold there. The word in the
    sentence is "here", and it has to be true of here.
    """
    q = r.get("qualifiers") or []
    quals = ("".join(f'<li>{h(x)}</li>' for x in q)
             if q else "")
    drv = ('<p class="rgdrv">Vegetation here usually tracks water '
           'availability.</p>' if r.get("driver") == "water" else "")
    return f"""
      <section class="rg" id="{h(slugify(r['region']))}">
        <h2>{h(r['region'])}</h2>
        <p class="rgval">{h(_fmt(r.get('value'), 'z-score'))}
          <span class="rgstate">{h(r.get('statement', ''))}</span></p>
        {drv}
        {_series_chart(r.get('series') or {})}
        <p class="rgbasis">{h(r.get('basis', ''))}</p>
        {f'<ul class="rgq">{quals}</ul>' if quals else ''}
      </section>"""


def render(country: dict, root_prefix: str = "../../") -> str:
    regions = sorted((country.get("regions") or []),
                     key=lambda r: r.get("value", 0))
    lows = [r for r in regions if r.get("rank") == 1]
    name = country["place"]
    units = country.get("crop_units")
    cb = country.get("chance_baseline") or {}

    # The count sentence carries its own baseline or it does not appear.
    # Four channels reached the same finding today: a count of
    # threshold-crossings is not a finding on its own.
    if cb.get("recent_max") is not None:
        stand = (f"{len(lows)} of {units} crop regions in {name} are at "
                 f"their worst on record for this point in the season. "
                 f"Its highest in any previous year was "
                 f"{cb['recent_max']}, on a recent average of "
                 f"{cb['recent_mean']:g}.")
    else:
        stand = (f"{len(lows)} of {units} crop regions in {name} are at "
                 f"their worst on record for this point in the season.")

    blocks = "".join(_region_block(r, regions, r.get("driver"))
                     for r in lows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{h(name)} | Crops | {h(SITE_NAME)}</title>
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
{SEVERITY_CSS}
.eyebrow, .rgval, .foot, .sc text, .rgbasis {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:31px; font-weight:500; line-height:1.18; margin:0 0 12px;
  letter-spacing:-0.015em; }}
.stand {{ color:var(--ink-soft); max-width:60ch; margin:0; }}
.rg {{ margin-top:38px; padding-top:14px;
  border-top:1px solid var(--rule); }}
.rg h2 {{ font-size:19px; font-weight:600; margin:0 0 4px; }}
.rgval {{ font-size:26px; color:var(--crop); margin:0; font-weight:600;
  font-variant-numeric:tabular-nums; }}
.rgstate {{ display:block; font-size:12.5px; color:var(--ink-soft);
  font-weight:400; margin-top:3px; }}
.rgdrv {{ margin:8px 0 0; font-size:13.5px; color:var(--ink-faint); }}
.sc {{ width:100%; height:auto; display:block; margin:12px 0 2px; }}
.sc-x {{ font-size:10px; fill:var(--ink-faint); }}
.rgbasis {{ margin:4px 0 0; font-size:11px; color:var(--ink-faint); }}
.rgq {{ margin:8px 0 0; padding-left:18px; font-size:13.5px;
  color:var(--ink-soft); max-width:62ch; }}
.peers {{ margin-top:14px; }}
.rr {{ width:100%; height:auto; display:block; }}
.rr text {{ font-family:"{T.FONT_DATA}",monospace; }}
.rr-n {{ font-size:11.5px; fill:var(--ink); }}
.rr-ax {{ font-size:10px; fill:var(--ink-faint); }}
.pat {{ margin:6px 0 0; font-size:18px; line-height:1.4; max-width:56ch; }}
/* The grid is the receipt, so it is quiet. The pattern sentence above
   carries the finding: showing all five and weighting all five equally
   are different decisions and Kristjan asked for the first. */
.lys-wrap {{ margin-top:16px; border-top:1px solid var(--rule); }}
.lyleg {{ margin:14px 0 0; font-size:11.5px; color:var(--ink-faint);
  font-family:"{T.FONT_DATA}",monospace; }}
.rt {{ width:96px; height:12px; display:block; align-self:center; }}
.ly {{ display:grid; grid-template-columns:11.5rem 5rem 96px 1fr; gap:12px;
  padding:9px 0; border-bottom:1px solid var(--rule); align-items:baseline; }}
.lyn {{ font-size:14px; }}
.lyv {{ font-family:"{T.FONT_DATA}",monospace; font-size:14.5px;
  font-variant-numeric:tabular-nums; text-align:right; }}
.lys {{ font-size:12.5px; color:var(--ink-faint); }}
/* Hue marks a RECORD and nothing else. 6th of 26 is poor and is not
   news; colouring it would spend the channel colour on exactly what
   this page spent the day learning not to. */
.ly-rec .lyv {{ color:var(--crop); font-weight:600; }}
/* An absent instrument is dimmed, not hidden, and carries the channel's
   own reason. Hiding it would let a reader conclude we do not measure
   it here, which is a different claim from "it has not arrived yet". */
.ly-out .lyn, .ly-out .lyv {{ color:var(--ink-faint); }}
.ly-out .lyv {{ font-style:italic; }}
@media (max-width:600px) {{
  .ly {{ grid-template-columns:1fr auto; }}
  .rt {{ grid-column:1 / -1; }}
  .lys {{ grid-column:1 / -1; }} }}
.note {{ margin:16px 0 0; font-size:13.5px; color:var(--ink-soft);
  max-width:64ch; }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow"><a href="{h(root_prefix)}crops/">Crops</a>
    &middot; dekad {h(country.get('dekad', ''))}</p>
  <h1>{h(name)}</h1>
  <p class="stand">{h(stand)}</p>

  <p class="eyebrow" style="margin-top:34px">How bad is it, against this
    country&rsquo;s own record</p>
  {severity_block(name, country.get("severity") or {})}

  <p class="eyebrow" style="margin-top:34px">What the instruments say</p>
  <p class="pat">{h(_pattern_sentence(country.get("instruments") or []))}</p>
  {_layers_block(country.get("instruments") or [])}
  <p class="note">Five instruments, each against its own 26 years for
    this point in the season. They are shown together because they
    disagree: across the regions on this site, roughly a quarter have
    vegetation at a record low while water or rainfall sits in its best
    third. This page reports where each one sits and does not say what
    caused what.</p>

  <p class="eyebrow" style="margin-top:34px">Every region of {h(name)},
    worst to least</p>
  <p class="secsub">Each bar is the full spread of that region&rsquo;s
    previous 25 years at this point in the season. The dot is this year.
    A dot at the left of a wide bar and a dot at the left of a narrow
    bar are different findings, which is why the history is drawn rather
    than described.</p>
  <div class="peers">{_range_rows(regions)}</div>
  <p class="note">Regions in colour are at their worst on record. The
    rest are placed on the same scale so a single deep region inside an
    otherwise ordinary country reads differently from a country where
    the whole distribution has moved.</p>

  {blocks}

  <p class="note">This measurement is of the crop canopy and not of what
    stressed it: heat, drought, disease and late planting are not
    separable here, which is why no claim on this page names a cause.</p>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
  </div>
</main>
</body>
</html>
"""
