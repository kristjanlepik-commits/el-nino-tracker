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
  who: v => LABSHARE[v] + ' of 100',
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

// ---------- question charts ----------
function lines(title, data, opts, fmtEnd, src) {
  const W = 340, H = 190, L = 4, R = 134, T = 10, B = 24;
  const max = Math.max(...Object.values(data).flat());
  const X = i => L + i * (W - L - R) / 4, Y = v => T + (H - T - B) * (1 - v / max);
  let s = `<line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}" stroke="var(--rule)"/>`;
  [0, 4].forEach(i => s += `<text x="${X(i)}" y="${H - 6}" text-anchor="${i ? 'end' : 'start'}">${YRS[i]}</text>`);
  // end labels, nudged apart so they never collide
  const ends = opts.map(o => ({ v: o[0], y: Y(data[o[0]][4]) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 30) ends[i].y = ends[i - 1].y + 30;
  opts.forEach(o => {
    const d = data[o[0]].map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
    const ly = ends.find(e => e.v === o[0]).y;
    s += `<g class="s" data-v="${o[0]}"><path d="${d}" fill="none" stroke="var(--line)" stroke-width="2.5"/>` +
      `<text x="${X(4) + 8}" y="${ly + 4}">${o[3].split('|')[0]}</text><text x="${X(4) + 8}" y="${ly + 18}">${o[3].split('|')[1] || fmtEnd(data[o[0]][4])}</text></g>`;
  });
  return `<h3>${title}</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${title}">${s}</svg><p class="src">${src}</p>`;
}
function bars(title, rows, unit, src) {
  const W = 340, rowH = 30, L = 160, R = 34, H = rows.length * rowH + 4;
  const X = v => L + v / 100 * (W - L - R);
  let s = '';
  rows.forEach(([v, label, val], i) => {
    const y = i * rowH + 4;
    s += `<g class="s" data-v="${v}"><text x="${L - 8}" y="${y + 15}" text-anchor="end">${label}</text>` +
      `<rect x="${L}" y="${y + 3}" width="${X(val) - L}" height="16" fill="var(--line)"/>` +
      `<text x="${X(val) + 6}" y="${y + 16}">${val}${unit}</text></g>`;
  });
  return `<h3>${title}</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${title}">${s}</svg><p class="src">${src}</p>`;
}
const CHARTS = {
  use: q => lines('How much AI gets used, 2026 to 2030', USE, q.o, () => '', 'AI work done each day, as a multiple of 2026. From the AI - Compute model.'),
  spend: q => lines('What AI labs spend on data centres a year', SPEND, q.o, v => '$' + Math.round(v) + 'bn in 2030', 'From the AI - Compute model. A halt cuts spending 40% from 2028.'),
  who: q => bars('Of every 100 AI tasks in 2030, how many go to labs like Anthropic', q.o.map(o => [o[0], o[3], LABSHARE[o[0]]]), '', 'From the AI - Compute model. The rest goes to Big Tech bundles, specialist software and AI run in-house.'),
  share: q => bars("Anthropic's share of what companies pay the AI labs in 2030", q.o.map(o => [o[0], o[1].replace('Anthropic ', '').replace(/^./, c => c.toUpperCase()), +o[0]]), '%', 'Today it is about 45%, on end-September 2026 revenue.'),
};
function focus(v) {
  const c = $('qchart');
  c.classList.toggle('focus', !!v);
  c.querySelectorAll('.s').forEach(g => g.classList.toggle('on', g.dataset.v === v));
  document.querySelectorAll('#opts button').forEach(b => b.classList.toggle('hl', b.dataset.v === v));
}

// ---------- flow ----------
function ask() {
  const q = Q[step];
  $('qt').textContent = q.t;
  $('opts').innerHTML = q.o.map(([v, l, d]) => `<button type="button" data-v="${v}" aria-pressed="${A[q.k] === v}"><span class="t"><b>${l}</b><i class="fig">${FIG[q.chart](v)}</i></span><span class="d">${d}</span></button>`).join('');
  $('qchart').innerHTML = CHARTS[q.chart](q);
  $('back').style.visibility = step ? 'visible' : 'hidden';
  focus(A[q.k]);
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
  if (step < Q.length - 1) { step++; ask(); } else reveal();
});
opts.addEventListener('mouseover', e => { const b = e.target.closest('button'); if (b) focus(b.dataset.v); });
opts.addEventListener('focusin', e => { const b = e.target.closest('button'); if (b) focus(b.dataset.v); });
opts.addEventListener('mouseleave', () => focus(A[Q[step].k]));
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
  $('cap').textContent = `${zero} of ${total} ways to answer leave shareholders with nothing; ${above} beat the IPO price.`;
}

// ?a=late,mid,C1,45 opens on the reveal; ?step=2 opens on question 3 (screenshots)
const qs = new URLSearchParams(location.search), pre = qs.get('a');
const ok = (q, v) => q.o.some(o => o[0] === v);
if (pre && pre.split(',').length === 4 && pre.split(',').every((v, i) => ok(Q[i], v))) {
  pre.split(',').forEach((v, i) => A[Q[i].k] = v); reveal();
} else { step = Math.min(3, +(qs.get('step') || 0)); Q.slice(0, step).forEach(q => A[q.k] = q.o[0][0]); ask(); if (qs.get('hl')) focus(qs.get('hl')); }
})();
