// The one data file /ant and /ant-pro both read, so the same answers give
// the same price on both pages. Swap this file to change the valuation
// basis; neither page carries a number of its own.
//
// Two revenue paths from mkt/anthropic-valuation, $ a share today at 9.74%,
// with a crash keeping compute commitments in full
// (F-20261112-no-free-haircut-equal-weight-23-today), as carried in
// AI - Compute's explorer v15: LOW ties AI's work revenue to the jobs it
// replaces, HIGH follows the labs' own plans. A scenario's value is the two
// blended, each floored at $0 first. The pages show the model's equal
// weight (Kristjan: "Model's $23", D-373): $23 at the default weights and a
// 45% share. /ant-pro lets a reader move the weight; /ant does not.
//
// By Anthropic's share of frontier-lab revenue (35, 45, 55%), by world
// C1-C5. Columns, in STATES order:
//   [late, early, takeoff, late + crash, early + crash, takeoff + crash]
window.ANT = (function () {
  const IPO = 74;
  // The price scale's top: the highest value at equal weight is $99.1.
  const SCALE = 100;
  // Weight on the labs' own plans (HIGH): the model's equal weight.
  const HIGH_WEIGHT = 0.5;
  const STATES = ["late", "early", "takeoff", "lateBreak", "earlyBreak", "takeoffBreak"];
  const LOW = {
    35: { C1: [5.6, -10.4, 15.6, -0.3, -13.9, 10.4], C2: [-17.9, -22.4, -15.3, -20.4, -24.0, -17.9], C3: [-0.5, -13.6, 7.9, -5.3, -16.4, 3.4], C4: [9.9, -8.1, 22.0, 3.5, -11.9, 16.0], C5: [-13.7, -20.3, -11.3, -16.9, -22.4, -13.8] },
    45: { C1: [16.0, -4.6, 29.2, 8.8, -8.8, 22.6], C2: [-14.1, -20.0, -10.5, -17.1, -22.0, -13.7], C3: [8.3, -8.7, 19.4, 2.3, -12.2, 13.7], C4: [21.6, -1.6, 37.4, 13.5, -6.3, 29.7], C5: [-8.6, -17.3, -5.2, -12.6, -19.8, -8.3] },
    55: { C1: [26.4, 1.3, 42.7, 17.7, -3.8, 34.7], C2: [-10.2, -17.5, -5.6, -13.8, -19.9, -9.6], C3: [17.1, -3.8, 30.8, 9.9, -7.9, 23.8], C4: [33.0, 4.8, 52.5, 23.5, -0.8, 43.2], C5: [-3.5, -14.2, 1.0, -8.3, -17.2, -2.9] },
  };
  const HIGH = {
    35: { C1: [50.4, 14.7, 76.6, 41.0, 8.0, 66.1], C2: [-2.6, -13.6, 4.5, -7.4, -16.6, -0.8], C3: [38.5, 7.3, 60.1, 29.2, 1.8, 50.9], C4: [58.4, 19.9, 88.4, 48.4, 12.6, 77.1], C5: [7.9, -8.5, 15.8, 1.5, -12.3, 10.4] },
    45: { C1: [68.9, 27.1, 102.5, 58.4, 19.0, 90.4], C2: [5.6, -8.7, 14.7, -0.4, -12.4, 8.2], C3: [54.5, 18.0, 82.1, 45.3, 11.2, 71.3], C4: [78.9, 32.5, 117.6, 67.7, 24.7, 103.9], C5: [18.8, -2.1, 29.5, 11.0, -6.9, 22.6] },
    55: { C1: [86.3, 37.0, 127.4, 75.0, 29.8, 113.2], C2: [13.5, -3.8, 23.1, 6.5, -8.2, 16.9], C3: [69.3, 28.4, 102.6, 59.6, 20.4, 90.8], C4: [98.4, 42.9, 145.7, 85.9, 35.6, 129.5], C5: [29.1, 4.2, 43.0, 20.3, -1.4, 34.6] },
  };

  // One path, interpolated between the 35/45/55 grid points, not floored.
  function raw(T, world, si, share) {
    const s = Math.min(55, Math.max(35, share)), lo = s <= 45 ? 35 : 45, t = (s - lo) / 10;
    return T[lo][world][si] * (1 - t) + T[lo + 10][world][si] * t;
  }
  // A scenario's value: each path floored at $0 (equity cannot be worth less
  // than nothing), then blended by w, the weight on the labs' own plans.
  function cell(world, state, share, w) {
    const si = typeof state === "number" ? state : STATES.indexOf(state), h = w == null ? HIGH_WEIGHT : w;
    return Math.max(raw(LOW, world, si, share), 0) * (1 - h) + Math.max(raw(HIGH, world, si, share), 0) * h;
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
