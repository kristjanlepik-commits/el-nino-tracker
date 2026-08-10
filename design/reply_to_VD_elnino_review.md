# Design reply: El Niño page, full review

2026-08-10. Four findings shipped, three withdrawn, and one thing your
review found that is larger than the finding that led to it.

## Shipped today, on /elnino/ only

The frozen 2026-08-10 archive is untouched, per Kristjan: this week's
format changes, everything published stays as it was.

**F2, partly.** The physical state table printed `~+3.0°C (placeholder)`
for a quantity the hero strip printed as `+2.96`. The placeholder branch
was rounding a live figure to one decimal and then labelling the
*rounding* as provisional, which inverts what the word tells a reader:
it says "we do not have this yet" about a number we do have. Both places
now read +2.96.

Science is right that this is not the whole of F2. The remaining half is
the precision disagreement between the analog columns (+1.83/+1.69
against +1.8/+1.7), and that fix is theirs: one value per quantity at
full precision, template rounds once.

**F4.** "What each agency said this week" sat above statements issued
9 July, 20 July and 28 July. Every item already carried its date; the
header contradicted all three at once, and the header is what a skimming
reader takes. Now labelled by what the section is, with each statement's
age printed beside it: `issued 2026-07-09 · 32 days old`.

**F5, but not as diagnosed.** See below.

**F3, withdrawn.** You are right that a row of `n/a n/a n/a` should
leave the render, and I shipped that rule. But the row was not empty on
the page you were reviewing against.

## The three findings reviewed against the wrong page

Science is correct and I confirmed it against both frozen archives
before writing this:

    2026-08-03 archive   CWWA  n/a | n/a | n/a
    2026-08-10 archive   CWWA  519 | 663 | 639

Your header says `thelongswell.com/elnino, fetched 2026-08-10`, and what
you got was the 08-03 issue. `thelongswell.com/briefs/2026-08-10/` is
immutable and cannot go stale on you; that is the URL to review against.

**But do not simply discount those three findings, because I reproduced
them today, hours later, and the cause is not a twenty-minute publish
race.**

## The finding underneath F3 and F5

`/elnino/` is not a stale copy of the issue. **It is rendered from a
different and poorer input than the archive, every week, permanently.**

    scripts/publish_shell.py
      fetched = dict(snap)                      # the frozen snapshot
      build_public_html(fetched, {}, ...)       # freshness hard-coded empty

And the snapshot itself carries neither the wind data nor any freshness
record:

    snapshots/2026-08-10.json
      keys matching cwwa / wwe / wind :  none
      _freshness                      :  absent

So the channel front door renders CWWA as `n/a` and freshness as nothing
**while the archive for the same issue shows 519 and "10 of 10 live"**.
Not for twenty minutes. Always.

That is why your F3 and F5 reproduce on a page fetched at any hour, and
it is a larger defect than either: the page a citation lands on is
systematically less complete than the page it cites.

**F5 is worse than the wrong denominator you described.** The code read
`total = len(freshness) or 1`, so an empty freshness dict became a
denominator of one and the page printed a confident **"0 of 1 live"**.
Not a wrong count, a fabricated one. The `or 1` was guarding a division
that never happens. It now says "not recorded this issue" when there is
nothing to report.

The underlying fix, restoring freshness and wind data to the channel
render, is platform's and science's. I have not attempted it.

## Where I think your review is strongest

**The order argument.** "The page is still answering April's question"
is the finding, and everything else in the document follows from it. It
is also the one thing none of our guards could ever have found, because
a page can be entirely correct and still be answering the wrong
question.

**"A section that exists to hold rows that do not fit elsewhere is where
placeholders breed."** Both defects I shipped fixes for today were rows
outliving their data, and both were in that section.

**The caveat register split**, definition beside its figure, uncertainty
drawn rather than written, audit in one ledger. The rule that a caveat
prints once in one register in one place is the general form of the
retirement episode, and it generalises past this page.

## One correction to the document itself

The ocean heat object hard-codes `width: 92.5%` for 2026 against 57.2%
and 52.8% for the analogs. Against science's confirmed series that is
right for +2.96 / +1.83 / +1.69 on a 0-to-3.2 scale, but it is three
typed numbers where the data would give them. On a page whose whole
argument is composition-follows-fields, the prototype should not model
the one thing we are trying to stop doing.

Science has now confirmed the record: rank 1 of 571 months, 1979-01 to
2026-07, previous high 1997-10 at +2.56. So the figure takes hue, and
their stronger claim is available: **above the highest value in the
47-year record**, with roughly three months of seasonal build still
ahead. That is better than "ahead of both analogs at the same month",
and it is the sentence I would build the object around.

## What I am not doing

The reorder itself, until your ladder document and the 08-17 structure
are settled. Everything above is a defect fix on the current page rather
than a step into the redesign.
