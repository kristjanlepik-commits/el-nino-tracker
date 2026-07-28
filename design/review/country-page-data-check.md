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

Off by 275, and the origin was not the comp. **Correction to the first
version of this note, which blamed the comp.** The Fire chat has since
said the 21 973 was theirs: it is weeks 8 to **10**, mislabelled as 8 to
9 when they handed it over. Week 10 adds only 275 ha, which is why it
looked close enough to survive.

The fix is the same either way and would have caught it at either end:
both annotations, week 29 and the weeks 8 to 9 window, are computed from
`area_history/FRA.json` rather than typed, so they cannot drift from the
bars they label.

### 3. The pastoral-burning label comes off

New, and it overrides the comp. The Fire chat has ruled that "pastoral
burning" must not appear: it is their inference, not a sourced fact.
Ecobuage in the Pyrenees is a real documented practice in that window
and is the obvious candidate, but nobody has verified that this specific
burn is that, and asserting a cause without a named source is what the
aggregator posture forbids.

What is defensible is the pattern rather than the cause. The same
late-February window carries 16 583 ha in 2019, 15 171 in 2021 and
12 353 in 2025, so 2026 is the largest in the record but not different
in kind. The annotation will read along the lines of "recurs in this
window: 2019, 2021, 2025", which does more work than the guess did.

Worth generalising into the format definition: an annotation may state a
pattern, and may not state a cause unless the cause has a named source.
The attribution tag is the only place a causal claim belongs.

## Two notes on the spec that are being followed

The halo rule is taken as general, as you stated it: every in-plot label
carries the paper stroke, and where empty plot space exists the label
moves as well as being haloed. This is now ledger D-023 extended by
D-026 rather than a chart-local convention.

The weekly cell running to week 52 rather than to week 29 is being built
as specified. It is the strongest idea in the comp: the empty two-thirds
is the content, and it makes "season not half over" a quantity rather
than a claim.

## The emphasis constraint, from the Fire chat

Recorded here because it is the hardest thing to check and the easiest
to lose, and because it binds the render rather than the data.

**A fires page must not read as an El Niño story.** This week eight of
the twelve live countries are tagged `pending`, both Amazon boundaries
are running at under half their normal burn (ARO 0.46x, Brazil Legal
Amazon 0.48x), and the EU sits at 2.80x. So the honest reading is a
European fire season, not a global ENSO signal.

A page that led with El Niño framing would be wrong in a way that every
individual number on it would survive, which is precisely the gap D-030
condition 2 exists to close: correct numbers rendered misleadingly. It
would also pass every guard we have, because no structural check can see
a narrative.

What this means for the build, concretely:

- No ENSO framing in a fires lead, standfirst or claim unless the tag
  on that specific item says `enso`.
- `pending` renders as pending. It never falls back to a claim, and it
  is not visually quieter than the other two states, because the
  cheapest way to imply a link is to make its absence look like an
  omission.
- The house context, that this site is primarily an El Niño tracker,
  does not travel into a channel page as an assumption. The channel
  page argues from its own baselines only.

## One thing to be aware of for future comps

Both defects above are the same shape as the three real defects on the
public site today: a value that is correct in one context, carried into
another where it is wrong, and invisible to every automated check
because the page is structurally perfect either way. A comp is a design
artifact, so any figure in it is illustrative until it has been read
from the data. Flagging it here so the next spec can mark which figures
are real, which the last one did for the FIRMS series and not for the
EFFIS column.
