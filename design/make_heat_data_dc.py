"""Heat data inventory for VD's canvas, rebuilt for the 93910e8 emit.

Two files now, not one, and two instruments rather than one. ECA&D is
deleted from the pipeline rather than demoted, so the warning that used
to be in this document is gone: the file no longer exists.

Inventory only. No layout is implied.
"""
import json, html
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())
C, H = N["cities"], N["headline"]
e, MONO = html.escape, "'IBM Plex Mono', monospace"
NO_MULT = N["cities_without_day_multiple"]

rows = sorted(C.items(), key=lambda kv: (kv[1]["rank"]["value"],
                                         -(kv[1]["record_margin_nights"] or 0)))


def lab(t, rule=3):
    return (f'<div style="font-family:{MONO};font-size:9.5px;letter-spacing:.22em;'
            f'text-transform:uppercase;color:#1A1A18;border-bottom:{rule}px solid #1A1A18;'
            f'padding-bottom:10px;margin:44px 0 16px">{t}</div>')


def note(k, v):
    return (f'<div style="border-top:1px solid #C6C5C2;padding:13px 0;display:grid;'
            f'grid-template-columns:250px minmax(0,1fr);gap:24px;align-items:baseline">'
            f'<div style="font-family:{MONO};font-size:11px;color:#1A1A18">{k}</div>'
            f'<div style="font-size:15.5px;line-height:1.55;color:#3A3A36;max-width:66ch">'
            f'{e(str(v))}</div></div>')


def city_row(n, v):
    r, d = v["rank"], v.get("days", {})
    c90 = d.get("counts_per_year", {}).get("90", {})
    a, b = c90.get("b6190"), c90.get("r1125")
    mult = (f"{b/a:.1f}&times;" if d.get("multiple_available") and a
            else '<span style="color:#B32E10">omitted</span>')
    marg = (f'+{v["record_margin_nights"]}' if v["record_margin_nights"] is not None
            else '<span style="color:#6E6E67">null</span>')
    tie = ' <span style="color:#B32E10">tie</span>' if r.get("tied_with") else ""
    return (f'<tr><td style="font-weight:500;color:#1A1A18">{n}</td>'
            f'<td style="text-align:right">{v["nights_2026"]}</td>'
            f'<td style="text-align:right">{r["value"]}{tie}</td>'
            f'<td style="text-align:right;color:#6E6E67">{r["of_years"]}</td>'
            f'<td style="text-align:right">{marg}</td>'
            f'<td style="text-align:right">{d.get("days_2026",{}).get("90","-")}</td>'
            f'<td style="text-align:right;color:#6E6E67">{a if a else "-"}</td>'
            f'<td style="text-align:right">{b if b else "-"}</td>'
            f'<td style="text-align:right">{mult}</td>'
            f'<td style="color:#6E6E67">{v["source"]["who"].split(",")[0]}</td></tr>')


mars = C["Marseille"]
mday = mars["days"]["counts_per_year"]["90"]

doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="./support.js"></script></head><body><x-dc><helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Spectral:wght@400;500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#F1F0EC}}
table{{border-collapse:collapse;width:100%;font-family:{MONO};font-size:11px;
font-variant-numeric:tabular-nums}}
th{{text-align:left;font-weight:500;color:#6E6E67;font-size:9px;letter-spacing:.12em;
text-transform:uppercase;padding:0 8px 8px 0;border-bottom:2.4px solid #8E8E88}}
td{{padding:7px 8px 7px 0;border-bottom:1px solid #E0DFDA;color:#3A3A36}}</style>
</helmet>
<div style="max-width:1120px;margin:0 auto;padding:0 48px 90px;color:#3A3A36;
font-family:Spectral,serif">

<div style="padding:22px 0 12px;border-bottom:3px solid #1A1A18;display:flex;
align-items:baseline;gap:14px">
<span style="font-weight:500;font-size:22px;color:#1A1A18">The Long Swell</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.18em;
text-transform:uppercase;color:#1A1A18">Heat data inventory</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:#6E6E67;margin-left:auto">From design &middot; final emit 93910e8</span></div>

<h1 style="font-weight:400;font-size:44px;line-height:1.08;letter-spacing:-.018em;
color:#1A1A18;margin:40px 0 14px;max-width:24ch">Heat has two instruments, not one</h1>
<p style="font-size:17.5px;line-height:1.62;max-width:64ch;margin:0">
Generated from the payload, so every number here is live rather than described.
<strong style="font-weight:500;color:#1A1A18">Inventory, not a proposal.</strong>
This replaces the earlier version: ECA&amp;D has been deleted from the pipeline
rather than demoted, so the warning about never opening the cross-check file is
gone with it. All fifteen cities now sit on published commercial sources, with
nights and days from the same rows of the same record.</p>

{lab('The finding to design around')}
<div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,320px);gap:44px">
<div>
<p style="font-size:25px;line-height:1.32;color:#1A1A18;max-width:30ch;margin:0 0 14px">
Marseille is 7th of 77 on nights and has the most extreme summer of any of the
fifteen on days.</p>
<p style="font-size:16.5px;line-height:1.6;max-width:64ch;margin:0">
{mars['days']['days_2026']['90']} days above its own 90th percentile, the highest
count in the set, against {mday['b6190']} a year in 1961-1990. That is
{mday['r1125']/mday['b6190']:.1f} times its own former rate. On nights alone the
page would have called Marseille an ordinary summer.</p>
<p style="font-size:16.5px;line-height:1.6;max-width:64ch;margin:12px 0 0">
This is why the city page carries both. It is not that days add colour: it is that
one instrument was wrong about a city, and the reader has no way to know which
cities those are unless both are shown.</p>
</div>
<div style="border-left:1px solid #CFCEC7;padding-left:24px;font-family:{MONO};
font-size:11px;line-height:1.7;color:#3A3A36">
<div style="border-top:1px solid #1A1A18;padding:9px 0 11px">
<span style="color:#6E6E67">nights</span><br>rank 7 of 77, tied with 2018</div>
<div style="border-top:1px solid #C6C5C2;padding:9px 0 11px">
<span style="color:#6E6E67">days above 90th pct</span><br>43 in 2026, most of the fifteen</div>
<div style="border-top:1px solid #C6C5C2;padding:9px 0">
<span style="color:#6E6E67">the same station</span><br>{e(mars['station'])}, same rows</div>
</div></div>

{lab('The two files')}
{note('heat/data/city_nights.json', 'The current reading per city: nights, rank, day counts and thresholds, sources, and the headline with its baseline. This is what a page renders from.')}
{note('heat/data/city_series.json', 'The histories. Per city per year: window_days, full_days, usability flags, nights to the cut, nights full year, and day counts. This is what a chart draws from, and where the gaps are.')}

{lab('Two instruments, and they do not agree')}
<p style="font-size:16.5px;line-height:1.6;max-width:72ch;margin:0 0 16px">
Nights are a count against a station record. Days are a count above that station's
own 90th, 95th and 99th percentile of July-August maxima, 1971-2000. Both come from
the same station and the same rows.
<strong style="font-weight:500;color:#1A1A18">Rank order on one is not rank order on
the other</strong>, which is the whole reason to show both.</p>
<table><thead><tr><th>city</th><th style="text-align:right">nights</th>
<th style="text-align:right">rank</th><th style="text-align:right">of</th>
<th style="text-align:right">margin</th><th style="text-align:right">days 90th</th>
<th style="text-align:right">1961-90</th><th style="text-align:right">2011-25</th>
<th style="text-align:right">multiple</th><th>source</th></tr></thead>
<tbody>{"".join(city_row(n, v) for n, v in rows)}</tbody></table>
<p style="font-size:15px;line-height:1.55;max-width:70ch;margin:14px 0 0;color:#6E6E67">
<strong style="color:#1A1A18">margin</strong> is null rather than 0 where no record
was set: null means did not beat it, 0 would mean tied it.
<strong style="color:#1A1A18">tie</strong> marks a city whose 2026 equals a prior
year. <strong style="color:#1A1A18">multiple omitted</strong> is
{", ".join(NO_MULT)}: their stations opened after 1961 so the baseline is
part-length and drawn from the warmer end. The field is ABSENT rather than flagged,
so it cannot be rendered or reinstated by accident.</p>

{lab('What a renderer may not do')}
{note('tie_rule', S['tie_rule']['note'])}
{note('rank, never derived', 'Take rank from the payload. Recomputing it with a strict greater-than promotes ties to first place and would manufacture a record, taking the headline from 8 of 15 to 9 of 15.')}
{note('requires_series', C['Madrid']['rank'].get('requires_series_note', 'A rank may not be rendered without its series beneath it.'))}
{note('headline_requires_baseline', f"The count of {H['records']} may not appear without its baseline: a typical year produces {H['baseline']['typical_year_records']}, and with no trend the expected number is {H['baseline']['expected_no_trend']}.")}
{note('may_not_say', H['may_not_say'])}
{note('counted_to vs last_observation', 'Two separate fields. Sources now reach one day past the cut, and the cut is frozen through the launch because advancing it moves no rank but changes fourteen counts. The difference is visible rather than implied.')}
{note('cities_without_day_multiple_note', N['cities_without_day_multiple_note'])}
{note('the day threshold is not ours', N['day_definition']['standard_es'] + ' There is no Meteo-France equivalent, so the French thresholds are the same method with weaker verification, and that sentence must not be copied across.')}

{lab('Gaps are real, and Barcelona is the case')}
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0">
Paris no longer has a gap: the 22-year hole was an ECA&amp;D artefact and
Meteo-France has continuous coverage. <strong style="font-weight:500;color:#1A1A18">
Barcelona's are genuine</strong>, three present-runs at 1924-1927, 1938 alone, and
1944-2025. They are the Civil War and the war years, so the absence means something,
which makes it a better case than Paris ever was. Completeness bar is
{S['completeness']['bar']} over the window {e(S['completeness']['window'])}.</p>

{lab('Why the lead is not the record count')}
<p style="font-size:22px;line-height:1.35;color:#1A1A18;max-width:34ch;margin:0 0 12px">
&ldquo;{e(H['lead']['claim'])}&rdquo;</p>
<p style="font-size:16px;line-height:1.6;max-width:70ch;margin:0">
{H['lead']['in_top_10pct']} of {H['lead']['of_cities']} are in the warmest tenth of
their own record and {H['lead']['in_top_5pct']} in the warmest twentieth. The record
count can move on a data update, since Malaga leads by one night; this framing
cannot. {e(H.get('the_better_story',''))}</p>

{lab('What is NOT in the payload')}
<p style="font-size:16px;line-height:1.65;max-width:68ch;margin:0">
No standard deviation, so no z: rank and percentile only. No sub-annual detail, so
no daily or monthly values, only annual counts. No cities outside Spain and France,
and the metric does not travel north. No projection and no forecast. No population
or exposure figures, so nothing here supports a harm claim.</p>

</div></x-dc></body></html>"""
out = R / "design/review/heat-data-inventory.dc.html"
out.write_text(doc)
print(f"wrote {out} ({len(doc):,} bytes, {len(rows)} cities, "
      f"{len(NO_MULT)} without a day multiple)")
