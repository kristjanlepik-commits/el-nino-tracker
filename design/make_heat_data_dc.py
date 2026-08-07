"""Emit the heat data inventory as a .dc.html document for VD's canvas.

Plain .md at the project root does not appear in their document list, so
five earlier replies went unseen. Their canvas lists .dc.html only. Same
content as heat-data-overview.md, same generator source, different
wrapper.
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "heat/data/city_nights.json").read_text())
C, H = D["cities"], D["headline"]
M = C["Madrid"]
rows = sorted(C.items(), key=lambda kv: (kv[1]["rank"]["value"],
                                         -(kv[1]["record_margin_nights"] or 0)))
e = html.escape
MONO = "'IBM Plex Mono', monospace"

def lab(t):
    return (f'<div style="font-family:{MONO};font-size:9.5px;letter-spacing:.22em;'
            f'text-transform:uppercase;color:#1A1A18;border-bottom:3px solid #1A1A18;'
            f'padding-bottom:10px;margin:44px 0 16px">{t}</div>')

def note(k, v):
    return (f'<div style="border-top:1px solid #C6C5C2;padding:13px 0;display:grid;'
            f'grid-template-columns:230px minmax(0,1fr);gap:24px;align-items:baseline">'
            f'<div style="font-family:{MONO};font-size:11px;color:#1A1A18">{k}</div>'
            f'<div style="font-size:15.5px;line-height:1.55;color:#3A3A36;max-width:66ch">'
            f'{e(v)}</div></div>')

NULL_CELL = '<span style="color:#6E6E67">null</span>'
def _city_row(n, v):
    mg = v["record_margin_nights"]
    marg = f"+{mg}" if mg is not None else NULL_CELL
    src = v["source"]["who"].split(",")[0]
    return (f'<tr><td style="font-weight:500;color:#1A1A18">{n}</td>'
            f'<td style="text-align:right">{v["nights_2026"]}</td>'
            f'<td style="text-align:right">{v["rank"]["value"]}</td>'
            f'<td style="text-align:right;color:#6E6E67">{v["rank"]["of_years"]}</td>'
            f'<td style="text-align:right;color:#6E6E67">'
            f'{v["mean_1991_2020_to_date"]["value"]}</td>'
            f'<td style="text-align:right">{marg}</td>'
            f'<td style="color:#6E6E67">{src}</td>'
            f'<td style="color:#6E6E67">{v["as_of"]}</td></tr>')
city_rows = "".join(_city_row(n, v) for n, v in rows)

doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="./support.js"></script></head><body><x-dc><helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Spectral:wght@400;500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#F1F0EC}}
table{{border-collapse:collapse;width:100%;font-family:{MONO};font-size:11.5px;
font-variant-numeric:tabular-nums}}
th{{text-align:left;font-weight:500;color:#6E6E67;font-size:9.5px;letter-spacing:.14em;
text-transform:uppercase;padding:0 10px 8px 0;border-bottom:2.4px solid #8E8E88}}
td{{padding:7px 10px 7px 0;border-bottom:1px solid #E0DFDA;color:#3A3A36}}</style>
</helmet>
<div style="max-width:1080px;margin:0 auto;padding:0 48px 90px;color:#3A3A36;
font-family:Spectral,serif">

<div style="padding:22px 0 12px;border-bottom:3px solid #1A1A18;display:flex;
align-items:baseline;gap:14px">
<span style="font-weight:500;font-size:22px;color:#1A1A18">The Long Swell</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.18em;
text-transform:uppercase;color:#1A1A18">Heat data inventory</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:#6E6E67;margin-left:auto">From design &middot; 2026-08-06</span></div>

<h1 style="font-weight:400;font-size:44px;line-height:1.08;letter-spacing:-.018em;
color:#1A1A18;margin:40px 0 14px;max-width:22ch">What data heat actually has</h1>
<p style="font-size:17.5px;line-height:1.62;max-width:62ch;margin:0">Generated from
<span style="font-family:{MONO};font-size:15px">heat/data/city_nights.json</span>, so
every number here is the live payload rather than a description of it.
<strong style="font-weight:500;color:#1A1A18">This is an inventory, not a
proposal.</strong> No layout is implied, and my own mockup was confusing enough that
starting from the data rather than from my page is the better route.</p>

{lab('What the channel measures')}
<p style="font-size:17.5px;line-height:1.62;max-width:62ch;margin:0 0 12px">
<strong style="font-weight:500;color:#1A1A18">{e(D['definition']['name'])}</strong>:
{e(D['definition']['rule'])}. {e(D['definition']['standard'])}</p>
<p style="font-size:16px;line-height:1.6;max-width:66ch;color:#6E6E67;margin:0">
{e(D['_readme'])}</p>
<p style="font-size:16px;line-height:1.6;max-width:66ch;margin:12px 0 0">
<strong style="font-weight:500;color:#1A1A18">Coverage.</strong> {e(D['coverage_note'])}</p>
<p style="font-size:16px;line-height:1.6;max-width:66ch;margin:12px 0 0">
Attribution tag <span style="font-family:{MONO};font-size:14px">{e(D['attribution'])}</span>,
evidence basis {e(D['evidence_basis'])}. {H['records']} of {H['of_cities']} cities at an
outright record, {H['lead']['in_top_5pct']} in the warmest twentieth of their own history,
{H['lead']['in_top_10pct']} in the warmest tenth. Two sources, both permitting commercial
reuse: AEMET OpenData and Meteo-France.</p>

{lab('Three separate series per city, and only one is drawn anywhere')}
<p style="font-size:17.5px;line-height:1.62;max-width:64ch;margin:0 0 16px">The part most
likely to be missed, and probably where a better page lives. Every city carries three full
histories back to its record start.</p>
<table><thead><tr><th>field</th><th>what it is</th><th>years, Madrid</th><th>used</th></tr></thead><tbody>
<tr><td>series_to_same_date</td><td style="font-family:Spectral,serif;font-size:14.5px">nights so far, every prior year cut at the same calendar day</td><td style="text-align:right">{len(M['series_to_same_date']['values'])}</td><td>yes</td></tr>
<tr><td>full_year_series</td><td style="font-family:Spectral,serif;font-size:14.5px">nights across the whole year, complete seasons</td><td style="text-align:right">{len(M['full_year_series'])}</td><td style="color:#B32E10">no</td></tr>
<tr><td>warmest_night_c</td><td style="font-family:Spectral,serif;font-size:14.5px">the warmest single night of each year, in degrees</td><td style="text-align:right">{len(M['warmest_night_c'])}</td><td style="color:#B32E10">no</td></tr>
</tbody></table>
<p style="font-size:16px;line-height:1.6;max-width:68ch;margin:16px 0 0">
<strong style="font-weight:500;color:#1A1A18">warmest_night_c is a different quantity
entirely</strong>: an intensity in degrees rather than a count of nights. Madrid's runs
25.7, 25.7, 26.1 for 2023 to 2025 and reaches back to 1920. It answers "how hot did the
hottest night get", where the counts answer "how many hot nights were there". Nothing on
the site uses it.</p>
<p style="font-size:16px;line-height:1.6;max-width:68ch;margin:12px 0 0">
<strong style="font-weight:500;color:#1A1A18">full_year_series is the honest way to show
2026 is unfinished.</strong> Madrid has {M['nights_2026']} nights to {M['as_of']}, its
to-date record was {M['nights_2026'] - M['record_margin_nights']}, and its full-year 2025
was {M['full_year_series']['2025']}. My mockup could not say that, because it drew only
one of the three.</p>

{lab('Per city, everything emitted')}
<table><thead><tr><th>city</th><th style="text-align:right">2026</th>
<th style="text-align:right">rank</th><th style="text-align:right">of</th>
<th style="text-align:right">normally</th><th style="text-align:right">margin</th>
<th>source</th><th>as of</th></tr></thead><tbody>{city_rows}</tbody></table>
<p style="font-size:15.5px;line-height:1.55;max-width:66ch;margin:14px 0 0;color:#6E6E67">
margin is nights beyond that city's own previous record. It is <strong
style="font-weight:500;color:#1A1A18">null</strong> rather than 0 where no record was set:
null means "did not beat it", 0 would mean "tied it".</p>

{lab('What a renderer may not do')}
<p style="font-size:16px;line-height:1.6;max-width:66ch;margin:0 0 4px">These ride with the
data as fields rather than as conventions. Each is a build failure in my generator rather
than something to remember.</p>
{note('rank.requires_series', M['rank']['requires_series_note'])}
{note('headline_requires_baseline', f"The count of {H['records']} may not appear without its baseline: a typical year produces {H['baseline']['typical_year_records']}, and with no trend at all the expected number is {H['baseline']['expected_no_trend']}.")}
{note('may_not_say', H['may_not_say'])}
{note('series_to_same_date.cut_note', M['series_to_same_date']['cut_note'])}
{note('rank.matched_note', M['rank']['matched_note'])}
{note('never open the cross-check', 'heat/crosscheck/city_histories_ECAD.json is ECA&D, non-commercial, verification only. The payload is AEMET and Meteo-France. My first mockup drew series from it under AEMET ranks, which put two sources inside one figure.')}

{lab('Why the lead is not the record count')}
<p style="font-size:22px;line-height:1.35;color:#1A1A18;max-width:34ch;margin:0 0 12px">
&ldquo;{e(H['lead']['claim'])}&rdquo;</p>
<p style="font-size:16px;line-height:1.6;max-width:68ch;margin:0;color:#3A3A36">
{e(H['lead']['why_this_leads'])}</p>

{lab('What is NOT in the payload')}
<p style="font-size:16px;line-height:1.65;max-width:66ch;margin:0">No standard deviation,
so no z; only rank and percentile. No sub-annual detail, so no daily or monthly values,
only annual counts. No cities outside Spain and France, and the metric does not travel
north. No projection and no forecast. No population or exposure figures, so nothing in
here supports a harm claim.</p>

</div></x-dc></body></html>"""
out = ROOT / "design/review/heat-data-inventory.dc.html"
out.write_text(doc)
print(f"wrote {out} ({len(doc):,} bytes)")
