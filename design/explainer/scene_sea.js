// Scene 3 of "How a flood is made": it starts from the sea. A normal
// September beside September 2026, for Barcelona's own sea, the western
// Mediterranean. Kristjan preferred the moving sea in FLO's storyboard
// prototype to a static map, and this follows it with one honest change:
// the prototype scaled its vapour to about 20% more (the 7%-per-degree
// ceiling), but MEASURED evaporation was +6.3% basin-wide and 8th of 36,
// not a record, and during the storm itself the western basin evaporated
// 22% less than normal (FLO, evaporation.not_claimed).
//
// KRISTJAN, 16 OCT: at the measured rate the two panes looked the same,
// which made the point nobody would see; "it's okay to create content".
// So the 2026 sea is DRAWN more agitated (ENERGY), and the figure says
// on its face that the motion is illustrative and the temperatures are
// measured. No evaporation number is printed on the canvas any more.

const root = document.getElementById("sea");
const cv = document.getElementById("sea-cv");
const ctx = cv.getContext("2d");
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const D = root.dataset;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const panes = [
  { key: "normal", t: +D.tNormal, energy: 1.0, title: "WESTERN MEDITERRANEAN \u00b7 NORMAL SEPTEMBER",
    top: "#417785", deep: "#0A4A57", sub: "1991 to 2020 average" },
  { key: "y2026", t: +D.t2026, energy: 2.6, title: "WESTERN MEDITERRANEAN \u00b7 SEPTEMBER 2026",
    top: "#C05B3D", deep: "#5E1806", sub: "warmest in a record going back to 1940" },
];
for (const p of panes) p.parts = [];

function size() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  cv.width = Math.round(cv.clientWidth * dpr); cv.height = Math.round(cv.clientHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
addEventListener("resize", size); size();

const RATE = 70;            // particles per second at energy 1: illustrative
function frame(now, dt) {
  const W = cv.clientWidth, H = cv.clientHeight, gap = 16;
  const pw = (W - gap) / 2, surf = H * 0.58;
  ctx.clearRect(0, 0, W, H);
  panes.forEach((p, i) => {
    const x0 = i * (pw + gap);
    ctx.save(); ctx.beginPath(); ctx.rect(x0, 0, pw, H); ctx.clip();
    // air: a faint warmth above the hot sea
    const air = ctx.createLinearGradient(0, 0, 0, surf);
    air.addColorStop(0, css("--paper"));
    air.addColorStop(1, i ? "rgba(220,149,126,.62)" : "rgba(133,167,176,.58)");
    ctx.fillStyle = air; ctx.fillRect(x0, 0, pw, surf);
    // sea, with a moving surface
    const sea = ctx.createLinearGradient(0, surf, 0, H);
    sea.addColorStop(0, p.top); sea.addColorStop(1, p.deep);
    ctx.fillStyle = sea;
    ctx.beginPath(); ctx.moveTo(x0, H);
    const E = p.energy;
    for (let x = 0; x <= pw; x += 5) {
      const y = surf + 3 * E * Math.sin(x / 38 + now * 1.3 * E + i) + 2 * E * Math.sin(x / 13 - now * 2.1 * E)
              + (E > 1 ? 1.5 * Math.sin(x / 6 + now * 7) : 0);
      ctx.lineTo(x0 + x, y);
    }
    ctx.lineTo(x0 + pw, H); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.lineWidth = 1;
    for (let k = 1; k <= 4; k++) {
      ctx.beginPath();
      for (let x = 0; x <= pw; x += 8) {
        const y = surf + k * 18 + 2 * E * Math.sin(x / (30 + k * 9) + now * (1 + k * 0.3) * E + k);
        x ? ctx.lineTo(x0 + x, y) : ctx.moveTo(x0 + x, y);
      }
      ctx.stroke();
    }
    // heat shimmer over the hot sea: rising, wavering columns of light
    if (E > 1) {
      ctx.strokeStyle = "rgba(255,236,226,.16)"; ctx.lineWidth = 2;
      for (let k = 0; k < 9; k++) {
        const bx = ((k * 97 + now * 18) % pw);
        ctx.beginPath();
        for (let y = surf; y > surf * 0.35; y -= 6) {
          const xx = bx + 5 * Math.sin(y / 14 + now * 5 + k);
          y === surf ? ctx.moveTo(x0 + xx, y) : ctx.lineTo(x0 + xx, y);
        }
        ctx.stroke();
      }
    }
    // vapour: illustrative, scaled by the pane's energy
    if (!reduce) {
      let n = E * E * RATE * dt;
      while (n > 0) { if (Math.random() < n) p.parts.push({ x: Math.random() * pw, y: surf, v: (18 + Math.random() * 26) * (0.7 + 0.45 * E), r: 1.6 + Math.random() * 2.2 * (E > 1 ? 1.3 : 1), ph: Math.random() * 6 }); n -= 1; }
    }
    p.parts = p.parts.filter(q => q.y > 10);
    for (const q of p.parts) {
      if (!reduce) { q.y -= q.v * dt; q.x += Math.sin(q.y / 22 + q.ph) * 0.35 * p.energy; }
      const a = Math.max(0, Math.min(1, (q.y - 10) / (surf * 0.9)));
      ctx.fillStyle = "rgba(240,244,245," + (0.85 * a).toFixed(3) + ")";
      ctx.beginPath(); ctx.arc(x0 + q.x, q.y, q.r, 0, 6.283); ctx.fill();
    }
    // the readout
    ctx.fillStyle = css("--ink-soft");
    ctx.font = "500 11px " + css("--mono"); ctx.fillText(p.title, x0 + 14, 24);
    ctx.fillStyle = css("--ink");
    ctx.font = "500 " + Math.round(Math.min(44, pw / 6.5)) + "px " + css("--mono");
    ctx.fillText(p.t.toFixed(1) + " °C", x0 + 14, 24 + Math.min(52, pw / 5.5));
    ctx.fillStyle = "rgba(255,255,255,.92)";
    ctx.font = "400 12px " + css("--mono"); ctx.fillText(p.sub, x0 + 14, H - 16);
    if (i === 1) {   // on the figure itself, not only in the source line
      ctx.font = "500 10px " + css("--mono"); ctx.textAlign = "right";
      ctx.fillStyle = css("--ink-soft"); ctx.fillText("MOTION ILLUSTRATIVE", x0 + pw - 14, 24);
      ctx.textAlign = "left";
    }
    ctx.restore();
  });
}

// Reduced motion: one still frame with the air already full of vapour.
if (reduce) {
  for (const p of panes) for (let k = 0; k < Math.round(p.energy * p.energy * 160); k++)
    p.parts.push({ x: Math.random() * 400, y: 20 + Math.random() * cv.clientHeight * 0.5, v: 0, r: 1.6 + Math.random() * 2, ph: 0 });
  frame(0, 0);
} else {
  // warm up, so the air is not empty when the reader arrives
  for (let k = 0; k < 240; k++) frame(k / 60, 1 / 60);
  let on = false, last = null;
  const loop = ts => {
    if (!on) { last = null; return; }
    const dt = last === null ? 0 : Math.min(0.05, (ts - last) / 1000); last = ts;
    frame(ts / 1000, dt); requestAnimationFrame(loop);
  };
  new IntersectionObserver(es => { const was = on; on = es[0].isIntersecting; if (on && !was) requestAnimationFrame(loop); })
    .observe(root);
}
