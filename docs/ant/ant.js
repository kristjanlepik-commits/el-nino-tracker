// /ant, the four-question widget. Flow and charts from concept v3 (Mycelium
// UX, 12 Nov); every price comes from values.js (window.ANT), the file
// /ant-pro reads too.
(function () {
const IPO = ANT.IPO, YRS = [2026, 2027, 2028, 2029, 2030];
// Chart data, all from model v4.1 (scenarios_v41.py), as in concept v3:
// AI use: western tokens a day, 400tn in 2026, grown by SPEEDS[*].tokens.
const USE = { late: [400, 1000, 2000, 3200, 5120], early: [400, 640, 832, 998, 1148], takeoff: [400, 1120, 2912, 6698, 14065] };
// Lab compute spend, $bn: LAB_PLAN; a break cuts it 40% from 2028 (BREAK_COMMIT_HAIRCUT); "in between" is the average.
const SPEND = { yes: [156, 220, 275, 335, 395], no: [156, 220, 165, 201, 237] };
SPEND.mid = SPEND.yes.map((v, i) => (v + SPEND.no[i]) / 2);
// Share of AI use served by the frontier labs in 2030: WORLDS[*].seg.lab.
const LABSHARE = { C1: 50, C4: 65, C3: 32, C5: 25, C2: 22 };

// The one number each option's chart would light (VD design pass): on a phone
// the chart sits below the options and never lights, so the option carries it.
const FIG = {
  use: v => Math.round(USE[v][4] / USE[v][0]) + '× today',
  spend: v => '$' + Math.round(SPEND[v][4]) + 'bn',
  who: v => '$' + Math.round(window.ANT_HISTORY.ai[v].labs),
  share: v => v + '%',
};

const Q = [
  { k: 'speed', t: 'Which statement is closest to what you think will happen with AI by 2030?', s: 'AI by 2030', o: [
    ['late', 'It keeps improving, but more slowly', 'Like phones after the first iPhones: better every year, less of a leap', 'Keeps improving|13× today'],
    ['early', 'It stalls soon', 'Putting AI into every business turns out to be hard', 'Stalls soon|3× today'],
    ['takeoff', 'Something like AGI arrives', 'Progress speeds up, and AI does more of the work itself', 'AGI arrives|35× today']],
    chart: 'use' },
  { k: 'money', t: 'What is your view on data centres?', s: 'Data centres', o: [
    ['yes', 'Investors keep piling money in', 'Spending on new data centres keeps climbing', 'Money keeps flowing|'],
    ['mid', 'Something in between', 'A wobble: a funding crash is as likely as not', 'In between|'],
    ['no', 'The money stops', 'A funding crash in 2027-29 halts the build-out for a few years', 'Money stops|']],
    chart: 'spend' },
  { k: 'world', t: 'In 2030, a lawyer at your company uses AI to check a contract. Who gets paid?', s: 'Who gets paid', o: [
    ['C4', 'The labs, end to end', 'Anthropic or OpenAI sell a finished legal AI that does the review, and own the customer', 'The labs, end to end'],
    ['C1', 'The labs, as a tool', 'The company buys Claude or ChatGPT by the use, and the lawyer does the work', 'The labs, as a tool'],
    ['C3', 'A specialist AI firm', 'A legal AI company owns the client, often on its own models', 'A specialist AI firm'],
    ['C5', 'Microsoft or Google', 'It is a button in Word or Gmail, already in the bill', 'Microsoft or Google'],
    ['C2', 'Nobody much', 'Free models are just as good, so AI is cheap like spellcheck', 'Nobody much']],
    chart: 'who' },
  { k: 'share', t: 'Anthropic, OpenAI, Google: who is winning?', s: 'Anthropic vs rivals', o: [
    ['55', 'Anthropic pulls ahead', 'More companies choose Claude than today', '55%'],
    ['45', 'Anthropic holds its own', 'It keeps the 45% it has today', '45%'],
    ['35', 'The others catch up', 'OpenAI, Google and others win back customers', '35%']],
    chart: 'share' },
];
const A = {}; let step = 0, done = false;
const $ = id => document.getElementById(id);
const price = a => ANT.price(a);

// ---------- question charts (VD, "Ant Questions, charts with history", D-375) ----------
// One central chart per question: real history up to today, then the
// answers' paths to 2030. The reader's pick, or the option under the pointer,
// is the one ink path; tap any point to read it. History is history.js
// (AI - Compute, verified points only); the paths are the model's, above.
const H = window.ANT_HISTORY;
const SNAME = { late: 'Keeps improving', early: 'Stalls soon', takeoff: 'AGI arrives', yes: 'Money keeps flowing', mid: 'In between', no: 'Money stops' };
const t2x = s => { const [y, m] = String(s).split('-').map(Number); return y + ((m || 12) - 0.5) / 12; };
const path = pts => pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
const nice = v => v >= 1 ? v.toLocaleString() : String(v);

function chart1(sel, ph) {
  const W = ph ? 340 : 560, Ht = 300, L = ph ? 40 : 46, R = ph ? 104 : 132, T = 14, B = 30, x0 = 2024.2, x1 = 2030.9;
  const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = v => T + (Ht - T - B) * (1 - (Math.log10(v) + 1) / 6);
  let s = '';
  [0.1, 1, 10, 100, 1000, 10000].forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${nice(v)}</text>`);
  [2024, 2026, 2028, 2030].forEach(y => s += `<text x="${X(y + 0.5)}" y="${Ht - 8}" text-anchor="middle">${y}</text>`);
  const today = t2x('2026-11');
  s += `<line x1="${X(today)}" x2="${X(today)}" y1="${T}" y2="${Ht - B}" stroke="var(--soft)"/><text x="${X(today) - 5}" y="${T + 10}" text-anchor="end">today</text>`;
  s += `<text x="${L}" y="${T - 6}">trillion a day; each line up is ×10</text>`;
  const g = H.google.map(([d, v]) => [X(t2x(d)), Y(v), d, v]);
  s += `<path d="${path(g)}" fill="none" stroke="var(--soft)" stroke-width="2.5"/>`;
  g.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="var(--soft)" data-r="${H.google_src}, ${p[2]}: ${p[3]} trillion a day"/>`);
  s += `<text x="${g[1][0] + 8}" y="${g[1][1] + 14}" style="fill:var(--soft)">Google alone</text>`;
  const ends = [];
  ['early', 'late', 'takeoff'].forEach(k => {
    const on = sel === k, pts = USE[k].map((v, i) => [X(2026.92 + i), Y(v), 2026 + i, v]);
    s += `<path d="${path(pts)}" fill="none" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 3 : 2}" stroke-dasharray="${on ? '' : '5 4'}"/>`;
    pts.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="${on ? 4.5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}" data-r="Model, all Western AI, ${SNAME[k]}, end ${p[2]}: ${p[3].toLocaleString()} trillion a day"/>`);
    ends.push([k, pts[4][1], on]);
  });
  ends.sort((a, b) => a[1] - b[1]); for (let i = 1; i < ends.length; i++) if (ends[i][1] - ends[i - 1][1] < 18) ends[i][1] = ends[i - 1][1] + 18;
  ends.forEach(([k, y, on]) => s += `<text x="${W - R + 8}" y="${y + 4}" class="${on ? 'ink' : ''}">${SNAME[k]}</text>`);
  s += `<text x="${X(2027.2)}" y="${Y(250)}" style="fill:var(--soft)">all Western AI, model</text>`;
  return { svg: `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="AI tokens a day on a log scale: Google's history from 2024 and the model's three paths to 2030">${s}</svg>`,
    head: 'AI used every day, 2024 to 2030',
    src: 'History: Google, all surfaces (I/O 2026). Paths: AI - Compute model, all Western AI from about 400 trillion a day today.',
    human: `Google alone now processes about <b>${H.pages_per_person} pages of text a day for every person online</b>.` };
}
function chart2(sel, ph) {
  const W = ph ? 340 : 560, Ht = 300, L = 40, R = ph ? 96 : 112, T = 14, B = 30, x0 = 2023.7, x1 = 2030.3;
  const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = v => T + (Ht - T - B) * (1 - v / 1000);
  let s = '';
  [0, 250, 500, 750, 1000].forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`);
  [2024, 2026, 2028, 2030].forEach(y => s += `<text x="${X(y)}" y="${Ht - 8}" text-anchor="middle">${y}</text>`);
  s += `<text x="${L}" y="${T - 6}">$bn a year</text>`;
  H.comps.forEach(([n, v, y]) => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--soft)" stroke-dasharray="2 3"/><text x="${W - R + 6}" y="${Y(v) - 2}">${n.replace('spending', '').replace('Global ', 'World ').replace(' operator capex', '').replace(' investment', '').trim()}</text><text x="${W - R + 6}" y="${Y(v) + 11}">$${v}bn, ${y}</text>`);
  const c = H.capex.map(([y, v, kind]) => [X(y), Y(v), y, v, kind]);
  s += `<path d="${path(c)}" fill="none" stroke="var(--soft)" stroke-width="2.5"/>`;
  c.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="var(--soft)" data-r="Big four tech firms, all data-centre building, ${p[2]}${p[4] ? ' (' + p[4] + ')' : ''}: $${p[3]}bn"/>`);
  s += `<text x="${c[2][0] + 8}" y="${c[2][1] + 4}" style="fill:var(--soft)">Big four, all building</text>`;
  ['no', 'mid', 'yes'].forEach(k => {
    const on = sel === k, pts = SPEND[k].map((v, i) => [X(2026 + i), Y(v), 2026 + i, v]);
    s += `<path d="${path(pts)}" fill="none" stroke="${on ? 'var(--ink)' : 'var(--line)'}" stroke-width="${on ? 3 : 2}" stroke-dasharray="${on ? '' : '5 4'}"/>`;
    pts.forEach(p => s += `<circle cx="${p[0]}" cy="${p[1]}" r="${on ? 4.5 : 3.5}" fill="${on ? 'var(--ink)' : 'var(--line)'}" data-r="Model, AI labs' compute spend, ${SNAME[k]}, ${p[2]}: $${Math.round(p[3])}bn"/>`);
    if (on && !ph) s += `<text x="${pts[4][0] - 4}" y="${pts[4][1] - 10}" text-anchor="end" class="ink">${SNAME[k]}, $${Math.round(pts[4][3])}bn</text>`;
  });
  s += `<text x="${X(2026.2)}" y="${Y(120)}" style="fill:var(--soft)">Labs' compute, model</text>`;
  const P = H.power, bw = 340, us = P.us_ai_gw / P.comp_gw * bw;
  const pw = `<svg viewBox="0 0 ${bw + 50} 56" role="img" aria-label="US AI data centres at about ${P.us_ai_gw} gigawatts against ${P.comp_name} of ${P.comp_gw} gigawatts" class="power">
    <text x="0" y="12">US AI data centres, end 2026</text><rect x="0" y="16" width="${us}" height="9" fill="var(--ink)"/><text x="${us + 6}" y="25">${P.us_ai_gw} GW</text>
    <text x="0" y="40">${P.comp_name.replace(', average electricity load', ', average electricity use')}</text><rect x="0" y="44" width="${bw}" height="9" fill="var(--line)"/><text x="${bw + 6}" y="53">${Math.round(P.comp_gw)} GW</text></svg>`;
  return { svg: `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Spending on AI computing in billions of dollars a year, 2024 to 2030, against US military, grid and telecom spending">${s}</svg>${pw}`,
    head: 'Money spent on AI computing, 2024 to 2030',
    src: 'History: big four capex from company filings (2026 is guidance). Paths: AI - Compute model. Comparators: SIPRI, IEA, Omdia.' };
}
const LAYERS = [['labs', 'AI labs'], ['cloud_chip', 'Cloud and chips'], ['specialists', 'Specialist firms'], ['bundles', 'Microsoft and Google bundles']];
function chart3(sel, ph) {
  const key = sel || 'today', W = ph ? 340 : 560, w = H.work[key], a = H.ai[key], BW = W - 20, X0 = 10, kept = w.buyers_keep;
  const when = sel ? 'in 2030' : 'today';
  let s = `<text x="${X0}" y="12">$100 of a lawyer's work, done by AI ${when}</text>`;
  s += `<rect x="${X0}" y="20" width="${kept / 100 * BW}" height="26" fill="var(--sunk)"/><text x="${X0 + 8}" y="38" style="fill:var(--ink)">Company keeps $${kept.toFixed(0)}</text>`;
  s += `<rect x="${X0 + kept / 100 * BW}" y="20" width="${(100 - kept) / 100 * BW}" height="26" fill="var(--soft)"/><text x="${X0 + BW}" y="62" text-anchor="end">$${(100 - kept).toFixed(0)} spent on AI</text>`;
  s += `<text x="${X0}" y="90">Every $100 spent on AI goes to</text>`;
  let x = X0; const y = 98, h = 28, fill = { labs: 'var(--ink)', cloud_chip: 'var(--line)', specialists: 'var(--rule)', bundles: 'var(--sunk)' };
  const tx = X0 + H.ai.today.labs / 100 * BW;
  let ly = y + h + 24, legend = '';
  LAYERS.forEach(([k, n]) => {
    const v = a[k]; if (v <= 0) return; const ww = v / 100 * BW;
    s += `<rect x="${x}" y="${y}" width="${Math.max(ww - 2, 1)}" height="${h}" fill="${fill[k]}" data-r="${n}: $${v.toFixed(0)} of every $100 spent on AI ${when} (model estimate)"/>`;
    legend += `<rect x="${X0}" y="${ly - 9}" width="10" height="10" fill="${fill[k]}" stroke="var(--rule)"/><text x="${X0 + 16}" y="${ly}" class="${k === 'labs' ? 'ink' : ''}">${n}, $${v.toFixed(0)}${k === 'labs' && sel ? ' (today $' + Math.round(H.ai.today.labs) + ')' : ''}</text>`;
    ly += 18; x += ww;
  });
  if (sel) s += `<line x1="${tx}" x2="${tx}" y1="${y - 4}" y2="${y + h + 4}" stroke="var(--paper)" stroke-width="3"/><line x1="${tx}" x2="${tx}" y1="${y - 4}" y2="${y + h + 4}" stroke="var(--soft)" stroke-width="1.5" stroke-dasharray="3 2"/>`;
  s += legend;
  return { svg: `<svg viewBox="0 0 ${W} ${ly}" role="img" aria-label="Of $100 of a lawyer's work done by AI, how much the company keeps, and how each $100 spent on AI splits among labs, cloud and chips, specialists and bundles">${s}</svg>`,
    head: `Who gets paid, ${sel ? '2030' : 'today'} <span class="tag">model estimate</span>`,
    src: 'AI - Compute model: AI priced at a small share of the wage it replaces. The split among sellers is the model\'s judgement; there is no history for it.' + (sel ? ' The dashed tick is the labs\' share today.' : ' Pick an answer to see 2030.') };
}
function chart4(sel, ph) {
  const W = 260, Ht = 220, T = 18, B = 30, Y = v => T + (Ht - T - B) * (1 - v / 70);
  let s = `<text x="0" y="10">US enterprise API spend, %</text>`;
  [0, 20, 40, 60].forEach(v => s += `<line x1="30" x2="${W - 70}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--rule)"/><text x="24" y="${Y(v) + 4}" text-anchor="end">${v}</text>`);
  const xa = 40, xb = W - 80, lab = d => /-/.test(d) ? 'Sep ' + d.slice(0, 4) : d;
  const firm = Object.values(H.share)[0];
  s += `<text x="${xa}" y="${Ht - 8}" text-anchor="middle">${lab(firm[0][0])}</text><text x="${xb}" y="${Ht - 8}" text-anchor="middle">${lab(firm[firm.length - 1][0])}</text>`;
  Object.entries(H.share).forEach(([n, pts]) => {
    const an = n === 'Anthropic', a = pts[0][1], b = pts[pts.length - 1][1], col = an ? 'var(--soft)' : 'var(--line)';
    s += `<line x1="${xa}" x2="${xb}" y1="${Y(a)}" y2="${Y(b)}" stroke="${col}" stroke-width="${an ? 2.5 : 2}"/>`;
    s += `<circle cx="${xa}" cy="${Y(a)}" r="4" fill="${col}" data-r="${n}, ${lab(pts[0][0])}: ${a}% (Menlo Ventures)"/><circle cx="${xb}" cy="${Y(b)}" r="4" fill="${col}" data-r="${n}, ${lab(pts[pts.length - 1][0])}: ${b}% (Menlo Ventures)"/>`;
    s += `<text x="${xb + 8}" y="${Y(b) + 4}" style="${an ? 'fill:var(--ink)' : ''}">${n} ${b}</text>`;
  });
  const left = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Enterprise API spend shares by firm, Menlo Ventures survey">${s}</svg>`;
  const W2 = 300, H2 = 220, Y2 = v => T + (H2 - T - B) * (1 - v / 70);
  let r = `<text x="0" y="10">Share of all lab revenue in 2030, %</text>`;
  [0, 20, 40, 60].forEach(v => r += `<line x1="30" x2="${W2}" y1="${Y2(v)}" y2="${Y2(v)}" stroke="var(--rule)"/><text x="24" y="${Y2(v) + 4}" text-anchor="end">${v}</text>`);
  [['35', 'Catch up'], ['45', 'Holds'], ['55', 'Ahead']].forEach(([k, n], i) => {
    const on = sel === k, x = 50 + i * 70, v = +k;
    r += `<rect x="${x}" y="${Y2(v)}" width="44" height="${Y2(0) - Y2(v)}" fill="${on ? 'var(--ink)' : 'var(--line)'}" data-r="Anthropic in 2030, ${n}: ${v}% of all frontier-lab revenue (model)"/><text x="${x + 22}" y="${Y2(v) - 6}" text-anchor="middle" class="${on ? 'ink' : ''}">${v}</text><text x="${x + 22}" y="${H2 - 8}" text-anchor="middle">${n}</text>`;
  });
  r += `<line x1="30" x2="${W2}" y1="${Y2(45)}" y2="${Y2(45)}" stroke="var(--soft)" stroke-dasharray="3 3"/><text x="${W2}" y="${Y2(45) - 4}" text-anchor="end">today 45</text>`;
  const right = `<svg viewBox="0 0 ${W2} ${H2}" role="img" aria-label="Anthropic's share of all frontier-lab revenue in 2030 under each answer: 35, 45 or 55 per cent">${r}</svg>`;
  return { svg: `<div class="two"><div>${left}</div><div>${right}</div></div>`,
    head: 'Where Anthropic stands, and where it could be',
    src: 'Left: Menlo Ventures enterprise survey, verified points only. Right: AI - Compute model, a wider base than enterprise API spend.' };
}
const CHARTS = { use: chart1, spend: chart2, who: chart3, share: chart4 };
function draw(sel) {
  const q = Q[step], ph = window.matchMedia && matchMedia('(max-width: 720px)').matches, c = CHARTS[q.chart](sel || null, ph);
  $('qchart').innerHTML = `<h3>${c.head}</h3>${c.svg}<p class="readout" aria-live="polite">Tap a point to read it.</p><p class="src">${c.src}</p>${c.human ? `<p class="human">${c.human}</p>` : ''}`;
  const ro = $('qchart').querySelector('.readout');
  $('qchart').querySelectorAll('[data-r]').forEach(el => { const f = () => ro.textContent = el.getAttribute('data-r'); el.addEventListener('mouseenter', f); el.addEventListener('click', f); });
  document.querySelectorAll('#opts button').forEach(b => b.classList.toggle('hl', b.dataset.v === sel));
}

// ---------- flow ----------
// A tap picks an answer and lights its path; Next moves on, so a phone
// reader sees the chart answer back before leaving the question (D-375).
function ask() {
  const q = Q[step];
  $('qt').textContent = q.t;
  $('opts').innerHTML = q.o.map(([v, l, d]) => `<button type="button" data-v="${v}" aria-pressed="${A[q.k] === v}"><span class="t"><b>${l}</b><i class="fig">${FIG[q.chart](v)}</i></span><span class="d">${d}</span></button>`).join('');
  $('back').style.visibility = step ? 'visible' : 'hidden';
  $('next').disabled = !A[q.k];
  $('next').innerHTML = step < Q.length - 1 ? 'Next question &rarr;' : 'See the price &rarr;';
  draw(A[q.k]);
  panel();
}
let first = true;
function reveal() {
  done = true; $('ask').hidden = true; $('after').hidden = false; panel();
  const p = $('panel');
  if (p.getBoundingClientRect().top < 0) {
    const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    p.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' });
  }
}
const opts = $('opts');
opts.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  A[Q[step].k] = b.dataset.v;
  opts.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
  $('next').disabled = false; draw(b.dataset.v); panel();
});
opts.addEventListener('mouseover', e => { const b = e.target.closest('button'); if (b) draw(b.dataset.v); });
opts.addEventListener('focusin', e => { const b = e.target.closest('button'); if (b) draw(b.dataset.v); });
opts.addEventListener('mouseleave', () => draw(A[Q[step].k]));
$('next').addEventListener('click', () => { if (!A[Q[step].k]) return; if (step < Q.length - 1) { step++; ask(); } else reveal(); });
$('back').addEventListener('click', () => { step = Math.max(0, step - 1); ask(); });
$('mine').addEventListener('change', e => { A[e.target.dataset.k] = e.target.value; panel(); });

// ---------- valuation panel ----------
function answers() { return Q.map(q => A[q.k]).join(','); }
function panel() {
  const n = Object.keys(A).length;
  $('panel').classList.toggle('waiting', !done);
  const head = $('head');
  if (!done) {
    head.innerHTML = `<p class="kick">What is an Anthropic share worth?</p><div class="v" style="color:var(--faint)">$ ?</div><div class="wait">Answer 4 questions to see the valuation of Anthropic.<div class="prog">${Q.map((_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</div></div>`;
  } else {
    const v = price(A), fails = v <= 0, d = v / IPO - 1;
    head.innerHTML = `<p class="kick">On your view of AI, Anthropic is worth</p><div class="v">${fails ? '$0' : '$' + Math.round(v) + '<small> a share</small>'}</div>` +
      `<p class="vs">${fails ? 'Its debts and compute contracts outweigh the business. <b>Shareholders get nothing.</b>' : `That is <b>${Math.abs(Math.round(d * 100))}% ${d >= 0 ? 'above' : 'below'}</b> the $${IPO} IPO price.`}</p>`;
    // The address bar carries the answers, so a reader can share their own number.
    try { history.replaceState(null, '', '?a=' + answers()); } catch (e) {}
    $('more').href = '../ant-pro/?a=' + answers();
    // In the one-file prototype both pages share a document: hand the answers across in place.
    // The bar's version switch carries the answers too (VD, "two versions").
    const sw = document.querySelector('.sw a[data-to="pro"]');
    if (sw) sw.href = '../ant-pro/?a=' + answers();
    if (window.ANT_PROTO) [$('more'), sw].forEach(a => a && (a.onclick = e => { e.preventDefault(); ANT_PROTO.toPro(answers()); }));
    $('mine').innerHTML = Q.map(q => `<div class="row"><label for="s-${q.k}">${q.s}</label><select id="s-${q.k}" data-k="${q.k}">` +
      q.o.map(([v, l]) => `<option value="${v}"${A[q.k] === v ? ' selected' : ''}>${l}</option>`).join('') + `</select></div>`).join('');
  }
  strip();
}
function strip() {
  if (!done) { ANTSCALE($('strip'), { price: null }); $('cap').textContent = ''; return; }
  // The two counts the dot strip used to show stay, in words: every way of
  // answering the first three questions, at the reader's own answer to the fourth.
  let zero = 0, above = 0, total = 0;
  for (const sp of ['late', 'early', 'takeoff']) for (const m of ['yes', 'mid', 'no']) for (const w of ['C1', 'C2', 'C3', 'C4', 'C5']) {
    const x = price({ speed: sp, money: m, world: w, share: A.share }); total++;
    if (x <= 0) zero++; else if (x >= IPO) above++;
  }
  ANTSCALE($('strip'), { price: price(A), animate: first });
  first = false;
  $('cap').textContent = `${zero} of ${total} ways to answer leave shareholders with nothing; ${above} ${above === 1 ? 'beats' : 'beat'} the IPO price.`;
}

// ?a=late,mid,C1,45 opens on the reveal; ?step=2 opens on question 3 (screenshots)
const qs = new URLSearchParams(location.search), pre = qs.get('a');
const ok = (q, v) => q.o.some(o => o[0] === v);
if (pre && pre.split(',').length === 4 && pre.split(',').every((v, i) => ok(Q[i], v))) {
  pre.split(',').forEach((v, i) => A[Q[i].k] = v); reveal();
} else { step = Math.min(3, +(qs.get('step') || 0)); Q.slice(0, step).forEach(q => A[q.k] = q.o[0][0]); ask(); if (qs.get('hl')) draw(qs.get('hl')); }
})();
