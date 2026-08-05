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

**The valid candidate is ERA5.** Growing-season temperature over the
qualified crop regions, computed against 1961-1990 and against
1991-2020. ERA5 runs from 1940, is technology-neutral, and the repo
already holds a CDS key. The statement it supports is exactly the house
form: *this growing season is warm against 1991-2020; against 1961-1990
it is off the chart.*

**Temperature and water balance are NOT equally defensible back to
1961**, per the ENSO tracker chat, which owns the ERA5 surface.
Growing-season temperature over well-observed land is solid, because
dense surface networks were assimilated even pre-satellite. **Water
balance is much weaker**: ERA5 precipitation is model output rather than
assimilated observation, and its pre-satellite quality degrades badly
outside Europe and North America. Publishing both against 1961-1990 with
equal confidence would hand a hostile reader the water-balance half to
dismantle first. So: temperature as the drift line, water balance either
restricted to well-observed regions or carrying a visibly weaker
confidence flag.

Two operational notes from the same source: use **monthly means, not
daily** (growing-season aggregates do not need daily resolution, and
monthly is two orders of magnitude smaller), and note that the **CDS
credential is shared and already contended** (SEAS5 budget raised from
25 to 40 minutes this month; an SSL outage on 7-20 knocked both ERA5
fetchers to cached data mid-brief). Twenty-five country-crop regions
across sixty years on that account would contend with the Monday brief,
which is invariant 1. That is the strongest argument for the computation
living in platform's shared service rather than in any channel fetcher.

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

**And it is not a clean climate statement either.** Raised by the ENSO
tracker chat, 2026-07-29, and it is right: modern agriculture has
actively *reduced* weather sensitivity through irrigation, cultivar
breeding and management. So flat volatility is a **joint test of climate
stress and adaptation**, not of climate stress alone. Stable variance is
equally consistent with rising stress fully offset by adaptation, and a
reader will hear "climate is not affecting crops".

**The qualifier therefore travels in the emitted data, not in the
copy**, so it cannot be dropped downstream by a renderer or a quote. Any
payload carrying this null carries with it that it measures the net of
stress and adaptation.

**Recommendation: crops should not be the drift exception.** ERA5
through platform's climatology service remains the right route for a
drift statement. What crops uniquely contributes is a measured null that
the calibration requirement needs.

### 6k. Stress-only scope under D-065: 123 countries, and a correction

Product asked which of the four filters were about PREDICTION, and so
fall away when the product measures damage rather than forecasting
harvests, and which were about MEANING and therefore stay.

| Filter | 752 to | Kind | Under D-065 |
|---|---|---|---|
| FDR correlation with production | 28 | prediction | falls away |
| Non-degenerate production series | 23 | prediction | falls away |
| Cross-instrument corroboration | 22 | see below | **reformulated** |
| Two independent outcome sources | 17 | prediction | falls away |

**My first attempt to reformulate filter 3 was wrong, and the way it was
wrong is the useful part.** Removing production from it gives "does
vegetation agree with the water instruments", and on that test **all
twelve European countries fail** while Australia passes at 0.88, Mexico
0.88, Argentina 0.85. Spain reads 0.18, Poland 0.03, Czechia -0.09.

Europe is obviously valid cropland, so a test that rejects it is not
measuring validity. It is measuring **whether the system is
water-limited**. In semi-arid Australia water is the driver, so
vegetation and water co-move. In Germany a poor season may be heat,
excess rain or timing, so they do not. The stress is equally real in
both; only the mechanism differs.

**The actual meaning gate is closer to product's own starting list:**
cropland exists, a season exists, history exists, and the aggregate is
not degenerate. Measured:

| | |
|---|---|
| Countries with an ASAP crop series | 165 |
| ...with at least 3 crop units | 123 |
| ...and a full 26-year record | 123 |
| ...and non-degenerate variance | **123** |

**123 countries, covering 2,169 crop units, can carry a stress number.**
Up from 29 pairs, and the widening is principled rather than a gate
being dropped: every one has a validated crop mask, a season mask and 25
years of its own history.

**The 62 finding is not a validity tier, it is a claim tier.** In 62 of
the 123 the instruments agree well enough to say what kind of stress it
is. In the other 61 the honest claim stops at "below its own record",
without a driver. Two grades of sentence, not two grades of truth.

### The correction on crop calendars

Product recorded that the missing calendars for Australia, Ukraine,
Argentina, Mexico and Canada stay the top data priority under the damage
framing, for a different reason than before: so that "at this point in
the season" is meaningful.

**That is the one thing in their read I would change. Under stress-only
reporting the calendars matter LESS, not more.**

ASAP's own phenology already supplies a season mask for all 2,368 units
globally, which is why the indicator class is "Crop during growing
cycle". So "at this point in the season" is answerable everywhere
without any external calendar. What the calendars buy is the ability to
say *Australian wheat* rather than *Australian cropland*, which is a
crop-specific claim, and stress-only reporting does not make crop-
specific claims.

They are still needed for the production layer, which is where the
attribution to a harvest year lives. But they should not hold up a
stress channel, and if the top data priority was being set on this
basis, it should move.

### 6l. Three reconnaissance candidates (D-066)

D-066 makes the first pieces reconnaissance: each tests what data we can
actually get in order to prove or disprove a specific news claim, so
they should probe different questions rather than the same one three
times. Selected from `data/stress_current.json`, dekad 2026-07-11.

**1. Southeastern Anatolia. Tests: can we find what the coverage missed,
and does sub-national contradict national?** Sanliurfa z = -1.82, with
Mardin, Sirnak and Gaziantep also rank 1 of 26 and seven Turkish units
in their worst three. Turkiye's **national** rank is 23 of 26, the
better half. Driver is identified as water, making this the only
candidate where the strongest claim form is available: dry, not merely
stressed. A country in the better half containing four provinces at
25-year lows is the argument for the sub-national layer, made concrete.

**2. Europe. Tests: can one piece deflate a vague claim and locate a
real one at once?** 74% of Europe's 360 admin units sit in the better
half and Finland and Greece are at their best, so "European crops are
damaged" is not supported as stated. But Poland ranks 5 of 26 nationally
with Lodzkie, Mazowieckie and Kujawsko-Pomorskie in their worst three,
and western Ukraine has L'vivs'ka and Rivnens'ka at rank 1 of 26. **No
driver is identified** for any of them, so the honest sentence stops at
"below its own record". That also makes this a test of the weaker claim
form, the commoner case at 61 of 123 countries.

**3. The Sahel. Tests: do we add anything where agencies already
operate?** Chad ranks 1 of 26 with 13 of 22 units in their worst three,
Sudan 2 of 26 with 11 of 15, Mali 3 of 26 with 6 of 9. The most severe
signal in the file and also the best covered, by FEWS NET, GEOGLAM and
FAO. The reconnaissance value is a question about us rather than about
the crops: if FEWS NET says it better, that is a useful negative result
about where the channel should point, and cheaper to learn now than
after the map is built.

Between them these span both claim tiers, both directions of the
national-versus-regional relationship, and the range from uncovered to
over-covered. If only two are wanted, drop the Sahel: most severe,
least likely to teach something actionable, and the context where being
wrong costs most.

### 6m. The chance baseline, and two corrections to my own advice

Product caught that "81 admin units at their worst on record" is not a
finding: 2,122 units against 26 observations each gives 81.6 expected by
chance. They were right, and checking it properly makes the point
stronger rather than weaker.

**The theoretical baseline rests on ranks being uniform, and they are
not.** At this dekad 212 units sit at rank 26, their best on record,
against 82 expected, and a chi-square across all 26 ranks returns
p < 0.0001. That is what a greening trend does to recent years, so 1/26
is an approximation.

**So the baseline was rebuilt empirically, assuming nothing.** For every
year in the record, count how many units had their worst value for this
dekad in that year:

| | |
|---|---|
| 2026 | **81** |
| Other 25 years | mean 83, median 63, range 25 to 247 |
| 2026's position | higher than 64% of other years |

**81 is the middle of the distribution.** The early years carry 222, 172
and 247, which is the greening trend making old years look bad, and it
cuts in the direction of making 2026 *less* remarkable rather than more.
Product's arithmetic survives its own assumption being wrong.

**Corrected 2026-07-29 after the Europe result.** The sentence above
originally read "as many regions as an ordinary year produces", which is
too strong. The Europe analysis showed uniform 1/26 fails wherever a
series trends, so the same recount was run globally with a recent-decade
baseline:

| | Global |
|---|---|
| Uniform expectation | 83.3 |
| All other years | mean 83.4, median 63, range 25 to 247 |
| **2014-2025 only** | **mean 60.1, range 25 to 110** |
| **2026** | **81** |

**Global hoarding is much weaker than Europe's**: a factor of 1.39
against Europe's 4.0, because the big years differ by region rather than
being one continental event. So the uniform figure was roughly right
globally and badly wrong for Europe, which is the opposite of what a
single correction factor would have given.

The honest global sentence is therefore neither of the extremes:
**2026's 81 is modestly above a recent-year norm of 60, exceeds 75% of
the last twelve years, and sits well inside the range, short of 2015's
110.** Not the null, not a strong signal. The individual claims survive;
the count is mildly elevated and should not be described as either
ordinary or alarming.

**Operational consequence.** A European null must not be published in a
way that implies the world is unremarkable, because globally it is
mildly elevated and the one unambiguous cluster is the Sahel and East
Africa.

### Correction 1: the Anatolia piece cannot rest on counting

Testing concentration within each country, binomial against n x 3/26:

| Country | Units | In worst 3 | Expected | p |
|---|---|---|---|---|
| Rwanda | 28 | 16 | 3.2 | <0.00001 |
| Sudan | 14 | 11 | 1.6 | <0.00001 |
| Chad | 21 | 13 | 2.4 | <0.00001 |
| Eritrea | 5 | 5 | 0.6 | 0.00002 |
| Mali | 9 | 6 | 1.0 | 0.00015 |
| **Turkiye** | **79** | **7** | **9.1** | **0.82** |

**Turkiye has fewer extreme units than chance would give.** The Anatolia
case therefore rests on **severity and adjacency**, Sanliurfa at z =
-1.82 among the most extreme values in the file and four contiguous
provinces at rank 1, and not on any count. That is still a real piece,
but the argument has to be made the right way or a reader checking it
finds Turkiye unremarkable overall and concludes we cherry-picked.

### Correction 2: I told product to drop the Sahel and the data disagrees

My advice to drop it was editorial: FEWS NET and GEOGLAM already cover
it well. The statistics say it is the **only** cluster in the file whose
concentration is unambiguously beyond chance, by orders of magnitude.
Rwanda at 16 of 28 expected 3.2 is the strongest signal here.

The editorial argument may still win. But it should be made knowing that
the data ranks the Sahel and East Africa first and Anatolia nowhere, and
I gave that advice before I had run the test.

### 6n. The Europe number, and why the theoretical baseline misleads

Product asked for observed versus expected at rank 1 for every region a
piece would name, since that number decides what the Europe piece is.
The theoretical and empirical answers disagree, and the empirical one is
correct.

**Theoretical.** 281 European growing regions with a complete same-dekad
series, so 10.8 expected at rank 1 under a uniform 1/26. **Observed: 2.**
Read naively, Europe is far better than chance.

**Empirical, and this is the one to use.** Counting European
record-worst units in every year of the record:

| Year | Units at their worst | |
|---|---|---|
| 2003 | **103** | the European heatwave |
| 2006 | 54 | |
| 2001 | 38 | |
| 2013 | 20 | |
| 2014-2025 | mean 2.7, range 1 to 5 | |
| **2026** | **2** | ordinary |

The theoretical 10.8 is badly wrong because the record's rank-1 slots
are hoarded by 2003, 2006 and 2001. Recent years almost never produce
them, so a uniform assumption overstates the expectation by a factor of
four. **2026's 2 is dead ordinary for a recent year**, which is the null,
just not for the reason the arithmetic gave.

**The comparison the instrument supplies for free:** in 2003, 103 of 281
European growing regions were in their worst condition on record for
this point in the season. This year, two. Both in western Ukraine,
L'vivs'ka at z = -1.23 and Rivnens'ka at -1.10. That is a calibration
anchor of the kind D-043 requires and almost nobody publishes.

Country-level, all against expected = units / 26:

| Country | Units | Expected | Observed | |
|---|---|---|---|---|
| Poland | 16 | 0.6 | 0 | chance |
| Ukraine | 25 | 1.0 | 2 | p = 0.25 |
| Turkiye | 79 | 3.0 | 4 | p = 0.36 |
| Germany | 16 | 0.6 | 0 | chance |
| Spain | 17 | 0.7 | 0 | chance |

**Standing consequence: use the empirical baseline, never 1/26.** The
uniform assumption fails wherever the series carries a trend, which is
everywhere, and it fails in the direction that manufactures alarm.

### 6o. The Sahel cluster mostly does not survive its own rule

Product asked, correctly, that the Sahel sentence use an empirical
baseline rather than the uniform one, since it would be poor to state
the rule in one paragraph and use units/26 in the next. Run for every
country in the cluster:

**Corrected 2026-07-29, and the correction is mine.** The first version
of this table averaged `value_counts()` output, which omits years with a
count of zero. That silently conditions the mean on "years that had at
least one", inflating every baseline. Both figures shown:

| Country | Units | Uniform | Inflated mean | **True mean** | Recent max | 2026 | |
|---|---|---|---|---|---|---|---|
| **Chad** | 21 | 0.8 | 2.5 | **0.83** | 3 | **8** | survives |
| **Sudan** | 14 | 0.5 | 1.5 | **0.50** | 2 | **3** | survives |
| Rwanda | 28 | 1.1 | 6.7 | 1.67 | **12** | 5 | marginal |
| Eritrea | 5 | 0.2 | 2.0 | 0.17 | 2 | 2 | marginal |
| Mali | 9 | 0.3 | 1.0 | 0.25 | 1 | 1 | marginal |
| Burundi | 17 | 0.7 | 3.0 | 0.75 | **6** | 2 | marginal |

The correction moves things in both directions. **Chad strengthens**: 8
against a true recent average of 0.83 and a maximum of 3, with zero in
eight of the last twelve years. **Sudan upgrades** from marginal to
surviving. **Rwanda, Eritrea, Mali and Burundi are marginal rather than
failing**: each is above its own mean but none exceeds its own recent
maximum, and Rwanda's 2017 gave 12 against this year's 5.

Europe is unaffected in conclusion but its quoted figure was also wrong:
the true 2014-2025 mean is **1.58**, not 2.71, and 2026's 2 remains
ordinary against it.

So the original claim of a cluster "unambiguously beyond chance" was
still wrong, but for a different reason than the first correction gave:
not because the countries fail, but because only two of six clear their
own recent maximum.

**The hoarding runs the opposite way here, and that is the real find.**
Every country in this group has a recent mean *above* its uniform
expectation, factors of 0.1 to 0.4, where Europe's was 4.0. Europe hoards
its record-lows in 2003 and 2001; the Sahel hoards them in recent years.
That is a browning signal rather than a greening one.

**Chad specifically:** 2014 gave 2, 2015 gave 3, then eight consecutive
years of zero, then 2024 gave 2, 2025 gave 3 and 2026 gives 8. Three
consecutive rising years after a decade of none is a stronger and more
interesting statement than any single-year count, and it is the form the
sentence should take.

**Corrected Sahel sentence:** Chad alone, with its own trajectory, not a
regional cluster claim.

### 6p. Why the empirical baseline beats a binomial, for a reason neither of us claimed

Identified by product, 2026-07-29, and worth recording because it
answers the obvious challenge to this whole method.

A binomial expectation over N units assumes the units are independent.
Neighbouring admin units are not: adjacent provinces share weather, so
four contiguous provinces at rank 1 is closer to one event than to four.
That is awkward to correct for and it was raised twice as a caution.

**Comparing a place against its own past counts sidesteps the problem
entirely.** Chad's 2015 has the same spatial correlation structure as
Chad's 2026, because it is the same set of provinces in the same
arrangement. The correlation is already priced into both sides of the
comparison, so it cannot distort the ratio between them.

So the empirical baseline is not merely more accurate than the uniform
one. It is **robust to a problem the uniform one cannot handle at all**,
and that is the answer when someone asks why we do not just use a
binomial.

**The adopted bar, from the same exchange: a count is notable when it
clears the place's own recent maximum**, not when it clears a mean. That
is what separated Chad (8 against a max of 3) and Sudan (3 against 2)
from Rwanda (5 against 12), Eritrea, Mali and Burundi. It needs no
distributional assumption whatever, and it is emitted as
`clears_own_recent_max`.

### 6q. The notable set is unstable at dekadal resolution

Product is taking the recurring sign-off cost to Kristjan: 36 dekads a
year at even fifteen minutes each is about nine hours standing. I
proposed a lever, sign-off on CHANGE rather than on schedule, and tested
it over a full year of dekads.

**It fails. The notable set changed in 34 of 35 transitions, 97%.**
Sign-off on change would be 34 reviews a year against 36, saving half an
hour annually.

Requiring persistence helps but does not fix it:

| Rule | Transitions with a change | Set size |
|---|---|---|
| Current (single dekad) | 34 of 35 | 0 to 12 |
| Notable 2 dekads running | 26 of 34 | 0 to 10, median 4 |
| Notable 3 dekads running | 24 of 33 | 0 to 8, median 2 |

**The churn is mostly threshold flicker, not events.** Peru enters,
leaves, enters and leaves across four consecutive dekads. Saudi Arabia
does the same. These are small counts crossing a bar, and a reader
visiting weekly would infer a volatility that is not in the cropland.

**Two consequences, and the second is the important one.**

**Chad is the only country notable two dekads running in the latest
data.** That independently confirms the Chad piece by a route nothing
else in this report used, and it is a stronger argument than the count
that selected it.

**The signal persists longer than the instrument's cadence, which is an
argument for publishing monthly on data grounds rather than cost
grounds.** I had assumed dekadal publication because the instrument is
dekadal. That was wrong. Dekadal publication would show mostly flicker;
monthly publication of a persistence-filtered set would show the same
findings with a third of the churn and a third of the review cost. The
data updating every ten days does not oblige us to publish every ten
days.

### 6r. Six notable countries is an ordinary number, and the field name invites the error

Design proposed an h1: "6 countries have more cropland at a record low
than their own recent history explains", and asked whether that is a
fair reading of the `notable` flag. It is not.

**Tested the same way product tested the 81.** Counting notable
countries by the identical rule in every dekad of the last year:

| | |
|---|---|
| This dekad | **6** |
| Other 35 dekads | mean 5.4, median 5, range 0 to 12 |
| 6 is higher than | 20 of 35 dekads, the 57th percentile |

**Six is the middle of the distribution.** Their recent history explains
it entirely; it is what an ordinary dekad produces.

The theoretical check agrees. Clearing a 12-year maximum has probability
about 1/13 by chance, so across 123 countries roughly **9.5 are expected
to clear before the count floor is applied**. Ten do.

**The error is mine as much as the wording's, because I named the
field.** `notable` was built as a *selection* device: design asked for
an ordering key, and it filters which countries to show and in what
order. A field called "notable" invites exactly the reading design
gave it. `selected_for_display` would not have.

**What survives is what survived before: the individual claim, not the
count.** Chad at 8 against a recent maximum of 3 and a recent mean of
0.83 clears by a wide margin and has been checked four separate ways.
Six countries clearing their own maximum is chance. One country clearing
it by nearly a factor of three is not.

This is the third time the same shape has appeared: 81 regions, 6
countries, and my own Sahel cluster. **Aggregate counts of
threshold-crossings are always near chance here, and the individual
extremes are the finding.** That should probably be a standing rule for
the channel rather than a lesson relearned each time.

### 6s. Is the early-record surplus greening, or the instrument settling?

Product's caution, and it is the right one: the record-low surplus sits
in 2001 to 2003, which is exactly where a satellite product is least
like itself. Early calibration, fewer overpasses in a composite, and
Aqua not joining MODIS until 2002. That is the shape that produced
Fire's 5.2x EFFIS artifact and the reason D-068 moved Heat's drift claim
off ERA5.

Three tests, all cheap.

**1. Does the index's dispersion fall after 2003?** A settling instrument
requires it; greening does not.

| Period | Cross-region sd |
|---|---|
| 2001-2003 | 0.718 |
| 2004-2013 | 0.557 |
| 2014-2025 | 0.607 |
| 2026 | **0.771** |

Early dispersion is elevated, 1.18x the recent mean, which is consistent
with settling. **But it is not monotonic**: 2026 is higher than 2001-2003
and 2014-2025 exceeds 2004-2013. A settling instrument declines and
stays down. This looks like year-to-year variation with an early bump,
not a calibration curve.

**2. Does the gap survive dropping the suspect years?** Rebuilding the
record from 2004, so ranks are recomputed over 23 years and 2001-2003
never enter:

| | |
|---|---|
| Forced mean, 23-year record | 92.3 |
| 2004-2013 observed | **115.1** |
| 2014-2025 observed | **73.1** |
| Gap | **42.0 regions/year** |

**The gap survives and widens.** The decline is visible inside 2004-2025
alone, with the suspect period entirely removed. If the early surplus
were an artifact of instrument settling, deleting those years should
have collapsed the gap; instead it is larger than the 22.6 measured
across the full record.

**3. Processing changes.** ASAP's metadata gives the source as Terra and
Aqua MODIS FPAR, product version V062, which is Collection 6.1. MODIS
collections are **reprocessed retrospectively across the whole archive**,
so a version change re-derives the full record rather than creating a
step inside it. Aqua joining in 2002 is a genuine change in input
density, and it affects only the first two years, which test 2 removes.

**Conclusion: the drift is probably real, and I will not call it
greening.** The tests rule out the early-record artifact as the whole
explanation. They say nothing about the cause. An upward drift in
cropland FPAR is equally consistent with management intensification,
irrigation expansion, CO2 fertilisation, cultivar change, or the crop
mask capturing different land over time. **The measurable claim is that
the index has drifted upward; naming why would be attribution, and this
channel does not attribute.**

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
12. **A coarse measure ties, and a tie stated as a rank is a false
   claim.** The severity measure of section 13 can only land on
   multiples of 1/125, so on 2026-07-11 **29 of 123 places tie with a
   prior year and three of those are at rank 1**. Ethiopia read "the
   most stressed of 26 observations" while 2002 sat at exactly the same
   value, which is a strict maximum the data does not support. The
   granularity of any constructed measure has to be compared against
   the number of observations it ranks BEFORE the rank is put into a
   sentence. Related and worse: **ranking the raw floats let summation
   noise decide**, since two arithmetically equal years differ in the
   last bit, which put Chad 3rd or 4th depending on the order the
   instruments were averaged in.
13. **A within-place measure will be read as a between-place ranking,
   and averaging hides which one it is.** Severity places each country
   against its own history, so the value cannot order countries. It
   looks exactly as though it can. The reason is mechanical: the spread
   of a country's own 26 values is set almost entirely by how far its
   instruments move together, **r = 0.97 across the 123 places**. Where
   instruments co-move, an extreme average is the ordinary shape of a
   bad year; where they are independent, the same average is
   unprecedented. Papua New Guinea (instrument spread 0.151) is worst
   on record at 0.840 while Sudan (0.248) is only third at 0.904. **The
   rank is comparable across places; the value is not**, and the
   qualifier carrying that says so with the place's own spread in it.
14. **Equal weighting is not the conservative choice when the
   instruments are not peers.** Argued the other way in section 13 and
   defended to design: we do not know which instrument matters more, so
   any weights we invented would be the arbitrary part. That is right
   only if the five are five views of the same thing. They are not.
   They are **one cumulative crop outcome (zFPARc, the instrument ASAP
   builds its own warnings from), one instantaneous crop state (zFPAR),
   one crop-water-balance model (WSI), and two pure meteorology (SPI3,
   temperature)**. Equal weights therefore put four fifths of the
   measure on inputs and snapshots and one fifth on the season's actual
   crop outcome, which on a crops page is trap 11 wearing a new
   disguise. It surfaced as **Hungary at severity rank 1 with
   cumulative vegetation at rank 14 of 26, a median crop signal, and
   zero regions even in their worst three**; Slovakia, Austria,
   Ethiopia and Chile are the same shape. Declining to weight is itself
   a weighting, and it has to be defended against what the instruments
   ARE rather than against the wish to stay neutral.
15. **A count can pass its baseline and still be measuring the wrong
   thing, and gating it is what reveals that.** The 12 places at
   severity rank 1 cleared baseline A at p = 0.08, 2.6x the prior mean.
   Requiring the crop-outcome instrument to agree took **2026 from 12
   to 7 while 2015 went 18 to 18 and 2024 went 12 to 10**. In previous
   high-count years the places at their worst were at their worst on
   the crop instrument too; in 2026 they disproportionately are not, so
   the count was carrying a composition change rather than a crop
   signal. **A baseline tests whether a count is unusual; it never
   tests whether the count is made of the right things.** Only
   decomposing it does.

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
- **A qualifier is a property of the datum, never of the layout.** Any
  number this channel emits carries its own caveat as a field, not as
  prose beside it. The volatility null carries that it measures stress
  net of adaptation; a pair carries its earliest publishable dekad; a
  European pair carries that it rests on one outcome source. The test:
  if the number were quoted alone in someone else's article, would it
  still be honest? Prose gets truncated, rewritten and quoted away;
  fields do not. Four chats reached this independently in one week
  (ECON on estimate_state, platform on emitted-field CI coverage, the
  ENSO tracker on drift values, and this channel on the volatility
  null), which is a strong hint it is a house rule rather than four
  local conventions.
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

## 13. Severity: how deep, not just how many

Added 2026-08-05, answering Kristjan's question: the count of regions in
trouble says how many, not how bad, and "stressed vs not stressed is
binary, but some cases are bad and some horrible."

**The measure.** Each instrument is converted to its position within its
own record at this dekad, then the positions are averaged with equal
weights. Emitted at country level as `severity`.

**Equal weights are not a shortcut, they are the conservative choice.**
We do not know which instrument matters more for outcomes, and section
6 established that the instrument-to-production link is weak enough that
we do not report it. Any weights we invented would be the arbitrary part
of an otherwise distribution-free measure.

**Denominator is n-1**, worse than k of the other 25 years. Design's
convention, adopted over the n of 26 used first: a record year reads
1.000 rather than 0.962, and it agrees with rank, since rank 1 of 26
means beating all 25 others. Recorded because the two chats computed
values exactly 26/25 apart on every country, with **identical
orderings**, so every ordering check either side would run came back
clean. It surfaced only because design recomputed from the payload
rather than accepting the numbers.

**What it adds over the counted measure**, which is the test it had to
pass. Papua New Guinea clears only 4 of 5 instruments on the binary
tally and is worst on record by depth, further into its instruments'
extremes than Chad, which clears 5 of 5. The tally and the depth
disagree, and depth is the one that answers the question asked.

**It survives the stability test that killed the trajectory taxonomy.**
Rank across the last eight dekads:

| | d13 | d14 | d15 | d16 | d17 | d18 | d19 | d20 |
|---|---|---|---|---|---|---|---|---|
| Papua New Guinea | 4 | 3 | 2 | 3 | 1 | 1 | 1 | 1 |
| Honduras | 16 | 9 | 7 | 5 | 5 | 3 | 1 | 2 |
| Sudan | 18 | 20 | 9 | 5 | 4 | 5 | 2 | 3 |
| Chad | 7 | 6 | 3 | 6 | 8 | 6 | 3 | 3 |
| Turkiye | 25 | 25 | 26 | 25 | 24 | 24 | 24 | 24 |

Smooth and directional rather than flickering. The pattern taxonomy
proposed earlier produced 7 to 10 distinct patterns per country across
12 dekads, which is noise wearing a label; a continuous measure evolves
instead of crossing thresholds back and forth. **The test is the point,
not the result**: any constructed indicator gets run across consecutive
dekads before it is offered to design.

**It is COMBINED under D-033, not Measured**, and the first such number
crops has produced. Every input is measured against its own record, but
no source publishes the average. Publication is Kristjan's call rather
than the channel's.

**It is a reading, not a forecast.** The eight-dekad sequence above is
the most forecast-shaped object this channel has made, and section 6d
found in-season skill weak. It is stated as a past-tense sentence and
never drawn as a line, because the eye finishes a line before it reads
the caption.

**Two traps it produced are recorded as traps 12 and 13**: coarse
granularity ties (29 of 123 places), and a within-place measure being
read as a between-place ranking.

**What was checked before it was emitted**, since section 12's four
errors all came from believing a number that had not been read against
anything:

| Check | Result |
|---|---|
| Recomputed by code sharing nothing with the emitter | agrees on all 123 places |
| Rank against the series emitted beside it | agrees on all 123 |
| Instruments averaged vs instruments the page shows available | identical on all 123 |
| Instrument set identity, not just the count | the same five everywhere; soil moisture missing in all 123 |
| Qualifier text vs the field it describes | spread matches on all 123 |
| Statement vs rank and tie state | no strict claim on a tied place |

The identity check matters more than the count: five instruments here
and a **different** five there would be invisible in a tally, and the
resulting numbers would not be comparable while looking as though they
were.

### 13a. The severity count, and why it is not published

Added 2026-08-05. Design proposed leading the crops index on severity
rank rather than region count, on the grounds that rank is comparable
across places and the index and country pages would then answer the
same question at two scales. The argument is right and the measure
still failed.

**The two orderings barely overlap.** The index selects 6 places by
region count; 12 sit at severity rank 1. **Papua New Guinea is the only
place in both.** That alone is worth recording: breadth (how much of a
country is at a record) and depth (how far into its own extremes the
country sits) are close to independent on this data.

**Baseline A**, at this dekad, places at their worst on record per year:

| | value |
|---|---|
| uniform would say | 4.7 |
| empirical mean, 25 prior years | 4.6 (median 3, range 0 to 18) |
| 2026 | 12 (9 strict, 3 joint) |
| prior years at or above 12 | 2 of 25 (2015 at 18, 2024 at 12) |

**The uniform figure failed in a new direction here and the standing
rule did not cover it.** Its MEAN was almost exactly right, 4.7 against
4.6, because leave-one-out percentiles are exchangeable across years by
construction. Its TAIL was not: empirical sd 4.00 against a Poisson
2.15, 1.86x overdispersed, because neighbouring countries share
weather. Under the uniform assumption 12 is p = 0.003, one in 326;
empirically p = 0.08, one in 12, a **27x overstatement**. Every earlier
instance of this trap on the channel got the mean wrong, so the usual
check would have passed it.

**What killed it was decomposition, not the baseline.** Gating on the
crop-outcome instrument being in its worst third:

| gate | 2026 | prior mean | years at or above | p | ratio |
|---|---|---|---|---|---|
| none | 12 | 4.6 | 2/25 | 0.08 | 2.59x |
| crop rank <= 13 | 11 | 4.4 | 2/25 | 0.08 | 2.48x |
| crop rank <= 9 | 7 | 4.4 | 5/25 | 0.20 | 1.59x |
| crop rank <= 4 | 5 | 3.6 | 7/25 | 0.28 | 1.37x |

The worst-half row survives and does not rescue it: worst-half is
satisfied by half of all years by construction, gates almost nothing,
and drops a single place. At any gate strict enough to mean "the crop
instrument agrees", the count dissolves. See traps 14 and 15.

**Standing conclusions.**

- Severity rank stays on COUNTRY pages, where it is one place against
  its own history and no count is claimed. It is the depth answer and
  it beats the region tally at that job.
- **No severity count goes on the index.** D-079: lead with the place.
- The two places strong on both measures are the ones to lead with:
  Papua New Guinea (severity rank 1 strict, cumulative vegetation rank
  2, four units at their outright worst) and Chad (cumulative
  vegetation rank 1 of 26, 8 units at their worst, 13 of 22 in their
  worst three, severity rank 3).
- The three EU places that made design's T11 case, Austria, Slovakia
  and Hungary, are exactly the three where the measure is weakest. When
  the reader-relevance argument and the methodological weak point land
  on the same rows, say so early.

### 13b. The global frame: the two halves point opposite ways

Added 2026-08-05, from design's proposal to lead the index with a
page-level statistic instead of a count: the median severity across all
123 places, per year, at this dekad.

**The aggregate is legitimate, and the proof is structural rather than
empirical.** Each instrument's leave-one-out percentiles across 26
years are a permutation of {0/25 ... 25/25}, so they average to exactly
0.5, and so does any mean of them. Measured: every place's 26 severity
values average **0.5000, sd across the 123 places 0.00007**. The
co-movement problem of trap 13 therefore does NOT propagate to the
median: co-movement sets the spread of a place's values, never their
centre, so it cannot tilt any one year's median. It still widens the
year-to-year swing, which is why the comparison is against the 26
observed medians rather than against a theoretical null.

**And then the decomposition, which is where it goes wrong:**

| | all five | crop outcome only | meteorology only |
|---|---|---|---|
| 2026 | 0.584 | **0.400** | **0.720** |
| rank | 2 of 26 | **20 of 26** | **1 of 26** |
| prior mean | 0.488 | 0.509 | 0.486 |
| prior years at or above | 2 of 25 | 23 of 25 | **0 of 25** |

**2026 is the most meteorologically stressed year in the 26-year record
on these instruments, with no prior year close, while the typical
country's cumulative crop indicator sits at rank 20 of 26, below the
prior mean.** The all-five median averages two opposite facts and
describes neither.

The proposed sentence, "by the typical country's own standard 2026 is
among the most stressed years of the last 26", is therefore **wrong in
direction for a crops page**. By the typical country's own CROP
standard it is rank 20 of 26.

**2015 is the contrast that makes it legible**: meteorology 0.700 (rank
2) AND crop outcome 0.560, above the mean. The two moved together that
year. In 2026 they have not, and **the divergence is the finding**.

**The honest frame**, if one is published: on these instruments 2026 is
the most meteorologically stressed year in the 26-year record, and the
cumulative crop response so far is unremarkable, better than the
typical year. Two things ride with it and neither is optional. "So far"
is load-bearing, because at dekad 20 the cumulative indicator
integrates a season that is not finished. And it is a measurement, not
a forecast; section 6d found in-season skill weak.

**A fixed lower bar does not escape this.** Showing rank 1-3 rather
than rank 1 is a defensible editorial cut and it baselines better than
the twelve (33 places, prior mean 13.8, p = 0.04, 2.4x, against 12
places at p = 0.08). But it is computed on the same all-five severity
and inherits the contamination unchanged. A **moving** threshold, one
that lowers when little qualifies, is worse than either: it is pinned
to page length rather than to meaning, so the count can never tell a
reader anything, and it manufactures its own answer the way the
RECORD_RANK gate did.

**The general lesson, which is trap 15 restated at the aggregate
level.** A statistic can have a clean null, a proven-unbiased
aggregate, and a real baseline, and still be the wrong number, because
none of those properties says anything about what the statistic is made
of. Every check that passed here was a check on the container.
