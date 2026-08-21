"""The latency map: when a damage figure will exist, and who will publish it.

The question is one a reader has without knowing they have it. After an
event, why does nobody know what it cost? This answers it by hazard and
territory, and the answer is frequently "nobody will ever say".

## Why a timeline rather than a table

Every row is the same axis, days after the event, so the rows compare
by eye: European windstorm has four dated commitments inside a year,
Southern Africa drought has none at any horizon. A table of dates would
carry the same values and none of that comparison, because the reader
would have to hold seven number sets in their head to see the shape.

## The hard part: a step with no date

Several estimators publish no schedule. Those steps have offset_days
None, which means they cannot be placed on a timeline at all. That is
not missing data to be hidden or guessed at; it IS the finding, and it
is the reason the page exists. So undated steps sit in their own column
past the axis end, under a heading that says no date is committed. A
row with nothing on the timeline and three entries in that column is
telling the reader something precise.

## Rows with nothing anywhere

Southern Africa drought has two steps and neither is dated. The
timeline is empty and the emptiness is the result, which is the same
problem the crops null posed: an empty frame reads as a broken page.
Same answer as there. The axis, the settlement horizon and the
year-one marker are drawn on every row whether or not anything sits on
them, so the reader can see the scale the row is empty against.

## Marks

Three schedule bases, and the shape language is the one the null
component already teaches: filled is firmest, open is inferred, ringed
is conditional. This is a DIFFERENT taxonomy from the D-033 evidence
tiers and the legend says so in words, but the ranking is parallel and
a reader who has learned one reads the other.
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
from templates.page_head import head_meta                      # noqa: E402

BASIS_MARK = {"published_schedule": "firm",
              "observed_practice": "inferred",
              "conditional": "conditional"}
BASIS_WORD = {"published_schedule": "a dated commitment",
              "observed_practice": "inferred from repeated behaviour",
              "conditional": "only if triggered"}
ABSENCE_WORD = {
    "below_threshold": "watched, and below the publishing threshold",
    "outside_coverage": "not covered by any estimator",
    "not_yet_valid": "exists, but before its earliest valid point",
}


def _mark(x, y, kind, r=4.6):
    if kind == "inferred":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                f'fill="var(--paper)" stroke="var(--ink)" stroke-width="1.5"/>')
    if kind == "conditional":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="var(--ink)"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r - 2.2:.1f}" '
                f'fill="var(--paper)"/>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="var(--ink)"/>'


def latency_rows(entries, max_days=460) -> str:
    W = 680
    LAB_W, UNDATED_W = 196, 104
    AX_L = LAB_W
    AX_R = W - UNDATED_W - 12
    ROW_H = 52
    H = 42 + ROW_H * len(entries) + 16

    def X(d):
        return AX_L + min(d, max_days) / max_days * (AX_R - AX_L)

    out = []
    # The axis is drawn on every row whether or not anything sits on it,
    # so a row with nothing has a visible scale to be empty against.
    for d, lab in ((0, "event"), (90, "3 mo"), (180, "6 mo"),
                   (365, "1 yr"), (max_days, "later")):
        x = X(d)
        out.append(f'<line x1="{x:.1f}" y1="34" x2="{x:.1f}" y2="{H - 14}" '
                   f'stroke="var(--rule)" stroke-width="0.8"/>')
        out.append(f'<text class="lm-ax" x="{x:.1f}" y="26" '
                   f'text-anchor="middle">{h(lab)}</text>')
    # "later" and this header sat on the same baseline and overlapped.
    out.append(f'<text class="lm-ax" x="{AX_R + 10}" y="14">undated</text>')
    out.append(f'<line x1="{AX_R + 6:.1f}" y1="34" x2="{AX_R + 6:.1f}" '
               f'y2="{H - 14}" stroke="var(--ink-faint)" stroke-width="1" '
               f'stroke-dasharray="3 3"/>')

    for i, e in enumerate(entries):
        y = 42 + ROW_H * i + ROW_H / 2
        seq = e.get("sequence") or []
        dated = [s for s in seq if s.get("offset_days") is not None]
        undated = [s for s in seq if s.get("offset_days") is None]

        lab = e["label"]
        if len(lab) > 30:
            lab = lab[:30].rsplit(" ", 1)[0] + "\u2026"
        out.append(f'<text class="lm-lab" x="0" y="{y + 16:.1f}">'
                   f'{h(lab)}</text>')
        out.append(f'<line x1="{AX_L}" y1="{y + 12:.1f}" x2="{AX_R:.1f}" '
                   f'y2="{y + 12:.1f}" stroke="var(--rule-45)" '
                   f'stroke-width="1"/>')

        settles = (e.get("settles") or {}).get("value_days")
        if settles:
            sx = X(settles)
            out.append(f'<line x1="{sx:.1f}" y1="{y + 4:.1f}" x2="{sx:.1f}" '
                       f'y2="{y + 20:.1f}" stroke="var(--ink)" '
                       f'stroke-width="2.4"/>')

        for s in dated:
            out.append(_mark(X(s["offset_days"]), y + 12,
                             BASIS_MARK.get(s.get("basis"), "firm")))
        if dated:
            first = min(s["offset_days"] for s in dated)
            out.append(f'<text class="lm-first" x="{X(first):.1f}" '
                       f'y="{y + 27:.1f}" text-anchor="middle">'
                       f'day {first}</text>')
        else:
            out.append(f'<text class="lm-none" x="{(AX_L + AX_R) / 2:.1f}" '
                       f'y="{y + 16:.1f}" text-anchor="middle">'
                       f'nothing dated, at any horizon</text>')

        if undated:
            out.append(f'<text class="lm-un" x="{AX_R + 12}" '
                       f'y="{y + 16:.1f}">{len(undated)} '
                       f'{"source" if len(undated) == 1 else "sources"}</text>')

    return (f'<svg class="lm" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="When each estimator publishes, by hazard and '
            f'territory, in days after the event">' + "".join(out) + '</svg>')


# NOINDEX, unchanged by this pass. This template has never rendered a
# published page; the tag costs nothing today and stays until the econ
# chat is ready to ship it, per D-175's rule against deciding indexing
# on someone else's behalf.
def render(doc: dict, root_prefix: str = "../../") -> str:
    entries = doc.get("entries") or []
    hole = next((e for e in entries if e.get("editorial_note")), None)

    detail = ""
    for e in entries:
        ab = e.get("absence") or e.get("absence_meaning") or {}
        settles = e.get("settles") or {}
        detail += f"""
      <div class="lrow">
        <div class="lname">{h(e["label"])}</div>
        <div class="lbody">
          <p class="lsettle"><b>Settles:</b> {h(str(settles.get("label", "unknown")))}</p>
          <p class="lnote">{h(e.get("coverage_note", ""))}</p>
          <p class="labs"><span class="abk">{h(ABSENCE_WORD.get(ab.get("reason"), ab.get("reason", "")))}</span>
            {h(ab.get("note", ""))}</p>
        </div>
      </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_meta(title=f"When will anyone know what it cost | {SITE_NAME}",
           description=doc.get("question", "") or
           "The latency map: when a damage figure will exist, and who "
           "will publish it, by hazard and territory.",
           path="/econ/latency/", robots="noindex")}
<title>When will anyone know what it cost | {h(SITE_NAME)}</title>
<style>
{T.font_faces_css(root_prefix + "fonts/")}
:root {{ {T.css_variables()} }}
@media (prefers-color-scheme: dark) {{ :root {{ {T.css_variables(dark=True)} }} }}
* {{ box-sizing: border-box; }}
:root {{ --shell-max: 900px; --shell-pad: 24px; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font-family:"{T.FONT_PROSE}",Georgia,serif; font-size:16.5px; line-height:1.55; }}
main {{ max-width:900px; margin:0 auto; padding:24px 24px 80px; }}
{SITE_MASTHEAD_CSS}
.eyebrow, .lm text, .lname, .abk, .foot, .lgd {{
  font-family:"{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink-faint); margin:22px 0 10px; }}
.hl {{ font-size:27px; line-height:1.22; letter-spacing:-0.014em;
  font-weight:500; margin:0; max-width:26ch; text-wrap:balance; }}
.hl + .hl {{ margin-top:14px; }}
.stand {{ color:var(--ink-soft); max-width:60ch; margin:18px 0 0; }}
.lm {{ width:100%; height:auto; display:block; margin-top:30px; }}
.lm text {{ paint-order:stroke; stroke:var(--paper); stroke-width:2.5;
  stroke-linejoin:round; }}
.lm-ax {{ font-size:10px; fill:var(--ink-faint); }}
.lm-lab {{ font-size:11.5px; fill:var(--ink); }}
.lm-first {{ font-size:10px; fill:var(--ink-soft); }}
/* An empty row is a result and says so in the frame, rather than
   leaving the reader to decide whether the page failed to load. */
.lm-none {{ font-size:11px; fill:var(--ink-soft); font-style:italic; }}
.lm-un {{ font-size:10.5px; fill:var(--ink-soft); }}
.lgd {{ font-size:11.5px; color:var(--ink-soft); margin:14px 0 0; }}
.lgd b {{ color:var(--ink); font-weight:500; }}
.seclab {{ font-size:11px; letter-spacing:{T.TRACK_LABEL}em;
  text-transform:uppercase; color:var(--ink); margin:44px 0 4px;
  padding-bottom:8px; border-bottom:2.4px solid var(--rule-45);
  font-family:"{T.FONT_DATA}",monospace; }}
.lrow {{ display:grid; grid-template-columns:12rem 1fr; gap:20px;
  padding:16px 0; border-bottom:1px solid var(--rule); }}
.lname {{ font-size:13px; }}
.lsettle, .lnote, .labs {{ margin:0 0 8px; font-size:14px;
  color:var(--ink-soft); max-width:62ch; }}
.lsettle b {{ color:var(--ink); font-weight:500; }}
/* The three silences look identical in a payload and mean opposite
   things, so each is named in words before its note. None is styled as
   a warning: a coverage hole is a fact about the record. */
.abk {{ font-size:10px; letter-spacing:0.04em; text-transform:uppercase;
  background:var(--paper-sunk); color:var(--ink-soft); padding:2px 6px;
  margin-right:8px; white-space:nowrap; }}
.hole {{ margin-top:30px; padding-left:16px;
  border-left:3px solid var(--damage); }}
.hole p {{ margin:0; max-width:60ch; }}
.foot {{ margin-top:46px; padding-top:14px; border-top:1px solid var(--ink);
  font-size:11.5px; color:var(--ink-faint); }}
@media (max-width:700px) {{ .lrow {{ grid-template-columns:1fr; gap:6px; }}
  .hl {{ font-size:23px; }} }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="damage")}
<main>
  <p class="eyebrow">Damages &middot; who publishes what, and when</p>
  <p class="hl">After a climate event, when will anyone credible say what
  it cost?</p>
  <p class="hl">For most of the world, the honest answer is never.</p>
  <p class="stand">{h(doc.get("question", ""))} Each row is one hazard in one
  territory. The axis is days after the event. A mark is a point at which
  some named body publishes a figure, and an empty row is a place where
  nobody has committed to publishing anything at all.</p>

  {latency_rows(entries)}

  <p class="lgd"><b>Filled</b> a dated commitment the estimator publishes
  itself &middot; <b>open</b> inferred from repeated behaviour, not promised
  &middot; <b>ringed</b> happens only if triggered. The heavy tick is where a
  figure stops moving. This is a schedule basis, not the evidence basis used
  elsewhere on the site.</p>

  {(f'<div class="hole"><p>{h(hole["editorial_note"])}</p></div>'
    if hole and hole.get("editorial_note") else "")}

  <p class="seclab">Row by row, and what each silence means</p>
  {detail}

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Damages.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; evidence basis {h(doc.get("evidence_basis", ""))},
    authorship {h(doc.get("authorship", ""))}</div>
</main>
</body>
</html>
"""
