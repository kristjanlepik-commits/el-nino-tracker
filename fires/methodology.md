# Fires: how these numbers are made

The fires channel tracks two things, on two instruments that measure
different quantities and are never converted into each other:

- **Detections.** Satellite thermal anomalies, daily, for 97 countries.
- **Burnt area.** Hectares mapped as burned, weekly, from Copernicus.

Every figure is one country compared against **that same country's own
history in the same week of the year**. We do not compare countries to
each other, and a page that appears to is misreading the numbers.

This page is written for someone deciding whether to cite us. The
thresholds it quotes are emitted in `data/events.json` under `method`,
so the page reads them rather than restating them and cannot drift from
the code that applies them.

## What is measured

**Detections.** NASA FIRMS, VIIRS aboard Suomi-NPP, 375 m, near-real-time
for the current week and the science-quality archive for prior years.
Low-confidence pixels are dropped. Each detection is assigned to a country
by point-in-polygon, not by bounding box, so a fire near a border counts
for the country it is in.

**The trailing complete week.** Seven days ending yesterday. A day is only
counted once the archive has closed it, roughly three hours after
midnight UTC, so the newest figure is always one day behind today. That
lag is the instrument, not a delay in our pipeline.

**Burnt area.** Copernicus EFFIS where it has coverage, GWIS elsewhere.
Cumulative hectares since 1 January, published weekly on a Wednesday and
available the following morning. Between releases the figure ages up to
seven days, which is why hectares and detections carry separate dates on
every page.

## How a week is judged

A country's week is compared against **the same seven calendar days in
each prior year**, using the same sensor throughout. From that we take:

- **rank**, its position among those years, which is robust to one
  outlier year;
- **multiple**, the count against the mean of those years;
- **z**, the count against their standard deviation.

**Rank is the sturdier reading and the multiple is the loudest.** Where
they disagree, the pages lead on rank. A country whose record year was
exceptional will show a modest multiple against a genuinely extreme rank,
and the reverse is true for a country with a flat history.

**A noise floor applies before any of it.** Below the floor emitted as
`noise_floor_detections` a country cannot qualify however large its
ratio, because a multiple built on a handful of pixels is arithmetic
rather than a finding.

## Standing limits

These are the reasons a number on this channel might mislead you. They
are the part of this page worth reading.

**The instrument does not see what is burning.** It sees a thermal
anomaly, a time and a radiative power. Everything we say about what is
alight is an inference from where the heat sits, never a measurement.

**Cropland is a ratio, not a share.** We sample a published 500 m crop
mask at each detection and compare it against the share of that country
which *is* cropland. Cuba's detections sat on farmland 28% of the time in
the week to 29 August, against 11.5% of Cuba being farmland, which is the
2.4 times the page reports. The share alone would have told you nothing.

The ratio is withheld unless enough detections actually fall on cropland.
Peru read five times enriched on about twenty pixels, which is arithmetic
rather than a finding, and the floor exists because of it.

**Not assessed is not zero.** Two different withholdings exist and both
render as "not assessed": the mask has no data for that country at all,
and the mask was unavailable to the machine that built the payload. In
neither case have we looked, and neither is evidence about farmland.

**Some countries are not burning, they are flaring.** Gas flares and
industrial heat appear as thermal anomalies every night of the year. We
exclude a country whose week is nocturnal, low-powered, recurring in the
same cells **and flat**. The flatness test matters: Algeria met the first
three thresholds while a genuine record burned underneath, and a real
fire is a curve where a flare is a line.

**A country not in the roster is a gap in our coverage, not a quiet
country.** Absence from these pages says nothing about whether a place is
burning. It says we have not built a baseline for it.

**Averages can include years nobody measured.** Copernicus counts years
before its own coverage began as zero. We drop a leading run of empty
years before computing any "times the average", because Algeria's mean
was otherwise divided across three years that were never observed.
Interior zeros are kept: a quiet year after coverage begins is real.

**Records and multiples fail differently.** A record ignores zeros and
survives all of the above. A multiple depends on a denominator and does
not. Where a claim can be made either way, the pages make it on the
record.

## Sources

| what | source | cadence |
|---|---|---|
| detections | NASA FIRMS, VIIRS SNPP 375 m | daily |
| burnt area | Copernicus EFFIS / GWIS | weekly, Wednesday |
| cropland | JRC ASAP crop mask, 500 m | static, vintage recorded |
| country outlines | Natural Earth | static |

## Version history

**1.0, 2026-08-30.** First publication. Written after a fortnight in
which most of the limits above were found the hard way, several of them
by other people reading our numbers rather than by us.
