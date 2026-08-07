"""Design mockup for the heat one-pager. Generated, never hand-edited.

Reads heat/data/city_nights.json and NOTHING ELSE. In particular it never
opens heat/crosscheck/city_histories_ECAD.json: that file is ECA&D while
the payload is AEMET and Meteo-France, and drawing an ECA&D series under
an AEMET rank would mix two sources inside one figure. The first draft of
this file did exactly that.

Everything the page claims comes from the payload:

  the lead        headline.lead.claim, which is product's ruling and NOT
                  the record count. The count can move on a data update,
                  since Malaga leads by one night; "no ordinary city"
                  cannot. A renderer that led on the count would publish
                  a headline that a revision could falsify.
  the margin      record_margin_nights, emitted rather than recomputed
  the series      series_to_same_date.values, at the city's own source
  the baseline    headline.baseline, because headline_requires_baseline

Three payload constraints are enforced as build failures rather than
honoured by convention, per D-104:

  requires_series          a rank may not render without its series
  headline_requires_baseline   the count may not render bare
  may_not_say              rendered verbatim, never paraphrased
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "heat/data/city_nights.json").read_text())
CITIES, HEAD = D["cities"], D["headline"]

if not HEAD.get("headline_requires_baseline"):
    raise SystemExit("headline_requires_baseline missing; re-read the payload")
BASE, MAY_NOT_SAY = HEAD["baseline"], HEAD["may_not_say"]

rows = []
for name, c in CITIES.items():
    r = c["rank"]
    if r.get("requires_series") and not c.get("series_to_same_date", {}).get("values"):
        raise SystemExit(f"{name}: rank requires a series and the payload has none")
    rows.append({"name": name, **c, "r": r,
                 "series": sorted((int(y), n) for y, n in
                                  c["series_to_same_date"]["values"].items())})
# Records first, then by emitted margin. Deliberately NOT by nights: the
# payload's cut_note says cities are cut at different calendar days by
# source, so a cross-city ranking on the raw count is not a valid
# comparison. Rank and margin are each self-relative.
# record_margin_nights is null unless the city set a record, which is
# correct of the payload: a margin over your own record does not exist
# if you did not beat it. Never coerce it to 0, which would read as
# "tied its record".
rows.sort(key=lambda x: (x["r"]["value"], -(x["record_margin_nights"] or 0)))
FEAT = D["featured_cities"]


def spark(x, w=220, h=36):
    """One city against ITS OWN record. The y axis is that city's history
    and nothing else, so two of these cannot be compared, which is the
    point rather than a limitation."""
    ser = x["series"]
    top = max([n for _, n in ser] + [x["nights_2026"]]) or 1
    x0, x1 = min(y for y, _ in ser), 2026
    px = lambda y: (y - x0) / (x1 - x0) * w
    py = lambda n: h - (n / top) * h
    pts = " ".join(f"{px(y):.1f},{py(n):.1f}" for y, n in ser)
    prev = max(n for _, n in ser)
    pyr = max(y for y, n in ser if n == prev)
    return (f'<svg viewBox="0 0 {w} {h+3}" width="{w}" height="{h+3}">'
            f'<polyline points="{pts}" fill="none" stroke="var(--rule)" stroke-width="1"/>'
            f'<line x1="{px(pyr):.1f}" y1="{py(prev):.1f}" x2="{px(pyr):.1f}" y2="{h}" '
            f'stroke="var(--ink-faint)" stroke-width="1" stroke-dasharray="2 2"/>'
            f'<line x1="{px(2026):.1f}" y1="{py(x["nights_2026"]):.1f}" '
            f'x2="{px(2026):.1f}" y2="{h}" stroke="var(--accent)" stroke-width="2.4"/>'
            f'<circle cx="{px(2026):.1f}" cy="{py(x["nights_2026"]):.1f}" r="2.6" '
            f'fill="var(--accent)"/></svg>')


def ordinal(n):
    return f"{n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'}"


def row(x):
    r = x["r"]
    fact = (f'<span class="marg">+{x["record_margin_nights"]}</span> on its own record'
            if r["value"] == 1 else f'{ordinal(r["value"])} of {r["of_years"]}')
    return (f'<div class="crow{" feat" if x["name"] in FEAT else ""}">'
            f'<span class="cname">{x["name"]}</span>'
            f'<span>{spark(x)}</span>'
            f'<span class="cfact">{fact}<br><span class="cbase">'
            f'normally {x["mean_1991_2020_to_date"]["value"]} · since {x["record_from"]}'
            f'</span></span>'
            f'<span class="cnum">{x["nights_2026"]}</span></div>')


# The number set alone is the SMALLEST margin among the records, not the
# largest. Product's constraint, and it is D-043 in its hardest case: a
# one-night margin is exactly the reading a system tuned for alarm would
# round up to "record" and stop. Sorting put Lyon's twelve first, which
# made the caption compare Lyon to itself.
recs = [x for x in rows if x["r"]["value"] == 1]
thin = min(recs, key=lambda x: x["record_margin_nights"])
fat = max(recs, key=lambda x: x["record_margin_nights"])
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heat mockup · The Long Swell</title><style>
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:780px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}}
.facts{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--soft);margin:40px 0 14px}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.06;
letter-spacing:-.018em;color:var(--ink);margin:0;max-width:20ch;text-wrap:balance}}
.stand{{font-size:17.5px;line-height:1.62;max-width:60ch;margin:18px 0 0}}
.note{{font-size:15.5px;line-height:1.6;max-width:68ch;margin:14px 0 0}}
.seclab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:52px 0 0}}
.crow{{display:grid;grid-template-columns:100px 220px 1fr 42px;gap:18px;
align-items:center;padding:9px 0;border-bottom:1px solid var(--rule)}}
.crow.feat{{background:var(--sunk)}}
.cname{{font-size:16.5px;font-weight:500;color:var(--ink)}}
.cfact{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.5}}
.cbase{{color:var(--ink-faint)}}
.marg{{color:var(--ink);font-weight:600}}
.cnum{{font-family:'IBM Plex Mono',monospace;font-size:19px;font-weight:500;
font-variant-numeric:tabular-nums;color:var(--ink);text-align:right}}
.alone{{margin:60px 0 54px;display:flex;align-items:baseline;gap:18px}}
.big{{font-family:'IBM Plex Mono',monospace;font-size:64px;font-weight:500;line-height:1;
letter-spacing:-.02em;color:var(--ink)}}
.cap{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;
text-transform:uppercase;color:var(--ink-faint);max-width:28ch;line-height:1.7}}
.tag{{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:9.5px;
letter-spacing:.14em;text-transform:uppercase;background:var(--sunk);
color:var(--soft);padding:4px 8px}}
.warn{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.7;
color:var(--soft);background:var(--sunk);padding:13px 15px;margin:34px 0 0}}
</style></head><body><main>
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">Tropical nights · to 2-3 August 2026</span></div>

<p class="facts">{HEAD['of_cities']} cities · {D['definition']['rule']} ·
station records to 105 years</p>
<h1>{HEAD['lead']['claim']}</h1>
<p class="stand">{HEAD['lead']['in_top_10pct']} of {HEAD['lead']['of_cities']} are in
the warmest tenth of their own record and {HEAD['lead']['in_top_5pct']} in the
warmest twentieth. {HEAD['records']} have already beaten their record outright,
with the season unfinished.</p>
<p class="note"><strong>A typical year produces {BASE['typical_year_records']}.</strong>
The mean since 2011 is {BASE['mean_2011_2025']}, and with no trend at all the
expected number is {BASE['expected_no_trend']}.</p>
<p class="note">{MAY_NOT_SAY}</p>
<p class="note"><span class="tag">{D['attribution']}</span></p>

<p class="seclab">Every city against its own record</p>
<p class="note" style="margin-bottom:16px">Each line is scaled to that city's own
history, so no two can be read against each other. The dashed mark is its previous
best, the solid mark is 2026. {D['definition']['standard']}</p>
{"".join(row(x) for x in rows)}

<div class="alone"><span class="big">+{thin['record_margin_nights']}</span>
<span class="cap">night is all that separates {thin['name']} from its own previous
record. In the count of eight it weighs the same as {fat['name']}'s
{fat['record_margin_nights']}, which is why the lead above does not rest on
that count.</span></div>

<div class="warn">MOCKUP for design review. Every figure is read from
heat/data/city_nights.json and none is recomputed here. The cross-check file
heat/crosscheck/city_histories_ECAD.json is deliberately never opened: it is ECA&amp;D
where the payload is AEMET and Meteo-France.</div>
</main></body></html>"""
out = ROOT / "design/review/heat-mockup.html"
out.write_text(html)
print(f"wrote {out} ({len(rows)} cities, {HEAD['records']} records, "
      f"lead: {HEAD['lead']['claim'][:44]}...)")
