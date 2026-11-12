// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// HOLD: the basis is not settled (UX, 12 Nov). These are the values in the
// approved concept v3: late and early from Compute 2030 Explorer v4.1 VAL
// (R-20261112-v41-grid-valuation); takeoff from mkt/anthropic-valuation
// F-20261112-takeoff-upside-weighted-63-today, commit 2296561, at the
// explorer's precision; takeoff + crash from v3 (mkt, same commit). MKT's
// wage-based values are the alternative Kristjan has not chosen between.
//
// $ a share today, by Anthropic's share of frontier-lab revenue (35, 45,
// 55%), by world C1-C5. Columns, in STATES order:
//   [late, early, takeoff, late + crash, early + crash, takeoff + crash]
// A negative value is a scenario where debts and compute contracts
// outweigh the business; shareholders get $0 in it.
window.ANT = (function () {
  const IPO = 74;
  const STATES = ["late", "early", "takeoff", "lateBreak", "earlyBreak", "takeoffBreak"];
  const VAL = {
    35: { C1: [104.3, -8.4, 160.3, 53.9, -5.5, 107], C2: [-13.1, -25.0, -2.2, -7.4, -14.0, -1], C3: [64.3, -15.2, 101.1, 25.6, -9.0, 69], C4: [164.8, 7.0, 279.6, 84.8, -0.3, 178], C5: [10.8, -20.9, 30.2, 3.4, -11.9, 17] },
    45: { C1: [136.3, -2.0, 208.3, 70.6, -2.0, 138], C2: [-8.0, -23.3, 3.6, -4.5, -13.0, 3], C3: [85.2, -10.8, 132.3, 34.9, -6.5, 90], C4: [214.1, 17.8, 361.7, 110.1, 4.6, 230], C5: [21.5, -18.1, 43.3, 8.9, -10.2, 24] },
    55: { C1: [168.2, 4.4, 256.2, 86.9, 1.5, 170], C2: [-4.3, -21.7, 8.5, -2.0, -11.9, 6], C3: [105.9, -6.4, 163.4, 43.3, -4.0, 110], C4: [263.3, 28.3, 443.7, 135.1, 9.5, 281], C5: [30.2, -15.3, 54.6, 13.5, -8.6, 30] },
  };

  // Raw cell, interpolated between the 35/45/55 grid points.
  function cell(world, state, share) {
    const si = typeof state === "number" ? state : STATES.indexOf(state);
    const s = Math.min(55, Math.max(35, share)), lo = s <= 45 ? 35 : 45, t = (s - lo) / 10;
    return VAL[lo][world][si] * (1 - t) + VAL[lo + 10][world][si] * t;
  }

  // One price rule for both pages: each scenario is floored at $0 BEFORE
  // any averaging, because equity cannot be worth less than nothing. The
  // explorer always did this; concept v3 averaged first, which priced
  // "something in between" lower whenever one side failed.
  function value(world, state, share) { return Math.max(cell(world, state, share), 0); }

  // The four questions' answers: speed (late | early | takeoff), money
  // (yes | mid | no), world (C1-C5), share (35 | 45 | 55). "Something in
  // between" is half the flowing case and half the crash case.
  function weights(a) {
    const go = a.speed, stop = a.speed + "Break";
    return a.money === "yes" ? { [go]: 1 } : a.money === "no" ? { [stop]: 1 } : { [go]: 0.5, [stop]: 0.5 };
  }
  function price(a) {
    const w = weights(a);
    return Object.keys(w).reduce((s, k) => s + w[k] * value(a.world, k, +a.share), 0);
  }
  return { IPO, STATES, VAL, cell, value, weights, price };
})();
