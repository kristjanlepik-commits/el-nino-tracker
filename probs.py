"""
Harmonize the headline buckets across sources.

Headline buckets are stated in TRADITIONAL Niño 3.4 (ONI) terms:
  - moderate    : peak ONI > 1.0 °C
  - strong      : peak ONI > 1.5 °C
  - super       : peak ONI > 2.0 °C
  - 1997/2015   : peak ONI > 2.5 °C

CPC publishes the strength table in RONI bins. We translate from RONI to
traditional ONI by subtracting the RONI-to-ONI offset, which equals the
tropical-mean SST anomaly. The offset is now passed in as a parameter
(driven by the live OISST fetcher's per-week observation) rather than
read as a fixed constant; sources.RONI_TO_ONI_OFFSET is the seed/fallback
when a live offset is unavailable.

Within-bin probability redistribution: rather than the original
uniform-mass-per-bin assumption (which is convenient but underestimates
the right tail of an inherently right-skewed SST anomaly distribution),
we fit a skew-normal distribution to the nine bin probabilities and
evaluate the survival function at each headline threshold. The
lo-hi range on the +2.5 °C bucket comes from a bootstrap that jitters the
bin probabilities by Gaussian noise (sigma = 1.0 percentage point, the
rough quantization precision of CPC's published table) and refits.

The legacy linear-interpolation API (`p_above_traditional_oni`) is kept
for the `__main__` smoke-test path and for reference.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import skewnorm

import sources as S


# Bin edges in RONI space, ordered low to high.
BINS: list[tuple[float, float, str]] = [
    (-np.inf, -2.0, "<=-2.0"),
    (-2.0, -1.5, "-2.0to-1.5"),
    (-1.5, -1.0, "-1.5to-1.0"),
    (-1.0, -0.5, "-1.0to-0.5"),
    (-0.5,  0.5, "neutral"),
    ( 0.5,  1.0, "0.5to1.0"),
    ( 1.0,  1.5, "1.0to1.5"),
    ( 1.5,  2.0, "1.5to2.0"),
    ( 2.0,  np.inf, ">=2.0"),
]


# ---- Legacy uniform-within-bin interpolation, kept for reference ----

def roni_bucket_lower(label: str) -> float:
    if label == "<=-2.0":
        return float("-inf")
    if label.startswith("-"):
        return float(label.split("to")[0])
    if label == "neutral":
        return -0.5
    if label == ">=2.0":
        return 2.0
    return float(label.split("to")[0])


def roni_bucket_upper(label: str) -> float:
    if label == ">=2.0":
        return float("+inf")
    if label == "<=-2.0":
        return -2.0
    if label == "neutral":
        return 0.5
    return float(label.split("to")[1])


def p_above_traditional_oni(season_probs: dict, threshold_oni: float,
                            roni_to_oni: float) -> float:
    """Legacy linear interpolation; preserved for sanity checks."""
    threshold_roni = threshold_oni - roni_to_oni
    total = 0.0
    for label, pct in season_probs.items():
        lo = roni_bucket_lower(label)
        hi = roni_bucket_upper(label)
        if hi <= threshold_roni:
            continue
        if lo >= threshold_roni:
            total += pct
            continue
        if hi == float("+inf") or lo == float("-inf"):
            assumed_lo = lo if lo > -1e9 else hi - 1.0
            assumed_hi = assumed_lo + 1.0
            frac = max(0.0, min(1.0, (assumed_hi - threshold_roni) / 1.0))
            total += pct * frac
        else:
            width = hi - lo
            total += pct * (hi - threshold_roni) / width
    return total


# ---- Parametric fit (current default) ----------------------------------

def _bin_probs_array(season_probs: dict) -> np.ndarray:
    return np.array([season_probs.get(label, 0) / 100.0
                     for _, _, label in BINS])


def _predicted_bin_probs(loc: float, scale: float, shape: float) -> np.ndarray:
    cdf = lambda x: skewnorm.cdf(x, shape, loc, scale)
    out = []
    for lo, hi, _ in BINS:
        if np.isneginf(lo):
            out.append(cdf(hi))
        elif np.isposinf(hi):
            out.append(1.0 - cdf(lo))
        else:
            out.append(cdf(hi) - cdf(lo))
    return np.array(out)


def _initial_loc(observed: np.ndarray) -> float:
    """Probability-weighted mean of the bin midpoints."""
    midpoints = []
    for lo, hi, _ in BINS:
        if np.isneginf(lo):
            midpoints.append(-2.5)
        elif np.isposinf(hi):
            midpoints.append(2.5)
        else:
            midpoints.append((lo + hi) / 2.0)
    midpoints = np.array(midpoints)
    if observed.sum() <= 0:
        return 0.0
    return float((midpoints * observed).sum() / observed.sum())


def fit_skew_normal(season_probs: dict) -> tuple[float, float, float]:
    """Fit (loc, scale, shape) of a skew-normal that matches the nine bin probabilities."""
    observed = _bin_probs_array(season_probs)

    def loss(params: np.ndarray) -> float:
        loc, scale, shape = params
        if scale <= 1e-3:
            return 1e10
        diff = _predicted_bin_probs(loc, scale, shape) - observed
        return float(np.sum(diff * diff))

    init = np.array([_initial_loc(observed), 0.7, 1.0])
    # BFGS is ~2.5x faster than Nelder-Mead here and converges to a CDF
    # indistinguishable to 0.5 ppt over the ranges we care about.
    result = minimize(loss, init, method="BFGS")
    loc, scale, shape = result.x
    return float(loc), float(max(scale, 1e-3)), float(shape)


def p_above(loc: float, scale: float, shape: float, threshold_roni: float) -> float:
    """Survival function of a fitted skew-normal at the given RONI threshold."""
    return float(100.0 * (1.0 - skewnorm.cdf(threshold_roni, shape, loc, scale)))


def p_above_parametric(season_probs: dict, threshold_roni: float) -> float:
    """Convenience: fit and evaluate in one call. Prefer to fit once and reuse."""
    loc, scale, shape = fit_skew_normal(season_probs)
    return p_above(loc, scale, shape, threshold_roni)


def _bootstrap_p_above(season_probs: dict, threshold_roni: float,
                       n: int = 100, sigma_pct: float = 1.0) -> np.ndarray:
    """Bootstrap by jittering bin probabilities (Gaussian, sigma = 1 ppt)."""
    rng = np.random.default_rng(seed=0)
    out = np.empty(n)
    labels = [label for _, _, label in BINS]
    for i in range(n):
        jittered = {}
        for label in labels:
            base = season_probs.get(label, 0)
            jittered[label] = max(0.0, base + rng.normal(0.0, sigma_pct))
        total = sum(jittered.values())
        if total > 0:
            jittered = {k: 100.0 * v / total for k, v in jittered.items()}
        out[i] = p_above_parametric(jittered, threshold_roni)
    return out


# ---- Public API ---------------------------------------------------------

def cpc_headline_buckets(strength_table: dict, season: str = "NDJ 2026-27",
                         offset: float | None = None) -> dict:
    """Headline buckets from the parametric fit. Offset defaults to S.RONI_TO_ONI_OFFSET."""
    if offset is None:
        offset = S.RONI_TO_ONI_OFFSET
    probs = strength_table[season]
    loc, scale, shape = fit_skew_normal(probs)
    return {
        "moderate_>1.0": round(p_above(loc, scale, shape, 1.0 - offset)),
        "strong_>1.5":   round(p_above(loc, scale, shape, 1.5 - offset)),
        "super_>2.0":    round(p_above(loc, scale, shape, 2.0 - offset)),
        "9715_>2.5":     round(p_above(loc, scale, shape, 2.5 - offset)),
    }


def cpc_headline_with_uncertainty(strength_table: dict, season: str = "NDJ 2026-27",
                                  offset: float | None = None) -> dict:
    """As above plus a bootstrap CI on the +2.5 °C bucket."""
    if offset is None:
        offset = S.RONI_TO_ONI_OFFSET
    probs = strength_table[season]
    base = cpc_headline_buckets(strength_table, season, offset)

    samples = _bootstrap_p_above(probs, 2.5 - offset, n=100, sigma_pct=1.0)
    lo = round(float(np.percentile(samples, 5)))
    hi = round(float(np.percentile(samples, 95)))

    return {
        "moderate_>1.0": {"mid": base["moderate_>1.0"]},
        "strong_>1.5":   {"mid": base["strong_>1.5"]},
        "super_>2.0":    {"mid": base["super_>2.0"]},
        "9715_>2.5":     {"mid": base["9715_>2.5"], "lo": lo, "hi": hi},
    }


if __name__ == "__main__":
    print("CPC RONI->trad headline buckets (NDJ 2026-27 peak):")
    for k, v in cpc_headline_with_uncertainty(S.CPC_STRENGTH_RONI).items():
        if "lo" in v:
            print(f"  {k}: {v['mid']}% (range {v['lo']}-{v['hi']}%)")
        else:
            print(f"  {k}: {v['mid']}%")
