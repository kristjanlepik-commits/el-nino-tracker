// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// Values since 12 Nov evening: AI - Compute's values_equal_weight
// (compute-demand-2030/outputs/ant-stories-facts.json), sent by the Mycelium
// UX desk with Kristjan's "send". Each cell is the equal weight of MKT's low
// and high revenue paths, each floored at $0, at 9.74%: the method behind
// Kristjan's $27 headline. They replace the token x price grid (concept v3),
// which MKT withdrew as the valuation basis.
//
// $ a share today, by Anthropic's share of frontier-lab revenue (35, 45,
// 55%), by world C1-C5. Columns, in STATES order:
//   [late, early, takeoff, late + crash, early + crash, takeoff + crash]
// A cell at $0 is a scenario where debts and compute contracts outweigh the
// business; shareholders get nothing in it.
window.ANT = (function () {
  const IPO = 74;
  // The price scale's top: the values now top out near $100, so $0 to $150
  // fits them with room, and the IPO sits clear of the axis ends.
  const SCALE = 150;
  const STATES = ["late", "early", "takeoff", "lateBreak", "earlyBreak", "takeoffBreak"];
  const VAL = {
    35: { C1: [28.0, 7.3, 46.1, 31.1, 10.2, 48.5], C2: [0.0, 0.0, 2.2, 3.0, 0.0, 6.3], C3: [19.2, 3.6, 34.0, 23.7, 7.4, 38.0], C4: [34.1, 9.9, 55.2, 36.3, 12.8, 56.4], C5: [4.0, 0.0, 7.9, 7.4, 0.5, 12.0] },
    45: { C1: [42.5, 13.6, 65.8, 43.2, 16.8, 65.8], C2: [2.8, 0.0, 7.3, 6.1, 0.5, 9.3], C3: [31.4, 9.0, 50.8, 34.0, 12.2, 52.2], C4: [50.2, 16.2, 77.5, 50.0, 20.1, 75.4], C5: [9.4, 0.0, 14.8, 12.0, 3.1, 19.9] },
    55: { C1: [56.3, 19.1, 85.1, 55.2, 23.1, 82.0], C2: [6.8, 0.0, 11.6, 8.2, 2.5, 14.1], C3: [43.2, 14.2, 66.7, 44.0, 17.6, 66.2], C4: [65.7, 23.8, 99.1, 62.8, 27.1, 93.5], C5: [14.6, 2.1, 22.0, 17.4, 5.8, 27.1] },
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
  return { IPO, SCALE, STATES, VAL, cell, value, weights, price };
})();
