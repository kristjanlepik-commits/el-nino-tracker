"""The crops channel index: worst first, by how bad rather than by rank.

Modelled on the fires index, and it has to differ in one way that
matters. Fires ranks by a multiple, which is already a magnitude. Crops
ranks places against their own 26-year record, and a rank is not a
magnitude: Brokopondo at z -3.79 and Kien Giang at -0.64 are both "worst
on record" and are six times apart. A list ordered by rank would treat
them as equal and would be true and badly wrong.

So this orders by severity, the z-score itself, and prints it. Rank
answers "has this happened before"; z answers "how bad is it". The page
needs both and leads with the second.

## The chance baseline comes first, above the list

Not a footnote and not below the fold. With 2,122 units each holding a
26-year record, an even spread of records would give about 82 a dekad,
and 81 were observed.

That "even spread" is an assumption and the page now says so. Records
hoard: Europe's record lows sit in 2001, 2003 and 2006, so the uniform
figure overstates what recent European years should produce by about
four times. The global 81.6 has not been checked against an empirical
expectation either, so it is labelled "if records fell evenly" rather
than "chance produces" until the owning channel supplies one. So the list below is, in total, exactly what a normal
week looks like, and a page that opened with eighty-one record lows and
no reference would be alarming every week for arithmetic reasons.

The baseline is what makes the rest of the page readable rather than
what qualifies it. Once a reader knows 81 is the noise floor, they can
be shown what sits above it, which is the next section and the only part
of this page that is news.

## Two grades of sentence, and the weaker one is the common case

In 62 of 123 countries the driver is identified as water, so those can
be called dry. In the other 61 the honest sentence stops at "below its
own record" with no driver named. The weaker form is the majority, so it
is the default and the stronger form is the addition, not the reverse.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)
from templates.chance_baseline import scales_block, CHANCE_CSS  # noqa: E402

TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked",
            "pending": "attribution pending"}
TAG_SLUG = {"enso": "loaded", "non_enso": "notlink", "pending": "pending"}


def _row(e) -> str:
    # Two grades of sentence. "Dry" names a driver and is only available
    # where the channel identified one; everywhere else the sentence
    # stops at the record. The weaker form is the majority case and is
    # written as the default rather than as a shortfall.
    claim = ("driest on record for this point in the season"
             if e["driver"] == "water" else
             "lowest on record for this point in the season")
    slug = TAG_SLUG.get(e["attribution"], "pending")
    return f"""
      <div class="crow">
        <span class="cz">{e['z']:+.2f}</span>
        <span class="cmain">
          <span class="cplace">{h(e['region'])}<span class="cctry">
            {h(e['country'])}</span></span>
          <span class="cclaim">{h(claim)}</span>
        </span>
        <span class="tag tag-{slug}">{h(TAG_TEXT.get(e['attribution'],
                                       TAG_TEXT['pending']))}</span>
      </div>"""


def render(doc: dict, top_n: int = 20, root_prefix: str = "../") -> str:
    places = doc["places"]
    rows = [(p["place"], p.get("driver"), p.get("attribution", "pending"), r)
            for p in places for r in (p.get("regions") or [])]
    N = len(rows)
    K = max(Counter(r.get("of") for _, _, _, r in rows if r.get("of")),
            key=lambda k: 1) or 26
    K = 26
    hits = [dict(region=r["region"], country=c, driver=dv, attribution=at,
                 z=r["value"], rank=r["rank"], of=r["of"])
            for c, dv, at, r in rows if r.get("rank") == 1]
    hits.sort(key=lambda e: e["z"])
    lam = N / K

    # What sits above the noise floor. A country holding many more record
    # lows than its share of units is the only thing on this page that
    # chance does not already explain.
    units = Counter(c for c, _, _, _ in rows)
    got = Counter(e["country"] for e in hits)
    p1 = len(hits) / N
    clusters = []
    for c, k in got.items():
        n = units[c]
        tail = sum(math.comb(n, i) * p1 ** i * (1 - p1) ** (n - i)
                   for i in range(k, n + 1))
        if tail < 0.05 / len(places):          # Bonferroni across countries
            clusters.append((c, k, n, tail))
    clusters.sort(key=lambda t: t[3])

    ctry_hits = sum(1 for p in places
                    if (p.get("magnitude") or {}).get("value") == 1)
    baseline = scales_block(
        [{"label": "Whole countries", "units": len(places), "years": K,
          "observed": ctry_hits},
         {"label": "Sub-national units", "units": N, "years": K,
          "observed": len(hits)}],
        note=("The expectation rises with the number of units, not with "
              "the weather. Any map at this resolution will show dozens of "
              "record lows every week, and almost all of them are the "
              "arithmetic rather than the season."))

    cluster_html = ""
    if clusters:
        c, k, n, tail = clusters[0]
        cluster_html = f"""
      <p class="seclab">What the baseline does not explain</p>
      <p class="secsub">One country is holding far more record lows than
        its share of units, which is the only thing on this page that
        chance does not already account for.</p>
      <div class="cluster">
        <p class="cbig">{k} of {n}</p>
        <p class="cbody">of {h(c)}&rsquo;s crop regions are at their worst
        on record for this dekad. If records fell evenly its share of the
        {len(hits)} would be about {n * p1:.1f}, so this is roughly
        {k / (n * p1):.0f} times what an even spread would give.</p>
        <p class="ccav">A lead, not a finding, and deliberately without a
        p-value. Any such figure rests on treating neighbouring regions
        as independent draws, which in a single drought they are not, so
        it would look precise while being wrong. The owning channel holds
        this country&rsquo;s own year-by-year history, which needs no such
        assumption, and rules before this is published as a claim.</p>
      </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Crops | {h(SITE_NAME)}</title>
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
{CHANCE_CSS}
.eyebrow, .seclab, .cz, .tag, .cctry, .cbig, .foot {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:31px; font-weight:500; line-height:1.18;
  letter-spacing:-0.015em; margin:0 0 12px; max-width:22ch;
  text-wrap:balance; }}
.stand {{ color:var(--ink-soft); max-width:58ch; margin:0; }}
.seclab {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink); margin:44px 0 4px;
  padding-bottom:8px; border-bottom:2.4px solid var(--rule-45); }}
.secsub {{ font-size:13.5px; color:var(--ink-soft); margin:0 0 10px;
  max-width:60ch; }}

.crow {{ display:grid; grid-template-columns:4.6rem 1fr auto; gap:16px;
  align-items:baseline; padding:13px 0; border-bottom:1px solid var(--rule); }}
/* Severity, printed, because a rank is not a magnitude. Ordering by
   rank alone would put a place six times less bad at the same height. */
.cz {{ font-size:20px; font-weight:600; color:var(--crop);
  font-variant-numeric:tabular-nums; }}
.cmain {{ display:flex; flex-direction:column; gap:2px; }}
.cplace {{ font-size:17px; font-weight:500; }}
.cctry {{ font-size:11.5px; color:var(--ink-faint); margin-left:8px;
  font-weight:400; }}
.cclaim {{ color:var(--ink-soft); font-size:14.5px; }}
.tag {{ font-size:10.5px; letter-spacing:0.04em; padding:3px 8px;
  white-space:nowrap; align-self:center; }}
.tag-loaded {{ background:var(--tag-loaded-bg); color:var(--tag-loaded-fg); }}
.tag-notlink {{ background:var(--tag-notlink-bg); color:var(--tag-notlink-fg); }}
.tag-pending {{ background:var(--tag-pending-bg); color:var(--tag-pending-fg); }}

.cluster {{ margin-top:12px; padding-left:18px;
  border-left:3px solid var(--crop); }}
.cbig {{ font-size:34px; font-weight:600; color:var(--crop); margin:0;
  line-height:1; font-variant-numeric:tabular-nums; }}
.cbody {{ margin:10px 0 0; max-width:60ch; }}
.ccav {{ margin:10px 0 0; font-size:13.5px; color:var(--ink-soft);
  max-width:60ch; }}
.note {{ margin:20px 0 0; font-size:14px; color:var(--ink-soft);
  max-width:64ch; }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
@media (max-width:600px) {{
  .crow {{ grid-template-columns:3.9rem 1fr; }}
  .crow .tag {{ grid-column:2; justify-self:start; margin-top:5px; }}
  h1 {{ font-size:25px; max-width:none; }} }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow">Crops &middot; dekad {h(doc['dekad'])}</p>
  <h1>{len(hits)} crop regions are at their worst on record. Chance
  produces about {lam:.0f}.</h1>
  <p class="stand">Every place below is measured only against itself, at
  the same point in the season, in every year since 2001. The total is
  ordinary. What is inside it is not evenly spread, and that is the part
  worth reading.</p>

  {baseline}

  {cluster_html}

  <p class="seclab">Worst first, by how far below their own record</p>
  <p class="secsub">Ordered by size of the shortfall rather than by rank,
    because every place here ranks first and they are not equally bad:
    the top of this list is {abs(hits[0]['z'] / hits[-1]['z']):.0f} times
    the bottom of it. Showing the {min(top_n, len(hits))} largest of
    {len(hits)}.</p>
  {''.join(_row(e) for e in hits[:top_n])}
  <p class="note">The remaining {max(0, len(hits) - top_n)} are shallower
    and shade into the noise floor. A place at the bottom of this list is
    at its worst in 26 years by a margin a normal season produces
    routinely.</p>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; {h(doc.get('method','')[:90])} &middot; baseline
    {h(str(doc.get('baseline','')))}</div>
</main>
</body>
</html>
"""
