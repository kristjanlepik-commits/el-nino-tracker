# El Niño Probability Tracker, Methodology Overview

This document describes how the weekly El Niño probability brief is
constructed. It is meant for someone reviewing the methodology cold,
without prior context on the project.

## What this is

A weekly internal probability tracker focused on the 2026-27 El Niño
event. The brief reports peak-season strength probabilities (DJF
2026-27, with NDJ used as a proxy when CPC's strength table doesn't
extend that far) and a small set of physical-state observations.

It is an **aggregator**, not an original model. We harmonize forecasts
from publicly published agency outputs into a common framing
(traditional Niño 3.4 ONI), surface disagreements between centers, and
let the reader judge. We do not run any custom statistical or ML model.
The historical sample of super El Niño events is small (n~4) and
under-determined for any classifier or regression that would beat the
agency forecasts.

## Headline buckets

The brief reports four cumulative probability buckets in **traditional
Niño 3.4 ONI** terms (3-month running mean SST anomaly vs 1991-2020
climatology, peak season DJF):

- **At least moderate:** peak ONI > +1.0 °C
- **Strong:** peak ONI > +1.5 °C
- **Very strong / super:** peak ONI > +2.0 °C
- **1997/2015 magnitude:** peak ONI > +2.5 °C

The +2.5 °C bucket is reported as a `lo`-`hi` range when it depends on
how the open-ended top RONI bin is discretized. See "RONI to traditional
ONI" below.

## Sources

Seven publicly-published sources are fetched live each Monday. Each
carries an `issued` date stamped by the agency, distinct from when we
fetched it. The diff layer uses issued dates to distinguish "agency
re-released this week" from "agency stale, we're carrying forward".

| Source | Contributes | Cadence |
|---|---|---|
| NOAA CPC ENSO strength table | Quantitative bin-by-bin probabilities (RONI) for 9 overlapping seasons | Monthly, 2nd Thursday |
| OISST weekly Niño 3.4 | Current weekly traditional-ONI anomaly | Weekly, Mondays |
| CPC heat content index | 0-300m subsurface heat content anomaly, 180W-100W | Monthly |
| IRI ENSO Quick Look | 3-category probabilities (La Niña / Neutral / El Niño) for 9 seasons | Monthly, ~19th |
| BoM ENSO outlook | Australian Bureau categorical alert + summary | Fortnightly |
| ECMWF SEAS5 (via Copernicus CDS) | 51-member Niño 3.4 SST forecast, leads 1-6 | Monthly, ~5th |
| ERA5 cumulative westerly wind anomaly (CWWA) | Cumulative positive 850 hPa zonal-wind anomaly since March 1, m/s · days | Continuous (5-day lag) |

If a fetcher fails, the brief falls back to the last successful cache
for that source, then to a hand-curated seed value, and surfaces the
fallback in a "Source freshness" panel at the bottom of the brief. The
pipeline is designed to never fail to produce a brief on Monday.

## Quantitative aggregation

### RONI to traditional ONI

NOAA CPC switched from traditional ONI to RONI (Relative Oceanic Niño
Index) as the official ENSO index in February 2026. RONI is the
traditional Niño 3.4 SST anomaly minus the tropical-mean SST anomaly,
which removes the global-warming background warming signal from the
ENSO measurement.

For the brief, all headline buckets are stated in **traditional ONI**
because that is what most readers and most analog references (1997-98,
2015-16) are expressed in. By definition the offset
`offset = ONI − RONI = tropical_mean_SST_anomaly`. We compute it
**directly each week** from CPC's published indices: the difference
between the most recent week's traditional Niño 3.4 anomaly
(`wksst9120.for`) and relative Niño 3.4 anomaly (`rel_wksst9120.txt`)
gives the offset, observed live. The brief reports it in the section 1
preamble. The current offset around +0.4 °C reflects the present
tropical-mean warmth; previously a static +0.3 °C had been used and
would have drifted under the warming trend.

The forecast horizon (NDJ 2026-27) introduces a small additional
uncertainty: we use the latest observed weekly offset as the best
estimate for the offset at the target season, on the assumption that
tropical-mean SST anomaly drifts only slowly (the 30-year trend is
~+0.15 °C/decade; seasonal variability is small in the tropics). The
brief flags whether the offset is live-fetched or seeded.

### Bin-interior shape: skew-normal fit, not uniform mass

CPC publishes a strength table in 0.5 °C-wide RONI bins, with the top
bin open-ended at `>= +2.0 °C`. To convert these bin probabilities to
the probability that traditional ONI exceeds a specific threshold (e.g.,
+2.5 °C), we need an assumption about how mass is distributed within
each bin.

The brief fits a **skew-normal distribution** to the nine bin
probabilities (loc, scale, shape; minimized via BFGS to match observed
bin masses) and evaluates the survival function at each headline
threshold. This is more defensible than a uniform-within-bins assumption
because peak Niño 3.4 anomaly distributions are inherently right-skewed
(rare super events sit in the right tail with low probability mass that
a uniform interpolation would misallocate).

Sensitivity range on the +2.5 °C bucket comes from a bootstrap that
jitters each bin probability by Gaussian noise (sigma = 1 percentage
point, matching CPC's whole-percent reporting precision), refits the
skew-normal, and reports the 5th and 95th percentile of the resulting
+2.5 °C survival probabilities. The range therefore captures
**reporting-quantization uncertainty** in CPC's published table; it
does not capture forecast uncertainty in the underlying CPC ensemble or
methodological uncertainty in the choice of distribution family.

### ECMWF SEAS5 cross-check

ECMWF's SEAS5 produces 51 ensemble members per monthly forecast. For
each member at the longest available lead month (typically 6 months
out), we compute the Niño 3.4 area-mean SST and subtract the SEAS5
**model climatology**, computed as the mean across 24 years of
hindcasts (1993-2016, 25 members per year, same start month and lead).
The result is one anomaly per member, in traditional ONI units.

We then count members above {+1.0, +1.5, +2.0, +2.5} °C and report
both the counts and the median.

These ECMWF numbers are presented as a **cross-check to CPC**, not
averaged in. The two centers can disagree materially: the choice to
surface that disagreement rather than smooth it away is deliberate.

### Why model climatology, not observational

ECMWF SEAS5 has a known warm bias in the equatorial Pacific. Subtracting
the model's own climatology removes that bias from the anomaly count;
subtracting an observational climatology (the more common practice in
news summaries) does not. The model-anomaly approach answers "the model
itself thinks this run is X °C above its own typical forecast for this
calendar window," which is a cleaner signal-detection question. The
observational-anomaly approach answers "the model output, evaluated
against the real-world climatology," which mixes signal with the warm
bias.

We use the model approach for the brief's headline numbers and note
the observational comparison would shift the count higher in the
caveat text.

## What is explicitly out of scope

- **No custom statistical or ML model.** As above, sample size argues
  against this.
- **No probability calibration against historical events.** We do not
  retrospectively score the brief's probabilities against observed
  outcomes; the agency forecasts are not long-tracked enough at the
  brief's framing for that to be meaningful.
- **No impact modeling.** We do not model hurricane counts, food
  prices, drought severity, or energy demand. Beginning v1.3, the brief
  does aggregate institutional impact ranges (WMO, IMF, FAO, Allianz,
  Swiss Re, OCHA, NASA SERVIR, IMD, etc.) in an "Impact outlook"
  section; see "Impact aggregation" below for the policy and "What the
  impact section does not do" for the explicit exclusions.
- **No public dashboard or real-time updates faster than weekly.**

## Impact aggregation

Starting in v1.3, the brief includes an "Impact outlook" section after
the analog tracker. This section aggregates institutional impact ranges
for the developing event in the same posture as the headline ENSO
numbers: we surface what major institutions and peer-reviewed regional
analyses are saying, with named sources, and surface disagreement
rather than averaging it away.

**Method.** Regional probabilities are stated as the source states
them (high, medium, ~70%, etc.). When multiple sources address the
same region with materially different ranges, both are surfaced and the
disagreement is noted. The probabilities are conditional on the
headline strong-to-super case from section 1 materializing; we do not
multiply them out, which would overstate confidence given that the
headline probability is itself a 90 / 72 / 45 / 21 distribution across
four buckets.

**Sources.** The institutional sources for the impact section include
WMO, NOAA CPC seasonal outlooks, IMF WEO and the Cashin-Mohaddes-Raissi
(2017) framework, Allianz Research, FAO Food Price Index and Crop
Prospects, Swiss Re sigma, IIF Capital Flows, OCHA and SADC
humanitarian reporting, World Weather Attribution, NASA SERVIR and the
Brazilian Geologic Service, IMD MMCFS, the International Coral Reef
Initiative and NOAA Coral Reef Watch, the IEA Oil Market Report,
IFPRI and IFA fertilizer-trade statistics, Lloyd's Market Association
Joint War Committee, and sell-side framing notes (Goldman, JPMorgan)
cited for analytical framing rather than for asset-price targets.
Cadence ranges from continuous (heat stress, river gauges) to annual
(IFA statistics). The impact section is currently re-curated by hand
each issue (edit `impacts.md` at the project root); there are no
impact fetchers in v1.3.

**Editorial synthesis.** The section ends with one labeled subsection
(currently: "Joint Iran + El Niño shocks") that goes beyond aggregation.
This is the brief's one explicit deviation from aggregator posture.
The label is structurally visible (the public template uses an
`.editorial-synthesis` CSS class with a left border and tinted
background so a cold reader sees immediately where aggregation ends).
The synthesis names a transmission chain that no single source
assembles end to end; it does not assign a pooled probability to the
compound scenario.

## What the impact section does not do

The credibility of this brief depends on holding a strict aggregator
line outside the labeled synthesis. Specifically, the impact section
does not:

- **Assign asset-price targets.** No price targets for crude, gold,
  equity indices, currencies, agricultural futures, or any other
  tradable instrument. The sources we cite (Goldman, Allianz, IMF) do
  publish such targets; we do not reproduce them as endorsements.
- **Issue trade recommendations.** No long-X / short-Y views, no
  portfolio construction, no ETF or specific-security mentions, no
  options structures or hedge ratios.
- **Advocate for any digital asset or alternative store of value.**
  Bitcoin, gold, and other inflation-hedge candidates are out of scope
  as recommendations even when source documents discuss them.
- **Forecast specific harvest tonnage or commodity-balance numbers.**
  USDA, FAO, ICCO, Czarnikow, Cocoaintel and similar bodies publish
  point estimates; we cite them but do not issue our own.
- **Take sides on US or other domestic political horse-race
  questions.** Climate salience and election-year framing are mentioned
  only where peer-reviewed political-science or institutional sources
  have discussed them first.

The reason for these exclusions is reader-specific. The brief is read
by climate scientists and policy-elite audiences who lose trust the
moment the prose resembles a sell-side trade note or a political
column. The aggregator posture is what makes the synthesis paragraph
credible. The synthesis paragraph is the only place that posture is
suspended, and it is structurally labeled.

## Known limitations

1. **Spring predictability barrier.** Forecasts issued in April and May
   for the following peak season carry materially wider error bars than
   what we'll see by July or August. All current numbers are preliminary
   in a way that won't be true later in the year.
2. **CWWA in place of WWE event counting.** The brief originally
   reported a discrete count of westerly wind events using a simplified
   area-mean criterion (≥5 m/s sustained ≥5 days). In v1.2 we
   replaced that with a continuous Cumulative Westerly Wind Anomaly
   index (CWWA) over 5N-5S, 130E-150W (the standard equatorial WWE
   source domain): the running sum of positive daily 850 hPa zonal
   wind anomalies vs the 1991-2020 same-calendar-day climatology,
   from March 1 of the develop year. The chart panel below the ONI
   analog plot overlays the 2026 CWWA against 1997, 2015, 2023, and
   2025 reference curves at the same calendar offset. Limitation: the
   cumulative integral does not preserve which dates carried most of
   the forcing, only the running total. A discrete spatial-peak event
   count (Gemini's full method per WWE follow-up) is on the V2 list.
3. **Heat content climatology mismatch.** CPC's published heat content
   series uses a 1981-2010 climatology, while the rest of the brief uses
   1991-2020. Difference is small at current magnitudes (~0.1-0.3 °C)
   and the value enters the brief qualitatively, not in any headline
   probability.
4. **No formal uncertainty propagation.** The `lo`-`hi` range on the
   +2.5 °C bucket comes from a single discretization assumption (the
   open-ended top bin width). It does not reflect uncertainty in the
   RONI offset, in the bin-interior interpolation, or in the agency
   forecasts themselves.
5. **Forecast-horizon offset stability.** The offset is now fetched live
   each week, but applied unchanged to the target season several months
   ahead. Tropical-mean SST anomaly varies on inter-annual timescales
   that are smaller than seasonal Niño 3.4 swings, but a residual ±0.05
   to ±0.10 °C uncertainty over an 8-month horizon translates into ±1
   to ±2 percentage point shifts in the upper-tail headline buckets.
6. **Distribution-family choice.** The skew-normal is one defensible
   right-skewed family; generalized extreme value (GEV) and log-normal
   would also fit. The brief commits to skew-normal for tractability
   and predictability of fit; alternative families are not currently
   reported as a sensitivity range.
7. **Single-model ensemble breadth.** Our forecast cross-check pulls
   from one model (ECMWF SEAS5, 51 members) and reports the 5-95
   percentile band as the visualization of forecast uncertainty. This
   captures *initial-condition* uncertainty (member-to-member
   differences in starting state) but not *structural* uncertainty
   (different ocean-atmosphere coupling, parameterizations, and bias
   characteristics across forecast centers). A multi-model pool
   (CFSv2, JMA, UKMO, NMME, etc., as on the Climate Brink dashboard)
   captures both, and at October 2026 the multi-model 5-95 spread is
   roughly three times wider than SEAS5's alone (a ~3°C span vs our
   1°C). The single-model fan in the chart is therefore an
   over-confident representation of total forecast uncertainty. The
   central tendency is similar (within ~0.1°C of multi-model median
   in observational-anomaly terms); the spread understatement is the
   live methodological gap.
8. **Forecast horizon limit.** ECMWF SEAS5 system 51 publishes 6-7
   leads operationally, so an April issue cannot reach the DJF
   2026-27 target peak season directly. Each successive monthly run
   extends the visible window forward; full DJF coverage from SEAS5
   alone arrives with the August 2026 brief. Public dashboards using
   multi-model pools (CFSv2 and JMA both have 9-month leads) reach
   January 2027 from an April issue. Adding a longer-lead second
   model (CFSv2 the cleanest candidate, accessed via the same CDS
   API with `originating_centre=ncep, system=2`) is queued for V2,
   primarily for the breadth argument in #7 above rather than the
   horizon argument alone.

## Snapshot and diff machinery

Each issue freezes the input state to a JSON snapshot. The next issue
loads the prior snapshot and computes:

- Per-source `issued` date deltas (new release vs unchanged)
- Bin-by-bin probability deltas for CPC's NDJ row when it re-issues
- Three-category deltas for IRI's DJF row when it re-issues
- Numerical deltas for the physical state panel

The methodology version (`METHODOLOGY_VERSION`, currently 1.0) is bumped
any time the conversion math, RONI offset, analog list, or bucket logic
changes. When a snapshot loaded for diffing has a different methodology
version, the brief flags this loudly so the reader knows headline
numbers are not strictly week-over-week comparable across the change.

## What a reviewer should focus on

If you are reviewing this for methodological soundness, the highest-
value places to push back are:

1. **Forecast-horizon validity of the live offset.** We use the
   most-recent observed tropical-mean SST anomaly as the offset for
   the target season several months ahead. Is that defensible, or
   should we project a seasonally-resolved tropical-mean trajectory?
2. **Skew-normal as the parametric family.** Is this the right shape
   for CPC's nine-bin probability distribution at the upper tail?
   Generalized Pareto (for the tail alone) or GEV (full distribution)
   are alternatives we did not adopt. Should we report a sensitivity
   range across families instead of just the bootstrap?
3. **The bootstrap range.** Sigma = 1 percentage point Gaussian noise
   on bin probabilities matches CPC's reporting precision but does
   not capture true forecast uncertainty (which is much larger).
   Should the brief surface a separate "forecast uncertainty" range,
   and how would we estimate it? See limitation #7 (single-model
   ensemble breadth) for the related concern on ECMWF.
4. **The model-vs-observational climatology choice for ECMWF.** Is
   "model anomaly" the right framing for a "what's the chance peak
   ONI exceeds X" question, given the question is observational by
   construction? Or should we report both and let the reader choose?
5. **The bucket thresholds (+1.0/+1.5/+2.0/+2.5 °C).** Are these the
   right cuts for the audience the brief is written for?
6. **The decision to surface CPC vs ECMWF disagreement rather than
   average them.** Pros and cons of pooling vs surfacing?

What we are *not* asking for is predictive-skill review of any
individual agency forecast (we did not produce any of them) nor
calibration evidence (we are not trying to outperform the agency
median).

## Methodology change log

- **1.0** (2026-04-26): Initial methodology. Static +0.3 °C RONI offset.
  Linear interpolation within bins; uniform-mass assumption; lo-hi range
  on +2.5 bucket from varying assumed top-bin width (0.4-1.3 °C).
- **1.1** (2026-04-26): Two changes following external methodology
  review. Live RONI offset computed each week as `traditional weekly
  Niño 3.4 anomaly − relative weekly Niño 3.4 anomaly` from CPC's
  paired indices files; this equals the tropical-mean SST anomaly by
  definition and avoids the drift inherent to a static estimate over
  the 8-month forecast horizon. Within-bin redistribution switched
  from uniform-mass-and-vary-bin-width to a skew-normal fit on the
  nine bin probabilities, evaluated by survival function at each
  headline threshold; lo-hi range on +2.5 bucket now comes from a
  bootstrap that perturbs CPC's whole-percent bin probabilities by
  Gaussian noise.
- **1.2** (2026-04-26): Replaced the discrete WWE event count with a
  continuous Cumulative Westerly Wind Anomaly (CWWA) index over
  5N-5S, 130E-150W (domain shifted west and contracted east relative
  to the v1.1 area, per literature on WWE source regions). CWWA is
  the running sum of positive daily 850 hPa zonal wind anomalies
  since March 1 of the develop year, expressed in m/s · days. The
  analog chart now has a second panel overlaying the 2026 CWWA
  trajectory against 1997, 2015, 2023, and 2025 reference curves.
  Replacing a count metric with a continuous index addresses the
  reviewer concern that count-based metrics discard intensity data
  and tend to undercount the persistent westerly forcing that drives
  Kelvin-wave excitation.
- **1.3** (2026-04-26): Added an "Impact outlook" section after the
  analog tracker, aggregating institutional regional impact ranges
  (WMO, IMF, FAO, Allianz, Swiss Re, OCHA, NASA SERVIR, IMD, ICRI,
  IEA, IFPRI/IFA, Lloyd's JWC, plus sell-side framing notes). Section
  ends with a structurally labeled "Editorial synthesis: joint Iran +
  El Niño shocks" subsection naming the Hormuz to sulfur to fertilizer
  to El Niño-crops transmission chain. Two new methodology sub-sections
  spell out the aggregation method and the explicit exclusions (no
  asset-price targets, no trade recommendations, no specific harvest
  tonnage forecasts). Impact content is curated by hand each issue in
  `impacts.md` at the project root; no impact fetchers in v1.3.

---

*Methodology version 1.3. RONI offset fetched live each week from CPC.
ECMWF anomaly subtracts SEAS5 model climatology (1993-2016 hindcasts).
WWE forcing tracked via CWWA over 5N-5S, 130E-150W. Impact section
added v1.3 as institutional aggregation plus labeled editorial synthesis.*
