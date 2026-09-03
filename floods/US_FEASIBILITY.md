# Can we test the El Nino US precipitation signal against floods?

Asked by science, 2026-09-03, for aftereffects' US work. This is the
feasibility answer, not the analysis.

## What this channel holds for the United States

Nothing. Verified rather than recalled, and two apparent hits were both
false positives worth naming:

- `design/review/map-field-variants.png` matched a case-insensitive
  search for "nwis". The match is the byte sequence `nwIs` inside a PNG.
  A grep across binaries will do this, and it is the mirror of the usual
  trap: not a search that misses what exists, a search that finds what
  does not.
- `floods/data/offset_eu_us_week*.json` are the MCDWD science-versus-NRT
  product crossing, measured over European and US scenes. They contain no
  US flood data. The filename carries "us" and nothing else does.

## The right instrument exists, and it is better than what we use elsewhere

USGS NWIS daily values, parameter 00060, discharge. Probed 2026-09-03:

    Florida discharge gauges with daily values        3,623
    of those with 50 or more years of record            351
    of those still reporting in 2024 or later           319
    longest record found            Suwannee River at White Springs,
                                    1906 to present, 120 years

**These are gauges. Observed, not modelled.** That matters more here than
anywhere else this channel works, because of what it changes about a
negative result. See below.

## Why the European GloFAS finding does not transfer

D-275 concluded: do not run the Mediterranean SST correlation, because
GloFAS is selectively blind to small steep flash catchments and a null
would be an artefact.

**That reasoning does not carry to Florida, and neither does its
conclusion.** The European failure was a resolution failure against fast
steep hydrology. Florida is the opposite: flat, low-relief, slow. GloFAS
would probably still represent it badly, but for an unrelated reason,
that Florida's hydrology is heavily engineered, with canals, water
control structures and pumped drainage, and that much of its flood risk
is pluvial and coastal rather than fluvial. A model of natural river
routing is the wrong instrument for that landscape.

The conclusion inverts:

    Europe, GloFAS      do not run it. A null would measure the
                        instrument, not the world.
    Florida, USGS       run it. With observed gauges a null is a real
                        null, and that is a result rather than a gap.

## What the test would be

DJF maximum daily discharge per gauge per winter, ranked within that
gauge's own record, against ONI for the same winter. Daily values answer
science's own stated limit directly: climdiv is monthly, so it measures
seasonal totals, and floods are driven by daily intensity. USGS dailies
are the intensity.

## The screen that has to come first

**Regulation.** Many Gulf and Florida gauges sit below dams, diversions
or managed water bodies, and a regulated gauge records the operator's
decisions as much as the weather. Any correlation run without screening
for this measures reservoir policy. USGS peak-streamflow records carry
qualification codes for regulation; the daily-value sites do not carry
them as directly, so the screen is real work and not a flag lookup.

Until that screen exists, no number from this should be quoted.
