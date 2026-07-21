# CLAUDE.md

Context for Claude Code working on this repo. Read this first.

## What this is

Internal weekly probability tracker for the 2026-27 El Niño event.
Built and maintained by Kristjan. Output is a markdown brief, an
HTML rendering of the same, and an analog chart, generated each
Monday and emailed to him.

V1.5 is functionally complete as of 2026-04-26: all 7 fetchers run
live (CPC strength, OISST weekly, CPC heat content, IRI, BoM, ECMWF
SEAS5, ERA5 WWE). A `methodology.md` overview at the repo root is
rendered to `methodology.html` on every run for sharing with external
reviewers. The GitHub Actions workflow file exists but has not been
run; that requires a remote push and secret config (user actions).

## Operator profile

Kristjan has deep VCM and climate fluency, light-to-moderate Python
fluency. Explain Python only when using a non-standard library or
pattern. Explain climate concepts only when they're non-obvious or
contested.

## Editorial constraints (apply to all generated text and code comments)

- **Never use em-dashes** (U+2014). Use commas, semicolons, or periods.
  This applies to brief text, code comments, and commit messages.
- Be concrete and skeptical of overfitting.
- When forecast centers disagree, surface the disagreement rather than
  averaging it away.
- Prefer the simplest thing that works. A Python script run manually
  beats a cron-scheduled pipeline that breaks.

## Build philosophy

This is an aggregator. **Do not build a custom logistic regression or
ML model.** The historical sample of super El Niño events is too small
(n=4) to calibrate anything that beats agency forecasts. Our edge is
harmonization across sources, not original modeling.

Out of scope for V1/V1.5:
- Public dashboard or web app
- Custom ML
- Impact attribution (food prices, hurricanes); that's V2 / Pt 2
- Push notifications, social posting
- Real-time updates faster than weekly cadence

## Architecture

```
sources.py        Hand-curated seed values + methodology constants.
                  Lives as fallback when fetchers fail.
fetchers/         One module per data source. All 7 implemented and live.
                  _common.py provides FetchResult, http_get, safe_fetch,
                  cache layer.
fetch_all.py      Orchestrator. Runs all fetchers; falls back to
                  sources.py seeds on failure. Returns a sources-shaped
                  dict plus a _freshness sub-dict for the brief.
probs.py          RONI to traditional ONI conversion + headline buckets.
snapshot.py       Save/load JSON snapshots, compute week-over-week diff.
                  Snapshots reflect the fetched dict, not sources.py.
analog.py         Render the analog tracker chart. 1997, 2015, 2023 are
                  super-event peers; 2025 is plotted as a non-event
                  (La Niña) reference; 2026 is current.
editorial.py      Call Anthropic API to generate the Analyst Read prose.
                  Always prepends "AUTO-GENERATED, review before quoting"
                  banner per Kristjan's choice (option C). Falls back
                  to template prose if no API key.
run_brief.py      Entry point. Orchestrates everything; renders both
                  brief.md and brief.html, plus regenerates
                  methodology.html from methodology.md.

methodology.md / .html   Standalone methodology overview at repo root,
                         written for external reviewers reading cold.

briefs/YYYY-MM-DD/   Output: brief.md, brief.html, analog.png.
snapshots/YYYY-MM-DD.json   Frozen input state per issue (for diffing).
.fetch_cache/        Last-good fetcher results plus SEAS5 and ERA5
                     climatology caches (gitignored).

.github/workflows/weekly_brief.yml   Mondays 13:00 UTC cron + manual.
                                     Has not yet run; needs remote push.
scripts/send_email.py                SMTP send: multipart, plain-text +
                                     HTML alternative + analog inline.
```

## Ownership: which chat touches what

This repo is maintained from two parallel chat sessions, each with a
clear surface area. Read this before editing anything to avoid stepping
on the other chat.

### Methodology chat owns

- `fetchers/` (all modules + `_common.py`)
- `fetch_all.py` (orchestration over the fetchers)
- `probs.py` (skew-normal fit, bucket computation, bootstrap)
- `snapshot.py` (snapshot + diff logic)
- `editorial.py` (Analyst Read prose generation, internal brief only)
- `analog.py` chart math: SEAS5 fan computation, threshold gridlines,
  projection logic, and in-figure annotations whose text is
  auto-generated from data
- `data/oni_historical.csv`
- `methodology.md` (the scientific argument, including the "Impact
  aggregation" subsection that describes the *method*; the *content*
  in `impacts.md` is public-side)
- `sources.py` data values (`METHODOLOGY_VERSION`, `RONI_TO_ONI_OFFSET`,
  `ANALOG_SAME_WEEK`, `_most_recent_monday` helper). Note:
  `RONI_TO_ONI_OFFSET = 0.3` is the static fallback only used when the
  live `oisst_weekly` offset is unavailable. Production offset is
  dynamic and comes from the fetcher.
- `.github/workflows/weekly_brief.yml` (operational pipeline)

### Public chat owns

- `run_brief.py`: `build_public_html`, `build_impacts_html_block`,
  `_render_world_map_block`, `_render_rung`,
  `_split_aggregation_into_regions`, `PUBLIC_CSS`, `IMPACTS_TAB_SCRIPT`,
  `REGION_MAP_COORDS`, `PUBLIC_SOURCE_NAMES`, `public_preamble`
- `impacts.md` (curated regional content)
- `card.py` and `assets/fonts/` (weekly one-page situation card PNG:
  design, composition, prose; generated by run_brief.py step 9 from
  published artifacts only, never from a live fetch)
- `docs/world-map.svg` (static asset)
- HTML structure, CSS, OG/Twitter meta, footer (author, GitHub link,
  methodology link), archive index layout
- `analog.py` visual styling: colors (`#c92020` etc.), line widths,
  marker sizes, font choices, legend label phrasing, chart-caption
  text *outside* the figure (the section-sub paragraph in the public
  HTML)
- All page-level prose: lede, bottom-line copy, chart-caption framing

### Shared seams (ping the other chat when touching)

- `run_brief.py` `main()` (orchestration; methodology-side by default)
- `run_brief.py` `build_markdown()` (internal brief; methodology-side)
- `analog.py` chart math when methodology changes (public-chat caption
  may need a refresh)
- `methodology.md` "What a reviewer should focus on" section
  (read by externals; public-chat may want input on framing)

### Decision rule

If you're not sure, the principle: **anything that ships INSIDE the
matplotlib figure or that drives a probability number is methodology;
anything wrapped AROUND the image in HTML, or that decides voice and
audience framing, is public.**

## Key invariants

1. **`run_brief.py` always produces a brief.** Even if every fetcher
   fails, it falls back to seeded sources.py values and the editorial
   layer's fallback prose. Never let it crash on a Monday.

2. **Each input source has an `issued` date** distinct from when we
   fetched it. The diff uses issued dates to distinguish "agency
   re-released" from "agency stale, we're carrying forward".

3. **`METHODOLOGY_VERSION` in sources.py is bumped** any time the
   conversion math, RONI offset, analog list, or bucket logic
   changes. The diff renderer surfaces version bumps with a loud
   banner so brief readers know headline numbers are not strictly
   week-over-week comparable.

4. **Snapshots are immutable.** They're the audit trail. If you need
   to fix one, write a new one with a later date, never edit the old.

5. **Past archives are immutable.** A brief, once written for a given
   Monday, IS that Monday's brief. Methodology improvements, prose
   tweaks, new dynamic sentences, or any other change apply only to
   subsequent issues. `run_brief.py` enforces this: if
   `docs/briefs/YYYY-MM-DD/index.html` already exists, it exits early
   and writes nothing. Use `--force` only to fix a published archive
   in genuine emergencies (factual error, broken link, etc.). The
   front page `docs/index.html` and `docs/briefs/YYYY-MM-DD/` move
   together; when the archive freezes, so does the front page.

6. **No em-dashes anywhere.** Run `grep -rnP '\xe2\x80\x94' .` after every change; it should return 0 hits.

## How the brief gets to Kristjan each Monday

1. GitHub Actions cron triggers Monday 13:00 UTC.
2. Workflow installs deps, configures CDS API key from secret.
3. Runs `python run_brief.py`.
4. Commits new snapshot + brief back to the repo.
5. `scripts/send_email.py` emails the brief to Kristjan via SMTP.

Required GitHub Actions secrets:
- `ANTHROPIC_API_KEY` for editorial.py
- `CDS_API_KEY` for ECMWF and ERA5 fetchers
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `BRIEF_RECIPIENT` for email

## Working style

- Run `python run_brief.py` after every meaningful change. End-to-end
  with cached climatologies and live fetchers, the pipeline finishes
  in roughly 1-3 minutes (the SEAS5 forecast pull and the ERA5
  observation pull dominate).
- For any new fetcher, write a small live test first:
  `python -c "from fetchers import <name>; print(<name>.fetch())"`
  before integrating into `fetch_all.py`.
- Don't add abstractions until you have a second concrete use case.
- After implementing a fetcher, manually compare its output to the
  hand-curated seed in sources.py for the same week. They should be
  close; if not, find out why before trusting the fetcher.
- The `.venv/` in the repo root is the working virtualenv. Use
  `.venv/bin/python` (not `python`) for runs.
