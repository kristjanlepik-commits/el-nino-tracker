# El Niño Probability Tracker, V1.5

Internal weekly tracker for the 2026-27 El Niño peak. Generates a
markdown brief and analog chart each Monday, automated via GitHub
Actions.

This README is the operator's guide. Implementation context for Claude
Code lives in `CLAUDE.md`. Methodology lives in `methodology.md`
(maintained separately as a project doc).

## What it produces

Each Monday, in `briefs/YYYY-MM-DD/`:

- `brief.md`: 4-section structured brief with headline probability
  buckets, physical state panel, analog tracker, and editorial layer.
- `analog.png`: 2026-27 ONI trajectory vs 1997-98, 2015-16, 2023-24.

And in `snapshots/YYYY-MM-DD.json`, a frozen copy of all input data
that produced that issue. This is what makes week-over-week comparisons
possible.

## Quickstart

```bash
git clone <this repo>
cd eltracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_brief.py
```

This generates a brief using whatever's in `sources.py` (the V1
hand-curated seed values). It will work without any API keys.

To enable live fetching and AI-generated editorial layer:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Configure CDS API for ECMWF/ERA5 (free, register at cds.climate.copernicus.eu):
cat > ~/.cdsapirc <<EOF
url: https://cds.climate.copernicus.eu/api
key: <your-uid>:<your-api-key>
EOF
chmod 600 ~/.cdsapirc

python run_brief.py
```

## Deploy to GitHub Actions (the weekly automation)

1. Push this repo to GitHub (private).
2. Settings -> Secrets and variables -> Actions, add:
   - `ANTHROPIC_API_KEY` (required for the auto-generated editorial)
   - `CDS_API_KEY` in format `<UID>:<API-key>` (required once ECMWF
     and ERA5 fetchers are implemented)
   - `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `BRIEF_RECIPIENT` (optional;
     for emailing the brief). Without these the workflow still runs
     and commits to the repo.
3. Actions tab -> "Weekly El Nino brief" -> "Run workflow" once
   manually to verify the scaffolding before trusting the cron.
4. The cron runs Mondays 13:00 UTC after that. Adjust the schedule in
   `.github/workflows/weekly_brief.yml` if needed.

## What's auto-fetched vs hand-curated

As of this V1.5 scaffolding, all fetchers are stubs that fall back to
seed values in `sources.py`. The pipeline runs end-to-end but reads
from seeds, not the live web. To make it truly automated, implement
the fetchers in priority order (see `HANDOVER.md`).

The brief includes a "Source freshness" subsection in the editorial
layer that shows which sources were fetched live vs fell back. So you
can always tell at a glance whether a given week was fully automated
or not.

## What you do each week

In the steady state (all fetchers implemented, cron running):

**Nothing.** The brief lands in your inbox Monday afternoon. You read
it, decide whether to edit the auto-generated Analyst Read paragraph,
and move on.

In the bootstrap state (fetchers still stubs):

Either run `python run_brief.py` locally Monday morning after manually
updating any changed fields in `sources.py` (V1 workflow), or skip
weeks until the fetchers are implemented enough to run unattended.

## Methodology version stability

When you change anything that would shift headline numbers without an
underlying probability change (RONI offset, conversion math, bucket
definitions, analog event list), bump `METHODOLOGY_VERSION` in
`sources.py`. The next brief will surface the bump with a loud banner
so you know that week's numbers are not strictly comparable to last
week's.

## Layout

```
sources.py        Seed values, methodology constants
fetchers/         One module per data source
fetch_all.py      Orchestrator
probs.py          Probability harmonization
snapshot.py       Snapshots and diffing
analog.py         Chart generation
editorial.py      Anthropic API call for analyst prose
run_brief.py      Entry point

briefs/           Generated briefs
snapshots/        Input state per issue (audit trail)

.github/workflows/weekly_brief.yml
scripts/send_email.py
```
