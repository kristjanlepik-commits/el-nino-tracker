"""One crop region: what the payload actually supports, and no more.

The destination the index rows link to, and the page where the shape of
the data bites hardest.

## What a region record contains

    region, value, baseline_mean, rank, of

That is all of it. Five fields, one of which is a name. There is no
per-region time series in this payload, so **the 26-year history that
would make this page obvious cannot be drawn**. A page that drew one
would be inventing 25 numbers to decorate the one it was given.

So the history is stated rather than plotted: worst of 26, at this z,
against a baseline mean of roughly zero. That is honest and it is thin,
and the thinness is visible on the page rather than papered over. If
CRO later emits the per-region series, this page gains a chart and
loses nothing else.

## The distinction that would otherwise mislead

The five instruments belong to the COUNTRY, not to this region. Chad's
water satisfaction and rainfall are national figures, and printing them
under a region heading would imply they were measured here. They are
shown, because they are the only mechanism evidence available, and they
are labelled as national throughout. The region contributes one number
to the page and the page says which one.

## Why the country context is on a region page at all

Because a single region at its worst on record is, by itself, exactly
what chance produces eighty-one times a dekad. What makes Ennedi Est
worth reading is that seven other Chad regions are also at their worst,
which is a fact about Chad rather than about Ennedi Est. A region page
without that context invites a reader to treat one dot as a finding.
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

TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked",
            "pending": "attribution pending"}
TAG_SLUG = {"enso": "loaded", "non_enso": "notlink", "pending": "pending"}


def _fmt(v, unit) -> str:
    """A value in its own unit, because these are five different things.

    The payload carries `unit` per instrument and the first version of
    this page ignored it, printing water satisfaction of 73.4 percent as
    "+73.39" and a temperature of 29 C as "+28.95". A signed two-decimal
    format is right for a z-score and wrong for everything else, and a
    plus sign in front of a percentage asserts a departure that is not
    what the number means. Same class of error as a rank rendered as
    +18.00, and found the same way, by looking at it.
    """
    if v is None:
        return ""
    if unit in ("z-score", "SPI"):
        return f"{v:+.2f}"
    if unit == "percent":
        return f"{v:.0f}%"
    if unit and "C" in unit:
        return f"{v:.1f} \u00b0C"
    return f"{v:,.2f}"


def _peer_strip(regions, focus) -> str:
    """Every region of this country on one axis, this one marked.

    The only comparison the payload supports, and it is the useful one:
    it shows at a glance whether this region is an outlier inside its
    own country or one of many.
    """
    vals = [r["value"] for r in regions]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 0.4)
    lo, hi = lo - span * 0.12, hi + span * 0.12
    W, H = 660, 96
    PAD = 10

    def X(v):
        return PAD + (v - lo) / (hi - lo) * (W - 2 * PAD)

    out = [f'<line x1="{PAD}" y1="58" x2="{W - PAD}" y2="58" '
           f'stroke="var(--rule)" stroke-width="1"/>']
    if lo <= 0 <= hi:
        out.append(f'<line x1="{X(0):.1f}" y1="40" x2="{X(0):.1f}" y2="76" '
                   f'stroke="var(--ink-soft)" stroke-width="1" '
                   f'stroke-dasharray="4 3"/>')
        out.append(f'<text class="rg-s" x="{X(0):.1f}" y="90" '
                   f'text-anchor="middle">its own 25-year average</text>')
    for r in regions:
        x = X(r["value"])
        is_focus = r["region"] == focus
        rec = r.get("rank") == 1
        if is_focus:
            out.append(f'<circle cx="{x:.1f}" cy="58" r="7" '
                       f'fill="var(--crop)"/>')
            out.append(f'<text class="rg-f" x="{x:.1f}" y="34" '
                       f'text-anchor="middle">{h(r["region"])}</text>')
            out.append(f'<text class="rg-fz" x="{x:.1f}" y="20" '
                       f'text-anchor="middle">{r["value"]:+.2f}</text>')
        elif rec:
            # Also at its worst on record: filled, because it is the same
            # kind of thing as the focus rather than background.
            out.append(f'<circle cx="{x:.1f}" cy="58" r="4.2" '
                       f'fill="var(--ink)"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="58" r="4.2" '
                       f'fill="var(--paper)" stroke="var(--ink-faint)" '
                       f'stroke-width="1.3"/>')
    return (f'<svg class="rg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Every crop region of this country on one axis">'
            + "".join(out) + "</svg>")


def render(country: dict, region_name: str, root_prefix: str = "../../") -> str:
    regions = country["regions"]
    reg = next(r for r in regions if r["region"] == region_name)
    at_record = [r for r in regions if r.get("rank") == 1]
    tag = country.get("attribution", "pending")
    slug = TAG_SLUG.get(tag, "pending")
    driver_known = country.get("driver") == "water"

    instruments = "".join(f"""
      <div class="irow">
        <span class="iname">{h(i['name'])}
          <span class="ibase">normally {_fmt(i.get('baseline_mean'), i.get('unit'))}
          &middot; {'lower is worse' if i.get('worse_is') == 'low' else 'higher is worse'}</span></span>
        <span class="ival">{_fmt(i.get('value'), i.get('unit'))}</span>
        <span class="irank">{i.get('rank','')} of {i.get('of','')}</span>
      </div>""" for i in (country.get("instruments") or []))

    quals = "".join(f"""
      <p class="qual"><span class="qk">{h(q.get('kind',''))}</span>
      {h(q.get('text',''))}</p>""" for q in (country.get("qualifiers") or []))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{h(region_name)}, {h(country['place'])} | {h(SITE_NAME)}</title>
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
.eyebrow, .hero, .seclab, .iname, .ival, .irank, .qk, .tag, .rg text,
.foot, .thin {{ font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
h1 {{ font-size:33px; font-weight:500; line-height:1.16;
  letter-spacing:-0.015em; margin:0 0 14px; max-width:22ch;
  text-wrap:balance; }}
.head {{ border-top:3px solid var(--ink); padding-top:14px; margin-top:24px; }}
.hero {{ font-size:44px; font-weight:600; color:var(--crop); margin:0;
  line-height:1; font-variant-numeric:tabular-nums; }}
.sub {{ font-size:12px; color:var(--ink-soft); margin:12px 0 0;
  line-height:1.6; max-width:58ch; }}
/* The history is stated, not plotted, because the payload holds one
   value per region and no series. Saying so is the alternative to
   inventing twenty-five numbers to decorate the one we were given. */
.thin {{ font-size:11.5px; color:var(--ink-faint); margin:10px 0 0; }}
.seclab {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink); margin:40px 0 4px;
  padding-bottom:8px; border-bottom:2.4px solid var(--rule-45); }}
.secsub {{ font-size:13.5px; color:var(--ink-soft); margin:0 0 8px;
  max-width:62ch; }}
.rg {{ width:100%; height:auto; display:block; margin-top:8px; }}
.rg text {{ paint-order:stroke; stroke:var(--paper); stroke-width:2.5;
  stroke-linejoin:round; }}
.rg-s {{ font-size:10px; fill:var(--ink-soft); }}
.rg-f {{ font-size:12px; fill:var(--ink); font-weight:600; }}
.rg-fz {{ font-size:13px; fill:var(--crop); font-weight:600; }}
.irow {{ display:grid; grid-template-columns:1fr 5rem 5rem; gap:14px;
  padding:11px 0; border-bottom:1px solid var(--rule); align-items:baseline; }}
.iname {{ font-size:13.5px; }}
.ibase {{ display:block; font-size:10.5px; color:var(--ink-faint);
  margin-top:2px; }}
.ival {{ font-size:16px; font-weight:600; text-align:right;
  font-variant-numeric:tabular-nums; }}
.irank {{ font-size:11.5px; color:var(--ink-soft); text-align:right; }}
.qual {{ font-size:13.5px; color:var(--ink-soft); margin:12px 0 0;
  max-width:64ch; }}
.qk {{ font-size:9.5px; letter-spacing:0.05em; text-transform:uppercase;
  background:var(--paper-sunk); color:var(--ink-soft); padding:2px 6px;
  margin-right:8px; white-space:nowrap; }}
.tag {{ font-size:10.5px; letter-spacing:0.04em; padding:3px 8px;
  display:inline-block; margin-top:22px; }}
.tag-loaded {{ background:var(--tag-loaded-bg); color:var(--tag-loaded-fg); }}
.tag-notlink {{ background:var(--tag-notlink-bg); color:var(--tag-notlink-fg); }}
.tag-pending {{ background:var(--tag-pending-bg); color:var(--tag-pending-fg); }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
@media (max-width:600px) {{ h1 {{ font-size:26px; max-width:none; }}
  .hero {{ font-size:36px; }} }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow">{h(country['place'])} &middot; {h(region_name)}
    &middot; dekad {h(country['dekad'])}</p>
  <h1>{h(region_name)} is at its {'driest' if driver_known else 'lowest'}
  for this point in the season in twenty-six years.</h1>

  <div class="head">
    <p class="hero">{reg['value']:+.2f}</p>
    <p class="sub">standardised departure of the crop canopy, cumulated
      over the growing season, against this region&rsquo;s own average for
      the same dekad since 2001. Rank {reg['rank']} of {reg['of']}.
      Its own 25-year average is {reg['baseline_mean']:+.2f}.</p>
    <p class="thin">The payload holds one value per region and no series,
      so the twenty-six years behind this rank are not plotted here. The
      rank is what we hold; the history is not.</p>
  </div>

  <p class="seclab">Against every other crop region of {h(country['place'])}</p>
  <p class="secsub">The comparison the data does support. Filled marks are
    regions also at their worst on record, hollow ones are not, and this
    region is the large mark. {len(at_record)} of {len(regions)} are at a
    record low, which is what makes this worth reading: one region alone
    would be unremarkable.</p>
  {_peer_strip(regions, region_name)}

  <p class="seclab">What the country&rsquo;s instruments say</p>
  <p class="secsub">These are NATIONAL figures for {h(country['place'])},
    not measurements of {h(region_name)}. They are the only mechanism
    evidence available and they are shown as national throughout.</p>
  {instruments}

  <p class="seclab">What this does not tell you</p>
  {quals}

  <span class="tag tag-{slug}">{h(TAG_TEXT.get(tag, TAG_TEXT['pending']))}</span>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; authorship {h(country.get('authorship',''))}
    &middot; evidence basis {h(country.get('evidence_basis',''))}</div>
</main>
</body>
</html>
"""
