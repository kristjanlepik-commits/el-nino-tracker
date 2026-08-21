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


def _fmt(v: float, diverging: bool) -> str:
    if diverging:
        return f"{v:+.1f}"
    return f"{v:,.0f}"


def _series_bars(chart: dict, hue: str) -> str:
    """The named fallback chart: one series, its baseline drawn.

    The baseline is DRAWN, not stated, so a reader can verify the
    headline multiple by eye rather than taking it on trust. That is the
    visual chat's rule and it is the difference between a chart and an
    illustration of a number.

    Diverging series hang from a zero line that sits inside the plot;
    magnitude series sit on a zero line at the floor. Same code path,
    because the only real difference is where zero goes.
    """
    series = chart["series"]
    if not series:
        return ""
    diverging = bool(chart.get("diverging"))
    base = chart.get("baseline") or {}
    baseline_v = base.get("value")

    W, H = 760, 260
    PAD_L, PAD_R, PAD_T, PAD_B = 8, 8, 26, 30
    ys = [p["y"] for p in series]
    lo = min(ys + ([baseline_v] if baseline_v is not None else []) + [0.0])
    hi = max(ys + ([baseline_v] if baseline_v is not None else []) + [0.0])
    if hi == lo:
        hi = lo + 1.0
    pad = (hi - lo) * 0.12
    lo, hi = lo - (pad if diverging else 0.0), hi + pad

    def Y(v):
        return H - PAD_B - (v - lo) / (hi - lo) * (H - PAD_T - PAD_B)

    n = len(series)
    slot = (W - PAD_L - PAD_R) / n
    bw = min(slot * 0.62, 34.0)
    zero_y = Y(0.0)

    parts = []
    for i, p in enumerate(series):
        cx = PAD_L + slot * (i + 0.5)
        y_val, y_zero = Y(p["y"]), zero_y
        top, height = min(y_val, y_zero), abs(y_val - y_zero)
        current = str(p["x"]) == str(chart.get("current_x"))
        fill = hue if current else "var(--rule-45)"
        parts.append(
            f'<rect x="{cx - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" '
            f'height="{max(height, 1.2):.1f}" fill="{fill}"/>')
        if current or i == 0 or i == n - 1:
            parts.append(
                f'<text class="fr-xl" x="{cx:.1f}" y="{H - PAD_B + 15:.1f}" '
                f'text-anchor="middle">{h(str(p["x"]))}</text>')
        if current:
            above = y_val <= y_zero
            ty = (top - 7) if above else (top + height + 15)
            parts.append(
                f'<text class="fr-val" x="{cx:.1f}" y="{ty:.1f}" '
                f'text-anchor="middle" fill="{hue}">'
                f'{h(_fmt(p["y"], diverging))}</text>')

    if diverging:
        parts.insert(0, f'<line x1="{PAD_L}" y1="{zero_y:.1f}" '
                        f'x2="{W - PAD_R}" y2="{zero_y:.1f}" '
                        f'stroke="var(--ink)" stroke-width="1"/>')
    if baseline_v is not None:
        by = Y(baseline_v)
        parts.append(
            f'<line x1="{PAD_L}" y1="{by:.1f}" x2="{W - PAD_R}" '
            f'y2="{by:.1f}" stroke="var(--ink-soft)" stroke-width="1" '
            f'stroke-dasharray="4 4"/>')
        # Halo on every in-plot label (D-023, extended by D-026). Bar
        # heights move every week, so any annotation eventually lands on
        # data; haloing only the ones that overlap today is a bug with a
        # delay on it.
        #
        # The halo is the floor, not the whole answer: the rule is move
        # the label as well, where empty plot space exists. So the
        # baseline label goes to whichever end has more clearance above
        # the line, measured rather than assumed. On the ONI series the
        # left end is a tall 1997 bar and the right end is not, and a
        # haloed label sitting on a bar is still a label sitting on a bar.
        label = base.get("label", "")
        # How many bars the label actually covers, rounded up and never
        # fewer than two. Rounding down checked only the first bar and
        # missed the one the label was landing on, which is how a
        # collision survives a collision check.
        span = max(2, math.ceil(len(label) * 6.6 / slot))
        left_clear = min((Y(p["y"]) for p in series[:span]), default=by)
        right_clear = min((Y(p["y"]) for p in series[-span:]), default=by)
        if right_clear > left_clear:
            lx, anchor = W - PAD_R - 2, "end"
        else:
            lx, anchor = PAD_L + 2, "start"
        parts.append(
            f'<text class="fr-base" x="{lx:.1f}" y="{by - 6:.1f}" '
            f'text-anchor="{anchor}">{h(label)}</text>')

    for ann in chart.get("annotations") or []:
        idx = next((i for i, p in enumerate(series)
                    if str(p["x"]) == str(ann["x"])), None)
        if idx is None:
            continue
        cx = PAD_L + slot * (idx + 0.5)
        anchor = "end" if idx > n / 2 else "start"
        dx = -bw / 2 - 8 if anchor == "end" else bw / 2 + 8
        parts.append(
            f'<text class="fr-ann" x="{cx + dx:.1f}" '
            f'y="{Y(series[idx]["y"]) + 4:.1f}" text-anchor="{anchor}">'
            f'{h(ann["text"])}</text>')

    return (f'<svg class="fr-chart" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{h(chart.get("label", "chart"))}">'
            + "".join(parts) + '</svg>')


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
.fr-stale {{ border-left:3px solid var(--ink-faint); padding:8px 0 8px 13px;
  margin:0 0 16px; font-size:14px; line-height:1.5; color:var(--ink-2);
  max-width:62ch; }}
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
{fr_stale(piece)}  <p class="fr-stand">{h(piece.get("standfirst", ""))}</p>

  <div class="fr-cell">
    <div class="fr-hero">{h((piece.get("value") or {}).get("display", ""))}</div>
    <p class="fr-cap">{h((piece.get("value") or {}).get("caption", ""))}</p>
  </div>

  <p class="fr-lab">{h(chart.get("label", ""))}</p>
  {_series_bars(chart, hue)}

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
