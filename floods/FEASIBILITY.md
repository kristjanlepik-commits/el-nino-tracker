# Floods (FLO): baseline feasibility report

Status: Phase 1 deliverable under D-032, for Kristjan's decision.
Author: FLO chat, 2026-07-28. Brief: `research/handover_floods.md`.
Nothing here is published; this report decides whether a channel opens.

## Verdict

**Open floods, on two instruments rather than one, with two publish
gates the data itself dictates.**

The brief warned that floods was the channel most at risk of failing
the D-033 gate, on the reasoning that global flood information tends to
be a curated event catalogue rather than a measurement. That was true
of the leads named in the brief. It is not true of the instrument that
turned out to exist, which the brief did not mention because it was
released three months ago.

**NASA's MODIS Global Flood Product (MCDWD) reached Measured.** A
reprocessed science-quality archive covering 2000 to 2025 was published
on 6 April 2026: daily, global, 250m gridded flood extent, distributed
through the same LANCE and LAADS infrastructure the Fire channel
already uses. Usable full coverage begins in 2003, when Aqua joined
Terra, giving **23 complete years**.

Tested against two reference events on two continents and two flood
mechanisms:

| Region | Mechanism | Reference | Result |
|---|---|---|---|
| Coastal Peru and Ecuador | Rainfall-driven coastal | 2017 coastal El Nino | **rank 1 of 23**, 12.0x median, +4.7 sigma |
| Juba and Shabelle, Somalia | Slow riverine | 2023 Deyr floods | rank 3 of 23, 6.1x median, +2.1 sigma |
| Tana, Kenya | Slow riverine | 2023 Deyr floods | rank 1 of 23, but counts too small to trust |

**The Somalia result is the one that should carry weight**, and it is
stronger for not putting the reference year first. Ranked blind, its
top five are 2019, 2006, 2023, 2020, 2024. Independent sources describe
2019 as Somalia's worst flooding in recent history, 2020 as affecting
close to a million people, and 2023 as the worst in decades. The
instrument identified the known worst year without being told anything
about events. Had 2023 come first, a working instrument would have been
indistinguishable from a lucky choice of reference.

**A second instrument is required, not optional.** GPM IMERG
precipitation (0.1 degree, daily, June 2000 to present) measures
rainfall, not flooding, and must be labelled as such everywhere. It
earns its place because it correlates with flood extent at only
**Spearman +0.23** outside extreme events. The two answer different
questions, agreeing sharply only on major events, which is physically
what one expects since flooding depends on antecedent soil moisture and
upstream river state rather than on local weekly rain. Neither
validates the other. Both are needed, and they must never be merged
into a single number.

**Two gates, both derived from the data rather than imported:**

1. **Observability comparability.** The current period's observed
   fraction must sit inside the baseline distribution for that region
   and week. Not an absolute floor: a literal 0.6 threshold would
   delete 22 of the 23 Peru baseline years.
2. **Minimum count, near 300 flood pixels.** Below it, the two MODIS
   products stop agreeing with each other and the measurement is noise.

**One thing is already time-critical and is running.** See section 7.

## 1. What was tested

Everything below was measured against live data pulled on 2026-07-28,
not read from documentation. Where a documented figure and a measured
one disagree, the report uses the measured one and says so.

    MCDWD flood extent   23 years x 7 days x 3 regions      483 day-records
    IMERG rainfall       26 years x 7 days x 3 regions      532 day-records
    Product comparison   20 paired days, science vs NRT
    Instrument overlap   7 paired days x 4 regions, MODIS vs VIIRS
    Volume moved         roughly 20 GB, of which 1.5 MB retained

Artifacts are committed under `floods/data/` as JSONL, one record per
region-day, carrying the full value histogram rather than a derived
flood count so the legend could be resolved after the fact rather than
assumed during collection.

## 2. The leads in the brief, and what happened to them

**GloFAS**, the brief's strongest candidate, is real and accessible but
was not needed. It is on the CEMS Early Warning Data Store rather than
the CDS, which the brief did not know; the existing ECMWF token
authenticates there, so access was never the obstacle. River discharge
from 1979 to two days ago, no sensor discontinuity, no cloud problem.
Its weakness is that it is **modelled**, LISFLOOD forced by ERA5, not
observed. It is retained as a backstop and as a third view, not as the
spine, because an observed instrument was available.

**Dartmouth Flood Observatory** is still maintained (v4.6) and its
River Watch satellite gauging at 2,500+ reaches is genuinely measured
and genuinely long (1998 to present). It is point-based rather than
areal and rests on one small university group. Good validation layer,
poor spine.

**Global Flood Database** is a closed series: 913 curated events, 2000
to 2018, ended. Confirmed dead as a baseline.

**GDACS** is alert-driven and editorial by construction, as the brief
predicted.

**AER FloodScan** is the strongest thing we cannot have. Daily global
flood extent from 1998, passive microwave so cloud-penetrating, with
baseline comparisons already built in. The free HDX slice covers only
the last 90 days and ships FloodScan's own baseline, which would make
us **Compiled** rather than Measured. Kristjan's constraint that
nothing is paid for while there is no revenue stream rules out the full
archive. Retained as a free cross-check.

**Copernicus GFM** (Sentinel-1 SAR, 2015 to present) is cloud-
penetrating and high resolution, and was rejected on a specific
ground: Sentinel-1B failed in 2021 and 1C only joined recently, so the
number of looks per place per week changed mid-record. A series whose
observation density changes is exactly what a baseline cannot tolerate.

## 3. Brief Q1: is there a continuous measured series?

Yes, two.

**MCDWD**, 2000 to 2025 in the archive, usable from 2003 when Aqua
joined Terra and global coverage completes at 287 tiles per day. 23
complete years, 161 of 161 day-records retrieved per region, no gaps.

**IMERG**, June 2000 to present at 0.1 degree, 26 years, no gaps, and
structurally cheaper: one global file per day rather than tiles, and
OPeNDAP server-side subsetting returns **38 KB per region-day against
34 MB for the whole file**. A 26-year same-week baseline for a region
is about 7 MB and a few minutes. IMERG gets cheaper as regions are
added; MCDWD gets more expensive.

## 4. Brief Q2: comparison without a human deciding what counts as an event

Yes, and this is the core of the verdict. The measure is flood pixels
in a fixed box over a fixed calendar window, compared against the same
window in every prior year. No event is declared, nothing is selected,
and the arithmetic is identical every week.

**The decisive check was whether cloudiness drives the ranking**, since
floods arrive with cloud and the instrument is optical. Across 23 years
in Peru, the Spearman correlation between a year's observability and
its flood measure is **+0.05** on raw counts and **-0.04** adjusted.
Cloudy years do not read high or low. 2017 itself sat below median
observability, so its ranking is if anything understated.

The same check in Somalia returns **+0.25**. Not significant at n = 23,
but the wrong sign to ignore, and it is recorded as an open item rather
than filed away.

## 5. Brief Q3: latency, and is the recent end consistent with the archive?

This was the more fundamental question, ahead of the instrument
succession problem, because baselines come from the archive and current
weeks arrive as near real time. If the two disagree, every published
comparison measures the product change rather than the weather.

**It passes.** December 2025 is the only window where LAADS holds both
`MCDWD_L3` and `MCDWD_L3_NRT`. Over 20 paired days:

    observability     median absolute difference 0.0002, worst 0.0066
    flood, period     5,119 science pixels vs 5,155 NRT, ratio 1.007
    days >= 300 px    n=5,  median ratio 1.003, range 0.93 to 1.17
    days <  300 px    n=15, median ratio 0.906, range 0.54 to 1.77

The two pipelines see the same ground. The day-to-day scatter is a
function of count magnitude, not bias, and it is where the 300-pixel
floor in the verdict comes from.

**Latency, measured rather than documented.** IMERG's Final Run is
documented at 3.5 months. Its newest granule is 2025-09-30, a **ten
month** lag. Late and Early Runs are both at one day. Near-real-time
work is therefore fine, but any baseline window after September 2025
crosses a product boundary and needs the same treatment MCDWD just
received. MCDWD's own near-real-time latency is under a day.

## 6. Brief Q4: honest resolution, and what it misses

250m native, aggregated to 0.1 degree for storage. Daily. Global except
the poles.

**What it misses, stated as a number rather than a caveat.** The
instrument is optical, so it looks away exactly when the news happens.
Over the Ganges and Brahmaputra delta at the height of the monsoon,
observability across seven days ran from **0.123 to 0.710**. On the
worst day the instrument could see one seventh of the region.

This is survivable only because the product ships `ValidCounts`, an
observation denominator per pixel per day. **The blindness is itself
measured.** Without it, 21 July would have read as "641 flood pixels",
looking like a quiet day in Bangladesh in July, which would have been a
badly wrong thing to publish. Fire has no equivalent: a hotspot count
cannot tell you how much of the region was under cloud.

Observability is strongly regional and seasonal, and East Africa is far
kinder than coastal Peru: mean 0.93 on the Juba and Shabelle, 0.85 on
the Tana, against 0.61 in Peru in March.

**Also missed**, and not recoverable: flash floods shorter than the
compositing window, urban drainage failure, and flooding under dense
canopy. The product finds standing water in the open.

**Flood is defined against a stale mask.** Detected water outside
MOD44W, a static 2009 reference water map, is called flood. NASA is
candid that reservoirs built since, rivers that changed course and
shifted coastlines all read as permanent flood. The absolute number is
therefore not trustworthy. The error is static and identical every
year, so it very largely cancels in a same-week ratio, which is the
only claim we make. `WaterCounts` is retained alongside as a
mask-independent fallback.

## 7. The MODIS shutdown, and the one thing already time-critical

MODIS is switched off during the event this project exists to cover:
Aqua around August 2026, Terra around January 2027. The 23-year archive
is a MODIS record.

**The VIIRS successor (VCDWD) has no archive anywhere.** Verified three
ways on 2026-07-28: LAADS archive set 5200 holds no VCDWD collection;
CMR returns zero granules for May 2025 and March 2026 despite
advertising coverage from April 2025; the LANCE server retains about
seven days and then deletes. The successor instrument has a seven-day
memory.

**The reconciliation itself is tractable.** Over the Ganges at high
observability, VIIRS runs a stable **1.85x** MODIS:

    observability 0.12-0.15   ratio 160x to 388x   meaningless
    observability 0.25        ratio 7.0x, 4.1x     unusable
    observability 0.53-0.61   ratio 2.6x
    observability 0.70        ratio 1.76x, 1.93x   stable

A stable multiplicative offset is correctable. An earlier reading of
this, taken over dry-season boxes with counts in the tens, appeared to
show the two instruments disagreeing in opposite directions by region;
that was noise over noise and is retracted. VIIRS also **sees more
ground than MODIS** (median observability 0.44 against 0.26), so the
succession is a point in the channel's favour once the offset is
measured.

What is not tractable is time. Per **D-038**, a daily global VIIRS
capture is running: 3.57 GB in per day, reduced to 0.1 degree
aggregates of single-digit MB, raw discarded. It buys an option against
an asymmetry. NASA may yet archive VCDWD themselves, as they did for
MODIS NRT in January before reprocessing the whole record in April, and
that is more likely than not. Capturing costs a little disk; not
capturing is unrecoverable.

## 8. Evidence basis and authorship

**Measured** under D-033, for each instrument separately.

- Flood extent: one continuous series against its own history.
- Rainfall: one continuous series against its own history.

They are **not** to be combined into a single number. Presented side by
side they are two measurements; averaged or blended they become
Combined at best, and D-033 makes Combined the exception rather than
the register. The +0.23 correlation is the reason: two things that
disagree that much are not measuring one underlying quantity.

Authorship is `agency` throughout. Every number is a NASA product
aggregated against its own record. TLS authors no flood estimate, no
probability and no forecast.

## 9. What the data requires before anything publishes

1. **Observability comparability**, not an absolute floor. The current
   period's observed fraction must sit inside the baseline distribution
   for that region and week. A literal 0.6 floor, derived from the
   cross-instrument work, would delete 22 of 23 Peru baseline years,
   because comparing one instrument against its own history is a less
   demanding test than comparing two instruments against each other.
2. **Minimum count near 300 flood pixels**, below which the two MODIS
   products stop agreeing with each other.
3. **Quiet weeks must be allowed to be unreportable.** Where either
   gate fails, the honest output is "we could not see", not a number.

## 10. Traps recorded

- **Region geometry moves the answer by a factor of four.** Peru 2017
  reads 1.8x the median over a regional rectangle and 4.4x over the
  Piura and Chira catchments alone. Flood regions are catchment-shaped,
  not box-shaped, and Fire's rectangular region boxes would
  systematically understate flood events.
- **And boxes can be too small.** The Tana's median week is 157 flood
  pixels, under the 300 floor. Peru's box diluted the signal; Kenya's
  destabilised it. There is a workable band between them and it has not
  been mapped.
- **Use rank on record, never a fixed multiple.** The Fire chat found
  a fixed 1.5x gate meaningless across regions, because fire has two
  variance regimes: fuel-limited savanna repeats on schedule (CV 0.06)
  while weather-limited boreal waits for its year (CV 0.97), so one
  threshold means 8.9 sigma in Mozambique and 0.5 in Canada. Tested
  here: floods does not split that way, because there is no
  fuel-limited analogue. Flooding is weather-limited everywhere, so all
  three regions sit in the high-variance regime (CV 0.84 to 1.31) and
  1.5x median lands within a quarter of a sigma of the same place in
  each. But that is the wrong kind of pass: **1.5x is only about -0.2
  sigma here and would fire in 6 to 9 years out of 23.** A gate that
  trips a third of the time detects nothing. Rank on record is
  non-parametric and immune to the regime question entirely.
  Untested and worth checking before launch: a basin that floods every
  year, such as the Ganges delta, may be the low-variance case that
  does behave like savanna.
- **A global ranking by raw flood pixels is dominated by artifacts.**
  Checked against the first captured global day (2026-07-21): the top
  five tiles worldwide sit at 60 to 80 degrees north, in east
  Greenland, Iceland, Siberia and the Norwegian Sea. In late July those
  are snow and ice melt falling outside the stale 2009 water mask, plus
  low-sun-angle shadow, which is the same regime NASA's own evaluation
  found the product's errors concentrating in. The only plausible entry
  was `h21v08`, the Ethiopian highlands feeding the Juba and Shabelle
  in their rainy season. Any "biggest floods worldwide" list must rank
  by abnormality against a local baseline, never by raw count. Fire
  reached the same conclusion visually and colours its map by
  abnormality for the same reason; this is the numerical form of it.
- **255 does not mean dry.** It means "insufficient data" and NASA
  states it may be a false negative. Treating it as "no flood" would
  manufacture a decline every cloudy week.
- **The 1-Day composite is contaminated.** It requires a single water
  detection and NASA warns of substantial cloud-shadow false positives.
  All work here uses the 3-Day composite, which requires three.
- **A same-week baseline measures that week, not that year.** Somalia
  2018 saw one of Beledweyne's biggest floods in recent history and
  ranks 17 of 23 in this report, because that event was in the Gu
  season and this window is Deyr.
- **Three separate Earthdata approvals.** GES DISC, LAADS and LANCE are
  distinct OAuth applications and approving one does nothing for the
  others. Failures look different: GES DISC returns a clean JSON EULA
  error, LAADS silently serves an HTML login page with HTTP 200.
- **Tokens expire at 60 days.** The current one dies 2026-09-26, inside
  the event window.
- **HDF5 is not thread-safe in this build.** It hangs rather than
  crashing. Downloads are handed to curl for this reason; see the
  session record.

## 11. If floods opens

Phase 2, in dependency order:

1. Map the workable region-size band, between Peru's dilution and the
   Tana's instability, then draw regions on catchments.
2. Freeze baselines per region and calendar week, immutable, in the
   pattern of `fires/fire_baselines.md`.
3. Continue the VIIRS capture and measure the MODIS-to-VIIRS offset per
   region rather than relying on the single Ganges figure.
4. Design the emitted JSON with ECON's agreed field set (see section
   12) and the D-030 discovery process.
5. Hand platform the five items from the platform contract.

## 12. Open questions for Kristjan

1. **Is the two-instrument design accepted?** It is twice the
   machinery, and rainfall will sometimes contradict flood extent in
   public. My view is that the contradiction is the honest content, but
   it is a product decision.
2. **The Somalia observability correlation of +0.25.** Not significant
   at n = 23, wrong sign to ignore. Re-test before launch, or accept?
3. **Region count.** Bandwidth and baseline cost both argue for few,
   well-chosen catchments. How few?
4. **The live Ganges flood.** A real event is developing now with a
   26-year baseline and working machinery, before this channel formally
   exists. Editor and strategy call, not mine.

## 13. Session record, 2026-07-28

Access path established: Earthdata token, three application approvals,
`pyhdf` needed for HDF4 and not present in the repo `.venv` (a pending
dependency request to platform; all MCDWD work here ran against a
scratch venv).

Instruments built: `fetch_mcdwd_baseline.py`, `fetch_imerg_baseline.py`,
`compare_products.py`, `capture_nrt_overlap.py`,
`capture_viirs_global.py`.

Four claims made during the session and later corrected by measurement,
recorded because the corrections are part of the evidence:

- That near-real-time MODIS ran hot relative to the archive. It does
  not; the December comparison settles it at 1.007.
- That MODIS and VIIRS disagreed in opposite directions by region. That
  was noise over noise at counts in the tens.
- That NASA throttles per account at 1.3 MB/s. Measured while one job
  was deadlocked and contributing nothing; two healthy jobs reach 2.2
  MB/s combined. A correction was sent to platform.
- Two successive diagnoses of a hanging capture job, both wrong, before
  the thread pool was replaced with curl.
