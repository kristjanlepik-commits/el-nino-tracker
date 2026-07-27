# Rendered pages, for design review

Generated output, not production and not published. GitHub Pages serves
`docs/` only, so nothing in here is on the live site.

These are what `run_brief.py` actually produces, so they are the honest
subject of a design review: the CSS in them is `PUBLIC_CSS` verbatim,
and every number came from the 2026-07-20 snapshot and the fire
pipeline's 07-20..07-26 week.

| File | What it is |
|---|---|
| `front-page.html` | the house front page, global event map, 14 countries |
| `weekly-issue.html` | the El Nino dense data page |
| `methodology.html` | the credential document external reviewers read |
| `archive.html` | the issue index |

Asset paths point back at `../../docs/`, so open them from this folder
and the fonts, chart and map resolve.

## Where the source lives

- `tokens.py` at the repo root: the single source of truth for colour
  and type. Read this first; the reasoning is in its comments.
- `run_brief.py`: `PUBLIC_CSS` for the site, `_map_html` for the event
  map, `_ocean_heat_html` and `_render_rung` for the two components
  worth arguing about.
- `citable.py`, `analog.py`, `card.py`: the three image surfaces.

## Regenerating

    .venv/bin/python run_brief.py --preview --date 2026-08-03

Preview writes to `briefs/<date>-preview/` and touches neither `docs/`
nor the snapshot history.

## Caveat that matters

**This is on branch `worktree-tls-rebrand`, not `main`.** Reviewing
`main` will show none of it. The merge is held until the 2026-07-27
issue publishes, because that issue must ship under the old branding
with its archive copy unrestyled (D-013).
