"""
Harmonize the headline buckets across sources.

Headline buckets are stated in TRADITIONAL Niño 3.4 (ONI) terms:
  - moderate    : peak ONI > 1.0 C
  - strong      : peak ONI > 1.5 C
  - super       : peak ONI > 2.0 C
  - 1997/2015   : peak ONI > 2.5 C

CPC's strength table is RONI-based. We translate using the constant
offset from sources.py (this year ~+0.3 C). The conversion within a
discrete bin is an approximation: we assume the probability mass is
distributed roughly uniformly across each 0.5 C bin and interpolate.
This is rough but transparent.
"""

import sources as S


def roni_bucket_lower(label: str) -> float:
    """Lower edge of a CPC RONI strength bin (return -inf for unbounded)."""
    if label == "<=-2.0":
        return float("-inf")
    if label.startswith("-"):
        # e.g. "-2.0to-1.5" -> lower = -2.0
        return float(label.split("to")[0])
    if label == "neutral":
        return -0.5
    if label.endswith(">=2.0") or label == ">=2.0":
        return 2.0
    # "0.5to1.0", "1.0to1.5", etc.
    return float(label.split("to")[0])


def roni_bucket_upper(label: str) -> float:
    """Upper edge of a CPC RONI strength bin (return +inf for unbounded)."""
    if label == ">=2.0":
        return float("+inf")
    if label == "<=-2.0":
        return -2.0
    if label == "neutral":
        return 0.5
    return float(label.split("to")[1])


def p_above_traditional_oni(season_probs: dict, threshold_oni: float,
                            roni_to_oni: float) -> float:
    """
    Estimate probability traditional ONI > threshold_oni for a given
    CPC RONI strength distribution. Linear interpolation within bins.
    """
    threshold_roni = threshold_oni - roni_to_oni
    total = 0.0
    for label, pct in season_probs.items():
        lo = roni_bucket_lower(label)
        hi = roni_bucket_upper(label)
        if hi <= threshold_roni:
            continue                     # whole bin below threshold
        if lo >= threshold_roni:
            total += pct                 # whole bin above
            continue
        # partial overlap; uniform-density assumption
        if hi == float("+inf") or lo == float("-inf"):
            # tail bins: be conservative, count proportionally to the
            # upper-tail bin width. For the >=2.0 bin we assume mass
            # spans roughly 2.0 to 3.0 C.
            assumed_width = 1.0
            assumed_lo = 2.0 if lo == float("-inf") is False and lo >= 2.0 else lo
            # simpler: assume the bin spans 1.0 C beyond its lower edge
            assumed_lo = lo if lo > -1e9 else hi - 1.0
            assumed_hi = assumed_lo + assumed_width
            frac = max(0.0, (assumed_hi - threshold_roni) / assumed_width)
            frac = min(1.0, frac)
            total += pct * frac
        else:
            width = hi - lo
            frac = (hi - threshold_roni) / width
            total += pct * frac
    return total


def cpc_headline_buckets(season: str = "NDJ 2026-27") -> dict:
    """
    Return CPC-derived probabilities for the four headline buckets,
    converted to traditional ONI using the offset in sources.py.
    """
    probs = S.CPC_STRENGTH_RONI[season]
    return {
        "moderate_>1.0": round(p_above_traditional_oni(probs, 1.0, S.RONI_TO_ONI_OFFSET)),
        "strong_>1.5":   round(p_above_traditional_oni(probs, 1.5, S.RONI_TO_ONI_OFFSET)),
        "super_>2.0":    round(p_above_traditional_oni(probs, 2.0, S.RONI_TO_ONI_OFFSET)),
        "9715_>2.5":     round(p_above_traditional_oni(probs, 2.5, S.RONI_TO_ONI_OFFSET)),
    }


def cpc_headline_with_uncertainty(season: str = "NDJ 2026-27") -> dict:
    """
    Same as cpc_headline_buckets but returns a (lo, mid, hi) range to
    capture the discretization uncertainty within the open >=2.0 RONI bin.

    For trad ONI > 2.5, the range comes from varying the assumed width
    of the >=2.0 RONI bin from 0.7 (steeper decay) to 1.3 (shallower),
    which spans 10-22% of the headline >=2.0 bin sitting above trad 2.5.
    The other thresholds (1.0, 1.5, 2.0) are not sensitive to this
    assumption because they sit at or below the 2.0 RONI edge.
    """
    probs = S.CPC_STRENGTH_RONI[season]
    base = cpc_headline_buckets(season)

    # For >2.5 only, recompute under different assumptions about where
    # the probability mass sits inside CPC's open-ended >=2.0 RONI bin.
    # Width 0.4 = mass concentrated just above 2.0 (steepest decay).
    # Width 1.3 = mass spread out toward 3.3 RONI (shallowest decay).
    # The "best estimate" stays at width=1.0 (uniform to 3.0).
    def above_25_with_width(w: float) -> float:
        threshold_roni = 2.5 - S.RONI_TO_ONI_OFFSET   # = 2.2
        upper_pct = probs[">=2.0"]
        if threshold_roni >= 2.0 + w:
            return 0.0
        if threshold_roni <= 2.0:
            return float(upper_pct)
        return upper_pct * (2.0 + w - threshold_roni) / w

    return {
        "moderate_>1.0": {"mid": base["moderate_>1.0"]},
        "strong_>1.5":   {"mid": base["strong_>1.5"]},
        "super_>2.0":    {"mid": base["super_>2.0"]},
        "9715_>2.5":     {"mid": round(base["9715_>2.5"]),
                          "lo":  round(above_25_with_width(0.4)),
                          "hi":  round(above_25_with_width(1.3))},
    }


if __name__ == "__main__":
    print("CPC RONI->trad headline buckets (NDJ 2026-27 peak):")
    for k, v in cpc_headline_with_uncertainty().items():
        if "lo" in v:
            print(f"  {k}: {v['mid']}% (range {v['lo']}-{v['hi']}%)")
        else:
            print(f"  {k}: {v['mid']}%")
