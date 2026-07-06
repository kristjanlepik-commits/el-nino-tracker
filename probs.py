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
        # v1.8: "beyond instrumental record" bucket. This is a deep
        # skew-normal tail extrapolation (CPC's table tops out at >=2.0
        # RONI), so the CPC anchor here is unreliable; in the consensus
        # headline it is down-weighted to 0.15 and the bucket is driven
        # mostly by direct model member counts above +3.0.
        "record_>3.0":   round(p_above(loc, scale, shape, 3.0 - offset)),
        # Added 2026-07-06: a still-higher bucket, +3.5, once the July
        # SEAS5 run pushed the top of the distribution so far that +3.0
        # was losing discriminating power. The +3.5 CPC anchor is an even
        # deeper extrapolation (~+3.0 RONI), effectively zero, so this
        # bucket is almost entirely model-member-driven. It is the brief's
        # single least-anchored figure; see the caveat in run_brief.py.
        "record_>3.5":   round(p_above(loc, scale, shape, 3.5 - offset)),
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


# ---- v1.5: smoothed headline (CPC anchor + bounded SEAS5 deflection) ----

SMOOTHING_WEIGHT = 0.2     # SEAS5 contributes 20% of the gap to CPC's anchor
SMOOTHING_CAP_PPT = 10.0   # max ±10 ppt deflection per bucket

# ---- v1.8: multi-model consensus deflection -----------------------------
# v1.5 used SEAS5 alone at weight 0.2 with a +-10 ppt cap, deliberately
# small because it was one warm-biased model and the goal was only to
# un-freeze the headline between CPC's monthly re-issues. v1.8 replaces
# that single signal with an equal-weight consensus across all available
# models (SEAS5 + the NMME suite) and raises the weight, because:
#   - it is now a multi-model consensus, not one model, so agreement
#     across independent models is far more informative than one model;
#   - by June we are past the worst of the spring predictability barrier,
#     when seasonal models are most over-confident;
#   - the subsurface heat content and WWB peak-amplitude evidence
#     independently corroborate the hot model consensus.
# CONSENSUS_WEIGHT is the operator-chosen trust the headline places in the
# model consensus vs CPC's calibrated table. At 0.85 the headline is
# consensus-led: CPC is a minor anchor. The deflection is governed by the
# weight (result is always between the anchor and the consensus), so no
# per-bucket cap is applied in consensus mode.
CONSENSUS_WEIGHT = 0.85


def _nmme_consensus_p_above(nmme: dict | None, threshold_oni: float):
    """The NMME equal-model-weight consensus probability above a threshold,
    as a percent, plus the number of NMME models behind it. Returns
    (pct, n_models) or (None, 0) when unavailable.

    Reads the pre-computed `ensemble_frac_above` (the mean across the NMME
    models' member fractions) from the nmme payload, which is on the same
    model-anomaly footing as SEAS5 (each model's anomalies are vs its own
    hindcast climatology), so no RONI offset is applied.
    """
    if not nmme or not nmme.get("ok"):
        return None, 0
    frac = (nmme.get("ensemble_frac_above") or {}).get(f"{threshold_oni:.1f}")
    n = nmme.get("n_models_ok") or 0
    if frac is None or not n:
        return None, 0
    return float(frac), int(n)


def _model_consensus_p_above(seas5_per_lead, nmme, threshold_oni: float):
    """Equal-weight model-consensus probability above a threshold, pooling
    SEAS5 (one model) with the NMME suite (n models). Each model gets equal
    weight, so the consensus is (p_seas5 + n_nmme * p_nmme_mean) / (1 +
    n_nmme). Returns (pct, n_total_models) or (None, 0).

    Falls back gracefully: SEAS5 alone if NMME is missing, NMME alone if
    SEAS5 is missing.
    """
    p_seas5 = _seas5_p_above(seas5_per_lead, threshold_oni) if seas5_per_lead else None
    p_nmme, n_nmme = _nmme_consensus_p_above(nmme, threshold_oni)
    if p_seas5 is None and p_nmme is None:
        return None, 0
    if p_nmme is None:
        return p_seas5, 1
    if p_seas5 is None:
        return p_nmme, n_nmme
    pooled = (p_seas5 + n_nmme * p_nmme) / (1 + n_nmme)
    return pooled, 1 + n_nmme


def _seas5_p_above(seas5_per_lead: list, threshold_oni: float) -> float | None:
    """Fraction of SEAS5 ensemble members exceeding the threshold at the max
    available lead, in traditional-ONI-equivalent terms.

    SEAS5 ensemble anomalies are computed against SEAS5 model climatology,
    which removes the model's mean ENSO warm bias. The resulting anomalies
    are then read as observational-frame anomalies (degrees C above
    observational climatology), so the threshold lookup is direct: no RONI
    offset adjustment is applied. Returns None when per-lead data is
    unavailable.
    """
    if not seas5_per_lead:
        return None
    headline = seas5_per_lead[-1]
    members_above = headline.get("members_above", {})
    member_count = headline.get("member_count")
    if not members_above or not member_count:
        return None
    n_above = members_above.get(f"{threshold_oni:.1f}")
    if n_above is None:
        return None
    return 100.0 * float(n_above) / float(member_count)


def smoothed_headline_buckets(
    strength_table: dict,
    seas5_per_lead: list | None,
    season: str = "NDJ 2026-27",
    offset: float | None = None,
    nmme: dict | None = None,
    weight: float | None = None,
    cap_ppt: float | None = None,
) -> dict:
    """Smoothed headline: CPC anchor with a model deflection.

    v1.8 (consensus mode): when an NMME payload is supplied, the deflection
    uses an equal-weight model consensus (SEAS5 + the NMME suite) at
    CONSENSUS_WEIGHT (0.85), with no per-bucket cap (the weight bounds the
    move; the result is always between the anchor and the consensus).

    v1.5 (fallback mode): when NMME is unavailable, the deflection falls
    back to SEAS5 alone at SMOOTHING_WEIGHT (0.2) with a +-SMOOTHING_CAP_PPT
    cap, exactly as before. The fallback is the conservative direction
    (toward CPC), so a missing NMME pull cannot inflate the headline.

    Per bucket: deflection = weight * (p_model - p_anchor), optionally
    capped; headline = clamp(p_anchor + deflection, 0, 100). Returns a dict
    with mid, anchor, seas5, consensus, n_models, weight, mode, and
    deflection per bucket so the brief can show the math.
    """
    if offset is None:
        offset = S.RONI_TO_ONI_OFFSET
    anchor = cpc_headline_buckets(strength_table, season, offset)
    thresholds = {
        "moderate_>1.0": 1.0,
        "strong_>1.5":   1.5,
        "super_>2.0":    2.0,
        "9715_>2.5":     2.5,
        "record_>3.0":   3.0,
        "record_>3.5":   3.5,
    }
    # Mode selection: consensus when NMME is available, else SEAS5-only.
    consensus_mode = bool(nmme and nmme.get("ok"))
    if consensus_mode:
        eff_weight = CONSENSUS_WEIGHT if weight is None else weight
        eff_cap = cap_ppt   # None -> uncapped
    else:
        eff_weight = SMOOTHING_WEIGHT if weight is None else weight
        eff_cap = SMOOTHING_CAP_PPT if cap_ppt is None else cap_ppt

    out: dict = {}
    for key, threshold in thresholds.items():
        p_anchor = float(anchor[key])
        p_seas5 = _seas5_p_above(seas5_per_lead, threshold) if seas5_per_lead else None
        p_model, n_models = _model_consensus_p_above(seas5_per_lead, nmme, threshold)
        if p_model is None:
            out[key] = {"mid": int(round(p_anchor)),
                        "anchor": int(round(p_anchor)),
                        "seas5": None, "consensus": None, "n_models": 0,
                        "weight": eff_weight, "mode": "anchor_only",
                        "deflection": 0}
            continue
        raw = eff_weight * (p_model - p_anchor)
        applied = raw if eff_cap is None else max(-eff_cap, min(eff_cap, raw))
        smoothed = max(0.0, min(100.0, p_anchor + applied))
        out[key] = {
            "mid": int(round(smoothed)),
            "anchor": int(round(p_anchor)),
            "seas5": int(round(p_seas5)) if p_seas5 is not None else None,
            "consensus": int(round(p_model)),
            "n_models": n_models,
            "weight": eff_weight,
            "mode": "consensus" if consensus_mode else "seas5_fallback",
            "deflection": round(applied, 1),
        }
    return out


if __name__ == "__main__":
    print("CPC RONI->trad headline buckets (NDJ 2026-27 peak):")
    for k, v in cpc_headline_with_uncertainty(S.CPC_STRENGTH_RONI).items():
        if "lo" in v:
            print(f"  {k}: {v['mid']}% (range {v['lo']}-{v['hi']}%)")
        else:
            print(f"  {k}: {v['mid']}%")
