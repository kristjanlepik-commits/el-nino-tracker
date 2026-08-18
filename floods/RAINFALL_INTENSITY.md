# What the rainfall instrument can and cannot say about intensity

Measured 2026-08-18 against gauges, at product's request, because rainfall
became the European instrument when flood extent failed 0 of 6 European
regions in the screen. A limit on one of two instruments is a caveat; a
limit on the only instrument is a limit on the channel.

## The test

Valencia DANA, **29 October 2024**. Chosen because it is the most extreme
convective rainfall event in recent Spanish record, so if IMERG under-reads
anywhere it under-reads here, and because Spain is where the European build
actually is.

Ground truth is 853 AEMET stations for that day, joined to coordinates from
the station inventory. Comparison is **paired at station locations**, not
maximum against maximum, because max-against-max also folds in position
error and would flatter or damn the instrument for the wrong reason.

45 stations fall inside the box.

## The result

    gauge maximum          TURIS      710.8 mm
    IMERG at TURIS                    128.1 mm     ratio 0.18
    IMERG maximum cell anywhere        182.1 mm     26% of the gauge peak

**And the shape matters more than the headline.** Binned by how much
actually fell, GPM_3IMERGDL:

    gauge under 10 mm    n=29   gauge   2.6   IMERG  14.8   ratio 5.80
    gauge 10 to 50 mm    n= 4   gauge  23.8   IMERG  18.9   ratio 0.79
    gauge 50 to 150 mm   n= 9   gauge  82.3   IMERG  57.0   ratio 0.69
    gauge over 150 mm    n= 3   gauge 366.9   IMERG 119.4   ratio 0.33

This is not a scale error, it is **smoothing**. IMERG puts rain where
little fell and takes it from where much fell, which is what an 11 km
footprint does to a 5 km convective cell. The Final Run smooths harder
than the Late Run at the dry end (ratio 12.28) and no less at the wet end
(0.30), so science quality does not rescue it.

**A multiplier cannot correct this**, because the bias runs from 5.8x
over-reading to 0.33x under-reading across the same field on the same day.

## What follows for the channel

**Never report an intensity, a peak rate, or a flash-flood magnitude from
IMERG.** At the one station that defined the event it reads 18% of truth.

**Year-to-year rankings remain sound when the years compared are of similar
event character**, because the bias applies to every year alike and largely
cancels in a rank. That is the claim the channel actually makes.

**But rankings are biased AGAINST convective years.** A convective extreme
reads lower than a frontal one of equal true magnitude, so a persistent wet
spell can out-rank a genuinely wetter cloudburst. Any ranking near the top
should be checked against event character before it carries an ordinal.

Worked example, the eastern Pyrenees fortnight that prompted this: 2026
concentrates 23% of its total into its wettest day and 2009, the runner-up,
concentrates 28%. **The two are of similar character, so differential
smoothing cannot explain the gap between them** and the rank-1 finding
survives. Had 2009 been a 60% single-day event the ordinal would not have
been safe.

One caution on that diagnostic: the correlation between fortnight total and
top-day share is -0.36, and it must NOT be read as evidence of instrument
bias. Top-day share carries the total in its denominator, so the two are
mechanically linked. That is Pearson's 1897 spurious correlation of ratios,
the same trap the qualification gate is built to avoid, and it is why the
comparison above is between two named years rather than across the sample.

## Does half-hourly IMERG fix it? No, and it is not worth the cost

Product costed half-hourly at 18,048 fetches per region-window against 376,
so five to ten hours per region per window.

**It would buy temporal detail on a spatially smoothed field.** The failure
measured here is the 11 km footprint against a 5 km cell, which is a
sampling-scale problem that finer time steps do not touch. The peak would be
resolved in time and still wrong in magnitude.

So the global satellite route is the wrong instrument for mid-latitude
convection, and the answer is gauges: MIDAS for the UK and AEMET for Spain,
both of which we hold credentials for. AEMET was used for this test.
