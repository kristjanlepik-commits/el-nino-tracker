# Brief for VD: the El Niño probability ladder

Design, 2026-08-10. For a proper redesign rather than a restyle, at
Kristjan's direction.

## Why this is a redesign and not CSS

Three things landed on this object in one day, and each changes what it
should emphasise rather than how it should look:

1. **A rung was retired** (+2.0), because it reached 100%.
2. **The 100 was 99.850 rounded up**, against NOAA's own 99 the same
   week. Displayed probabilities are now bounded to [1, 99].
3. **Volatility is now monotonic with height.** The higher the rung, the
   more it moves.

Any of those alone would be a tweak. Together they mean the ladder is a
different object from the one the current layout was drawn for.

## The finding the design has to carry

**The ladder is saturating from the bottom up.** It is not static and it
is not uniformly live.

    rung        mid   weekly mean move since 15 June
    super >2.0   99   0.62   retired, reached 100 and was capped
    >2.5         98   2.25   nearly there
    >3.0         94   3.50
    >3.5         70   5.60   the most volatile rung on the ladder

Two rungs have topped out in two months. **The most informative figure
the site publishes is currently 70 per cent for a peak beyond +3.5 °C**,
and it sits at the end of a block a reader is likely to skim as settled.

The current layout treats the four rungs as one object of equal weight.
That was right when they moved together and is now wrong in a specific
way: it buries the live number under the finished ones.

## The constraint that matters more than any of it

**Never encode which rung is live. Read the fields.**

Science emits, per bucket:

    retired      true when the rung has topped out and left the render
    state        settled | live
    saturated    true when it cannot move up

A design that names the top rung as the volatile one is true this week
and will stop being true. >2.5 is at 98; the third rung is coming. If
the emphasis is a judgement re-made in CSS each time the numbers shift,
it will be re-made wrongly at least once and nobody will notice, because
a stale emphasis produces no error.

**Composition has the same problem as emphasis.** The current assembly
hard-codes which rungs exist. Both should follow the data: settled rungs
render as resolved, live rungs render as the reading, and retired rungs
leave the render without anybody editing a template.

Retirement is presentation only. The computation, the internal brief,
the snapshot and meta.json keep every bucket, so the archive series and
the v1.9 verification pledge stay unbroken.

## What the rounding episode should teach the drawing

The live page printed "+2.0 °C peak, 100% probability" a few lines above
its own footnote explaining that rungs reaching 100% are retired. **The
page stated its convention and breached it in the same view.**

That is a design failure as much as a data one. A number and the rule
that governs it were far enough apart to contradict each other without
anyone noticing. Whatever the redesign does, the retirement rule and the
rungs it governs should be legible together.

And 100 should be unreachable by construction now, not by luck: nothing
in the design should imply certainty, because the underlying figure is
bounded to 99 precisely so it cannot.

## The open question, which is yours to answer

**Should observations lead the page, ahead of the probability ladder?**

The argument I went in with was that probabilities were static, and
science withdrew it. The better argument survives: SST has climbed every
week without a reversal and CWWA runs at 41 per week, so **observations
lead because they are evidence a reader can check**, not because the
alternative is quiet.

But item 2 above cuts against putting the ladder in a de-emphasised
block. Both can be true, and reconciling them is the design problem.

## What is not in scope

Heat content stays a dated statement rather than a standing component:
+2.96 is a single July print and the next release is early September.

## Constraints from the rest of the system

- **One ink.** D-101 retired channel colour; hue marks a record and
  nothing else. The ladder cannot have a palette.
- **D-043, calibration not amplification.** A rung within its normal
  range must read as legibly as an extreme one. The site's own rule,
  ratified on another channel: colour carries the finding, never the
  recency.
- **Archives are immutable.** Any change lands in the next issue and
  never rewrites a published one.

## Where the detail lives

`research/decisions.md` D-115 for the retirement and the rounding.
`design/VD_NOTES_REVIEW.md`, parked section, for science's own account
of the correction. The payload fields are in the weekly meta.
