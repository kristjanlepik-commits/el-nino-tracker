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


def _ground_panel(x0, wet: bool, label: str, sub: str) -> str:
    """One soil column under the same rain. Every timing is illustrative.

    The two panels share one clock (CYCLE seconds, looping) and one rain.
    Only the ground differs: the dry column soaks the rain in and ponds
    late; the wet one is near full before the rain starts, so water stands
    on the surface early and the excess runs off to the stream.
    """
    W, SURF, BOT = 300, 120, 300
    C = CYCLE
    parts = []
    # Rain: the same drops, same timing, in both panels.
    for i, (dx, off) in enumerate(_DROPS):
        x = x0 + 12 + dx * (W - 70)
        parts.append(
            '<line x1="%.1f" x2="%.1f" y1="-14" y2="0" class="fx-drop">'
            '<animateTransform attributeName="transform" type="translate" '
            'from="0 0" to="0 %d" dur="0.9s" begin="indefinite" '
            'repeatCount="indefinite" data-off="%.2f"/></line>'
            % (x, x, SURF + 14, off))
    # Soil, then the water held in it, which grows downward from the
    # surface. Wet ground starts most of the way full.
    parts.append('<rect x="%d" y="%d" width="%d" height="%d" class="fx-soil"/>'
                 % (x0, SURF, W - 40, BOT - SURF))
    full = BOT - SURF - 20
    h0, h1 = (0.62 * full, 0.84 * full) if wet else (0.0, 0.70 * full)
    parts.append(
        '<rect x="%d" y="%d" width="%d" height="%.1f" class="fx-held">'
        '<animate attributeName="height" values="%.1f;%.1f;%.1f" '
        'keyTimes="0;0.85;1" dur="%ds" begin="indefinite" '
        'repeatCount="indefinite"/></rect>'
        % (x0, SURF, W - 40, h1, h0, h1, h1, C))
    # Water standing on the surface: from the start on wet ground, from
    # well into the storm on dry.
    t = 0.12 if wet else 0.55
    ph = 7 if wet else 3
    parts.append(
        '<rect x="%d" y="%d" width="%d" height="%d" class="fx-pond">'
        '<animate attributeName="opacity" values="0;0;1;1" '
        'keyTimes="0;%.2f;%.2f;1" dur="%ds" begin="indefinite" '
        'repeatCount="indefinite"/></rect>'
        % (x0, SURF - ph, W - 40, ph, t, t + 0.08, C))
    # Runoff: over the lip into the stream on the right, dashes moving.
    sx = x0 + W - 40
    path = "M%d %d L%d %d Q%d %d %d %d L%d %d" % (
        x0 + 30, SURF - ph / 2, sx - 6, SURF - ph / 2, sx + 10, SURF - ph / 2,
        sx + 14, SURF + 16, sx + 14, BOT - 30)
    parts.append(
        '<path d="%s" class="fx-run" style="stroke-width:%d">'
        '<animate attributeName="opacity" values="0;0;1;1" '
        'keyTimes="0;%.2f;%.2f;1" dur="%ds" begin="indefinite" '
        'repeatCount="indefinite"/>'
        '<animate attributeName="stroke-dashoffset" from="0" to="-28" '
        'dur="0.7s" begin="indefinite" repeatCount="indefinite"/></path>'
        % (path, 5 if wet else 2, t + 0.04, t + 0.14, C))
    parts.append('<text x="%d" y="%d" class="fx-key">%s</text>'
                 % (x0, BOT + 24, label.upper()))
    parts.append('<text x="%d" y="%d" class="fx-say fx-say-s">%s</text>'
                 % (x0, BOT + 48, sub))
    return "".join(parts)


CYCLE = 9
# Fixed, not random: the figure must render identically on every build.
_DROPS = [(0.03, 0.0), (0.17, 0.35), (0.29, 0.7), (0.41, 0.15), (0.52, 0.55),
          (0.63, 0.25), (0.74, 0.8), (0.86, 0.45), (0.97, 0.1), (0.10, 0.6),
          (0.36, 0.9), (0.58, 0.05), (0.80, 0.65)]


def fig_ground(measured_line: str, measured_source: str) -> str:
    """The ground cannot drink that fast. Section 7, the motion piece.

    Two columns of soil under identical rain. The only difference is how
    much water the ground already holds, which is the measured fact the
    caller passes in (FLO's topsoil ranks). The drawing itself is
    illustrative and says so on the figure: no depth, rate or share in it
    is a measurement.
    """
    W, H = 640, 400
    return f"""<figure class="fx fx-ground">
<svg viewBox="0 0 {W} {H}" width="100%" role="img"
  aria-label="Two columns of soil under the same rain. Dry ground soaks it in; ground that is already wet fills quickly and the rest runs off.">
{_ground_panel(10, False, "Dry ground", "soaks the rain in")}
{_ground_panel(330, True, "Already wet", "fills, and the rest runs off")}
<text x="{W - 10}" y="{H - 8}" text-anchor="end" class="fx-key">ILLUSTRATIVE &#183; NOT TO SCALE</text>
</svg>
<div class="fx-live" style="display:none">
  <div class="fx-pair">
    <div><canvas></canvas><p class="fx-key-h">DRY GROUND</p><p class="fx-sub">soaks the rain in</p></div>
    <div><canvas></canvas><p class="fx-key-h">ALREADY WET</p><p class="fx-sub">fills, and the rest runs off</p></div>
  </div>
  <p class="fx-key-h fx-foot"><span class="fx-clock">HOUR 0 OF 24</span><span>SAME RAIN ON BOTH &#183; ILLUSTRATIVE &#183; NOT TO SCALE</span></p>
</div>
<figcaption class="fx-cap">{measured_line} <span>{measured_source}</span></figcaption>
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
.fx-say-s { font-size: 16px; }
.fx-drop { stroke: var(--flood); stroke-width: 1.4; stroke-linecap: round; }
.fx-soil { fill: var(--land); }
.fx-held { fill: var(--flood); fill-opacity: .35; }
.fx-pond { fill: var(--flood); }
.fx-run { fill: none; stroke: var(--flood); stroke-linecap: round;
  stroke-dasharray: 10 4; }
.fx-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.fx-pair canvas { display: block; width: 100%; aspect-ratio: 1 / 1; }
.fx-key-h { font-family: var(--mono); font-size: 10px; letter-spacing: 1.6px;
  color: var(--ink-soft); margin: 8px 0 0; }
.fx-sub { font-size: 16px; margin: 2px 0 0; }
.fx-foot { display: flex; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; margin-top: 14px; }
.fx-cap { font-size: 15px; color: var(--ink-soft); margin-top: 6px;
  max-width: 60ch; }
.fx-cap span { display: block; font-family: var(--mono); font-size: 10.5px;
  color: var(--ink-faint); margin-top: 4px; }
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
      e.target.querySelectorAll('animate, animateTransform').forEach(function(a){
        var off = parseFloat(a.getAttribute('data-off') || '0');
        try { off ? a.beginElementAt(off) : a.beginElement(); } catch (_) {}
      });
      io.unobserve(e.target);
    });
  }, {threshold: .5});
  document.querySelectorAll('figure.fx').forEach(function(f){ io.observe(f); });
})();
</script>"""

# The ground scene, live. Two canvases, one rain: every drop event is drawn
# from one seeded sequence and fed to both panels, so the ONLY difference a
# reader can see is the ground's starting wetness. A drop that lands where
# the soil still has room soaks in; one that does not runs downhill, trying
# again at every column it crosses (dry ground downstream drinks runoff),
# and what reaches the channel raises the river. Illustrative physics,
# labelled on the figure: no rate, depth or share here is a measurement.
#
# Replaces the static drawing only when motion is allowed and canvas works;
# otherwise the SVG above it is the figure.
GROUND_JS = """<script>
(function(){
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var figs = document.querySelectorAll('figure.fx-ground');
  if (!figs.length || !document.createElement('canvas').getContext) return;
  function css(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function rng(seed){ return function(){ seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

  var T = 16, HOLD = 3, N = 64;
  function storm(){
    var r = rng(20261003), ev = [], t = 0;
    while (t < T) {
      var x = t / T, rate = 18 + 150 * Math.exp(-Math.pow((x - 0.42) / 0.14, 2));
      t += -Math.log(1 - r()) / rate;
      ev.push([t, r()]);
    }
    return ev;
  }
  var EV = storm();

  function Panel(cv, wet){
    this.cv = cv; this.wet = wet; this.reset();
  }
  Panel.prototype.reset = function(){
    this.S = []; this.allow = [];
    var r = rng(this.wet ? 7 : 3);
    for (var i = 0; i < N; i++) {
      this.S.push(this.wet ? 0.66 + 0.1 * r() : 0.08 + 0.08 * r());
      this.allow.push(0);
    }
    this.drops = []; this.surf = []; this.sink = []; this.river = 0; this.k = 0;
  };
  Panel.prototype.geom = function(){
    var w = this.cv.clientWidth, h = this.cv.clientHeight;
    var land = w * 0.87;
    return {w: w, h: h, land: land, cw: land / N,
            sy: function(x){ return h * 0.40 + (x / land) * h * 0.12; },
            floor: h * 0.97, chanBot: h * 0.90};
  };
  Panel.prototype.step = function(t, dt){
    var g = this.geom(), i;
    while (this.k < EV.length && EV[this.k][0] <= t) {
      var x = EV[this.k][1] * g.w * 0.98;
      this.drops.push({x: x, y: -10 - Math.random() * 20, v: g.h * 1.6});
      this.k++;
    }
    for (i = 0; i < N; i++) {
      var room = 1 - this.S[i];
      this.allow[i] = Math.min(1.5, this.allow[i] + dt * 9 * Math.pow(room, 1.6));
    }
    var keep = [];
    for (i = 0; i < this.drops.length; i++) {
      var d = this.drops[i]; d.y += d.v * dt;
      if (d.x >= g.land) {
        if (d.y >= g.chanBot - this.riverH(g)) { this.river++; continue; }
      } else if (d.y >= g.sy(d.x)) { this.land(d.x, g); continue; }
      keep.push(d);
    }
    this.drops = keep;
    keep = [];
    for (i = 0; i < this.surf.length; i++) {
      var s = this.surf[i], c0 = Math.floor(s.x / g.cw);
      s.x += g.w * 0.16 * dt;
      var c1 = Math.floor(s.x / g.cw);
      if (s.x >= g.land) { this.river++; continue; }
      if (c1 !== c0 && this.soak(c1, s.x, g)) continue;
      keep.push(s);
    }
    this.surf = keep;
    keep = [];
    for (i = 0; i < this.sink.length; i++) {
      var p = this.sink[i]; p.y += g.h * 0.35 * dt;
      if (p.y < p.to) keep.push(p);
    }
    this.sink = keep;
  };
  Panel.prototype.soak = function(c, x, g){
    if (c < 0 || c >= N || this.allow[c] < 1 || this.S[c] >= 0.995) return false;
    this.allow[c] -= 1; this.S[c] = Math.min(1, this.S[c] + 0.018);
    var top = g.sy(x);
    this.sink.push({x: x, y: top, to: top + (g.floor - top) * this.S[c]});
    return true;
  };
  Panel.prototype.land = function(x, g){
    var c = Math.floor(x / g.cw);
    if (!this.soak(c, x, g)) this.surf.push({x: x});
  };
  Panel.prototype.riverH = function(g){ return Math.min(g.h * 0.42, this.river * g.h * 0.0012); };
  Panel.prototype.draw = function(C){
    var g = this.geom(), x = this.cv.getContext('2d'), dpr = window.devicePixelRatio || 1, i;
    if (this.cv.width !== Math.round(g.w * dpr)) {
      this.cv.width = Math.round(g.w * dpr); this.cv.height = Math.round(g.h * dpr);
    }
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    x.clearRect(0, 0, g.w, g.h);
    // soil, then the water it holds: a smoothed wetting front, since
    // column steps read as data and none of this is
    x.fillStyle = C.land;
    x.beginPath(); x.moveTo(0, g.sy(0)); x.lineTo(g.land, g.sy(g.land));
    x.lineTo(g.land, g.floor); x.lineTo(0, g.floor); x.fill();
    x.globalAlpha = 0.42; x.fillStyle = C.flood;
    x.beginPath(); x.moveTo(0, g.sy(0)); x.lineTo(g.land, g.sy(g.land));
    for (i = N - 1; i >= 0; i--) {
      var a = this.S[Math.max(0, i - 1)], b = this.S[i], c = this.S[Math.min(N - 1, i + 1)];
      var cx = (i + 0.5) * g.cw, top = g.sy(cx);
      x.lineTo(cx, top + (g.floor - top) * (a + 2 * b + c) / 4);
    }
    x.lineTo(0, g.sy(0)); x.fill();
    x.globalAlpha = 1;
    // channel and river
    x.fillStyle = C.land;
    x.fillRect(g.land, g.chanBot, g.w - g.land, g.floor - g.chanBot);
    var rh = this.riverH(g);
    x.fillStyle = C.flood; x.globalAlpha = 0.9;
    x.fillRect(g.land, g.chanBot - rh, g.w - g.land, rh);
    x.globalAlpha = 1;
    x.strokeStyle = C.ink; x.lineWidth = 1;
    x.beginPath(); x.moveTo(0, g.sy(0)); x.lineTo(g.land, g.sy(g.land));
    x.lineTo(g.land, g.chanBot); x.lineTo(g.w, g.chanBot); x.stroke();
    x.fillStyle = C.ink; x.font = '9px ' + C.mono; x.textAlign = 'center';
    if (g.w - g.land >= 36) x.fillText('RIVER', (g.land + g.w) / 2, g.floor - 1);
    // rain, water soaking in, water running off
    x.strokeStyle = C.flood; x.lineWidth = 1.3;
    x.beginPath();
    for (i = 0; i < this.drops.length; i++) {
      var d = this.drops[i]; x.moveTo(d.x, d.y - 7); x.lineTo(d.x, d.y);
    }
    x.stroke();
    x.fillStyle = C.flood;
    for (i = 0; i < this.sink.length; i++) x.fillRect(this.sink[i].x - 0.8, this.sink[i].y, 1.6, 3);
    for (i = 0; i < this.surf.length; i++) {
      var s = this.surf[i]; x.beginPath(); x.arc(s.x, g.sy(s.x) - 2, 2.1, 0, 6.3); x.fill();
    }
  };

  figs.forEach(function(fig){
    var svg = fig.querySelector('svg'), live = fig.querySelector('.fx-live');
    if (!svg || !live) return;
    var cvs = live.querySelectorAll('canvas'), clock = live.querySelector('.fx-clock');
    var P = [new Panel(cvs[0], false), new Panel(cvs[1], true)];
    svg.style.display = 'none'; live.style.display = 'block';
    var t0 = null, last = null, on = false;
    var C = {};
    function colours(){ C = {land: css('--land'), flood: css('--flood'), ink: css('--ink-faint'), mono: css('--mono')}; }
    colours();
    function frame(ts){
      if (!on) { last = null; return; }
      if (t0 === null) t0 = ts;
      var dt = last === null ? 0 : Math.min(0.05, (ts - last) / 1000); last = ts;
      var t = (ts - t0) / 1000;
      if (t > T + HOLD) { t0 = ts; t = 0; P.forEach(function(p){ p.reset(); }); }
      var tt = Math.min(t, T);
      P.forEach(function(p){ if (t <= T + 1.5) p.step(tt, dt); p.draw(C); });
      clock.textContent = 'HOUR ' + Math.round(24 * tt / T) + ' OF 24';
      requestAnimationFrame(frame);
    }
    new IntersectionObserver(function(es){
      es.forEach(function(e){
        var was = on; on = e.isIntersecting;
        if (on && !was) { colours(); requestAnimationFrame(frame); }
      });
    }, {threshold: .25}).observe(fig);
  });
})();
</script>"""
