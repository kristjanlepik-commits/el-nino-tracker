"""Regional night drift: July nights against the year as a whole.

The finding is a DIFFERENCE OF DIFFERENCES and that is what the page has
to draw. Summer nights have not moved at the same rate as the year, and
the direction is not the same everywhere. Three regions where July
outran the year, one where it lagged.

## Why the gap is the mark

A bar chart of July drift would say "nights are warming", which is true,
known, and not this. The finding lives in the SPACE between two numbers
for the same region, so the page draws both and the connector between
them. A reader sees the gap before they read a number, and the one
region whose connector points the other way is visible without being
labelled as an exception.

## The weakest region is emitted as weak, not judged as weak here

`rhetorical_weight` is the channel's field, not my inference. Three
regions carry "assert"; the US Southwest carries "state_with_margin",
because its margin over the box-choice spread is 1.6x where the others
are 6 to 9x.

It stays on the page at full size. It is the only negative contrast in
the set and therefore carries half the finding: without it the page
says "summer nights are warming faster", which is a weaker and more
ordinary claim than "and in one of these four places they are not". The
margin is printed beside it so a reader can see which regions do the
heavier lifting, rather than the page quietly styling one of them into
the background.

## What this page may not say

No city-level anything: this is a 1-degree regional grid, 500 to 900 km
across. No cause and no attribution; two 30-year means differ and we do
not say why. And nothing that composes a distance from both this and the
ERA5 work, per D-068: two instruments, two claims, never one number
built from both.

The headline baseline pair is 1961-1990 against 1991-2020 because it was
the pre-registered one. The alternative 1951-1980 pair STRENGTHENS the
result, including more than doubling the Southwest's negative contrast,
and is reported as robustness only. Swapping to the flattering pair is
the thing we would criticise in someone else and a reader could never
detect it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)


# The three ratified attribution strings, D-033. There is no fourth.
ATTRIBUTION = {
    "enso": "ENSO-loaded window",
    "non_enso": "Not ENSO-linked",
    "pending": "Attribution pending",
}


def _attribution_tag(value) -> str:
    """The tag, or a build failure. Never silent omission.

    T9 requires the attribution as a UI element rather than prose, and
    this page had NO SLOT FOR IT AT ALL, so Heat's invalid string
    ("not assessed", a fourth word D-033 forbids) produced a page with
    no tag and no error. Heat found that by reading their own payload
    against the ratified list; nothing here would have told them.

    So an unrecognised value stops the build. A missing tag on a page
    that requires one is indistinguishable from a page whose claim needs
    no tag, and that is the same fail-open that let five countries
    render a driver line that did not hold there.
    """
    if value in ATTRIBUTION.values():
        slug = next(k for k, v in ATTRIBUTION.items() if v == value)
        return f'<span class="tag tag-{slug}">{h(value)}</span>'
    raise SystemExit(
        f"heat/data/night_drift.json has attribution {value!r}, which is "
        f"not one of the three ratified strings under D-033:\n  "
        + "\n  ".join(ATTRIBUTION.values())
        + "\nRefusing to render a page with no attribution tag rather "
          "than omitting it silently. T9 requires the tag as an element.")


def _rows(regions) -> str:
    """Four regions on one Celsius axis, July and annual, gap between."""
    vals = [v for r in regions
            for v in (r["july_night_drift_c"]["value"],
                      r["annual_night_drift_c"]["value"])]
    lo, hi = min(vals + [0.0]), max(vals)
    pad = max((hi - lo) * 0.10, 0.06)
    lo, hi = lo - pad, hi + pad

    W, RH, PAD_L, PAD_R, TOP = 660, 62.0, 178, 22, 34
    H = TOP + RH * len(regions) + 26

    def X(v):
        return PAD_L + (v - lo) / (hi - lo) * (W - PAD_L - PAD_R)

    out = []
    if lo <= 0 <= hi:
        z = X(0.0)
        out.append(f'<line x1="{z:.1f}" y1="{TOP - 14:.1f}" x2="{z:.1f}" '
                   f'y2="{H - 24:.1f}" stroke="var(--rule)" stroke-width="1"/>')
        out.append(f'<text class="nd-ax" x="{z:.1f}" y="{TOP - 19:.1f}" '
                   f'text-anchor="middle">no change</text>')
    for i, r in enumerate(regions):
        y = TOP + RH * i + RH / 2
        jul = r["july_night_drift_c"]["value"]
        ann = r["annual_night_drift_c"]["value"]
        weak = r.get("rhetorical_weight") != "assert"
        out.append(f'<text class="nd-n" x="0" y="{y - 4:.1f}">'
                   f'{h(r["display_name"])}</text>')
        # The connector IS the finding. Drawn first so the two marks sit
        # on top of it, and hued only where the channel says assert:
        # the Southwest's gap is real and is the one a reader should
        # weigh least, so it is present in ink rather than in colour.
        # NO CHANNEL HUE HERE, deliberately. tokens.py defines five
        # channel colours and heat is not one of them; I used a
        # var(--heat) that does not exist and would have shipped a
        # broken stroke. A sixth channel colour is a visual-design
        # decision with a contrast bar to clear in both themes, and
        # heat against fire is a real confusion risk, so it is VD's to
        # set rather than mine to invent for one page.
        #
        # The assert / state_with_margin distinction is carried by
        # weight and tone instead, which is sufficient and does not
        # pre-empt the colour decision.
        out.append(f'<line x1="{X(ann):.1f}" y1="{y:.1f}" '
                   f'x2="{X(jul):.1f}" y2="{y:.1f}" '
                   f'stroke="{"var(--ink)" if not weak else "var(--ink-faint)"}" '
                   f'stroke-width="{5 if not weak else 2.5}"/>')
        out.append(f'<circle cx="{X(ann):.1f}" cy="{y:.1f}" r="4.6" '
                   f'fill="var(--paper)" stroke="var(--ink)" '
                   f'stroke-width="1.8"/>')
        out.append(f'<circle cx="{X(jul):.1f}" cy="{y:.1f}" r="5.2" '
                   f'fill="var(--ink)"/>')
        c = r["contrast_c"]["value"]
        # THE LABELLED NUMBER IS THE DRIFT, NOT THE CONTRAST. It was the
        # contrast, and Kristjan's read was "July nights are 0.4 degrees
        # warmer, who cares". Right: +0.40 is a difference of
        # differences, three times smaller than the drift sitting in the
        # same payload, and it is not a sentence. "Italy's July nights
        # are 1.27 C warmer than they were" is.
        #
        # It is also the mislabel I flagged on this axis earlier: the
        # axis said "night warming" while the labelled figure was the
        # gap between two warmings. Same defect, arriving as a product
        # problem rather than a caption one.
        tx = max(X(jul), X(ann)) + 10
        out.append(f'<text class="nd-c" x="{tx:.1f}" y="{y + 1:.1f}">'
                   f'{jul:+.2f} &#176;C</text>')
        # The contrast stays, smaller, as the second beat: it is what
        # makes this more than a warming chart, because one region runs
        # the other way.
        out.append(f'<text class="nd-g" x="{tx:.1f}" y="{y + 13:.1f}">'
                   f'{c:+.2f} vs the year</text>')
        # READ the margin, never compute it. I computed it and got 1.0x
        # against an emitted 1.6x, because there are TWO
        # region_cut_spread_c fields at two levels: one on the July
        # drift (0.12) and one on the contrast (0.075). I reached a
        # level up and divided by the wrong one.
        #
        # That is D-081 exactly, and it is the rule about recomputing
        # outside the payload failing on the same day I wrote it. The
        # payload puts the spread beside the thing it qualifies and
        # emits the ratio too; both protections are lost the moment a
        # renderer does the division itself.
        m = (r.get("contrast_c") or {}).get("margin_over_spread")
        note = f"margin {m:.1f}x" if (weak and m) else ""
        if note:
            out.append(f'<text class="nd-w" x="0" y="{y + 13:.1f}">'
                       f'contrast {h(note)}, the weakest here</text>')
    out.append(f'<text class="nd-ax" x="{PAD_L}" y="{H - 6:.1f}">'
               f'night warming since 1961-1990, &#176;C</text>')
    return (f'<svg class="nd" viewBox="0 0 {W} {H:.0f}" role="img" '
            f'aria-label="Four regions. Open mark is the whole-year night '
            f'warming, filled mark is July, and the gap between them is '
            f'the contrast.">' + "".join(out) + '</svg>')



def render(doc: dict, root_prefix: str = "../") -> str:
    regions = list(doc["regions"].values())
    # Sorted by DRIFT, matching what the headline names and what the
    # large figure on each row shows. It sorted by contrast while the
    # headline named the largest drift, so the first row was not the
    # region in the h1. Ordering has to agree with the quantity the page
    # leads on, or the list quietly argues with the headline.
    regions.sort(key=lambda r: -r["july_night_drift_c"]["value"])
    b = doc["baseline"]
    # The headline names the largest DRIFT and a place, not the largest
    # contrast. A place and a temperature is a sentence; a difference of
    # differences is not.
    lead = max(regions, key=lambda r: r["july_night_drift_c"]["value"])
    lead_name = lead["display_name"]
    lead_drift = lead["july_night_drift_c"]["value"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Summer nights | {h(SITE_NAME)}</title>
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
.eyebrow, .nd text, .foot, .key {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:31px; font-weight:500; line-height:1.18; margin:0 0 12px;
  letter-spacing:-0.015em; max-width:24ch; text-wrap:balance; }}
.stand {{ color:var(--ink-soft); max-width:60ch; margin:0; }}
.nd {{ width:100%; height:auto; display:block; margin:20px 0 4px; }}
.nd-n {{ font-size:12px; fill:var(--ink); }}
.nd-w {{ font-size:10px; fill:var(--ink-faint); }}
.nd-c {{ font-size:14px; fill:var(--ink); font-weight:600; }}
.nd-g {{ font-size:10.5px; fill:var(--ink-faint); }}
.nd-ax {{ font-size:10px; fill:var(--ink-faint); }}
.key {{ font-size:11.5px; color:var(--ink-faint); margin:8px 0 0; }}
/* The attribution tag, from the shared three-state set. Sits above the
   headline because T9 wants it as an element a reader can find, not a
   clause they have to reach the end of a paragraph for. */
.tag {{ display:inline-block; font-family:"{T.FONT_DATA}",monospace;
  font-size:11px; letter-spacing:.05em; padding:2px 8px; margin:0 0 10px; }}
.tag-enso {{ background:var(--tag-loaded-bg); color:var(--tag-loaded-fg); }}
.tag-non_enso {{ background:var(--tag-notlink-bg);
  color:var(--tag-notlink-fg); }}
.tag-pending {{ background:var(--tag-pending-bg);
  color:var(--tag-pending-fg); }}
.note {{ margin:18px 0 0; font-size:14px; color:var(--ink-soft);
  max-width:64ch; }}
.basis {{ margin:22px 0 0; padding:12px 15px; background:var(--paper-sunk);
  font-size:13px; color:var(--ink-soft); max-width:66ch; }}
.foot {{ margin-top:44px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="")}
<main>
  <p class="eyebrow">Heat &middot; regional night warming</p>
  {_attribution_tag(doc.get("attribution"))}
  <h1>July nights over {h(lead_name)} are {lead_drift:.2f} &#176;C warmer
  than they were.</h1>
  <p class="stand">Measured against 1961-1990, across four regions. And
  summer is not moving at the same rate as the rest of the year: in three
  of these four, July nights have drifted further than the annual
  average, while in the US Southwest they have drifted less.</p>

  {_rows(regions)}
  <p class="key">Filled mark and the large figure: how much July nights
    have warmed. Open mark: the same for the whole year. The gap between
    them is the smaller figure.</p>

  <p class="note">Each region is a 1-degree grid box roughly 500 to 900
    km across, land cells only. Nothing here is a claim about any city:
    a regional average and a city are different measurements, and this
    page does not make the second.</p>

  <div class="basis">Monthly means of daily minimum temperature, July
    only, {h(b['early'])} against {h(b['current'])}, {h(b['completeness'])}.
    {h(doc.get('source', ''))}. Held to the pre-registered baseline pair:
    the alternative {h(doc['regions']['iberia']['robustness_alternative_baseline']['pair'])}
    strengthens every region including the Southwest, and is reported as
    robustness rather than swapped in.</div>

  <p class="note">Two 30-year averages differ. This page does not say
    why, and does not combine with any other instrument to produce a
    single distance.</p>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Heat.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; {h(doc.get('evidence_basis', ''))}</div>
</main>
</body>
</html>
"""
