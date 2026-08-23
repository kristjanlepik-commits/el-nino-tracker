"""The fast-reaction template: one question, one baseline, one chart.

D-030 condition 1 makes this the design chat's first deliverable, and
D-029 defines the format: one question ("how bad is this compared to
historical?"), one baseline, one citable chart, named sources, an
attribution tag, shipped in about a day.

## What makes this a template rather than a page with variables

The visual chat's test, and it is the right one: a template reviewed
against one channel encodes that channel's assumptions. Fires think in
multiples of a mean, in counts, over a 15-year satellite record. El Nino
has no multiple at all; its magnitude is an anomaly in degrees that can
be negative. So this renders both, and `validate.py` alongside it builds
a fire week and an ONI reading from real committed data every run. If a
change makes one of them look wrong, that is the template failing, not
the data.

The two differences that forced actual generality:

  magnitude series   counts, zero-based, baseline is a positive mean
  diverging series   anomalies, zero-centred, can run negative, and the
                     baseline is a threshold rather than an average

Everything else (hue, labels, source, attribution) was already data.

## The chart is the named fallback, deliberately

D-030's escalation rule says a piece ships in the generic template with
a plainer chart or it does not ship. The visual chat's objection was
that "plainer" decided under deadline is how a design system erodes, so
the fallback is named in advance and it is this: a single series against
its baseline. Every channel has a current value and a historical
baseline, so every channel can fall into this form. "Plainer" is a
lookup, not a judgement call.

## The handoff

`render()` takes a dict and returns HTML. It never imports a channel
module, never reads a channel's data files, and never converts units.
The shape is discovered rather than specified (platform's framing) and
is not a contract until a third case has shown which parts are stable.
`PIECE_KEYS` documents what is currently read.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from templates.page_head import head_meta
sys.path.insert(0, str(ROOT))

import tokens as T                                    # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,  # noqa: E402
                       SITE_NAME, h, site_masthead)

# The three fixed attribution strings (T9). Never freeform: a fourth
# state would be a new editorial claim, not a new label.
TAG_TEXT = {
    "enso": "ENSO-loaded window",
    "non_enso": "not ENSO-linked",
    "pending": "attribution pending",
}

PIECE_KEYS = """
channel      str, key in tokens' channel hues; drives colour only
region        str, what the piece is about ("France", "Nino 3.4")
window        str, the period in words
claim         str, the headline at display size
standfirst    str, one paragraph under the claim
value         {display, caption}
chart         {label, series[{x,y}], current_x, baseline{value,label},
               unit, diverging, annotations[{x,text}]}
source        {name, detail, as_of}
attribution   one of enso | non_enso | pending
notes         {what_this_is, what_this_is_not}
"""


def _fmt(v: float, diverging: bool, dp=None) -> str:
    """The value as the chart should print it.

    dp COMES FROM THE CHART because the right precision is a property of
    the quantity, not of the renderer. Whole numbers are right for
    millimetres of rain and days of heat; they turned Lima's 21.7 C into
    22, on the bar the piece is about. A tenth of a degree is the
    difference between this August and 1997.
    """
    if diverging:
        return f"{v:+.{1 if dp is None else dp}f}"
    if dp is not None:
        return f"{v:,.{dp}f}"
    return f"{v:,.0f}"


def _record_strip(chart: dict, hue: str) -> str:
    """The record on its own axis, as a tally. VD's replacement for the bars.

    THE BAR CHART WAS GENERIC BECAUSE IT ANSWERED THE WRONG QUESTION. It
    drew a series of YEARS, spending its whole width on year identity that
    no sentence on either page uses, and left rank to be inferred from bar
    heights. Every page carrying it asks where ONE READING FALLS IN A
    RECORD. VD's argument, and it is right: grey bars with one in an accent
    is generic partly because it is everywhere and mostly because it fits
    badly.

    So the axis is the quantity, every observation is a stroke on it,
    stacked where values collide, and the record's own shape appears: a
    dense body, a thinning tail, a gap, then this year. Rank is countable
    rather than asserted, and the sentence underneath is DERIVED from the
    marks rather than typed beside them.

    THE CURRENT READING CARRIES NO HUE. It is ink at full weight, taller
    than the record, and labelled. Position already carries departure, so
    an accent on top of it is the one colour on these pages that is
    provably unearned. That is also what removes terracotta from every
    interior chart in a single move, which is the largest single thing
    putting us in the family the reader recognised, and it leaves
    fire #B32E10 a channel hue only without any palette change.

    NO AXIS FURNITURE. No baseline rule, no tick row, no year labels.
    Three labelled positions at most: the low end of the record, the
    baseline, and the reading. Mono ticks along a hairline axis are half of
    what makes the old form legible as a default and none of them are read.

    A SECOND VARIABLE TRAVELS AS FORM, NOT HUE: a marked observation gets a
    foot serif. Same decision the channel system made about identity, and
    it keeps the drawing readable in greyscale and for a colourblind reader
    before hue does any work.

    THE CALM CASE IS DRAWN AT IDENTICAL WEIGHT (D-043). A bar chart has to
    fake this, because the calm bar is short and short reads as absence.
    Here the mark simply sits inside the body of the record instead of
    beyond it, at the same ink, because the drawing is the RECORD and not
    the reading.
    """
    series = chart.get("series") or []
    if not series:
        return ""
    cur_x = str(chart.get("current_x"))
    obs = [p for p in series if str(p["x"]) != cur_x]
    cur = next((p for p in series if str(p["x"]) == cur_x), None)
    if cur is None or not obs:
        return ""
    dp = chart.get("decimals")
    base = chart.get("baseline") or {}
    bval = base.get("value")

    vals = sorted(float(p["y"]) for p in obs)
    lo = min(vals + [float(cur["y"])] + ([bval] if bval is not None else []))
    hi = max(vals + [float(cur["y"])])
    span = (hi - lo) or 1.0
    lo -= span * 0.06
    hi += span * 0.06

    # HEIGHT COMES FROM THE DEEPEST STACK, not from a constant. Fixed at
    # 190 the taller strokes pushed the reading's own value label off the
    # top of the viewBox: the label vanished on the one mark the chart
    # exists to show, which is the same defect as the clipped 2026 bar in
    # the version this replaces. Measured, so it cannot recur when a
    # record gets denser.
    _bins = {}
    for _p in obs:
        _k = round((float(_p["y"]) - lo) / (hi - lo) * 862 / 5)
        _bins[_k] = _bins.get(_k, 0) + 1
    _peak = max(_bins.values()) if _bins else 1
    W = 880
    H = max(190, 52 + 4 + _peak * 13 + 18 + 46)
    axY, x0, x1 = H - 52, 8, W - 10
    def X(v):
        return x0 + (float(v) - lo) / (hi - lo) * (x1 - x0)

    marked = {str(p["x"]) for p in obs if p.get("mark")}
    bins, parts = {}, []
    for p in sorted(obs, key=lambda q: float(q["y"])):
        key = round(X(p["y"]) / 5)
        bx = key * 5
        bins[key] = bins.get(key, 0) + 1
        top = axY - 4 - (bins[key] - 1) * 13
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" '
                     'stroke="var(--ink-soft)" stroke-width="2.4"/>'
                     % (bx, bx, top, top - 11))
        if str(p["x"]) in marked:
            # Foot serif, not a colour.
            parts.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" '
                         'stroke="var(--ink-soft)" stroke-width="2"/>'
                         % (bx - 3.4, bx + 3.4, top + 1.0, top + 1.0))

    peak = max(bins.values()) if bins else 1
    cx = X(cur["y"])
    top = min(axY - 4 - peak * 13 - 18, axY - 74)
    anchor = "end" if cx > W * 0.72 else ("start" if cx < W * 0.28 else "middle")
    parts.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" '
                 'stroke="var(--ink)" stroke-width="3"/>' % (cx, cx, axY - 2, top))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="%s" class="rs-cur">%s</text>'
                 % (cx, top - 20, anchor,
                    h(_fmt(float(cur["y"]), False, dp) + (chart.get("unit") or ""))))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="%s" class="rs-kick">%s</text>'
                 % (cx, top - 7, anchor, h(str(chart.get("current_kicker") or cur["x"]))))

    labels = [(vals[0], _fmt(vals[0], False, dp) + (chart.get("unit") or ""), "start")]
    if bval is not None:
        labels.append((bval, base.get("label", ""), "middle"))
    for lab in (chart.get("named") or []):
        labels.append((lab["v"], lab["label"], lab.get("anchor", "middle")))
    for v, text, anc in labels:
        if not text:
            continue
        parts.append('<text x="%.1f" y="%.1f" text-anchor="%s" class="rs-lab">%s</text>'
                     % (X(v), axY + 24, anc, h(text)))

    # THE SENTENCE IS DERIVED FROM THE MARKS, never passed in, so it cannot
    # disagree with the drawing above it.
    above = sum(1 for v in vals if v > float(cur["y"]))
    one = chart.get("noun") or "observation"
    many = chart.get("noun_plural") or (one + "s")
    if above == 0:
        said = "No %s in the record reaches it." % one
    elif above == 1:
        said = "One %s in the record of %d sits above it." % (one, len(vals))
    else:
        said = "%d of %d %s in the record sit above it." % (above, len(vals), many)
    parts.append('<text x="%d" y="%d" class="rs-said">%s</text>'
                 % (x0, H - 6, h(said)))
    if marked and chart.get("mark_label"):
        parts.append('<text x="%d" y="%d" text-anchor="end" class="rs-key">'
                     'FOOT SERIF = %s</text>'
                     % (x1, H - 6, h(chart["mark_label"].upper())))

    # SAY WHAT A STROKE IS, INSIDE THE CHART.
    #
    # Kristjan, on the first build: "it is hard for the reader to understand
    # that those other lines are previous years". He is right, and VD's
    # mockup hides the problem rather than solving it: their page carries a
    # sentence of body copy saying each stroke is one August, so the drawing
    # never has to say it. A chart that only works with a paragraph beside
    # it is not a chart, and this one gets shared as an image.
    #
    # Placed above the strokes rather than in a corner, because it has to be
    # read BEFORE the marks are, not after.
    xs = sorted(str(p["x"]) for p in obs)
    span = ""
    if len(xs) > 1 and xs[0].isdigit() and xs[-1].isdigit():
        span = ", %s to %s" % (xs[0], xs[-1])
    parts.insert(0, '<text x="%d" y="%d" class="rs-key">'
                    'EACH STROKE = ONE %s%s</text>'
                 % (x0, 14, h((chart.get("noun") or "observation").upper()),
                    h(span)))

    return ('<svg class="rs" viewBox="0 0 %d %d" width="100%%" role="img" '
            'aria-label="%s">%s</svg>'
            % (W, H, h(chart.get("label", "")), "".join(parts)))

def fr_instruments(piece):
    """Every instrument, assessed or not, at one weight. Decision 2A.

    THE NOT-ASSESSED ROW IS DRAWN, NOT OMITTED. It carries the same type
    and the same column as the measurement, and only its value differs.
    Greyed but present is the point: a row that says "not assessed" cannot
    be read as a zero, and a row that is missing entirely will be.

    D-193 is the reason there is anything to say. Flood extent failed the
    screen on 0 of 6 European regions not because Europe cannot be seen,
    but because week-to-week visibility varies enough that a ranking would
    rank the weather over the sensor. That is a limit we measured.
    """
    rows = piece.get("instruments") or []
    if not rows:
        return ""
    out = []
    for r in rows:
        na = r.get("state") == "not_assessed"
        out.append(
            '<tr class="%s"><th scope="row">%s<span>%s</span></th>'
            '<td class="fr-iv">%s</td><td class="fr-ir">%s</td></tr>'
            % ("fr-na" if na else "", h(r.get("name", "")),
               h(r.get("detail", "")), h(r.get("value", "")),
               h(r.get("rank", ""))))
        if r.get("caveat"):
            out.append('<tr class="fr-icav"><td colspan="3">%s</td></tr>'
                       % h(r["caveat"]))
    return ('  <table class="fr-inst"><caption>What was measured, and what '
            'was not</caption>%s</table>\n' % "".join(out))


def fr_corroboration(piece):
    """Whether the event happened, when we have not established it.

    Same treatment as the staleness line and for the same reason: a reader
    who takes only the headline is the one who most needs it, and this
    qualifies what the page's own URL asserts rather than what its
    measurement says.
    """
    text = piece.get("corroboration")
    if not text:
        return ""
    return '  <p class="fr-stale fr-unk">%s</p>\n' % h(text)


def fr_stale(piece):
    """A closed event says so, directly under the claim.

    ABOVE THE STANDFIRST RATHER THAN IN IT. A reader who takes only the
    headline is exactly the reader who would otherwise carry away a
    three-week-old event as today's news, and they never reach a note
    further down. This is the same reasoning as putting a qualifier in the
    claim rather than one line below it.

    Rendered as a bordered line rather than a coloured banner: the finding
    is not in doubt and nothing about it is a warning. It is out of date,
    which is a fact about the page and not about the rain.
    """
    text = piece.get("staleness")
    if not text:
        return ""
    return '  <p class="fr-stale">%s</p>\n' % h(text)


def render(piece: dict, root_prefix: str = "../../") -> str:
    """One fast-reaction piece as a standalone page.

    INDEXABLE SINCE 2026-08-21, on product's ruling. This template
    carried noindex from the day it was written and it cost nothing,
    because nothing ever rendered through it. Its first real use is a
    dated European flood finding, and a template optimised for a
    one-day turnaround whose output cannot be found in search is a
    contradiction. The tag is gone rather than overridden per call,
    so no caller has to remember.

    `path` is required for the canonical URL and only the builder
    knows it. A piece without one canonicalises to "/", which is
    wrong in a way nothing visible would show, so build_piece asserts
    it rather than defaulting.
    """
    ch = piece.get("channel", "fire")
    hue = {"fire": "var(--fire)", "elnino": "var(--nino)",
           "flood": "var(--flood)", "crop": "var(--crop)"}.get(ch, "var(--fire)")
    chart = piece.get("chart") or {}
    src = piece.get("source") or {}
    notes = piece.get("notes") or {}
    tag = piece.get("attribution", "pending")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_meta(title=f'{piece.get("region", "")} | {SITE_NAME}',
           description=piece.get("standfirst", "") or piece.get("claim", ""),
           path=piece.get("path", "/"),
           og_image=piece.get("og_image"))}
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
:root {{ --shell-max: 820px; --shell-pad: 24px; }}
body {{
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: "{T.FONT_PROSE}", Georgia, serif; font-size: 17px;
  line-height: 1.55;
}}
main {{ max-width: 820px; margin: 0 auto; padding: 28px 24px 80px; }}
{SITE_MASTHEAD_CSS}
.fr-inst {{ width:100%; border-collapse:collapse; margin:0 0 22px;
  font-size:14px; }}
.fr-inst caption {{ text-align:left; font-family:"{T.FONT_DATA}",monospace;
  font-size:10px; letter-spacing:.07em; text-transform:uppercase;
  color:var(--ink-faint); padding-bottom:7px; }}
.fr-inst tr {{ border-top:1px solid var(--rule); }}
.fr-inst th {{ text-align:left; font-weight:400; padding:9px 12px 9px 0;
  vertical-align:baseline; }}
.fr-inst th span {{ display:block; font-family:"{T.FONT_DATA}",monospace;
  font-size:10.5px; color:var(--ink-faint); margin-top:2px; }}
.fr-iv {{ font-family:"{T.FONT_DATA}",monospace; text-align:right;
  padding:9px 14px 9px 0; white-space:nowrap; }}
.fr-ir {{ font-family:"{T.FONT_DATA}",monospace; text-align:right;
  color:var(--ink-2); padding:9px 0; white-space:nowrap; }}
.fr-inst tr.fr-na th, .fr-inst tr.fr-na .fr-iv {{ color:var(--ink-faint); }}
.fr-icav td {{ padding:0 0 10px; font-size:12.5px; line-height:1.5;
  color:var(--ink-faint); border:0; }}
.fr-icav {{ border-top:0 !important; }}
.rs {{ display:block; width:100%; height:auto; }}
.rs-cur {{ font-family:"{T.FONT_DATA}",monospace; font-size:23px;
  font-weight:500; fill:var(--ink); }}
.rs-kick {{ font-family:"{T.FONT_DATA}",monospace; font-size:9.5px;
  letter-spacing:1.9px; fill:var(--ink-2); }}
.rs-lab {{ font-family:"{T.FONT_DATA}",monospace; font-size:10.5px;
  letter-spacing:0.6px; fill:var(--ink-2); }}
/* The derived sentence is SERIF, deliberately. It is prose the reader
   reads, not a figure, and mono-everything is on the rule-out list. */
.rs-said {{ font-family:var(--serif); font-size:17px; fill:var(--ink); }}
.rs-key {{ font-family:"{T.FONT_DATA}",monospace; font-size:10px;
  letter-spacing:1.6px; fill:var(--ink-2); }}
.fr-stale {{ border-left:3px solid var(--ink-faint); padding:8px 0 8px 13px;
  margin:0 0 16px; font-size:14px; line-height:1.5; color:var(--ink-2);
  max-width:62ch; }}
.fr-unk {{ border-left-color:var(--ink); }}
.fr-eyebrow {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint);
  margin: 26px 0 10px;
}}
h1 {{
  font-size: 40px; font-weight: 500; line-height: 1.12;
  letter-spacing: -0.018em; margin: 0 0 16px; text-wrap: balance;
}}
.fr-stand {{ color: var(--ink-soft); max-width: 60ch; margin: 0 0 34px; }}
.fr-cell {{ border-top: 3px solid var(--ink); padding-top: 14px; }}
.fr-hero {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 46px; font-weight: 600; letter-spacing: -0.02em;
  color: {hue}; font-variant-numeric: tabular-nums; line-height: 1;
}}
.fr-cap {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 12px; color: var(--ink-soft); margin: 10px 0 0;
  max-width: 58ch; line-height: 1.5;
}}
.fr-lab {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint);
  margin: 30px 0 6px; padding-bottom: 8px;
  border-bottom: 1px solid var(--rule);
}}
.fr-chart {{ width: 100%; height: auto; display: block; }}
/* Every in-plot label carries the paper halo. Stated once, here, so no
   chart has to remember it (D-023 extended by D-026). */
.fr-chart text {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  paint-order: stroke; stroke: var(--paper); stroke-width: 2.5;
  stroke-linejoin: round;
}}
.fr-xl {{ font-size: 11px; fill: var(--ink-faint); }}
.fr-val {{ font-size: 15px; font-weight: 600; }}
.fr-base {{ font-size: 11px; fill: var(--ink-soft); }}
.fr-ann {{ font-size: 11.5px; fill: var(--ink-soft); }}
.fr-tag {{
  display: inline-block;
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 10.5px; letter-spacing: 0.04em; padding: 3px 8px;
  background: var(--tag-{'loaded' if tag == 'enso' else
                         'notlink' if tag == 'non_enso' else 'pending'}-bg);
  color: var(--tag-{'loaded' if tag == 'enso' else
                    'notlink' if tag == 'non_enso' else 'pending'}-fg);
  margin-top: 22px;
}}
.fr-notes {{ margin-top: 40px; }}
.fr-notes h2 {{
  font-size: 19px; font-weight: 500; margin: 26px 0 8px;
  padding-bottom: 8px; border-bottom: 2.4px solid var(--rule-45);
}}
.fr-notes p {{ max-width: 62ch; color: var(--ink-soft); }}
.fr-src {{
  margin-top: 34px; padding-top: 14px;
  border-top: 1px solid var(--ink);
  font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 12px; color: var(--ink-faint); line-height: 1.6;
}}
.fr-src b {{ color: var(--ink-soft); font-weight: 500; }}
@media (max-width: 560px) {{ h1 {{ font-size: 30px; }}
  .fr-hero {{ font-size: 36px; }} }}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active=ch)}
<main>
  <p class="fr-eyebrow">{h(piece.get("region", ""))} &middot;
     {h(piece.get("window", ""))}{" &middot; " + h(piece["measured"]) if piece.get("measured") else ""}</p>
  <h1>{h(piece.get("claim", ""))}</h1>
{fr_stale(piece)}{fr_corroboration(piece)}  <p class="fr-stand">{h(piece.get("standfirst", ""))}</p>

{fr_instruments(piece)}
  <div class="fr-cell">
    <div class="fr-hero">{h((piece.get("value") or {}).get("display", ""))}</div>
    <p class="fr-cap">{h((piece.get("value") or {}).get("caption", ""))}</p>
  </div>

  <p class="fr-lab">{h(chart.get("label", ""))}</p>
  {_record_strip(chart, hue)}

  <span class="fr-tag">{h(TAG_TEXT.get(tag, TAG_TEXT["pending"]))}</span>

  <div class="fr-notes">
    <h2>What this is</h2>
    <p>{h(notes.get("what_this_is", ""))}</p>
    <h2>What this is not</h2>
    <p>{h(notes.get("what_this_is_not", ""))}</p>
  </div>

  <div class="fr-src">
    <p><b>Source.</b> {h(src.get("name", ""))}, {h(src.get("detail", ""))}.
    As of {h(src.get("as_of", ""))}.</p>
  </div>
</main>
</body>
</html>
"""
