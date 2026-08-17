"""The country page: two columns, one instrument each.

Design chat's build under D-030. The Fire chat owns the data and the
methodology and signs off on the rendered result; nothing in here knows
what a baseline gate is or how a perimeter is mapped.

## Why two columns rather than two sections

The two headline numbers are not one measurement at two zoom levels.
Detections are a rate, seen from orbit, daily. Burnt area is a stock,
mapped from perimeters, weekly, and it lands in the week it is mapped
rather than the week it burned. Giving each instrument a column means
nothing has to say so in a caveat: the split is the layout.

Each column runs compare on top, decompose below. The top row answers
"is this unusual", the bottom row answers "what is it made of".

## The constraints that shaped this, all from the owning channel

Both multiples are stated and they are NEVER adjacent and never in one
frame. The week multiple lives under FIRMS, the year multiple under the
area instrument, each beneath its own baseline. Across the live set they
diverge hard in both directions (Algeria 1.9x on the week against 14.2x
on the year; Botswana 5.9x against 0.4x), and that divergence is the
product, but only if a reader never sees the two side by side and reads
one as a correction of the other. There is deliberately no summary line.

No annotation states a cause. The February window recurs in 2019, 2021
and 2025 and 2026 is the largest of them, which is a pattern and is
sourced; calling it pastoral burning would be an inference. The
attribution tag is the only place on this page where a causal claim
belongs.

No El Nino framing anywhere in the lead. Most countries here are tagged
pending and both Amazon boundaries are currently under half their normal
burn, so a page that opened on ENSO would be wrong in a way every
individual number on it would survive. `pending` renders at the same
weight as the other two tags, because making its absence look like an
omission is the cheapest way to imply a link.

The named source is read per country. 33 of 45 resolve to GWIS and 12 to
EFFIS, so a literal would name a European instrument for Canadian fires.

`as_of` is shown, `lag_days` is not: publishing the lag invites
arithmetic the date already answers.

The weekly cell runs to week 52, not to the current week. The empty
right-hand stretch is the content, because it turns "the season is not
half over" from a claim into a visible quantity.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                          # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,  # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)

# D-076: no entry for a null tag. "attribution pending" was the code's
# default fallback, so it rendered on nearly every page and told the
# reader only that we had not looked, which is not their problem.
# events.json now emits null rather than "pending", so every lookup here
# must tolerate a missing key and render NOTHING rather than a word.
TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked"}
TAG_SLUG = {"enso": "loaded", "non_enso": "notlink"}


def _chip(tag) -> str:
    """The attribution chip, or nothing at all."""
    if not tag or tag not in TAG_TEXT:
        return ""
    return f'<span class="tag tag-{TAG_SLUG[tag]}">{h(TAG_TEXT[tag])}</span>'


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def emphasis(value: float, baseline: float) -> str:
    """Channel hue when the datum clears its own baseline, ink when not.

    D-043 requirement 2: the system must be equally capable of showing
    "this is within historical range", and a chart that can only look
    alarming has stopped being an instrument. Botswana is the case that
    exposed this. Its year is 0.4x normal, a quiet season, and it was
    rendering 105,637 ha in fire red at 40px, identical to France at
    8.9x. The number said unremarkable and the page said emergency.

    This is not colour carrying magnitude, which D-016 amendment 4
    reserves for the diverging anomaly scale. It is a threshold: the
    channel hue is spent only where the datum is above the baseline it
    is being measured against. Below it, the figure is ink and the
    reader gets a quiet page for a quiet season, which is the whole
    point of being trusted on the loud ones.
    """
    return "var(--fire)" if baseline and value >= baseline else "var(--ink)"


def _halo(cls: str, x: float, y: float, text: str, anchor: str = "start",
          fill: str = "var(--ink-soft)", weight: str = "") -> str:
    """An in-plot label. Always haloed (D-023 as extended by D-026)."""
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="{anchor}" fill="{fill}"{w}>{h(text)}</text>')


def _same_week_bars(hist: dict, now: int, mean: float, year: int) -> str:
    """Compare: this week against the same week in every year."""
    years = sorted(hist) + [year]
    vals = [hist[y] for y in sorted(hist)] + [now]
    W, H, PAD_B, PAD_T = 420, 168, 24, 26
    hi = max(vals + [mean]) * 1.14
    n = len(vals)
    slot = W / n
    bw = min(slot * 0.64, 22.0)

    def Y(v):
        return H - PAD_B - (v / hi) * (H - PAD_B - PAD_T)

    out = []
    for i, (y, v) in enumerate(zip(years, vals)):
        cx = slot * (i + 0.5)
        cur = y == year
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" '
                   f'width="{bw:.1f}" height="{max(H - PAD_B - Y(v), 1.2):.1f}" '
                   f'fill="{emphasis(v, mean) if cur else "var(--rule-45)"}"/>')
    my = Y(mean)
    out.append(f'<line x1="0" y1="{my:.1f}" x2="{W}" y2="{my:.1f}" '
               f'stroke="var(--ink-soft)" stroke-width="1" '
               f'stroke-dasharray="4 4"/>')
    out.append(_halo("cx-s", 2, my - 6, f"same-week mean {mean:,.0f}"))
    out.append(_halo("cx-s", 0, H - 6, str(years[0])))
    out.append(_halo("cx-s", W, H - 6, str(year), anchor="end"))
    out.append(_halo("cx-b", W, Y(vals[-1]) - 7, f"{now:,}", anchor="end",
                     fill=emphasis(now, mean), weight="600"))
    # COUNT WHAT WAS COMPARED; NEVER NAME A START YEAR. This said "every
    # year since {years[0]}", which renders as 2012 and asserts a
    # continuous fourteen-year span the baseline does not have: 2022 has
    # no SNPP science archive over most windows and is excluded on
    # purpose, so thirteen years are compared. Wherever the missing year
    # would have outranked the current week, "every year since" is wrong
    # rather than merely loose. Fire found it and it is the same defect
    # they had already fixed in the visible headline.
    #
    # WHY IT SURVIVED TWO INSPECTIONS, mine included, and this is the part
    # worth remembering: years[0] is DERIVED from the series, so it wore
    # the shape of the corrected pattern. Deriving a value does not make
    # the sentence built on it true. It only makes a wrong claim
    # recompute itself. "Derive, do not hardcode" is necessary and not
    # sufficient.
    #
    # Hardcoding 13 would be wrong too: the excluded year is 2021 in some
    # windows and 2022 in others, because the exclusion follows the
    # defective dates and the window rolls daily. Count the series.
    return (f'<svg viewBox="0 0 {W} {H}" class="ch" role="img" '
            f'aria-label="Detections in the same week, {len(years)} years '
            f'compared">' + "".join(out) + "</svg>")


def _daily_bars(daily: dict, mean: float) -> str:
    """Decompose: the seven days inside this week."""
    items = sorted(daily.items())
    if not items:
        return ""
    W, H, PAD_B, PAD_T = 420, 150, 24, 26
    normal = mean / 7.0
    hi = max(list(daily.values()) + [normal]) * 1.16
    n = len(items)
    slot = W / n
    bw = min(slot * 0.56, 30.0)

    def Y(v):
        return H - PAD_B - (v / hi) * (H - PAD_B - PAD_T)

    out = []
    for i, (d, v) in enumerate(items):
        cx = slot * (i + 0.5)
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" '
                   f'width="{bw:.1f}" height="{max(H - PAD_B - Y(v), 1.2):.1f}" '
                   f'fill="var(--fire)"/>')
        out.append(_halo("cx-s", cx, H - 6, d[-2:], anchor="middle"))
    ny = Y(normal)
    out.append(f'<line x1="0" y1="{ny:.1f}" x2="{W}" y2="{ny:.1f}" '
               f'stroke="var(--ink-soft)" stroke-width="1" '
               f'stroke-dasharray="4 4"/>')
    # Named for what it is, not for what it would be convenient to call
    # it. This line is the same-week mean divided by seven, so calling it
    # a "normal day" asserts that fire is spread evenly across a week.
    # It is not: fire is bursty, which is the whole reason this strip is
    # worth drawing, so the flat-day label both misdescribed the line and
    # inflated every ratio measured against it. A real daily climatology
    # is computable from the full-year baseline build and will replace
    # this once the owning channel emits it.
    out.append(_halo("cx-s", 2, ny - 6,
                     f"one seventh of a normal week, {normal:,.0f}"))
    return (f'<svg viewBox="0 0 {W} {H}" class="ch" role="img" '
            f'aria-label="Detections day by day this week">'
            + "".join(out) + "</svg>")


def _cumulative(years: dict, cur_year: int, hue: str) -> str:
    """Compare: every season since the record began, this one in hue."""
    W, H, PAD_L, PAD_R, PAD_T, PAD_B = 420, 190, 46, 46, 20, 26
    ymax = max(max(w.values()) for w in years.values()) * 1.08

    def axis(v):
        """Compact, because the gutter is fixed and the range is not.

        Botswana burns millions of hectares where France burns tens of
        thousands, so a thousands-only format produced "2,815k", which
        was wider than the gutter and rendered as ",815k" with the
        leading digit outside the viewBox. A clipped number is worse
        than a rounded one: it looks like a value rather than a bug.
        """
        if v >= 1_000_000:
            return f"{v / 1_000_000:,.1f}M"
        if v >= 10_000:
            return f"{v / 1000:,.0f}k"
        return f"{v:,.0f}"

    def X(w):
        return PAD_L + (w - 1) / 51 * (W - PAD_L - PAD_R)

    def Y(v):
        return H - PAD_B - v / ymax * (H - PAD_T - PAD_B)

    out = []
    for v in (0, ymax / 2):
        out.append(f'<line x1="{PAD_L}" y1="{Y(v):.1f}" x2="{W - PAD_R}" '
                   f'y2="{Y(v):.1f}" stroke="var(--rule)" stroke-width="0.7"/>')
        out.append(_halo("cx-s", PAD_L - 5, Y(v) + 4, axis(v), anchor="end"))
    for i, m in ((1, "Jan"), (27, "Jul"), (48, "Dec")):
        out.append(_halo("cx-s", X(i), H - 6, m, anchor="middle"))

    prev = [y for y in years if y != cur_year]
    record = max(prev, key=lambda y: max(years[y].values())) if prev else None
    for y in sorted(prev):
        pts = " ".join(f"{X(w):.1f},{Y(v):.1f}"
                       for w, v in sorted(years[y].items()))
        out.append(f'<polyline points="{pts}" fill="none" '
                   f'stroke="var(--rule)" stroke-width="1.1"/>')
    if record:
        rv = max(years[record].values())
        out.append(f'<line x1="{PAD_L}" y1="{Y(rv):.1f}" x2="{W - PAD_R}" '
                   f'y2="{Y(rv):.1f}" stroke="var(--ink-faint)" '
                   f'stroke-width="1" stroke-dasharray="3 3"/>')
        out.append(_halo("cx-s", PAD_L + 2, Y(rv) - 6,
                         f"previous record, {record}: {rv:,.0f} ha"))
    cw = sorted(years[cur_year].items())
    pts = " ".join(f"{X(w):.1f},{Y(v):.1f}" for w, v in cw)
    out.append(f'<polyline points="{pts}" fill="none" stroke="{hue}" '
               f'stroke-width="2.4"/>')
    lw, lv = cw[-1]
    out.append(f'<circle cx="{X(lw):.1f}" cy="{Y(lv):.1f}" r="3.4" '
               f'fill="{hue}"/>')
    out.append(_halo("cx-b", X(lw) + 7, Y(lv) - 6, str(cur_year),
                     fill=hue, weight="600"))
    return (f'<svg viewBox="0 0 {W} {H}" class="ch" role="img" '
            f'aria-label="Cumulative burnt area by week, every season">'
            + "".join(out) + "</svg>")


def _weekly_area(weeks: dict, cur_year: int, hue: str) -> str:
    """Decompose, and the reason this cell runs to week 52.

    The empty stretch to the right of the current week is the content:
    it turns "the season is not half over" into a quantity a reader can
    see rather than a sentence they have to believe.

    Annotations state patterns only, never causes.
    """
    W, H, PAD_T, PAD_B = 420, 168, 30, 26
    order = sorted(weeks)
    inc = {}
    prev = 0.0
    for w in order:
        inc[w] = max(0.0, weeks[w] - prev)
        prev = weeks[w]
    if not inc:
        return ""
    hi = max(inc.values()) * 1.30
    slot = W / 52.0
    bw = max(slot * 0.62, 1.6)

    def Y(v):
        return H - PAD_B - (v / hi) * (H - PAD_B - PAD_T)

    out = []
    for w, v in inc.items():
        cx = slot * (w - 0.5)
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" '
                   f'width="{bw:.1f}" height="{max(H - PAD_B - Y(v), 0.8):.1f}" '
                   f'fill="var(--fire)"/>')
    # Anchor the outermost month labels inward. Centring them put half of
    # "Jan" and half of "Dec" outside the viewBox, so the axis read "an"
    # and "De": a clipped label looks like a typo rather than a bug.
    for i, m in ((1, "Jan"), (14, "Apr"), (27, "Jul"), (40, "Oct"), (52, "Dec")):
        x = slot * (i - 0.5)
        anchor = "start" if i == 1 else "end" if i == 52 else "middle"
        x = 0.0 if i == 1 else W if i == 52 else x
        out.append(_halo("cx-s", x, H - 6, m, anchor=anchor))

    peak = max(inc, key=lambda w: inc[w])
    px = slot * (peak - 0.5)
    out.append(_halo("cx-b", px - 6, Y(inc[peak]) - 16,
                     f"{inc[peak]:,.0f} ha in week {peak}", anchor="end",
                     fill=hue, weight="600"))
    out.append(_halo("cx-s", px - 6, Y(inc[peak]) - 4,
                     f"{len(order)} weeks in, {52 - max(order)} still to come",
                     anchor="end"))
    early = [w for w in inc if w <= 12]
    if early:
        ew = max(early, key=lambda w: inc[w])
        span = [w for w in early if inc[w] > inc[ew] * 0.25]
        tot = sum(inc[w] for w in span)
        if tot > 0 and ew != peak:
            out.append(_halo("cx-s", slot * (ew - 0.5) + 6,
                             Y(inc[ew]) - 6,
                             f"weeks {min(span)} to {max(span)}, "
                             f"{tot:,.0f} ha"))
    return (f'<svg viewBox="0 0 {W} {H}" class="ch" role="img" '
            f'aria-label="Burnt area week by week this year, to week 52">'
            + "".join(out) + "</svg>")


def render(piece: dict, root_prefix: str = "../../") -> str:
    """One country page from a validated piece dict."""
    det, area = piece["detections"], piece.get("area")
    tag = piece.get("attribution")
    year = piece["year"]

    left = f"""
      <div class="col">
        <p class="cell-lab">This week &middot; {h(piece["window_pretty"])}</p>
        <p class="hero" style="color:{"var(--ink)" if piece.get("volume_context") and not piece.get("anomalous") else emphasis(det["multiple"], 1.0)}">
          {det["multiple"]:.1f}&times;</p>
        <p class="cell-sub">active-fire detections against the same-week
          mean of {det["mean"]:,.0f}, {det["baseline_span"]}<br>
          {h(det["instrument"])}<br>
          <span class="verdict">{h(piece["verdict"])}</span></p>
        <p class="ch-lab">Against the same week, every year</p>
        {_same_week_bars(det["hist"], det["count"], det["mean"], year)}
        <p class="ch-note">Each year&rsquo;s detections in the same window
          of the year, same sensor throughout.</p>
        <p class="ch-lab">The seven days</p>
        {_daily_bars(det["daily"], det["mean"])}
        <p class="ch-note">{h(det["daily_note"])}</p>
      </div>"""

    if area:
        right = f"""
      <div class="col">
        <p class="cell-lab">This year &middot; since 1 January</p>
        <p class="hero" style="color:{emphasis(area["multiple"], 1.0)}">
          {area["area_ha"]:,} <span class="unit">ha</span></p>
        <p class="cell-sub">burnt area mapped, {area["multiple"]:.1f}&times;
          the average for this point in the year<br>
          {h(area["instrument"])}, week {area["week"]},
          through {h(area["as_of"])}</p>
        <p class="ch-lab">Cumulative, every season since {area["first_year"]}</p>
        {_cumulative(area["years"], year, emphasis(area["multiple"], 1.0))}
        <p class="ch-note">{h(area["cumulative_note"])}</p>
        <p class="ch-lab">Week by week, {year} so far</p>
        {_weekly_area(area["years"][year], year, emphasis(area["multiple"], 1.0))}
        <p class="ch-note">{h(area["weekly_note"])}</p>
      </div>"""
    else:
        right = ('<div class="col"><p class="cell-lab">This year</p>'
                 '<p class="cell-sub">No mapped burnt-area series is '
                 'published for this country, so only the detection '
                 'instrument appears here. The two are never converted '
                 'into one another.</p></div>')

    elsewhere = "".join(
        f'<a class="ew-row" href="{h(o["href"])}">'
        f'<span class="ew-stat">{h(o["stat"])}</span>'
        f'<span class="ew-name">{h(o["region"])}</span>'
        f'<span class="ew-claim">{h(o["title"])}</span>'
        f'{_chip(o.get("attribution"))}</a>'
        for o in piece.get("elsewhere", []))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<!-- ALL THREE LINES LAND TOGETHER OR NONE DO. A page that declares
     summary_large_image and supplies no image is worse than one that
     declares nothing: the platform reserves the space and renders it
     empty. That is why heat was worse off than fires despite looking
     better configured, 36 pages declaring the card with nothing to show
     against fires declaring nothing and degrading to a text card.
     The house card is generic and beats an empty slot; per-page cards
     wait for the citable chart, and fires is the worst case for them
     because its figures change daily, so any card here needs its window
     stamped on the face rather than only regenerated. -->
<meta property="og:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- INDEXABLE SINCE D-183, 2026-08-17. The unlisted period ENDED here, it
     did not fail to exist: fires/SPEC.md line 11 records that unlisted was
     chosen with Kristjan on 2026-07-25, and the spec defined it by two
     testable conditions, no front-page link and no promotion. Both had
     already lapsed. The front page links fires in the masthead and links
     Cuba, the United Kingdom and Croatia by absolute URL, and socials
     promoted fire content all week at Kristjan's request, so the tag was
     the last surviving piece of a decision superseded everywhere else.

     NOT THE SAME EVENT AS D-172, and Fire asked for the distinction. Crops
     inherited its tag by copy and nobody decided it; fires chose its own
     and the choice ran out. A future audit finding the spec should read
     these as opposites rather than as one lapse.

     THE OTHER HALF IS fires/build_page.py LINE 340, which is Fire's. This
     tag lives in two files and the split is INVISIBLE in rendered output,
     so neither half is done until both are, and whoever verifies counts
     pages rather than checking one. -->
<title>{h(piece["region"])} fires | {h(SITE_NAME)}</title>
<style>
{T.font_faces_css(root_prefix + "fonts/")}
:root {{
{T.css_variables()}
}}
@media (prefers-color-scheme: dark) {{ :root {{
{T.css_variables(dark=True)}
}} }}
:root[data-theme="dark"] {{
{T.css_variables(dark=True)}
}}
* {{ box-sizing: border-box; }}
:root {{ --shell-max: 980px; --shell-pad: 28px; }}
body {{ margin: 0; background: var(--paper); color: var(--ink);
  font-family: "{T.FONT_PROSE}", Georgia, serif; font-size: 16.5px;
  line-height: 1.55; }}
main {{ max-width: 980px; margin: 0 auto; padding: 26px 28px 80px; }}
{SITE_MASTHEAD_CSS}
.mono, .cell-lab, .ch-lab, .cell-sub, .hero, .rail, .tag, .ew-stat,
.cx-s, .cx-b, .foot {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint);
  font-family: "{T.FONT_DATA}", ui-monospace, monospace; margin: 24px 0 10px; }}
h1 {{ font-size: 40px; font-weight: 500; line-height: 1.13;
  letter-spacing: -0.018em; margin: 0 0 16px; max-width: 18ch;
  text-wrap: balance; }}
.stand {{ color: var(--ink-soft); max-width: 52ch; margin: 0 0 34px; }}

.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
.col {{ border-top: 3px solid var(--ink); padding: 14px 32px 0 0; }}
.col + .col {{ border-left: 1px solid var(--rule); padding: 14px 0 0 32px; }}
.cell-lab {{ font-size: 10.5px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); margin: 0 0 12px; }}
.hero {{ font-size: 40px; font-weight: 600; letter-spacing: -0.02em;
  color: var(--fire); margin: 0; line-height: 1;
  font-variant-numeric: tabular-nums; }}
.hero .unit {{ font-size: 20px; font-weight: 500; }}
.verdict {{ color: var(--ink); }}
.cell-sub {{ font-size: 11.5px; color: var(--ink-soft); margin: 12px 0 0;
  line-height: 1.62; }}
.ch-lab {{ font-size: 10px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); margin: 26px 0 6px;
  padding-bottom: 6px; border-bottom: 1px solid var(--rule); }}
.ch {{ width: 100%; height: auto; display: block; }}
/* Every in-plot label is haloed, once, here. Bar heights move weekly, so
   an annotation that clears the data today will not next week. */
.ch text {{ paint-order: stroke; stroke: var(--paper); stroke-width: 2.5;
  stroke-linejoin: round; }}
.cx-s {{ font-size: 9.5px; }}
.cx-b {{ font-size: 11.5px; }}
.ch-note {{ font-size: 12.5px; color: var(--ink-soft); margin: 8px 0 0;
  max-width: 46ch; line-height: 1.5; }}

.tagrow {{ display: flex; justify-content: flex-end; margin: 26px 0 0; }}
/* All three states at one weight. Making pending quieter is the cheapest
   way to imply a link the tag is explicitly declining to make. */
.tag {{ font-size: 10.5px; letter-spacing: 0.04em; padding: 3px 8px;
  white-space: nowrap; }}
.tag-loaded {{ background: var(--tag-loaded-bg); color: var(--tag-loaded-fg); }}
.tag-notlink {{ background: var(--tag-notlink-bg); color: var(--tag-notlink-fg); }}
.tag-pending {{ background: var(--tag-pending-bg); color: var(--tag-pending-fg); }}

.lower {{ display: grid; grid-template-columns: 1.55fr 1fr; gap: 44px;
  margin-top: 44px; border-top: 2.4px solid var(--rule-45); padding-top: 26px; }}
.lower h2 {{ font-size: 19px; font-weight: 500; margin: 0 0 8px;
  padding-bottom: 8px; border-bottom: 2px solid var(--ink); }}
.lower h2 + p {{ margin-top: 10px; }}
.lower p {{ color: var(--ink-soft); max-width: 56ch; }}
.lower section + section {{ margin-top: 28px; }}
.rail {{ font-size: 11.5px; line-height: 1.6; color: var(--ink-soft); }}
.rail h3 {{ font-size: 9.5px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); font-weight: 400;
  margin: 0 0 6px; }}
.rail div + div {{ margin-top: 20px; padding-top: 16px;
  border-top: 1px solid var(--rule); }}

.ew {{ margin-top: 52px; border-top: 3px solid var(--ink); padding-top: 8px; }}
.ew-lab {{ font-size: 10px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); margin: 6px 0 0;
  font-family: "{T.FONT_DATA}", ui-monospace, monospace; }}
.ew-row {{ display: grid; grid-template-columns: 4.6rem 1fr auto;
  gap: 16px; align-items: baseline; padding: 13px 0;
  border-bottom: 1px solid var(--rule); text-decoration: none;
  color: inherit; }}
.ew-row:hover .ew-claim {{ text-decoration: underline; }}
.ew-stat {{ font-size: 21px; font-weight: 600; color: var(--fire);
  font-variant-numeric: tabular-nums; }}
.ew-name {{ font-size: 17px; font-weight: 500; }}
.ew-claim {{ color: var(--ink-soft); font-size: 14.5px; }}
.foot {{ margin-top: 46px; padding-top: 14px;
  border-top: 1px solid var(--ink); font-size: 11.5px;
  color: var(--ink-faint); display: flex; justify-content: space-between;
  gap: 20px; flex-wrap: wrap; }}
@media (max-width: 760px) {{
  .grid, .lower {{ grid-template-columns: 1fr; }}
  .col {{ padding: 14px 0 0; }}
  .col + .col {{ border-left: none; border-top: 3px solid var(--ink);
    margin-top: 32px; padding-left: 0; }}
  h1 {{ font-size: 29px; max-width: none; }}
  .ew-row {{ grid-template-columns: 3.8rem 1fr; }}
  .ew-row .tag {{ grid-column: 2; justify-self: start; margin-top: 5px; }}
}}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="fire")}
<main>
  <p class="eyebrow">{h(piece["region"])} &middot;
     {h(piece["window_pretty"])}</p>
  <h1>{h(piece["claim"])}</h1>
  <p class="stand">{h(piece["standfirst"])}</p>

  <div class="grid">{left}{right}</div>

  {f'<div class="tagrow">{_chip(tag)}</div>' if _chip(tag) else ''}

  <div class="lower">
    <div>
      <section><h2>What this is</h2><p>{h(piece["what_this_is"])}</p></section>
      <section><h2>What this is not</h2>
        <p>{h(piece["what_this_is_not"])}</p></section>
    </div>
    <div class="rail">
      <div><h3>Baseline</h3>{piece["rail_baseline"]}</div>
      <div><h3>Instruments</h3>{piece["rail_instruments"]}</div>
      {f'<div><h3>Attribution</h3>{piece["rail_attribution"]}</div>'
        if (piece.get("rail_attribution") or "").strip() else ''}
      <div><h3>Revision</h3>{piece["rail_revision"]}</div>
    </div>
  </div>

  <div class="ew">
    <p class="ew-lab">The same week elsewhere</p>
    {elsewhere}
  </div>

  <div class="foot">
    <span>{h(AUTHOR_NAME)} ({year}). {h(SITE_NAME)}, Fires.
      <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a></span>
    <span>{h(piece["region"])} &middot; week {area["week"] if area else ""}</span>
  </div>
</main>
</body>
</html>
"""
