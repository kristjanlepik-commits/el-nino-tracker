# Crops (CRO): baseline feasibility report

Status: Phase 1 deliverable under D-032, for Kristjan's decision.
Author: CRO chat, 2026-07-28. Brief: `research/handover_crops.md`.
Nothing here is published; this report decides whether a channel opens.

## Verdict

**Open crops, narrower than commissioned.** The dependency that made
this "not yet" was closed the same day (section 8), so the remaining
question is scope, not feasibility.

The scope is genuinely narrow, and now measured rather than guessed. A
systematic scan of **752 country-commodity pairs** across 107 countries,
detrended and FDR-controlled at q = 0.10, then filtered for degenerate
series, qualifies 23 pairs, of which **22 survive cross-instrument corroboration and 17 survive an independent outcome source**.

**Plan on 17.** All of them are water-limited rainfed systems, and the
scan recovered them without being told where to look: Australian wheat
and rapeseed, the semi-arid belt from Morocco and Tunisia through Syria
and Iraq and Iran into Kyrgyzstan and Kazakhstan, and rainfed Mexico,
Argentina and Canada. Nothing tropical, irrigated or perennial qualifies
anywhere.

The attrition is itself the finding. 23 pairs cleared significance and
non-degeneracy; one fell to cross-instrument corroboration (irrigated,
so the water instruments contradicted the vegetation one) and five more
fell to an independent outcome source (minor crops where two agencies
disagree about what happened). Each filter removed something the
previous one could not see.

**Plus 12 European pairs, added 2026-07-29** after a question about UK
crop failures exposed that PSD reports the EU as one aggregate and the
scan had therefore never tested Europe at all (section 6h). Redone on
FAOSTAT: Spain wheat and barley, Germany and Czech potatoes, Hungary
maize and rapeseed, Poland, Sweden and Belarus wheat, Romania barley and
rapeseed, Slovakia rapeseed. These are corroborated across instruments
but rest on a **single outcome source**, since no standalone European
PSD series exists to check them against, and they should carry that
distinction rather than be presented as equals.

**So: 17 fully corroborated pairs, plus 12 European pairs at one
outcome source.** A crops channel built on those is a real product. A
crops channel that claims to cover crops generally is not.

The narrowing, stated plainly: crops reports **how stressed a country's
cropland is against its own 25-year record**, and the production outcome
that followed.

**Under D-042 (2026-07-29) that is the product, not a consolation
prize.** An earlier draft of this report treated "ASAP tracks the
harvest, not El Nino" as a limitation to be confessed. It is not. The
site measures the extreme events of H2 2026 and supplies context;
whether a given extreme has an ENSO link is one piece of that context
and often the answer is no. Australian wheat correlating with production
at 0.69 while Australia's 2015-16 super event ranks 16th of 24 on crop
stress is a finding about what drives Australian wheat, not a failure of
the instrument.

The practical consequence for this channel: coverage follows the
measured extremes, the twelve European pairs are not second-class for
sitting outside any teleconnection, and "Not ENSO-linked" is a tag we
expect to use often and without apology.

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

Per-country mean of ASAP's FPAR Cumulated z-score, crop-masked and
restricted to the growing cycle, against PSD production deviation from
its own trailing 5-year mean, 2002 to 2025, at lag 0 and lag 1.
Expected sign is positive: a low z-score means a poor season.

**Every correlation is reported twice, raw and after linear detrending
of both series.** This is not optional and the reason is section 9 trap
7: cropland that greens over 25 years and a yield trend that rises over
the same 25 years will correlate strongly while sharing no season-level
information whatever.

**9 of 44 pairs survive detrending** at r >= 0.40:

| Pair | raw r | detrended r | Lag |
|---|---|---|---|
| Mexico / Corn | 0.75 | **0.82** | 0 |
| Ukraine / Wheat | 0.70 | **0.81** | 0 |
| Australia / Wheat | 0.71 | **0.69** | 0 |
| Zimbabwe / Corn | 0.56 | 0.58 | 0 |
| Zambia / Corn | 0.53 | 0.54 | 0 |
| Kazakhstan / Wheat | 0.51 | 0.51 | 0 |
| Malawi / Corn | 0.52 | 0.51 | 0 |
| Kenya / Corn | 0.39 | 0.47 | 0 |
| Pakistan / Wheat | 0.25 | 0.40 | 0 |

**Every survivor is lag 0, and the set is physically coherent**: rainfed
cereals in water-limited systems, where a season's vegetation deficit is
the season's yield deficit. That coherence is worth more than any single
correlation, because it is the part a reviewer can check against
agronomy rather than against our arithmetic.

### Four apparent results that detrending destroyed

| Pair | raw r | detrended r |
|---|---|---|
| Indonesia / Palm oil | 0.71 | 0.30 |
| Malaysia / Palm oil | 0.59 | **-0.14** |
| India / Rice, Milled | 0.58 | 0.13 |
| Indonesia / Rice, Milled | 0.51 | 0.05 |

All four were lag 1, and all four were shared trends rather than shared
seasons.

**This corrects an earlier claim of this chat's.** An interim pass
reported that Malaysia palm oil at a one-year lag independently
corroborated the 12-month lag behind the published 13.2% figure. It does
not. That correlation is trend co-movement and disappears entirely on
detrending. The published 13.2% figure is not challenged by this, since
it comes from named agency data and not from us; what is withdrawn is
the claim that our indicator independently supports it.

The wider lesson for the channel: **perennial tree crops and
intensively irrigated or multi-cropped rice are outside what this
indicator can measure.** Palm oil is a perennial whose output responds
to stress 12 to 18 months earlier through bunch formation, which an
annual growing-cycle mask does not represent. Irrigated rice is buffered
from the rainfall deficit the indicator detects.

One genuine inversion, which is not a trend artifact: **Bangladesh rice
at lag 1, raw -0.83, still -0.68 after detrending**. A strong, stable,
wrong-signed relationship. Most likely flood-driven, where a high-FPAR
monsoon coincides with inundation damage, but we have not established
that and should not assert it. It is recorded as a hard exclusion with
the mechanism marked unknown.

Overfitting caution, per the build philosophy: 44 pairs were tested and
at n = 24 the r >= 0.40 threshold sits near p = 0.05, so roughly two of
the nine survivors are chance. **The relationship is pair-specific, not
general**, so qualified pairs get established and frozen one at a time,
exactly as fire baselines are.

### 6a. The systematic scan (all 168 countries)

With the full sweep in hand, the hand-picked 44 was replaced by a
systematic scan: **752 country-commodity pairs across 107 countries**,
16 commodities, every one detrended.

A scan needs a correction a hand-picked set does not. At n = 24 a naive
r >= 0.40 cut returns **111 of 752 pairs, with about 37 expected from
noise alone**. Those 37 would look exactly as convincing as Australia
wheat. So the scan applies **Benjamini-Hochberg FDR control at
q = 0.10**, giving 28 survivors of which about 3 are expected false.

A third filter was then needed, for a failure mode FDR does not touch.

**Trap: FDR controls for chance, not for a degenerate series.** Five of
the 28 survived on series that cannot support a correlation at all:

| Dropped | detrended r | Why |
|---|---|---|
| Morocco / Cotton | 0.61 | **2 distinct values** in 24 years, 4 zeros, median 1 bale |
| Tunisia / Cotton | 0.60 | **2 distinct values**, 5 zeros, median 10 bales |
| Turkmenistan / Wheat | 0.75 | 12 distinct values in 24 years, a carried-forward estimate |
| Dem People's Rep of Korea / Wheat | 0.60 | 14 distinct values, median 98 kt |
| Zambia / Sugar | 0.61 | 16 distinct values |

Requiring at least 18 distinct annual values and no zeros leaves
**23 qualified pairs**:

| Country | Commodity | detrended r | p | Lag |
|---|---|---|---|---|
| Mexico | Corn | 0.82 | <0.001 | 0 |
| Ukraine | Wheat | 0.81 | <0.001 | 0 |
| Uzbekistan | Barley | 0.77 | <0.001 | 0 |
| Syria | Wheat | 0.77 | <0.001 | 0 |
| Mexico | Rice, Milled | 0.72 | <0.001 | 0 |
| Australia | Oilseed, Rapeseed | 0.72 | <0.001 | 0 |
| Australia | Rice, Milled | 0.70 | <0.001 | 0 |
| Australia | Wheat | 0.69 | <0.001 | 0 |
| Argentina | Wheat | 0.69 | <0.001 | 0 |
| Kazakhstan | Oats | 0.68 | <0.001 | 0 |
| Zimbabwe | Sorghum | 0.67 | <0.001 | 0 |
| Australia | Cotton | 0.65 | <0.001 | 0 |
| Kyrgyzstan | Barley | 0.64 | 0.001 | 0 |
| Australia | Corn | 0.63 | 0.001 | 0 |
| Canada | Oilseed, Rapeseed | 0.62 | 0.002 | 1 |
| Iraq | Barley | 0.62 | 0.002 | 0 |
| Iran | Barley | 0.61 | 0.002 | 0 |
| Kyrgyzstan | Wheat | 0.59 | 0.003 | 0 |
| Zimbabwe | Millet | 0.59 | 0.003 | 0 |
| Tunisia | Wheat | 0.59 | 0.003 | 0 |
| Morocco | Wheat | 0.58 | 0.004 | 0 |
| Iraq | Rice, Milled | 0.58 | 0.004 | 0 |
| Zimbabwe | Corn | 0.58 | 0.004 | 0 |

**The geography is the strongest evidence in this report**, because it
was not chosen. The scan independently recovered four coherent blocks:
the entire Australian cropping system (five commodities), the semi-arid
belt from Morocco and Tunisia through Syria and Iraq and Iran into
Uzbekistan, Kyrgyzstan and Kazakhstan, southern African smallholder
cereals in Zimbabwe, and the rainfed Americas in Mexico, Argentina and
Canada. Every one is a water-limited rainfed system. Nothing tropical,
irrigated or perennial appears anywhere in the list. An instrument that
finds exactly the systems where water is the binding constraint, without
being told where they are, is measuring what it claims to measure.

### 6c. Cross-instrument corroboration (the stiffer test)

Qualification on one instrument is weak: FPAR cumulated z-score measures
greenness, and a pair correlating with greenness alone might be tracking
a MODIS artifact, a land-cover change or a cropping shift rather than a
season.

So all 168 countries were pulled again on five further instruments,
1,006 files and 1.5 GB in total, and every qualified pair was retested
against physically different measurements:

| Instrument | Measures | Expected sign |
|---|---|---|
| zfparc, zfpar | vegetation anomaly | positive |
| wsi | water satisfaction | positive |
| spi3 | 3-month rainfall anomaly | positive |
| sm | soil moisture | positive |
| temp | temperature anomaly | **negative**, heat hurts |

**22 of 23 pairs corroborate** across both vegetation and water-balance
instruments. Australia wheat is the cleanest case in the study: zFPARc
0.69, zFPAR 0.83, WSI 0.84, SPI-3 0.89, soil moisture 0.89, and
temperature at -0.57 in the correct direction. Six independent
instruments agreeing is not a correlation, it is a mechanism.

**One pair fails and is withdrawn. Uzbekistan barley** shows 0.77 on
cumulative vegetation and 0.68 on instantaneous vegetation, but 0.12 on
water satisfaction, 0.19 on rainfall and 0.23 on soil moisture. Water
tells us nothing, which is what irrigation looks like: the crop is
buffered from the rainfall the instrument detects, so the vegetation
correlation has some other cause. On one instrument it was the third
strongest pair in the study. **Qualified pairs: 22.**

Two caveats recorded rather than smoothed over:

- **Canada rapeseed qualified at lag 1, and I cannot yet tell a physical
  lag from a market-year offset.** PSD market years do not align to
  calendar years identically across countries, and my method tested both
  lags and kept the better rather than verifying the alignment. For the
  22 lag-0 pairs this does not arise. For Canada it does, and the pair
  should not be described as showing a one-year lag until the market
  year is checked.
- Afghanistan and Algeria returned persistent HTTP 502 on the WSI
  instrument across two attempts, so they carry five instruments rather
  than six. Neither is a qualified pair.

### 6d. In-season skill: can a pair be called before harvest?

This is the question that decides whether crops is an early-warning
instrument or a retrospective record, and the first attempt at it was
invalid in a way worth recording.

**Trap: a forecast test that uses post-harvest data is not a forecast
test.** Sweeping a cutoff dekad from January to December produced
"Mexico corn readable in January, peaking in late December". For a crop
harvested in autumn, December data is after the harvest. Every pair
looked excellent and none of the numbers meant what they appeared to.

Redone using only dekads between planting and the start of harvest,
with production attributed to the harvest year and the season wrap
handled explicitly. ASAP's crop calendar supplies the windows for 8 of
the 13 qualified countries.

Correlation with final production, by how much season is still to run
(T-6 means 60 days before harvest begins):

| Pair | T-0 | T-3 | T-6 | T-9 | T-12 |
|---|---|---|---|---|---|
| Kazakhstan / Oats | 0.68 | 0.65 | 0.61 | 0.56 | **0.49** |
| Syria / Wheat | 0.63 | 0.60 | 0.58 | 0.55 | **0.47** |
| Kyrgyzstan / Wheat | 0.60 | 0.58 | 0.56 | 0.51 | **0.45** |
| Kyrgyzstan / Barley | 0.60 | 0.57 | 0.53 | 0.48 | **0.41** |
| Iraq / Barley | 0.66 | 0.63 | 0.56 | 0.44 | 0.27 |
| Morocco / Wheat | 0.47 | 0.41 | 0.35 | 0.28 | 0.20 |
| Tunisia / Wheat | 0.37 | 0.32 | 0.27 | 0.22 | 0.18 |
| Zimbabwe / Corn | 0.35 | 0.25 | 0.14 | 0.04 | -0.06 |
| Zimbabwe / Sorghum | 0.31 | 0.22 | 0.12 | 0.03 | -0.06 |
| Iran / Barley | 0.35 | 0.24 | -0.01 | -0.32 | **-0.51** |
| Zimbabwe / Millet | 0.16 | 0.06 | -0.04 | -0.12 | -0.18 |

Three findings, and the second is the one that matters commercially.

**Removing the leakage costs real skill.** Zimbabwe corn was 0.58 on the
annual mean and is 0.35 using only pre-harvest data. The honest numbers
are lower across the board, and these are the honest numbers.

**Four pairs carry genuine early-warning skill.** Kazakhstan oats, Syria
wheat, and Kyrgyz wheat and barley all hold r around 0.45 with **120
days of season still to run**. That is a real in-season product: a
warning publishable four months before the harvest it describes.

**For several pairs, an early reading is worse than none.** Iran barley
runs to **-0.51 at T-12**, a confident signal pointing the wrong way.
Zimbabwe millet and corn also cross into negative territory early. A
channel that published early-season readings uniformly would be
systematically wrong on these, so **the earliest publishable dekad is a
per-pair property that has to be established and frozen**, exactly like
the baseline itself.

Aggregate: at T-6, only 5 of 11 pairs reach r >= 0.40, median 0.34. In-season
warning is available for a minority of pairs, not as a general property
of the channel.

**Blocked, and it is the commercially important half.** ASAP has no crop
calendar for **Australia, Mexico, Ukraine, Argentina or Canada**, so the
in-season question cannot yet be answered for wheat in Australia,
Ukraine and Argentina, corn in Mexico, or Canadian rapeseed. Those are
the largest and most reader-relevant of the qualified pairs. A crop
calendar for those five from USDA IPAD or an equivalent is the single
highest-value next input.

### 6e. Deriving the missing season windows, and how far it got

USDA IPAD blocks automated access (HTTP 503), and hand-copying planting
dates into the repo would put an unsourced, undated constant at the
centre of every in-season claim. But ASAP already encodes the answer:
warning code 98 means "off season" and is published per unit per dekad
for all 2,368 units, including the five countries its crop calendar
omits. The season is therefore derivable from data already in hand, with
the same provenance as everything else.

**The validation matters more than the derivation.** For the 65
countries where ASAP publishes both the off-season flag and a crop
calendar, the derived window can be checked against the stated one:
median error in season start is **2 dekads (20 days)**, and **49 of 65**
land within a month.

The 16 failures are not random. They cluster in **multi-season
countries**: Kenya (17 dekads out), Iran (14), Nigeria (12), Rwanda
(12), Myanmar (9). A method that takes the longest single run of active
dekads cannot represent two distinct rainy seasons, and it should not be
used where they exist.

Applying it to the blocked five, only one genuinely unblocks:

**Australia does.** Its cropland is dominated by a single winter cereal
season, so the derived March to November window is the wheat season.
Australian wheat holds **r = 0.50 using data through July**, against a
harvest that begins in November. That is roughly **four months of lead
on the largest qualified pair in the study** (24.5 Mt median
production), and it is the strongest in-season result anywhere in this
report.

**The other four do not, and their apparent numbers are traps.** Ukraine
wheat shows 0.82, but Ukrainian winter wheat is harvested in July while
the derived cropland window runs to November, so the figure still
contains post-harvest information: the same leakage as before, one level
down. Mexico's derived window is 31 of 36 dekads, which is not a season.
Australian rice scores *higher* at T-9 than at T-0, which is the
signature of a mismatched window rather than of skill.

So: **Australia unblocked, Mexico, Ukraine, Argentina and Canada still
blocked**, and blocked on a per-crop calendar specifically, not a
cropland one. The derived window is a cropland season and only coincides
with a crop season where one crop dominates.

### 6f. Outcome-side corroboration: 17 of 22 survive

The instrument side was corroborated across six measurements. The
outcome side was still single-sourced on USDA PSD, so every qualified
pair depended on one agency's production series being right. FAOSTAT is
the independent check: different institution, method and reporting
chain, 34 MB, open.

**The two sources broadly agree: median correlation on year-to-year
deviations is 0.91.** Comparison is on deviations, not levels, since the
levels differ by definition (FAOSTAT rice is paddy, PSD rice is milled).

**But 5 pairs qualify on PSD and fail on FAOSTAT:**

| Pair | r on PSD | r on FAOSTAT | Source agreement |
|---|---|---|---|
| Zimbabwe / Sorghum | 0.67 | **0.09** | 0.34 |
| Australia / Corn | 0.63 | **0.10** | **0.21** |
| Australia / Cotton | 0.65 | 0.32 | 0.58 |
| Australia / Rice, Milled | 0.70 | 0.31 | 0.65 |
| Zimbabwe / Corn | 0.58 | 0.39 | 0.61 |

**The pattern is not random: every failure is a minor crop in its own
country.** Australian rice is 372 kt and corn 380 kt against Australian
wheat at 24,458 kt; Zimbabwean sorghum is 77 kt. Where a crop is small,
the two agencies stop agreeing about what happened, which means at least
one of them is estimating rather than measuring. Australia corn at 0.21
source agreement is the clearest case: USDA and FAO barely agree on the
year-to-year story at all, so a correlation with either is a correlation
with one agency's estimating procedure.

FAOSTAT's provenance flags support this. Australian cotton carries 7
"estimated" values in 23 years where the surviving pairs are almost
entirely "official".

**Qualified on both sources: 17 pairs.** That is the defensible set, and
it is the number to plan on rather than 22 or 23.

The Australian cluster shrinks accordingly: wheat (source agreement
1.00) and rapeseed (0.99) survive cleanly; rice, corn and cotton do not.
This does not weaken the Australian wheat result, which is the strongest
in the report on every test applied to it.

### 6g. The four sourced calendars, and what they changed (D-040)

Sourced 2026-07-29 from named agency publications and recorded with
their wording in `crops/crop_calendars.json`. Re-running the pre-harvest
test on real harvest dates rather than derived cropland windows:

| Pair | T-0 | T-3 | T-6 | T-9 | Verdict |
|---|---|---|---|---|---|
| Mexico / Corn | 0.73 | 0.68 | 0.60 | 0.43 | **in-season, strong** |
| Argentina / Wheat | 0.63 | 0.61 | 0.63 | **0.63** | **in-season, flat** |
| Ukraine / Wheat | 0.52 | 0.45 | 0.35 | 0.21 | late season only |
| Canada / Rapeseed | 0.24 | 0.21 | 0.18 | 0.15 | **no in-season skill** |

Four results, and three of them change a decision.

**Mexico corn and Argentina wheat join the in-season set, and both are
reader-relevant.** Argentina is the more striking: its skill is **flat
at 0.63 from T-0 all the way out to T-9**, meaning early-season
conditions carry essentially all the information the full season does.
Ninety days of lead at undiminished strength is the best early-warning
property found anywhere in this study.

**Ukraine wheat drops from an apparent 0.82 to a real 0.52**, and decays
to 0.21 nine dekads out. The earlier figure was the post-harvest leakage
predicted in section 6e, now measured rather than suspected. Ukraine is
qualified but late-season only.

**Canada rapeseed fails outright at 0.24**, never reaching the bar even
using the whole pre-harvest season. Its earlier 0.62 came from a lag-1
fit that section 6c already flagged as possibly a market-year offset
rather than a physical lag. With the real calendar there is no in-season
skill. Canada stays qualified on the annual outcome and is publishable
at harvest only.

This is the single largest improvement in the report per hour spent, and
it vindicates sequencing the calendars ahead of the open decision: the
in-season launch set went from one reader-relevant pair to three.

### 6h. Europe was missing, and it was our fault not the data's

Prompted by a question about UK crop failures in the news on
2026-07-29. The UK did not appear anywhere in the 752-pair scan, and
the reason turned out to be systematic.

**USDA PSD reports the European Union as a single aggregate.** UK wheat
exists in PSD only from 2016, being inside the EU aggregate before
Brexit. Checked across 24 European countries: **20 have fewer than 20
years of standalone PSD wheat and 12 have none at all**, including
France, Germany, Spain, Italy, Greece, Portugal, Denmark, Sweden,
Finland, Ireland, the Netherlands, Belgium and Austria.

So the scan did not find Europe unqualified. It never tested it. For a
project whose audience is explicitly EU and US (T11), that is the worst
possible place to have a silent coverage hole.

**Redone with FAOSTAT as the outcome source** (1961 to 2024, official
flags, no EU aggregation): 156 European pairs tested, 17 survive
Benjamini-Hochberg at q = 0.10, and **12 survive cross-instrument
corroboration** at the same bar every other pair faced:

| Country | Commodity | r |
|---|---|---|
| Germany | Potatoes | 0.69 |
| Hungary | Rapeseed | 0.69 |
| Hungary | Maize | 0.68 |
| **Spain** | **Barley** | **0.68** |
| Sweden | Wheat | 0.67 |
| Romania | Barley | 0.65 |
| Slovakia | Rapeseed | 0.63 |
| Czech Republic | Potatoes | 0.60 |
| Poland | Wheat | 0.60 |
| Romania | Rapeseed | 0.59 |
| **Spain** | **Wheat** | **0.58** |
| Belarus | Wheat | 0.57 |

**Spain is the standout.** Barley reads 0.68 on cumulative vegetation,
0.80 on current vegetation, 0.81 on water satisfaction, 0.62 on rainfall
and 0.64 on soil moisture; wheat is similar with 0.84 on current
vegetation. Five instruments in strong agreement, and Spain is a
water-limited Mediterranean system, so it fits the physical pattern that
every other qualified pair fits.

Worth flagging for the editor: Spain is also the fire channel's declared
**non-ENSO control**. A Spanish crop story would carry "Not ENSO-linked"
and that is a feature, since it is what makes the loaded-window tag
believable elsewhere (T9).

**One caveat, and it is not small.** These 12 rest on a **single outcome
source**. PSD has no standalone European series, so the two-source check
that cut 22 pairs to 17 elsewhere cannot be run here. European pairs are
corroborated on the instrument side but single-sourced on the outcome
side, and should carry that distinction rather than be presented as
equals to Australia wheat or Mexico corn.

### On the UK specifically

**The UK does not qualify.** Its best pair is wheat at r = 0.40,
p = 0.063, which fails the bar; barley, oats, rapeseed and potatoes are
all near zero. So we cannot make a production claim about the UK.

What we can say is measured and striking. For the season to date
(October 2025 through 20 July 2026), against the UK's own 2002 to 2025
record for the same dekads:

- **Water satisfaction: worst on record**, 94.7 against a 98.1 mean
- **Temperature: warmest on record**, 9.45C against an 8.51C mean
- Vegetation: near its best, rank 24 of 25
- Rainfall: above average

That combination is coherent rather than contradictory: rainfall was
adequate, but record warmth raised evaporative demand enough to drive
the crop water balance to its lowest in 25 years, while the canopy still
looks green.

And the named agency does not currently show a 2026 failure. USDA's own
figures put UK wheat at **+0.8% against its trailing five-year mean**
for 2026 and barley at **-11.1%**. The severe UK wheat year in the
record is **2024, at -19.0%**, not 2026.

That is the whole channel discipline in one case: a real measured
extreme, no qualified link to production, and a named agency whose
current estimate does not support the headline.

### 6i. Baseline drift: what the crops equivalent is, and is not

Asked by the strategy chat under D-042. The house form of the swell is
arithmetic rather than attribution: extreme against 1991-2020, off the
chart against 1961-1990. What is the crops version?

**Two candidates fail, and both fail informatively.**

**1. Production against an old baseline is invalid.** It is dominated by
plant breeding, fertiliser and mechanisation, not climate. "This harvest
would have been extraordinary in 1970" is a statement about agronomy
wearing a climate costume. This is the same trap as section 9 trap 7,
one level up: the trend is real and it is not the trend being claimed.

**2. Season timing drift cannot be measured from ASAP at all, because
ASAP's season is a constant.** Tested directly: the in-season dekad
count per unit is **identical in every year of the record**. Australia
reads 25.2 dekads in 2002 and 25.2 in 2025, Germany 26.4 in both,
Zimbabwe 23.7 in both, with zero variance across 24 years.

ASAP's off-season flag comes from a **static phenology layer** (the
pheno rasters, version 04), not from observing when each season actually
began. So the season mask can never drift by construction, and a first
pass at this analysis reported seasons lengthening by 9 days across 18
countries with an identical p-value of 0.097 in every one. Identical
p-values across 18 independent countries were the tell; the entire
effect was 2001 being a partial year with 22 dekads rather than 36,
dragging the early-period mean down.

**Consequence for section 6e that must be carried forward:** the season
windows derived there are a fixed climatology, not observed seasons.
That is acceptable for defining a window, and it means those windows
should never be described as showing anything about season change.

**The valid candidate is ERA5.** Growing-season temperature and water
balance over the qualified crop regions, computed against 1961-1990 and
against 1991-2020. ERA5 runs from 1940, is technology-neutral, and the
repo already holds a CDS key for it. The statement it supports is
exactly the house form: *this growing season is warm against 1991-2020;
against 1961-1990 it is off the chart.*

**This is a cross-chat dependency, not a crops build.** ERA5 is the ENSO
tracker's surface (`fetchers/` and the CDS credential), so the sensible
route is a request to that chat rather than a second ERA5 fetcher here.

### 6j. Can crops do a real 1961-1990 baseline? Partly, and the answer is a null

Asked by strategy under D-045, with Fire's EFFIS cautionary case
attached: their apparent 5.2x Mediterranean burnt-area increase was
reporting coverage expanding, not fire increasing.

**PSD passes the test EFFIS failed.** Countries reporting production
average **150 in 1961-1990 and 149 in 1991-2020**, an expansion factor
of 0.99. USDA built PSD retrospectively as a consistent global series,
so it does not carry the coverage-growth artifact. **11 of the 17
qualified pairs have a complete, zero-free 1961-1990 record.**

**But three homogeneity hazards remain, and they are agricultural rather
than statistical, so a coverage test cannot see them.**

1. **Political.** Ukraine, Kazakhstan and Kyrgyzstan have 4 of 30 early
   years, because they did not exist as reporting entities before
   1987-1992. Not a data defect, a country one.
2. **Cultivar.** Canadian "rapeseed" in 1961 is not canola; canola was
   bred in the 1970s. Same series name, different crop. This is Fire's
   "same instrument at both ends" question in agronomic form, and no
   statistical check will ever flag it.
3. **Technology.** Established in section 6i: the level of a production
   or yield series is set by breeding and fertiliser, so even a perfect
   series cannot carry a climate drift claim.

**The technology-neutral form, tested.** Hazard 3 is escapable by
measuring **variability** rather than level: detrend within each era and
compare residual volatility. That is breeding-neutral and
climate-relevant, since a more variable climate should produce more
variable harvests.

Result across the 11 clean pairs:

| | |
|---|---|
| Median ratio, later era over earlier | **0.87** |
| Pairs more variable in 1991-2020 | **4 of 11** |
| Wilcoxon signed-rank on paired CVs | **p = 0.966** |

**No detectable change in harvest volatility between the two baseline
eras.** The two largest movers both have obvious non-climate
explanations: Zimbabwe millet at 2.77x spans the 2000 land reform, and
Mexico corn at 0.48x spans a large irrigation expansion.

**This is a publishable null under D-043's calibration rule**, and it is
the honest answer rather than a disappointing one. What it is not is the
house drift statement: crops can say "harvest volatility in these
systems has not measurably changed since the 1961-1990 era", which is a
calibration finding, but it cannot say "against 1961-1990 this is off
the chart".

**Recommendation: crops should not be the drift exception.** ERA5
through platform's climatology service remains the right route for a
drift statement. What crops uniquely contributes is a measured null that
the calibration requirement needs.

### 6b. How the nine pre-registered pairs fared

Judged against the 752-pair scan's FDR threshold, only 4 of the 9
survive. **That is the wrong test.** The nine were chosen in advance on
agronomic grounds and did not motivate the other 743 comparisons, so
penalising them for those tests would be an incorrect correction.

Judged correctly, with Benjamini-Hochberg **within their own family of
nine** at q = 0.10, **all 9 survive**, from Mexico corn at p < 0.001 to
Pakistan wheat at p = 0.057 against a threshold of 0.10.

Both numbers belong in the record. The 4 is what a sceptic gets if they
treat our pre-registration as post-hoc, and the honest answer to that
sceptic is that Pakistan, Kenya, Malawi, Zambia and Kazakhstan are
qualified on a weaker footing than Mexico, Ukraine, Australia and
Zimbabwe, and should carry that difference visibly rather than being
presented as equals.

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

## 8. The blocking dependency, RESOLVED 2026-07-28

**Update, same day.** The dependency below is closed. The ASAP export
endpoint was cracked: it needs four internal ids (`variable_id`,
`class_id`, `classesset_id`, `sensor_id`) that the public manual does
not document, read from the download page's own catalogue (32 indicator
and class combinations, 168 countries). The class list includes **"Crop
during growing cycle"**, so the series is crop-masked and season-masked
at source.

The proxy's defect is gone rather than mitigated: every admin unit
carries a value in every dekad, so there is no denominator to collapse.
Australia has 8 units reporting in all 906 dekads, Malaysia 14. Both
were untestable under the unit-count gate; both are now testable, and
Australia wheat is the third strongest pair in the study at a detrended
r = 0.69.

No contact with JRC is required. The puller is
`crops/pull_asap_indicator.py`: sequential, paused between calls,
resumable, and it discards any response that is not the documented CSV
header rather than caching it. The priority 40 took 23.7 minutes with
zero failures; the full 168 is running.

One weakness remains and is not closed. The country aggregate is an
**unweighted mean across admin units**, so a small unit counts as much
as a large one. ASAP area-averages within a unit but publishes no
cropped area per unit, so weighting across units needs the crop mask
raster (`asap_mask_crop_v04.tif`, 250 m). That is build-time work, and
it is a refinement rather than a defect.

The original statement of the problem follows, kept because the reasoning
that led to the fix is worth more than the conclusion.

### As originally written

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
7. **Shared trends manufacture correlation, and this one nearly shipped.**
   Four of the strongest apparent pairs, including Malaysia palm oil at
   raw r = 0.59, collapse to nothing once both series are linearly
   detrended. Cropland greens over 25 years and yields rise over 25
   years, and those two facts alone produce a confident-looking
   correlation that carries no season-level information. **Every
   qualifying correlation is reported raw and detrended, and the
   detrended figure is the one that decides.** A pair that survives only
   raw is not a pair.
8. **FDR controls for chance, not for a degenerate series.** Five
   pairs cleared Benjamini-Hochberg on series that cannot support a
   correlation: Morocco and Tunisia cotton have **two distinct values in
   24 years**, Turkmenistan wheat has twelve. A significance test asks
   whether a pattern could be noise; it never asks whether the series
   had enough information to carry a pattern at all. Qualification
   therefore requires at least 18 distinct annual values and no zeros,
   checked before the correlation is believed.
9. **A current reading is about whatever is in cycle now, which may
   not be the crop the qualified pair names.** Zimbabwe sits at 26 of 26
   for the 11 to 20 July dekad, its best July on record. Zimbabwean
   maize is a November to April crop, so that reading says nothing
   whatever about it; it is a real measurement of a different crop. The
   value is not carried or flat out of season (across-year spread at
   that dekad is 0.635, comparable to any other), so nothing in the data
   warns you. **A pair may only be reported when its own season is
   running**, and ASAP's crop calendar does not cover Australia, Mexico,
   Argentina, Canada or Ukraine, so per-pair season windows have to come
   from elsewhere. This is the same off-season trap as trap 2 wearing a
   different disguise, and it would have shipped as a confident wrong
   claim.
10. **A fixed percentage threshold means different things in different
   countries.** Raised by the Fire chat on 2026-07-29 from their own
   baselines, and tested here: across the 17 qualified pairs the
   standard deviation of production deviation ranges from 0.107 (Mexico
   corn) to 0.733 (Iraq rice), a **6.8x spread**. A "25% below average"
   headline is 2.3 sigma in Mexico and 0.3 sigma in Iraq, so the same
   sentence means once-in-a-generation in one country and roughly every
   other year in another.
   Crops fails differently from fires here, and the difference matters:
   16 of 17 pairs have reached -25% at least once and all 17 have
   reached -10%, so the channel is **not structurally blind**, it would
   simply **misrepresent**. Fires hides events; crops would mis-scale
   them. **Report rank on record, which is distribution-free. Never
   headline a percentage.**
11. **The indicator has a domain, and it is narrower than "crops".** It
   measures rainfed vegetation performance inside an annual growing
   cycle. Perennial tree crops (palm oil) and buffered irrigated systems
   (Egypt wheat, delta rice) are outside it. Bangladesh rice is not
   merely outside it but stably inverted, detrended r = -0.68, mechanism
   unestablished.

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
- **Every check this channel builds must be capable of failing.** The
  generalisation, from platform on 2026-07-29, of four failures shipped
  in one week: an exit-3 no-op counter that could only read healthy on a
  10 day cadence; a pacing wrapper calling `timeout`, which macOS does
  not ship, logging 22 successful passes over 90 minutes with nothing
  running; a `continue-on-error` whose comment credited a step that did
  not exist; and a freshness check measuring our own polling clock. Each
  was a signal that could only say one thing, and each read as coverage
  while providing none. Before adding any guard here, ask what input
  makes it go red, and if there is no such input do not add it.
- **Staleness is an absolute check, not a consecutive-no-op counter.**
  ASAP publishes every 10 days, so a legitimate "nothing to fetch" run
  repeats for nine days running and the exit-3 convention makes that
  silence look healthy. The Fire chat lost six days to exactly this
  shape on 2026-07-27. Crops is worse: a stuck fetcher needs about 20
  days before the silence is obviously wrong. Rule: **no new dekad for
  more than 20 days is an error, not a warning**, being two full
  publication cycles.
- Any multi-hour pull announces itself in `.running-jobs` per CLAUDE.md,
  **and removes the line when it ends**. The 2026-07-28 three-hour
  indicator batch never wrote one; other chats share the laptop and had
  no way to see it. The Fire chat hit the sharper version of the same
  failure the next day: their line survived three restarts, so it named
  a dead pid and reported 7 of 45 countries against an actual 295 of
  630. **A stale line is worse than no line**, because a reader acts on
  it. So the rule is write it, keep it true, delete it, and if it cannot
  be kept true then do not write it.

## 11. Open questions for Kristjan

1. ~~Do we email JRC for multi-country indicator extracts?~~
   **Closed 2026-07-28**: not needed, see section 8. The export endpoint
   is scriptable and the sweep is running.
2. **Is a channel that reports crop stress but rarely attributes it to
   El Nino worth opening**, given T10 says events are the front door?
   My read is yes, because "Australian wheat is under more stress than
   in 21 of the last 25 years" is a citable baseline claim and needs no
   causal story. But it is a narrower promise than the brief made.
3. **CLAUDE.md has no CRO ownership section.** Platform owns that file;
   it needs one before crops writes anything beyond this report.
4. **The missing crop calendars are a sourcing task, not a data task.**
   Mexico, Ukraine, Argentina and Canada hold four of the largest
   qualified pairs and all four are blocked on per-crop planting and
   harvest dates.

   Routes checked on 2026-07-28: **USDA IPAD** has the calendars and
   returns HTTP 503 to automated access. **ESA WorldCereal** publishes
   global wheat and maize season start and end at 0.5 degrees, CC BY 4.0
   (Franch et al. 2022, doi 10.6084/m9.figshare.20005293), but the
   figshare record carries only HTML bundles rather than the rasters,
   and the product is a Random Forest synthesis trained partly on ASAP
   itself, so it would not be an independent source.

   The conclusion is that this was the wrong shape of problem. What is
   actually needed is **four uncontested facts**: the wheat harvest
   window in Ukraine and Argentina, corn in Mexico, rapeseed in Canada.
   Each can be taken from a named agency publication with an issue date
   and cited like any other number in the house. That is a sourcing task
   of perhaps an hour, and pursuing a global raster to obtain it was
   over-engineering.
5. **Which pairs ship first, if it opens?** On the evidence the honest
   launch set is small: Australia wheat (four months of lead, six
   instruments agreeing, the largest pair in the study), Kazakhstan oats,
   Syria wheat, and Kyrgyz wheat and barley. Zimbabwe, Morocco and
   Tunisia are qualified but only readable close to harvest. Iran barley
   is qualified yet must never be published early, since its T-12 reading
   points the wrong way at -0.51.

## 12. Session record, 2026-07-28

Everything above was established in one working session. What was
actually run, so a later reader can tell evidence from assertion:

| Step | Scale |
|---|---|
| Sources verified live | ASAP warnings, ASAP crop calendar, 8 PSD bulk files |
| ASAP indicator sweep | 6 instruments x 168 countries, 1,006 files, 1.5 GB |
| Qualification scan | 752 country-commodity pairs, detrended, FDR-controlled |
| Corroboration | 22 of 23 pairs across 6 physically distinct instruments |
| In-season test | 11 pairs on published calendars, 10 on derived ones |

Four errors were made and corrected in the process, and they are left in
the record because each one nearly shipped as a finding: the Malaysia
palm oil corroboration claim (trend co-movement), the unit-count
denominator (structurally excluded the strongest pairs), the forecast
test that used post-harvest data, and the corroboration run that tested
lag 0 for a pair qualified at lag 1.
