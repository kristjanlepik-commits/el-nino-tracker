"""A crops country page: every region of it that is at a record low.

Kristjan asked for "country sub-pages for crops" and the index is
already grouped by country, so one page per country holding its regions'
detail satisfies that literally and gives the index one link per group
rather than one per row. 41 pages this dekad rather than 81.

## What is on it that the index cannot carry

The index shows a country's regions as a collapsed list of names and
z-scores, because eighty-one rows of chart would be unreadable. This
page is where the detail goes:

- **Each region against its own 26 years.** `series` is emitted per
  region as of b809f28, which is the thing this page was blocked on. It
  was built once without it and said so on its face rather than
  inventing a history to decorate a five-field row.
- **Every region of the country on one axis**, the marked one included,
  which is the only comparison the payload supports and the one that
  answers "is this region an outlier here, or is the whole country
  like this".

## The claim shapes are enumerated, not sampled

CRO signs off on the template plus every distinct claim shape it can
emit, and a new shape inside an approved template is a new sign-off
rather than a variation. That rule exists because "driest" reached a
live page inside a template that had already been approved.

This page emits: two `statement` shapes (rank-1 and not-rank-1), times
a driver line present or absent, times a qualifiers list empty or not.
Eight in total, and `claim_shapes()` prints them so the sign-off
conversation is a list rather than a page-by-page read.
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
from templates.crops_region import _fmt, _peer_strip          # noqa: E402


def slugify(name: str) -> str:
    import re
    s = re.sub(r"[^\w\s-]", "", name.lower().replace("'", "")).strip()
    return re.sub(r"[-\s]+", "-", s)


def _series_chart(series: dict, this_year: str = "2026") -> str:
    """One region against its own record, year by year.

    Bars rather than a line: these are discrete annual observations of
    the same dekad, not a continuous signal, and a line would imply
    values between them that were never measured.

    The current year takes the channel hue ONLY when it is the lowest in
    the series. A record year drawn in crop and an ordinary year drawn
    in ink is the calibration rule applied to a bar, and it means the
    colour carries the finding rather than the recency.
    """
    if not series:
        return ""
    years = sorted(series)
    vals = [series[y] for y in years]
    lo, hi = min(vals + [0.0]), max(vals + [0.0])
    span = max(hi - lo, 0.6)
    W, H, PAD_T, PAD_B, PAD_L, PAD_R = 660, 132, 16, 24, 8, 8
    slot = (W - PAD_L - PAD_R) / len(years)
    bw = min(slot * 0.62, 15.0)
    worst = min(vals)

    def Y(v):
        return PAD_T + (hi - v) / (hi - lo + span * 0.12) * (H - PAD_T - PAD_B)

    zero = Y(0.0)
    out = [f'<line x1="{PAD_L}" y1="{zero:.1f}" x2="{W - PAD_R}" '
           f'y2="{zero:.1f}" stroke="var(--rule)" stroke-width="1"/>']
    for i, y in enumerate(years):
        v = series[y]
        cx = PAD_L + slot * (i + 0.5)
        top, bot = (Y(v), zero) if v < 0 else (zero, Y(v))
        is_now = (y == this_year)
        hue = ("var(--crop)" if (is_now and v <= worst) else
               "var(--ink)" if is_now else "var(--ink-faint)")
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{min(top, bot):.1f}" '
                   f'width="{bw:.1f}" height="{abs(bot - top):.1f}" '
                   f'fill="{hue}"/>')
    for i, y in enumerate(years):
        if y in (years[0], years[-1]):
            cx = PAD_L + slot * (i + 0.5)
            anchor = "start" if y == years[0] else "end"
            out.append(f'<text class="sc-x" x="{cx:.1f}" y="{H - 6}" '
                       f'text-anchor="{anchor}">{h(y)}</text>')
    return (f'<svg class="sc" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="This region in every year of the record for the '
            f'same point in the season">' + "".join(out) + '</svg>')


def claim_shapes(country: dict) -> list:
    """Every distinct sentence shape this page can emit, for sign-off.

    CRO's gate is the template plus every claim shape, and showing them
    a list is both cheaper and closer to where the failure lives than
    showing them pages. "Driest" was a shape, not a page.
    """
    import re
    seen = {}
    # ONLY the regions this page actually renders. It iterated every
    # region of the country, including the ones the page never shows,
    # and reported "Nth lowest of N" as an emitted shape when these
    # pages carry rank-1 regions exclusively and therefore only ever
    # emit "lowest of N". That sent CRO a gate covering sentences the
    # template cannot produce, which is the opposite failure to the one
    # the gate exists for and just as useless: a sign-off is worthless
    # if it is not on the thing that ships.
    for r in [x for x in (country.get("regions") or []) if x.get("rank") == 1]:
        # Collapse the ordinal suffix too. "1st", "2nd" and "4th lowest"
        # are one shape, and leaving them distinct inflated the list
        # from four shapes to ten, which would have sent CRO a longer
        # sign-off than the template actually needs.
        st = re.sub(r"\bN(?:st|nd|rd|th)\b", "Nth",
                    re.sub(r"[-+]?\d[\d,.]*", "N",
                           re.sub(r"\b(?:19|20)\d\d\b", "YYYY",
                                  r.get("statement") or "")))
        key = (st, bool(r.get("driver") == "water"),
               bool(r.get("qualifiers")))
        seen.setdefault(key, r.get("region"))
    return [{"statement": k[0], "driver_line": k[1], "qualifiers": k[2],
             "example": v} for k, v in seen.items()]


def _region_block(r: dict, all_regions: list, driver: str) -> str:
    """One region. `driver` is the REGION's, never the country's.

    This read the country field and it is the Cairo fault one level
    down: a country property worn by a region. Namibia is water-driven
    as a country; Hardap is not, at 0.15 against the 0.30 the test
    requires, and Hardap was one of my own two named examples for this
    shape, which is how CRO found it.

    Not a stray case either: 677 of 2,122 regions, 32 percent, have a
    driver differing from their country's. A third of every region row
    would have carried a claim that does not hold there. The word in the
    sentence is "here", and it has to be true of here.
    """
    q = r.get("qualifiers") or []
    quals = ("".join(f'<li>{h(x)}</li>' for x in q)
             if q else "")
    drv = ('<p class="rgdrv">Vegetation here usually tracks water '
           'availability.</p>' if r.get("driver") == "water" else "")
    return f"""
      <section class="rg" id="{h(slugify(r['region']))}">
        <h2>{h(r['region'])}</h2>
        <p class="rgval">{h(_fmt(r.get('value'), 'z-score'))}
          <span class="rgstate">{h(r.get('statement', ''))}</span></p>
        {drv}
        {_series_chart(r.get('series') or {})}
        <p class="rgbasis">{h(r.get('basis', ''))}</p>
        {f'<ul class="rgq">{quals}</ul>' if quals else ''}
      </section>"""


def render(country: dict, root_prefix: str = "../../") -> str:
    regions = sorted((country.get("regions") or []),
                     key=lambda r: r.get("value", 0))
    lows = [r for r in regions if r.get("rank") == 1]
    name = country["place"]
    units = country.get("crop_units")
    cb = country.get("chance_baseline") or {}

    # The count sentence carries its own baseline or it does not appear.
    # Four channels reached the same finding today: a count of
    # threshold-crossings is not a finding on its own.
    if cb.get("recent_max") is not None:
        stand = (f"{len(lows)} of {units} crop regions in {name} are at "
                 f"their worst on record for this point in the season. "
                 f"Its highest in any previous year was "
                 f"{cb['recent_max']}, on a recent average of "
                 f"{cb['recent_mean']:g}.")
    else:
        stand = (f"{len(lows)} of {units} crop regions in {name} are at "
                 f"their worst on record for this point in the season.")

    blocks = "".join(_region_block(r, regions, r.get("driver"))
                     for r in lows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{h(name)} | Crops | {h(SITE_NAME)}</title>
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
.eyebrow, .rgval, .foot, .sc text, .rgbasis {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:31px; font-weight:500; line-height:1.18; margin:0 0 12px;
  letter-spacing:-0.015em; }}
.stand {{ color:var(--ink-soft); max-width:60ch; margin:0; }}
.rg {{ margin-top:38px; padding-top:14px;
  border-top:1px solid var(--rule); }}
.rg h2 {{ font-size:19px; font-weight:600; margin:0 0 4px; }}
.rgval {{ font-size:26px; color:var(--crop); margin:0; font-weight:600;
  font-variant-numeric:tabular-nums; }}
.rgstate {{ display:block; font-size:12.5px; color:var(--ink-soft);
  font-weight:400; margin-top:3px; }}
.rgdrv {{ margin:8px 0 0; font-size:13.5px; color:var(--ink-faint); }}
.sc {{ width:100%; height:auto; display:block; margin:12px 0 2px; }}
.sc-x {{ font-size:10px; fill:var(--ink-faint); }}
.rgbasis {{ margin:4px 0 0; font-size:11px; color:var(--ink-faint); }}
.rgq {{ margin:8px 0 0; padding-left:18px; font-size:13.5px;
  color:var(--ink-soft); max-width:62ch; }}
.peers {{ margin-top:34px; }}
.note {{ margin:16px 0 0; font-size:13.5px; color:var(--ink-soft);
  max-width:64ch; }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow"><a href="{h(root_prefix)}crops/">Crops</a>
    &middot; dekad {h(country.get('dekad', ''))}</p>
  <h1>{h(name)}</h1>
  <p class="stand">{h(stand)}</p>

  <p class="eyebrow" style="margin-top:30px">Every region of {h(name)},
    worst to least</p>
  <div class="peers">{_peer_strip(regions, None)}</div>
  <p class="note">The regions below are the ones at their worst on
    record. The axis above carries every region of the country, so a
    single deep region inside an otherwise ordinary country reads
    differently from a country where the whole distribution has
    moved.</p>

  {blocks}

  <p class="note">This measurement is of the crop canopy and not of what
    stressed it: heat, drought, disease and late planting are not
    separable here, which is why no claim on this page names a cause.</p>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
  </div>
</main>
</body>
</html>
"""
