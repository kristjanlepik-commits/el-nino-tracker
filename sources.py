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

from datetime import date

METHODOLOGY_VERSION = "1.0"

# Brief date and target peak season
BRIEF_DATE = date(2026, 4, 25)
TARGET_SEASON = "DJF 2026-27"   # canonical winter peak
NEAREST_CPC_SEASON = "NDJ 2026-27"  # CPC's longest lead in current strength table

# Current RONI-to-traditional ONI offset, estimated empirically from
# 2026 JFM where trad = -0.4 and RONI = -0.7 (source: CPC ENSO Evolution PDF).
# This will drift; revisit each issue.
RONI_TO_ONI_OFFSET = 0.3

# ---------------------------------------------------------------
# Section 1 input: NOAA CPC ENSO Strength Probabilities, Apr 2026
# Source: https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php
# Issued 9 April 2026 alongside the ENSO Diagnostic Discussion.
# Probabilities are RONI-based (5N-5S, 170W-120W, minus tropical mean).
# Each row is one 3-month season; values sum to 100 (rounding).
# Update on the 2nd Thursday of each month when CPC re-issues.
# ---------------------------------------------------------------
CPC_STRENGTH = {
    "issued": date(2026, 4, 9),
    "table": {
        # season label : {bin_label: pct, ...}
        # bin_label is in RONI, traditional ~ RONI + 0.3
        "MAM 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 1,
                         "neutral": 99, "0.5to1.0": 0, "1.0to1.5": 0, "1.5to2.0": 0, ">=2.0": 0},
        "AMJ 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 80, "0.5to1.0": 20, "1.0to1.5": 0, "1.5to2.0": 0, ">=2.0": 0},
        "MJJ 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 39, "0.5to1.0": 56, "1.0to1.5": 5, "1.5to2.0": 0, ">=2.0": 0},
        "JJA 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 21, "0.5to1.0": 53, "1.0to1.5": 24, "1.5to2.0": 2, ">=2.0": 0},
        "JAS 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 13, "0.5to1.0": 38, "1.0to1.5": 37, "1.5to2.0": 11, ">=2.0": 1},
        "ASO 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 10, "0.5to1.0": 27, "1.0to1.5": 36, "1.5to2.0": 21, ">=2.0": 6},
        "SON 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 8, "0.5to1.0": 20, "1.0to1.5": 31, "1.5to2.0": 26, ">=2.0": 15},
        "OND 2026":     {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 7, "0.5to1.0": 16, "1.0to1.5": 27, "1.5to2.0": 27, ">=2.0": 23},
        "NDJ 2026-27": {"<=-2.0": 0, "-2.0to-1.5": 0, "-1.5to-1.0": 0, "-1.0to-0.5": 0,
                         "neutral": 8, "0.5to1.0": 15, "1.0to1.5": 26, "1.5to2.0": 26, ">=2.0": 25},
    },
}
# CPC publishes 9 overlapping seasons; at this lead, NDJ 2026-27 is the
# longest available and is our closest proxy for the DJF 2026-27 peak.

# Convenience alias for backward compat with existing probs.py
CPC_STRENGTH_RONI = CPC_STRENGTH["table"]

# ---------------------------------------------------------------
# Section 1 input: IRI ENSO plume, April 2026
# Source: https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
# IRI publishes 3-category probabilities (La Niña / neutral / El Niño)
# but does not publish strength bins directly in the Quick Look.
# Below are the El-Niño-vs-other splits; can't decompose into strength
# without parsing member-level plume data (deferred to V1.5).
# Update around the 19th of each month.
# ---------------------------------------------------------------
IRI = {
    "issued": date(2026, 4, 16),  # IRI Quick Look mid-Apr 2026
    "three_cat": {
        # season : (La Niña, Neutral, El Niño) percent
        "AMJ 2026":     (0, 30, 70),
        "MJJ 2026":     (0, 12, 88),
        "JJA 2026":     (0, 9, 91),
        "JAS 2026":     (0, 8, 92),
        "ASO 2026":     (0, 7, 93),
        "SON 2026":     (0, 6, 94),
        "OND 2026":     (0, 7, 93),
        "NDJ 2026-27": (0, 8, 92),
        "DJF 2026-27": (0, 10, 90),
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
