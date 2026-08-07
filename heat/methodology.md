# Heat: how these numbers are made

The heat channel tracks two things in fifteen European cities: **nights
that never cool below 20 °C**, and **days that pass each city's own
extreme-heat thresholds**. Every figure is one thermometer in one city,
compared against that same thermometer's own history.

This page is written for someone deciding whether to cite us. It states
what the numbers are, what they are not, and what has changed since we
started publishing them.

## What is measured

**Tropical night.** A calendar day whose minimum air temperature is
20.0 °C (68 °F) or above. This is the ETCCDI index **TR**, the standard
European met services publish. We did not choose the threshold.

**Hot day.** A day whose maximum reaches this station's own 90th, 95th
or 99th percentile of July and August maxima over 1971-2000. **This is
AEMET's published rule**, not one we invented, and it is locally
calibrated by construction: 41.2 °C in Seville, 30.2 °C in Nice. A flat
threshold cannot work across this range. Measured over 2011-2025, a
single 35 °C bar gives 0.5 days a year in Barcelona and 66.8 in Seville.

**Both, together, deliberately.** Marseille is **7th of 77** years for
hot nights in 2026 and **1st of 77** for hot days. A nights-only page
would have called Marseille an ordinary summer.

## Sources

| Country | Source | Licence |
|---|---|---|
| Spain | AEMET OpenData | commercial and non-commercial reuse permitted |
| France | Météo-France via data.gouv.fr | Licence Ouverte 2.0 |

One station per city, named in the data. Nights and days come from the
same rows of the same station record, never assembled from two.

## How a year is counted

**Every year is cut to the same calendar day.** 2026 is compared against
prior years counted to that same date, so a part-season is never ranked
against complete ones. Spanish and French cities have different cuts
because the two services publish on different lags, which is why **a
cross-city ranking is not available** and we do not print one.

**A year is usable if it holds 90% of its days from 1 May to the cut.**
The window is measured rather than assumed: across every city and year,
99.98% of tropical nights fall on or after 1 May. Days outside it cannot
hide a tropical night, so counting them toward completeness would discard
usable evidence.

**A tie is not a record.** A year's rank counts prior years at or above
it, so a tied year keeps 2026 off first place. Three cities tie 2026;
resolving it the other way would manufacture a record.

**A gap is not an end, and neither is a thin year.** Each series carries
how many slots the station record should hold, how many are present, how
many were observed but too thin to rank, and how many are truly empty.
Barcelona's record has real holes at 1928-1937 and 1939-1943.

## Standing limits

**None of these is a defect awaiting a fix.** They are properties of the
measurement and they are permanent.

**This is not a climate measurement.** A city thermometer records the
city: buildings, tarmac and traffic warm it alongside any regional
change. We make no attempt to separate the two, and no figure here should
be read as a climate trend for the surrounding region.

**One station is not a city.** Madrid Retiro is a park in central Madrid.
Barcelona's is the airport. A different station in the same city would
give different numbers, and the choice is visible in the data rather than
buried.

**The night metric does not work in northern Europe.** Amsterdam averages
under one tropical night a year, so a ratio divides by almost nothing and
produces an enormous, meaningless multiple. The channel covers Spain and
France for that reason and not because they were convenient.

**The French thresholds have weaker standing than the Spanish ones.**
AEMET publishes its percentile rule and we reproduce its published Madrid
(36.4 °C) and Seville (41.2 °C) figures exactly. **Météo-France publishes
no equivalent**, so the French thresholds are AEMET's method applied to
French stations. Defensible, and not the same thing as citing a national
service's own published number.

**Three cities publish a hot-day count and no multiple.** Lyon, Murcia
and Palma have stations that opened in 1975, 1984 and 1978. Their
1961-1990 baselines are part-length and drawn from the warmer end of the
period, so a multiple against them would understate itself while looking
like the figures beside it. The number is not printed rather than printed
with a caveat.

**Records are rare, and a count of them needs its baseline.** In a
typical year none of these fifteen cities sets a record; 2003 set twelve.
"Eight of fifteen" is uninterpretable without both.

**Short records are short.** Murcia's is 43 years, Palma's 49, Lyon's 52.
A rank of 1 of 43 is a weaker statement than 1 of 106 and the denominator
is always printed with it.

## Version history

### v1.1, 2026-08-07

**What changed.** Every city's history moved onto the national met
service that the payload already named as its source. Murcia moved to the
city station. Completeness is now measured over 1 May to the cut at 90%,
rather than over the whole calendar year. Series carry explicit slot
counts, and the tie rule is stated in the data rather than implied by the
code.

**What went wrong to prompt it.** The payload **named one source and read
another, in both countries.** Every Spanish city ranked an AEMET 2026
value against a history from ECA&D, a research archive that cannot be
published commercially; every French city named Météo-France and read
ECA&D too. It survived because the current-year value genuinely did come
from the named source, so every check of recent data passed.

**Murcia was worse: it was not one station.** ECA&D publishes that series
under the name of an air base 10 km outside the city while splicing the
city station into recent decades. Our pairing matched by name, so the
history came from the air base and the 2026 value from the city. The
published rank had compared two different thermometers. A blended record
agrees perfectly with its first component until the splice, so this is
invisible to any check that scores a record as a whole.

The completeness bar was also being applied over the wrong window: a
whole-year rule on a series cut in early August discarded Madrid 1936,
which is complete to the cut, while keeping years whose missing days fell
in July.

**What it left open.** Murcia's correction costs 42 years of record, and
the station that is correct for a page named Murcia is also the one that
keeps a record for 2026; the alternative would take the channel from
eight records to seven. The northern European cities still have no
working night metric. The French thresholds still rest on a method
borrowed from another country's service.

### v1.0, 2026-08-06

**What changed.** First publication. Fifteen cities, tropical nights
counted against each city's own record, with per-city extreme-heat
thresholds derived but not yet rendered.

**What went wrong to prompt it.** Not applicable; this is the baseline.

**What it left open.** Hot days were computed for ten Spanish stations
and no French ones, leaving the channel structurally lopsided. Sourcing
was not yet verified against publication licences.
