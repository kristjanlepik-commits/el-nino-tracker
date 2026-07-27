"""Render one page per qualifying country at docs/fires/<slug>/.

These are the destinations the channel page and the landing-page
markers link to, so every href the pipeline emits resolves. Styling
comes from tokens.py; the Bulletin rules apply, so bars are drawn with
plain divs on hairlines rather than boxed cards, radius 0, no shadows.

Content per page: the multiple as the hero, the fifteen-year same-week
history as bars with the current year highlighted and the mean drawn
behind, this week day by day, and the shared method and attribution
footer. Numbers come from fires/data/current_week.json, which is whole
days only.
"""
import json
import os
import re
import sys

import tokens as T

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Single source of truth for the analytics tag; see build_page.py.
sys.path.insert(0, REPO)
from run_brief import ANALYTICS_SNIPPET  # noqa: E402
EVENTS = os.path.join(REPO, "data", "events.json")
DETAIL = os.path.join(REPO, "fires", "data", "current_week.json")
OUTDIR = os.path.join(REPO, "docs", "fires")

TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked",
            "pending": "attribution pending"}
ORD = {1: "highest", 2: "second-heaviest", 3: "third-heaviest",
       4: "fourth-heaviest", 5: "fifth-heaviest"}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def page(ev, det, window_label, end_pretty):
    name = ev["region"]
    hist = {int(k): v for k, v in det["hist"].items()}
    now = det["count"]
    mean = det["mean"]
    years = sorted(hist) + [2026]
    vals = [hist[y] for y in sorted(hist)] + [now]
    mx = max(vals)
    rank = 1 + sum(1 for v in hist.values() if v > now)
    prev_year = max(hist, key=lambda y: hist[y])

    bars = []
    for y, v in zip(years, vals):
        cur = y == 2026
        hpct = max(1.2, v / mx * 100)
        lbl = (f'<span class="bv">{v:,}</span>'
               if y in (prev_year, 2026) else "")
        bars.append(
            f'<div class="bcol{" cur" if cur else ""}" '
            f'title="{y}: {v:,} detections">{lbl}'
            f'<div class="bar" style="height:{hpct:.1f}%"></div>'
            f'<span class="byr">{str(y)[2:]}</span></div>')

    daily = det.get("daily", {})
    dmax = max(daily.values()) if daily else 1
    dbars = []
    for d, v in daily.items():
        dbars.append(
            f'<div class="dcol" title="{d}: {v:,}">'
            f'<span class="dv">{v:,}</span>'
            f'<div class="dbar" style="height:{max(2, v / dmax * 100):.0f}%">'
            f'</div><span class="dl">{d[-2:]}</span></div>')

    verdict = (f"{name}'s {ORD.get(rank, str(rank) + 'th-heaviest')} "
               f"week for this point in the year since 2012")
    where = ""
    if det.get("lat") is not None:
        basis = ("centre of this week's detections"
                 if det["basis"] == "weighted"
                 else "centre of the largest cluster, because the "
                      "fires are spread across separate regions")
        where = (f'<p class="note">Fires centred near {det["lat"]}&deg;, '
                 f'{det["lon"]}&deg; ({basis}).</p>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} | Fire | The Long Swell</title>
<style>
{T.font_faces_css("../../fonts/")}
:root {{
{T.css_variables()}
}}
@media (prefers-color-scheme: dark) {{ :root {{
{T.css_variables(dark=True)}
}} }}
:root[data-theme="dark"] {{
{T.css_variables(dark=True)}
}}
:root[data-theme="light"] {{
{T.css_variables()}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font-family:"{T.FONT_PROSE}",Georgia,serif; font-size:17px;
  line-height:1.55; }}
main {{ max-width:760px; margin:0 auto; padding:28px 24px 80px; }}
a {{ color:inherit; }}
.masthead {{ display:flex; align-items:baseline; gap:14px;
  padding-bottom:10px; border-bottom:2px solid var(--ink); }}
.house {{ font-size:19px; }}
.product {{ font-family:"{T.FONT_DATA}",monospace; font-size:12px;
  font-weight:600; text-transform:uppercase;
  letter-spacing:{T.TRACK_PRODUCT}em; color:var(--fire);
  text-decoration:none; }}
.when {{ margin-left:auto; font-family:"{T.FONT_DATA}",monospace;
  font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); }}
h1 {{ font-size:36px; font-weight:500; margin:26px 0 6px;
  letter-spacing:-0.015em; }}
.verdict {{ color:var(--ink-soft); margin:0 0 22px; }}
.hero {{ display:flex; align-items:baseline; gap:16px; flex-wrap:wrap;
  border-top:2px solid var(--ink); border-bottom:1px solid var(--rule);
  padding:16px 0; margin-bottom:8px; }}
.hero .big {{ font-family:"{T.FONT_DATA}",monospace; font-size:52px;
  font-weight:600; color:var(--fire); line-height:1;
  font-variant-numeric:tabular-nums; }}
.hero .cap {{ font-size:15px; color:var(--ink-soft); flex:1;
  min-width:230px; }}
.hero .cap b {{ color:var(--ink); font-weight:500; }}
.tag {{ font-family:"{T.FONT_DATA}",monospace; font-size:10.5px;
  padding:3px 8px; letter-spacing:0.04em; }}
.tag-non_enso {{ background:var(--tag-notlink-bg);
  color:var(--tag-notlink-fg); }}
.tag-enso {{ background:var(--tag-loaded-bg); color:var(--tag-loaded-fg); }}
.tag-pending {{ background:var(--tag-pending-bg);
  color:var(--tag-pending-fg); }}
.lab {{ font-family:"{T.FONT_DATA}",monospace; font-size:11px;
  font-weight:600; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint);
  margin:34px 0 12px; padding-bottom:8px;
  border-bottom:1px solid var(--ink); }}
.chart {{ display:flex; align-items:flex-end; gap:5px; height:190px;
  position:relative; border-bottom:1px solid var(--ink); }}
.meanline {{ position:absolute; left:0; right:0; z-index:3;
  border-top:1px dashed var(--ink-faint); }}
.meanline span {{ position:absolute; right:0; top:-16px; font-size:10px;
  font-family:"{T.FONT_DATA}",monospace; color:var(--ink-faint);
  background:var(--paper); padding:0 4px; }}
.bcol {{ flex:1; display:flex; flex-direction:column;
  justify-content:flex-end; align-items:center; height:100%;
  position:relative; z-index:2; }}
.bar {{ width:100%; max-width:30px; background:var(--paper-sunk);
  border-top:1px solid var(--rule); }}
.bcol.cur .bar {{ background:var(--fire); border-top:none; }}
.bv {{ font-family:"{T.FONT_DATA}",monospace; font-size:10px;
  color:var(--ink-soft); margin-bottom:3px; }}
.bcol.cur .bv {{ color:var(--ink); font-weight:600; font-size:11.5px; }}
.byr {{ font-family:"{T.FONT_DATA}",monospace; font-size:9.5px;
  color:var(--ink-faint); margin-top:5px; }}
.bcol.cur .byr {{ color:var(--ink); font-weight:600; }}
.dchart {{ display:flex; align-items:flex-end; gap:6px; height:96px;
  border-bottom:1px solid var(--ink); }}
.dcol {{ flex:1; display:flex; flex-direction:column;
  justify-content:flex-end; align-items:center; height:100%; }}
.dbar {{ width:100%; max-width:54px; background:var(--paper-sunk);
  border-top:1px solid var(--rule); }}
.dv {{ font-family:"{T.FONT_DATA}",monospace; font-size:10px;
  color:var(--ink-soft); margin-bottom:3px; }}
.dl {{ font-family:"{T.FONT_DATA}",monospace; font-size:9.5px;
  color:var(--ink-faint); margin-top:5px; }}
.note {{ font-size:14px; color:var(--ink-soft); margin:14px 0 0;
  max-width:62ch; }}
.foot {{ margin-top:40px; padding-top:14px;
  border-top:1px solid var(--ink); font-size:13px;
  color:var(--ink-faint); max-width:66ch; }}
.foot p {{ margin:0 0 9px; }}
.foot b {{ color:var(--ink-soft); font-weight:500; }}
.back {{ display:inline-block; margin-top:26px; font-size:14px;
  color:var(--fire); }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
<main>
  <div class="masthead">
    <span class="house">The Long Swell</span>
    <a class="product" href="../">Fire</a>
    <span class="when">{window_label}</span>
  </div>

  <h1>{name}</h1>
  <p class="verdict">{verdict}.</p>

  <div class="hero">
    <span class="big">&times;{ev['stat'][:-1]}</span>
    <span class="cap"><b>{now:,} detections</b> in the week to
      {end_pretty}, against a 2012-2025 average of
      {mean:,.0f} for the same week.</span>
    <span class="tag tag-{ev['attribution']}">
      {TAG_TEXT[ev['attribution']]}</span>
  </div>

  <p class="lab">The same week, every year since 2012</p>
  <div class="chart">
    <div class="meanline" style="bottom:{mean / mx * 100:.1f}%">
      <span>14-yr mean {mean:,.0f}</span></div>
    {''.join(bars)}
  </div>

  <p class="lab">This week, day by day</p>
  <div class="dchart">{''.join(dbars)}</div>
  {where}

  <div class="foot">
    <p><b>What a detection is.</b> One satellite pixel, about 375 m
    across, seen radiating enough heat to be flagged as actively
    burning on a single overpass. A large fire front registers as many
    pixels at once, and a fire that keeps burning is counted again on
    every pass it stays hot. Detections are not burned area.</p>
    <p><b>Method.</b> NASA FIRMS, VIIRS on Suomi-NPP only so that every
    year is measured by the same sensor, low-confidence detections
    excluded, detections assigned by national boundary polygons applied
    identically in all years. Seven whole UTC days, refreshed once
    daily at 06:00 UTC, so nothing here is a partial day.</p>
  </div>
  <a class="back" href="../">All countries</a>
</main>
</body>
</html>
"""


def main():
    events = json.load(open(EVENTS))["events"]
    detail = json.load(open(DETAIL))
    label = detail["source"].split(", ")[-1]
    end_date = detail["window"].split("..")[-1]
    end_pretty = f"July {int(end_date.split('-')[-1])}"
    n = 0
    for ev in events:
        slug = slugify(ev["region"])
        iso = next((k for k, v in detail["countries"].items()
                    if v["name"] == ev["region"]), None)
        if not iso:
            print(f"  no detail for {ev['region']}, skipped")
            continue
        d = os.path.join(OUTDIR, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(page(ev, detail["countries"][iso], label, end_pretty))
        n += 1
    print(f"wrote {n} country pages under docs/fires/")


if __name__ == "__main__":
    main()
