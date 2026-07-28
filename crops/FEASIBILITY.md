# Crops (CRO): baseline feasibility report

Status: Phase 1 deliverable under D-032, for Kristjan's decision.
Author: CRO chat, 2026-07-28. Brief: `research/handover_crops.md`.
Nothing here is published; this report decides whether a channel opens.

## Verdict

**Open crops, but narrower than commissioned, and not yet.** One
dependency has to be resolved first (section 8), and it is a real one:
the metric that survives methodological scrutiny is not the metric the
open bulk data gives us.

The narrowing, stated plainly: crops can honestly report **how stressed
a country's cropland is against its own 25-year record**, and can
report the production outcome that followed. It usually cannot say El
Nino is the reason. Those are different claims and the channel has to be
built so they cannot be confused.

## 1. What was tested

Two sources, both fetched live on 2026-07-28, both open with no API key,
no registration and no licence gate.

| Source | What it is | Verified |
|---|---|---|
| JRC ASAP `warnings_ts.zip` | dekadal crop and rangeland warnings, sub-national (GAUL1), global | 30.7 MB, 569 MB expanded, 2,145,408 rows |
| JRC ASAP crop calendar | planting and harvest dekads per unit per crop | 3,068 rows, 74 countries |
| USDA FAS PSD grains and pulses | country by commodity by market year | 581,535 rows, 9 commodities, 163 countries |
| USDA FAS PSD oilseeds | as above | 801,669 rows, 27 commodities, 168 countries |

Also confirmed present and open, not yet pulled: PSD coffee, sugar,
cotton, livestock, dairy, fruits and vegetables.

ASAP is a **perfectly balanced panel**: 2,368 units by 906 dekads from
2001-05-21 to 2026-07-11, and all 1,773 crop-relevant units are present
in every dekad. No holes, no unit churn, no growing panel. It is a
better-conditioned series than the VIIRS record the fire channel runs on.

## 2. Which pairs carry a long consistent series (brief Q1)

PSD covers market years from **1960** for the major grains and oilseeds,
at country by commodity by attribute granularity, with Production, Area
Harvested and Yield as separate attributes. Coverage is not the
constraint. The constraint is which pairs mean anything, which is
section 6.

## 3. Baseline definition (brief Q2)

**Adopt production against the trailing 5-year mean**, as the brief
proposes, with one amendment: the window is **trailing, not centred**. A
centred window uses the two years after the one being judged, which we
would not have had at publication time, and a baseline that could not
have been computed when the claim was made is not a baseline.

For the stress layer the baseline is the fire channel's discipline
transplanted unchanged: **the same dekad of every prior year in the
record**, reported as a multiple of the mean plus rank on record. Rank
is the sturdier reading on a 25-year record, exactly as the fire spec
argues for its 14-year one.

## 4. Revision behaviour (brief Q3)

**The PSD bulk file carries no revision history.** Tested directly:
zero duplicate rows on (commodity, country, market year, attribute).
One current estimate per cell.

`Calendar_Year` and `Month` are a **last-changed stamp**, not a vintage
series: 324,960 of 581,535 grain rows still carry the 2006-07 stamp from
the PSD Online migration. That stamp does support a real and useful
claim, "this figure last moved in the July 2026 cycle", and it should be
carried into the JSON. What it does not support is a retrospective
revision story.

Consequence, and it should be stated before anyone promises otherwise:
**crops vintage history begins the day we start snapshotting.** A
"this estimate tripled in six weeks" story of the kind T5 describes is
available to crops only prospectively. ECON's ledger has the same
property for different reasons.

## 5. Cadence and lag (brief Q4)

| Layer | Cadence | Lag |
|---|---|---|
| ASAP warnings | dekadal, 36 per year on an irregular 8 to 11 day grid | published about 3 days after the dekad closes |
| PSD | monthly re-estimates on the WASDE cycle | the outcome itself arrives after harvest |

The brief's warning holds. **Crops is not a fast-reaction channel** and
should not be presented as one. The dekadal layer is timely enough to be
current, not timely enough to be news.

A cheap freshness probe exists and is verified:
`getIndicatorsInfo.php?dekad=YYYYMMDD&indicator_name=zFPARc` returns a
small JSON when that dekad is published and a literal `[]` when it is
not. A daily job can decide whether to work at all for the cost of one
small request.

## 6. Which pairs have a signal (brief Q5), and the lead test

Season stress (mean warning share over each country's active dekads)
against PSD production deviation from its own trailing 5-year mean,
2001 to 2025, tested at lag 0 and lag 1 because market-year labels do
not align to calendar years identically across countries.

**7 of 18 pairs track**, expected sign negative:

| Pair | r | Lag |
|---|---|---|
| Australia / Wheat | -0.77 | 0 |
| India / Rice, Milled | -0.61 | 0 |
| Zimbabwe / Corn | -0.59 | 0 |
| Malaysia / Palm oil | -0.54 | 1 |
| Zambia / Corn | -0.53 | 0 |
| India / Wheat | -0.49 | 1 |
| Kenya / Corn | -0.42 | 0 |

Malaysia palm oil peaking at a **one-year lag** independently
corroborates the 12-month lag behind the 13.2% figure the house already
publishes.

**11 of 18 do not track.** Indonesia rice is r = +0.07, no relationship
at all, in the country with the loudest El Nino stress signal of any
tested. Brazil corn -0.12, Argentina corn -0.14, South Africa corn
+0.17, Mozambique corn -0.04.

Overfitting caution, per the build philosophy: at n = 25, r = -0.40 sits
near p = 0.05, and 18 pairs were tested, so roughly one of these is
chance. Australia at -0.77 is robust. Kenya at -0.42 and India wheat at
-0.49 are marginal and must not be leaned on. **The relationship is
pair-specific, not general**, so qualified pairs get established and
frozen one at a time, exactly as fire baselines are.

### The distinction this exposes

Australia wheat tracks production at -0.77. Yet Australia's 2015-16
super El Nino year ranks **16th of 24** on crop stress.

Both are true, and the channel must be built around them: **ASAP tracks
the harvest. It does not track El Nino.** Conflating the two is precisely
the failure the attribution tags exist to prevent. The channel can say
"Australian wheat is under more stress than in 21 of the last 25 years".
It usually cannot say why, and for Australia the record says El Nino
often is not the reason.

## 7. Evidence basis and authorship

Under D-033 the stress layer is **Measured**: one continuous series
against its own history. The production layer is **Measured** where a
single PSD series is shown against its own trailing mean, and
**Compiled** where PSD sits beside another estimator.

Under D-021 the authorship split, at field level:

- the ASAP warning code is `agency`, because JRC published it
- our country-level aggregation, the same-dekad baseline and the rank
  are `tls_built`, because we computed them

Same row, two authorship values. This is the distinction the field
exists to make, and crops is where it gets tested early because the
temptation to compute our own agricultural numbers is real.

**ASAP's own ML yield forecast is out of scope for CRO.** It is
forward-looking and modelled. If it is used at all it is a named
forecaster's figure, which makes it aftereffects' material under D-034,
not ours.

## 8. The blocking dependency

The metric used throughout this report, share of a country's crop-active
admin1 units under warning, is a **proxy, and it has a defect that gates
cannot fully repair**.

The defect: the denominator collapses at season edges. Ungated, the
current dekad returned Austria at "100%, rank 1 of 26" on 9 active units
in mid-July. That is a saturating base, not a record drought.

Two gates fix the artifact (minimum 15 active units now, and a current
base at least half the historical base for that dekad). They drop 106 of
137 countries at the current dekad and they work: Austria, Mauritania,
Panama, Nicaragua and Sudan all correctly disappear.

But they also drop **Malaysia (8 crop units), Australia (6), South
Africa (3 active), Argentina (8) and Ethiopia (9)**. Countries with few
admin1 units can never pass a unit-count gate. That list includes
Australia wheat and Malaysia palm oil, the two strongest pairs in
section 6.

**So the proxy fails exactly where the signal is strongest.** This is not
a tuning problem.

The fix exists and is specific. ASAP publishes, per GAUL1 unit and per
dekad, area-averaged values of its underlying numeric indicators
(zFPARc, WSI, SPI, rainfall), with a class selector restricting to areas
inside the growing cycle. That is numeric, area-weighted and
season-masked at source. It retires the denominator problem rather than
patching it, and it is a stronger Measured series than a categorical
count.

Two obstacles:

1. The export endpoint needs four internal ids (`variable_id`,
   `class_id`, `classesset_id`, `sensor_id`) not documented in the
   public manual. Readable names return HTTP 400. This is build-time
   work, not a blocker.
2. JRC states that the tool serves **one country and one indicator per
   request**, and that multi-country extracts require contacting them.
   For a global channel that is 220 scripted requests or an email to
   JRC. **Kristjan's call, not the chat's.**

## 9. Traps recorded

1. **The ASAP warning name is not a unique key.** Codes 2 and 3 are both
   "Warning level 1"; 6, 7, 16 and 17 are all "Warning level 3". Only
   the numeric code is safe.
2. **Off-season (98) and insufficient-area (99) units must leave the
   denominator**, or the metric measures the calendar.
3. **Calendar year is the wrong window and the lag is the point.**
   Zimbabwe's 2015-16 drought appears in 2016 (rank 3), not 2015 (rank
   8). Malaysia is the same shape.
4. **ENSO year labels must be regional event windows, not calendar
   peak-year tags.** A crude tagging pass scored Argentina 2023 as an El
   Nino signal; that spike is the 2022-23 La Nina drought.
5. **The ASAP crop calendar covers only 74 early-warning countries.**
   Brazil, Australia, Argentina, India, Malaysia and the US are absent.
   The warnings themselves are global and already carry an off-season
   code, so the season mask does not depend on the calendar; only
   crop-specific splits do.
6. **PSD commodity names are not colloquial.** Soybean is "Oilseed,
   Soybean"; palm oil is "Oil, Palm".

## 10. If crops opens

- Spine: ASAP area-averaged indicators per GAUL1 unit, dekadal.
- Outcome layer: PSD production against a trailing 5-year mean.
- Qualified pairs established and frozen one at a time, with the lead
  correlation recorded per pair as part of the baseline.
- Attribution decided per pair per event, defaulting to
  "Attribution pending" (editorial standards section 2 rule 5).
- Cadence: dekadal refresh, monthly outcome, never fast-reaction.
- Raw pulls to `crops/.cache/`, gitignored; committed artifact is the
  compact derived series under `crops/data/`.

## 11. Open questions for Kristjan

1. **Do we email JRC** for multi-country indicator extracts, or script
   220 per-country requests? Outward-facing, so your call.
2. **Is a channel that reports crop stress but rarely attributes it to
   El Nino worth opening**, given T10 says events are the front door?
   My read is yes, because "Australian wheat is under more stress than
   in 21 of the last 25 years" is a citable baseline claim and needs no
   causal story. But it is a narrower promise than the brief made.
3. **CLAUDE.md has no CRO ownership section.** Platform owns that file;
   it needs one before crops writes anything beyond this report.
