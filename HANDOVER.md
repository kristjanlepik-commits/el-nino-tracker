# Handover to Claude Code

This is the prioritized work list to take this project from "scaffolded,
falls back to seeds" to "fully automated, cron-runs unattended". Tasks
are ordered by dependency and value. Do them in order unless you have
a reason not to.

For each task: do the work, run the verification, then move on. Don't
batch tasks; commit per task so you can roll back cleanly.

Read `CLAUDE.md` for project conventions before starting. The em-dash
ban is real and applies to your code comments and commit messages too.

## Task 0: orient yourself, verify the scaffold

Before changing anything:

```bash
python run_brief.py
```

Expected output:
- Creates `briefs/2026-04-25/brief.md` and `briefs/2026-04-25/analog.png`
- Creates `snapshots/2026-04-25.json`
- "Source freshness this issue" section in the brief shows all sources
  as "not implemented or cache empty; using seed values from sources.py"
- "Analyst read" section shows the AUTO-GENERATED banner followed by
  fallback prose (because no ANTHROPIC_API_KEY is set yet)

If any of this is wrong, fix it before proceeding. The scaffold needs
to be a known-good baseline.

## Task 1: fix `build_markdown` to read from fetched data, not `sources.py`

**Why:** Right now `run_brief.py:build_markdown` still reads
`S.IRI_3CAT["DJF 2026-27"]`, `S.PHYSICAL_STATE`, `S.ANALOG_SAME_WEEK`,
`S.BOM_QUALITATIVE`, `S.ECMWF_QUALITATIVE` directly from the
hand-curated module. This is invisible while fetchers are stubs (the
seeded fallbacks happen to match `sources.py`), but the moment any
fetcher returns live data, the brief body will show stale `sources.py`
values while the freshness panel claims the data is live. That's worse
than no automation.

**What to do:**

1. Change `build_markdown` signature to accept the `fetched` dict
   (the orchestrator output minus `_freshness`).
2. Replace every `S.IRI_3CAT[...]`, `S.PHYSICAL_STATE`, etc. with
   reads from `fetched["iri"]`, `fetched["physical_state"]`, etc.
3. `S.ANALOG_SAME_WEEK` and `S.RONI_TO_ONI_OFFSET` and
   `S.METHODOLOGY_VERSION` stay sourced from `sources.py` (they're
   constants, not fetched data).
4. Update `main()` to pass `fetched` through.
5. The CPC strength table also needs to flow through: `probs.py`
   currently reads `S.CPC_STRENGTH_RONI` directly. Decide whether to
   pass the fetched table into `probs.cpc_headline_with_uncertainty()`
   as an arg, or to have probs.py read from a module-level state set
   by run_brief. The arg approach is cleaner.

**Verification:**

```bash
python run_brief.py
```

The brief should look identical to before this task (because all
fetchers are still stubs, so seeded values flow through). But now
when you implement fetchers in later tasks, the brief body will
update with live data automatically.

Run with one fetcher temporarily hardcoded to return different values
than the seed, to prove the wiring works. Revert the hardcode when done.

## Task 2: implement `fetchers/oisst_weekly.py` (easiest, highest signal)

**Why first:** It's the simplest fetcher (one fixed-width ASCII file,
takes the last line), and weekly Niño 3.4 is the single most
information-dense input we get each Monday. Getting this live makes
every brief from now on more current.

**Source:**
`https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for`

**Format:** fixed-width ASCII. Each row is one week. Columns are
date, then four pairs of (SST, anomaly) for Niño regions 1+2, 3, 3.4, 4.
Take the most recent row's Niño 3.4 anomaly column.

**Implementation hint:** `pandas.read_fwf` with no header, then take
the last row. The file's first 4 lines are header text; skip them.

**Verification:**

```bash
python -c "from fetchers import oisst_weekly; r = oisst_weekly.fetch(); print(r)"
```

Expected: `ok=True`, `issued` is a recent Monday's date, payload has
`weekly_traditional` as a float in a sane range (call it -3.0 to +3.0).

Then run `python run_brief.py` and verify:
- "Source freshness" panel now shows `oisst_weekly: fetched live`
- The Niño 3.4 weekly value in the physical state panel matches
  what you got from the direct fetch test
- No regressions elsewhere

Compare the fetched value to Kristjan's hand-curated value in
`sources.py` for the most recent overlapping week. If they differ by
more than 0.1°C, investigate before trusting the fetcher.

## Task 3: implement `fetchers/bom.py`

**Why next:** BoM is HTML, parses with bs4, no auth needed. Good
practice run before tackling CPC's strength table (which is HTML but
more structurally fragile).

**Source:** `https://www.bom.gov.au/climate/enso/`

**Implementation hint:** Look for the alert-status pill (typically a
heading or styled span) and the "Issued on:" line. The fortnightly
summary paragraph is usually the first `<p>` in the main content area.
View the page source first; don't assume structure.

**Verification:**

Same pattern as Task 2. Compare to the seeded BoM value.

## Task 4: implement `fetchers/cpc_strength.py`

**Why now:** This is the only quantitative source feeding the headline
buckets. Until this is live, every Monday's brief has the same headline
probabilities until you manually re-seed.

**Source:**
`https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php`

**Implementation hint:** `pandas.read_html(url)` returns a list of
DataFrames. The strength table is identifiable by its column headers
(the RONI bin labels). Match the bin labels to the keys used in
`sources.CPC_STRENGTH["table"]` exactly: `"<=-2.0"`, `"-2.0to-1.5"`,
..., `"neutral"`, ..., `">=2.0"`. CPC publishes 9 overlapping seasons;
keep all of them in the table dict.

**Be careful with:** The page header includes an issuance date. Parse
that into the `issued` field. CPC uses month names (e.g.,
"April 2026"); convert to ISO.

**Verification:**

After implementing, run `python run_brief.py` and verify the headline
buckets. They should match what `sources.py` produced for April 2026
(±1 percentage point if CPC has re-issued since the seed was captured).

Edge case to test: what happens if CPC re-issues the table mid-week
with different probabilities? The diff renderer should show the bin-
by-bin deltas in next week's brief. Force this by manually editing
the most recent snapshot file before the next run.

## Task 5: implement `fetchers/iri.py`

**Source:** `https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/`

**Implementation hint:** Look for a JSON endpoint in the page source
first; IRI publishes the Quick Look data that way and it's much more
stable than parsing the rendered page. Search the HTML for `.json` or
`fetch(`. If no JSON, fall back to parsing the PDF version of the
plume figure with `pdfplumber`.

**Verification:** Same pattern. The `three_cat` dict structure must
match what's in `sources.IRI["three_cat"]`.

## Task 6: implement `fetchers/heat_content.py`

**Source:** verify URL on first run. Try
`https://www.cpc.ncep.noaa.gov/products/GODAS/heat_content_index.txt`
first; if that 404s, scrape from the GODAS monitoring page. The
0-300m equatorial Pacific (180W-100W, 5N-5S) anomaly is what we want.

**Verification:** Should be a single float updated weekly to bi-weekly.
Sane range: -3 to +3 °C.

## Task 7: implement `fetchers/ecmwf_seas5.py`

**This is the heaviest task by far.** Plan for 2-4 hours including
debugging.

**Prerequisites:**
- Register at `cds.climate.copernicus.eu` (free for non-commercial use).
- Get UID and API key. Set in `~/.cdsapirc`.
- `pip install cdsapi xarray netCDF4` (already in requirements.txt).

**Approach:**
1. Use `cdsapi.Client().retrieve(...)` to pull the most recent SEAS5
   monthly forecast. Dataset name to verify in CDS catalog;
   probably `seasonal-monthly-single-levels`.
2. Variable: `sea_surface_temperature`. Region: 5N to -5S, 170W to
   120W (note CDS uses 0-360 longitude; convert).
3. Pull all 51 ensemble members for lead times covering DJF target.
4. Open the NetCDF with xarray. Area-mean over the box. Time-mean
   over Dec, Jan, Feb of target year.
5. Subtract SEAS5 model climatology (NOT observational climatology).
   You'll need to also pull hindcasts for the same start month/lead
   over 1991-2020 to compute climatology. This is the slowest part.
6. Count members above thresholds 1.0, 1.5, 2.0, 2.5 °C.
7. Cache the climatology to disk so you don't recompute it every week.
   The forecast data changes monthly; the climatology essentially
   doesn't.

**Verification:**
- `member_count` should be 51 (or whatever SEAS5's current ensemble
  size is, verify in the CDS docs).
- `members_above[1.0]` should be high (probably 45+ given current state),
  `members_above[2.5]` should be roughly 50% per the qualitative read
  in `sources.ECMWF`. If your number is wildly different, climatology
  subtraction is probably wrong.
- Compare to the qualitative seed in `sources.ECMWF["summary"]` and
  to public ECMWF plume images at `apps.ecmwf.int`.

**Once this works, the headline-bucket aggregation in `probs.py`
becomes a real two-source median.** Update `probs.py` to ingest
ECMWF members_above counts as a second numerical input; the existing
range logic (lo, mid, hi) extends to "min and max across CPC and
ECMWF" naturally.

## Task 8: implement `fetchers/era5_wwe.py`

**Frequency:** Run monthly, not weekly. ERA5 has 5-day delay; WWE
count is a slow-moving signal. The orchestrator should skip this
fetcher if the cached version is less than 25 days old.

**Approach:**
1. cdsapi pull of daily 850 hPa zonal wind from Mar 1 of develop year
   to most recent ERA5 day available. Region: 5N to -5S, 160E to 120W.
2. Compute anomaly vs ERA5 1991-2020 same-calendar-day climatology.
3. Spatial mean over region.
4. Apply McPhaden (1999) WWE criteria: anomaly > 5 m/s, persists
   > 5 days, centered east of 160°E.
5. Count distinct events.

**Verification:** As of late April 2026, count should be ~1-2. If
you get >5 or 0, criteria are likely wrong.

## Task 9: live test the GitHub Actions workflow

Once at least Tasks 1-4 are done (oisst_weekly, bom, cpc_strength
implemented), the workflow has enough to produce a meaningfully
automated brief.

1. Push to GitHub.
2. Add the secrets in Settings (ANTHROPIC_API_KEY at minimum;
   CDS_API_KEY once you've done Task 7).
3. Actions -> Weekly El Nino brief -> Run workflow.
4. Watch the run. Verify it commits a snapshot and brief back to the
   repo, and emails you if SMTP is configured.
5. Open the committed brief and read it end-to-end as if you were
   Kristjan reading it Monday afternoon. It should make sense
   without any prior context from chat.

## Task 10: verify week-over-week comparability

After running the workflow at least twice (manually trigger a second
run a few minutes after the first to simulate two consecutive weeks):

- The second brief's "What changed week-over-week" subsection should
  show source-by-source which agencies re-issued vs stayed the same.
- Numerical deltas in physical state should appear as `prev -> curr
  (delta +X.X)` lines.
- Methodology version should be unchanged across both runs (no banner).

If any of this is wrong, the snapshot/diff machinery is broken and
should be fixed before trusting the automation.

## Things explicitly out of scope for this handover

- Custom statistical models (insufficient training data; see
  `methodology.md`).
- Real-time SST nowcasting beyond what NOAA publishes.
- Impact attribution (food prices, drought, hurricanes); that's a
  separate project (Pt 2 / V2).
- Public dashboard.
- Probability calibration against historical events.

If you find yourself wanting to add any of these, stop and ask
Kristjan first; they're scope expansions.

## When you're stuck

If a fetcher won't parse, screenshot the page source / failed output
and ask Kristjan in chat. Don't burn an hour on a parser when the
agency may have just changed format and a 30-second visual inspection
would tell you that.

If the GitHub Actions run is failing for non-obvious reasons, run
`act` locally (or just run the workflow steps manually in a venv) to
debug before pushing fix attempts.

If you've implemented something and the headline numbers shift in a
way that surprises you, double-check the climatology and the unit
conversion. ENSO bugs almost always trace to one of those two things.
