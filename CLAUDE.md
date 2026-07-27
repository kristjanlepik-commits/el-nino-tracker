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

The project is The Long Swell (TLS), maintained from parallel chat
sessions under the team structure ratified 2026-07-26 in
`research/team.md`. The registry defines mandates; this section maps
them to files. Read it before editing anything. A file has exactly
one owner; where a file is split below (run_brief.py, analog.py,
card.py), the boundary is stated and everything not explicitly
assigned belongs to the first-listed owner of that file.

Shared artifacts every chat reads at session start: this file,
`research/theses.md` (T1-T11), `research/decisions.md` (append-only
ratification ledger; any chat appends when Kristjan ratifies), and
auto-memory MEMORY.md (cross-chat bulletin).

## Telling another chat something (read this, it is new)

Chats can now message each other directly. Kristjan is no longer the
clipboard. Use `mcp__ccd_session_mgmt__list_sessions` to get session
ids, then `mcp__ccd_session_mgmt__send_message`. The message lands in
the target chat as a turn labelled with your chat's name.

**The one rule: draft it, show Kristjan, send it after he confirms.**
Never send unseen. He keeps oversight; he just stops copy-pasting.
(His instruction, 2026-07-27: "I need to confirm the messages, but
sending is automatic.")

Send a message when any of these is true. This list exists because
every item on it has already gone wrong at least once:

1. **You changed something another chat owns, or a shared seam.**
   Say what changed and what they must not undo.
2. **You found a bug on someone else's surface.** Do not fix it and
   do not stay quiet. Report it with file and line.
3. **You are blocked on another chat.** Say exactly what you need.
4. **You shipped something others build on.** Especially anything
   that changes how pages are published or verified.
5. **You are proposing a change to a file another chat owns.** Send
   the proposal, do not merge it for them.

Two habits worth copying, both learned the hard way:

- **Verify the specific property you changed, live.** A generic check
  will happily green-light the exact regression you just introduced.
  A link check found zero broken links on a page that had silently
  lost its entire masthead.
- **Assume nothing is live until you have seen it live.** A merged
  commit is not a published page. This repo has several publish
  paths; `scripts/publish_all.py` runs the ones that do not fetch.

## Bugs

Private tracker: **GitHub Issues on `kristjanlepik-commits/tls-internal`**
(the private internal repo). File anything that is not fixed in the
same session, with file and line. `gh issue list -R
kristjanlepik-commits/tls-internal` to read, `gh issue create -R ...`
to file. The public repo's Issues are for reader-visible defects only.

A bug that can regress should become a **guard**, not just a ticket.
`scripts/qa_check.py` and `scripts/publish_all.py` enforce the ones we
have already hit: em-dashes, dead links, archive immutability, exactly
one analytics tag per page, the shared masthead per page. A guard
cannot be forgotten; a ticket can.

### ENSO tracker chat ("El Nino model buildout"; formerly "methodology chat")

- `fetchers/` (all modules + `_common.py`)
- `fetch_all.py` (orchestration over the fetchers)
- `probs.py` (skew-normal fit, bucket computation, bootstrap)
- `snapshot.py` (snapshot + diff logic)
- `editorial.py` (Analyst Read prose generation, internal brief only)
- `run_brief.py` `build_markdown()` (internal brief)
- `analog.py` chart math: SEAS5 fan computation, threshold gridlines,
  projection logic, and in-figure annotations whose text is
  auto-generated from data
- `data/oni_historical.csv`
- `methodology.md` (the scientific argument, including the "Impact
  aggregation" subsection that describes the *method*; the *content*
  in `impacts.md` is editor-side)
- `sources.py` data values (`METHODOLOGY_VERSION`, `RONI_TO_ONI_OFFSET`,
  `ANALOG_SAME_WEEK`, `_most_recent_monday` helper). Note:
  `RONI_TO_ONI_OFFSET = 0.3` is the static fallback only used when the
  live `oisst_weekly` offset is unavailable. Production offset is
  dynamic and comes from the fetcher.

### Fire chat

- `fires/` end to end: science, pipeline, content, including the
  country spotlight page and the fire damage panel. First issue
  2026-08-03.

### Aftereffects / impacts chat

- `research/impact_database_2026-27.md`,
  `research/impact_timeline_2026-27.md`
- The cross-channel damage ledger content (vintage-tracked named
  estimates across heat, drought, agriculture, food security,
  humanitarian, economic). Fire-specific content stays with the
  Fire chat; aftereffects owns the view that reads across channels.

### Country reports chat

- Per-country baseline pieces. No standing files in the repo yet;
  as pieces ship they land in surfaces designed by the platform
  chat (event-page pipeline) to the editor's format.

### Editor chat (formerly "public chat")

- All reader-facing prose: lede, bottom-line copy, chart-caption
  framing outside the figure, `public_preamble`,
  `PUBLIC_SOURCE_NAMES`, and the prose strings in `card.py`
- `run_brief.py`: `build_impacts_html_block`,
  `_split_aggregation_into_regions` (impacts content assembly)
- `impacts.md` (curated regional content)
- Format definitions and copy standards that subsection chats
  produce to: baseline-check format, attribution-tag usage in copy,
  EU/US reader framing per T11, units rule (metric and Celsius
  default, Fahrenheit alongside for US events)

### Design and brand chat

- `run_brief.py`: `build_public_html` (HTML structure and
  templates), `_render_world_map_block`, `_render_rung`,
  `PUBLIC_CSS`, `IMPACTS_TAB_SCRIPT`, `REGION_MAP_COORDS`, OG/Twitter
  meta, footer, archive index layout
- `card.py` layout, composition, and typography (the weekly card
  PNG; generated by run_brief.py step 9 from published artifacts
  only, never from a live fetch)
- `analog.py` visual styling: colors (`#c92020` etc.), line widths,
  marker sizes, font choices, legend label phrasing
- `assets/brand/`, `assets/fonts/`, `docs/world-map.svg`
- The design token set, the citable-chart template (to be built),
  social card design

### Platform chat (the CTO surface)

- `.github/workflows/` (all CI and automation, including
  `weekly_brief.yml`)
- `scripts/` (including `send_email.py`)
- `run_brief.py` `main()`: CLI, orchestration order, publishing
  steps, `--date` / `--force` handling, the archive-freeze guard
- Repo structure, `.gitignore`, dependency management, `.venv`
  policy
- `docs/` deployment mechanics: Pages configuration, custom domain
  and CNAME, the redirect map for immutable archive URLs
- The event-page publishing pipeline (to be designed), email
  capture infrastructure
- This CLAUDE.md section (ownership map)

### Strategy chat

- `research/theses.md`, `research/team.md`, `research/decisions.md`
  (audits; any chat appends), `research/handover_*.md`, business and
  sponsor docs, memory hygiene

### Shared seams (ping the affected chat when touching)

- `run_brief.py` `main()`: platform owns; a change to what gets
  built or published pings ENSO tracker (weekly data flow) and
  editor (public surfaces).
- `build_public_html`: design owns the function. Editor-owned copy
  inside it lives in named constants (`public_preamble` etc.); new
  reader-facing prose goes into a named constant, not inline, so
  the boundary stays crisp.
- `card.py`: design owns layout, editor owns the prose strings;
  either side pings the other before restructuring.
- `analog.py`: chart math (ENSO tracker) vs visual styling (design);
  a methodology change pings design and editor, since captions may
  need a refresh.
- `methodology.md` "What a reviewer should focus on" section: ENSO
  tracker owns; editor may want input on framing (read by
  externals).
- `sources.py`: data values are ENSO tracker's; structural or
  import-level changes from platform ping ENSO tracker.

### Decision rule

If you're not sure, the principle: **the science and anything that
drives a published number belongs to the owning subsection chat;
the pipeline that builds and ships it is platform; how it looks is
design; what it says in reader-facing prose is editor.** Still
unsure: ask Kristjan rather than guess.

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

6. **No em-dashes in anything new.** After every change, run:
   `git ls-files -z | xargs -0 grep -n "$(printf '\xe2\x80\x94')"`
   (macOS BSD grep has no `-P`; earlier documented commands silently
   passed or errored). Known legitimate hits that must NOT grow:
   `LICENSE`, the frozen 2026-05-18 and 2026-05-25 archive briefs
   (immutable, invariant 5), and the regex character classes in
   `fetchers/iri.py` that parse em-dashes in upstream text. Any hit
   outside that list is a violation.

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

- Run `.venv/bin/python scripts/qa_check.py` before any push that
  publishes to `docs/`. It enforces invariants 4, 5, and 6 plus link
  and structure checks; CI (`.github/workflows/qa.yml`) runs the same
  script on every push as a backstop.
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
