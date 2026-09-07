# Tracked sources, not a cache

These 28 per-city daily series are committed. `heat/.cache/src/` is not, and
the difference is deliberate.

## The rule

**The test is not "is this re-derivable in theory" but "can the machine that
needs it re-derive it within its own budget."**

Platform's wording, and it is better than the one this file first carried
("cheap to regenerate"), because it is machine-relative. AEMET is re-derivable
by the laptop over about two hours and not by a 45-minute CI job, so for CI's
purposes it is a source while remaining a cache locally. That resolves the
apparent contradiction without making `.cache/` half-trustworthy, which is
what an "exception" would have done.

Everything here CAN be rebuilt. The question is by whom, and inside what
budget.

    heat/.cache/src/     514 MB   DWD, KNMI, MeteoSwiss, SMHI, CHMI, FMI,
                                  GeoSphere, Meteo-France. Each fetcher pulls
                                  a whole archive in one call. Disposable.
    heat/data/sources/    21 MB   The ten AEMET cities and the eighteen
                                  assembled ones. Tracked.

**AEMET**, ten cities. AEMET serves 3-month windows behind a hard rate limit,
so a full rebuild is four requests per year per city: **79 minutes of enforced
sleep** before latency and before its asynchronous second step. The weekly
refresh appends a 30-day tail instead.

**The eighteen assembled cities**, built by `build_london.py`, `build_uk.py`,
`build_tallinn.py`, `build_argentina.py` and `build_bridge.py`. These bridge a
long archive with the station's own bulletins, so rebuilding one re-fetches
years of SYNOP to gain a few days. The weekly job's `fetch_*.py` glob never
reaches them, which is a second reason their output has to persist.

## What this is NOT about

**It is not about the data being irreplaceable.** Heat raised it that way on
2026-09-07 and was wrong: the irreplaceable INPUTS were already committed,
and they still are, one directory up.

    heat/data/official/tallinn_keskkonnaagentuur.xlsx     supplied by email
    heat/data/official/Heathrow_Jan_2026-Present.xlsx     Met Office NMLA
    heat/data/official/Aldergrove_Dyce_Nottingham_*.xlsx  Met Office NMLA
    heat/data/histories/*_midas.json.gz                   four MIDAS baselines
    heat/data/latam_gather.json                           station identity

`build_uk._frozen` explains the MIDAS case in its own docstring, and it was
written to solve exactly this: those cities "become buildable on a machine
that is not this laptop for the first time."

## Plain JSON, deliberately

Gzip measured about 35% smaller here even after git's delta compression, so
this costs real space. It is still plain, because a gzipped blob is "binary
files differ" in every diff, invisible to any guard that walks tracked files,
and unreviewable by a human checking what a weekly refresh actually changed.
In a repo whose discipline is that a change nobody can inspect did not really
happen, readability wins. If the total ever gets uncomfortable the answer is
fewer tracked files, not opaque ones.

## Why not heat/data/histories/

That directory solves a similar-looking problem and is not the same one.
Measured 2026-09-07:

    histories/aberdeen_midas.json.gz    1957-01-01 .. 2025-12-31
    histories/london_midas.json.gz      1949-01-01 .. 2025-12-31
    sources/aemet_Madrid.json           1920-01-01 .. 2026-09-03
    sources/london.json                 1949-01-01 .. 2026-08-21

**Everything in `histories/` ends in 2025 and never moves again**, which is
why gzip is right there: MIDAS Open publishes in arrears and will not change.
**Everything here runs into 2026 and advances weekly.** Same shape on disk,
opposite lifecycle, and the gzip argument flips with it.

`sources/london.json` is also DERIVED FROM `histories/london_midas.json.gz`
plus the Met Office workbook. Filing a live series beside its own frozen
input, under a near-identical name, is how somebody eventually rebuilds one
from the other and loses the 2026 season.

## Adding a city here

Resolve the path through `source_file()` in `build_city_series.py`. It
classifies by filename prefix and deliberately does **not** fall back from one
directory to the other: a fallback would mean a missed writer leaves the file
in both places, with the tracked copy stale, and a resolver preferring it
reads perfectly while serving last month's data. Classification instead makes
a missed writer produce a file nothing reads, which the pre-flight in
`main()` reports by name.

Platform's call, 2026-09-07. Written up here rather than in a commit message
because the next person to wonder why 21 MB of JSON is tracked will look in
this directory.
