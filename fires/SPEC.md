# Forest Fire Tracker: product spec (v1)

Status: draft for Kristjan's review, 2026-07-25.
Parent: the 2026-27 El Niño weekly tracker (this repo).
Kickoff context: `research/handover_fire_tracker.md`.

## Decision log

Confirmed with Kristjan 2026-07-25:

1. **Audience: public from the start, unlisted until ready.**
   (Supersedes the internal-first call made earlier the same day.)
   The tracker ships as a public GitHub Pages surface immediately,
   but is not linked from the parent front page and not promoted
   until Kristjan decides to share it.
2. **Placement: this repo, `fires/` directory.** Reuses
   `fetchers/_common.py`, the `.venv`, the Monday cadence, and the
   research base in `research/impact_database_2026-27.md`. Split
   criterion: the tracker goes public with its own identity, or grows
   past two or three fetchers; then it graduates to its own repo.
3. **Automation: one fetcher in v1.** NASA FIRMS area API for weekly
   same-sensor hotspot counts per region box. Burned area, emissions,
   and damage stay manually curated.
4. ~~**Damage scope: health-cost estimates included**, always labeled
   as study-based and years-lagged, never mixed into direct or insured
   comparisons.~~ **SUPERSEDED 2026-07-28 by D-032.** Money is ECON's
   surface: the cross-channel damage ledger, named estimators, issue
   dates, vintage and revision history. Fire consumes that ledger and
   does not track loss figures itself. The reasoning inside the struck
   text was sound and ECON's schema now enforces a stricter version of
   it, including a category enum that keeps humanitarian appeals
   unsummable with losses and a validator that rejects a monetised
   mortality figure not linked to the death toll it prices.

   Kept as a caution: this decision was ratified on 2026-07-25 from
   research/handover_fire_tracker.md, which was itself written before
   the decisions that moved money to ECON. The damage layer here was
   never wrong when written; it was overtaken three days later, and
   nothing in the file said so until aftereffects flagged it.
5. **Cadence: one automated update per day**, plus the curated weekly
   issue on Mondays. Twice-daily considered and rejected for v1; see
   "Update cadence" for the reasoning and the peak-week escalation
   path.
6. **Three comparison frames on the page** (from the 2026-07-25 mockup
   review): analog El Niño years (is this like 2015/2023/2024?), the
   single-sensor climatological norm (how far from normal?), and a
   global top-clusters list for context. Daily windows shown: 1, 7,
   and 15 days. The climatology is the same-calendar-week mean and
   per-year values over the SNPP-only VIIRS record (2012-2025),
   presented as a multiple of the mean plus rank-on-record; rank is
   the sturdier reading given the short record and warming trend.
   A month-average alternative was considered and rejected: fire
   seasons ramp too steeply within a month.

## Mission

REFRAMED 2026-07-29 by D-042 and D-043. ENSO is a data layer, not the
frame. The bar for covering a country is a computable baseline and a
measured extreme, NOT an established ENSO link, and "not ENSO-linked"
is a finding rather than an apology. This channel tags zero of 45
countries as ENSO-linked and its strongest 2026 anomaly is the
Mediterranean, its own declared control region; under the old weighting
that read as a disappointing result, and it is simply what the
measurements say.

The gate implements this already: it ranks on z-score, multiple and
rank-on-record against each country's own history, and ENSO appears
nowhere in it.

A weekly tracker that measures, for any region with a computable
baseline (originally: for the El Niño-relevant fire regions):

1. **Fire activity, observed**: what is burning now, quantified against
   same-week analog-year baselines.
2. ~~**Economic damage, attributed**: what the fires cost, per named
   institutional estimator, with issue dates, revisions tracked as
   data.~~ **Moved to ECON, D-032.** Fire consumes their ledger. The
   mission is levels 1 to 3 of the metrics ladder and all six
   measurement traps; the money layer is a dependency, not a build
   item.

Same epistemic posture as the parent brief: aggregation of named
sources, disagreement surfaced not averaged, no original modeling. The
edge is baseline discipline (this week vs the same week of the analog
years) and vintage discipline (damage numbers dated and revised
transparently).

## Users and delivery

- **Surface: a public GitHub Pages page from day one**, at
  `docs/fires/` on the existing site
  (kristjanlepik-commits.github.io/el-nino-tracker/fires/). Live but
  unlisted: no link from the parent front page, no promotion, until
  Kristjan decides to share. Going live early means the format
  hardens in public conditions without an audience watching yet.
- **Two-layer product on one surface:**
  - The **daily activity layer** updates automatically once per day:
    per-region hotspot counts vs baselines, data-only, fixed
    disclaimer language, a visible "last updated" stamp. Mutable by
    nature; it shows current state.
  - The **weekly issue** (Mondays) is the curated product of record:
    lede, analog comparisons, freshness footer, and a damage panel
    rendered FROM ECON's ledger rather than tracked here (D-032).
    Immutable once published, parent-archive rules.
- **Kristjan reads the same page.** No separate internal artifact; the
  weekly issue markdown in `fires/` is the source the HTML is rendered
  from, same relationship as the parent brief.

## Update cadence

One automated run per day, timed so that every region's previous
local day is complete. The reasoning:

- Each VIIRS satellite sees a region twice a day (~01:30 and ~13:30
  local), with ~3 h processing latency. A region's day is complete a
  few hours after the afternoon overpass, once per day.
- A twice-daily publish would alternate full-day and half-day counts.
  A half-day count reads as a die-down to a casual reader; that is a
  self-inflicted version of the measurement traps this spec exists to
  avoid. Every published daily number should be a complete day.
- The run slot is chosen at build time (roughly 10:00-12:00 UTC works:
  by then the previous UTC day has cleared its last afternoon overpass
  in every tracked region, including Indonesia and Australia).
- **Escalation path**: during an extreme week the cron can be flipped
  to twice daily, with the second run labeled "today so far, partial
  day" and excluded from day-over-day comparisons. One-line change,
  decided by Kristjan, never silently.

## Scope: regions and windows

| Region | Fire window | Framing |
|---|---|---|
| Amazon / Brazil (+ Bolivia, Peru) | Aug-Oct 2026, peak Sep | R4 El Niño drought-fire. 2024's ~2.8 M ha primary-forest burn is the standing mark |
| Indonesia / Maritime Continent | Aug-Oct 2026 | R5. Peatland fire and haze; 1997 and 2015 are the two worst modern precedents |
| Australia | Nov 2026-Feb 2027 | R4. One line until the season opens; analogs are 2015-16 and 2023-24, never Black Summer (non-El Niño) |
| US West (California, PNW) | Now-Oct 2026 | In scope, flagged: ENSO link weak. Report activity, never imply El Niño causation |
| Mediterranean | Jun-Sep 2026 | Non-ENSO control, kept visible deliberately as part of the credibility posture |

Canada boreal is out unless a signal appears; its ENSO link is weak.

## v2 investigation: the gate threshold is not comparable across countries

Raised 2026-07-29 from the first completed full-year baselines, and
flagged by Kristjan as worth a proper investigation rather than a quick
patch. Not yet acted on. The gate still ships as described below.

Fire countries sit in two statistical regimes, and a fixed multiple
means something different in each:

    country      mean/yr    CV    14-year range
    Mozambique   662,127   0.06   0.90 to 1.07x
    Zambia       711,853   0.06   0.88 to 1.08x
    DR Congo   1,680,654   0.07   0.86 to 1.10x
    Angola     1,082,161   0.07   0.83 to 1.12x
    Brazil     1,255,823   0.24   0.62 to 1.42x
    Australia  1,072,986   0.34   0.63 to 1.79x
    Canada       416,670   0.97   0.11 to 4.04x

Savanna burning is fuel-limited and largely anthropogenic, so it
repeats on schedule. Boreal burning is weather-limited, so it waits for
the year the weather allows. That is a physical difference, not a
sampling artifact.

MIN_MULTIPLE = 1.5 therefore translates to roughly 8.9 standard
deviations in Mozambique, 7.1 in DR Congo, and 0.5 in Canada. Eight of
the ten countries with full history have never reached 1.5x in fourteen
years and could not. Those eight include the four largest fire systems
on Earth by detection count. DR Congo could have its worst season on
record, register 1.10x, and never appear on the site, while Canada at
1.5x is an unremarkable year and gets a page.

Likely direction: rank on standardised anomaly, where a window sits
within that country's own distribution, rather than on a raw multiple.
That changes which countries appear, so it needs Kristjan's sign-off,
not just an implementation.

Two things to establish before building anything:

1. The figures above are ANNUAL. The gate runs on weekly windows, where
   variance is higher everywhere, so the sigma values will soften. The
   ordering should survive because it follows from the physics, but
   that must be measured, not assumed.
2. Fourteen points is a thin basis for a variance estimate. Whether the
   two regimes are genuinely distinct or a continuum with savanna at
   one end is an open question, and it decides whether a single
   standardised rule works or the channel needs regime-specific gates.

## The metrics ladder (four levels, never conflated)

1. **Activity** (daily data, automated; weekly headline): active-fire
   detections and fire radiative power. NASA FIRMS (VIIRS as the
   baseline sensor), INPE Programa Queimadas as the Brazil cross-check.
   FIRMS is near-real-time (~3 h latency, two VIIRS overpasses per
   day), so daily counts are the native resolution; the weekly number
   is their sum.
2. **Burned area** (lags by days-weeks, manual): Copernicus GWIS
   global, EFFIS for the Mediterranean, MAAP/Amazon Conservation for
   Amazon primary forest, Sipongi (KLHK) for Indonesia.
3. **Emissions** (monthly-ish, manual): GFED, Copernicus CAMS. The
   1997 Indonesia record (up to 2.57 Gt C, Page et al. 2002) is the
   standing benchmark.
4. **Economic damage** ECON'S SURFACE SINCE D-032, retained here only
   so Fire knows what it is consuming and can tell when a figure is
   being misused. Do not build against this list; read ECON's ledger.
   (slowest, most revisable, manual): EM-DAT, the
   billion-dollar disasters dataset (US only; NOAA NCEI discontinued
   it May 2025, Climate Central now stewards it with the same
   methodology), Munich Re / Swiss Re sigma (insured), World Bank
   DALA-style (total), academic health-cost studies (lagged, labeled).
   Suppression costs (NIFC, state agencies) are a fifth type, kept
   separate. Every figure carries estimator + issue date.

## Product surfaces

### 1. `fires/fire_baselines.md` (first deliverable, before any issue)

Frozen reference document; the weekly numbers are meaningless without
it. Contains, per region:

- Same-week analog-year hotspot series, sensor-consistent (VIIRS),
  for the analog years in the region table (Amazon: 2023, 2024;
  Indonesia: 2015*, 2023; Australia: 2015-16, 2023-24; US West and
  Mediterranean: recent seasons for context, no ENSO claim).
  *2015 predates VIIRS maturity for some series; where only MODIS
  exists, the baseline says so and the comparison stays same-sensor.
- Analog season totals (hotspots, burned area where sourced).
- The climatological same-week series: per region, weekly totals for
  every year of the SNPP-only VIIRS record (2012-2025), from which
  the daily page computes its mean and rank.
- The standing records from the verified anchors in the handover
  (Indonesia 2015 and 1997, Amazon 2024, Australia precedents, the
  Callahan-Mankin scale anchor). Do not re-derive; cite
  `research/impact_database_2026-27.md`.

Baselines are immutable once frozen, like parent snapshots. A baseline
correction is a dated addendum, not an edit.

### 2. Weekly issue: `fires/YYYY-MM-DD.md` (Mondays)

Structure, mirroring parent conventions:

- **Lede**: 2-3 sentences, what changed this week.
- **Per-region table**: hotspots this week (sensor named) vs same
  calendar week of the region's analog years; season-to-date burned
  area vs analog season-to-date where the source allows.
- **Daily strip**: per active region, the trailing 7 daily hotspot
  counts (same sensor), so within-week acceleration or die-down is
  visible. Daily numbers show shape only; the analog comparison is
  always the weekly total, because daily counts are noisy (cloud
  cover, overpass geometry, agricultural burning).
- **Damage panel**: named estimates only, each with estimator + issue
  date, new-or-revised flagged, in the estimator's own units. Insured,
  direct, total-economic, and health-inclusive kept in separate
  columns or rows, never summed across categories.
- **Source freshness footer**: same pattern as the parent brief, with
  each source's issued date distinct from fetch date.
- Quiet regions get one line. Quiet weeks look quiet; no padding.

Issues are immutable once written, same rule as parent archives.

### 3. Public page: `docs/fires/index.html`

Single page, generated by the fire tracker's own entry point:

- **Top: daily activity table.** Per region: yesterday's hotspot count
  (complete day, sensor named), 7-day and 15-day totals, trailing
  7-day daily strip, 7-day vs same analog week, "last updated" UTC
  stamp. Fixed boilerplate carries the attribution framing (El
  Niño-loaded windows wording, US West / Mediterranean caveats) so no
  daily run ever generates fresh prose.
- **World-map bubble widget** (added 2026-07-25 after Kristjan saw
  currentwildfires.com's raw-count map): the at-a-glance layer at the
  top of the page. One bubble per tracked region plus the largest
  untracked global clusters. **Size encodes 7-day detections; color
  encodes abnormality vs the same-week climatological norm** (gray
  near normal, orange 1.5-2x, red 2x+, dashed outline for clusters
  with no baseline series). Coloring by raw count was considered and
  rejected: raw counts make routine savanna burning the loudest thing
  on the map, which is measurement-trap thinking in visual form. Our
  map answers "where should I look?", not "where is fire?". Rendered
  as static SVG reusing `docs/world-map.svg` (equirectangular, same
  x/y convention as `REGION_MAP_COORDS`), regenerated by the daily
  run; native tooltips carry name, count, and vs-norm detail. No
  external tiles or libraries.
- **Country spotlight layer** (added 2026-07-25; UX gap raised by
  Kristjan: news attention is country-shaped, region boxes are not,
  and the UK sits outside every box). A spotlighted country gets a
  row computed like a region row but against its own 2012-2025
  same-calendar-week history: this week, 14-yr mean, multiple, rank
  on record. Computed live from the archive (area API + country
  polygons, point-in-polygon, identical shapes both sides), SNPP-only,
  labeled "spotlight" to distinguish from frozen-baseline tracked
  regions. Cost ~30 requests per country, so any country can be
  spotlighted within minutes of becoming newsworthy. Spotlighted
  countries get their own map bubble colored by their own
  abnormality. Standing European mini-table (ES, PT, FR, IT, GR, TR)
  during the Mediterranean season. Trigger: country prominently in
  fire news, or any country we notice at 2x+ its norm. First live
  demonstration in the 2026-07-25 pilot: France 6.0x (record week),
  UK 2.6x (record week), Spain 5.3x (2nd of 15).
- **Historical-norm section.** Per region: this calendar week vs the
  SNPP-only 2012-2025 same-week distribution (dot strip per year,
  mean marker, current week emphasized), stated as a multiple of the
  mean plus rank on record. Computed on the SNPP-only series for
  sensor consistency; caption says so and notes the trend caveat.
- **Global clusters section.** Largest active clusters worldwide over
  the trailing 7 days (with 15-day totals), tracked regions tagged,
  framed as context and explicitly not a severity league table since
  raw counts favor routine savanna and agricultural burning.
- **Middle: latest weekly issue**, rendered from its markdown.
- **Bottom: archive list** of past weekly issues
  (`docs/fires/briefs/YYYY-MM-DD/`, immutable once written) and a link
  to the methodology/baselines doc.
- The daily refresh regenerates only the top layer; the weekly layers
  change only when a new issue is published on Monday.
- No link from the parent front page until Kristjan decides to share;
  adding that link is a one-line change owned by the public chat.

### 4. Daily workflow: `.github/workflows/fires_daily.yml`

Separate file from the parent's `weekly_brief.yml`; the parent
pipeline is never touched by fire automation (parent invariant 1
stays safe by construction).

- Daily cron in the chosen UTC slot, plus manual dispatch.
- Steps: FIRMS pull, write daily JSON snapshot, regenerate
  `docs/fires/index.html` top layer, commit and push.
- One secret: `FIRMS_MAP_KEY`.
- On fetch failure: the page keeps the last-good day, the stamp says
  so explicitly ("no update since ...; FIRMS unreachable"), parent
  disclosure style. The workflow never publishes a partial or empty
  table.
- Daily snapshots (`fires/snapshots/YYYY-MM-DD.json`) are immutable,
  same audit-trail role as parent snapshots.

### 5. FIRMS fetcher: `fetchers/firms_hotspots.py`

- NASA FIRMS area API, free MAP_KEY (stored like the CDS key, not in
  the repo).
- Pulls daily counts per region box (the area API serves date ranges
  up to 10 days per request, ample for a weekly pull plus overlap).
- Stores the raw point detections (lat/lon, timestamp, FRP,
  confidence, satellite) in the cache, not just the aggregates. Points
  are the atomic unit; any sub-national slice can be computed from
  them later without refetching.
- One bounding box per region, defined once in the fetcher and echoed
  in `fire_baselines.md`; box changes are a versioned event.
- VIIRS (SNPP+NOAA-20 or SNPP-only, decided at build time and fixed)
  as the sole weekly series sensor. MODIS pulled only where a baseline
  year predates VIIRS.
- Returns `FetchResult` via `fetchers/_common.py`; cached last-good
  like the other seven fetchers; on failure the issue carries forward
  the cached week with disclosure, parent-brief style.
- Live test before integration, per repo convention:
  `python -c "from fetchers import firms_hotspots; print(firms_hotspots.fetch())"`.

Not built in v1: burned-area scrapers, emissions fetchers, damage
scrapers, any orchestration into `run_brief.py` or the parent GitHub
Actions workflow. The fire tracker has its own entry point
(`fires/run_fire_page.py` or similar) with two modes: the daily
refresh (run by `fires_daily.yml`) and the weekly issue build (run
manually on Mondays, since the weekly issue is curated).

## Granularity policy

FIRMS detections are points (375 m VIIRS pixels with lat/lon,
timestamp, FRP), so aggregation to any polygon is possible: country,
French région, Indonesian province. The discipline is in what becomes
a *tracked series* versus an *ad-hoc slice*:

- **Tracked series** (frozen, baselined): the five region boxes only.
  Every tracked series needs its own analog-year baseline to mean
  anything, and baselines are expensive to build and freeze. New
  tracked series are a spec change, not an issue-day decision.
- **Ad-hoc slices** (prose material): sub-national counts computed on
  demand from the stored raw detections when a local story warrants it
  (e.g., "the Aude département accounts for half of France's
  detections this week"). Cited with sensor and box definition inline,
  compared to an analog year only if the same slice is computed for
  that year in the same pass.
- **Europe burned area**: EFFIS publishes per-country season-to-date
  burned area against a 2006+ mean, which covers France and the rest
  of the Mediterranean control at country level with no custom work.
  Use it for the burned-area layer rather than building polygon
  aggregation.

## Measurement rules (from the handover's traps; binding)

1. Year-over-year comparisons are same-sensor, sensor named inline.
2. Hotspots and burned area are separate layers; never convert one
   into the other.
3. Peak-week comparisons note cloud/smoke undercount when relevant.
4. Damage estimates are vintage-tracked: estimator, issue date,
   revision history. Early numbers are expected to be low. As of
   D-032 this is ECON's requirement to enforce, not ours; it stays
   listed because Fire must not render a loss figure that fails it.
5. Framing is "fires in the El Niño-loaded windows," never "El Niño
   caused this fire." Formal attribution defers to WWA-type studies.
   US West and Mediterranean get the weakest framing.
6. Amazon: use MAAP's primary-forest split where available; INPE raw
   hotspot counts mix land-clearing with drought wildfire.
7. NRT vs science-quality: current-week counts come from the FIRMS
   near-real-time product; the standard (science-quality) archive
   replaces NRT with a ~2-3 month lag, and analog baselines are built
   from that archive. Differences are usually small but nonzero; the
   weekly issue states which product each number came from, and
   season-to-date figures are restated from the archive once it
   catches up.

## Editorial constraints (identical to parent, non-negotiable)

- No em-dashes (U+2014) anywhere; `grep -rnP '\xe2\x80\x94' .` returns
  zero hits after every change.
- Every number cites a named source; no anonymous attributions.
- Disagreement between estimators is surfaced, never averaged.
- Aggregator posture: no asset-price targets, no trade
  recommendations, no original damage estimates.

## Ownership and boundaries

- This workstream (fire-tracker chat) owns: `fires/` (spec, baselines,
  weekly issues, entry point), `fetchers/firms_hotspots.py`,
  `docs/fires/` (the fire page and its archive), and
  `.github/workflows/fires_daily.yml`.
- Shared seam: `fetchers/_common.py` belongs to the methodology chat;
  changes there are pinged, not made unilaterally.
- Nothing here feeds a parent probability number (methodology chat's
  domain). The parent front page (`docs/index.html`) stays the public
  chat's; the eventual link from it to the fire page is that chat's
  one-line change at share time.
- The aftereffects screener links here for fire items rather than
  duplicating; this tracker is the deep treatment of the one channel.
- CLAUDE.md gets a Fire-tracker ownership section when building starts.

## Milestones

1. **Baselines** (target: week of 2026-07-27): FIRMS key, region
   boxes, analog-year weekly series pulled and frozen into
   `fire_baselines.md`.
2. **Fetcher** (same week): `firms_hotspots.py` live-tested against
   the baseline pulls.
3. **Public page + daily workflow live** (before the first issue):
   `docs/fires/index.html` rendering real daily data,
   `fires_daily.yml` running on cron with `FIRMS_MAP_KEY` configured
   (secret setup is a Kristjan action). Page live but unlisted.
4. **First weekly issue, Monday 2026-08-03**: Amazon, Indonesia, US
   West, Mediterranean vs baselines; Australia one line (pre-season);
   damage panel with whatever named 2026 estimates exist.
5. **Steady state**: daily auto-refresh plus weekly issues each Monday
   through the Australian season (Feb-Mar 2027), then a season
   retrospective.
6. **Share gate** (Kristjan's call, any time): link from the parent
   front page and promote. Nothing technical blocks it; the gate is
   editorial confidence after watching the daily layer run for a
   while.

## Out of scope for v1

- Link from the parent front page, OG/social cards, any promotion
  (behind the share gate).
- Intraday updates (the twice-daily escalation path exists but is
  off by default).
- Burned-area, emissions, or damage automation; those layers stay
  manually curated in the weekly issue.
- Any change to the parent `weekly_brief.yml` or `run_brief.py`
  orchestration.
- Probability statements of any kind about fire outcomes.
- Impact channels other than fire (crops, health beyond fire-smoke
  cost estimates, etc.); those belong to the screener stream.

## V2 idea backlog

Gathered, not built. Current list: FRP intensity column; Indonesia
haze line (Singapore PSI, NEA) once its season starts; named agency
seasonal fire outlooks (NIFC, Copernicus); emissions layer (GFED,
CAMS) as a monthly line first. Additions accumulate here and in the
project memory.
