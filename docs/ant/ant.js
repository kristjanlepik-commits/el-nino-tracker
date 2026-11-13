// /ant, the four-question widget, redrawn (VD, canvas page "The Long Swell
// Ant Questions, redrawn", 13 Nov; faults in research/vd/review_ant_prototype
// _2026-11-13.md, after Kristjan: "absolutely not happy"). One question, one
// chart, one quantity per screen; every path drawn and labelled before a
// choice; the price panel waits for the end; the reveal keeps the four
// answers in sight. Prices come from values.js (window.ANT), the history from
// history.js (window.ANT_HISTORY, AI - Compute, verified points only).
(function () {
const IPO = ANT.IPO, H = window.ANT_HISTORY;
// The model's paths, from AI - Compute model v4.1 (scenarios_v41.py):
// all Western AI tokens a day from about 400 trillion at end-2026, and the
// labs' compute spend, $bn, where a crash cuts it 40% from 2028.
const USE = { late: [400, 1000, 2000, 3200, 5120], early: [400, 640, 832, 998, 1148], takeoff: [400, 1120, 2912, 6698, 14065] };
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
const times = v => Math.round(USE[v][4] / USE[v][0]);
// The figure an option carries, and the longer one the reveal lists.
const FIG = {
  speed: v => times(v) + '× today', money: v => '$' + Math.round(SPEND[v][4]) + 'bn',
  world: v => '$' + Math.round(H.ai[v].labs) + ' to labs', share: v => v + '%',
};
const LONG = {
  speed: v => times(v) + " times today's AI use", money: v => '$' + Math.round(SPEND[v][4]) + 'bn a year on computing',
  world: v => '$' + Math.round(H.ai[v].labs) + ' of every AI $100 to labs', share: v => v + '% of lab revenue',
};

const A = {}; let step = 0, done = false, editing = false, first = true;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const phone = () => window.matchMedia && matchMedia('(max-width: 720px)').matches;
const t2x = s => { const [y, m] = String(s).split('-').map(Number); return y + ((m || 12) - 0.5) / 12; };
const line = pts => pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
// A ratio in words where it lands on a plain fraction, else a percentage.
function frac(r) {
  const F = [[0.25, 'a quarter'], [1 / 3, 'a third'], [0.5, 'half'], [2 / 3, 'two-thirds'], [0.75, 'three-quarters']];
  const f = F.find(([v]) => Math.abs(r - v) < 0.04);
  return f ? f[1] : Math.round(r * 100) + '%';
}
function sig2(v) { const p = Math.pow(10, Math.floor(Math.log10(v)) - 1); return Math.round(v / p) * p; }

// ---------- 1. AI by 2030: every line against its own 2026 ----------
function chart1(sel, ph) {
  const W = ph ? 328 : 860, Ht = ph ? 300 : 340, L = ph ? 84 : 110, R = ph ? 44 : 190, T = 16, B = 28, x0 = 2024, x1 = 2031;
  const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = v => T + (Ht - T - B) * (1 - (Math.log10(v) + 3) / 5);
  const G = [['1/1000', 0.001], ['1/100', 0.01], ['1/10', 0.1], ['2026 level', 1], ['10 times', 10], ['100 times', 100]];
  let s = '';
  G.forEach(([n, v]) => { const on = v === 1; s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${on ? 'var(--soft)' : 'var(--rule)'}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" class="${on ? 'ink' : ''}">${n}</text>`; });
  [2024, 2026, 2028, 2030].forEach(y => s += `<text x="${X(y + 0.5)}" y="${Ht - 6}" text-anchor="middle">${y}</text>`);
  const last = H.google[H.google.length - 1][1], growth = sig2(last / H.google[0][1]);
  const g = H.google.map(([d, v]) => [X(t2x(d)), Y(v / last)]);
  s += `<path d="${line(g)}" fill="none" stroke="var(--soft)" stroke-width="3"/>`;
  g.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="var(--soft)"/>`);
  s += `<text x="${g[1][0] + 10}" y="${g[1][1] + 18}" class="big" style="fill:var(--ink)">Google: ${growth} times</text><text x="${g[1][0] + 10}" y="${g[1][1] + 34}" class="big">in two years</text>`;
  const N = ph ? { late: times('late') + '×', early: times('early') + '×', takeoff: times('takeoff') + '×' }
    : { late: 'Keeps improving, ' + times('late') + '×', early: 'Stalls, ' + times('early') + '×', takeoff: 'AGI, ' + times('takeoff') + '×' };
  const ends = [];
  ['early', 'late', 'takeoff'].forEach(k => {
    const on = sel === k, pts = USE[k].map((v, i) => [X(2026.9 + i), Y(v / USE[k][0])]);
    s += `<path d="${line(pts)}" fill="none" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 4 : 2.5}"/>`;
    s += `<circle cx="${pts[4][0]}" cy="${pts[4][1]}" r="${on ? 5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}"/>`;
    ends.push([k, pts[4][1], on]);
  });
  ends.sort((a, b) => a[1] - b[1]); for (let i = 1; i < ends.length; i++) if (ends[i][1] - ends[i - 1][1] < 18) ends[i][1] = ends[i - 1][1] + 18;
  ends.forEach(([k, y, on]) => s += `<text x="${W - R + (ph ? 8 : 12)}" y="${y + 4}" class="big ${on ? 'ink' : ''}">${N[k]}</text>`);
  return `<h4>How much AI gets used, against 2026</h4><svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="AI use against its 2026 level: Google grew ${growth} times in two years; the paths to 2030 reach ${times('early')}, ${times('late')} or ${times('takeoff')} times">${s}</svg>
    <p class="say">Today Google alone handles about ${H.pages_per_person} pages of text a day for every person online.</p>
    <p class="src">Google, all surfaces (I/O 2026), against its May 2026 level. Paths: AI - Compute model, all Western AI, against 2026.</p>`;
}

// ---------- 2. Data centres: one quantity, a year's spending, ranked ----------
function chart2(sel, ph) {
  const NAME = { 'US military spending': 'US military', 'Global grid investment': 'World grid investment', 'Global telecom operator capex': 'World telecom' };
  const cap = H.capex[H.capex.length - 1], earlier = H.capex.slice(0, -1).map(([y, v]) => `${y} $${v}bn`).join(' · ');
  const rows = H.comps.map(([n, v, y]) => [`${NAME[n] || n}, ${y}`, v, 'c'])
    .concat([[`Big Four building data centres, ${cap[0]}`, cap[1], 'h', earlier],
      ["AI labs' computing in 2030: piling in", Math.round(SPEND.yes[4]), 'a', '', 'yes'],
      ["AI labs' computing in 2030: in between", Math.round(SPEND.mid[4]), 'a', '', 'mid'],
      ["AI labs' computing in 2030: money stops", Math.round(SPEND.no[4]), 'a', '', 'no'],
      [`AI labs' computing today, ${cap[0]}`, SPEND.yes[0], 'h']]).sort((a, b) => b[1] - a[1]);
  const W = ph ? 328 : 860, LW = ph ? 0 : 330, BW = W - LW - 70, RH = ph ? 46 : 32, top = 1000;
  let s = '', y = 0;
  rows.forEach(([n, v, kind, sub, k]) => {
    const on = kind === 'a' && k === sel, fill = kind === 'a' ? (on ? 'var(--ink)' : 'var(--line)') : 'var(--rule)';
    const ty = ph ? y + 13 : y + 15, by = ph ? y + 19 : y + 4, bh = ph ? 14 : 18;
    s += `<text x="${ph ? 0 : LW - 12}" y="${ty}" text-anchor="${ph ? 'start' : 'end'}" class="${on ? 'ink' : ''}" style="${kind === 'a' && !on ? 'fill:var(--ink)' : ''}">${n}</text>`;
    s += `<rect x="${LW}" y="${by}" width="${v / top * BW}" height="${bh}" fill="${fill}"/><text x="${LW + v / top * BW + 8}" y="${by + bh - 3}" class="${on ? 'ink' : ''}">$${v}bn</text>`;
    if (sub && !ph) s += `<text x="${LW + v / top * BW + 80}" y="${by + bh - 3}" class="small">${sub}</text>`;
    y += RH;
  });
  const mil = H.comps.find(c => /military/.test(c[0])), P = H.power;
  return `<h4>A year's spending, $bn</h4><svg viewBox="0 0 ${W} ${y}" role="img" aria-label="A year's spending, ranked: ${rows.map(r => r[0] + ' $' + r[1] + 'bn').join(', ')}">${s}</svg>
    <p class="say">The Big Four are already spending ${frac(cap[1] / mil[1])} of the US military budget on data centres this year, and US AI data centres draw about ${frac(P.us_ai_gw / P.comp_gw)} of Germany's average electricity.</p>
    <p class="src">SIPRI, IEA, Omdia; Big Four from company filings (${cap[0]} is guidance); labs from the AI - Compute model. Power: ${P.us_ai_gw} GW at the plug against Germany's ${Math.round(P.comp_gw)} GW (SMARD).</p>`;
}

// ---------- 3. Who gets paid: one $100, the answers are the chart ----------
const LAY = [['labs', 'AI labs', 'var(--soft)'], ['cloud_chip', 'Cloud and chips', 'var(--line)'], ['specialists', 'Specialist firms', 'var(--rule)'], ['bundles', 'Microsoft and Google bundles', 'hatch']];
const fillOf = (c, n) => c === 'hatch' ? `repeating-linear-gradient(135deg, var(--soft) 0 1px, var(--paper) 1px ${n}px)` : c;
const split = (sh, h) => `<span class="split" style="height:${h || 16}px">${LAY.map(([k, , c]) => sh[k] > 0 ? `<s style="width:${sh[k]}%;background:${fillOf(c, 5)}"></s>` : '').join('')}</span>`;
function chart3() {
  const key = `<div class="key">${LAY.map(([, n, c]) => `<span><em style="background:${fillOf(c, 4)}"></em>${n}</span>`).join('')}</div>`;
  return `<h4>Every $100 a company spends on AI goes to</h4>${key}<div class="today"><span>Today</span><i>$${Math.round(H.ai.today.labs)} to labs</i>${split(H.ai.today, 12)}</div>`;
}
function after3() {
  const keep = Object.entries(H.work).filter(([k]) => k !== 'today').map(([, w]) => w.buyers_keep);
  return `<p class="say">Whichever answer you pick, the company keeps $${Math.round(Math.min(...keep))} to $${Math.round(Math.max(...keep))} of every $100 of the lawyer's time. AI is cheap next to the work it does.</p>
    <p class="src">AI - Compute model estimate; the split among sellers has no history.</p>`;
}

// ---------- 4. Anthropic vs rivals: one basis, the answers' own ----------
function chart4(sel, ph) {
  const W = ph ? 328 : 860, Ht = ph ? 240 : 280, L = 44, R = ph ? 104 : 220, T = 14, B = 28;
  const X = x => L + (x - 2026) / 4 * (W - L - R), Y = v => T + (Ht - T - B) * (1 - (v - 25) / 40);
  let s = '';
  [30, 40, 50, 60].forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${v}%</text>`);
  [2026, 2028, 2030].forEach(y => s += `<text x="${X(y)}" y="${Ht - 6}" text-anchor="middle">${y}</text>`);
  s += `<circle cx="${X(2026)}" cy="${Y(TODAY_SHARE)}" r="5" fill="var(--soft)"/>${ph ? '' : `<text x="${X(2026)}" y="${Y(TODAY_SHARE) + 24}" class="big" style="fill:var(--ink)">${TODAY_SHARE}% today</text>`}`;
  const N = { 55: 'Pulls ahead, 55%', 45: 'Holds its own, 45%', 35: 'Others catch up, 35%' };
  ['35', '45', '55'].forEach(k => {
    const on = sel === k;
    s += `<line x1="${X(2026)}" x2="${X(2030)}" y1="${Y(TODAY_SHARE)}" y2="${Y(+k)}" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 4 : 2.5}"/><circle cx="${X(2030)}" cy="${Y(+k)}" r="${on ? 5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}"/>`;
    s += `<text x="${X(2030) + 10}" y="${Y(+k) + 4}" class="big ${on ? 'ink' : ''}">${ph ? k + '%' : N[k]}</text>`;
  });
  return `<h4>Anthropic's share of what companies pay the AI labs</h4><svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Anthropic's share of AI lab revenue, ${TODAY_SHARE}% today, to 35, 45 or 55% in 2030">${s}</svg>
    <p class="say">${ph ? `Anthropic has about ${TODAY_SHARE}% today. ` : ''}OpenAI, Google and the rest share whatever Anthropic does not win.</p>
    <p class="src">AI - Compute model: Anthropic's Q3 2026 revenue against the lab market's run-rate.</p>`;
}
const CHARTS = [chart1, chart2, chart3, chart4];

// ---------- a question screen ----------
function ask() {
  const q = Q[step], sel = A[q.k], ph = phone();
  $('prog').innerHTML = `The Anthropic IPO &nbsp;·&nbsp; ${step + 1} of 4 <i>${Q.map((_, j) => `<b class="${j <= step ? 'on' : ''}"></b>`).join('')}</i>`;
  $('qt').textContent = q.t;
  $('qchart').innerHTML = CHARTS[step](sel, ph);
  $('opts').className = 'opts' + (q.o.length === 3 ? ' three' : '');
  $('opts').innerHTML = q.o.map(([v, l, d]) => `<button type="button" aria-pressed="${sel === v}" data-v="${v}"><b>${esc(l)}</b><i>${FIG[q.k](v)}</i><span>${esc(d)}</span>${q.k === 'world' ? split(H.ai[v]) : ''}</button>`).join('');
  $('after3').innerHTML = q.k === 'world' ? after3() : '';
  $('back').hidden = !step || editing;
  $('next').hidden = !sel; $('hint').hidden = !!sel;
  $('next').innerHTML = editing ? 'Back to your price &rarr;' : step < Q.length - 1 ? 'Next question &rarr;' : 'See the price &rarr;';
}
function show(onReveal) {
  $('ask').hidden = onReveal; $('panel').hidden = !onReveal; $('after').hidden = !onReveal;
}
$('opts').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  A[Q[step].k] = b.dataset.v; ask();
});
$('next').addEventListener('click', () => {
  if (!A[Q[step].k]) return;
  if (editing || step === Q.length - 1) { editing = false; reveal(); } else { step++; ask(); window.scrollTo(0, 0); }
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
