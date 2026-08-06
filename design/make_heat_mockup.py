"""Design mockup for the heat one-pager. Generated, never hand-edited.

Built against the PRE-RE-EMIT payload and marked as such on the page.
Heat re-sources the Spanish cities from AEMET tonight; Madrid's baseline
mean moves 21.0 to 21.2 and ranks do not change. This is a review of the
TREATMENT, so it swaps its data rather than being rebuilt.

Three constraints from product, all structural rather than cosmetic:

  each city scaled to ITS OWN record   so cross-city comparison is
                                       impossible rather than discouraged
  every rank drawn ON its own series   which is where requires_series is
                                       satisfied rather than asserted
  Malaga's one-night margin visible    D-043 in its hardest case, since a
                                       one-night margin is exactly what a
                                       system tuned for alarm rounds up

And two devices product ruled free (VD's 03 and 04), shown in place:
the repeated rhythm (instrument, then a dense list, then one number
alone) and the type scale used at its extremes with nothing between.

No channel hue, per D-101. Identity is the tracked mono product name
against the Spectral wordmark. ACCENT marks the current reading only.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cur = json.loads((ROOT / "heat/data/city_nights_2026.json").read_text())
hist = json.loads((ROOT / "heat/data/city_histories.json").read_text())
base = json.loads((ROOT / "heat/data/record_rate_baseline.json").read_text())

# The prohibition travels with the datum (D-104). Fail rather than render
# a headline the payload forbids.
MAY_NOT_SAY = base["may_not_say"]
if "2003" not in MAY_NOT_SAY:
    raise SystemExit("may_not_say changed shape; re-read it before rendering")

rows = []
for city, v in cur.items():
    td = hist[city]["todate"]
    series = [(int(y), n) for y, n in td.items() if n is not None]
    series.sort()
    prev = max(n for _, n in series)
    prev_year = max(y for y, n in series if n == prev)
    rows.append({
        "city": city, "country": v["country"], "n": v["n"],
        "rank": v["rank"], "of": v["of_years"], "mean": v.get("mean_9120"),
        "series": series, "prev": prev, "prev_year": prev_year,
        "margin": v["n"] - prev, "first": hist[city]["first"],
    })
# Rank first, then margin. NOT by count: ordering fifteen cities by
# nights would rank Palma's 58 above Paris's 17 and say nothing, because
# the whole point is that each city is measured against itself.
rows.sort(key=lambda r: (r["rank"], -r["margin"]))
records = [r for r in rows if r["rank"] == 1]


def spark(r, w=210, h=34):
    """One city's record, scaled to ITS OWN maximum.

    The y axis is that city's own history and nothing else, so two
    sparklines on this page cannot be compared and are not meant to be.
    """
    ys = [n for _, n in r["series"]] + [r["n"]]
    top = max(ys) or 1
    xs = [y for y, _ in r["series"]]
    x0, x1 = min(xs), 2026
    def px(y): return (y - x0) / (x1 - x0) * w
    def py(n): return h - (n / top) * h
    pts = " ".join(f"{px(y):.1f},{py(n):.1f}" for y, n in r["series"])
    cx, cy = px(2026), py(r["n"])
    prev_x, prev_y = px(r["prev_year"]), py(r["prev"])
    return f"""<svg viewBox="0 0 {w} {h + 12}" width="{w}" height="{h + 12}" aria-hidden="true">
      <polyline points="{pts}" fill="none" stroke="var(--rule)" stroke-width="1"/>
      <line x1="{prev_x:.1f}" y1="{prev_y:.1f}" x2="{prev_x:.1f}" y2="{h}"
            stroke="var(--ink-faint)" stroke-width="1" stroke-dasharray="2 2"/>
      <line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx:.1f}" y2="{h}"
            stroke="var(--accent)" stroke-width="2.4"/>
      <circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.6" fill="var(--accent)"/>
    </svg>"""


def row_html(r):
    marg = (f'<span class="marg">+{r["margin"]}</span> on {r["prev_year"]}'
            if r["rank"] == 1 else
            f'{r["rank"]}<span class="ord">{"nd" if r["rank"]==2 else "rd" if r["rank"]==3 else "th"}</span> of {r["of"]}')
    return f"""<a class="crow" href="#">
      <span class="cname">{r['city']}</span>
      <span class="cspark">{spark(r)}</span>
      <span class="cfact">{marg}<br><span class="cbase">normally {r['mean']} · since {r['first']}</span></span>
      <span class="cnum">{r['n']}</span>
    </a>"""


lead = records[0]
html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heat mockup · The Long Swell</title>
<style>
:root {{
  --paper:#F1F0EC; --sunk:#E7E6DF; --ink:#1A1A18; --soft:#3A3A36;
  --ink-faint:#6E6E67; --rule:#CFCEC7; --accent:#173F9E;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --paper:#1A1A18; --sunk:#252521; --ink:#EDECE6; --soft:#B4B3AB;
          --ink-faint:#86857D; --rule:#3A3A36; --accent:#6E97E8; }}
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
  font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:760px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:14px;padding:20px 0 11px;
  border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
/* D-101: no channel hue. The product name is set in tracked mono
   against the Spectral wordmark, and that split IS the identity. */
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;
  font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
  letter-spacing:0.14em;text-transform:uppercase;color:var(--ink-faint)}}
/* Device 04: the scale at its extremes. One mono line carrying every
   fact, then the claim, and nothing in between. */
.facts{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;
  letter-spacing:0.22em;text-transform:uppercase;color:var(--soft);
  margin:40px 0 14px}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.06;
  letter-spacing:-0.018em;color:var(--ink);margin:0;max-width:19ch;text-wrap:balance}}
.stand{{font-size:17.5px;line-height:1.62;max-width:60ch;margin:18px 0 0}}
.seclab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;
  letter-spacing:0.22em;text-transform:uppercase;color:var(--ink);
  border-bottom:3px solid var(--ink);padding-bottom:10px;margin:52px 0 0}}
/* Device 03, beat 2: the dense list. Thin rows, tight leading. */
.crow{{display:grid;grid-template-columns:104px 210px 1fr 44px;gap:18px;
  align-items:center;padding:9px 0;border-bottom:1px solid var(--rule);
  text-decoration:none;color:inherit}}
.cname{{font-size:16.5px;font-weight:500;color:var(--ink)}}
.cspark{{line-height:0}}
.cfact{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.5;
  color:var(--soft)}}
.cbase{{color:var(--ink-faint)}}
.marg{{color:var(--ink);font-weight:600}}
.ord{{font-size:8.5px}}
.cnum{{font-family:'IBM Plex Mono',monospace;font-size:19px;font-weight:500;
  font-variant-numeric:tabular-nums;color:var(--ink);text-align:right}}
/* Device 03, beat 3: one number, alone, with air around it. */
.alone{{margin:64px 0 60px;display:flex;align-items:baseline;gap:18px}}
.alone .big{{font-family:'IBM Plex Mono',monospace;font-size:64px;font-weight:500;
  line-height:1;letter-spacing:-0.02em;color:var(--ink)}}
.alone .cap{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;
  letter-spacing:0.18em;text-transform:uppercase;color:var(--ink-faint);max-width:26ch}}
.note{{font-size:15.5px;line-height:1.6;color:var(--soft);max-width:66ch;margin:16px 0 0}}
.warn{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.7;
  color:var(--soft);background:var(--sunk);padding:13px 15px;margin:34px 0 0}}
</style></head><body><main>

<div class="mast"><span class="house">The Long Swell</span>
  <span class="prod">Heat</span>
  <span class="when">Tropical nights · to 3 August 2026</span></div>

<p class="facts">15 cities · Spain and France · station records to 105 years ·
  nights at or above 20&deg;C</p>
<h1>Three of the four worst years on record are the last four.</h1>
<p class="stand">Eight of these fifteen cities have already had more tropical
  nights than in any year on record, and the season is not over. A typical
  year produces none: the median since 1990 is zero and, with no trend at
  all, the expected number is 0.19.</p>
<p class="note">{MAY_NOT_SAY} 2022 and 2025 produced seven each. The pattern
  is the finding, not this year.</p>

<p class="seclab">Every city against its own record</p>
<p class="note" style="margin-bottom:14px">Each line is scaled to that city's
  own history, so no two can be compared with each other. The dashed mark is
  its previous best; the solid mark is 2026.</p>
{"".join(row_html(r) for r in rows)}

<div class="alone">
  <span class="big">+{lead['margin']}</span>
  <span class="cap">nights is all that separates {lead['city']} from its own
    previous record, set last year. It counts the same as Lyon's twelve.</span>
</div>

<div class="warn">MOCKUP, pre-re-emit. Built from city_nights_2026.json at
  2026-08-03, before heat re-sources the Spanish cities from AEMET. Madrid's
  baseline mean moves 21.0 to 21.2 and no rank changes. Review the treatment,
  not the third significant figure.</div>

</main></body></html>"""
out = ROOT / "design/review/heat-mockup.html"
out.write_text(html)
print(f"wrote {out} ({len(html):,} bytes, {len(rows)} cities, {len(records)} records)")
