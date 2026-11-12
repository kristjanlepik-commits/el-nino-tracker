// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// Values since 12 Nov evening: AI - Compute's values_equal_weight
// (compute-demand-2030/outputs/ant-stories-facts.json), sent by the Mycelium
// UX desk with Kristjan's "send". Each cell is the equal weight of MKT's low
// and high revenue paths, each floored at $0, at 9.74%, with no free
// commitment haircut (F-20261112-no-free-haircut-equal-weight-23-today) and
// the temporary crash cap off: $23 at the default weights and a 45% share.
// Not Kristjan's own reading, which stands at $27 until he says otherwise. They replace the token x price grid (concept v3),
// which MKT withdrew as the valuation basis.
//
// $ a share today, by Anthropic's share of frontier-lab revenue (35, 45,
// 55%), by world C1-C5. Columns, in STATES order:
//   [late, early, takeoff, late + crash, early + crash, takeoff + crash]
// A cell at $0 is a scenario where debts and compute contracts outweigh the
// business; shareholders get nothing in it.
window.ANT = (function () {
  const IPO = 74;
  // The price scale's top: the highest value is $99.1, so $0 to $100 fits
  // every scenario with the $74 IPO marked (UX).
  const SCALE = 100;
  const STATES = ["late", "early", "takeoff", "lateBreak", "earlyBreak", "takeoffBreak"];
  const VAL = {
    35: { C1: [28.0, 7.3, 46.1, 20.5, 4.0, 38.2], C2: [0.0, 0.0, 2.2, 0.0, 0.0, 0.0], C3: [19.2, 3.6, 34.0, 14.6, 0.9, 27.1], C4: [34.1, 9.9, 55.2, 25.9, 6.3, 46.5], C5: [4.0, 0.0, 7.9, 0.8, 0.0, 5.2] },
    45: { C1: [42.5, 13.6, 65.8, 33.6, 9.5, 56.5], C2: [2.8, 0.0, 7.3, 0.0, 0.0, 4.1], C3: [31.4, 9.0, 50.8, 23.8, 5.6, 42.5], C4: [50.2, 16.2, 77.5, 40.6, 12.3, 66.8], C5: [9.4, 0.0, 14.8, 5.5, 0.0, 11.3] },
    55: { C1: [56.3, 19.1, 85.1, 46.4, 14.9, 74.0], C2: [6.8, 0.0, 11.6, 3.2, 0.0, 8.4], C3: [43.2, 14.2, 66.7, 34.8, 10.2, 57.3], C4: [65.7, 23.8, 99.1, 54.7, 17.8, 86.3], C5: [14.6, 2.1, 22.0, 10.2, 0.0, 17.3] },
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
