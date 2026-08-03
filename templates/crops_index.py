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
than "chance produces" until the owning channel supplies one.

**The page must not call the total unremarkable, and an earlier version
did.** CRO has since recounted globally against a recent-decade
baseline: the global hoarding factor is 1.39, so the uniform figure is
roughly right worldwide even though it was four times wrong for Europe.
Against a 2014-2025 mean of 60.1 and a range of 25 to 110, this dekad's
81 exceeds three quarters of the last twelve years. Neither the null nor
a strong signal: mildly elevated.

Those figures are not in the payload, only in the channel's analysis, so
this page does not print them and does not assert whether 81 is
ordinary. It shows the uniform figure, labels it as uniform, and stops.
The empirical expectation wants to be a field.

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


def _join_and(names) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


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


def _trajectory(cb: dict, place: str) -> str:
    """A country's own record-low count, year by year.

    This replaces a binomial. It needs no independence assumption, which
    is the assumption that was wrong: neighbouring regions in one drought
    are not independent draws, so a p-value computed over them looked
    precise and was not. A reader can see twenty-five years of mostly
    nothing and then this one, and that is both more legible to a 4-8
    and more defensible than any test.
    """
    series = {int(y): v for y, v in cb["series"].items()}
    years = sorted(series)
    hi = max(max(series.values()), 1) * 1.25
    W, H, PAD_T, PAD_B, PAD_L, PAD_R = 660, 150, 26, 26, 8, 8
    slot = (W - PAD_L - PAD_R) / len(years)
    bw = min(slot * 0.6, 16.0)

    def Y(v):
        return H - PAD_B - v / hi * (H - PAD_T - PAD_B)

    out = []
    rm = cb.get("recent_mean")
    if rm is not None:
        y = Y(rm)
        out.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" '
                   f'y2="{y:.1f}" stroke="var(--ink-soft)" stroke-width="1" '
                   f'stroke-dasharray="4 3"/>')
        out.append(f'<text class="tj-s" x="{PAD_L + 2}" y="{y - 5:.1f}">'
                   f'recent average {rm:g}</text>')
    cur = max(years)
    for i, yr in enumerate(years):
        v = series[yr]
        cx = PAD_L + slot * (i + 0.5)
        fill = "var(--crop)" if yr == cur else "var(--rule-45)"
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{Y(v):.1f}" '
                   f'width="{bw:.1f}" height="{max(H - PAD_B - Y(v), 1.0):.1f}" '
                   f'fill="{fill}"/>')
        if yr in (years[0], cur):
            out.append(f'<text class="tj-x" x="{cx:.1f}" y="{H - 8:.1f}" '
                       f'text-anchor="middle">{yr}</text>')
        if yr == cur:
            out.append(f'<text class="tj-v" x="{cx:.1f}" y="{Y(v) - 7:.1f}" '
                       f'text-anchor="middle">{v}</text>')
    return (f'<svg class="tj" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{h(place)} crop regions at their worst on record, '
            f'each year since {years[0]}">' + "".join(out) + "</svg>")


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
    # Selection AND threshold are the channel's, not mine. My floor stood
    # here for one day and is deleted: a materiality threshold is domain
    # knowledge, so it belongs on CRO's side of the seam, and a floor I
    # invent renders my judgement under their byline.
    #
    # Read `notable`, order by `excess_share`. Never order on
    # `clears_own_recent_max`: it is a boolean over a small sample, so
    # Turkiye at 4 against a recent max of 2 and China at 1 against 0
    # both read True and are not comparable events.
    #
    # Why not the two shapes I proposed, both of which CRO tested and
    # rejected. Excess per unit rewards small denominators, ranking China
    # at 1 of 31 units above Turkiye at 4 of 79, so going from zero
    # regions to one outranks going from two to four. Absolute excess
    # cannot separate Chad's 8-against-3 from Suriname's 2-against-1.
    # The count floor is what actually works, because every noise case
    # has the same shape: 0 to 1, or 1 to 2.
    clusters = [(pl["place"], pl["chance_baseline"], pl.get("crop_units"))
                for pl in places
                if (pl.get("chance_baseline") or {}).get("notable")]
    clusters.sort(key=lambda t: -(t[1].get("excess_share") or 0))

    def _also(rest):
        """The rest of the notable set, printed so the drop-off shows.

        A bare list would read as six equivalent findings. Chad's excess
        share is more than three times the next country's, and five of
        the six clear their own maximum by exactly one region, so each
        row carries its own counts.

        The denominator is printed because it is what does the ordering.
        Without it Viet Nam's 6 sits below Sudan's 3 for no visible
        reason, and an order the reader cannot account for reads as a
        mistake in the page rather than as a property of the data. With
        "6 of 64" against "3 of 15" it is self-evident.
        """
        if not rest:
            return ""
        rows = "".join(
            f'<li><span class="alsoc">{h(c)}</span> '
            f'{cb["this_year"]} of {u} regions, against a previous high '
            f'of {cb["recent_max"]}</li>'
            for c, cb, u in rest)
        return (f'<p class="alsolab">Also above their own recent maximum, '
                f'by a smaller share of the country</p>'
                f'<ul class="also">{rows}</ul>')

    ctry_hits = sum(1 for p in places
                    if (p.get("magnitude") or {}).get("value") == 1)
    baseline = scales_block(
        [{"label": "Whole countries", "units": len(places), "years": K,
          "observed": ctry_hits},
         {"label": "Sub-national units", "units": N, "years": K,
          "observed": len(hits)}],
        note=("The expectation rises with the number of units, not with "
              "the weather, so any map at this resolution shows dozens of "
              "record lows every week. The figure marked is what an EVEN "
              "spread of records would give. Records do not fall evenly, "
              "and the owning channel holds the measured expectation, so "
              "this page does not say whether 81 is a high count or an "
              "ordinary one."))

    # The two blocks answer DIFFERENT QUESTIONS: depth (how bad is the
    # worst place) and breadth (how much of a country is affected).
    # Neither is a weaker form of the other, so neither may be labelled
    # as though it outranked the other.
    #
    # CRO's evidence, and it is decisive. Five of the eight deepest
    # countries are not broad at all: Suriname at z -3.79, Libya -3.75,
    # Ecuador -2.50, Congo -2.26, Colombia -1.82, each one catastrophic
    # region inside an otherwise ordinary country. Three of the six broad
    # countries are nowhere near the top on depth. If this page reads as
    # "most extreme" then "also extreme", it is simply wrong, because
    # Suriname's Brokopondo is the single most extreme cropland reading
    # on Earth this dekad and it sits in the second block.
    #
    # Breadth does imply some depth, which is why the broad set falls
    # inside the deep set at a z <= -1.0 cut. That is arithmetic, not
    # redundancy: three regions simultaneously at their record worst
    # makes it likely one of them is extreme. Depth implies nothing
    # about breadth, which is why Suriname and Libya exist.
    # State the asymmetry with the page's own numbers rather than
    # asserting it. Counting the countries that appear in BOTH blocks
    # would be the wrong statistic here: five of the six broad countries
    # also hold a deep region, so that figure reads as "the two blocks
    # mostly agree" and invites the reader to ask why there are two.
    # The direction that carries the meaning is the other one, because
    # depth does not imply breadth.
    deep = hits[:top_n]
    broad_names = {c for c, _, _ in clusters}
    deep_only = sum(1 for e in deep if e["country"] not in broad_names)
    pair_intro = f"""
      <p class="pairlab">Two questions, not a ranking</p>
      <p class="pairsub">Below, how much of a country is affected. Under
        it, how bad the worst single regions are. A country can lead
        either without appearing in the other, and the order of the two
        sections carries no claim about which matters more: of the
        {len(deep)} deepest regions listed here, {deep_only} sit in
        countries that are not widely affected at all.</p>"""

    cluster_html = ""
    if clusters:
        c, cb, cu = clusters[0]
        cluster_html = pair_intro + f"""
      <p class="seclab">Countries where it is widespread</p>
      <p class="secsub">Measured against each country&rsquo;s own record-low
        count in every previous year rather than against an assumed rate,
        which needs no claim that neighbouring regions fail
        independently.</p>
      <div class="cluster">
        <p class="cbig">{cb['this_year']} of {cu} regions</p>
        <p class="cbody">in {h(c)} are at their worst on record this dekad.
        Its highest in any of the previous twenty-five years was
        {cb['recent_max']}, and its recent average is {cb['recent_mean']:g}.</p>
        {_trajectory(cb, c)}
        {_also(clusters[1:])}
        <p class="ccav">A lead rather than a finding: the owning channel
        rules before this is published as a claim. The payload also
        carries what an even spread would have predicted, and it is not
        printed here, because that figure exists to be argued with rather
        than shown to a reader.</p>
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

/* The pair framing sits above both blocks and belongs to neither, so it
   is ink and unhued. Giving it the channel colour would make it read as
   the first block's heading, which is the ordering claim it exists to
   deny. */
.pairlab {{ margin:34px 0 0; font-size:11px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink);
  font-family:"{T.FONT_DATA}",monospace; }}
.pairsub {{ margin:8px 0 0; font-size:14px; color:var(--ink-soft);
  max-width:64ch; }}

.cluster {{ margin-top:12px; padding-left:18px;
  border-left:3px solid var(--crop); }}
.tj {{ width:100%; height:auto; display:block; margin:14px 0 4px; }}
.tj text {{ font-family:"{T.FONT_DATA}",monospace; paint-order:stroke;
  stroke:var(--paper); stroke-width:2.5; stroke-linejoin:round; }}
.tj-s {{ font-size:10.5px; fill:var(--ink-soft); }}
.tj-x {{ font-size:10px; fill:var(--ink-faint); }}
.tj-v {{ font-size:13px; fill:var(--crop); font-weight:600; }}
.cbig {{ font-size:34px; font-weight:600; color:var(--crop); margin:0;
  line-height:1; font-variant-numeric:tabular-nums; }}
.cbody {{ margin:10px 0 0; max-width:60ch; }}
.ccav {{ margin:10px 0 0; font-size:13.5px; color:var(--ink-soft);
  max-width:60ch; }}
/* The runners-up are ink, not crop. The channel hue marks the one case
   that is above its own history by a real margin; spending it on five
   countries that clear by a single region would make the drop-off the
   block exists to show invisible. */
.alsolab {{ margin:18px 0 0; font-size:11px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint);
  font-family:"{T.FONT_DATA}",monospace; }}
.also {{ margin:8px 0 0; padding:0; list-style:none; font-size:14px;
  color:var(--ink-soft); max-width:60ch; }}
.also li {{ padding:4px 0; border-bottom:1px solid var(--rule);
  font-variant-numeric:tabular-nums; }}
.alsoc {{ color:var(--ink); font-weight:600; }}
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
  <h1>{len(hits)} crop regions are at their worst on record for this
  point in the season.</h1>
  <p class="stand">Every place below is measured only against itself, at
  the same point in the season, in every year since 2001. Whether {len(hits)}
  is a high count for a single dekad is a question about how records fall
  rather than about this week, and it is answered further down. What is
  inside the {len(hits)} is not evenly spread, and that is the part worth
  reading now.</p>

  {baseline}

  {cluster_html}

  <p class="seclab">The worst single regions</p>
  <p class="secsub">Ordered by size of the shortfall rather than by rank,
    because every place here ranks first and they are not equally bad:
    the top of this list is {abs(hits[0]['z'] / hits[-1]['z']):.0f} times
    the bottom of it. Showing the {min(top_n, len(hits))} largest of
    {len(hits)}. A country reaches this list on one region alone, and
    can do so while reading as entirely ordinary nationally.</p>
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
