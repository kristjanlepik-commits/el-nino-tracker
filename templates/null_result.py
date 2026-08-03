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

## Evidence basis, at a glance

Product's veto: separable at a glance, not on careful reading. So the
distinction is SHAPE, not colour, and the vocabulary is the three D-033
tiers and ONLY those three: Measured, Compiled, Combined. An earlier
version of this file said "measured / inferred", which introduced a
fourth word for the evidence basis; a fourth word erodes the one
labelling system the whole site runs on. The mechanism was right and the
labels were not.

Colour is already carrying channel identity and would need a legend
lookup. Filled against open against ringed is pre-attentive, survives
greyscale and colour blindness, and reuses what the world map already
teaches for anomaly against context.

## When something IS outside the band

A component that can only say "all inside" breaks the first time
something sits outside, and on the volatility null four of eleven pairs
did become more variable. So an outside point can carry a callout
naming itself. That matters more than it looks: the two largest movers
there are land reform and irrigation rather than weather, so the
outliers are where the piece stops being about climate, and a shape
with nowhere to put them would have buried its own best content.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import h                                       # noqa: E402


def _mark(x: float, y: float, basis: str, r: float = 5.2) -> str:
    """One observation, its evidence basis carried by SHAPE.

    The three D-033 tiers and only these three. Shape rather than colour
    because product's constraint is separability at a glance: a filled
    against open against ringed mark is pre-attentive, survives
    greyscale and colour blindness, and needs no legend lookup. Colour
    is already spent on channel identity.

    An earlier version used "measured / inferred", which was a fourth
    word for the evidence basis. A fourth word erodes the one labelling
    system the whole site runs on, so it is gone.
    """
    if basis == "compiled":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                f'fill="var(--paper)" stroke="var(--ink)" stroke-width="1.6"/>')
    if basis == "combined":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="var(--ink)"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r - 2.6:.1f}" '
                f'fill="var(--paper)"/>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="var(--ink)"/>'


def _halo_text(x: float, y: float, text: str) -> str:
    return (f'<text class="nb-call" x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="middle">{h(text)}</text>')


def null_band(points, band, centre, unit_label, note="") -> str:
    """A distribution against its own historical envelope.

    points  [{label, value, basis, callout}] where basis is one of the
            three D-033 tiers and callout names a point worth naming
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

    # Shape carries the evidence basis; a callout names a point that is
    # doing something the band does not explain.
    for i, p in enumerate(points):
        x = X(p["value"])
        y = AXIS_Y - 16 + (i % 3) * 16          # jitter, so dots do not hide
        out.append(_mark(x, y, p.get("basis", "measured")))
        if p.get("callout"):
            out.append(_halo_text(x, y - 12, p["callout"]))

    # Only the three D-033 tiers ever appear here, and only the ones
    # actually present in the data: a legend entry for a tier nothing on
    # the chart uses teaches a distinction the reader will not find.
    present = [b for b in ("measured", "compiled", "combined")
               if any(p.get("basis", "measured") == b for p in points)]
    legend, lx = "", PAD_L + 5
    for b in present:
        legend += _mark(lx, 18, b)
        legend += f'<text class="nb-l" x="{lx + 11}" y="22">{b}</text>'
        lx += 26 + len(b) * 6.4

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
.nb-call {{ font-size: 11px; fill: var(--ink); font-weight: 600; }}
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
