// /ant, the four-question widget, redrawn (VD, canvas page "The Long Swell
// Ant Questions, redrawn", 13 Nov; faults in research/vd/review_ant_prototype
// _2026-11-13.md, after Kristjan: "absolutely not happy"). One question, one
// chart, one quantity per screen; every path drawn and labelled before a
// choice; the price panel waits for the end; the reveal keeps the four
// answers in sight. Prices come from values.js (window.ANT), the history from
// history.js (window.ANT_HISTORY, AI - Compute, verified points only).
(function () {
const IPO = ANT.IPO, H = window.ANT_HISTORY;
// The labs' compute spend, $bn, from AI - Compute model v4.1
// (scenarios_v41.py), where a crash cuts it 40% from 2028. Screen 1's money
// paid to the labs comes from history.js, history and paths in one file.
const SPEND = { yes: [156, 220, 275, 335, 395], no: [156, 220, 165, 201, 237] };
SPEND.mid = SPEND.yes.map((v, i) => (v + SPEND.no[i]) / 2);
const TODAY_SHARE = 45;

const Q = [
  { k: 'speed', short: 'AI by 2030', t: 'Which statement is closest to what you think will happen with AI by 2030?', o: [
    ['late', 'It keeps improving, but more slowly', 'Like phones after the first iPhones: better every year, less of a leap'],
    ['early', 'It stalls soon', 'Putting AI into every business turns out to be hard'],
    ['takeoff', 'Something like AGI arrives', 'Progress speeds up, and AI does more of the work itself']] },
  { k: 'money', short: 'Data centres', t: 'What is your view on data centres?', o: [
    ['yes', 'Investors keep piling money in', 'Spending on new data centres keeps climbing'],
    ['mid', 'Something in between', 'A wobble: a funding crash is as likely as not'],
    ['no', 'The money stops', 'A funding crash in 2027-29 halts the build-out for a few years']] },
  { k: 'world', short: 'Who gets paid', t: 'In 2030, a lawyer at your company uses AI to check a contract. Who gets paid?', o: [
    ['C4', 'The labs, end to end', 'Anthropic or OpenAI sell a finished legal AI that does the review, and own the customer'],
    ['C1', 'The labs, as a tool', 'The company buys Claude or ChatGPT by the use, and the lawyer does the work'],
    ['C3', 'A specialist AI firm', 'A legal AI company owns the client, often on its own models'],
    ['C5', 'Microsoft or Google', 'It is a button in Word or Gmail, already in the bill'],
    ['C2', 'Nobody much', 'Free models are just as good, so AI is cheap like spellcheck']] },
  { k: 'share', short: 'Anthropic vs rivals', t: 'Anthropic, OpenAI, Google: who is winning?', o: [
    ['55', 'Anthropic pulls ahead', 'More companies choose Claude than today'],
    ['45', 'Anthropic holds its own', 'It keeps the 45% it has today'],
    ['35', 'The others catch up', 'OpenAI, Google and others win back customers']] },
];
const PAID = H.spend.paths, bn = v => '$' + Math.round(v).toLocaleString('en-US') + 'bn';
// The figure an option carries, and the longer one the reveal lists.
const FIG = {
  speed: v => bn(PAID[v][4]), money: v => '$' + Math.round(SPEND[v][4]) + 'bn',
  world: v => '$' + Math.round(H.ai[v].labs) + ' to labs', share: v => v + '%',
};
const LONG = {
  speed: v => bn(PAID[v][4]) + ' a year paid to AI labs', money: v => '$' + Math.round(SPEND[v][4]) + 'bn a year on computing',
  world: v => '$' + Math.round(H.ai[v].labs) + ' of every AI $100 to labs', share: v => v + '% of lab revenue',
};

const A = {}; let step = 0, done = false, editing = false, first = true;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const phone = () => window.matchMedia && matchMedia('(max-width: 720px)').matches;
// '2024' is a calendar year, drawn mid-year; '2026-Q1' a quarter; '2026-09' a month.
const t2x = s => { const [y, m] = String(s).split('-'); return +y + (!m ? 0.5 : m[0] === 'Q' ? (m[1] * 3 - 1.5) / 12 : (m - 0.5) / 12); };
const line = pts => pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
// A ratio in words where it lands on a plain fraction, else a percentage.
function frac(r) {
  const F = [[0.25, 'a quarter'], [1 / 3, 'a third'], [0.5, 'half'], [2 / 3, 'two-thirds'], [0.75, 'three-quarters']];
  const f = F.find(([v]) => Math.abs(r - v) < 0.04);
  return f ? f[1] : Math.round(r * 100) + '%';
}
function sig2(v) { const p = Math.pow(10, Math.floor(Math.log10(v)) - 1); return Math.round(v / p) * p; }

// ---------- 1. AI by 2030: money paid to the AI labs, so far and to 2030 ----------
// Kristjan: "why are we using google only? why cannot we use token spend?"
// Tokens are priced, so the money paid to the labs is the paid-for token
// volume; it has a sourced history. Plain dollar axis, so the paths read as
// amounts. History is the two sourced labs; the paths start from all labs.
function chart1(sel, ph) {
  const W = ph ? 328 : 860, Ht = ph ? 300 : 340, L = ph ? 64 : 70, R = ph ? 70 : 210, T = 16, B = 28, x0 = 2024, x1 = 2030.6;
  const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = v => T + (Ht - T - B) * (1 - v / 1100);
  let s = '';
  [0, 250, 500, 750, 1000].forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${v ? bn(v) : '$0'}</text>`);
  [2024, 2026, 2028, 2030].forEach(y => s += `<text x="${X(y + 0.5)}" y="${Ht - 6}" text-anchor="middle">${y}</text>`);
  const h = H.spend.history.map(([d, v]) => [X(t2x(d)), Y(v)]), sx = X(t2x(H.spend.seam[0])), sy = Y(H.spend.seam[1]);
  s += `<path d="${line(h)}" fill="none" stroke="var(--soft)" stroke-width="3"/>`;
  h.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="3.5" fill="var(--soft)"/>`);
  if (!ph) s += `<text x="${h[0][0]}" y="${h[0][1] - 12}" class="small">Anthropic and OpenAI</text><text x="${sx - 10}" y="${sy - 12}" text-anchor="end" class="big" style="fill:var(--ink)">All labs today, ${bn(H.spend.seam[1])} a year</text>`;
  const N = ph ? { late: bn(PAID.late[4]), early: bn(PAID.early[4]), takeoff: bn(PAID.takeoff[4]) }
    : { late: 'Keeps improving, ' + bn(PAID.late[4]), early: 'Stalls, ' + bn(PAID.early[4]), takeoff: 'AGI, ' + bn(PAID.takeoff[4]) };
  const ends = [];
  ['early', 'late', 'takeoff'].forEach(k => {
    const on = sel === k, pts = [[sx, sy]].concat(PAID[k].slice(1).map((v, i) => [X(H.spend.years[i + 1] + 0.5), Y(v)]));
    s += `<path d="${line(pts)}" fill="none" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 4 : 2.5}"/>`;
    s += `<circle cx="${pts[4][0]}" cy="${pts[4][1]}" r="${on ? 5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}"/>`;
    ends.push([k, pts[4][1], on]);
  });
  s += `<circle cx="${sx}" cy="${sy}" r="5" fill="var(--ink)" stroke="var(--paper)" stroke-width="2"/>`;
  ends.sort((a, b) => a[1] - b[1]); for (let i = 1; i < ends.length; i++) if (ends[i][1] - ends[i - 1][1] < 18) ends[i][1] = ends[i - 1][1] + 18;
  ends.forEach(([k, y, on]) => s += `<text x="${W - R + (ph ? 8 : 12)}" y="${y + 4}" class="big ${on ? 'ink' : ''}">${N[k]}</text>`);
  const h0 = H.spend.history[0][1];
  return `<h4>Money paid to AI labs, a year</h4><svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Money paid to AI labs: Anthropic and OpenAI ${bn(h0)} in 2024, all labs ${bn(H.spend.seam[1])} a year today; by 2030 ${bn(PAID.early[4])}, ${bn(PAID.late[4])} or ${bn(PAID.takeoff[4])}">${s}</svg>
    <p class="say">In 2024 people and companies paid Anthropic and OpenAI about ${bn(h0)}. Today they pay all AI labs at a rate of ${bn(H.spend.seam[1])} a year.</p>
    <p class="src">Anthropic's audited revenue and OpenAI's reported revenue; today's all-labs figure adds an estimated $30bn for Google, xAI and others. Paths to 2030: AI - Compute model, before any funding crash.</p>`;
}

// ---------- 2 and 3: the answers are the bars ----------
// VD, canvas page "The Long Swell Ant Questions 2 and 3, simple", after
// Kristjan: screen 2 "Such a messy screen! ... It needs to be simple!",
// screen 3 "Too confusing". Each answer button holds one bar, every bar on
// one scale, one dashed line for today, labelled once on the first bar. No
// chart above the answers, no legend, no ranked list.
const BARS = {
  money: { max: 400, today: SPEND.yes[0], val: v => Math.round(SPEND[v][4]), fmt: v => '$' + v + 'bn', track: false },
  world: { max: 100, today: Math.round(H.ai.today.labs), val: v => Math.round(H.ai[v].labs), fmt: v => '$' + v, track: true },
};
function bar(k, v, on, first, ph) {
  const q = BARS[k], W = ph ? 296 : 480, VW = ph ? 64 : 80, BW = W - VW, Ht = first ? 40 : 26, y = first ? 16 : 2, h = 20, X = x => x / q.max * BW, tx = X(q.today), n = q.val(v);
  let s = '';
  if (q.track) s += `<rect x="0" y="${y}" width="${BW}" height="${h}" fill="var(--sunk)"/>`;
  s += `<rect x="0" y="${y}" width="${X(n)}" height="${h}" fill="${on ? 'var(--ink)' : 'var(--line)'}"/>`;
  s += `<line x1="${tx}" x2="${tx}" y1="${y - (first ? 4 : 3)}" y2="${y + h + 3}" stroke="var(--soft)" stroke-width="1.5" stroke-dasharray="3 3"/>`;
  if (first) s += `<text x="${tx}" y="10" text-anchor="${tx > BW - 60 ? 'end' : 'middle'}">today ${q.fmt(q.today)}</text>`;
  s += `<text x="${Math.max(X(n), q.track ? BW : 0) + 10}" y="${y + 16}" class="v">${q.fmt(n)}</text>`;
  return `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="${q.fmt(n)}, against today's ${q.fmt(q.today)}">${s}</svg>`;
}
function chart2() {
  const mil = H.comps.find(c => /military/.test(c[0]));
  return `<p class="lead">What AI labs would spend on computing in 2030, a year. <b>For scale, the US military spends $${Math.round(mil[1])}bn.</b></p>`;
}
function chart3() {
  return `<p class="lead">Of every <b>$100</b> a company spends on AI, how much goes to labs like Anthropic.</p>`;
}
const SRC = {
  money: 'Labs from the AI - Compute model; US military from SIPRI.',
  world: 'AI - Compute model estimate; how the rest of the $100 splits is in the full model.',
};

// ---------- 4. Anthropic vs rivals: one basis, the answers' own ----------
// Kristjan: "Where is history?" Same basis as the answers, Anthropic over all
// lab revenue. Only today is on the full market; earlier points hold the
// other labs at today's size against the two leaders, so they are drawn
// hollow on a dashed line and the source line says so.
function chart4(sel, ph) {
  const W = ph ? 328 : 860, Ht = ph ? 240 : 280, L = 44, R = ph ? 56 : 220, T = 14, B = 28, x0 = 2024, x1 = 2030.6;
  const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = v => T + (Ht - T - B) * (1 - v / 60);
  let s = '';
  [0, 20, 40, 60].forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${v}%</text>`);
  [2024, 2026, 2028, 2030].forEach(y => s += `<text x="${X(y + 0.5)}" y="${Ht - 6}" text-anchor="middle">${y}</text>`);
  const h = H.share.map(([d, v, ok]) => [X(t2x(d)), Y(v), ok]), [sx, sy] = h[h.length - 1];
  s += `<path d="${line(h)}" fill="none" stroke="var(--soft)" stroke-width="2.5" stroke-dasharray="5 4"/>`;
  const N = { 55: 'Pulls ahead, 55%', 45: 'Holds its own, 45%', 35: 'Others catch up, 35%' };
  ['35', '45', '55'].forEach(k => {
    const on = sel === k, ex = X(2030.5);
    s += `<line x1="${sx}" x2="${ex}" y1="${sy}" y2="${Y(+k)}" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 4 : 2.5}"/><circle cx="${ex}" cy="${Y(+k)}" r="${on ? 5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}"/>`;
    s += `<text x="${ex + 10}" y="${Y(+k) + 4}" class="big ${on ? 'ink' : ''}">${ph ? k + '%' : N[k]}</text>`;
  });
  h.forEach(([x, y, ok]) => s += ok ? `<circle cx="${x}" cy="${y}" r="5" fill="var(--ink)" stroke="var(--paper)" stroke-width="2"/>`
    : `<circle cx="${x}" cy="${y}" r="3.5" fill="var(--paper)" stroke="var(--soft)" stroke-width="2"/>`);
  const first = H.share[0];
  if (!ph) s += `<text x="${h[0][0] - 6}" y="${h[0][1] + 22}" class="small">${first[1]}% in ${first[0]}</text><text x="${sx}" y="${sy + 30}" text-anchor="middle" class="big" style="fill:var(--ink)">${TODAY_SHARE}% today</text>`;
  return `<h4>Anthropic's share of what is paid to the AI labs</h4><svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Anthropic's share of AI lab revenue: about ${first[1]}% in ${first[0]}, ${TODAY_SHARE}% today, to 35, 45 or 55% in 2030">${s}</svg>
    <p class="say">Anthropic went from about ${first[1]}% of what was paid to the AI labs in ${first[0]} to ${TODAY_SHARE}% today. OpenAI, Google and the rest share whatever it does not win.</p>
    <p class="src">Only today's ${TODAY_SHARE}% is measured against the whole market. Earlier points (hollow) hold Google, xAI and others at today's size against the two leaders, an estimate. Anthropic's audited revenue; OpenAI's reported.</p>`;
}
const CHARTS = [chart1, chart2, chart3, chart4];

// ---------- a question screen ----------
function ask() {
  const q = Q[step], sel = A[q.k], ph = phone();
  $('prog').innerHTML = `The Anthropic IPO &nbsp;·&nbsp; ${step + 1} of 4 <i>${Q.map((_, j) => `<b class="${j <= step ? 'on' : ''}"></b>`).join('')}</i>`;
  $('qt').textContent = q.t;
  $('qchart').innerHTML = CHARTS[step](sel, ph);
  const bars = !!BARS[q.k];
  $('opts').className = 'opts' + (bars ? ' bars' : q.o.length === 3 ? ' three' : '');
  $('opts').innerHTML = q.o.map(([v, l, d], i) => bars
    ? `<button type="button" aria-pressed="${sel === v}" data-v="${v}"><span class="t"><b>${esc(l)}</b><span>${esc(d)}</span></span>${bar(q.k, v, sel === v, i === 0, ph)}</button>`
    : `<button type="button" aria-pressed="${sel === v}" data-v="${v}"><b>${esc(l)}</b><i>${FIG[q.k](v)}</i><span>${esc(d)}</span></button>`).join('');
  $('after3').innerHTML = bars ? `<p class="src">${SRC[q.k]}</p>` : '';
  $('back').hidden = !step || editing;
}
function show(onReveal) {
  $('ask').hidden = onReveal; $('panel').hidden = !onReveal; $('after').hidden = !onReveal;
}
// A tap answers and moves on (Kristjan: "'Next question' button is bad UX,
// once you click and answer you are done"). The pick shows in ink for a
// moment so the tap reads, then the next question, or the price, loads.
let moving = false;
$('opts').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b || moving) return;
  A[Q[step].k] = b.dataset.v; ask(); moving = true;
  setTimeout(() => {
    moving = false;
    if (editing || step === Q.length - 1) { editing = false; reveal(); } else { step++; ask(); window.scrollTo(0, 0); }
  }, 250);
});
$('back').addEventListener('click', () => { step = Math.max(0, step - 1); ask(); });
// Charts are drawn for the width they sit at; redraw when that changes.
let wasPhone = phone();
window.addEventListener('resize', () => { const p = phone(); if (p !== wasPhone) { wasPhone = p; if (!done || editing) ask(); else panel(); } });

// ---------- the reveal ----------
function answers() { return Q.map(q => A[q.k]).join(','); }
function reveal() {
  done = true; show(true); panel();
  const p = $('panel');
  if (p.getBoundingClientRect().top < 0) {
    const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    p.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' });
  }
}
function panel() {
  const v = ANT.price(A), fails = v <= 0, d = v / IPO - 1;
  $('head').innerHTML = `<p class="kick">On your view of AI, Anthropic is worth</p><div class="v">${fails ? '$0' : '$' + Math.round(v) + '<small> a share</small>'}</div>` +
    `<p class="vs">${fails ? 'Its debts and compute contracts outweigh the business. <b>Shareholders get nothing.</b>' : `That is <b>${Math.abs(Math.round(d * 100))}% ${d >= 0 ? 'above' : 'below'}</b> the $${IPO} IPO price.`}</p>`;
  ANTSCALE($('strip'), { price: v, animate: first }); first = false;
  let zero = 0, above = 0, total = 0;
  for (const sp of ['late', 'early', 'takeoff']) for (const m of ['yes', 'mid', 'no']) for (const w of ['C1', 'C2', 'C3', 'C4', 'C5']) {
    const x = ANT.price({ speed: sp, money: m, world: w, share: A.share }); total++;
    if (x <= 0) zero++; else if (x >= IPO) above++;
  }
  $('cap').textContent = `${zero} of ${total} ways to answer leave shareholders with nothing; ${above} ${above === 1 ? 'beats' : 'beat'} the IPO price.`;
  // How the answers got there: one figure each; Change reopens that question
  // with its chart and comes back here.
  $('mine').innerHTML = Q.map((q, i) => {
    const o = q.o.find(x => x[0] === A[q.k]);
    return `<div class="hrow"><span class="q">${q.short}</span><span class="a">${esc(o[1])}</span><span class="f">${LONG[q.k](A[q.k])}</span><button type="button" class="c" data-i="${i}">Change</button></div>`;
  }).join('');
  try { history.replaceState(null, '', '?a=' + answers()); } catch (e) {}
  const href = '../ant-pro/?a=' + answers();
  $('more').href = href;
  const sw = document.querySelector('.sw a[data-to="pro"]');
  if (sw) sw.href = href;
  // In the one-file prototype both pages share a document: hand the answers across in place.
  if (window.ANT_PROTO) [$('more'), sw].forEach(a => a && (a.onclick = e => { e.preventDefault(); ANT_PROTO.toPro(answers()); }));
}
$('mine').addEventListener('click', e => {
  const b = e.target.closest('button.c'); if (!b) return;
  step = +b.dataset.i; editing = true; show(false); ask(); window.scrollTo(0, 0);
});

// ?a=late,mid,C1,45 opens on the reveal; ?step=2 opens on question 3 (checks)
const qs = new URLSearchParams(location.search), pre = qs.get('a');
const ok = (q, v) => q.o.some(o => o[0] === v);
if (pre && pre.split(',').length === 4 && pre.split(',').every((v, i) => ok(Q[i], v))) {
  pre.split(',').forEach((v, i) => A[Q[i].k] = v); reveal();
} else { step = Math.min(3, +(qs.get('step') || 0)); Q.slice(0, step).forEach(q => A[q.k] = q.o[0][0]); show(false); ask(); }
})();
