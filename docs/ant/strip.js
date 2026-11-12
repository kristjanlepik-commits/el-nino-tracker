// The one price scale /ant and /ant-pro both draw (VD, "Ant Pro Hero, second
// pass", 12 Nov). No dots: Kristjan found the dot strip confusing ("some
// weird dots confuse a lot"; for /ant, "Drop them too"). One $0 to $MAX (values.js)
// scale with three things on it: the price as the one ink mark, the IPO as a
// short tick, and on /ant-pro how far the price moves with Anthropic's share,
// as a band on the axis. Ink means yours, on both pages.
//
// o.price: the price, or null before /ant's reveal (ticks and IPO only, so
// the panel does not jump when the price lands). o.lo, o.hi: the band.
window.ANTSCALE = function (svg, o) {
  const IPO = ANT.IPO, MAX = ANT.SCALE || 400, X0 = 10, X1 = 390, X = v => X0 + Math.min(Math.max(v, 0), MAX) / MAX * (X1 - X0), AX = 44;
  // Ticks every $50 on a scale up to $200, every $100 above that, dropping
  // any that would sit under the IPO label.
  const step = MAX <= 200 ? 50 : 100, ticks = [];
  for (let t = step; t <= MAX; t += step) if (Math.abs(X(t) - X(IPO)) > 40) ticks.push(t);
  let s = `<line x1="${X0}" x2="${X1}" y1="${AX}" y2="${AX}" stroke="var(--rule)"/>`;
  // short enough to clear the price label when the two are close
  s += `<line x1="${X(IPO)}" x2="${X(IPO)}" y1="${AX}" y2="${AX - 11}" stroke="var(--soft)" stroke-width="1"/>`;
  if (o.lo != null) s += `<rect x="${X(o.lo)}" y="${AX - 4}" width="${Math.max(X(o.hi) - X(o.lo), 1)}" height="8" fill="var(--line)"/>`;
  s += `<text x="${X(0)}" y="${AX + 22}" text-anchor="start">$0</text>`;
  s += `<text x="${X(IPO)}" y="${AX + 22}" text-anchor="middle" style="font-weight:500">$${IPO} IPO</text>`;
  ticks.forEach(t => s += `<text x="${X(t)}" y="${AX + 22}" text-anchor="${t === MAX ? 'end' : 'middle'}">$${t}</text>`);
  if (o.price != null) s += `<g class="${o.animate ? 'me in' : 'me'}"><circle cx="${X(o.price)}" cy="${AX}" r="7" fill="var(--ink)" stroke="var(--sunk)" stroke-width="2"/>` +
    `<text x="${X(o.price)}" y="${AX - 14}" text-anchor="middle" style="fill:var(--ink);font-weight:600">$${Math.round(o.price)}</text></g>`;
  svg.setAttribute('viewBox', '0 0 400 74');
  svg.setAttribute('aria-label', o.price == null ? `Price scale from $0 to $${MAX}, with the IPO at $${IPO}` :
    `Price scale from $0 to $${MAX}: the IPO at $${IPO}, the price at $${Math.round(o.price)}` + (o.lo != null ? `, and a band from $${Math.round(o.lo)} to $${Math.round(o.hi)} as Anthropic's share runs from 35 to 55%` : ''));
  svg.innerHTML = s;
};
