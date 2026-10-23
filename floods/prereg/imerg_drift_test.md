# Pre-registration: does IMERG Late set records more often in recent years?

Science's condition 4 (D-318 thread). Written and committed BEFORE any
data for this test was downloaded; the commit time is the evidence.

## The question

IMERG combines whichever microwave satellites were flying, and there were
fewer before the GPM Core Observatory launched in February 2014. If heavy
rain was sampled less well early on, recent years would set records more
easily for reasons that have nothing to do with rain. That produces records
that are not real, the failure that matters. This test asks whether recent
years hold the record more often than chance, in windows chosen without
reference to any storm.

## Fixed in advance

- **Windows**: seven days starting 10 Jan, 10 Mar, 10 May, 10 Jul, 10 Sep
  and 10 Nov. Six weeks evenly spaced through the year, chosen by the
  calendar, not by any event.
- **Years**: 2001 to 2025, 25 years. 2000 is excluded because the archive
  begins in June 2000; 2026 because it is the year the channel would claim
  records in.
- **Product**: IMERG Late V07 (GPM_3IMERGDL) only, every year. Reduced to
  0.5 degrees by floods/global_week_anomaly.py, unchanged.
- **Cells**: land only (ERA5 land-sea mask at least 0.5); observed on all
  seven days in every year of that window; a maximum weekly total of at
  least 1 mm; and a single record year (ties excluded).
- **Per window**, each year's **record share** is the fraction of eligible
  cells where that year holds the maximum. Chance is 1 in 25, 4%.

## The criterion

Primary, one-sided: S = the sum over the six windows of (mean record share,
2014 to 2025) minus (mean record share, 2001 to 2013). Null distribution by
shuffling year labels within each window, 10,000 times; shuffling whole
years keeps each year's spatial pattern intact, so neighbouring cells
moving together cannot fake a result.

**FAIL, biased toward the present, if p < 0.05.** Then satellite rankings
cannot carry a public record claim until corrected.

Reported alongside, not part of the criterion: the reverse direction (bias
toward the past, which makes records harder to set and is the safe side),
and the rank correlation between year and mean record share.

A year the script excludes for a missing day is dropped from that window
only, and named in the result.
