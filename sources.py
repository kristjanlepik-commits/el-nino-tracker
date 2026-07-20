"""
Inputs for the weekly brief. For V1 first batch, the agency forecasts are
hand-curated from the published bulletins (links in each block). The intent
is to automate fetching once we add a CDS API key and set up parsers for
the CPC strength table HTML and the IRI plume PDF.

Convention: anomalies in degrees C, anomalies vs 1991-2020 climatology
unless explicitly noted. RONI = Relative ONI (NOAA CPC's official index
since Feb 2026); ONI = traditional Niño 3.4 anomalies. Conversion factor
this year is roughly +0.3 from RONI to traditional (i.e., trad = RONI + ~0.3).

Each source block carries an `issued` date. Use the issuance date the
agency stamps on the bulletin, not the date you copied it. This lets the
diffing logic distinguish "CPC unchanged since 9 Apr" from "CPC new
release on 14 May".

Methodology version: bump METHODOLOGY_VERSION any time you change the
conversion math, the analog list, the offset, or any decision that would
make this week's headline non-comparable to last week's.
"""

from __future__ import annotations

from datetime import date, timedelta

METHODOLOGY_VERSION = "1.9"


def _most_recent_monday(today: date | None = None) -> date:
    """Return the most-recent Monday on or before `today` (default: today).

    The cron fires Monday 13:00 UTC, so on a scheduled run this resolves to
    today itself. For manual runs on any other weekday, it lands on that
    week's Monday, matching the operator's mental model of "which week's
    brief is this".
    """
    today = today or date.today()
    return today - timedelta(days=today.weekday())   # Monday=0


# Brief date and target peak season. Computed at module import time so each
# weekly run lands in its own dated directory (briefs/YYYY-MM-DD/) and the
# issue stamp at the top of the brief reflects the current week.
BRIEF_DATE = _most_recent_monday()
TARGET_SEASON = "DJF 2026-27"   # canonical winter peak
NEAREST_CPC_SEASON = "NDJ 2026-27"  # CPC's longest lead in current strength table

# Current RONI-to-traditional ONI offset, estimated empirically from
# 2026 JFM where trad = -0.4 and RONI = -0.7 (source: CPC ENSO Evolution PDF).
# This will drift; revisit each issue.
RONI_TO_ONI_OFFSET = 0.3

# ---------------------------------------------------------------
# Section 1 input: NOAA CPC ENSO Strength Probabilities, May 2026
# Source: https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths/
# Issued 14 May 2026 alongside the ENSO Diagnostic Discussion.
# Probabilities are RONI-based (5N-5S, 170W-120W, minus tropical mean).
# Each row is one 3-month season; values sum to 100 (rounding).
# Update on the 2nd Thursday of each month when CPC re-issues.
#
# May 2026 issuance highlights vs April 9 issuance:
# - MAM 2026 falls out of the table (CPC's 9-row window slides forward).
# - DJF 2026-27 enters the table for the first time at this lead.
# - Probability mass shifts upward at all leads JAS onward; the largest
#   single move is the NDJ 2026-27 super (>=2.0 RONI) bucket from 25%
#   to 37% (+12pp). DJF 2026-27 super = 31%.
# ---------------------------------------------------------------
CPC_STRENGTH = {
    "issued": date(2026, 5, 14),
    "table": {
        # season label : {bin_label: pct, ...}
        # bin_label is in RONI, traditional ~ RONI + 0.3
        "AMJ 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 84, "0.5to1.0": 16, "1.0to1.5": 0, "1.5to2.0": 0, ">=2.0": 0},
        "MJJ 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 18, "0.5to1.0": 72, "1.0to1.5": 10, "1.5to2.0": 0, ">=2.0": 0},
        "JJA 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 8, "0.5to1.0": 52, "1.0to1.5": 37, "1.5to2.0": 3, ">=2.0": 0},
        "JAS 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 4, "0.5to1.0": 30, "1.0to1.5": 48, "1.5to2.0": 17, ">=2.0": 1},
        "ASO 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 2, "0.5to1.0": 17, "1.0to1.5": 41, "1.5to2.0": 31, ">=2.0": 9},
        "SON 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 2, "0.5to1.0": 11, "1.0to1.5": 30, "1.5to2.0": 35, ">=2.0": 22},
        "OND 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 2, "0.5to1.0": 9, "1.0to1.5": 24, "1.5to2.0": 32, ">=2.0": 33},
        "NDJ 2026-27": {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 2, "0.5to1.0": 9, "1.0to1.5": 22, "1.5to2.0": 30, ">=2.0": 37},
        "DJF 2026-27": {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 4, "0.5to1.0": 11, "1.0to1.5": 25, "1.5to2.0": 29, ">=2.0": 31},
    },
}
# CPC publishes 9 overlapping seasons. From May 2026 onward DJF 2026-27
# is in the table, so it is the direct (no-proxy) read for the brief's
# target season. NEAREST_CPC_SEASON below is retained at NDJ for
# continuity through this transition; switching to DJF is queued as a
# separate methodology decision.

# Convenience alias for backward compat with existing probs.py
CPC_STRENGTH_RONI = CPC_STRENGTH["table"]

# ---------------------------------------------------------------
# Section 1 input: IRI ENSO plume, May 2026
# Source: https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
# IRI publishes 3-category probabilities (La Niña / neutral / El Niño)
# but does not publish strength bins directly in the Quick Look.
# Below are the El-Niño-vs-other splits; can't decompose into strength
# without parsing member-level plume data (deferred to V1.5).
# Update around the 19th of each month.
#
# Page-format note (May 19 2026 onward): IRI removed the HTML 3-category
# table; data is now visible only as PNG images plus prose. The fetcher
# parses the prose ("97-98% narrow range" framing) and populates all 9
# seasons with the same tuple. Per-season variation is collapsed by IRI's
# own framing to 1-2 ppt and is not recoverable from prose alone. The
# seed below mirrors that flat-curve assumption for the May 19 issuance.
# ---------------------------------------------------------------
IRI = {
    "issued": date(2026, 6, 22),  # IRI Quick Look June 2026
    "three_cat": {
        # season : (La Niña, Neutral, El Niño) percent
        # Hand-curated from the June 22 prose ("assigned at 100% from JJA
        # through SON... 99% [OND to DJF]... 98% and 97% for JFM and FMA").
        # The live prose parser flat-fills at the max (100); this seed
        # carries the accurate per-season decay.
        "JJA 2026":     (0, 0, 100),
        "JAS 2026":     (0, 0, 100),
        "ASO 2026":     (0, 0, 100),
        "SON 2026":     (0, 0, 100),
        "OND 2026":     (0, 1, 99),
        "NDJ 2026-27": (0, 1, 99),
        "DJF 2026-27": (0, 1, 99),
        "JFM 2027":     (0, 2, 98),
        "FMA 2027":     (0, 3, 97),
    },
}
IRI_3CAT = IRI["three_cat"]   # alias

# ---------------------------------------------------------------
# Section 1 input: ECMWF SEAS5 (qualitative, no API access yet)
# Sources used for qualitative read this week:
#   - Yale Climate Connections, 8 Apr 2026: "For October, roughly half
#     of the ECMWF ensemble is calling for [traditional] Niño 3.4 to
#     exceed +2.5°C."
#   - Pogodnik, 9 Apr 2026: "NMME multi-model mean forecast for late
#     2026 already approaches or exceeds [+2.0°C]."
#   - Infoplaza summary of C3S ensemble: spread "neutral to moderate
#     El Niño" with median at "weak El Niño" (this reads stale; the
#     April Copernicus run looks much warmer per other summaries).
# Action: hard-flag ECMWF as warmer-tail than CPC; do not aggregate
# numerically until we have member-counted CDS pulls.
# ---------------------------------------------------------------
ECMWF = {
    "issued": date(2026, 4, 5),    # April 2026 SEAS5 run
    "summary": (
        "Median ensemble path crosses traditional Niño 3.4 +2.0°C "
        "by autumn. Roughly 50% of members exceed +2.5°C for October. "
        "Implies meaningfully higher upper-tail probabilities than "
        "the CPC RONI strength table for the NDJ peak."
    ),
    "approx_p_above_2.5_oct": 0.50,  # one anchor we have
    "warm_bias_caveat": (
        "ECMWF SEAS5 is known to run warm for ENSO (cf. Tippett et al. "
        "2019; Johnson et al. 2019 SEAS5 paper). Treat the upper-tail "
        "split between CPC and ECMWF as a real disagreement to surface, "
        "not a number to average."
    ),
}
ECMWF_QUALITATIVE = ECMWF   # alias

# ---------------------------------------------------------------
# Section 1 input: BoM ENSO Outlook, week ending 12 April 2026
# Source: https://www.bom.gov.au/climate/enso/
# BoM provides categorical alert + verbal description. Used as a
# qualitative cross-check, not as a quantitative bucket input.
# Update fortnightly.
# ---------------------------------------------------------------
BOM = {
    "issued": date(2026, 4, 15),
    "alert_status": "El Niño Watch (ENSO neutral but warming)",
    "summary": (
        "All models warm to El Niño thresholds by July, with onset "
        "ranging from May to July across model groups. No strength "
        "guidance issued in the fortnightly bulletin."
    ),
    "relative_nino34_week_ending_2026_04_12": -0.27,  # BoM relative index
}
BOM_QUALITATIVE = BOM   # alias

# ---------------------------------------------------------------
# Section 2 input: physical state, week ending ~22 April 2026
# Updates weekly (Mondays).
# ---------------------------------------------------------------
PHYSICAL_STATE = {
    "issued": date(2026, 4, 22),
    "nino34_weekly_traditional": 0.5,    # week centered Apr 15 2026 (IRI)
    "nino34_weekly_roni": -0.3,           # week of Apr 1 2026 (CPC)
    "heat_content_0_300m_estimate": 1.3,  # placeholder; flag in brief
    "heat_content_qualitative": (
        "Above-average and rising. Qualitatively the warmest since "
        "Jun 2023; comparable to spring of 2015, well short of spring "
        "1997. New downwelling Kelvin wave initiated in March 2026."
    ),
    "wwe_count_since_mar1_estimate": 1,   # at least one (TC Maila-aided)
    "wwe_qualitative": (
        "Westerly wind anomalies strengthened in March and early April "
        "2026 in the western Pacific and near the Date Line. McPhaden-"
        "defined count requires ERA5 daily winds; not computed this run."
    ),
}

# Same-week comparisons for 1997 and 2015 (week ~Apr 22 of develop year).
# These are weekly OISST values from NOAA archive; numbers below are
# representative figures from the published CPC weekly time series and
# are used for context, not quantitative attribution.
ANALOG_SAME_WEEK = {
    "1997_apr22_nino34_weekly": -0.1,   # 1997 was still cool/neutral in late April
    "2015_apr22_nino34_weekly": 0.6,    # 2015 was already warming
    "2023_apr22_nino34_weekly": 0.6,    # 2023 similar to 2015
    "1997_apr_heat_content": 0.7,       # 1997 was modest in April, surged through summer
    "2015_apr_heat_content": 1.6,       # 2015 spring was very warm subsurface
    "2023_apr_heat_content": 1.0,
    "1997_wwe_to_apr22": 1,             # 1 westerly burst by late April
    "2015_wwe_to_apr22": 2,             # 2 by late April (very active spring)
    "2023_wwe_to_apr22": 1,
}
