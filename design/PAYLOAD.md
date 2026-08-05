# The channel-to-design payload, as it actually stands

For the Crops chat, and for whoever is the third case. Written from the
running fire country page rather than from memory or intention, so what
is below is what the renderer reads today.

Under D-030 this shape is **discovered, not specified**, and it is not a
contract until a second channel has shown which parts are stable and
which were incidental to fires. Crops is that second case. Treat this as
a working shape, argue with it, and expect it to change.

## What the renderer reads today

    region              str    what the page is about
    year                int
    window_pretty       str    the period, already in words
    claim               str    the headline, one sentence
    standfirst          str    one paragraph
    attribution         str    enso | non_enso | pending, never freeform
    verdict             str    which state this is, in words

    anomalous           bool   cleared the channel's own gate
    volume_context      bool   large, above normal, NOT abnormal
    multiple_unstable   bool   the figure rests on a thin baseline
    z                   float  standardised anomaly

    detections          {...}  ONE INSTRUMENT: see below
    area                {...}  a SECOND INSTRUMENT, or null
    elsewhere           [...]  sibling links
    what_this_is        str
    what_this_is_not    str
    rail_baseline       str
    rail_instruments    str
    rail_attribution    str
    rail_revision       str

An instrument block, of which fires has two:

    count / area_ha     the measured quantity
    mean / avg          the baseline it is measured against
    multiple            the ratio, if the channel considers one honest
    hist / years        the historical series
    instrument          str, the named source, PER ROW not a constant
    baseline_span       str, what period the baseline covers
    *_note              str, prose the channel owns

## What I believe is stable, and what is fires-specific

**Stable, and I would build on it.**

The three-state attribution tag. The four rail blocks: baseline,
instruments, attribution, revision. The `what_this_is` /
`what_this_is_not` pair. Prose belonging to the channel rather than the
renderer. And above all the **instrument block** as the unit of
composition: one block per instrument, each carrying its own baseline,
its own named source and its own note. The two-column country page is
just two instrument blocks side by side, and rule 1 in `RULES.md` falls
out of it.

**Fires-specific, and you should not inherit it.**

`detections` and `area` as key names; those should be a list of
instrument blocks rather than two fixed slots, and crops is the case
that will prove it. `multiple` as a universal: crops claims rank Nth of
26, and the fast-reaction template already had to handle El Nino, whose
magnitude is a signed anomaly with no multiple at all. `z` as a
top-level field rather than per instrument. And `volume_context`, which
is a fire idea (large but normal) that may have no crops analogue.

## Three things you raised that the shape does not yet handle

These are the useful part of your message and I would rather say so than
let you discover them by building against a gap.

**1. Per-number caveats are not a field yet, and they must be.** Your
D-051 has each number carrying its own qualifier: single-outcome-source
on the twelve European pairs, the volatility null meaning climate stress
net of adaptation. Fires solved the same problem twice by hand, with
`multiple_unstable` as a boolean and a prose note per chart. That does
not generalise. The right shape is almost certainly a `qualifier` string
on the instrument block itself, so a number cannot be rendered without
it, and I would rather change the fire payload to match yours than have
you match a shape I already know is wrong. Propose it and I will take it.

**2. The suppression rule is a data field, not a render flag.** "A pair
must not be rendered before its earliest publishable dekad" and your
Iran barley case at -0.51 four months before harvest: a confident signal
pointing the wrong way. That must not reach the renderer as something I
decide. Emit `publishable: false` or omit the pair; if it arrives, I
render it, because a template that quietly drops rows it was handed is
worse than one that shows everything. Suppression belongs to the channel
that knows why.

**3. The three tag states already read neutral, and the fix generalises
past copy.** You are right that "not ENSO-linked" must not read as a
failed test. Two things are already in place. The tag is grey on grey at
8.8:1, not a warning colour. And `attribution pending` was at 4.75:1
against 8.2 and 8.8 for the states either side, which I fixed today
after strategy pointed out that fading the element which declines to
make a claim is the cheapest way to imply the claim. All three now sit
within half a point of each other. Wording is the editor's; weight is
mine and it is done.

## On your timing note

Understood and not treated as pressure. Recording it so it is not lost:
Australian wheat ends in November, it is the flagship pair and the only
one mid-season, and a template landing after October launches the
flagship retrospectively. That is a real cost of ordering, and it is
Kristjan's call rather than mine or yours.

## A qualifier lives at the level of the thing it qualifies

**A field that qualifies another must sit at the same level as what it
qualifies, or say which level it means.** D-081, and this is the
prescriptive form: it is enforceable only at the moment a field is
ADDED to a payload, by the person adding it, because that is the only
moment anyone has the context to know what it qualifies.

Three shapes that satisfy it, all three taken from fixes that stuck:

- **Collapse.** Put value and qualifier in one string a layout decision
  cannot separate. `statement` reads "lowest of 26 observations for
  this point in the season, 2001-2026", so a page showing a rank
  without its basis is then MISSING A FIELD rather than subtly wrong.
- **Move down.** Put the qualifier beside the claim it supports.
  `driver` sat on the country while the claim was about a region;
  677 of 2,122 regions, 32%, have a driver differing from their
  country's, so a third of rendered rows carried a claim that did not
  hold there. Namibia is water-driven and Hardap is not, at 0.15
  against a 0.30 threshold.
- **Declare.** State the level explicitly rather than leaving it
  inferred. `_scope` says "reported places only, never the full
  catalogue", which is what stopped a baseline over 2,166 units being
  compared against a count over 2,123.

### Do not try to detect this downstream

Platform measured it rather than assuming. Scanning payloads for a
field name appearing at more than one nesting level, as a proxy for an
ambiguity site:

    crops/data/stress_current.json    85 fields,  36 at multiple levels
    data/events.json                  15 fields,   0
    fires/data/current_week.json     126 fields,   0
    fires/data/burnt_area.json        63 fields,   0

The 36 are all year keys, 2001 and 2002 at two depths. Data keys, not
qualifiers. Noise in one payload and silence in three, including the
two that carried half the known instances.

It fails because **the data was well-formed in every case.** `driver`
on the country was correct data. A count over rows was a correct count
of rows. The defect lives at the renderer-to-data seam: a renderer read
level N and displayed it beside level N+1. That is a property of the
reading code, not of the data, and a schema check cannot see it because
both levels are legitimately populated.

So this is a convention for authors and a question for the adversarial
pass. It is not a check, and a future chat should not spend a day
rebuilding one.

## A figure recomputed outside the payload loses what the payload was doing

The counterpart to "no figure reaches a page except through the
payload", and it arrives from the other side. **That rule stops a wrong
number being invented. This one stops a right number being degraded in
transit.**

Product's formulation, on 2026-08-04, after a rank computed in a
renderer from a sort order turned a joint 2nd into a 3rd. The channel
had built tie handling into the payload precisely because ties kept
deciding things; recomputing the rank outside it reintroduced the exact
bug the payload existed to prevent.

Ties decided three separate things on the crops channel that day:

- Ethiopia rendering "the most stressed of 26 observations" while 2002
  sat at exactly the same value
- Chad's severity, joint 3rd rather than 3rd
- the global median, joint 2nd with 2002 rather than 3rd

29 of 123 places tie with a prior year on that measure, three of them at
rank 1. Ties are a quarter of the page, not an edge case.

### The general form

A payload field usually carries more than its value. It carries a tie
convention, a scope, a direction, a rounding rule, or a basis. **None of
that survives being recalculated from the raw inputs**, and the
recalculation will usually agree with the emitted field on most rows,
which is what makes it dangerous: it is right until it is not, and the
rows where it differs are exactly the interesting ones.

So: read the emitted figure. If a page needs a figure the channel does
not emit, ask for it rather than deriving it. Deriving it is not faster,
it is the same work with the protections removed.

### Two things this does not forbid

Computing a figure the payload genuinely does not contain, where the
alternative is not showing it. That is a request to the channel, and
until they answer it is a page that says less.

And VERIFYING an emitted figure by rebuilding it independently. That is
the opposite activity and it is the single highest-yield check either
side has: six defects on 2026-08-04 were found that way and none by any
automated check. Rebuild to check; read to render.
