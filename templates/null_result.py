"""Rendering "nothing happened" as a confident result.

Product's test of D-043, and the right one: a system that can only look
alarming is a defect, and until now that claim has been asserted rather
than tested. The crops volatility null is eleven values scattered around
1.0, and the finding IS the scatter around 1.0.

## Why the obvious render fails

Every instinct in a system built to show extremity works against this.
An anomaly ramp with nothing anomalous on it reads as a rendering
failure: the reader sees an empty chart and concludes the page is
broken, not that the world is calm. Colour carries nothing because
nothing crossed a threshold. Bars are all the same height. The page
looks like it failed to load.

## The fix: draw the envelope, not just the observations

An empty chart looks broken because there is nothing in it. So the
subject changes. Instead of plotting how anomalous each value is against
a scale designed for extremity, plot the values inside the range they
have historically occupied, and DRAW that range.

The band is what fills the frame. The dots sitting inside it are then
obviously a result rather than an absence, because the reader can see
the thing they are being compared against. "Within range" stops being
the absence of a finding and becomes a visible relationship between two
drawn objects.

The headline is a count, not a magnitude. "Eleven of eleven, within
range" is a strong number, and a strong number is what a reader who
gives this ninety seconds standing up can take away. A null with no
number in it reads as nothing to say.

## Measured against inferred, at a glance

Product's veto: separable at a glance, not on careful reading. So the
distinction is SHAPE, not colour. Filled disc for measured, open ring
for inferred. Colour is already carrying channel identity and would have
to be read against a legend; a filled versus open mark is pre-attentive,
survives greyscale, and survives colour blindness. It is the same device
already used on the world map for anomaly against context, which means
a reader who has seen one page has already learned it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import h                                       # noqa: E402


def null_band(points, band, centre, unit_label, note="") -> str:
    """A distribution against its own historical envelope.

    points  [{label, value, basis}] where basis is measured | inferred
    band    {low, high, label}  the range these have historically held
    centre  the reference value, usually 1.0
    """
    W, H = 680, 168
    PAD_L, PAD_R, PAD_T = 14, 14, 46
    AXIS_Y = 104

    vals = [p["value"] for p in points]
    lo = min(vals + [band["low"]])
    hi = max(vals + [band["high"]])
    span = max(hi - lo, 1e-6)
    lo, hi = lo - span * 0.30, hi + span * 0.30

    def X(v):
        return PAD_L + (v - lo) / (hi - lo) * (W - PAD_L - PAD_R)

    out = []
    # The envelope first, and it is the largest object in the frame.
    # This is what stops an unremarkable result reading as an empty
    # chart: the reader sees the thing being compared against.
    bx1, bx2 = X(band["low"]), X(band["high"])
    out.append(f'<rect x="{bx1:.1f}" y="{AXIS_Y - 34:.1f}" '
               f'width="{bx2 - bx1:.1f}" height="68" '
               f'fill="var(--paper-sunk)"/>')
    out.append(f'<line x1="{bx1:.1f}" y1="{AXIS_Y - 34:.1f}" '
               f'x2="{bx1:.1f}" y2="{AXIS_Y + 34:.1f}" '
               f'stroke="var(--rule)" stroke-width="1"/>')
    out.append(f'<line x1="{bx2:.1f}" y1="{AXIS_Y - 34:.1f}" '
               f'x2="{bx2:.1f}" y2="{AXIS_Y + 34:.1f}" '
               f'stroke="var(--rule)" stroke-width="1"/>')
    out.append(f'<text class="nb-band" x="{(bx1 + bx2) / 2:.1f}" '
               f'y="{AXIS_Y - 42:.1f}" text-anchor="middle">'
               f'{h(band.get("label", ""))}</text>')

    # The reference line, drawn at full ink because it is the thing the
    # claim is about.
    cx = X(centre)
    out.append(f'<line x1="{cx:.1f}" y1="{AXIS_Y - 40:.1f}" x2="{cx:.1f}" '
               f'y2="{AXIS_Y + 40:.1f}" stroke="var(--ink)" '
               f'stroke-width="1.4"/>')
    out.append(f'<text class="nb-c" x="{cx:.1f}" y="{AXIS_Y + 56:.1f}" '
               f'text-anchor="middle">{h(unit_label)}</text>')

    # Filled = measured, open = inferred. Shape rather than colour, so
    # the distinction survives a glance, greyscale and colour blindness.
    for i, p in enumerate(points):
        x = X(p["value"])
        y = AXIS_Y - 16 + (i % 3) * 16          # jitter, so dots do not hide
        if p.get("basis") == "inferred":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" '
                       f'fill="var(--paper)" stroke="var(--ink)" '
                       f'stroke-width="1.6"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" '
                       f'fill="var(--ink)"/>')

    legend = (f'<circle cx="{PAD_L + 5}" cy="18" r="5.2" fill="var(--ink)"/>'
              f'<text class="nb-l" x="{PAD_L + 16}" y="22">measured</text>'
              f'<circle cx="{PAD_L + 104}" cy="18" r="5.2" fill="var(--paper)" '
              f'stroke="var(--ink)" stroke-width="1.6"/>'
              f'<text class="nb-l" x="{PAD_L + 115}" y="22">inferred</text>')

    note_html = (f'<p class="nb-note">{h(note)}</p>' if note else "")
    return (f'<svg class="nb" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{len(points)} values against the range they have '
            f'historically occupied">{legend}{"".join(out)}</svg>{note_html}')


NULL_CSS = f"""
.nb {{ width: 100%; height: auto; display: block; }}
.nb text {{ font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  paint-order: stroke; stroke: var(--paper); stroke-width: 2.5;
  stroke-linejoin: round; }}
.nb-band {{ font-size: 11px; fill: var(--ink-soft); }}
.nb-c {{ font-size: 11px; fill: var(--ink); }}
.nb-l {{ font-size: 11px; fill: var(--ink-soft); }}
.nb-note {{ font-size: 13px; color: var(--ink-soft); margin: 10px 0 0;
  max-width: 62ch; }}
/* The headline of a null is a COUNT, not a magnitude. A null with no
   number in it reads as nothing to say, and the reader gives this
   ninety seconds standing up. */
.nb-count {{ font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 38px; font-weight: 600; letter-spacing: -0.02em;
  color: var(--ink); line-height: 1; font-variant-numeric: tabular-nums; }}
.nb-claim {{ font-size: 19px; line-height: 1.35; margin: 12px 0 0;
  max-width: 30ch; }}
@media (max-width: 560px) {{ .nb-count {{ font-size: 32px; }} }}
"""
