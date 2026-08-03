# Heat: baseline feasibility report

Owner: Heat chat (HEAT). Born 2026-08-03 from
`research/handover_heat.md` under D-061.

Status: **NOT YET TESTED.** No data has been pulled. Sections 1 and 2
are a pre-registration: the test design and the pass/fail rule are
fixed here so the threshold cannot move once the numbers arrive.
Section 3 is instrument documentation verified against ECMWF sources.
Section 5 records the rulings received from platform and product on
2026-08-03. Nothing below is a measured result.

Crops pre-registered nine pairs before scanning and it is why their
scan is credible. Fire formatted a 5.2x before checking it and it is
why that number is a cautionary tale in three documents. This channel
starts on the crops side of that line.

## Verdict

Pending. One test gates the channel per D-061, and one question now
gates the drift claim specifically: see section 6.

The honest expected outcome, stated in advance so it can be scored
against: I expect the urbanisation contamination test to **pass**, and
I expect it to pass for a reason that is itself a finding. See 1c.

## 1. The pre-registered D-049 test

### 1a. What is actually being asked

D-049: the level of a managed system cannot carry a drift claim,
because the level is set by management rather than climate.

Temperature is unmanaged, so Heat is not disqualified the way crops
was. But urbanisation is a non-climate signal that grows monotonically
inside the record, which is the same shape. The question is narrow:
**does an ERA5 grid cell over a city capture that city's growth?**

Two routes exist and they need separating, because only one is open.

- **Through the model: closed.** ERA5's land surface has no urban tile
  and its land cover is static. The model cannot know a city grew,
  because nothing in its boundary conditions varies with built-up area.
- **Through assimilation: open.** ERA5's 2m temperature comes from a
  two-dimensional optimal interpolation of screen-level observations,
  which takes SYNOP station data. Stations cluster in and near cities.
  Urban warming can therefore enter the analysis even though it cannot
  enter the physics.

The test targets the second route. Dismissing the question on "no urban
tile" is the shortcut to avoid, because it answers the closed route
only.

### 1b. Design

A differential design. A single city's trend cannot separate urban
growth from regional warming, so the test measures a difference and
compares groups.

- **Variable:** daily minimum 2m temperature. Night minimums are where
  the urban signal is strongest, and they are the channel's distinctive
  metric anyway, so the test exercises the thing we intend to publish.
- **Unit:** city cell minus the mean of a surrounding rural ring, with
  water cells and cells containing other urban areas excluded from the
  ring.
- **Period:** 1950 to 2026. The 1940s are the thinnest observing years
  in the back extension and are excluded from the test rather than
  argued about.
- **Statistic:** the linear trend in that city-minus-ring difference,
  in degrees C per decade. Written below as `dtrend`.
- **Groups:** cities paired on population trajectory, fast-growing
  against flat or shrinking, matched within climate region so that
  regional warming differences do not confound the comparison.

### 1b-i. Specification freeze, 2026-08-03, before any data is pulled

D-067 fixed the threshold. It did **not** fix everything a result
depends on, and the remaining choices are the garden of forking paths:
ring definition, city list and estimator can each be nudged after
seeing data in ways a fixed threshold does not catch. Frozen here.

**Cities.** Growth: Phoenix, Dallas-Fort Worth, Houston, Madrid,
Munich. Flat or shrinking: Buffalo, Cleveland, Detroit, Leipzig,
Liverpool, Naples. Chosen for growth contrast, disposable, and **not**
the channel's reader-facing set, which is product's and answers a
different question.

**Correction to 1b as first written.** That draft required matching
within climate region so regional warming would not confound the
comparison. It is not needed, and the reason is the design's own
strength: the ring sits immediately around the city, so regional
warming cancels inside each city's own difference before any group
comparison happens. The groups need to differ in population
trajectory and nothing else. Cross-region pairing was belt-and-braces
described as load-bearing.

**Ring.** All cells whose centres fall in the annulus 0.75 to 1.5
degrees from the city cell centre, excluding cells more than 50 percent
water on ERA5's land-sea mask. Simple mean, unweighted.

**A limitation with a known direction, recorded because it changes how
a clean result should be read.** The ring is not screened for suburban
growth. If ring cells have themselves urbanised, city-minus-ring
**understates** urban contamination. So the bias runs toward finding
the channel clean: a contaminated verdict is stronger than it looks,
and a clean verdict is weaker than it looks. This compounds with gate
0 rather than offsetting it, and both point the same way.

**Estimator.** Ordinary least squares on the annual series of the
city-minus-ring difference in daily night minima, 1950 to 2026, in
degrees C per decade. Theil-Sen computed as a pre-registered
robustness check; a sign disagreement between the two is investigated
rather than resolved by preference.

**Season.** Annual and JJA both computed and both reported, fixed in
advance so neither can be chosen after the fact.

### 1b-ii. Amendment, 2026-08-03, before any test data existed

One amendment, recorded with its reason and date because the freeze is
worth nothing if changes are not visible.

**The test uses the minimum over a six-hour night window, not the true
daily minimum.** Forced by cost: section 5b shows the derived product,
which serves true daily minima, caps at one to two years per request
and cannot carry a 77-year record. The raw product can, at six hours
per day.

**Why this cannot steer the result.** The statistic is a difference
between a city cell and a ring within 1.5 degrees of it, so city and
ring sit inside six minutes of solar time of each other and share the
window exactly. Any bias the window introduces applies to both and
cancels. The amendment was also made before any test data existed, for
a cost reason independent of the answer.

**Product's published Madrid series is unaffected** and still comes
from the derived product at true daily minimum, because that one is
reader-facing and cheap enough at one city.

**An error this caught in the probe, worth recording because it would
have been silent.** The probe sampled 00:00-05:00 UTC, which is a
reasonable night window for Europe and is 17:00-23:00 local in Phoenix,
which is evening. A single UTC window cannot serve boxes 37 degrees of
longitude apart. The windows are therefore per region: **02:00-07:00
UTC for Europe, 09:00-14:00 UTC for the US**, each covering roughly
03:00-08:00 local across the box and both seasons. Had this gone
unnoticed, every US "night minimum" in the test would have been an
evening temperature, and nothing downstream would have flagged it.

### 1c. The check that runs first, and why it is the important one

**Before the trend test: does ERA5 resolve a static urban heat island
at all?**

ERA5's horizontal resolution is 31 km, distributed on a 0.25 degree
grid. Madrid's built-up area is one to two cells. Most cities a reader
lives in are entirely sub-grid. So the prior question is whether the
city cell is measurably warmer at night than its ring in the first
place, in level, in any era.

This matters because a flat `dtrend` has two completely different
readings and only one of them is good news:

- ERA5 sees a city and sees no growth in it. Clean. The level claim
  survives.
- ERA5 does not see a city at all. Then the trend test had no power and
  proves nothing about contamination, and the real finding is that the
  measurement is of a 31 km box that mostly is not the city.

**Without this check, the second outcome would be reported as the
first.** That is the D-049 diagnostic in its inverted form: if a test
cannot move, confirm the instrument is capable of moving before reading
its stillness as a result.

### 1d. The decision rule, fixed before the numbers

**Awaiting Kristjan's ratification before the test runs.**

Reference scale: a drift signal of the size this channel intends to
publish is order 1.5 to 2.5 degrees C over sixty years, so roughly 0.25
to 0.40 degrees C per decade. The thresholds below are set as fractions
of that.

**Gate 0, power.** If the city-minus-ring difference in level is not
distinguishable from zero for the growth cities, the test is
uninformative about contamination. Record it as such, do not report it
as a pass, and go to section 4.

If gate 0 clears:

**Contaminated** if mean `dtrend` among growth cities exceeds that
among flat or shrinking cities by more than **0.03 degrees C per
decade**, being about 0.2 degrees over sixty years, about a tenth of
the signal we would be claiming. The level claim cannot be published
per city without an explicit correction.

**Clean** if that difference is below **0.01 degrees C per decade**.
The level claim stands and the channel publishes it as designed.

**Grey** in between. The claim publishes carrying the measured
contamination as a field on the datum under D-051, never as prose.

I am recording that I expect gate 0 to be the operative one.

## 2. What this test does not cover

It tests contamination. It does not test whether the number means what
the label says. Those are different failures with opposite fixes, and
section 4 is the second one.

## 3. Instrument facts, verified

Checked against ECMWF documentation on 2026-08-03 rather than asserted
from memory. Sources at the end of this section.

- **Resolution:** ERA5 HRES is 31 km, 0.28125 degrees native,
  distributed on a 0.25 degree grid.
- **2m temperature analysis:** produced by two-dimensional optimal
  interpolation of screen-level observations; the land data
  assimilation system uses the global SYNOP network for screen-level
  temperature and humidity, soil moisture and snow depth. This confirms
  the assimilation route in 1a is real.
- **Observation volume:** about 0.75 million observations per day in
  1979 against about 24 million in 2018. The observing system is not
  the same instrument at both ends of the record.
- **Back extension:** the final 1940-1978 extension is a separate
  production effort, available alongside the main release. The earlier
  preliminary 1950-1978 version suffered excessively intense tropical
  cyclones and is deprecated, with access discontinued 2023-08-15. That
  defect is resolved in the final version.
- **Discontinuity across production transitions:** ECMWF documents that
  discontinuities can occur at transitions between production
  experiments, depending on how well an experiment is spun up.

So the 1979 concern is real and milder than first put: the pre-1979
data is final rather than preliminary, and the tropical cyclone defect
is fixed. What stands is that the record spans a production boundary
and a thirty-fold change in observation volume, and that ECMWF itself
names spin-up discontinuity as a known mechanism. A homogeneity check
across 1979 is therefore a prerequisite for the drift claim, not an
optional refinement.

### 3a. A documented defect sitting inside the 1961-1990 baseline

The sharpest thing found on day one, and it lands on the channel's own
pitch example.

**ERA5 assimilated erroneous in situ snow data over Iberia. Snow is
present throughout 1978, and 2m temperature shows negative anomalies of
several degrees Celsius.** The erroneous snow depth period runs
1977-12 to 1979-03 in the monthly mean dataset.

Four consequences:

1. 1978 sits inside the 1961-1990 baseline. A year biased cold by
   several degrees, in one of thirty, biases that baseline cold, which
   **inflates** any drift computed against it. The direction is the
   flattering one, which is the direction that gets published without
   being questioned.
2. The handover's worked example is Madrid. The defect is in Iberia.
   The channel's pitch sentence runs straight through it.
3. **ERA5-Land does not escape it.** ERA5-Land carries no snow, since
   the data is not assimilated there, but the 2m temperature anomaly is
   present anyway because the forcing comes from ERA5.
4. **It is documented on the ERA5 page and not on the ERA5-Land page**,
   whose known-issues list records no 2m temperature problems at all.
   Reading only the documentation for the product you are using would
   miss it.

Not yet quantified by us. The check is cheap and pre-registered: pull
Madrid July 1978 and compare it against its neighbours in the baseline,
before any Iberian number is published. Order of magnitude, several
degrees on one year in thirty moves a thirty-year July mean by roughly
0.1 degrees C, so this is unlikely to be fatal to a drift claim and
very likely fatal to an unqualified "hottest July on record" ranking if
1978 lands anywhere near the ordering.

### 3b. ERA5-Land, priced at product's request

- 9 km against ERA5's 31 km. Land only. **1950 to present**, so it does
  not reach 1940 but does cover a full 1961-1990 baseline.
- **Produced without data assimilation.** It runs the H-TESSEL land
  surface model forced by ERA5 atmospheric fields.

That second point is the answer, and it is counterintuitive: **higher
resolution does not mean it sees the city better.** The only open route
for a city to enter the field is assimilation of urban-influenced
station data, and ERA5-Land does not assimilate. Combined with a land
surface that has no urban tile, ERA5-Land gives a smaller box that is
still not the city.

For the felt-experience claim that is a no. For the **drift** claim it
is arguably a virtue, since an unassimilated, urban-free land
temperature field at 9 km is close to what a drift instrument should
be. See section 6.

Sources:
- ERA5 data documentation:
  https://confluence.ecmwf.int/spaces/CKB/pages/76414402/ERA5+data+documentation
- ERA5-Land data documentation:
  https://confluence.ecmwf.int/pages/viewpage.action?pageId=462911184
- The family of ERA5 datasets:
  https://confluence.ecmwf.int/display/CKB/The+family+of+ERA5+datasets
- Hersbach et al. 2020, The ERA5 global reanalysis, QJRMS:
  https://rmets.onlinelibrary.wiley.com/doi/10.1002/qj.3803

## 4. The exposure the D-049 test will not catch, and product's ruling

**Heat has the floods shape.** Floods found that rainfall is unmanaged
and could carry a drift claim but is not what readers mean by a flood,
while flood extent is what they mean but cannot carry one. Heat's
version is spatial rather than causal: the ERA5 grid cell is unmanaged
and its arithmetic is honest, and it is not a measurement of the
reader's city. It is a measurement of a 31 km box containing it.

Product's ruling, 2026-08-03, and it sharpens the problem before
answering it: **the sub-grid gap is largest exactly on the metric the
channel leads with**, because urban heat island is strongest at night
and night minimums are the distinctive column.

The ruling is that the box clears the bar, because two claims are
available and only one of them needs the city.

- **The drift claim does not want the city.** "Against 1961-1990 this
  would have been the hottest July on record" is a claim about the
  climate, and a city-centre thermometer partly measures the city's
  growth. A box that is mostly not city is **less** contaminated. For
  the core product claim the regional box is the right instrument
  rather than a compromise.
- **The felt-experience claim does want the city, and we may not make
  it.** No "this is what your street was like", and no implying it.

Labelling, per D-051: the spatial qualifier is a field on the datum,
and the page says "Madrid and roughly the 30 km around it" rather than
"Madrid", with one clause saying why, because that clause converts the
limitation into the reason to trust the number.

**Product's requirement before this is settled: measure the gap.** How
much cooler are night minima in the box than in the urban core, for two
or three cities where both exist. Note that this is a **different**
measurement from gate 0 in 1c: gate 0 is internal to ERA5 and tests
contamination; the gap needs an external urban reference, since ERA5
has no urban core to compare against, and it tests representativeness.

## 5. Rulings received, 2026-08-03

### From platform (D-045 seam)

- **Heat delivers the land-temperature instance**, matching ENSO
  delivering SST. The service takes an instance per variable from
  whoever owns that variable. Platform owns the contract and the
  consumption path; Heat owns the science and the pull.
- **Pull gridded, store gridded, aggregate afterwards.** The expensive
  irreversible thing is the 60 years of ERA5; the interface is a
  question about aggregation. Cache the field, not the answer, and the
  interface can change repeatedly without a second pull.
- **The interface is deliberately not specified**, per D-030: the shape
  is discovered, not specified, and an interface with one
  implementation is a guess. ENSO's SST instance is the draft; Heat is
  the second case that turns it into a contract.
- Two binding constraints: **key by something already shared**, since
  other channels are country-shaped or catchment-shaped rather than
  lat-lon-box shaped, so store the grid and produce ISO3 means later;
  and **both baselines out of one field by one method**, or the
  difference measures our processing rather than the climate.
- **No drift figure in front of a reader until the 1979 question
  settles.** Platform is raising the D-045 exposure with Kristjan.
- CDS quota is per account, not per machine. Tell platform before the
  60-year pull.

### From product

- **Q1, the box: it clears the bar.** Full reasoning in section 4.
- **Q2, piece first, and the drift piece**, with a fourth argument
  beyond the three offered: we do not know where the next abnormal
  thing lands, so channels are insurance and pieces are what reach
  people now, and a piece is how we learn whether anyone cares before
  building a weekly cadence.
  **Gated on the homogeneity result.** If the 1961-1990 comparison is
  not safe, the piece that depends on it cannot be the first thing
  shipped under a new channel's name.
  **Named fallback: night minima ranked within the satellite era
  alone**, 1979 to now, forty-seven years, entirely inside one
  observing regime, making no cross-boundary claim. Weaker than the
  drift line and still a real piece, since nobody publishes night
  minima for a general audience.
- **Q3, city set:** product supplies the reader-facing set before
  anything freezes. Constraints: where readers live, and it includes
  cities that will read normal.
- **Q4, the spine exists, and it is the question rather than the
  layout**: where does this sit against its own history, answered at
  whatever cadence each instrument supports. Putting six channels side
  by side showed the fire page's two-column form does not generalise.
  Heat is one of two channels it fits cleanly, so Heat uses it: a fast
  left (this week's nights against every week like it) and a slow,
  genuinely independent right (this month or season against the full
  record, with the drift line). Fire page as reference, not as a
  constraint to justify departing from.

### From product, second round (page content, product's call)

- **Named city: Madrid.** In the T11 audience, tied to a story readers
  are already following through the Spanish fire season, and Iberian
  night minima are a mortality story rather than a curiosity. Paris is
  the fallback if Madrid is awkward for the test set.
  **Heat's note:** Madrid is fine for the differential test, since the
  Iberia defect in 3a is regional and largely cancels in a city-minus-
  ring difference. It does **not** cancel in a published level series,
  and the documented error window runs to 1979-03, so a night-minima
  series starting 1979-01 opens inside it. Start 1979-04 or later, or
  carry those months marked.
- **The page's argument is night minima against daytime maxima**, not
  the drift gap. Product reversed their own instruction to design on
  the ground that a page built on the one number that might collapse
  loses its argument rather than gaining a caveat. If drift survives
  homogeneity it leads and the page carries two tensions; if not, the
  page still works.
- **The global half is a ranked list of cities, not a grid.** This
  keeps one instrument across both halves of the page and needs no
  global daily-minima baseline. Trade accepted by product: less
  visually striking than a map, and the ranking is only over cities we
  chose, so selection becomes load-bearing and must be declared.
  **Heat's open item, which decides what the list shows:** ranking by
  absolute anomaly and ranking by standardised anomaly give
  substantially different lists, because cities with low interannual
  variance in night minima reach extreme percentiles on small absolute
  departures. Recommendation is percentile against each city's own
  record, consistent with the spine, with the unit carried as a field
  per D-051.

### From platform, second round: the night-minima gap, reframed

Platform corrected my statement of the open risk in D-068 and their
version is better, so it is recorded here rather than mine.

**The variable gap is narrower than the architecture already
tolerates.** D-045's own worked example was a fire page showing
regional temperature drift beside a detection anomaly: hectares and
degrees, not the same physical quantity. Drift was never meant to be
the channel's metric on a longer baseline. It is a reference layer
sitting beside the channel's number, answering how far the background
has moved. By that standard, mean temperature beside night minima is a
smaller gap than the design already accepts.

**The real risk is false continuity, not difference.** Both numbers
are degrees Celsius, so proximity invites a reader to take them as one
quantity. A reader seeing hectares next to degrees knows they are
different things. Fire's version of this was safe by accident; Heat's
is not.

**So the requirement is presentational, and it does not change the
source choice.** The drift component names its own variable and its own
subject month in its own label, never in a footnote: "regional mean
temperature, June 2026, 1961-1990 against 1991-2020" beside "night
minima, July 2026". The same two numbers under a shared header with no
variable named is the defect. This is D-051 applied to a component
rather than to a datum.

Platform's ruling on the trade, adopted: do not spend a source change
to close the variable gap. Mean temperature from a homogenised product
beats night minima from a source carrying an assimilation artifact
across the baseline boundary. Labelling fixes the reader problem;
nothing fixes a biased baseline.

**Publication lag, corrected upward.** Platform estimated two to four
weeks; the measured figure is that Berkeley Earth's latest release on
2026-08-03 was June 2026, so closer to two months. The consequence is
not only a slower update: the two halves of the page are **about
different months**. Freshness budget for the drift layer follows the
source at roughly 75 days, set by Berkeley Earth's cadence rather than
by how often we recompute. Platform wires it when the path exists.

**A caution carried into the probe.** The `era5_wwe.py` rejection this
probe tests against may be specific to the derived daily-statistics
product rather than a general CDS limit, so a positive result there
does not generalise back to the reanalysis endpoints. Record which
product each result applies to. This is the same shape as the
documentation asymmetry in 3a.

## 5b. CDS cost caps, measured 2026-08-03

Recorded per product, because platform's caution is correct that a
result on one CDS endpoint does not transfer to another. Every row
below is measured, not inferred.

| Product | Request | Result |
|---|---|---|
| derived daily-statistics | 1 yr, 9x15 box | accepted, 658s, 0.2 MB |
| derived daily-statistics | 3 yr, 9x15 box | **rejected**, cost limits |
| derived daily-statistics | 10 yr, 9x15 box | **rejected**, cost limits |
| derived daily-statistics | 1 yr, 65x89 box | accepted, 3509s, 3.9 MB |
| raw single-levels | 10 yr, 1 month, 6 night hours, 9x15 box | accepted, 321s, 0.6 MB |

**The derived product's cap counts years, and it is far tighter than
`fetchers/era5_wwe.py` implies.** That docstring records the dataset
rejecting 30-year requests. It rejects three. The note is not wrong,
it is loose in a way that cost this chat a probe round: it reads as a
constraint that bites at decades when it bites at years. Platform owns
that file; the correction is theirs to make.

**Area is cheap but not free**, correcting an earlier guess in this
document. 43 times the cells cost roughly 2.4 to 5 times the wall
clock. The uncertainty is because the 65x89 run rode through a local
DNS outage and spent an unknown share of its 3509s in 120-second retry
backoff rather than at CDS.

**cdsapi survives a network outage unattended**, which the same run
demonstrated by accident: it retried 16 or more times at 120-second
intervals against a limit of 500 and completed. That is a real
robustness finding for an overnight job on this laptop.

**Consequence for the test pull.** The derived product cannot carry a
77-year record at one to two years per request. The raw product can,
chunked as `era5_wwe.py` already chunks, and probe D confirms it takes
ten years of one month at six night hours in 321s. Production shape is
therefore two regional boxes, Europe and US, chunked by ten-year block
and month: about 192 requests. Sequentially that is well over a day; at
the concurrency CDS permits it is an overnight job, not an evening and
not a week.

Three conditions ride with that, all from CLAUDE.md's unattended-job
discipline and none optional: per-chunk caching to disk so the job is
genuinely resumable rather than merely restartable, a **duration**-based
wake lock covering the whole window, and a `.running-jobs` line before
it starts. Platform is told first, since CDS quota is per account.

## 5c. D-068's open risk is CLOSED, and a constraint follows from it

D-068 logged an open risk: if the observational products offered no
usable night minima, the published drift would be in mean temperature
while Heat leads with nights, so the page's two claims would differ in
variable as well as instrument.

**Closed favourably, 2026-08-03.** Berkeley Earth publishes land-only
**TMAX and TMIN as separate gridded products**, 1 degree, **1833 to
present**, NetCDF, about 140 MB each, monthly. These are monthly
averages of daily extremes. Found independently by Heat and platform
within an hour of each other.

So the drift claim is computed on TMIN and both halves of the page are
about daily minimum temperature. Platform's false-continuity problem
does not disappear, since the instruments still differ, but it shrinks
from "two different quantities that both read as degrees" to "one
quantity measured two ways", and their labelling requirement gets
cheaper rather than being dropped.

### The constraint this creates, and it binds publication

**The six-hour night-window construction in 1b-ii is TEST-ONLY and
never publishes.**

A minimum over six selected hours is necessarily warmer than a true
daily minimum, because it is a minimum over a subset, and the gap
widens on days when the low falls outside the window. That bias is
harmless inside the test, where city and ring share the window and it
cancels in the difference. It would **not** be harmless sitting beside
a Berkeley monthly mean of true daily minima, because there is nothing
for it to cancel against.

Therefore every published ERA5 night-minima anomaly comes from the
derived daily-statistics product at true daily minimum, which section
5b shows is affordable at the one-to-two-year chunk size for a small
number of reader-facing cities. The raw six-hour product serves the
77-year differential test and nothing else.

Stated to platform 2026-08-03 as a constraint on Heat rather than a
preference, so it is not quietly relaxed later under deadline.

### An open proposal, not yet accepted

Berkeley publishes TMAX on the same terms. Since the page's spine is
night minima against daytime maxima, pulling both would let the drift
line carry the same tension: how far the night normal has moved against
how far the day normal has moved, on a 190-year record. Measured,
arithmetic rather than attribution, and not something published for a
general audience as far as Heat is aware.

**Deliberately not stating an expected direction here.** It has not
been measured, and today produced two separate cases of a number being
formatted before it was checked.

**Platform accepted it 2026-08-03 with a precise caution: they are
giving Heat the data, not the claim.** The verification is Heat's and
is not inside their S. Written down here before their numbers arrive,
for the same reason the D-049 threshold was fixed before its pull.

### 5c-i. Pre-registered verification of the night-versus-day drift differential

Fixed before any value is seen. A differential that comes out the
interesting way is exactly the shape that gets published fastest, which
is why the checks are written first.

**Check 1, station coverage parity. Rated highest, and platform's
catch.** Berkeley's TMIN and TMAX grids need not rest on the same
stations. If TMIN coverage over 1961-1990 is thinner than TMAX in a
region, a night-versus-day differential partly measures which stations
reported what, not which warmed more. **This is Fire's 5.2x in a new
costume**: an arithmetically correct number whose coverage is the lie.
Check the per-cell station count or uncertainty field in both files
over the baseline windows before computing anything.

**Check 2, baseline-pair sensitivity.** Recompute against an alternative
pair, 1951-1980 against 1991-2020. Sign and rough magnitude must hold.

**Check 3, region-cut sensitivity.** Recompute on shifted and enlarged
boxes. A differential that depends on where a box edge falls is a box
artifact.

**The bar, set now rather than after.** The differential publishes only
if it exceeds the stated uncertainty envelope of both fields in the
same region **and** holds its sign under checks 2 and 3. No arbitrary
threshold is invented here, because the data carries its own.

**If it fails, that is a result and not a dead end.** "Night and day
normals have moved by indistinguishable amounts in this region" is a
measured null under D-050, in a domain where the assumption runs the
other way, and it is publishable on the same terms as the crops null.

**Also required before publication, and it is a page-level issue rather
than a data one:** drift regions and anomaly regions are different
geographies. The ERA5 anomaly boxes stop at 115W and do not reach the
US Pacific Northwest, which the drift boxes cover. A reader seeing both
on one page would reasonably assume they are the same area. Platform is
carrying this to design alongside the two-month publication lag.

## 6. The open question that now gates the drift claim

Platform and product converged on the same point from opposite
directions, which is worth recording as evidence rather than
coincidence. Platform proposed that the pre-1979 half might come from a
homogenised observational series rather than reanalysis. Product argued
that the drift claim does not want the city and is better served by a
less contaminated field. **Both point at the same instrument.**

Homogenised observational products are not merely an alternative
source. Their homogenisation exists to remove non-climate
inhomogeneities, urbanisation included, which is the D-049 question
this channel was sent to answer. Berkeley Earth applies an explicit
urban heat island correction after gridding; HadCRUT5 carries
urbanisation uncertainty in its ensemble. The effect is that the
gridded field represents the rural environment by construction.
Resolution: Berkeley Earth 1 degree, HadCRUT5 5 degrees, against ERA5's
0.25.

That cuts both of day one's findings. A station-based product does not
share a reanalysis assimilation artifact, so the Iberia 1978 defect
does not follow it, and it is built to span exactly the boundary in
section 3.

**The consequence is a saving.** If the drift instrument and the
anomaly instrument are not the same instrument, Heat uses ERA5 for the
city anomaly, where high resolution, hourly data and night minimums are
non-negotiable, and the delivered drift instance is observational. The
1961-1990 half of the ERA5 pull may then not be needed at all. A
30-year ERA5 climatology is still required for the anomaly; the
extension from 30 to 60 years is the incremental cost the roadmap
flags as most quota-heavy, and it is the part that would fall away.

**The catch, and it is real.** Two instruments makes the channel's
pitch sentence **Combined** under D-033, not Measured. "July 2026 sat
in the top 2% against 1991-2020; against 1961-1990 it would have been
the hottest on record" is one series against its own history only if
both halves come from one series. Split the instruments and the second
clause is arithmetic across two sources, which is Combined, and D-033
says Combined is the exception rather than the register.

So the choice is sharper than which source is cleaner:

- **One series (ERA5 both halves):** the sentence is Measured, and it
  carries the production boundary and the Iberia defect.
- **Two series:** each half is clean, and the sentence that sold the
  channel is Combined and must be labelled as such.

This is Kristjan's, not Heat's, and it is adjacent to what platform is
already taking to him on D-045 and what product is taking to him on the
argument that won Heat the slot. All three are the same question.

## 7. Traps recorded

1. **"No urban tile" answers only the closed route.** The assimilation
   route is open and is the one the test must target.
2. **A flat trend can mean no contamination or no power.** Gate 0 in
   1c exists solely to separate them.
3. **Cold-biased baseline years inflate drift.** Errors in the
   flattering direction are the ones that survive review, so the
   baseline period needs its own known-issues pass, not just the
   recent end.
4. **The pitch example is inside a documented defect region.** Worked
   examples in a handover are not vetted data.
5. **The channel's test set is not the channel's city set.** Selected
   against different criteria; conflating them would let reader
   relevance contaminate a methods test.
6. **Higher resolution is not closer to the reader.** ERA5-Land at 9 km
   sees the city no better than ERA5 at 31 km, because it does not
   assimilate and has no urban tile. Resolution and representativeness
   are different properties.
7. **A product's own known-issues page can be incomplete.** The Iberia
   defect is present in ERA5-Land and documented only on the ERA5 page.
8. **Splitting instruments to clean two claims can downgrade the
   evidence basis of the sentence that joins them.** Section 6.

## 8. Open questions

To Kristjan, and these are now one question rather than three:
ratification of the 1d decision rule before the test runs; whether the
1961-1990 comparison survives the production boundary; and if the
instruments split, whether the pitch sentence is acceptable as
Combined. Platform and product are each escalating a face of this.

To product, answered pending measurement: the box-to-core gap in
section 4, and the ERA5-Land pricing in 3b, which is a no for the
felt-experience claim.

## 9. Session record, 2026-08-03

Read the shared set and the handover. Wrote the pre-registration before
pulling anything. Verified the ERA5 instrument facts against ECMWF
documentation rather than from memory, which produced 3a and 3b.
Messaged platform and product; both answered the same day and their
answers are in section 5. No data pulled, no fetcher written, no ledger
entry made, since nothing has been ratified. FLO had a roughly 1.2 GB
job on the laptop from 16:31; nothing here collided with it.
