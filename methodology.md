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
| ERA5 westerly wind events | Count of westerly wind events since March 1 | Continuous (5-day lag) |

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
2015-16) are expressed in. We translate CPC's RONI strength bins to
traditional ONI by adding a flat offset (currently +0.3 °C, estimated
empirically from observed differences between RONI and traditional ONI
in late 2025 and early 2026). The offset is expected to drift through
the year.

CPC's strength table uses 0.5 °C-wide RONI bins. To compute the
probability that traditional ONI exceeds +X °C, we adjust the threshold
to RONI = X − 0.3 °C and integrate the bin probabilities, using **linear
interpolation** within partially-overlapping bins (assuming uniform mass
distribution).

The open-ended top bin (RONI >= +2.0 °C) requires an assumption about
how its probability mass is distributed. We vary the assumed bin width
between 0.4 °C (steeper decay above +2.0) and 1.3 °C (shallower decay)
to produce a `lo`-`hi` range for the >+2.5 °C bucket. The mid value
assumes a uniform distribution over a 1.0 °C span.

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
- **No impact attribution.** Hurricane counts, food prices, drought
  severity, energy demand, etc. are not modeled here. Those are
  downstream questions handled in a separate effort.
- **No public dashboard or real-time updates faster than weekly.**

## Known limitations

1. **Spring predictability barrier.** Forecasts issued in April and May
   for the following peak season carry materially wider error bars than
   what we'll see by July or August. All current numbers are preliminary
   in a way that won't be true later in the year.
2. **WWE simplification.** Our westerly wind event count uses an
   area-mean criterion over 5N-5S, 160E-120W (anomaly > 5 m/s sustained
   > 5 days) sampled at 12 UTC, instead of McPhaden 1999's full
   spatial-peak detection on daily means. This tends to undercount
   events; the brief labels the figure as a lower bound.
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
5. **Single-offset RONI translation.** A flat +0.3 °C offset is an
   approximation. The true RONI-to-ONI difference depends on the
   global-warming signal and is technically state- and season-dependent.
   The brief notes the offset and revisits it every issue.

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

1. **The flat +0.3 °C RONI-to-ONI offset.** Is this a reasonable
   approximation, or should it be season-dependent or state-dependent?
   How quickly should it be re-estimated as the year progresses?
2. **The bin-interior interpolation assumption.** We assume uniform
   mass within each 0.5 °C RONI bin. Is there a defensible empirical
   shape (e.g., from past years' member-level CPC ensembles, if those
   are available) that would give better interpolation?
3. **The open-ended top bin width range (0.4 to 1.3 °C).** Is this the
   right span for the `lo`-`hi` range on the +2.5 °C bucket, or
   defensibly wider/narrower?
4. **The model-vs-observational climatology choice for ECMWF.** Is
   "model anomaly" the right framing for a "what's the chance peak ONI
   exceeds X" question, given that the question is observational by
   construction? Or should we report both and let the reader choose?
5. **The bucket thresholds (+1.0/+1.5/+2.0/+2.5 °C).** Are these the
   right cuts for the audience the brief is written for?
6. **The decision to surface CPC vs ECMWF disagreement rather than
   average them.** Pros and cons of pooling vs surfacing?

What we are *not* asking for is predictive-skill review of any
individual agency forecast (we did not produce any of them) nor
calibration evidence (we are not trying to outperform the agency
median).

---

*Methodology version 1.0. RONI to traditional ONI offset assumed flat
at +0.3 °C. ECMWF anomaly subtracts SEAS5 model climatology
(1993-2016 hindcasts).*
