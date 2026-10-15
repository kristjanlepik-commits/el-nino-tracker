"""Figures for "How a flood is made", the floods reader explainer.

Storyboard by FLO, order and visual direction set by Kristjan, 15 October
2026. Every figure is drawn from measured data passed in by the caller
(floods/data/explainer_2026-10.json, emitted by FLO); this module never
reads a data file and never converts units, the same handoff rule as
fast_reaction.py. A figure that needs an illustrative number takes it as
an argument named `illustrative_*` and labels it on the drawing.

The figures are built before the page that holds them on purpose: whether
the words are a Note (Kristjan's, D-093) or an editor piece is decided
separately, and the figures are the same either way.

Motion: SMIL inside the SVG, started when the figure scrolls into view.
The final state is what the markup draws, so a reader with reduced motion,
no JavaScript, or a screenshot tool sees the finished figure, never an
empty one.
"""
from __future__ import annotations

import math

COS30, SIN30 = math.cos(math.radians(30)), 0.5


def _iso(cx, cy, s):
    """Isometric projection, metres to pixels. x right-down, y left-down."""
    def p(x, y, z=0.0):
        return (cx + (x - y) * s * COS30, cy + (x + y) * s * SIN30 - z * s)
    return p


def _pts(*xy):
    return " ".join("%.1f,%.1f" % q for q in xy)


def fig_bathtub(mm: float, day_words: str, station: str) -> str:
    """One square metre of ground under one day's rain, to scale.

    1 mm of rain is 1 litre on every square metre, so the depth IS the
    volume and the drawing needs no conversion: a 1 m by 1 m floor with
    the day's rain standing on it, at the same scale in all three
    directions, inside the outline of a whole cubic metre so the water has
    something to be measured against. A full cube would be 1,000 litres.
    """
    d = mm / 1000.0                       # metres of water
    S, W, H = 175, 640, 520
    p = _iso(W * 0.36, 200, S)
    rim = 1.0

    # Floor, walls, and the two faces of water that face the reader.
    floor = _pts(p(0, 0), p(1, 0), p(1, 1), p(0, 1))
    back_l = _pts(p(0, 0), p(0, 1), p(0, 1, rim), p(0, 0, rim))
    back_r = _pts(p(0, 0), p(1, 0), p(1, 0, rim), p(0, 0, rim))

    def water(z):
        top = _pts(p(0, 0, z), p(1, 0, z), p(1, 1, z), p(0, 1, z))
        left = _pts(p(0, 1), p(1, 1), p(1, 1, z), p(0, 1, z))
        right = _pts(p(1, 0), p(1, 1), p(1, 1, z), p(1, 0, z))
        return top, left, right

    t0, l0, r0 = water(0.0005)
    t1, l1, r1 = water(d)

    def anim(full, empty):
        # The markup holds the FULL state; the animation runs from empty.
        return ('<polygon points="%s">'
                '<animate attributeName="points" from="%s" to="%s" dur="2.6s" '
                'begin="indefinite" fill="freeze" calcMode="spline" '
                'keySplines=".3 0 .2 1" keyTimes="0;1"/></polygon>'
                % (full, empty, full))

    front_l = _pts(p(0, 1), p(1, 1), p(1, 1, rim), p(0, 1, rim))
    front_r = _pts(p(1, 0), p(1, 1), p(1, 1, rim), p(1, 0, rim))

    # Depth bracket on the right-hand front edge, at true scale.
    bx0, by0 = p(1, 0)
    bx1, by1 = p(1, 0, d)
    rx0, ry0 = p(1, 0, rim)
    lab_x = bx0 + 18

    # Metre edges, labelled once each.
    ex = p(0.5, 1)
    ey = p(1, 0.5)

    return f"""<figure class="fx fx-bath">
<svg viewBox="0 0 {W} {H}" width="100%" role="img"
  aria-label="{mm:.1f} millimetres of rain standing on one square metre, drawn to scale: {mm:.1f} litres">
<g class="fx-tray">
  <polygon points="{floor}" class="fx-floor"/>
  <polygon points="{back_l}" class="fx-wall"/>
  <polygon points="{back_r}" class="fx-wall"/>
</g>
<g class="fx-water">
  {anim(t1, t0)}
  {anim(l1, l0).replace('<polygon', '<polygon class="fx-wl"', 1)}
  {anim(r1, r0).replace('<polygon', '<polygon class="fx-wr"', 1)}
</g>
<g class="fx-glass">
  <polygon points="{front_l}" class="fx-pane"/>
  <polygon points="{front_r}" class="fx-pane"/>
</g>
<line x1="{lab_x - 6:.1f}" y1="{by0:.1f}" x2="{lab_x - 6:.1f}" y2="{by1:.1f}" class="fx-brk"/>
<line x1="{lab_x - 10:.1f}" y1="{by1:.1f}" x2="{lab_x - 2:.1f}" y2="{by1:.1f}" class="fx-brk"/>
<line x1="{lab_x - 10:.1f}" y1="{by0:.1f}" x2="{lab_x - 2:.1f}" y2="{by0:.1f}" class="fx-brk"/>
<text x="{lab_x + 4:.1f}" y="{(by0 + by1) / 2 + 8:.1f}" class="fx-big">{mm:.1f} mm</text>
<text x="{lab_x + 4:.1f}" y="{ry0 + 4:.1f}" class="fx-key">1 M</text>
<text x="{ex[0] - 14:.1f}" y="{ex[1] + 26:.1f}" text-anchor="end" class="fx-key">1 M</text>
<text x="{ey[0] + 14:.1f}" y="{ey[1] + 26:.1f}" class="fx-key">1 M</text>
<text x="{W - 20}" y="{H - 60}" text-anchor="end" class="fx-say">{mm:.0f} litres on one square metre</text>
<text x="{W - 20}" y="{H - 36}" text-anchor="end" class="fx-key">{station.upper()} &#183; {day_words.upper()} &#183; DRAWN TO SCALE</text>
</svg>
</figure>"""


FIG_CSS = """
.fx { margin: 28px 0 34px; }
.fx svg { display: block; width: 100%; height: auto; }
.fx-floor { fill: var(--paper-sunk); stroke: var(--ink-faint); stroke-width: 1; }
.fx-wall { fill: none; stroke: var(--rule); stroke-width: 1; }
.fx-pane { fill: none; stroke: var(--ink-faint); stroke-width: 1;
  stroke-dasharray: 3 3; }
.fx-water polygon { fill: var(--flood); fill-opacity: .28;
  stroke: var(--flood); stroke-width: 1; }
.fx-water .fx-wl { fill-opacity: .7; }
.fx-water .fx-wr { fill-opacity: .95; }
.fx-brk { stroke: var(--ink); stroke-width: 1.2; }
.fx-big { font-family: var(--mono); font-size: 26px; font-weight: 500;
  fill: var(--ink); }
.fx-key { font-family: var(--mono); font-size: 10px; letter-spacing: 1.6px;
  fill: var(--ink-soft); }
.fx-say { font-family: var(--serif); font-size: 19px; fill: var(--ink); }
"""

# Starts each figure's animation once, when it is half on screen. Without
# JavaScript, or with reduced motion, nothing starts and the markup's own
# final state is what shows.
FIG_JS = """<script>
(function(){
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){
      if (!e.isIntersecting) return;
      e.target.querySelectorAll('animate').forEach(function(a){
        try { a.beginElement(); } catch (_) {}
      });
      io.unobserve(e.target);
    });
  }, {threshold: .5});
  document.querySelectorAll('figure.fx').forEach(function(f){ io.observe(f); });
})();
</script>"""
