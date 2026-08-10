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

MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]

# The rungs the page draws. +1.0, +1.5 and +2.0 have reached the display
# bound and left the ladder (D-115/D-116). Read from the payload rather
# than assumed: a rung that is not emitted simply does not render.
RUNGS = [("9715_>2.5", "+2.5 °C", "1997 / 2015 magnitude"),
         ("record_>3.0", "+3.0 °C", "beyond the observed record"),
         ("record_>3.5", "+3.5 °C", "far beyond it")]


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
    out = ""
    for key, lab, note in RUNGS:
        mid = _clamp((headline.get(key) or {}).get("mid"))
        if mid is None:
            continue
        out += (f'<div class="r wide"><span class="yr">{lab}</span>'
                f'{_bar(mid)}<span class="v">{mid}<span class="u">%</span></span>'
                f'<span class="note">{h(note)}</span></div>')
    return out


def _provenance(fetched, brief_date):
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
        '<div>+1.0, +1.5 and +2.0 reached the bound and left the ladder. '
        'Their full history stays in the archive.</div>'
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
           briefs_href="../briefs/", asset_prefix="../"):
    phys = fetched.get("physical_state") or {}
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
<style>
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
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="elnino",
               methodology_href=root_prefix + "methodology.html",
               briefs_href=briefs_href)}
<main>
<div class="eyebrow">El Ni&ntilde;o 2026-27 &middot; week of {h(di)} &middot;
 <a href="{h(briefs_href)}{h(di)}/">as published</a></div>
<h1>How big does this one get?</h1>
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
 alt="Nino 3.4 ONI for 2026-27 against 1997, 2015, 2023 and 2025, with the
 SEAS5 forecast median and spread carried forward to February 2027."></figure>
</div>

<div class="sec"><h2>05 &middot; Provenance</h2>
<p class="lede">What each source said, when it said it, and every caveat
that governs a figure above. One register rather than three.</p>
{_provenance(fetched, brief_date)}</div>

<div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.
 <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
 &middot; <a href="{h(briefs_href)}">every issue, immutable</a></div>
</main>
</body>
</html>
"""
