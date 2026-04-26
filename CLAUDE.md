# CLAUDE.md

Context for Claude Code working on this repo. Read this first.

## What this is

Internal weekly probability tracker for the 2026-27 El Niño event.
Built and maintained by Kristjan. Output is a markdown brief plus an
analog chart, generated each Monday and emailed to him.

This is V1.5 in progress. V1 (hand-curated inputs) shipped and works.
V1.5 (auto-fetched inputs, GitHub Actions cron, auto-generated analyst
prose) is scaffolded but most fetchers are stubs.

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
fetchers/         One module per data source. Returns FetchResult.
                  All currently stubs except _common.py.
fetch_all.py      Orchestrator. Runs all fetchers; falls back to
                  sources.py seeds on failure.
probs.py          RONI to traditional ONI conversion + headline buckets.
snapshot.py       Save/load JSON snapshots, compute week-over-week diff.
analog.py         Render the analog tracker chart.
editorial.py      Call Anthropic API to generate the Analyst Read prose.
                  Always prepends "AUTO-GENERATED, review before quoting"
                  banner per Kristjan's choice (option C).
run_brief.py      Entry point. Orchestrates everything.

briefs/YYYY-MM-DD/   Output: brief.md and analog.png.
snapshots/YYYY-MM-DD.json   Frozen input state per issue (for diffing).
.fetch_cache/        Last-good fetcher results (gitignored).

.github/workflows/weekly_brief.yml   Mondays 13:00 UTC cron + manual.
scripts/send_email.py                SMTP send of latest brief.
```

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

5. **No em-dashes anywhere.** Run `grep -rnP '\xe2\x80\x94' .` after every change; it should return 0 hits.

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

- Run `python run_brief.py` after every meaningful change. It exercises
  the full pipeline in <5 seconds with stub fetchers.
- For each fetcher you implement, write a small live test:
  `python -c "from fetchers import cpc_strength; print(cpc_strength.fetch())"`
  before integrating into `fetch_all.py`.
- Don't add abstractions until you have a second concrete use case.
- After implementing a fetcher, manually compare its output to
  Kristjan's hand-curated seed in sources.py for the same week. They
  should be close; if they're not, find out why before trusting the
  fetcher.
