// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// Two revenue paths from mkt/anthropic-valuation, engine v6 (AI - Compute
// compute-demand-2030 de24b9b, explorer v23): $ a share today, cost of
// capital 10.75% fading to 9.13%, share-based pay expensed, a crash keeping
// compute commitments in full. LOW ties AI's work revenue to the jobs it
// replaces, HIGH follows the labs' own plans. A scenario's value is the two
// blended, each floored at $0 first, except the AGI scenarios, which use the
// labs'-plans path only (statement 20261113-0900). At equal weight this is
// the model's value and Kristjan's reading: $31 at the default weights and a
// 45% share (MKT statement 20261113-1126). /ant-pro lets a reader move the
// weight; /ant does not.
//
// By Anthropic's share of frontier-lab revenue (35, 45, 55%), by world
// C1-C5. Columns, in STATES order:
//   [late, early, takeoff, late + crash, early + crash, takeoff + crash]
window.ANT = (function () {
  const IPO = 74;
  // The price scale's top: the highest value at equal weight is $110.6.
  const SCALE = 150;
  // Weight on the labs' own plans (HIGH): the model's equal weight.
  const HIGH_WEIGHT = 0.5;
  const STATES = ["late", "early", "takeoff", "lateBreak", "earlyBreak", "takeoffBreak"];
  const LOW = {
    35: { C1: [26.4, 9.5, 37.3, 20.5, 6.1, 31.9], C2: [0.5, -3.9, 2.8, -1.8, -5.8, 0.4], C3: [20.1, 6.2, 29.2, 15.3, 3.4, 24.6], C4: [30.9, 12.0, 44.0, 24.4, 8.2, 37.7], C5: [4.1, -2.2, 5.8, 1.1, -4.6, 3.6] },
    45: { C1: [37.2, 15.6, 51.4, 29.9, 11.3, 44.6], C2: [4.2, -1.2, 7.3, 1.3, -3.1, 4.2], C3: [29.2, 11.3, 41.1, 23.1, 7.8, 35.2], C4: [42.9, 18.6, 59.7, 34.9, 14.0, 51.9], C5: [8.7, 1.1, 11.3, 5.0, -1.3, 8.4] },
    55: { C1: [47.2, 21.6, 64.7, 39.1, 16.5, 57.0], C2: [7.8, 1.1, 11.7, 4.3, -1.2, 8.1], C3: [38.1, 16.4, 52.7, 31.0, 12.2, 45.7], C4: [52.3, 25.3, 72.3, 45.0, 19.7, 65.0], C5: [13.4, 3.9, 16.7, 9.0, 1.1, 13.3] },
  };
  const HIGH = {
    35: { C1: [68.3, 9.5, 72.8, 49.2, 6.1, 55.4], C2: [0.5, -3.9, 2.1, -1.8, -5.8, 0.3], C3: [47.5, 6.2, 51.1, 33.1, 3.4, 38.2], C4: [76.6, 12.0, 82.4, 56.6, 8.2, 62.8], C5: [7.8, -2.2, 7.9, 3.5, -4.6, 5.1] },
    45: { C1: [87.2, 15.6, 93.1, 65.2, 11.3, 71.7], C2: [4.2, -1.2, 5.5, 1.3, -3.1, 3.2], C3: [62.5, 11.3, 66.4, 45.9, 7.8, 51.5], C4: [97.6, 18.6, 105.4, 73.5, 14.0, 81.1], C5: [13.5, 1.1, 13.0, 8.1, -1.3, 9.4] },
    55: { C1: [105.2, 21.6, 97.7, 80.0, 16.5, 75.6], C2: [7.8, 1.1, 7.7, 4.3, -1.2, 5.3], C3: [75.6, 16.4, 69.6, 58.1, 12.2, 54.9], C4: [117.8, 25.3, 110.6, 89.6, 19.7, 85.3], C5: [19.2, 3.9, 15.6, 12.7, 1.1, 11.8] },
  };

  // One path, interpolated between the 35/45/55 grid points, not floored.
  function raw(T, world, si, share) {
    const s = Math.min(55, Math.max(35, share)), lo = s <= 45 ? 35 : 45, t = (s - lo) / 10;
    return T[lo][world][si] * (1 - t) + T[lo + 10][world][si] * t;
  }
  // A scenario's value: each path floored at $0 (equity cannot be worth less
  // than nothing), then blended by w, the weight on the labs' own plans.
  // The AGI scenarios take the labs'-plans path whatever the weight.
  const AGI = [2, 5];
  function cell(world, state, share, w) {
    const si = typeof state === "number" ? state : STATES.indexOf(state), h = w == null ? HIGH_WEIGHT : w;
    const hi = Math.max(raw(HIGH, world, si, share), 0);
    if (AGI.includes(si)) return hi;
    return Math.max(raw(LOW, world, si, share), 0) * (1 - h) + hi * h;
  }
  const value = cell;

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
  return { IPO, SCALE, HIGH_WEIGHT, STATES, LOW, HIGH, cell, value, weights, price };
})();
