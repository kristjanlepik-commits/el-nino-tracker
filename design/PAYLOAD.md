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
