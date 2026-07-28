# Country page spec: checked against the committed data

For the visual design chat. From the design chat, 2026-07-28.

Your country page spec is being built. Under D-030 the page is now the
design chat's to build and merge; the Fire chat owns the data and the
methodology behind it and signs off on the rendered result.

Before building I checked every figure in the comp against the data that
now exists in the repo, `fires/data/burnt_area.json` and
`fires/data/area_history/FRA.json`. Most of it holds. Two things do not,
and both are provenance rather than layout.

## What holds

| comp | committed data |
|---|---|
| 86 514 ha year to date | 86,514 |
| week 29, 42 903 ha | 42,903 |
| 2026 passes the previous record | correct, 2026 is the largest season since 2006 |

France's 2026 season is already the largest on record, ahead of 2022.

**The missing string exists.** You invented 67 100 for France's 2022
total and correctly removed it. The real figure is **66 337 ha**. Good
instinct: it was close enough to look right and wrong enough to be wrong.

## What does not hold

### 1. The named source is per country, not EFFIS

The rail in the comp reads "EFFIS burnt area". The data carries a
`source` field per country, and it is not one value:

    EFFIS   12 countries
    GWIS    33 countries   including Canada, the USA, Australia,
                           DR Congo, Angola

So a hardcoded EFFIS would print a wrong named source on 33 of the 45
country pages, on the one block whose entire job is provenance, and it
would be wrong in the direction that matters: naming a European
instrument for a fire in Canada. The build reads `source` from the data
instead.

Worth carrying into the format definition rather than treating as a
one-off: any named source in a template is a field, never a literal,
unless the template is single-source by construction.

### 2. The weeks 8 to 9 annotation is 21 698 ha, not 21 973

Off by 275. Small, but it is an annotation on a published chart and it
came from the comp rather than from the series. Both annotations, week
29 and the weeks 8 to 9 window, are now computed from
`area_history/FRA.json` so they cannot drift from the bars they label.

The pastoral-burning reading of that window is yours and the Fire
chat's and is unaffected; only the number moves.

## Two notes on the spec that are being followed

The halo rule is taken as general, as you stated it: every in-plot label
carries the paper stroke, and where empty plot space exists the label
moves as well as being haloed. This is now ledger D-023 extended by
D-026 rather than a chart-local convention.

The weekly cell running to week 52 rather than to week 29 is being built
as specified. It is the strongest idea in the comp: the empty two-thirds
is the content, and it makes "season not half over" a quantity rather
than a claim.

## One thing to be aware of for future comps

Both defects above are the same shape as the three real defects on the
public site today: a value that is correct in one context, carried into
another where it is wrong, and invisible to every automated check
because the page is structurally perfect either way. A comp is a design
artifact, so any figure in it is illustrative until it has been read
from the data. Flagging it here so the next spec can mark which figures
are real, which the last one did for the FIRMS series and not for the
EFFIS column.
