# El Niño Probability Tracker, week of 2026-11-09

Internal use.

Target peak season: **DJF 2026-27**. CPC's longest-lead strength bin is NDJ 2026-27, used as the proxy for the DJF peak.

## 1. Headline probabilities

Peak Niño 3.4 (traditional ONI), DJF 2026-27 / NDJ 2026-27.
Headline numbers below are CPC-derived after translating from RONI bins to traditional ONI thresholds, then fitting a skew-normal distribution to the nine bin probabilities and evaluating its survival function at each threshold. RONI-to-traditional-ONI offset is +1.00°C, the live tropical-mean SST anomaly observed for the week of 2026-11-04 (CPC). ECMWF SEAS5 member counts in caveat 2 are a second quantitative cross-check.

- **At least moderate (>+1.0°C peak)**: 99%
- **Strong (>+1.5°C peak)**: 99%
- **Very strong / super (>+2.0°C peak)**: 99%
- **1997/2015 magnitude (>+2.5°C peak)**: 99% (6-model consensus; CPC anchor withdrawn, 96% of CPC's mass sits in the open-ended >=2.0 bin with only 1 populated bounded bin(s), so the fitted tail above 2.0 is not identified by the table)
- **Beyond instrumental record (>+3.0°C peak)**: 93% (6-model consensus; CPC anchor withdrawn, 96% of CPC's mass sits in the open-ended >=2.0 bin with only 1 populated bounded bin(s), so the fitted tail above 2.0 is not identified by the table)
- **Far beyond record (>+3.5°C peak)**: 46% (6-model consensus; CPC anchor withdrawn, 96% of CPC's mass sits in the open-ended >=2.0 bin with only 1 populated bounded bin(s), so the fitted tail above 2.0 is not identified by the table)
- **Nothing to compare it to (>+4.0°C peak)**: 17% (6-model consensus; CPC anchor withdrawn, 96% of CPC's mass sits in the open-ended >=2.0 bin with only 1 populated bounded bin(s), so the fitted tail above 2.0 is not identified by the table)

Headline values use the v1.8 smoothed estimator: a CPC anchor (monthly cadence) plus a deflection toward an equal-weight multi-model consensus (ECMWF SEAS5 + the NMME suite). The consensus carries weight 0.85, so the headline is consensus-led with CPC as a minor anchor. This replaces the v1.5 SEAS5-only deflection (weight 0.2) and was adopted because a multi-model consensus past the spring predictability barrier, corroborated by subsurface heat and WWB peak amplitude, is more informative than CPC's lagging monthly table alone. The anchor and consensus are shown alongside the smoothed value. See methodology.html for the full rule and the rationale.

**Source-by-source check (qualitative where strength bins aren't broken out):**

- NOAA CPC strength table, NDJ 2026-27 (RONI): super 96%, strong 4%, moderate 0%, weak El Niño 0%, neutral 0%, La Niña 0%. Issued 2026-10-08.
- IRI plume, DJF 2026-27: El Niño 100%, neutral 0%, La Niña 0%. Issued 2026-10-19. Strength not broken out in the public Quick Look.
- BoM ENSO Outlook, issued 2026-11-10: El Niño continues; positive IOD underway. Categorical only.
- ECMWF SEAS5, run 2026-11-01: 51-member SEAS5 ensemble, peak month 2027-01: median Niño 3.4 anomaly +4.12 deg C (single month); 51/51 members above +1.5 (~100% above +2.0, ~100% above +2.5). Last lead 2027-04: median +3.10 deg C.

**Caveats this issue:**

1. The +2.5°C bucket carries a 95-100% range. It comes from a bootstrap that perturbs CPC's published bin probabilities by Gaussian noise (sigma 1 percentage point, matching CPC's whole-percent reporting precision) and refits the skew-normal each time. The range therefore reflects reporting-quantization uncertainty in CPC's table, not underlying forecast uncertainty.
2. ECMWF SEAS5 vs CPC, upper tail above +2.5°C trad ONI: SEAS5 has 50/51 members (98%) at 2027-04 (max available lead). CPC's NDJ 2026-27 bucket lands at 95-100%. We subtract SEAS5's own model climatology, which removes its known ENSO warm bias; an observational-climatology subtraction would put SEAS5 higher still. Real disagreement to surface, not a number to average.
3. Forecast skill note: mid-year forecasts for the DJF peak are past the boreal-spring predictability barrier and carry materially narrower error bars than the April-May issuances did. The remaining uncertainty is concentrated in peak magnitude at the top of the distribution (the +3.0 and +3.5 buckets), not in whether a strong-to-super event occurs.
4. The +3.0°C and +3.5°C buckets are the most model-dependent numbers in the headline. +3.0°C exceeds every event in the instrumental record (1997 +2.37, 2015 +2.59), and it sits beyond CPC's published strength bins (which top out at >=2.0 RONI), so its CPC anchor (None%) is a deep skew-normal tail extrapolation. Under the consensus weighting the +3.0 bucket (93%) is driven mostly by direct model member counts, not that extrapolation. The +3.5°C bucket (46%, added 2026-07-06 once the July SEAS5 run pushed the top of the distribution past where +3.0 discriminates) is even more model-driven: its CPC anchor (None%) is effectively zero (that threshold is ~+3.0 RONI, far past CPC's top bin), so it is almost entirely direct model member counts above +3.5. Read it as 'where the hot models cluster,' not a calibrated probability, and note it leans hardest on the July ECMWF run.

## 2. Physical state panel

| Indicator | Current (week of 2026-11-04) | 1997 same week | 2015 same week |
|---|---|---|---|
| Niño 3.4 weekly (traditional) | +3.3°C | +2.2°C | +2.6°C |
| Niño 3.4 weekly (RONI) | +2.3°C | n/a (pre-RONI) | n/a (pre-RONI) |
| Niño 3 weekly (traditional) | +4.4°C | +3.0°C | +2.7°C |
| Niño 1+2 weekly (traditional) | +5.6°C | +3.7°C | +2.2°C |
| 0-300m heat content anomaly | +3.32°C (CPC monthly, 180W-100W, vs 1981-2010 climo) | +2.56°C | +1.91°C |
| Cumulative westerly wind anomaly since Mar 1 | 1049 m/s·days (CWWA, ERA5 130E-150W, vs 1991-2020 climo) | 1225 | 1000 |

**Regional records** (each region's highest week in CPC's weekly series since Sept 1981, before this year): Niño 1+2 +5.6 against +4.5 (1983-06), +1.1 past it; Niño 3 +4.4 against +3.3 (1997-11), +1.1 past it; Niño 3.4 +3.3 against +3.0 (2015-11), +0.3 past it; Niño 4 +1.5 against +1.7 (2015-11), below it.

**Heat content note:** At +3.32°C, 2026 exceeds both 1997 (+2.56°C) and 2015 (+1.91°C) at the same calendar month, running ahead of either super-event analog at this stage of development.

**CWWA 14-day rate (m/s·days per day, to 2026-11-02):** 2026 +3.6, 1997 +8.2, 2015 +2.6, 2023 +1.8. Below the 4/day watch line. The level above says what has been delivered; this says whether delivery is stalling, which is what a fade looks like. Watch line 4, fade signal 2. Window closes around November: bursts after that mostly cannot reach the NDJ peak.

**CWWA note:** Live ERA5 daily 850 hPa zonal wind through 2026-11-02, area-meaned over 5N-5S, 130E-150W and integrated for positive (westerly) anomalies vs the 1991-2020 same-calendar-day climatology. At the same calendar date, 2026 CWWA (1049) tracks closest to 2015 (1000); other reference years: 1997 (1225), 2023 (264), 2025 (11). Caveat: CWWA is a cumulative-area-mean metric and systematically understates transient localized westerly wind bursts, including those occurring just outside the 5N-5S band. A short intense burst can generate a downwelling Kelvin wave that does substantial physical work even when it barely moves the cumulative integral. For the operational read on whether ENSO development is on track, the surfacing-Kelvin-wave evidence in heat content (above) is at least as informative as this metric. See the WWB row below for the spatial-peak event count and analyst read (v1.7, complementary to CWWA).

**WWB events (spatial-peak detection, v1.7):** 18 westerly wind burst events detected since Mar 1, 2026. Detection: sliding 5x10 deg sub-region area-mean anomaly over 10N-10S, 130E-150W; dual threshold (5 m/s sustained for at least 5 days, peak day above 7 m/s) with peak-detection plus a 10-day recovery interval between events. Analogs (events to same calendar date): 1997 (15), 2015 (15), 2023 (12), 2025 (6).
  - 2026-03-01 to 2026-03-08, 8 days, peak 13.0 m/s, peak day 2026-03-02
  - 2026-03-09 to 2026-03-22, 14 days, peak 18.37 m/s, peak day 2026-03-14
  - 2026-03-23 to 2026-04-06, 15 days, peak 17.38 m/s, peak day 2026-03-31
  - 2026-04-07 to 2026-04-22, 16 days, peak 23.85 m/s, peak day 2026-04-12
  - 2026-05-01 to 2026-05-08, 8 days, peak 9.86 m/s, peak day 2026-05-02
  - 2026-05-19 to 2026-06-04, 17 days, peak 15.26 m/s, peak day 2026-05-26
  - 2026-06-05 to 2026-06-18, 14 days, peak 14.82 m/s, peak day 2026-06-13
  - 2026-06-19 to 2026-06-30, 12 days, peak 15.84 m/s, peak day 2026-06-24
  - 2026-07-01 to 2026-07-12, 12 days, peak 18.69 m/s, peak day 2026-07-07
  - 2026-07-13 to 2026-07-24, 12 days, peak 17.36 m/s, peak day 2026-07-17
  - 2026-07-25 to 2026-08-06, 13 days, peak 20.85 m/s, peak day 2026-07-31
  - 2026-08-07 to 2026-08-20, 14 days, peak 18.48 m/s, peak day 2026-08-13
  - 2026-08-21 to 2026-09-02, 13 days, peak 17.52 m/s, peak day 2026-08-27
  - 2026-09-03 to 2026-09-13, 11 days, peak 20.28 m/s, peak day 2026-09-08
  - 2026-09-14 to 2026-09-27, 14 days, peak 15.83 m/s, peak day 2026-09-18
  - 2026-09-28 to 2026-10-11, 14 days, peak 15.51 m/s, peak day 2026-10-06
  - 2026-10-12 to 2026-10-24, 13 days, peak 24.17 m/s, peak day 2026-10-16
  - 2026-10-25 to 2026-11-02, 9 days, peak 15.11 m/s, peak day 2026-11-01

**Analyst read on WWB row (v1.7).**

Peak amplitude is the primary signal in this row, not the count. 2026's strongest burst to date peaks at 24.2 m/s (peak day 2026-10-16). Full-season peaks for the analog years: 1997: 27.7 m/s, 2015: 29.5 m/s, 2023: 19.0 m/s, 2025: 12.7 m/s.

This lands in super-event territory: 2026's first burst is comparable in magnitude to 1997 and 2015 first bursts, well above what 2023 (sub-event El Niño) and 2025 (neutral / La Niña) produced. Peak amplitude is the strongest quantitative evidence to date that 2026's forcing is structurally aligned with the super-event analogs rather than the weaker recent analogs.

On count: 2026 has 18 events so far; analogs at the same calendar date: 1997 (15), 2015 (15), 2023 (12), 2025 (6). v1.7's peak-detection algorithm with a 10-day recovery interval splits sustained westerly periods into distinct bursts where v1.6 collapsed them. The count is now reasonably comparable across years, but peak amplitude remains the cleaner single number.

## 2b. Multi-model consensus (NMME)

North American Multi-Model Ensemble, init 2026110800 (issued 2026-11-08). Peak Nino 3.4 over Nov 2026 - Feb 2027 (NDJ-DJF), region 5N-5S, 170W-120W. Each cell is the percent of that model's ensemble members whose peak exceeds the threshold. Anomalies are vs each model's own hindcast climatology (same convention as SEAS5).

| Model | Members | Peak ONI (mean) | >+1.0 | >+1.5 | >+2.0 | >+2.5 | >+3.0 | >+3.5 | >+4.0 |
|---|---|---|---|---|---|---|---|---|---|
| NCEP CFSv2 | 32 | 3.18°C | 100% | 100% | 100% | 100% | 100% | 0% | 0% |
| CanESM5 | 20 | 3.50°C | 100% | 100% | 100% | 100% | 100% | 25% | 0% |
| GEM5.2-NEMO | 20 | 4.00°C | 100% | 100% | 100% | 100% | 100% | 100% | 50% |
| NCAR CCSM4 | 10 | 3.05°C | 100% | 100% | 100% | 100% | 60% | 0% | 0% |
| NCAR CESM1 | 10 | 3.47°C | 100% | 100% | 100% | 100% | 100% | 50% | 0% |
| **Consensus (equal model wt)** | 5 models | **3.58°C** | 100% | 100% | 100% | 100% | 92% | 35% | 10% |

**Consensus read:** The multi-model consensus puts 100% of members above +2.5°C (1997/2015 magnitude), and 92% above +3.0°C, which would exceed every event in the instrumental record (1997 +2.37, 2015 +2.59). These are directly-counted member fractions, not tail extrapolations. As of methodology v1.8 the NMME suite feeds the section-1 headline directly: the multi-model consensus deflection blends these models with ECMWF SEAS5 at weight 0.85. This panel shows the per-model breakdown behind that consensus, including the spread between the hot models (CFSv2, NCAR) and the cooler outliers (CanESM5).

**Panel caveats:**

- NMME updates monthly (around the 8th). This init (2026110800) predates the late-May model runs discussed publicly; the next init will capture those.
- Consensus is equal-weighted by model, so small-ensemble models (NCAR CCSM4/CESM1, 10 members each) carry the same weight as larger ones. Member-weighting lowers the upper-tail fractions by a few points. NCAR CESM1 is a known warm outlier.

## 3. Analog tracker

![Analog tracker](analog.png)

Three reference El Niño events (1997-98, 2015-16, 2023-24) vs current 2026-27 trajectory in 3-month-running-mean ONI. Common reference is March 1 of develop year.

**Read this week:** at the JFM tick (month -1 since Mar 1), 2026 sits at -0.4°C, very close to where 1997 was (-0.4°C) and 2023 was (-0.3°C) at the same calendar point. Both went on to become super events. 2015 was already running ahead at +0.6°C in JFM. The takeaway is that JFM position is a weak discriminator; the ramp speed through MAM-AMJ is what matters, and we won't see that until the next 1-2 ONI updates.

Caveat: the analog plot uses 3-month running mean ONI. The current weekly Niño 3.4 (+0.5°C trad, week of Apr 15) is not directly plotted because it's not a 3-month mean. Adding a weekly trajectory to this chart is on the V1.5 list.

## 4. Impact outlook

Aggregation of institutional impact ranges for the developing event. Probabilities below are from named external sources, conditional on the headline strong-to-super case in section 1 materializing.

### Mediterranean

Spain, Portugal, Italy, Greece, southern France. Probability of severe summer 2026 heat and drought: high, >70% Iberia, ~65% Italy/Greece/southern France. The 2024 July Mediterranean heatwave was characterized by World Weather Attribution as "virtually impossible without human-caused climate change". A 2003-magnitude European heat event (~70,000 excess deaths) is rated medium probability (~25-30%) on a strong El Niño compounded with the multi-year Mediterranean drought baseline.

### Amazon basin

Probability of major drought 2026: high (>70%); probability of fire season exceeding 2024 hotspot levels: medium-high (~50%). NASA SERVIR characterized the 2023-24 drought magnitude as "roughly double" the 2015-16 event. The 2024 fire season produced a 76% increase in hotspots vs 2023.

### Australia and the Great Barrier Reef

Probability of severe bushfire season austral summer 2026-27: high (>65%); GBR mass bleaching: very high (>85%); agricultural drought: high (>70%). The reef has bleached six times since 2016; another super event makes a sixth-in-eight-years bleaching baseline. Australian winter wheat is the cleanest El Niño short on record, with declines of 16% to 46% under prior strong events (1965, 1977, 1982, 1994, 1997, 2023).

### Southern Africa

Probability of major drought repeat: ~70% if rains arrive late, per OCHA framing of the 2023-24 baseline ("worst impacts in 40 years"). Probability of a humanitarian appeal exceeding $5 billion: medium-high (~50%). Six SADC countries declared emergency in 2024; back-to-back is the asymmetric humanitarian risk.

### India and South Asia

IMD's April 2026 monsoon outlook is 92% of the long-period average, the first below-normal April call since 2015. Of 16 historical El Niño years since 1950, 7 produced below-normal Indian monsoons (IMD MMCFS). Pre-monsoon heat already reached 43.8°C at Akola in mid-April 2026.

### United States

California atmospheric river season: above-normal Pacific storm count winter 2026-27 high (~70%), with ~50% probability of a major atmospheric river damage event January-March 2027. Pacific Northwest: warmer-drier winter (~70%) with significant 2026 fire season (~50%). Atlantic hurricane season: high probability (~70%) of below-normal activity from El Niño wind shear, partially offset by warm Atlantic SSTs (2023 produced 20 named storms despite an El Niño base state). Southern Plains drought relief: low-medium (~25-30%); the 2023-24 super event underdelivered there.

### Southeast Asia

Significant drought in Indonesia: high (>70%); palm oil production decline: medium-high (~55%). The 2015-16 super event delivered a 13.2% Malaysian palm oil production decline at a 12-month lag. Vietnamese coffee output fell 20% in 2023-24.

### Global coral

The 2023-25 fourth global bleaching event already affects ~84% of world reefs (International Coral Reef Initiative, April 2025). Continued mass bleaching across all tropical basins is essentially certain into 2026-27.

## 5. Editorial layer

### What changed week-over-week

**RONI->trad ONI offset changed: +0.9°C -> +1.0°C.** This shifts headline buckets even without underlying probability changes; flag in editorial.

**New agency releases since last issue:**

- **ecmwf**: prior issued 2026-10-01, now issued 2026-11-01.
- **bom**: prior issued 2026-10-27, now issued 2026-11-10.
- **nmme**: prior issued 2026-10-08, now issued 2026-11-08.
    - consensus above +3.0: 98% -> 92% (Delta -6)
    - consensus above +3.5: 59% -> 35% (Delta -24)
    - consensus above +4.0: 16% -> 10% (Delta -6)

**Unchanged since last issue:** cpc_strength, iri.

**Physical state deltas:**

- nino34_weekly_traditional: 3.4 -> 3.3 (delta -0.1)
- nino34_weekly_roni: 2.5 -> 2.3 (delta -0.2)
- heat_content_0_300m_estimate: 3.36 -> 3.32 (delta -0.04)
- cwwa_ms_days: 1026.78 -> 1048.58 (delta +21.8)
- wwb_events_since_mar1: 17 -> 18 (delta +1)

**New WWB event since last issue (spatial-peak detection):**

- 2026-10-25 to 2026-11-02, 9 days, peak 15.11 m/s, peak day 2026-11-01

### Analyst read

> **AUTO-GENERATED:** the prose below is written by Claude from this week's diff and physical state. Review before quoting externally; edit freely if the analysis warrants it.

**(Fallback prose: API call failed. Falling back to mechanical summary of the diff. Replace before quoting.)**

This week's brief was generated without analyst commentary because the editorial generator could not reach the Anthropic API. The auto-diff above is the floor; please read it directly and add interpretation manually for any week where the deltas matter materially.

### Source freshness this issue

- **cpc_strength**: fetched live, issued 2026-10-08.
- **oisst_weekly**: fetched live, issued 2026-11-04.
- **heat_content**: fetched live, issued 2026-10-31.
- **iri**: fetched live, issued 2026-10-19.
- **bom**: fetched live, issued 2026-11-10.
- **ecmwf_seas5**: fetched live, issued 2026-11-01.
- **era5_wwe**: fetched live, issued 2026-11-02.
- **era5_burst**: fetched live, issued 2026-11-03.
- **oni_history**: fetched live, issued 2026-10-31.
- **nmme**: fetched live, issued 2026-11-08.

---

*Generated by run_brief.py from sources.py + probs.py + analog.py. Methodology version 1.14. RONI offset +1.00°C (live, week of 2026-11-04). Next issue: Mon 4 May 2026 (per Monday cadence; first batch run is off-schedule).*
