// Port of model/scenarios_v41.py (ai/compute-demand-2030, 2026-11-12). Every constant is a field of DEFAULTS
// so the explorer can change it; run(P, world, speed, brk, refresh, energ) mirrors the Python run().
const YEARS = [2026, 2027, 2028, 2029, 2030];
const DEFAULTS = {
  COST_PER_GW: 11.6, CAPEX_PER_GW: 42.0, AGENTIC_WEIGHT: 0.30,
  BASE_POOLS: { US: { installed: 46.0, conv: 26.0 }, China: { installed: 28.6, conv: 23.6 }, RoW: { installed: 21.0, conv: 16.0 } },
  BASE_LOAD: { west_inference: 8.0, lab_training: 6.0, hs_training: 10.0, open_training: 1.0, china_ai: 5.0 },
  WEST_TOKENS: 400.0, CHINA_TOKENS: 300.0, BASE_AGENTIC: 0.35,
  BASE_SEG: { lab: 0.45, bundle: 0.35, hosted: 0.10, self: 0.06, device: 0.04 },
  SEG_W: { lab: 1.0, bundle: 0.6, hosted: 0.7, self: 1.3, device: 0.0 },
  LAB_REVENUE_2026: 150.0, HOSTED_PRICE_2026: 0.20, HOSTED_PASS: 0.70,
  LAB_PLAN: { 2027: 220.0, 2028: 275.0, 2029: 335.0, 2030: 395.0 }, LAB_RENT: 15.0,
  LAB_PLAN_WORLD: { C1: 1.0, C2: 0.6, C3: 0.8, C4: 1.25, C5: 0.75 },
  LAB_PLAN_SPEED: { late: 1.0, early: 0.7, takeoff: 1.5 },
  US_HOST: { inference: 0.70, lab_training: 0.85, hs_training: 0.85, open_training: 0.60 }, SPILL: 0.5,
  PIPELINE: { US: { 2027: 18.5, 2028: 15.0 }, RoW: { 2027: 6.0, 2028: 6.0 } },
  BUILD_RATE: { US: 15.0, RoW: 6.0 },
  ENERGISATION: { responsive: { US: 18.0, RoW: 9.0 }, grid: { US: 11.0, RoW: 7.0 }, backlash: { US: 7.0, RoW: 5.0 } },
  RESPONSIVE_EARLY: 13.0, CHINA_ADD: 5.0,
  WORLDS: {
    C1: { seg: { lab: 0.50, bundle: 0.30, hosted: 0.10, self: 0.04, device: 0.06 }, lab_price: 0.57, hosted_price: 0.25, eff: 1.46, agentic: 0.72, token_mult: 1.0, hs_growth_mult: 1.0, open_train_growth: 1.15 },
    C2: { seg: { lab: 0.22, bundle: 0.28, hosted: 0.28, self: 0.12, device: 0.10 }, lab_price: 0.18, hosted_price: 0.15, eff: 1.84, agentic: 0.80, token_mult: 1.10, hs_growth_mult: 0.95, open_train_growth: 1.45 },
    C3: { seg: { lab: 0.32, bundle: 0.25, hosted: 0.30, self: 0.07, device: 0.06 }, lab_price: 0.57, hosted_price: 0.40, eff: 1.46, agentic: 0.78, token_mult: 1.0, hs_growth_mult: 1.0, open_train_growth: 1.30 },
    C4: { seg: { lab: 0.65, bundle: 0.20, hosted: 0.07, self: 0.03, device: 0.05 }, lab_price: 0.68, hosted_price: 0.25, eff: 1.46, agentic: 0.78, token_mult: 1.0, hs_growth_mult: 0.95, open_train_growth: 1.10 },
    C5: { seg: { lab: 0.25, bundle: 0.55, hosted: 0.10, self: 0.04, device: 0.06 }, lab_price: 0.45, hosted_price: 0.25, eff: 1.60, agentic: 0.60, token_mult: 1.0, hs_growth_mult: 1.10, open_train_growth: 1.15 },
  },
  SPEEDS: {
    late: { tokens: [2.5, 2.0, 1.6, 1.6], hs_growth: 1.35, price_mult: 1.0, agentic: null },
    early: { tokens: [1.6, 1.3, 1.2, 1.15], hs_growth: 1.10, price_mult: 0.8, agentic: 0.40 },
    takeoff: { tokens: [2.8, 2.6, 2.3, 2.1], hs_growth: 1.70, price_mult: 1.3, agentic: 0.85 },
  },
  CHINA_TOKENS_GROWTH: { late: [2.6, 2.0, 1.7, 1.6], early: [1.8, 1.4, 1.25, 1.2], takeoff: [2.8, 2.5, 2.2, 2.0] },
  CHINA_EFF: 1.30, CONV_GROWTH: 1.08,
  BREAK_TOKENS: [0.85, 0.70, 0.85, 1.0], BREAK_HS: [0.95, 0.80, 0.90, 1.0],
  BREAK_BUILD: { 2028: 0.65, 2029: 0.50 }, BREAK_COMMIT_HAIRCUT: 0.40, BREAK_DEFERRED_EFF: [null, 1.15, 1.15, 1.30],
  // explorer-only multipliers (1.0 = model v4.1)
  token_scale: 1.0, eff_scale: 1.0, base_scale: 1.0, lab_plan_scale: 1.0,
};
function buildSignal(u) { return u >= 1.0 ? 1.25 : u >= 0.9 ? 1.0 : u >= 0.8 ? 0.6 : u >= 0.7 ? 0.3 : 0.1; }
const lerp = (a, b, i) => a + (b - a) * i / 4;
function run(P, world, speed, brk, refresh, energ) {
  const w = P.WORLDS[world], s = P.SPEEDS[speed];
  const pools = {}; for (const k in P.BASE_POOLS) pools[k] = { installed: P.BASE_POOLS[k].installed * P.base_scale, conv: P.BASE_POOLS[k].conv * P.base_scale };
  const L = {}; for (const k in P.BASE_LOAD) L[k] = P.BASE_LOAD[k] * P.base_scale;
  const segEnd = w.seg, wt = a => a * P.AGENTIC_WEIGHT + (1 - a);
  let idx0 = 0; for (const k in P.BASE_SEG) idx0 += P.BASE_SEG[k] * P.SEG_W[k];
  const agEnd = s.agentic !== null ? s.agentic : w.agentic;
  let tokens = P.WEST_TOKENS, ctok = P.CHINA_TOKENS, eff = 1, ceff = 1;
  let hs = L.hs_training, open = L.open_training, china = L.china_ai;
  const pf0 = P.LAB_REVENUE_2026 * 1e3 / (P.WEST_TOKENS * 365 * P.BASE_SEG.lab);
  const hist = {}, rows = [], queue = { US: 0, RoW: 0 }, dark = { US: 0, RoW: 0 };
  YEARS.forEach((y, i) => {
    if (i > 0) {
      let g = (1 + (s.tokens[i - 1] - 1) * P.token_scale) * Math.pow(w.token_mult, 0.25);
      if (brk) g *= P.BREAK_TOKENS[i - 1];
      tokens *= g;
      ctok *= P.CHINA_TOKENS_GROWTH[speed][i - 1] * (brk ? [0.9, 0.85, 0.95, 1.0][i - 1] : 1);
      let e = w.eff;
      if (brk && refresh === 'deferred' && P.BREAK_DEFERRED_EFF[i - 1]) e = P.BREAK_DEFERRED_EFF[i - 1];
      eff *= 1 + (e - 1) * P.eff_scale;
      ceff *= P.CHINA_EFF;
      hs *= s.hs_growth * w.hs_growth_mult * (brk ? P.BREAK_HS[i - 1] : 1);
      open *= w.open_train_growth * (brk ? P.BREAK_HS[i - 1] : 1);
      for (const p of ['US', 'RoW']) {
        let want = (y in P.PIPELINE[p]) ? P.PIPELINE[p][y] : P.BUILD_RATE[p] * buildSignal(hist[y - 2][p]);
        want += queue[p];
        let capY = P.ENERGISATION[energ][p];
        if (energ === 'responsive' && p === 'US' && y <= 2028) capY = P.RESPONSIVE_EARLY;
        let add = Math.min(want, capY);
        queue[p] = (y in P.PIPELINE[p]) ? want - add : 0;
        if (brk) {
          const built = add; add *= (P.BREAK_BUILD[y] !== undefined ? P.BREAK_BUILD[y] : 1); dark[p] += built - add;
          if (y === 2030) add += dark[p] * Math.min(buildSignal(hist[2028][p]), 1.0);
        }
        pools[p].installed += add; pools[p].conv *= P.CONV_GROWTH;
      }
      pools.China.installed += P.CHINA_ADD; pools.China.conv *= P.CONV_GROWTH;
      china = L.china_ai * (ctok / P.CHINA_TOKENS) / ceff;
    }
    const seg = {}; let idx = 0; for (const k in P.BASE_SEG) { seg[k] = lerp(P.BASE_SEG[k], segEnd[k], i); idx += seg[k] * P.SEG_W[k]; }
    const ag = lerp(P.BASE_AGENTIC, agEnd, i), wRel = wt(ag) / wt(P.BASE_AGENTIC);
    const westInf = L.west_inference * (tokens / P.WEST_TOKENS) * (idx / idx0) * wRel / eff;
    const labInf = westInf * seg.lab * P.SEG_W.lab / idx, bundleInf = westInf * seg.bundle * P.SEG_W.bundle / idx, selfInf = westInf * seg.self * P.SEG_W.self / idx;
    const pf = pf0 * lerp(1, w.lab_price * s.price_mult, i), ph = P.HOSTED_PRICE_2026 * lerp(1, w.hosted_price, i);
    const labRev = tokens * 365 * seg.lab * pf / 1e3, hostedRev = tokens * 365 * seg.hosted * ph / 1e3;
    let labGw, labSpend;
    if (i === 0) { labGw = labInf + L.lab_training; labSpend = labGw * P.LAB_RENT; }
    else {
      let f = P.LAB_PLAN_WORLD[world] * P.LAB_PLAN_SPEED[speed]; f = 1 + (f - 1) * (y === 2027 ? 0.5 : 1);
      labSpend = P.LAB_PLAN[y] * f * P.lab_plan_scale; if (brk && y >= 2028) labSpend *= 1 - P.BREAK_COMMIT_HAIRCUT;
      labGw = Math.max(labSpend / P.LAB_RENT, labInf / 0.7); labSpend = labGw * P.LAB_RENT;
    }
    const labTrain = labGw - labInf, H = P.US_HOST;
    const demUS = westInf * H.inference + labTrain * H.lab_training + hs * H.hs_training + open * H.open_training;
    const dem = { US: demUS, RoW: westInf + labTrain + hs + open - demUS, China: china };
    const cap = {}, served = {}, loadOn = {};
    for (const p in pools) { cap[p] = pools[p].installed - pools[p].conv; served[p] = Math.min(dem[p], cap[p]); loadOn[p] = served[p]; }
    for (const [a, b] of [['US', 'RoW'], ['RoW', 'US']]) {
      const unmet = dem[a] - served[a], spare = cap[b] - loadOn[b];
      if (unmet > 0 && spare > 0) { const t = Math.min(P.SPILL * unmet, spare); served[a] += t; loadOn[b] += t; }
    }
    const ratio = {}; for (const p in pools) ratio[p] = dem[p] / cap[p];
    const westDem = dem.US + dem.RoW, westServed = served.US + served.RoW, sf = westServed / westDem, westCap = cap.US + cap.RoW;
    const ownLoad = (bundleInf + hs + selfInf) * sf, rentedCap = Math.max(westCap - ownLoad, 1e-6);
    const paid = labSpend * sf + hostedRev * sf * P.HOSTED_PASS;
    rows.push({ year: y, tokens, westInf, labInf, labTrain, hs, open, china, dem, cap, ratio,
      installed: { US: pools.US.installed, RoW: pools.RoW.installed, China: pools.China.installed },
      globalDem: dem.US + dem.RoW + dem.China, globalCap: cap.US + cap.RoW + cap.China, sf,
      labRev, labRevServed: labRev * sf, labSpend: labSpend * sf, labRatio: (labSpend * sf) / Math.max(labRev * sf, 1e-6),
      ownerCover: paid / (rentedCap * P.COST_PER_GW) });
    hist[y] = ratio;
  });
  return rows;
}
function verdict(u) { return u >= 1 ? 'shortage' : u >= 0.85 ? 'balance' : u >= 0.75 ? 'grey' : 'glut'; }
if (typeof module !== 'undefined') module.exports = { DEFAULTS, run, verdict, YEARS };
const STATES = [['late', false], ['early', false], ['takeoff', false], ['late', true], ['early', true]];
const STATE_KEYS = ['late', 'early', 'takeoff', 'lateBreak', 'earlyBreak'];
const WEIGHTS = {
  states: { late: 0.25, early: 0.10, takeoff: 0.05, lateBreak: 0.45, earlyBreak: 0.15 },
  energ: { responsive: 0.30, grid: 0.50, backlash: 0.20 },
  deferred: 0.5,
  mix: { late: [30, 15, 15, 25, 15], early: [25, 40, 10, 5, 20], takeoff: [20, 5, 10, 55, 10], lateBreak: [35, 20, 10, 20, 15], earlyBreak: [25, 40, 5, 10, 20] },
};
const WORLD_KEYS = ['C1', 'C2', 'C3', 'C4', 'C5'];
function norm(o) { const t = Object.values(o).reduce((a, b) => a + b, 0) || 1; const r = {}; for (const k in o) r[k] = o[k] / t; return r; }
function cells(P, W) {
  const st = norm(W.states), en = norm(W.energ), out = [];
  STATES.forEach(([speed, brk], si) => {
    const key = STATE_KEYS[si], mixRaw = W.mix[key], mt = mixRaw.reduce((a, b) => a + b, 0) || 1;
    WORLD_KEYS.forEach((world, wi) => {
      for (const energ in en) {
        const branches = brk ? [['deferred', W.deferred], ['ontime', 1 - W.deferred]] : [['deferred', 1]];
        for (const [refresh, wr] of branches) {
          const weight = st[key] * (mixRaw[wi] / mt) * en[energ] * wr;
          if (weight <= 0) continue;
          out.push({ world, speed, brk, key, energ, refresh, weight, rows: run(P, world, speed, brk, refresh, energ) });
        }
      }
    });
  });
  return out;
}
if (typeof module !== 'undefined') Object.assign(module.exports, { STATES, STATE_KEYS, WEIGHTS, WORLD_KEYS, cells, norm });

