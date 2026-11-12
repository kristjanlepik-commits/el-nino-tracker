
// Anthropic's value per share comes from ../ant/values.js (window.ANT), the
// file /ant reads too, so the same answers give the same price on both pages.
// It adds a sixth path the explorer lacked, rapid takeoff with a funding
// crash, which /ant's "AGI arrives" + "the money stops" needs. Its default
// weight is 0, so the base case is unchanged.
STATES.push(['takeoff', true]); STATE_KEYS.push('takeoffBreak');
WEIGHTS.states.takeoffBreak = 0; WEIGHTS.mix.takeoffBreak = WEIGHTS.mix.takeoff.slice();
const JOBS = { // millions, [late, early, takeoff, lateBreak, earlyBreak, takeoffBreak], from explorer v14; takeoffBreak = takeoff x (lateBreak / late), an estimate
  C1: [2.73, 1.63, 4.68, 2.66, 1.71, 4.56], C2: [2.66, 1.53, 4.34, 2.58, 1.60, 4.21], C3: [3.31, 1.86, 5.47, 3.11, 1.81, 5.14], C4: [3.31, 1.86, 5.47, 3.11, 1.81, 5.14], C5: [2.62, 1.63, 4.68, 2.55, 1.71, 4.55],
};
// Frontier-lab revenue, $bn a year 2026-30, on the two paths the price rests
// on (explorer v14): low ties AI's work revenue to the jobs it replaces, high
// follows the labs' own plans. The usage-times-price revenue is retired.
const POOL = {"low": {"C1": {"late": [150, 189, 234, 284, 340], "lateBreak": [150, 176, 179, 208, 267], "early": [150, 168, 184, 198, 212], "earlyBreak": [150, 157, 141, 146, 168], "takeoff": [150, 193, 237, 286, 338], "takeoffBreak": [150, 185, 205, 230, 306]}, "C2": {"late": [150, 164, 174, 174, 162], "lateBreak": [150, 154, 135, 132, 132], "early": [150, 146, 136, 120, 98], "earlyBreak": [150, 137, 106, 91, 81], "takeoff": [150, 177, 198, 199, 184], "takeoffBreak": [150, 166, 156, 155, 156]}, "C3": {"late": [150, 180, 214, 248, 280], "lateBreak": [150, 169, 166, 185, 224], "early": [150, 160, 167, 171, 172], "earlyBreak": [150, 150, 130, 128, 139], "takeoff": [150, 189, 224, 255, 289], "takeoffBreak": [150, 179, 190, 206, 261]}, "C4": {"late": [150, 195, 249, 312, 384], "lateBreak": [150, 182, 190, 228, 301], "early": [150, 173, 195, 218, 240], "earlyBreak": [150, 162, 150, 160, 189], "takeoff": [150, 195, 247, 322, 404], "takeoffBreak": [150, 187, 217, 255, 358]}, "C5": {"late": [150, 167, 179, 184, 177], "lateBreak": [150, 156, 138, 135, 140], "early": [150, 148, 140, 128, 110], "earlyBreak": [150, 138, 108, 94, 88], "takeoff": [150, 173, 183, 178, 160], "takeoffBreak": [150, 165, 156, 140, 145]}}, "high": {"C1": {"late": [150, 237, 370, 566, 850], "lateBreak": [150, 222, 283, 414, 667], "early": [150, 211, 290, 395, 531], "earlyBreak": [150, 197, 223, 290, 419], "takeoff": [150, 243, 376, 568, 846], "takeoffBreak": [150, 233, 324, 457, 765]}, "C2": {"late": [150, 207, 275, 347, 406], "lateBreak": [150, 194, 214, 262, 329], "early": [150, 184, 214, 238, 246], "earlyBreak": [150, 172, 168, 181, 202], "takeoff": [150, 222, 314, 396, 459], "takeoffBreak": [150, 209, 247, 309, 390]}, "C3": {"late": [150, 227, 338, 493, 702], "lateBreak": [150, 212, 262, 368, 560], "early": [150, 201, 264, 340, 431], "earlyBreak": [150, 189, 205, 256, 348], "takeoff": [150, 237, 354, 508, 723], "takeoffBreak": [150, 225, 301, 409, 653]}, "C4": {"late": [150, 245, 393, 620, 961], "lateBreak": [150, 229, 301, 453, 753], "early": [150, 218, 309, 434, 601], "earlyBreak": [150, 203, 237, 318, 474], "takeoff": [150, 246, 390, 640, 1010], "takeoffBreak": [150, 235, 343, 508, 895]}, "C5": {"late": [150, 210, 283, 365, 443], "lateBreak": [150, 196, 218, 269, 350], "early": [150, 186, 222, 254, 276], "earlyBreak": [150, 174, 171, 188, 219], "takeoff": [150, 218, 290, 353, 401], "takeoffBreak": [150, 207, 247, 279, 362]}}};
const WNAMES = {
  C1: ['Labs sell AI by the use', 'Firms buy Claude, ChatGPT or Gemini as a service and keep their own clients'],
  C2: ['AI becomes a cheap commodity', 'Open models catch up; prices collapse and buyers keep the savings'],
  C3: ['Specialist AI firms win', 'Harvey-type firms in law, medicine and code own the client, often on their own models'],
  C4: ['Labs sell finished products', 'The labs own the model, the agents and the customer'],
  C5: ['Big tech bundles AI in', 'Google, Microsoft and Meta give AI away inside products people already pay for'],
};
const SNAMES = { late: 'AI keeps improving to about 2030', early: 'AI stalls in 2027-28', takeoff: 'AGI by about 2029', lateBreak: 'Keeps improving, funding crash 2027-29', earlyBreak: 'Stalls, plus a funding crash', takeoffBreak: 'AGI, plus a funding crash' };
const SSHORT = { late: 'Keeps improving', early: 'Stalls early', takeoff: 'AGI', lateBreak: 'Improving + crash', earlyBreak: 'Stalls + crash', takeoffBreak: 'AGI + crash' };
const clone = o => JSON.parse(JSON.stringify(o));
let P = clone(DEFAULTS), W = clone(WEIGHTS), share = 45, sel = { world: 'C1', key: 'late' };

const valAt = (world, si, sh) => ANT.cell(world, si, sh);
const valOf = (w, si) => valAt(w, si, share);

// ---- controls ----
const controls = [];
function slider(parent, { id, label, min, max, step, read, write, fmt }) {
  const d = document.createElement('div'); d.className = 'ctl';
  d.innerHTML = `<label for="${id}">${label}</label><output id="${id}-o"></output><input type="range" id="${id}" min="${min}" max="${max}" step="${step}">`;
  parent.appendChild(d);
  const inp = d.querySelector('input'), out = d.querySelector('output');
  const sync = () => { inp.value = read(); out.textContent = fmt(+inp.value); };
  inp.addEventListener('input', () => { write(+inp.value); out.textContent = fmt(+inp.value); touched(); update(); });
  controls.push(sync); sync();
}
const pct = v => Math.round(v) + '%', x2 = v => '×' + v.toFixed(2), gw = v => v.toFixed(0) + ' GW', pctf = v => Math.round(v * 100) + '%';
const gW = document.getElementById('g-weights');
for (const k of STATE_KEYS) slider(gW, { id: 'w-' + k, label: SNAMES[k], min: 0, max: 100, step: 1, read: () => W.states[k] * 100, write: v => W.states[k] = v / 100, fmt: v => pct(v) });
const gV = document.getElementById('g-val');
slider(gV, { id: 'share', label: "Anthropic's share of AI lab revenue", min: 35, max: 55, step: 1, read: () => share, write: v => share = v, fmt: pct });
gV.insertAdjacentHTML('beforeend', '<p class="hint">45% is Anthropic\'s Q3 2026 revenue against the lab market\'s $150bn run-rate. The end-October run-rate would be about 54%.</p>');

const gM = document.getElementById('g-mix');
gM.innerHTML = '<p class="hint">For each path, how likely each way of splitting the money is. Rows are rescaled to 100%.</p>';
const mt = document.createElement('table'); mt.className = 'mix';
mt.innerHTML = '<tr><th></th>' + WORLD_KEYS.map(w => `<th title="${WNAMES[w][0]}">${WNAMES[w][0].split(' ').slice(0, 2).join(' ')}</th>`).join('') + '</tr>' + STATE_KEYS.map(k => `<tr><th>${SSHORT[k]}</th>` + WORLD_KEYS.map(w => `<td><input id="m-${k}-${w}" type="number" min="0" max="100" step="5" aria-label="${SNAMES[k]}, ${WNAMES[w][0]}"></td>`).join('') + '</tr>').join('');
gM.appendChild(mt);
STATE_KEYS.forEach(k => WORLD_KEYS.forEach((w, i) => {
  const el = document.getElementById(`m-${k}-${w}`);
  controls.push(() => { el.value = W.mix[k][i]; });
  el.addEventListener('input', () => { W.mix[k][i] = Math.max(0, +el.value || 0); touched(); update(); });
}));

const gX = document.getElementById('g-model');
// These change the model's data-centre run, which the price does not respond
// to, so they sit beside the sliders they set rather than at the top (VD).
const MODEL_PRESETS = [
  ['Big tech keeps training through a crash', 'No cut to AI training in a crash', () => { P.BREAK_HS = [1, 1, 1, 1]; P.BREAK_COMMIT_HAIRCUT = 0; }],
  ['Deeper training cut in a crash', 'Big tech cuts AI training hard', () => { P.BREAK_HS = [0.90, 0.60, 0.80, 1.0]; P.BREAK_COMMIT_HAIRCUT = 0.40; }],
];
const mpb = document.createElement('div'); mpb.className = 'btns'; gX.appendChild(mpb);
MODEL_PRESETS.forEach(([n, t, f]) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = n; b.title = t; b.addEventListener('click', () => { f(); syncAll(); update(); }); mpb.appendChild(b); });
gX.insertAdjacentHTML('beforeend', '<h4>How fast the US can connect data centres</h4><p class="hint">Likelihood of each grid setting, and the most GW of IT capacity each can add a year. The US grid record is about 10 GW.</p>');
for (const [k, n] of [['responsive', 'Grid keeps up'], ['grid', 'Grid-limited'], ['backlash', 'Local opposition']]) slider(gX, { id: 'e-' + k, label: `Likelihood: ${n.toLowerCase()}`, min: 0, max: 100, step: 1, read: () => W.energ[k] * 100, write: v => W.energ[k] = v / 100, fmt: v => pct(v) });
slider(gX, { id: 'cr', label: 'Grid keeps up: GW a year from 2029', min: 8, max: 30, step: 1, read: () => P.ENERGISATION.responsive.US, write: v => P.ENERGISATION.responsive.US = v, fmt: gw });
slider(gX, { id: 'cre', label: 'Grid keeps up: GW a year, 2027-28', min: 6, max: 26, step: 1, read: () => P.RESPONSIVE_EARLY, write: v => P.RESPONSIVE_EARLY = v, fmt: gw });
slider(gX, { id: 'cg', label: 'Grid-limited: GW a year', min: 4, max: 22, step: 1, read: () => P.ENERGISATION.grid.US, write: v => P.ENERGISATION.grid.US = v, fmt: gw });
slider(gX, { id: 'cb', label: 'Local opposition: GW a year', min: 2, max: 16, step: 1, read: () => P.ENERGISATION.backlash.US, write: v => P.ENERGISATION.backlash.US = v, fmt: gw });
gX.insertAdjacentHTML('beforeend', '<h4>In a funding crash (2027-29)</h4><p class="hint">Growth multipliers for each year; ×1.00 means no cut.</p>');
[2027, 2028, 2029].forEach((y, i) => slider(gX, { id: 'bt' + y, label: `AI usage growth, ${y}`, min: 0.4, max: 1, step: 0.05, read: () => P.BREAK_TOKENS[i], write: v => P.BREAK_TOKENS[i] = v, fmt: x2 }));
[2027, 2028, 2029].forEach((y, i) => slider(gX, { id: 'bh' + y, label: `Big tech AI training growth, ${y}`, min: 0.4, max: 1.2, step: 0.05, read: () => P.BREAK_HS[i], write: v => P.BREAK_HS[i] = v, fmt: x2 }));
slider(gX, { id: 'bhc', label: 'Cut to AI labs\' compute spending from 2028', min: 0, max: 0.7, step: 0.05, read: () => P.BREAK_COMMIT_HAIRCUT, write: v => P.BREAK_COMMIT_HAIRCUT = v, fmt: pctf });
slider(gX, { id: 'bb28', label: 'Share of 2028 data-centre builds that get chips', min: 0.2, max: 1, step: 0.05, read: () => P.BREAK_BUILD[2028], write: v => P.BREAK_BUILD[2028] = v, fmt: pctf });
slider(gX, { id: 'bb29', label: 'Share of 2029 data-centre builds that get chips', min: 0.2, max: 1, step: 0.05, read: () => P.BREAK_BUILD[2029], write: v => P.BREAK_BUILD[2029] = v, fmt: pctf });
slider(gX, { id: 'w-def', label: 'Likelihood the crash delays the chip upgrade', min: 0, max: 100, step: 5, read: () => W.deferred * 100, write: v => W.deferred = v / 100, fmt: v => pct(v) });
gX.insertAdjacentHTML('beforeend', '<h4>Demand and supply</h4>');
slider(gX, { id: 'tok', label: 'AI usage growth (×1.00 = model)', min: 0.5, max: 1.5, step: 0.05, read: () => P.token_scale, write: v => P.token_scale = v, fmt: x2 });
slider(gX, { id: 'eff', label: 'Chip and software efficiency gains', min: 0.5, max: 1.5, step: 0.05, read: () => P.eff_scale, write: v => P.eff_scale = v, fmt: x2 });
slider(gX, { id: 'lps', label: 'AI labs\' compute spending plans', min: 0.5, max: 1.5, step: 0.05, read: () => P.lab_plan_scale, write: v => P.lab_plan_scale = v, fmt: x2 });
slider(gX, { id: 'rent', label: 'Rent labs pay, $bn per GW a year', min: 10, max: 20, step: 0.5, read: () => P.LAB_RENT, write: v => P.LAB_RENT = v, fmt: v => '$' + v.toFixed(1) + 'bn' });
slider(gX, { id: 'conv', label: 'Non-AI data-centre load growth a year', min: 1.0, max: 1.12, step: 0.01, read: () => P.CONV_GROWTH, write: v => P.CONV_GROWTH = v, fmt: v => '+' + Math.round((v - 1) * 100) + '%' });
slider(gX, { id: 'base', label: 'Size of today\'s data-centre base', min: 0.6, max: 1.4, step: 0.05, read: () => P.base_scale, write: v => P.base_scale = v, fmt: x2 });

// The presets are sets of the table's columns (VD, "two versions and the
// table"). Pressing one writes the path sliders, so the two never disagree.
const CRASH = [['late', 'lateBreak'], ['early', 'earlyBreak'], ['takeoff', 'takeoffBreak']];
const PRESETS = [
  ['Base case', 'Kristjan\'s weights over every scenario', () => { P = clone(DEFAULTS); W = clone(WEIGHTS); share = 45; mine = []; }],
  ['No funding crash', 'Moves the crash paths\' weight to the paths without one', () => CRASH.forEach(([a, b]) => { W.states[a] += W.states[b]; W.states[b] = 0; })],
  ['Funding crash', 'Moves every path\'s weight to its crash version', () => CRASH.forEach(([a, b]) => { W.states[b] += W.states[a]; W.states[a] = 0; })],
];
let preset = 'Base case', mine = [];
const pb = document.getElementById('presets');
PRESETS.forEach(([n, t, f]) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = n; b.title = t; b.dataset.p = n; b.addEventListener('click', () => { f(); preset = n; syncAll(); update(); }); pb.appendChild(b); });
const touched = () => { preset = null; };
function syncAll() { controls.forEach(f => f()); }
document.getElementById('metric').addEventListener('change', render);
// The assumptions open from the start, so a reader sees at once that every
// one of them can be changed (Kristjan, 12 Nov). On a desk the two folds
// inside open too; on a phone they stay shut so the grid is not pushed a
// screen-length down, and the open panel still shows they are there.
document.getElementById('controls').open = true;
try { if (window.matchMedia('(min-width: 1000px)').matches) document.querySelectorAll('#controls details.sub-fold').forEach(d => d.open = true); } catch (e) {}

// ---- compute ----
let C = [];
function summarise(cells, sh) {
  const v = { shortage: 0, balance: 0, grey: 0, glut: 0 }; let owners = 0, val = 0, jobs = 0, nojobs = 0, above = 0, fails = 0;
  for (const c of cells) {
    const r = c.rows[4]; v[verdict(r.ratio.US)] += c.weight; if (r.ownerCover >= 1) owners += c.weight;
    const si = STATE_KEYS.indexOf(c.key), x = valAt(c.world, si, sh);
    val += c.weight * ANT.value(c.world, si, sh);
    if (JOBS[c.world][si] == null) nojobs += c.weight; else jobs += c.weight * JOBS[c.world][si];
    // <= 0: the values arrive floored, so a wiped-out scenario is exactly $0.
    if (x >= ANT.IPO) above += c.weight; if (x <= 0) fails += c.weight;
  }
  return { v, owners, val, jobs: nojobs > 0 ? null : jobs, above, fails };
}
function update() { C = cells(P, W); render(); }
const col = { shortage: 'var(--short)', balance: 'var(--bal)', grey: 'var(--grey)', glut: 'var(--glut)' };
const vname = { shortage: 'shortage', balance: 'balanced', grey: 'weak', glut: 'oversupply' };
function render() {
  const S = summarise(C, share), lo = summarise(C, 35).val, hi = summarise(C, 55).val;
  document.getElementById('h-num').textContent = '$' + S.val.toFixed(0);
  const gap = S.val - 74;
  document.getElementById('h-vs').innerHTML = `a share, <b>$${Math.abs(gap).toFixed(0)} ${gap >= 0 ? 'above' : 'below'}</b> the $74 IPO price`;
  // /ant's scale: the price as the one ink dot and the IPO tick. No share
  // band (D-370, Kristjan: "one number for each"); the range stays in words.
  ANTSCALE(document.getElementById('h-strip'), { price: S.val });
  document.querySelectorAll('#presets button').forEach(b => b.setAttribute('aria-pressed', b.dataset.p === preset));
  document.getElementById('h-facts').innerHTML = `<span>$74 needs the labs' own plans <b>and</b> about a 76% market share (45% today)</span><span>Range <b>$${lo.toFixed(0)}-${hi.toFixed(0)}</b> as Anthropic's market share runs 35-55%</span><span><b>${Math.round(S.above * 100)}%</b> of outcomes above $74</span><span><b>${Math.round(S.fails * 100)}%</b> where the equity is wiped out</span>`;
  const gg = S.v.glut + S.v.grey;
  document.getElementById('t-verdict').textContent = `${Math.round(gg * 100)}% weak or oversupplied`;
  document.getElementById('t-stack').innerHTML = ['shortage', 'balance', 'grey', 'glut'].map(k => `<span style="width:${S.v[k] * 100}%;background:${col[k]}"></span>`).join('');
  document.getElementById('t-legend').textContent = ['shortage', 'balance', 'grey', 'glut'].map(k => `${vname[k]} ${Math.round(S.v[k] * 100)}%`).join(' · ');
  document.getElementById('t-owners').textContent = `In ${Math.round(S.owners * 100)}% of outcomes`;
  document.getElementById('t-jobs').textContent = S.jobs == null ? 'Not modelled for takeoff with a crash' : `${S.jobs.toFixed(1)}M (${(S.jobs / 157 * 100).toFixed(1)}%)`;
  const st = norm(W.states); document.getElementById('w-sum').textContent = `Rescaled to 100%. A funding crash in ${Math.round((st.lateBreak + st.earlyBreak + st.takeoffBreak) * 100)}% of outcomes.`;
  renderGrid(); renderDetail();
}
function cellRows(world, key) { const [speed, brk] = STATES[STATE_KEYS.indexOf(key)]; return run(P, world, speed, brk, 'deferred', 'grid'); }
function cellWeight(world, key) { return C.filter(c => c.world === world && c.key === key).reduce((a, c) => a + c.weight, 0); }
const KEYS = {
  // Classes are named by step on the house anomaly scale, not by verdict, so
  // one fill means one thing in every mode (VD design pass).
  val: [['px-hi', '$74 and above'], ['px-lo', 'Below $74'], ['rul', '$0: equity wiped out']],
  ratio: [['st5', 'Shortage (1.00 or more)'], ['st4', 'Balanced (0.85 to 1.00)'], ['st3', 'Weak (0.75 to 0.85)'], ['st2', 'Oversupply (below 0.75)']],
  cover: [['st4', 'Rents cover cost'], ['st3', '75 to 100% covered'], ['st2', 'Below 75%']],
  jobs: [], labrev: [],
};
function renderGrid() {
  const m = document.getElementById('metric').value;
  document.getElementById('key').innerHTML = KEYS[m].map(([c, n]) => `<span><i class="${c}"></i>${n}</span>`).join('') + (m === 'ratio' || m === 'cover' ? '<span>Grid-limited power, crash delays the chip upgrade.</span>' : m === 'labrev' ? '<span>Low if AI revenue grows with the work it replaces, high if it grows as the labs plan.</span>' : '');
  // A column head puts all path weight on that path and keeps the
  // who-gets-paid split; a row head puts all of the split on that world and
  // keeps the path weights. Both write the sliders (VD).
  const st = norm(W.states), colOn = STATE_KEYS.find(k => st[k] > 0.999);
  const rowOn = WORLD_KEYS.find((w, wi) => STATE_KEYS.every(k => W.mix[k].every((v, j) => (j === wi) === (v > 0))));
  const one = document.getElementById('one');
  if (one) {
    one.hidden = !(colOn || rowOn);
    one.querySelector('span').textContent = colOn && rowOn ? 'Showing one scenario only.' : colOn ? 'Showing one path only.' : 'Showing one world only.';
  }
  let h = '<tr><th></th>' + STATE_KEYS.map(k => `<th><button type="button" class="hd" data-col="${k}" aria-pressed="${k === colOn}">${SNAMES[k]}</button></th>`).join('') + '</tr>';
  for (const w of WORLD_KEYS) {
    h += `<tr><th class="w"><button type="button" class="hd" data-row="${w}" aria-pressed="${w === rowOn}">${WNAMES[w][0]}</button><small>${WNAMES[w][1]}</small></th>`;
    STATE_KEYS.forEach((k, si) => {
      const r = cellRows(w, k)[4]; let txt, cls = 'st4';
      if (m === 'ratio') { txt = r.ratio.US.toFixed(2); cls = { shortage: 'st5', balance: 'st4', grey: 'st3', glut: 'st2' }[verdict(r.ratio.US)]; }
      else if (m === 'val') { const v = valOf(w, si); txt = v <= 0 ? '$0' : '$' + v.toFixed(0); cls = v <= 0 ? 'rul' : v >= ANT.IPO ? 'px-hi' : 'px-lo'; }
      else if (m === 'jobs') txt = JOBS[w][si].toFixed(1) + 'M' + (k === 'takeoffBreak' ? ' est.' : '');
      else if (m === 'labrev') txt = '$' + POOL.low[w][k][4].toLocaleString() + '-' + POOL.high[w][k][4].toLocaleString() + 'bn';
      else { txt = Math.round(r.ownerCover * 100) + '%'; cls = r.ownerCover >= 1 ? 'st4' : r.ownerCover >= 0.75 ? 'st3' : 'st2'; }
      const selc = sel.world === w && sel.key === k ? ' sel' : '', cw = cellWeight(w, k);
      const off = cw < 0.0005 ? ' off' : '', me = mine.some(([mw, mk]) => mw === w && mk === k) ? ' mine' : '';
      h += `<td class="${cls}${selc}${off}${me}" data-w="${w}" data-k="${k}" tabindex="0">${txt}<small>${(cw * 100).toFixed(1)}%</small></td>`;
    });
    h += '</tr>';
  }
  const g = document.getElementById('grid'); g.innerHTML = h;
  g.querySelectorAll('.hd').forEach(b => b.addEventListener('click', () => {
    if (b.dataset.col) STATE_KEYS.forEach(k => W.states[k] = k === b.dataset.col ? 1 : 0);
    else STATE_KEYS.forEach(k => W.mix[k] = WORLD_KEYS.map(x => x === b.dataset.row ? 100 : 0));
    touched(); syncAll(); update();
  }));
  g.querySelectorAll('td').forEach(td => { const pick = () => { sel = { world: td.dataset.w, key: td.dataset.k }; renderGrid(); renderDetail(); }; td.addEventListener('click', pick); td.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } }); });
}
function renderDetail() {
  const rows = cellRows(sel.world, sel.key), si = STATE_KEYS.indexOf(sel.key), v = valOf(sel.world, si);
  document.getElementById('d-title').textContent = `${WNAMES[sel.world][0]} · ${SNAMES[sel.key]} · Anthropic ${v <= 0 ? '$0, wiped out' : '$' + v.toFixed(0) + ' a share'}`;
  const W0 = 540, H0 = 250, l = 42, r = 118, t = 22, b = 26;
  const maxV = Math.max(...rows.map(x => Math.max(x.dem.US, x.cap.US))) * 1.1;
  const nice = maxV <= 60 ? 10 : maxV <= 150 ? 25 : maxV <= 400 ? 50 : 100, top = Math.ceil(maxV / nice) * nice;
  const X = i => l + i * (W0 - l - r) / 4, Y = v => t + (H0 - t - b) * (1 - v / top);
  let s = '';
  for (let v2 = 0; v2 <= top; v2 += nice) s += `<line x1="${l}" x2="${W0 - r}" y1="${Y(v2)}" y2="${Y(v2)}" stroke="var(--rule)" stroke-width="1"/><text x="${l - 6}" y="${Y(v2) + 3}" text-anchor="end">${v2}</text>`;
  rows.forEach((x, i) => s += `<text x="${X(i)}" y="${H0 - 8}" text-anchor="middle">${x.year}</text>`);
  const path = f => rows.map((x, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(f(x)).toFixed(1)).join(' ');
  // Step 5 fills the gap only in the years demand runs above capacity, so
  // colour appears exactly where the shortage is (VD design pass).
  for (let i = 0; i < 4; i++) {
    const a = rows[i], b2 = rows[i + 1], da = a.dem.US - a.cap.US, db = b2.dem.US - b2.cap.US;
    if (da <= 0 && db <= 0) continue;
    const t0 = da > 0 ? 0 : da / (da - db), t1 = db > 0 ? 1 : da / (da - db), lerp2 = (u, f) => f(a) + (f(b2) - f(a)) * u;
    const xs = [t0, t1].map(u => l + (i + u) * (W0 - l - r) / 4);
    const dem = [t0, t1].map(u => Y(lerp2(u, x => x.dem.US))), cap = [t0, t1].map(u => Y(lerp2(u, x => x.cap.US)));
    s += `<path d="M${xs[0]} ${dem[0]}L${xs[1]} ${dem[1]}L${xs[1]} ${cap[1]}L${xs[0]} ${cap[0]}Z" fill="#EFC9BD" opacity=".9"/>`;
  }
  s += `<path d="${path(x => x.cap.US)}" fill="none" stroke="var(--soft)" stroke-width="1.5" stroke-dasharray="4 3"/><path d="${path(x => x.dem.US)}" fill="none" stroke="var(--ink)" stroke-width="2"/>`;
  rows.forEach((x, i) => { s += `<circle cx="${X(i)}" cy="${Y(x.dem.US)}" r="2.5" fill="var(--ink)"/>`; });
  const e = rows[4], yc = Y(e.cap.US), yd = Y(e.dem.US), apart = Math.abs(yc - yd) < 14 ? (yc < yd ? -7 : 7) : 0;
  s += `<text class="end" x="${X(4) + 8}" y="${yc + 4 + apart}" style="fill:var(--soft)">Capacity ${e.cap.US.toFixed(0)}</text>`;
  s += `<text class="end" x="${X(4) + 8}" y="${yd + 4 - apart}" style="fill:var(--ink)">Demand ${e.dem.US.toFixed(0)}</text>`;
  s += `<text x="${l}" y="${t - 8}">US AI, GW of IT capacity (grid-limited power)</text>`;
  document.getElementById('chart').innerHTML = s;
  const f0 = v2 => v2.toFixed(0), f2 = v2 => v2.toFixed(2);
  const lines = [
    ['AI usage, trillion tokens a day (West)', x => Math.round(x.tokens).toLocaleString()],
    ['US AI demand, GW', x => f0(x.dem.US)], ['US AI capacity, GW', x => f0(x.cap.US)],
    ['Demand ÷ capacity', x => f2(x.ratio.US)],
    ['AI lab revenue, $bn (low-high)', (x, i) => POOL.low[sel.world][sel.key][i].toLocaleString() + '-' + POOL.high[sel.world][sel.key][i].toLocaleString()], ['AI lab compute spend, $bn', x => f0(x.labSpend)],
    ['Owners paid (rent ÷ cost)', x => Math.round(x.ownerCover * 100) + '%'],
  ];
  document.getElementById('d-table').innerHTML = '<tr><th></th>' + rows.map(x => `<th>${x.year}</th>`).join('') + '</tr>' + lines.map(([n, f]) => `<tr><td>${n}</td>${rows.map((x, yi) => `<td>${f(x, yi)}</td>`).join('')}</tr>`).join('');
}
// ?a=late,mid,C1,45, from /ant's "Fine-tune it in the full model": every
// weight on the reader's path and world at their share, so the headline here
// is the number they just saw there.
function applyAnswers(list) {
  const a = (list || '').split(',');
  const sp = { late: 1, early: 1, takeoff: 1 }, mo = { yes: 1, mid: 1, no: 1 }, sh = { 35: 1, 45: 1, 55: 1 };
  if (a.length !== 4 || !sp[a[0]] || !mo[a[1]] || !WORLD_KEYS.includes(a[2]) || !sh[a[3]]) return;
  const w = ANT.weights({ speed: a[0], money: a[1], world: a[2], share: a[3] });
  STATE_KEYS.forEach(k => { W.states[k] = w[k] || 0; W.mix[k] = WORLD_KEYS.map(x => x === a[2] ? 100 : 0); });
  share = +a[3]; preset = null; mine = Object.keys(w).map(k => [a[2], k]); syncAll();
  const sw = document.querySelector('.sw a[data-to="ant"]');
  if (sw) { sw.href = '../ant/?a=' + a.join(','); if (window.ANT_PROTO) sw.onclick = e => { e.preventDefault(); ANT_PROTO.toAnt(); }; }
  const f = document.getElementById('from');
  f.innerHTML = 'Set from your four answers. <a id="back-q" href="../ant/?a=' + a.join(',') + '">Back to the questions</a> &middot; <button type="button" id="base">Start from the base case</button>';
  f.hidden = false;
  if (window.ANT_PROTO) document.getElementById('back-q').onclick = e => { e.preventDefault(); ANT_PROTO.toAnt(); };
  document.getElementById('base').addEventListener('click', () => { P = clone(DEFAULTS); W = clone(WEIGHTS); share = 45; preset = 'Base case'; mine = []; syncAll(); update(); f.hidden = true; try { history.replaceState(null, '', location.pathname); } catch (e) {} });
  return true;
}
document.getElementById('one-base').addEventListener('click', () => { P = clone(DEFAULTS); W = clone(WEIGHTS); share = 45; preset = 'Base case'; mine = []; syncAll(); update(); });
window.ANT_PRO = { apply: list => { if (applyAnswers(list)) update(); } };
// Fill every control from the model once: the split table's inputs had no
// initial values, so the rail showed empty boxes until a preset was pressed.
syncAll();
applyAnswers(new URLSearchParams(location.search).get('a'));
update();
