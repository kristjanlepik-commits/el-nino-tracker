"""The crops pair page, built against CRO's proposed payload shape.

Second implementation of the D-030 handoff, and the one that decides
which parts of the fire shape were real. Everything here consumes
`crops/PAYLOAD_PROPOSAL.md` as proposed, so building it is also the
review: a shape that cannot be rendered is not a shape.

What crops proves that fires could not:

  instruments is a LIST, not two fixed keys. Fires has two, crops has
  six per pair, and they disagree, which is the point of having six.
  `detections` and `area` did not survive contact with a second channel.

  magnitude is kind-tagged. Crops ranks Nth of 26, fires uses a ratio,
  El Nino uses a signed anomaly with no multiple at all. `basis` is
  required, so a comparison cannot lose its basis in layout.

  qualifiers is a list of {kind, text} on the instrument block. Three
  caveats concatenated is prose, and prose is what D-051 exists to
  stop. An EMPTY list is a positive assertion that the channel checked
  and none applies; an ABSENT key is a bug and should fail the build.

  a suppressed pair is rendered as suppressed, never omitted. CRO
  corrected me here using my own argument: omission makes the gate
  invisible in exactly the way I objected to, so the page says three of
  nineteen pairs are not yet readable rather than quietly showing
  sixteen.

## The calibration case

Spain wheat ranks 18 of 26 with direction "low", which means it is in
the better half of its record: a good result. D-043 requires this to
read as legibly as a crisis would, so the page states it plainly and
spends no channel hue on it. A crops channel that only knew how to look
worried would be useless, because most pairs most weeks are fine.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                          # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,  # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)
from templates.page_head import head_meta                    # noqa: E402

TAG_TEXT = {"enso": "ENSO-loaded window", "non_enso": "not ENSO-linked",
            "pending": "attribution pending"}
TAG_SLUG = {"enso": "loaded", "non_enso": "notlink", "pending": "pending"}

AUTHORSHIP = {"agency": "agency figure",
              "tls_built": "built by us from agency data"}


def magnitude_line(m: dict) -> tuple:
    """The headline figure and whether it is remarkable.

    Returns (display, basis, remarkable). `direction` says which end is
    bad and it differs by pair, so it is read rather than assumed: rank
    18 of 26 is good when direction is "low" and alarming when it is
    "high", and no amount of layout can recover that if it is dropped.
    """
    kind = m.get("kind")
    if kind == "rank":
        v, of = m.get("value"), m.get("of")
        display = f"{v} of {of}"
        half = (of or 0) / 2.0
        remarkable = (v > half) if m.get("direction") == "high" else (v <= half)
        # For a rank, "remarkable" means near the bad end.
        remarkable = (v >= (of - half / 2)) if m.get("direction") == "high" \
            else (v <= half / 2)
    elif kind == "multiple":
        display = f'{m.get("value"):.1f}×'
        remarkable = (m.get("value") or 0) >= 2.0
    else:
        display = f'{m.get("value"):+.2f}'
        remarkable = abs(m.get("value") or 0) >= 1.0
    return display, m.get("basis", ""), remarkable


def _qualifiers(qs) -> str:
    """An empty list renders nothing, deliberately: it is the channel
    asserting it checked. A missing key is a build failure upstream, not
    something to paper over here."""
    if not qs:
        return ""
    return ('<div class="quals">' + "".join(
        f'<div class="qual"><span class="qkind">{h(q.get("kind", ""))}</span>'
        f'<span class="qtext">{h(q.get("text", ""))}</span></div>'
        for q in qs) + "</div>")


def _instrument(ins: dict) -> str:
    z = ins.get("z")
    has = ins.get("value") is not None
    # An instrument value needs its own kind for the same reason
    # `magnitude` does, and the proposal only tags the latter. A rank
    # pushed through the z-score formatter rendered as "+18.00", which
    # is a signed anomaly of eighteen standard deviations rather than
    # eighteenth of twenty-six. Found by building it. Until the field
    # exists, an explicit display string wins over the default format.
    shown = ins.get("value_display")
    if shown is None and has:
        shown = f'{ins["value"]:+.2f}'
    return f"""
      <div class="irow{'' if has else ' novalue'}">
        <div class="iname">{h(ins.get("name", ""))}</div>
        <div class="ival">{h(shown) if has else
                           '<span class="pend">not in this payload</span>'}</div>
        <div class="iz">{f'z {z:+.2f}' if z is not None else ''}</div>
        <div class="imeta">
          {h(ins.get("source", ""))}
          {f'&middot; as of {h(ins["as_of"])}' if ins.get("as_of") else ''}
          <span class="auth">{h(AUTHORSHIP.get(ins.get("authorship", ""),
                                               ins.get("authorship", "")))}</span>
        </div>
        {_qualifiers(ins.get("qualifiers"))}
      </div>"""


def _suppressed(rows) -> str:
    if not rows:
        return ""
    out = "".join(f"""
      <div class="suprow">
        <div class="supname">{h(r.get("pair", ""))}</div>
        <div class="supwhen">readable from {h(str(r.get("publishable_from", "")))}</div>
        <div class="supwhy">{h(r.get("suppressed_because", ""))}</div>
      </div>""" for r in rows)
    return (f'<p class="seclab">Not yet readable this dekad</p>'
            f'<p class="secsub">These pairs exist and are being tracked. '
            f'Their signal does not yet predict the outcome well enough '
            f'to publish, and the channel says so rather than showing a '
            f'number or dropping the row. A page that silently omitted '
            f'them would leave a reader unable to tell whether the gate '
            f'ran.</p>{out}')


# INDEXABLE SINCE D-172, 2026-08-17. The tag that was here arrived by copy
# from the fires template in da318b1, one day before crops launched, and no
# ledger entry ever decided it. It was a contradiction rather than a
# posture: the front page is indexable, carries /crops/ in the nav and links
# eleven crops country pages by absolute URL, so the tag removed discovery
# without removing exposure.
#
# In Python rather than in an HTML comment for the reason recorded in
# templates/country_page.py: as markup it ships the word into every page and
# a grep for the tag then finds the explanation instead.
def render(doc: dict, root_prefix: str = "../../") -> str:
    tag = doc.get("attribution", "pending")
    slug = TAG_SLUG.get(tag, "pending")
    mag = doc.get("magnitude") or {}
    display, basis, remarkable = magnitude_line(mag)
    hue = "var(--crop)" if remarkable else "var(--ink)"
    instruments = doc.get("instruments") or []
    withval = [i for i in instruments if i.get("value") is not None]
    # Prototype payload shape (PAYLOAD_PROPOSAL.md); no builder has ever
    # called this template, so the slug and path below are provisional
    # and cost nothing to be wrong yet.
    pair_slug = "-".join(
        (doc.get("pair", "") or "pair").lower().split())
    page_path = f"/crops/pairs/{pair_slug}/"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_meta(title=f'{doc.get("pair", "")} | {SITE_NAME}',
           description=doc.get("claim", ""), path=page_path)}
<title>{h(doc.get("pair", ""))} | {h(SITE_NAME)}</title>
<style>
{T.font_faces_css(root_prefix + "fonts/")}
:root {{
{T.css_variables()}
}}
@media (prefers-color-scheme: dark) {{ :root {{
{T.css_variables(dark=True)}
}} }}
:root[data-theme="dark"] {{
{T.css_variables(dark=True)}
}}
* {{ box-sizing: border-box; }}
:root {{ --shell-max: 880px; --shell-pad: 26px; }}
body {{ margin: 0; background: var(--paper); color: var(--ink);
  font-family: "{T.FONT_PROSE}", Georgia, serif; font-size: 16.5px;
  line-height: 1.55; }}
main {{ max-width: 880px; margin: 0 auto; padding: 26px 26px 80px; }}
{SITE_MASTHEAD_CSS}
.eyebrow, .hero, .seclab, .iname, .ival, .iz, .imeta, .qkind, .tag,
.supname, .supwhen, .foot, .basis {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); margin: 24px 0 10px; }}
h1 {{ font-size: 36px; font-weight: 500; line-height: 1.15;
  letter-spacing: -0.018em; margin: 0 0 16px; max-width: 22ch;
  text-wrap: balance; }}
.head {{ border-top: 3px solid var(--ink); padding-top: 14px;
  margin-top: 26px; }}
.hero {{ font-size: 40px; font-weight: 600; letter-spacing: -0.02em;
  color: {hue}; line-height: 1; font-variant-numeric: tabular-nums; }}
/* The basis is required by the payload and printed with the figure, so
   a comparison cannot lose it in layout. */
.basis {{ font-size: 11.5px; color: var(--ink-soft); margin: 10px 0 0; }}
.seclab {{ font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink); margin: 40px 0 4px;
  padding-bottom: 8px; border-bottom: 2.4px solid var(--rule-45); }}
.secsub {{ font-size: 13.5px; color: var(--ink-soft); margin: 0 0 6px;
  max-width: 62ch; }}

.irow {{ display: grid; grid-template-columns: 1fr 5rem 5rem;
  gap: 14px 18px; padding: 14px 0; border-bottom: 1px solid var(--rule);
  align-items: baseline; }}
.iname {{ font-size: 13.5px; }}
.ival {{ font-size: 18px; font-weight: 600; text-align: right;
  font-variant-numeric: tabular-nums; }}
.iz {{ font-size: 12px; color: var(--ink-soft); text-align: right; }}
.imeta {{ grid-column: 1 / -1; font-size: 11px; color: var(--ink-faint);
  margin-top: -6px; }}
/* Two authorship values on one row is the case the field exists for:
   the ASAP number is the agency's, the rank against 25 years is ours. */
.auth {{ margin-left: 8px; padding: 1px 6px; background: var(--paper-sunk);
  color: var(--ink-soft); }}
.novalue .ival {{ font-weight: 400; }}
.pend {{ font-size: 11.5px; color: var(--ink-faint); }}

/* A qualifier is computed from the condition that triggered it, so it
   cannot outlive that condition. Rendered per instrument, never
   concatenated into prose. */
.quals {{ grid-column: 1 / -1; margin-top: 4px; }}
.qual {{ display: flex; gap: 10px; align-items: baseline;
  padding: 6px 0 0; }}
.qkind {{ font-size: 9.5px; letter-spacing: 0.06em; text-transform: uppercase;
  background: var(--paper-sunk); color: var(--ink-soft); padding: 2px 6px;
  white-space: nowrap; }}
.qtext {{ font-size: 13px; color: var(--ink-soft); max-width: 60ch; }}

.suprow {{ display: grid; grid-template-columns: 1fr auto;
  gap: 6px 18px; padding: 14px 0; border-bottom: 1px solid var(--rule); }}
.supname {{ font-size: 15px; }}
.supwhen {{ font-size: 11.5px; color: var(--ink-soft); }}
.supwhy {{ grid-column: 1 / -1; font-size: 13.5px; color: var(--ink-soft);
  max-width: 66ch; }}

.tagrow {{ display: flex; justify-content: flex-end; margin: 30px 0 0; }}
.tag {{ font-size: 10.5px; letter-spacing: 0.04em; padding: 3px 8px; }}
.tag-loaded {{ background: var(--tag-loaded-bg); color: var(--tag-loaded-fg); }}
.tag-notlink {{ background: var(--tag-notlink-bg); color: var(--tag-notlink-fg); }}
.tag-pending {{ background: var(--tag-pending-bg); color: var(--tag-pending-fg); }}
.foot {{ margin-top: 46px; padding-top: 14px;
  border-top: 1px solid var(--ink); font-size: 11.5px; color: var(--ink-faint); }}
@media (max-width: 700px) {{
  .irow {{ grid-template-columns: 1fr auto; }}
  h1 {{ font-size: 27px; max-width: none; }}
}}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="crop")}
<main>
  <p class="eyebrow">{h(doc.get("pair", ""))} &middot;
     {h(doc.get("dekad_label", ""))}</p>
  <h1>{h(doc.get("claim", ""))}</h1>

  <div class="head">
    <p class="hero">{h(display)}</p>
    <p class="basis">rank against {h(basis)}, where
      {'a high rank is the bad end' if mag.get('direction') == 'high'
       else 'a low rank is the good end'}</p>
  </div>

  <p class="seclab">The six instruments</p>
  <p class="secsub">Six measurements of the same season that do not have
    to agree. Each carries its own baseline, its own source and its own
    authorship, and the rank above is built by us from them rather than
    published by any one agency.</p>
  {''.join(_instrument(i) for i in instruments)}

  {_suppressed(doc.get("suppressed") or [])}

  <div class="tagrow"><span class="tag tag-{slug}">
    {h(TAG_TEXT.get(tag, TAG_TEXT["pending"]))}</span></div>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Crops.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; {len(withval)} of {len(instruments)} instruments carry a
    value in this payload</div>
</main>
</body>
</html>
"""
