# River low water: what is verified, and what blocks it

Routed to floods by CRO and ECON, accepted and deferred (D-159). This
file exists so the next attempt starts from measurements rather than
from the leads again. Everything below was fetched live on 2026-08-13,
not read from documentation.

## Why this is a new instrument, not a tail on an existing one

The routing argument was that low water is a flood series read at the
other end. It is not, for either instrument this channel runs.

**MCDWD flood extent cannot see it at all.** The product classifies
water *outside* the normal channel; the channel is masked as permanent
water. At 250 m the Rhine at Cologne is roughly one pixel wide. A river
falling from 92 cm to 50 cm entirely within its banks changes no pixel's
class. This is a structural absence, not a weak signal, and no amount of
box redrawing or compositing recovers it.

**IMERG at the low tail is meteorological drought,** which is the crops
channel's ground. Reading it here would duplicate their instrument, not
extend ours.

So low water needs gauge data, which this channel does not hold in any
form.

## The three access paths, as tested

**Pegelonline** (German WSV), free, no key, works now.
`https://www.pegelonline.wsv.de/webservices/rest-api/v2/`
36 Rhine stations at 15-minute resolution. Cologne is
`a6ee8177-107b-47dd-bcfd-30960ccc6e9c`.

Current only, and that is its limit: `P90D` returns 31 days, `P1Y` and
`P5Y` both return 500 points (CRO, verified).

**EFAS historical** on the Early Warning Data Store authenticates with
the CDS key already held. Gridded, area-subsettable, sub-daily, 1992 to
about 6 days ago. **Modelled**, forced by meteorological observations.

**GRDC**, observed and deep: 3,000+ European stations, earliest 1806,
mean series 53 years. Registration and lag; a real acquisition.

## What the free path already gives, which is more than reported

CRO's blocker was that observed-current and modelled-history cannot be
ranked against each other. True of the *time series*. Not true of the
station metadata, which the same free endpoint returns:

    /stations/<uuid>/W.json?includeCharacteristicValues=true

Cologne, 2026-08-13:

    NNW      69 cm   lowest low water on record
    MNW     114 cm   mean of low waters
    MW      297 cm   mean daily level
    MHW     725 cm   mean of floods
    HHW    1069 cm   highest flood on record
    GlW     139 cm   navigation reference level, from 2023-01-01

`NNW` of 69 cm is exactly the October 2018 record the press cites. So an
observed reading against an observed reference, same gauge and same
units, is available for free today. The current reading was 50.0 cm at
10:45, with the API's own `stateMnwMhw` flag reading `low`.

## The two things that block a superlative, and they are one layer down

**1. The gauge datum carries `validFrom: 2019-11-01`.** Gauge zero at
Cologne is 35.038 m above NHN *as of that date*. A centimetre reading
means nothing except against its datum, and the 2018 record predates it.
If that datum was revised rather than merely re-surveyed, then 50 cm
today against 69 cm in 2018 compares two rulers. Same fault class as
MODIS against VIIRS, or IMERG Final against Late: the quantity changed
while the unit did not.

Unresolved. The API does not expose datum history; BfG would.

**2. `NNW` and `MNW` carry no `validFrom` at all.** The reference period
is simply absent from the response. "Lowest on record" is unanswerable
until we know which record, and CRO's own warning about a 13-year z
against a 30-year one applies most sharply to the figure that looks most
quotable.

Until both are settled, the defensible sentence is that the reading sits
below the published NNW for that gauge, attributed to WSV, with the
record length stated as unknown. Not "lowest since records began".

## Two caveats on the source article, both the author's own

August is **not** the Rhine's seasonal minimum, so an August record is a
record for the month rather than for the series. And 1816 is the
**digitised** start, not the beginning of measurement. A page saying
"lowest since records began in 1816" would be wrong twice from one
dropped sentence each.

## What makes this worth doing later

Not the low-water story alone. A gauge network is an **observed**
validation layer for the optical flood instrument, which is precisely
what is missing where MCDWD goes blind: Manila returned `cannot_say` at
+0.82 observability dependence, and a river gauge does not care about
cloud. GRDC is global rather than European, so it would speak to the
Peru and Somalia regions too.

That is the reason to take the acquisition seriously when the region set
is frozen, and it is a better reason than the one the routing offered.

## Framing

A record-low Rhine in August has no ENSO teleconnection. It is a
notable-climate-event piece, not an El Nino impact, and should not be
filed as though the tracker's spine explains it.

Source lead: Guido Cioni, "European rivers are running dry".
Economic reading: `research/econ_notes/07_european_low_water_lead.md`.
