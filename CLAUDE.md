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
ratification ledger; any chat appends when Kristjan ratifies),
`research/allhands.md` (broadcast board, D-059: read it, reply only to
object, silence is assent), and auto-memory MEMORY.md (cross-chat
bulletin).

**If you are working in a git worktree, `research/` is a SYMLINK to the
main tree, and it is load-bearing.** `research/` is a separate nested
repo that this repo gitignores, so a worktree, being a fresh checkout,
gets no `research/` at all. Three worktrees ran that way until
2026-08-01: no ledger, no theses, no team.md, no all-hands. The chat
that OWNS the ledger was one of them. If `ls research/` is empty where
you are, stop and say so rather than proceeding without the shared
artifacts, because everything above silently does not apply to you.

The symlink is excluded via `.git/info/exclude` as well as `.gitignore`.
That is not belt-and-braces: git treats a symlink as a file, so the
`research/` directory pattern does not match it, and worktrees sit on
their own branches reading whatever `.gitignore` those branches
committed. `info/exclude` is shared by every worktree and takes effect
immediately. Without it a worktree reports `?? research` and will
eventually commit a link to a private repo into this public one.

**Check the Superseded index at the top of `research/decisions.md`
before acting on any ledger entry.** Entries are never edited, so an
entry can be live text and still be overtaken; the index is the only
place that says so.

## The one rule that holds all of this together

**A decision that lives only in a chat's context does not exist.**

Everything else in this file, the ownership map, the render seam, the
evidence basis, works because it was written down where another chat
could find it. The structure survives architecture changes and mandate
re-cuts. What it cannot survive is a call made in conversation and
never recorded, because that is how two chats end up confidently
disagreeing with Kristjan as the only tiebreaker, weeks later, with
nobody able to reconstruct why.

So, binding on every chat:

1. **If Kristjan approves, agrees, rejects, or decides anything that
   another chat could conceivably need, append it to
   `research/decisions.md` before the session ends.** Not next session.
   Not when convenient. Chat context is not storage.
2. **When unsure whether something qualifies, log it.** Over-logging
   costs four lines. Under-logging is unrecoverable, because by the
   time the gap is noticed the reasoning is gone.
3. **Re-read `research/decisions.md` immediately before appending.**
   Several chats write to it and the numbering has already collided
   once. Take the next free D-number and never reuse one.
4. **Record the reasoning, not just the outcome.** "We chose X" is
   nearly useless in six weeks. "We chose X over Y because Z" is what
   lets a future chat tell whether Z still holds.
5. **A decision goes in the ledger even when it reverses something you
   argued for.** Especially then. D-027 and D-030 disagree about who
   renders, and the pair is more useful than either alone.
6. **If it changes a mandate, a seam, or a shared file, the ledger is
   not enough**: update the owning document too (`research/team.md`
   for mandates, this file for ownership and invariants,
   `research/theses.md` for strategy) and message the affected chat.

The strategy chat owns `research/decisions.md` and audits it for gaps.
If you notice a decision that was acted on but never logged, say so,
including when it is one of Kristjan's asides. Silent gaps are the
failure mode; a false alarm costs nothing.

## Who builds what (D-030, 2026-07-28)

    Fires, Floods, Crops   fetch the data, own that it is
                           methodologically correct, emit validated JSON
    Design                 builds ALL front end, one touch everywhere,
                           and merges it
    Visual design (VD)     sets the visual bar
    Platform               pushes everything live

Two conditions ride with it, both ratified:

1. **Design works template-first, not page-first.** A small set of
   reusable templates (channel index, country page, fast-reaction
   piece, weekly issue) consuming the JSON. A new channel is then data
   plus a template choice, not new rendering code, and design's context
   is bounded by template count rather than channel count. Page-first
   would move the context problem rather than solve it.
2. **The owning channel signs off on its rendered page before
   publish.** Sign-off, not an edit right. Design does not know the
   science and the channel no longer sees the page, so the gap this
   closes is a correct number rendered misleadingly: wrong emphasis, or
   a chart implying causation the attribution tag denies.

   **A sign-off with a condition attached is not a sign-off.** Send it
   back, the way a blocker would be. CRO's rule, and it is the one to
   remember if only one of the two here sticks, because it needs no
   extra step from anybody: either the page is approved as it stands or
   it is not approved.

   The cost of the softer reading, measured on 2026-08-04: CRO approved
   the crops page conditional on a footer fix and told design. Design
   held the fix. Platform pushed. **The approval and the fix existed in
   two different chats and nobody held both**, so a page went live
   truncated mid-sentence. Nobody was careless; the sign-off simply
   meant two different things to the two chats holding its halves.

   The fuller version, if you want the belt as well: a sign-off is
   complete when the owning chat AND design have both confirmed, since
   conditional approval is the normal case rather than the exception.

Escalation, when speed and consistency collide: a piece ships in the
generic template with a plainer chart, or it does not ship. It never
ships outside the design system, because consistency is what makes the
numbers citable (T10).

The channel-to-design JSON shape is DISCOVERED, not specified. Drafted
from the fire country page, ratified only after a second case, because
an interface with one implementation is a guess. Until then it is a
working shape, not a contract.

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
- **Read the `age` header when you verify after publishing. A query
  string does NOT bust this cache.** The site is served with
  `cache-control: max-age=600`, so for up to ten minutes a live fetch
  can return the previous page and look exactly like a deploy that
  never happened. Fastly here does not vary the cache key on the query
  string: `/`, `/?cb=<random>` and `/?probe=<random>` all return the
  same cached object, measured 2026-07-28. So the only reliable
  signal is `curl -sI` and reading `age` and `x-cache`: treat any
  `age` greater than the time since you published as unverified, and
  re-check. A cache buster that silently does nothing is worse than
  none, because it converts "verified live" into "verified the cache"
  while looking rigorous.

  **The cache lies in BOTH directions, which is the half everyone
  misses.** Everything above treats it as a thing that falsely
  reassures. It will just as readily tell you a working page is broken.
  On 2026-08-04 platform and design independently fetched a freshly
  fixed page, got `x-cache: HIT` with `age` in the hundreds, saw
  pre-fix content, and each came close to reporting the deploy as
  failed. Same header, opposite error. Treat a BAD result from a cached
  page as unverified exactly as you would a good one.

  **Compounding trap: searching raw HTML.** A string that reads as one
  phrase on the page is often split across tags in the source, so a
  grep for it finds nothing and looks like proof of absence. Strip tags
  before searching. Against a cached page the two compound into a
  confident wrong answer in either direction, which is how platform
  briefly reported a correct footer as missing on the same day.
- **A green check run is not "done".** The guards prove structural
  properties: the page exists, carries the shared masthead and
  exactly one analytics tag, its numbers match the frozen record, no
  fetcher ran, nothing immutable moved. They cannot tell you a mark
  is too loud or that a correctly placed image contains the wrong
  ocean. The last three real defects on the public surface all passed
  every automated check and were all found by Kristjan opening the
  page. For anything visual, a human look is load-bearing.

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

- `fires/` science, fetch and emitted data: the FIRMS pull, the
  baseline gates, the burnt-area methodology, and the validated JSON
  the pages are rendered from. First issue 2026-08-03.
- Rendering moved to design by D-030. Fire signs off on its rendered
  pages before publish, and does not build them.

### Crops chat (CRO)

- `crops/` science, fetch and emitted data: the ASAP indicator pulls,
  the pair qualification method, the baselines, and the validated JSON
  the pages are rendered from. Approved narrow by D-040; ownership
  ratified by D-041.
- `crops/pull_asap_indicator.py`, `crops/asap_countries.json`,
  `crops/crop_calendars.json`, `crops/FEASIBILITY.md`.
- `crops/.cache/` is gitignored (`crops/.gitignore`) and never
  committed; the committed artifact is the compact derived series under
  `crops/data/`.
- Rendering is design's under D-030. Crops signs off on its rendered
  pages before publish and does not build them.

Two constraints for whoever wires the crops job, recorded here because
both are easy to get wrong and neither is visible in the code:

- **Staleness must be an absolute bound, never a consecutive-no-op
  counter.** ASAP publishes every 10 days, so a legitimate no-op repeats
  for nine days running and the silence looks healthy. Fire lost six
  days to exactly that shape. The threshold is: no new dekad for more
  than 20 days is an error, being two full publication cycles.
- **Probe before downloading.**
  `getIndicatorsInfo.php?dekad=YYYYMMDD&indicator_name=zFPARc` returns a
  small JSON when the dekad is published and a literal `[]` when it is
  not. One small GET decides whether a 30 MB download is worth starting.

### Aftereffects / impacts chat

- `research/impact_database_2026-27.md`,
  `research/impact_timeline_2026-27.md`
- The cross-channel damage ledger content (vintage-tracked named
  estimates across heat, drought, agriculture, food security,
  humanitarian, economic). Fire-specific content stays with the
  Fire chat; aftereffects owns the view that reads across channels.

### Country reports chat

- Per-country baseline pieces: the research, the baselines, the
  numbers, to the editor's format. No standing files in the repo yet.
- Pages are built by the design chat from the data and copy this chat
  produces, on a design template, per D-030. (This line previously
  said platform designs those surfaces; that was wrong twice over.)

### Editor chat (formerly "public chat")

- All reader-facing prose: lede, bottom-line copy, chart-caption
  framing outside the figure, `public_preamble`,
  `PUBLIC_SOURCE_NAMES`, and the prose strings in `card.py`
- **Exception: Notes (D-093). Kristjan writes every Note himself; the
  editor chat reviews each one against editorial standards 5a rather
  than drafting it.** His reasoning: "the reader needs human writing."
  This is a premise rather than a preference. The Notes surface exists
  because the channel pages are the instrument and a named human
  interprets them, so a drafted Note makes the premise false. Recorded
  here as well as in the ledger because the map is what a new chat
  reads first, and this is the one surface where getting it wrong is
  not recoverable by a later correction.
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
- **All front end for every channel** (D-030): the page templates
  every surface is rendered from, and the merges. Works template-first,
  and the first deliverable is the fast-reaction template, because that
  is the one on T4's critical path with a one-day budget.

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
- `research/allhands.md` (D-059). Owned here rather than by product
  because it is a shared artifact like this file, not a product
  surface. Any chat appends a broadcast; platform keeps the cap
  enforced and the delivery mechanism working.

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

### Long unattended jobs on Kristjan's laptop

Added 2026-07-28, after four unattended pulls from three chats ran
overnight on one machine, none of them aware of the others.

- **Hold a DURATION-based wake lock, never a pid-scoped one.**
  `caffeinate -i -m -w <pid>` dies with the job that owns it, so the
  first job to finish decides when the machine sleeps and silently
  kills everyone else's. Use `caffeinate -i -m -t <seconds>` covering
  the whole expected window instead.
- **But a duration lock sized against an OPTIMISTIC ETA fails just as
  silently, and that is the other half nobody had written down.** The
  lock expires, the machine sleeps, and the job stays alive and simply
  stops progressing, which is indistinguishable from slow. Heat lost
  about eighteen hours to this on 2026-08-04: `pmset -g log` showed
  repeated Maintenance Sleep from 23:00, and the three stalled chunks
  completed **53 seconds** after the machine was woken. The 1,667
  logged "connection errors" were the client noticing a sleeping host,
  not a network fault and not the API.
  **So: when progress plateaus, check `pgrep caffeinate` BEFORE
  diagnosing the network**, and renew the lock rather than sizing it
  once. We have now lost a night to each variant of this, the
  pid-scoped one above and the expired-duration one here, and both
  present as "the job is running, it is just slow".
- **`caffeinate -i -m` blocks idle and disk sleep only. It does NOT
  survive the lid closing.** Written down because it was asserted the
  other way once and cost a night of fetching. Lid open, on power.
- **Announce a multi-hour job where another chat can see it.** Append
  a line to `.running-jobs` at the repo root (gitignored, so it never
  reaches a commit, and visible to every chat because the working tree
  is shared): what is running, which chat, and the expected finish.
  Remove the line when it ends. Read the file before starting your own,
  because three chats each believed they were alone on the machine.
- Assume every long pull is resumable and check that it is before
  starting it unattended. A job that cannot resume turns a sleep into
  lost hours rather than lost minutes.

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
