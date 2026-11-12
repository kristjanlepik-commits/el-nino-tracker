// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// Values since 12 Nov evening: AI - Compute's values_equal_weight
// (compute-demand-2030/outputs/ant-stories-facts.json), sent by the Mycelium
// UX desk with Kristjan's "send". Each cell is the equal weight of MKT's low
// and high revenue paths, each floored at $0, at 9.74%, with every crash
// cell capped at its no-crash twin (Kristjan, statement 20261112-1900):
// $25 at his weights and a 45% share. They replace the token x price grid (concept v3),
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
    35: { C1: [28.0, 7.3, 46.1, 27.3, 7.3, 44.4], C2: [0.0, 0.0, 2.2, 0.0, 0.0, 2.2], C3: [19.2, 3.6, 34.0, 19.2, 3.6, 33.4], C4: [34.1, 9.9, 55.2, 32.9, 9.9, 52.8], C5: [4.0, 0.0, 7.9, 4.0, 0.0, 7.9] },
    45: { C1: [42.5, 13.6, 65.8, 40.2, 13.6, 62.5], C2: [2.8, 0.0, 7.3, 2.8, 0.0, 7.3], C3: [31.4, 9.0, 50.8, 30.2, 9.0, 48.3], C4: [50.2, 16.2, 77.5, 47.5, 16.2, 73.2], C5: [9.4, 0.0, 14.8, 9.4, 0.0, 14.8] },
    55: { C1: [56.3, 19.1, 85.1, 53.2, 19.1, 80.5], C2: [6.8, 0.0, 11.6, 6.8, 0.0, 11.6], C3: [43.2, 14.2, 66.7, 41.0, 14.2, 63.2], C4: [65.7, 23.8, 99.1, 61.9, 23.4, 93.5], C5: [14.6, 2.1, 22.0, 14.6, 2.1, 22.0] },
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
