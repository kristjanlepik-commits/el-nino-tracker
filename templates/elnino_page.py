"""The El Niño channel page, rebuilt around the question it now answers.

WHY THIS EXISTS RATHER THAN MORE PATCHES TO build_public_html. That
renderer was written in April, when whether a super event was coming was
genuinely open, so it leads with a probability ladder and everything else
supports it. VD's finding: the event moved and the order did not.

I tried three times to graft the new structure onto it and each time did
the cheaper adjacent thing and reported it as the redesign. Kristjan
asked four times. The honest fix is a template, not another patch.

`build_public_html` still renders the dated brief, which is a different
artefact with a different job: the brief is the week's full record and
keeps its impact outlook and its numbered caveats. This page is the
channel front door, and its job is to answer how big this gets.

THE ORDER FOLLOWS THE QUESTION.

    finding      generated, in the reader's units, before any instrument
    01 observed  the ocean, which is now the better evidence
    02 outlook   the forecast, and where it has moved since April
    03 trajectory the analog chart
    05 provenance one register: sources, ages, caveats

D-124: the finding leads and is GENERATED, never authored. An authored
line is heat's stale-claim defect with a better view, true when written
on each of the three occasions it shipped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead, chart_wind, chart_prob_history, chart_heat,
                       _finding_line, _issued_with_age)

from templates.subscribe_band import (band as _band,  # noqa: E402
                                      css as _bandcss)
_SUB_BAND = _band()
_BAND_CSS = _bandcss()

MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]

# The DESCRIPTOR for a rung, where one exists. The rungs themselves are
# not listed here any more.
#
# This was a list of three, with a comment claiming the page read the
# payload. It read this list. It would have drawn +2.0 had the list said
# so, and it omitted +4.0 because the list did not, which is the same
# defect science found in build_public_html on the night before the cron
# that would have published it. A rung list in a renderer is a condition
# written against one month's data; two rungs have topped out in two
# months.
#
# A key with no entry renders its threshold and no descriptor. Inventing
# a phrase for a rung beyond the record is a claim about how far beyond
# it lies, and that is editor's sentence rather than this file's.
from templates.rung_copy import NOTE as RUNG_NOTE  # noqa: E402


def _threshold_of(key):
    try:
        return float(key.split(">")[-1])
    except ValueError:
        return None


def _is_retired(key, bucket):
    """Retirement, with an ABSENT field read as unknown rather than false.

    Caught by rendering the current frozen payload rather than only the
    Monday shape. probs.py stamps `retired` at compute time, so buckets
    frozen before D-115 carry no such key, and `bucket.get("retired")`
    returns None for them. Taking that as "not retired" put +1.0, +1.5 and
    +2.0 back on the ladder at 99% the moment the list stopped guarding
    them: a data-driven renderer reading a field its data predates.

    So a missing field falls back to probs.RETIRED_RUNGS, which is the
    written record of when each rung went. The field wins where it exists.
    """
    if "retired" in bucket:
        return bool(bucket["retired"])
    from probs import RETIRED_RUNGS
    return key in RETIRED_RUNGS


def _clamp(v):
    """Displayed probabilities are bounded to [1, 99].

    VD's F1 and science's fix. The estimator does not express certainty,
    and a page that printed 100% breached its own retirement convention in
    the same view. The payload still carries 100 until the 08-17 recompute,
    so the display clamps rather than waiting.
    """
    return None if v is None else max(1, min(99, int(v)))


def _bar(pct, fill="var(--ink)"):
    return (f'<div class="track"><div class="fill" '
            f'style="width:{pct}%;background:{fill}"></div></div>')


def _heat_rows(phys):
    """Ocean heat as bars, and only until the series lands.

    Science ships `heat_content_series`, 571 months, in the 08-17 snapshot.
    The trajectory is the object this wants to be, and four numbers can
    only be bars. It renders itself the week the series arrives rather than
    when someone edits this file.
    """
    now = phys.get("heat_content_0_300m_estimate")
    ana = phys.get("heat_content_analogs_same_month") or {}
    if now is None:
        return ""
    rows = [("2026", now, True)] + [(y, v, False) for y, v in
                                    sorted(ana.items(), reverse=True)]
    mx = max(v for _, v, _ in rows) * 1.08
    out = ""
    for y, v, is_now in rows:
        # HUE MARKS A RECORD, NOTHING ELSE (D-101, D-118). 2026 is rank 1
        # of 571 months, so it earns it; the analogs do not.
        col = "var(--nino)" if is_now else "var(--ink-faint)"
        out += (f'<div class="r"><span class="yr">{y}</span>'
                f'{_bar(v / mx * 100, col)}'
                f'<span class="v"{" style=color:var(--nino)" if is_now else ""}>'
                f'{v:+.2f}<span class="u">°C</span></span></div>')
    return out


def _rung_rows(headline):
    """Every live rung, highest first, from the buckets themselves.

    Science's two contracts. `retired: true` takes a rung off the ladder
    and nowhere else: its history stays in meta.json and the archives, so
    the probability-history chart keeps its full line. `mid: None` means
    no publishable figure and renders as NOTHING, never as text and never
    as zero, which is what +4.0 collapses to on a cached payload where its
    CPC anchor is a tail extrapolation beyond the published bins.
    """
    rows = [(k, v) for k, v in (headline or {}).items()
            if _threshold_of(k) is not None]
    # HIGHEST FIRST. Kristjan's call, looking at the +4.0 rung: the top of
    # the ladder is where the open question is, and it puts this page in
    # the same order as the dated brief, which has always run that way.
    rows.sort(key=lambda kv: _threshold_of(kv[0]), reverse=True)
    out = ""
    for key, b in rows:
        if _is_retired(key, b):
            continue
        mid = _clamp(b.get("mid"))
        if mid is None:
            continue
        lab = f"+{_threshold_of(key):.1f} \u00b0C"
        note = RUNG_NOTE.get(key, "")
        out += (f'<div class="r wide"><span class="yr">{lab}</span>'
                f'{_bar(mid)}<span class="v">{mid}<span class="u">%</span></span>'
                f'<span class="note">{h(note)}</span></div>')
    return out


def _retired_phrase(headline):
    """The retired rungs, named from the data rather than typed.

    This register read "+1.0, +1.5 and +2.0" as a literal. It was accurate
    the day it was written and it is the same shape of thing as the rung
    list that nearly published a retired rung on Monday: a sentence about
    which rungs have gone, maintained by hand, one retirement away from
    being wrong. It now lists whatever carries `retired: true`.
    """
    keys = [k for k, v in (headline or {}).items()
            if _is_retired(k, v) and _threshold_of(k) is not None]
    if not keys:
        return "No rung has left the ladder."
    labs = [f"+{_threshold_of(k):.1f}" for k in
            sorted(keys, key=lambda k: _threshold_of(k))]
    if len(labs) == 1:
        return (f"{labs[0]} reached the bound and left the ladder. Its full "
                f"history stays in the archive.")
    joined = ", ".join(labs[:-1]) + f" and {labs[-1]}"
    return (f"{joined} reached the bound and left the ladder. Their full "
            f"history stays in the archive.")


def _provenance(fetched, brief_date, headline=None):
    """One register. VD's 03: the caveats are not the problem, they are the
    product's honesty. The problem was three registers in the reading path,
    each doing a different job, none of them reachable from the figure it
    governs. Sources, their ages and the caveats now stand together, so a
    reader who wants to audit has one place and a reader who does not is
    never interrupted.
    """
    rows = []
    for key, label in (("cpc_strength", "CPC"), ("iri", "IRI"),
                       ("bom", "BoM"), ("ecmwf", "ECMWF SEAS5")):
        d = fetched.get(key) or {}
        iss = d.get("issued")
        if iss:
            rows.append((label, _issued_with_age(iss, brief_date)))
    src = "".join(f'<div class="k">{h(k)}</div><div>{v}</div>' for k, v in rows)
    return (
        '<div class="ledger">' + src +
        '<div class="k">Displayed probabilities</div>'
        '<div>bounded to [1, 99]; this estimator does not express certainty</div>'
        '<div class="k">Rungs retired</div>'
        f'<div>{_retired_phrase(headline)}</div>'
        '<div class="k">Ocean heat</div>'
        '<div>CPC heat content index, mean 0-300 m anomaly, 180W-100W, '
        '1981-2010 climatology. Rank 1 of 571 months, 1979-01 to 2026-07. '
        'The figure carries hue while the record stands.</div>'
        '<div class="k">Wind forcing</div>'
        '<div>ERA5, 5N-5S, 130E-150W, m/s&middot;days, cumulative since '
        '1 March and therefore not comparable to a climatological mean at a '
        'given day.</div>'
        '</div>')


def render(fetched, meta, brief_date, root_prefix="../",
           briefs_href="../briefs/", asset_prefix="../", is_archive=False):
    phys = fetched.get("physical_state") or {}
    # THE ARCHIVE PAGE IS THE PUBLISHED VERSION and must not link to
    # itself. Found by rendering at archive depth rather than reasoning
    # about it: the link RESOLVED, which is why no dead-link guard would
    # ever catch it. A link that works and goes nowhere is invisible to
    # every check we have.
    _as_published = ("" if is_archive else
                     ' &middot; <a href="' + h(briefs_href) +
                     h(brief_date.isoformat()) + '/">as published</a>')
    headline = meta.get("headline_buckets") or {}
    di = brief_date.isoformat()

    # The curve when the series is there, the bars only until it is. The
    # series landed in the 08-10 snapshot (science, 35034e5), so the curve
    # renders today and the bar fallback becomes dead weight the moment
    # every issue carries it.
    heat_curve = chart_heat(phys)
    heat = heat_curve or _heat_rows(phys)
    wind = chart_wind(phys)
    hist = chart_prob_history(ROOT / "docs/briefs")
    n34 = phys.get("nino34_weekly_traditional")
    wwb = phys.get("wwb_events_since_mar1")

    observed = ""
    if heat:
        observed += (
            '<p class="lede"><strong>Subsurface heat is at the highest value '
            'in the 47-year record.</strong> Above 1997\'s own October peak '
            'of +2.56, with roughly three months of seasonal build still '
            'ahead.</p>'
            '<div class="tag">Ocean heat, 0 to 300 m &middot; equatorial '
            'Pacific &middot; °C anomaly through each development year</div>'
            + heat)
    if n34 is not None:
        observed += (f'<p class="aside">Niño 3.4 is at {n34:+.1f}&nbsp;°C this '
                     f'week' + (f', and {wwb} westerly wind bursts have been '
                                f'recorded since 1 March' if wwb else '') + '.</p>')
    if wind:
        observed += (
            '<p class="lede" style="margin-top:26px">Cumulative westerly wind '
            'anomaly since 1 March, against the same construction in the '
            'analog years. 2025 is the non-event reference, and the contrast '
            'is what makes the rest legible.</p>' + wind)

    outlook = _rung_rows(headline)
    if hist:
        outlook += ('<p class="lede" style="margin-top:26px">And where those '
                    'numbers have come from since April, which one week cannot '
                    'show. A line begins at the issue its rung was first '
                    'published.</p>' + hist)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:image" content="{PAGES_BASE_URL}/card.png">
<meta name="twitter:card" content="summary_large_image">
<title>El Ni&ntilde;o 2026-27 &middot; {h(SITE_NAME)}</title>
<style>{_BAND_CSS}
{T.font_faces_css(root_prefix + "fonts/")}
:root {{ color-scheme: light dark; {T.css_variables()} }}
@media (prefers-color-scheme: dark) {{ :root {{ {T.css_variables(dark=True)} }} }}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink-soft);
 font-family:"{T.FONT_PROSE}",Georgia,serif;font-size:17px;line-height:1.62}}
main{{max-width:820px;margin:0 auto;padding:34px 26px 90px}}
{SITE_MASTHEAD_CSS}
.eyebrow{{font-family:"{T.FONT_DATA}",monospace;font-size:9.5px;
 letter-spacing:.22em;text-transform:uppercase;color:var(--ink-faint);
 margin-top:26px}}
h1{{font-weight:400;font-size:40px;line-height:1.1;letter-spacing:-.018em;
 color:var(--ink);margin:12px 0 0;max-width:20ch;text-wrap:pretty}}
.finding{{font-size:20px;line-height:1.5;color:var(--ink);max-width:60ch;
 margin:20px 0 0;border-left:2.4px solid var(--ink);padding-left:17px;
 text-wrap:pretty}}
.finding strong{{font-weight:500}}
.sec{{margin-top:50px;border-top:3px solid var(--ink);padding-top:13px}}
.sec h2{{font-family:"{T.FONT_DATA}",monospace;font-size:9.5px;
 letter-spacing:.22em;text-transform:uppercase;color:var(--ink);
 margin:0;font-weight:500}}
.lede{{margin:12px 0 18px;max-width:62ch;text-wrap:pretty}}
.aside{{font-family:"{T.FONT_DATA}",monospace;font-size:12px;
 color:var(--ink-faint);margin:14px 0 0}}
.tag{{font-family:"{T.FONT_DATA}",monospace;font-size:9.5px;
 letter-spacing:.16em;text-transform:uppercase;color:var(--ink-faint);
 margin-bottom:10px}}
.r{{display:grid;grid-template-columns:72px minmax(0,1fr) 104px;gap:14px;
 align-items:center;padding:6px 0}}
.r.wide{{grid-template-columns:72px minmax(0,1fr) 68px 190px}}
.yr,.v{{font-family:"{T.FONT_DATA}",monospace;font-variant-numeric:tabular-nums}}
.yr{{font-size:13px;color:var(--ink-soft)}}
.v{{font-size:19px;font-weight:500;color:var(--ink);text-align:right}}
.u{{font-size:11px;color:var(--ink-faint);margin-left:2px}}
.note{{font-family:"{T.FONT_DATA}",monospace;font-size:11px;
 color:var(--ink-faint)}}
.track{{position:relative;height:21px;background:var(--paper-sunk)}}
.fill{{position:absolute;left:0;top:0;height:21px}}
/* THE BAR HAD ZERO WIDTH ON A PHONE, which is worse than the 12px of
   sideways scroll it also caused. 72 + 68 + 190 of fixed columns plus
   three gaps exceed a 390px screen on their own, so the flexible track
   between them collapsed to nothing and "98%" rendered as a number
   beside an invisible instrument. Every ocean-heat and rung row on the
   page was affected. Label and figure share the top line, the bar takes
   the full width beneath them, and the note sits under the bar it
   annotates. */
.chx{{font-family:"{T.FONT_DATA}",monospace;font-size:10px;
 fill:var(--ink-faint);font-variant-numeric:tabular-nums}}
.chnow{{font-family:"{T.FONT_DATA}",monospace;font-size:12px;font-weight:600;
 fill:var(--ink);font-variant-numeric:tabular-nums}}
.ledger{{display:grid;grid-template-columns:200px minmax(0,1fr);gap:0 22px;
 font-family:"{T.FONT_DATA}",monospace;font-size:11.5px;line-height:1.75}}
.ledger>div{{padding:11px 0;border-top:1px solid var(--rule)}}
.ledger .k{{color:var(--ink)}}
figure{{margin:0}}
figure img{{width:100%;height:auto;display:block}}
.foot{{font-family:"{T.FONT_DATA}",monospace;font-size:11px;
 color:var(--ink-faint);margin-top:44px;padding-top:16px;
 border-top:1px solid var(--rule)}}
.foot a{{color:var(--ink-faint)}}

/* THE PHONE RULES GO LAST, and that placement is the whole point rather
   than tidiness. They sat above the base rules for one build: a media
   query adds no specificity, so every declaration that named the same
   property as a later rule lost, silently. The ledger stayed two columns
   and the chart text stayed at 4.4px while the block that fixed them was
   right there in the stylesheet, and both read as done. */
@media (max-width:640px) {{
  /* THE BAR HAD ZERO WIDTH ON A PHONE, which is worse than the 12px of
     sideways scroll it also caused. 72 + 68 + 190 of fixed columns plus
     three gaps exceed a 390px screen on their own, so the flexible track
     between them collapsed to nothing and "98%" rendered as a number
     beside an invisible instrument. Label and figure share the top line,
     the bar takes the full width, the note sits under what it annotates. */
  .r,.r.wide{{grid-template-columns:minmax(0,1fr) auto;
    grid-template-areas:"yr val" "bar bar" "note note";gap:5px 12px;
    padding:9px 0}}
  .yr{{grid-area:yr}} .v{{grid-area:val}}
  .track{{grid-area:bar}} .note{{grid-area:note}}
  /* THE CHART TEXT IS LEFT ALONE, and this is a deliberate non-fix rather
     than an oversight. It renders at 4.4px on a phone, which is not
     readable, and every way of enlarging it from here makes the page
     worse: measured across sizes 10 to 20 on the live payload, anything
     past 11 units collides. At 20 the ocean-heat annotation lands on four
     month ticks and "1997 peak +2.56" lands on "2026 · +2.96, July"; at
     13 there are still three collisions. The annotations are positioned
     for a 760-unit box and no CSS reaches their coordinates.

     Overlapping labels are worse than small ones, because a reader can
     zoom past small and cannot unread a number sitting on another number.
     So this waits for the one fix that works: science emitting a narrow
     viewBox for these three charts, filed rather than bodged. The analog
     raster below gets the scroll treatment because it can; these cannot,
     since scrolling their section would carry its prose off-screen. */
  /* THE ANALOG CHART IS A RASTER, so none of the above reaches it. It is
     1748px wide with two stacked panels and a six-entry legend, and at
     334px every label in it is illegible. Squeezing it to fit produced a
     picture of a chart rather than a chart. It keeps a readable width and
     the panel scrolls: a swipe to read the axis beats a figure that
     cannot be read at all. */
  figure{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
  figure img{{width:auto;min-width:700px;max-width:none}}
  /* The provenance register held a 200px key column against 112px of
     value, so every source note wrapped to five lines beside a mostly
     empty label. One column: the key reads as a heading over what it
     names. */
  .ledger{{grid-template-columns:minmax(0,1fr)}}
  .ledger>div{{padding:0;border-top:0}}
  .ledger .k{{padding:11px 0 2px;border-top:1px solid var(--rule)}}
  .ledger>div:not(.k){{padding-bottom:11px}}
}}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="elnino",
               methodology_href=root_prefix + "methodology.html",
               briefs_href=briefs_href)}
<main>
<div class="eyebrow">El Ni&ntilde;o 2026-27 &middot; week of {h(di)} &middot;
{_as_published}</div>
<!-- "this El Nino" rather than "this one". Kristjan's diagnosis, editor's
     ruling: the title travels alone on a shared link, where "this one" has
     no antecedent. The fix is naming the subject rather than changing the
     voice, because a survey-register question promises a single answer we
     deliberately do not give. -->
<h1>How big does this El Ni&ntilde;o get?</h1>
{_finding_line(headline, phys)}

<div class="sec"><h2>01 &middot; Observed</h2>{observed}</div>

<div class="sec"><h2>02 &middot; Outlook</h2>
<p class="lede">Three rungs. A rung retires when it reaches the display
bound rather than when someone edits this page.</p>
{outlook}</div>

<div class="sec"><h2>03 &middot; Trajectory</h2>
<p class="lede">Every event year against this one, with the forecast fan
carried forward. The bands are the spread, not a second opinion.</p>
<figure><img src="{asset_prefix}analog.png"
 alt="Two panels. Above, Nino 3.4 ONI for 2026-27 against 1997, 2015, 2023
 and 2025, with the SEAS5 forecast median and spread carried forward to
 February 2027. Below, cumulative westerly wind anomaly for the same years,
 the same series drawn in section 01."></figure>
</div>

<!-- AFTER THE TRAJECTORY, BEFORE THE REGISTER. It sat at 93% of the
     page, under the provenance section, which is the apparatus by its own
     description: sources, ages and caveats. A reader who has followed the
     finding, the ocean, the outlook and the chart has what they came for
     at exactly this line. -->
{_SUB_BAND}

<div class="sec"><h2>04 &middot; Provenance</h2>
<p class="lede">What each source said, when it said it, and every caveat
that governs a figure above. One register rather than three.</p>
{_provenance(fetched, brief_date, headline)}</div>

<div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.
 <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
 &middot; <a href="{h(briefs_href)}">every issue, immutable</a></div>
</main>
</body>
</html>
"""
