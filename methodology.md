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
| ERA5 spatial-peak WWB events | Count + detail of westerly wind bursts (sliding 5x10 deg sub-region area-mean, dual threshold) | Continuous (5-day lag) |

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

### Headline smoothing: CPC anchor with multi-model consensus deflection (v1.8)

CPC reissues the strength table monthly, on the 2nd Thursday with the
ENSO Diagnostic Discussion. Between issuances, the raw skew-normal
output is mathematically frozen for 4-5 weeks, and during that window
new observational evidence and updated model ensembles can move the
underlying probabilities materially. The brief's audience is climate-
curious operators who read it weekly; a static headline reads as a
brief that has stopped tracking the event between CPC's monthly
releases.

We close that gap by **deflecting CPC's anchor probability toward an
equal-weight multi-model consensus.**

For each headline bucket b, given anchor probability `p_anchor[b]`
(the skew-normal-fitted CPC probability above threshold b in
traditional-ONI terms) and the model-consensus fraction `p_model[b]`:

```
deflection[b] = W × (p_model[b] − p_anchor[b])
headline[b]   = clamp(p_anchor[b] + deflection[b], 0, 100)
```

`p_model[b]` is the **equal-weight consensus across all available
models**: ECMWF SEAS5 (one model) and the NMME suite (CFSv2, CanESM5,
GEM5.2-NEMO, NCAR CCSM4, NCAR CESM1). With one SEAS5 model and
`n_nmme` NMME models, the consensus is
`(p_seas5 + n_nmme × p_nmme_mean) / (1 + n_nmme)`. All member fractions
are computed against each model's own hindcast climatology, so they sit
on the same model-anomaly footing and require no RONI offset.

The weight is **W = 0.85**: the headline is consensus-led, with CPC a
minor anchor. No per-bucket cap is applied; the weight bounds the move
(the result always lies between the anchor and the consensus).

When CPC reissues the strength table, `p_anchor` jumps to the new CPC
value and the deflection is recomputed against the new anchor; there
is no carryover. The diff section surfaces the CPC anchor change and
the consensus separately so the reader can see where the motion came
from.

**Why W = 0.85 (the change from v1.5's SEAS5-only W = 0.2):**

v1.5 used SEAS5 alone at W = 0.2 with a ±10 ppt cap, deliberately
small because it was one warm-biased model (Tippett et al. 2019;
Johnson et al. 2019) and the only goal was to un-freeze the headline
between CPC issuances. Three things changed that justify a much
higher weight in v1.8:

- **It is now a consensus, not one model.** Agreement across six
  independent models (SEAS5 + five NMME models) is far more
  informative than any single model, and averaging across them damps
  any one model's idiosyncratic bias.
- **We are past the spring predictability barrier.** Seasonal models
  are most over-confident in boreal spring; by early summer their
  skill rises sharply, so the reason to heavily temper them weakens.
- **Observations corroborate the consensus.** Subsurface heat content
  and the spatial-peak WWB amplitude (both in section 2) independently
  track the super-event analogs, so the hot model consensus is not
  running ahead of the physical state.

For NDJ 2026-27 at v1.8 introduction (CPC issued 2026-05-14; SEAS5 May
run; NMME May 8 init): the +2.5 °C bucket moves from a CPC anchor of
37% to a smoothed 66%, against a six-model consensus of 71%. Under the
superseded v1.5 SEAS5-only estimator the same bucket sat at 45%.

**The W = 0.85 choice is an explicit operator decision** documented
here per our methodology-calls policy. The conservative alternative
(stay nearer CPC) and the aggressive alternative (pure consensus, W = 1,
which drops the CPC anchor entirely) were both considered; W = 0.85
keeps CPC as a real, if minor, anchor so the brief is not a pure
restatement of the hottest models.

**Fallback.** If the NMME consensus is unavailable for an issue (total
fetch failure with no cache), the estimator reverts to the v1.5
SEAS5-only deflection (W = 0.2, ±10 ppt cap). This is the conservative
direction (toward CPC), so a missing NMME pull can never inflate the
headline. The brief states which mode produced the issue's numbers.

**What this is and is not:**

- It IS a multi-model consensus deflection. This is a deliberate change
  from v1.5, which was explicitly not a multi-model pool. The brief is
  now closer to a multi-model average than to CPC alone, by design.
- It is still anchored: CPC supplies the underlying bin probabilities
  and the skew-normal structure; the consensus deflects that anchor, it
  does not replace it.
- It is not a forecast of CPC's next issuance; it captures model and
  observational evidence accumulated since CPC's last release.

**Audit trail:** every headline number can be reconstructed from
(`p_anchor`, `p_seas5`, the NMME consensus, the model count, and `W`),
all reported in the brief per issue. A reviewer can replicate the math
without access to private state.

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

### Spatial-peak westerly wind burst detection (v1.7)

CWWA (above) gives a smooth cumulative scalar but is blind to burst
structure: a 5-day intense burst at 7N generates a Kelvin wave that
50 days of weak equatorial westerlies of the same area-integrated
magnitude would not, yet CWWA scores them similarly. v1.6 added a
complementary discrete-event indicator that captures the burst
structure directly; v1.7 (current) refines the event-detection
algorithm to fix a count-merging issue documented under v1.6.

Method (`fetchers/era5_burst.py`):

1. Pull ERA5 daily 850 hPa zonal wind at 12 UTC over the wider domain
   10N-10S, 130E-150W (broader than CWWA's 5N-5S, per Daniel Swain's
   2026-05-10 observation that productive bursts often sit just
   outside the equatorial band).
2. Build a full-field 1991-2020 same-calendar-day climatology over
   the same domain (chunked monthly, 30y x 1mo per CDS call, six
   chunks total). Cached on disk; re-pulled only when invalidated.
3. For each observation day, compute the full anomaly field
   `obs(lat, lon) - clim(mmdd, lat, lon)`.
4. Slide a 5deg lat x 10deg lon window over the anomaly field; the
   day's "spatial peak" is the maximum area-mean anomaly across all
   window positions (computed via `scipy.ndimage.uniform_filter`
   for efficiency, with edge pixels masked to avoid biased edge
   windows).
5. From the daily-spatial-peak time series, detect events via
   peak-detection with a recovery interval (v1.7, replaces v1.6
   run-detection):

   a. **Candidate peaks:** days where the spatial peak exceeds the
      peak threshold (7 m/s).
   b. **Non-maximum suppression:** sort candidates by amplitude
      descending. Greedily select the strongest, then suppress all
      candidates within +/- 10 days of any already-selected peak.
      Repeat. This yields a set of distinct peak days separated by
      at least 10 days each, matching the typical inter-burst
      separation in the super-event literature (McPhaden 1999,
      Lengaigne et al. 2003).
   c. **Event boundaries:** for each surviving peak, walk outward
      while the spatial peak stays above the base threshold (5 m/s),
      bounded by the midpoint to neighboring selected peaks. This
      lets a sustained westerly period containing multiple sub-bursts
      split into multiple events instead of collapsing into one.
   d. **Duration filter:** drop events shorter than 5 days.

Each detected event carries start date, end date, duration, peak
amplitude, and the peak date (the day of the surviving local
maximum). The fetcher returns the current-year event list plus full
event detail for each analog year (1997, 2015, 2023, 2025).

**Cache architecture.** The full-field climatology is cached once.
Per-year spatial peak series are cached as algorithm-independent
JSON. Per-year event lists are cached with an algorithm-version
suffix (`_v17`). When the detection algorithm changes again, only
the events caches need invalidating; peak series are reused. No CDS
re-pull needed for analog years.

**Relationship to CWWA.** CWWA and WWB are presented as
complementary, not as a swap. CWWA remains useful for season-on-
season comparisons (a smooth cumulative scalar). WWB is the
operationally important diagnostic for "did a Kelvin-wave-generating
burst occur." Brief readers see both numbers; the case where CWWA is
low but WWB count is non-zero is exactly the methodologically
interesting one Swain flagged.

**Parameter choices.** RECOVERY_DAYS = 10 is the central tunable
parameter introduced in v1.7. The typical autocorrelation length of
equatorial WWBs in the 850 hPa zonal wind field is 7-14 days
(McPhaden 1999 Figure 3; Lengaigne et al. 2003 Section 3). At 10
days the algorithm separates distinct bursts riding on a sustained
westerly background without over-splitting a single burst's natural
multi-day shape. A sensitivity check at 7 and 14 days produces
event counts within +/-1 of the production value for all analog
years; the analog ordering is preserved.

**v1.6 algorithm (deprecated).** The prior detector counted
"consecutive runs of days above the base threshold" as single
events. During persistently westerly periods, this merged multiple
distinct bursts into one long event: 1997's first event ran 71
days, 2015's 104 days, even though each contained 3-5 distinct
sub-bursts. v1.7 splits these correctly by peak. The methodology
change log entry under "Versioning and change log" documents the
swap and resulting count changes.

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

## What the impact section does not do

The credibility of this brief depends on holding a strict aggregator
line. Specifically, the impact section does not:

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
column.

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

   **Latitude-band sensitivity check (2026-05-09).** An external
   reviewer flagged that some of the most anomalous westerlies sit
   slightly off-equator and asked whether the 5N-5S band understates
   forcing. We computed CWWA at 10N-10S for the same domain for 1997,
   2015, 2023, 2025, and 2026 develop years (one-off script at
   `scripts/cwwa_sensitivity.py`; pulls cached at `.fetch_cache/era5_cwwa_*_10NS*`).

   Result: the wider band *reduces* the super-event CWWA values, not
   raises them. At May 1 of the develop year: 1997 narrow 306 → wide
   237 (−22%); 2015 narrow 248 → wide 177 (−29%); 2023 narrow 42 →
   wide 49 (+16% but small absolute); 2026 narrow 137 → wide 121 (−12%).
   The full-season totals (end-of-August) show the same pattern.
   Physical interpretation: westerly wind bursts during super-event
   development are equatorially confined within roughly ±3-5° latitude;
   subequatorial bands (5-10°N and 5-10°S) are typically neutral-to-
   easterly during ENSO development, so averaging the wider band
   dilutes the dynamically relevant signal rather than capturing more
   of it. The narrow band correctly isolates the Kelvin-wave forcing
   region.

   Conclusion: keep production at 5N-5S. McPhaden 1999 alignment plus
   the Kelvin-wave physics both argue for the narrow band. No
   methodology version change.

   Noteworthy side finding: the wider band changes 2026's "closest
   analog" assessment. 2015's forcing was tightly equatorially
   confined (loses 29% when widening), while 2026's is more
   latitudinally diffuse (loses only 12%). The narrow-band ranking
   puts 2026 closest to 2023; the wide-band ranking puts it closest
   to 2015. This is not a band-choice problem but a real observation:
   2026's wind forcing has different latitudinal structure than the
   2015 super event, broader but weaker at the equator. Worth
   watching whether this convergence holds as the season develops.

   **Follow-up from Daniel Swain (2026-05-10), reframing the
   limitation more substantively.** The cumulative-area-mean
   framing systematically understates the operationally important
   signal: transient localized westerly wind bursts. A burst lasting
   5 days at 7N (just outside the production band) generates a
   downwelling Kelvin wave that propagates east and surfaces 2
   months later, doing physical work that 50 days of weak equatorial
   westerlies of the same area-integrated magnitude would not. CWWA
   scores them similarly because cumulative integrals are blind to
   burst structure.

   This is a real metric-design limitation, not just a band-choice
   issue. The right diagnostic for "did a Kelvin-wave-generating
   burst occur in the basin" is **spatial-peak event detection**
   (moving 5x10 deg sub-region area-mean exceeding a threshold with
   persistence and continuity), not a fixed-domain cumulative
   integral. That method (per Gemini's earlier WWE follow-up,
   independently re-motivated by Swain's input) is being added
   alongside CWWA as a parallel indicator (added in v1.6, algorithm
   refined to peak-detection with 10-day recovery interval in v1.7);
   CWWA is being retained because the cumulative scalar is more
   comparable across analog years than a discrete event count and
   because the metrics capture complementary aspects of forcing.

   For 2026 specifically, Swain's operational read: the surfacing
   Kelvin wave (visible in heat content jumping +1.36 to +2.24 C in
   one issue, exceeding 1997 and 2015 at this calendar week, and
   record-breaking warm water volume in some datasets) is a more
   meaningful indicator of ENSO trajectory than the CWWA cumulative.
   The brief should weight ocean response signals (heat content,
   subsurface Kelvin wave evidence) at least as heavily as the wind
   metric.
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
  IEA, IFPRI/IFA, Lloyd's JWC, plus sell-side framing notes). Two new
  methodology sub-sections spell out the aggregation method and the
  explicit exclusions (no asset-price targets, no trade recommendations,
  no specific harvest tonnage forecasts). Impact content is curated by
  hand each issue in `impacts.md` at the project root; no impact
  fetchers in v1.3.
- **1.4** (2026-04-29): Public template restructure for the impacts
  section: regional content now renders as a real Natural Earth-derived
  world map plus a tab strip, showing one region at a time, instead of
  a stacked bullet list. Editorial-synthesis subsection (joint Iran +
  El Niño shocks) removed for now; the brief stays in pure aggregator
  posture. "Macro and cross-cutting" paragraph also removed. Internal
  markdown brief renders the regions as linear h3 sections.
- **1.5** (2026-05-10): Headline buckets now use a smoothed estimator
  (CPC anchor with bounded SEAS5 deflection, weight = 0.2, cap = ±10
  ppt per bucket per week) instead of the raw CPC probabilities alone.
  The change addresses the brief's structural lag between CPC monthly
  issuances: under v1.4, the headline was mathematically frozen for
  4-5 weeks at a time; under v1.5, weekly observational evidence
  embedded in SEAS5's evolving ensemble can move the headline within
  bounded limits, while CPC remains the dominant source of the
  underlying probability. For NDJ 2026-27 at v1.5 introduction (CPC
  issued 2026-04-09, SEAS5 May run): the +2.5 °C bucket moves from a
  raw CPC anchor of 25% to a smoothed 35% (deflection capped at +10
  ppt against an unbounded SEAS5 signal of 75%).
- **1.6** (2026-05-11): Added spatial-peak westerly wind burst (WWB)
  event detection alongside CWWA. Addresses the methodology limitation
  surfaced by Daniel Swain on X (2026-05-10): CWWA is a cumulative-
  area-mean and systematically understates transient localized bursts,
  including those occurring just outside the 5N-5S CWWA band.

  Implementation: new fetcher `fetchers/era5_burst.py`. For each day
  in Mar-onward, slide a 5deg lat x 10deg lon window over the search
  domain 10N-10S, 130E-150W (wider than CWWA's 5N-5S, per Swain's
  point that productive bursts sit just outside the equator). The
  per-day "spatial peak" is the maximum area-mean u_850 anomaly across
  all window positions. Event detection then applied a dual threshold
  (5 m/s sustained > 5 days, with at least one day > 7 m/s within the
  event), following McPhaden 1999 + Gemini's earlier follow-up.

  CWWA is retained as a complementary indicator: it remains the
  smoother, more comparable-across-years cumulative scalar, useful
  for season-on-season comparisons. WWB event count is the
  burst-structure indicator, useful for "did a Kelvin-wave-generating
  burst occur in the basin." The brief shows both in the physical-
  state section.

  Known limitation at v1.6 issuance: run-based detection merged
  multiple sub-bursts inside a sustained westerly period into a
  single long event (1997's first event ran 71 days; 2015's 104
  days). Addressed in v1.7.

- **1.7** (2026-05-14): Replaced v1.6 run-detection with peak-
  detection plus a 10-day recovery interval (`fetchers/era5_burst.py`,
  same domain, climatology, and dual threshold; the change is in the
  event-counting layer only). Peak amplitudes and approximate event
  timing are unchanged from v1.6; event counts increase in years with
  sustained westerly periods (most notably 1997 and 2015, where the
  v1.6 71-day and 104-day "events" now correctly split into their
  constituent bursts). Includes a cache refactor: per-year spatial
  peak series are now cached as algorithm-independent JSON, so future
  detection-layer changes do not require CDS re-pulls.

  Rationale: v1.6's count metric was systematically biased toward
  episodic-burst years (2023, 2025) over sustained-burst years (1997,
  2015) in a way that flipped the analog ordering relative to what
  the peak-amplitude and peak-date data actually say. v1.7 restores
  the expected ordering and brings the count metric into line with
  the literature's burst-counting conventions (McPhaden 1999;
  Lengaigne et al. 2003).

- **1.8** (2026-06-02): Headline deflection switched from SEAS5-only
  (v1.5, weight 0.2, ±10 ppt cap) to an equal-weight multi-model
  consensus (ECMWF SEAS5 + the NMME suite: CFSv2, CanESM5,
  GEM5.2-NEMO, NCAR CCSM4, NCAR CESM1) at weight 0.85, uncapped. The
  headline is now consensus-led with CPC as a minor anchor. Adds
  `fetchers/nmme.py` as a headline input (it shipped in v1.7-era as an
  informational panel only); the panel and the headline now draw on
  the same NMME data.

  Rationale: the May 2026 model runs (CFSv2 ~3.1-3.9, multi-model mean
  ~2.9) ran far hotter than CPC's lagging monthly table, and the v1.5
  SEAS5-only deflection at weight 0.2 left the headline's +2.5 °C
  bucket at 45% while the six-model consensus sat at 71%. The 0.2
  weight and the warm-bias tempering that justified it were calibrated
  for a single model in the spring barrier; by June, with a
  multi-model consensus and corroborating subsurface and WWB evidence,
  a much higher weight is warranted. Effect at introduction: the
  +2.5 °C bucket moves 45% -> 66%, super (+2.0) 74% -> 78%. Weight is
  an explicit operator choice (0.85); a graceful fallback to the v1.5
  SEAS5-only estimator applies if NMME is ever unavailable, always in
  the conservative (toward-CPC) direction.

  v1.8 also adds a fifth headline bucket, "beyond instrumental record"
  (>+3.0 °C), above the existing 1997/2015-magnitude (>+2.5 °C) bucket.
  +3.0 °C exceeds every event in the instrumental record (1997 ~2.4,
  2015 ~2.6, 1877 ~2.5 on HadISST), so it answers "probability of an
  unprecedented event" directly. It is the most model-dependent bucket:
  it sits beyond CPC's published strength bins (which top out at
  >=2.0 RONI), so its CPC anchor is the deepest skew-normal tail
  extrapolation in the brief. The consensus weighting (0.85) makes the
  bucket driven mostly by direct member counts above +3.0 (SEAS5 now
  reports this threshold alongside the NMME suite), not by that
  extrapolation, but the brief flags it as its least-anchored figure.
  At introduction: ~38% (CPC anchor 14%, six-model consensus 42%).

- **1.8, +3.5 bucket** (2026-07-06): added a sixth headline bucket,
  "far beyond record" (>+3.5 °C), above the +3.0 bucket. Trigger: the
  July 1 ECMWF SEAS5 run came in at a median of +3.93 °C with 94% of
  members above +3.5, pushing the top of the distribution far enough
  that +3.0 was losing discriminating power. +3.5 °C is roughly a full
  degree above the 1997/2015 record. This does NOT change any existing
  bucket's value (they are computed identically); it only adds a new,
  higher threshold, so the methodology version is not bumped and prior
  weeks' 1.0-through-3.0 numbers remain week-over-week comparable.

  The +3.5 bucket is the single least-anchored figure in the brief.
  Its CPC anchor is a ~+3.0-RONI skew-normal extrapolation, effectively
  zero, so the bucket is almost entirely direct model member counts;
  it leans hardest on the hottest models (the July ECMWF run in
  particular). SEAS5 and the NMME suite both now report the +3.5
  member fraction. At introduction: ~42% (CPC anchor ~10%, six-model
  consensus ~47%), up from ~36% the prior week, the +6 ppt move coming
  almost entirely from the June-to-July SEAS5 run. The brief caveats it
  explicitly as "where the hot models cluster," not a calibrated
  probability. If the models cool, this bucket moves first and most.

---

*Methodology version 1.8. RONI offset fetched live each week from CPC.
ECMWF anomaly subtracts SEAS5 model climatology (1993-2016 hindcasts).
WWE forcing tracked via CWWA (5N-5S, 130E-150W cumulative) AND
spatial-peak WWB detection (10N-10S, 130E-150W, McPhaden-inspired
dual threshold, peak-detection with 10-day recovery interval).
Impact section renders as institutional aggregation only (no
editorial synthesis). Headline buckets are CPC-anchored and deflected
toward an equal-weight multi-model consensus (SEAS5 + NMME) at weight
0.85; consensus-led with CPC as a minor anchor.*
