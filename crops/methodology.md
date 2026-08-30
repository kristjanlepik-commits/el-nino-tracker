# Crops: how these numbers are made

The crops channel answers one question, in 165 countries and 2,126
sub-national crop regions: **how does this growing season compare with
the same point in that same place's own 26 years?**

It does not rank countries against each other, and it does not say what
caused anything. Both of those are deliberate, and both are explained
below.

This page is written for someone deciding whether to cite us. It states
what the numbers are, what they are not, and which of them we decline to
make a claim about even when the arithmetic would allow one.

## The source

Every figure comes from the **Joint Research Centre's ASAP** system
(Anomaly hot Spots of Agricultural Production), the European
Commission's operational agricultural monitoring service. We fetch its
published indicators and re-express them; we do not run a crop model and
we do not produce our own remote sensing.

ASAP publishes on a **dekad**: 36 times a year, on the 1st, 11th and
21st of each month, each covering the following ten days except the 21st
which runs to month end.

We restrict every pull to ASAP's **"crop during growing cycle"** class.
A region that is out of season is not measured rather than measured as
zero, which is why the number of reporting regions changes through the
year.

## What is measured

Six instruments, of which **five are reporting as of the current
dekad**. Each carries its own unit, its own direction, and its own
observation window.

| Instrument | Unit | What it summarises | Worse when |
|---|---|---|---|
| Vegetation, current | z-score | this dekad | low |
| Soil moisture | m³/m³ | this dekad | low |
| Temperature | anomaly °C | this dekad | high |
| Rainfall, 3-month | SPI | the past 3 months | low |
| Vegetation, cumulative | z-score | the season so far, from sowing | low |
| Water satisfaction | percent | the season so far, as a water balance | low |

The order above is the order they appear on every page, shortest
observation window first, because **a shorter window can move sooner**.
That order is emitted as data rather than chosen by a renderer, so it
cannot differ between pages.

**Vegetation, cumulative is the crop-outcome measure**, the one closest
to yield. It integrates from the start of the season, so it is
structurally the last to move and reads calmest exactly when a fast
deterioration is under way. That property is the reason it is shown and
the reason it is excluded from the ordering key.

## The comparison

Every claim on this channel has the same shape: **one unit against its
own history, at the same dekad of the year.**

- The baseline is **2001 to 2025**, 25 prior observations, at the same
  dekad. Never a rolling window.
- The **current year is not in the baseline**, so a z-score has no
  (n-1)/√n ceiling. A rank of "N of 26" counts the 25 baseline years
  plus the current one.
- Ranks use competition ranking, so ties are stated rather than broken
  arbitrarily.

A region is compared against itself in August against its own Augusts.
It is never compared against a neighbouring region, and never against
its own spring.

## Country figures are weighted by cropland area

A country value is the **area-weighted mean of its regions**, weighted
by ASAP's own `km2_crop` crop mask. This changed in methodology version
2.0 and it matters: under the previous unweighted mean, England carried
a quarter of the United Kingdom figure while holding 85.6% of its
cropland.

Two consequences are disclosed per country rather than left implicit:

- **A region with no cropland in ASAP's mask gets no vote.** The count of
  such regions is published per country.
- **Weights are applied to every year**, not only the current one, so the
  rank is a like-for-like comparison.

Where one region dominates, the page says so by name and share, and the
sentence is computed from the same weights it describes rather than
written by hand.

## The one number that is ours

Everything above is a re-expression of a published indicator. **The
composite severity figure is not.** It is the mean position of a
country's instruments within their own histories, and **no source
publishes it**. It is labelled in the payload as our construction rather
than an observation, and it carries three qualifiers that travel with it
everywhere:

**1. It is not a cross-place ordering.** The value places a country
against itself. The rank also saturates: **18 of the 165 published
countries, about one in nine, sit at rank 1**, so sorting on it produces
a large tied block. For how much of a country is abnormal, use the
proportion of its regions at a record, which is comparable between
places. For how fast, use the rate.

**2. Its spread differs by place.** A higher composite elsewhere can be a
less unusual year than a lower one here, because the year-to-year spread
of the composite is itself a property of the place. The rank is the
comparable figure, not the value.

**3. It is a reading of conditions to date.** It carries no statement
about the rest of the season.

That saturation figure is computed at build time from the published set.
It previously read "roughly one country in seven", which was correct
when the channel covered 123 countries and wrong within an hour of its
covering 165.

## How many records to expect anyway

**This is the number most easily misread, so it is published rather than
buried.** With 2,126 units each compared against 26 years, dozens will
sit at a record in any given dekad by chance alone. An even spread of
records would put about 82 units at their worst at any moment.

So the count only means something against its own history:

- **This dekad: 69 units at their worst on record.**
- Recent twelve years at this dekad: mean 58.8, ranging from 25 to 111.
- The full series runs back to 2001, whose 242 dwarfs anything since.

A count in the sixties is therefore an ordinary reading, and we say so
on the page rather than presenting it as an alarm.

## What we decline to claim

Our own rate instrument currently shows **25 countries deteriorating
fast, against a prior-year mean of 5.6 and a prior maximum of 16, with
no year in the 25-year record at or above it.**

**We do not call that a record**, and the payload states the refusal in
the same field as the number. The count is not controlled for the level
each fall started from, nor for drift in the series. A steep fall from a
high starting level is partly regression toward the mean, and a raw
count that tops the record is not a record until that is accounted for.

Where a single country's fall does survive that control, the page says
so. Where it does not, the page says that too, in the same sentence as
the rank, so the two cannot be separated by a layout.

## What this channel never says

**It never says why.** The driver is unidentified for most places,
including every region of the United Kingdom. Where a page notes that
"vegetation here usually tracks water availability", that is a statement
about a historical relationship in that region, not a claim about this
year.

This matters because the instruments frequently disagree. Of the 196
regions currently at a record low on current vegetation, **38, about one
in five, have water satisfaction or rainfall sitting in its best third at
the same moment.** Angola is the clearest case: five regions at a record
on the harvest measure while the water instruments read ordinary to
favourable. A page reports where each instrument sits and leaves the
causal question open.

Sequence is treated the same way. A window can manufacture the order it
appears to reveal, so the per-country history covers the whole calendar
year to the published dekad rather than a chosen number of dekads, and
each cell carries the fullest coverage that place reached so a reader can
tell genuinely low extent from thin coverage.

## Freshness

The age of the newest observation **cycles** rather than drifting: it
falls to about 9 days when a dekad lands and reaches about 19 before the
next. That is a property of a dekadal source, not staleness.

Our own bound is **30 days from the dekad label**, being 21 days of
reader relevance past the window close plus the 9 days from label to
close. Separately, an automated check compares what ASAP has published
against what we hold, and fails when the source has moved and we have
not. That check exists because the collection job failed silently for
five days in August 2026 and every relevance-based check stayed green
throughout.

A page is never built from a fetch. The build refuses outright if the six
instruments do not all sit on the same dekad, so a page cannot be
assembled from mixed vintages.

## Who is not here

Three of ASAP's 168 countries are absent: **Greenland, the French
Southern and Antarctic Territories, and the Falkland Islands (Malvinas)**.
In each case ASAP reports no cropland inside a growing cycle. That is the
source's determination, not an exclusion of ours.

**Forty-two countries were excluded until 30 August 2026** because ASAP
reports them as a single national unit rather than sub-national regions,
among them Estonia, Ireland, Portugal, the Netherlands and Switzerland.
That threshold was wrong. Every claim here is one unit against its own 26
years, and that comparison is exactly as sound for a country reported
whole as for one split into eighteen. What a single unit cannot support
is the within-country reading, so those pages carry no map and no count
of regions at a record, and say so.

## Known limits

**Soil moisture has not reported since 1 July 2026.** Every country
therefore reads five instruments of six, and the composite says which
were used. This is channel-wide and is not a country-specific failure.

**Coverage varies within a season.** A region drops out when its growing
cycle closes, so a country's denominator changes through the year. A
fraction computed on a collapsed denominator is a statement about
coverage wearing the clothes of a statement about extent, so the fullest
coverage each place reaches is published alongside.

**A missing value is never a zero.** An instrument with no reading is
marked absent with the reason attached at the datum: no current value,
undefined at this dekad, too few comparable years, or not published for
that country.

## Version history

**2.0.** Country figures area-weighted by ASAP's `km2_crop`. Previously
an unweighted mean over regions. Affects every country value and
therefore the composite, the magnitude, the rate and the ordering key.
Ranks are computed on weighted values for every year so the comparison
stays like for like.

**1.0.** Unweighted mean over a country's regions.
