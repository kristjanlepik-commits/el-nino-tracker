"""IMERG drift test, exactly as pre-registered in floods/prereg/imerg_drift_test.md.

Does IMERG Late hold rain records more often in recent years than chance?
If so, the satellite record is biased toward the present and would
manufacture records. The rule below was committed before the data existed;
changing it after seeing a result would void the test.

Run:  .venv/bin/python floods/drift_test.py
Self-test:  .venv/bin/python floods/drift_test.py --selftest
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = [("01-10", "01-16"), ("03-10", "03-16"), ("05-10", "05-16"),
           ("07-10", "07-16"), ("09-10", "09-16"), ("11-10", "11-16")]
YEARS = list(range(2001, 2026))
SPLIT = 2014            # GPM Core Observatory launched February 2014
FLOOR_MM = 1.0
NPERM = 10_000
ALPHA = 0.05


def shares(grids, years, land):
    """Record share per year for one window: the fraction of eligible land
    cells where that year holds the single maximum weekly total."""
    tot = np.stack([grids[str(y)] for y in years])            # (n, lon, lat)
    val = np.stack([grids[f"{y}_validdays"] for y in years])
    ok = land & (val == 7).all(axis=0)
    mx = tot.max(axis=0)
    top = tot == mx
    ok &= (mx >= FLOOR_MM) & (top.sum(axis=0) == 1)
    n = int(ok.sum())
    return np.array([top[k][ok].mean() for k in range(len(years))]), n


def stat(sh, years):
    y = np.array(years)
    return sh[y >= SPLIT].mean() - sh[y < SPLIT].mean()


def run(windows_data, rng):
    """windows_data: list of (label, years, share_vector, n_cells)."""
    s_obs = sum(stat(sh, yrs) for _, yrs, sh, _ in windows_data)
    perm = np.empty(NPERM)
    for k in range(NPERM):
        perm[k] = sum(stat(rng.permutation(sh), yrs) for _, yrs, sh, _ in windows_data)
    p_present = float((perm >= s_obs).mean())
    p_past = float((perm <= s_obs).mean())
    return s_obs, p_present, p_past


def selftest():
    """A check that has only ever passed is untested. Prove this one can fail."""
    rng = np.random.default_rng(1)
    def fake(bias):
        out = []
        for lab in range(6):
            w = np.exp(bias * (np.array(YEARS) - 2013))   # bias > 0 favours recent years
            sh = rng.dirichlet(w * 40)
            out.append((lab, YEARS, sh, 5000))
        return out
    for name, bias, want in (("pure noise", 0.0, "PASS"), ("planted recent bias", 0.04, "FAIL")):
        s, pp, _ = run(fake(bias), np.random.default_rng(2))
        got = "FAIL" if pp < ALPHA else "PASS"
        print(f"  {name:<20} S={s:+.4f} p={pp:.4f} -> {got}   expected {want}   "
              f"{'ok' if got == want else 'WRONG'}")
        if got != want:
            sys.exit("SELFTEST FAILED: the test does not behave as designed")
    print("  self-test passed: the test can fail and can pass")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    land = np.load(os.path.join(HERE, "data", "landmask_0p5deg.npy"))
    wd, notes = [], []
    for s, e in WINDOWS:
        f = os.path.join(HERE, "data", f"imerg_global_week_{s}_{e}.npz")
        if not os.path.exists(f):
            sys.exit(f"INCOMPLETE: {f} missing; the pre-registered test needs all six windows")
        g = dict(np.load(f))
        yrs = [y for y in YEARS if str(y) in g]
        miss = sorted(set(YEARS) - set(yrs))
        if miss:
            notes.append(f"{s}..{e}: years excluded by the fetcher for a missing day: {miss}")
        sh, n = shares(g, yrs, land)
        wd.append((f"{s}..{e}", yrs, sh, n))

    s_obs, p_present, p_past = run(wd, np.random.default_rng(20261005))
    by_year = {y: float(np.mean([sh[yrs.index(y)] for _, yrs, sh, _ in wd if y in yrs]))
               for y in YEARS}
    rho, prho = spearmanr(list(by_year), list(by_year.values()))
    verdict = "FAIL" if p_present < ALPHA else "PASS"

    print(f"windows: {len(wd)}   chance share per year: {1/len(YEARS):.1%}")
    for lab, yrs, sh, n in wd:
        y = np.array(yrs)
        print(f"  {lab}: {n:>6} land cells, share 2001-13 {sh[y < SPLIT].mean():.2%}, "
              f"2014-25 {sh[y >= SPLIT].mean():.2%}")
    for x in notes:
        print("  NOTE", x)
    print(f"\nS = {s_obs:+.4f}   p(biased to present) = {p_present:.4f}   "
          f"p(biased to past) = {p_past:.4f}")
    print(f"rank correlation, year vs mean record share: {rho:+.2f} (p {prho:.2f})")
    print(f"\nVERDICT: {verdict}" + ("  -- recent years set records more often than chance"
                                     if verdict == "FAIL" else
                                     "  -- no evidence recent years set records more easily"))
    out = {"prereg": "floods/prereg/imerg_drift_test.md", "verdict": verdict,
           "S": s_obs, "p_biased_to_present": p_present, "p_biased_to_past": p_past,
           "spearman_year_vs_share": [float(rho), float(prho)],
           "windows": [{"window": lab, "land_cells": n, "years": yrs,
                        "record_share": [float(v) for v in sh]} for lab, yrs, sh, n in wd],
           "mean_share_by_year": by_year, "notes": notes}
    json.dump(out, open(os.path.join(HERE, "data", "imerg_drift_test.json"), "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
