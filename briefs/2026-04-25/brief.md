# El Niño Probability Tracker, week of 2026-04-25

Internal use.

Target peak season: **DJF 2026-27**. CPC's longest-lead strength bin is NDJ 2026-27, used as the proxy for the DJF peak.

## 1. Headline probabilities

Peak Niño 3.4 (traditional ONI), DJF 2026-27 / NDJ 2026-27.
Headline numbers below are CPC-derived after translating from RONI bins to traditional ONI thresholds, then fitting a skew-normal distribution to the nine bin probabilities and evaluating its survival function at each threshold. RONI-to-traditional-ONI offset is +0.40°C, the live tropical-mean SST anomaly observed for the week of 2026-04-15 (CPC). ECMWF SEAS5 member counts in caveat 2 are a second quantitative cross-check.

- **At least moderate (>+1.0°C peak)**: 90%
- **Strong (>+1.5°C peak)**: 72%
- **Very strong / super (>+2.0°C peak)**: 45%
- **1997/2015 magnitude (>+2.5°C peak)**: 21% (range 20-22%, see caveat)

**Source-by-source check (qualitative where strength bins aren't broken out):**

- NOAA CPC strength table, NDJ 2026-27 (RONI): super 25%, strong 26%, moderate 26%, weak El Niño 15%, neutral 8%, La Niña 0%. Issued 2026-04-09.
- IRI plume, DJF 2026-27: El Niño 88%, neutral 11%, La Niña 1%. Issued 2026-04-20. Strength not broken out in the public Quick Look.
- BoM ENSO Outlook, issued 2026-04-14: Increased chance of El Niño later in 2026. Categorical only.
- ECMWF SEAS5, run 2026-04-01: 51-member SEAS5 ensemble for 2026-10: median Niño 3.4 anomaly +2.21 deg C; 51/51 members above +1.5 (~76% above +2.0, ~25% above +2.5).

**Caveats this issue:**

1. The +2.5°C bucket carries a 20-22% range. It comes from a bootstrap that perturbs CPC's published bin probabilities by Gaussian noise (sigma 1 percentage point, matching CPC's whole-percent reporting precision) and refits the skew-normal each time. The range therefore reflects reporting-quantization uncertainty in CPC's table, not underlying forecast uncertainty.
2. ECMWF SEAS5 vs CPC, upper tail above +2.5°C trad ONI: SEAS5 has 13/51 members (25%) at 2026-10 (max available lead). CPC's NDJ 2026-27 bucket lands at 20-22%. We subtract SEAS5's own model climatology, which removes its known ENSO warm bias; an observational-climatology subtraction would put SEAS5 higher still. Real disagreement to surface, not a number to average.
3. Spring predictability barrier: April-May forecasts at any of these centers carry materially wider error bars than what we'll see in July-August. Treat all numbers as preliminary.

## 2. Physical state panel

| Indicator | Current (week of ~22 Apr 2026) | 1997 same week | 2015 same week |
|---|---|---|---|
| Niño 3.4 weekly (traditional) | +0.5°C | -0.1°C | +0.6°C |
| Niño 3.4 weekly (RONI) | +0.1°C | n/a (pre-RONI) | n/a (pre-RONI) |
| 0-300m heat content anomaly | +1.36°C (CPC monthly, 180W-100W, vs 1981-2010 climo) | +0.7°C | +1.6°C |
| WWE count since Mar 1 | 0 (simplified McPhaden, area-mean u850 anomaly > 5 m/s sustained > 5 days) | 1 | 2 |

**Heat content note:** Above-average and rising. Qualitatively the warmest since Jun 2023; comparable to spring of 2015, well short of spring 1997. New downwelling Kelvin wave initiated in March 2026.

**WWE note:** Live ERA5 1991-2020 climatology comparison through 2026-04-21. The simplified criterion (area-mean rather than spatial-peak detection) tends to undercount versus the full McPhaden definition; treat the count as a lower bound.

## 3. Analog tracker

![Analog tracker](analog.png)

Three reference El Niño events (1997-98, 2015-16, 2023-24) vs current 2026-27 trajectory in 3-month-running-mean ONI. Common reference is March 1 of develop year.

**Read this week:** at the JFM tick (month -1 since Mar 1), 2026 sits at -0.4°C, very close to where 1997 was (-0.4°C) and 2023 was (-0.3°C) at the same calendar point. Both went on to become super events. 2015 was already running ahead at +0.6°C in JFM. The takeaway is that JFM position is a weak discriminator; the ramp speed through MAM-AMJ is what matters, and we won't see that until the next 1-2 ONI updates.

Caveat: the analog plot uses 3-month running mean ONI. The current weekly Niño 3.4 (+0.5°C trad, week of Apr 15) is not directly plotted because it's not a 3-month mean. Adding a weekly trajectory to this chart is on the V1.5 list.

## 4. Editorial layer

### What changed week-over-week

This is the first issue under V1. No prior snapshot to diff against; future briefs will surface week-over-week deltas mechanically.

### Analyst read

> **AUTO-GENERATED:** the prose below is written by Claude from this week's diff and physical state. Review before quoting externally; edit freely if the analysis warrants it.

**(Fallback prose: API call failed. Falling back to mechanical summary of the diff. Replace before quoting.)**

This week's brief was generated without analyst commentary because the editorial generator could not reach the Anthropic API. The auto-diff above is the floor; please read it directly and add interpretation manually for any week where the deltas matter materially.

### Source freshness this issue

- **cpc_strength**: fetched live, issued 2026-04-09.
- **oisst_weekly**: fetched live, issued 2026-04-15.
- **heat_content**: fetched live, issued 2026-03-31.
- **iri**: fetched live, issued 2026-04-20.
- **bom**: fetched live, issued 2026-04-14.
- **ecmwf_seas5**: fetched live, issued 2026-04-01.
- **era5_wwe**: fetched live, issued 2026-04-21.

---

*Generated by run_brief.py from sources.py + probs.py + analog.py. Methodology version 1.1. RONI offset +0.40°C (live, week of 2026-04-15). Next issue: Mon 4 May 2026 (per Monday cadence; first batch run is off-schedule).*
