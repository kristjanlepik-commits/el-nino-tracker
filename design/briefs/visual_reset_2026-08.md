# Visual reset: brief for VD

Design, 2026-08-22. Written because a reader told Kristjan the site looks
AI-generated, naming the colours and the charts. This brief exists to make
that finding actionable, because "make it more human" is not.

## The finding, and it is not wrong

The literal claim is false: nothing is a matplotlib default. Charts are
inline SVG driven by `tokens.py`, and `analog.py` references brand tokens
twelve times. The colours were chosen.

**Chosen and generic are not opposites.** A warm bone ground, a serif
display face, a terracotta accent and hairline rules is itself one of the
looks that currently reads as machine-made. We chose our way into the
cluster. The reader is reporting the family we landed in, not our care.

## What I measured before writing this

Share of colour references on each page that are chromatic, saturation
above 0.25. Neutral means cream, ink, grey.

    front              66 refs    76% chromatic
    crops idx          42 refs    29% chromatic
    crops country     195 refs    44% chromatic
    heat idx           33 refs    36% chromatic
    heat city          23 refs    35% chromatic
    fires idx          84 refs    29% chromatic
    elnino             42 refs    29% chromatic
    pyrenees           63 refs    29% chromatic
    lima               63 refs    29% chromatic

**The front page is not the problem.** It is 76% chromatic: deep blue,
teal, rust, purple, four channels at once. Every interior page is 29% to
44%, which is a cream ground, ink text, grey hairlines and a single accent.

That matters because the front page is where we spent the design effort
and the interior pages are where a citing journalist lands. **We look most
generic exactly where we did the least specific work.**

The two pieces published today sit at 29%, which is the bottom of that
range. They are the newest thing on the site.

## The split inside our own work, which is where the brief starts

Not everything reads as template. The distinctive things are the ones the
data forced into a bespoke form:

- the crops region maps, three instruments as small multiples, colour and
  outline carrying different facts
- the sequence grid, five bands over dekads, with a state for coverage too
  thin to read
- the analog fan

What reads as template is the **generic fallback chart**: grey bars, one
bar highlighted in an accent, mono tick labels, a hairline baseline. It is
the single most recognisable AI-generated chart form and it is what both
of today's pieces carry.

**So the brief is not "redesign everything".** It is: the chrome and the
generic chart produce the reading; the bespoke forms already escape it.

## What to rule out, so the work is checkable

Someone can be told they failed this list. Ours is the first one.

1. Warm cream or bone ground, serif display, terracotta or rust accent
2. Near-black ground with a single acid accent
3. Broadsheet hairline rules with dense columns
4. Inter or Space Grotesk as the safe face
5. Rounded cards with an accent rail
6. Everything centred

For charts specifically, rule out: the single-highlighted-bar bar chart,
the lone sparkline, and mono-everything as a signal of rigour.

## Two constraints that are not aesthetic

**The semantic layer is load-bearing and the chrome is not.** Channel hues
carry meaning (`nino` `#173F9E`, `fire` `#B32E10`, `flood` `#0A5C66`,
`crop` `#2E5C16`, `damage` `#5C2C96`) and their contrast ratios were fought
for and documented. The ground, the display face, the rules and the
generic chart are what produce the AI reading, and they are the least
load-bearing part of the system. **These two layers barely overlap**, which
makes a reset far more tractable than it looks: the chrome can move
without touching what a colour MEANS.

Caveat inside that: `fire` at `#B32E10` is both a channel hue and the rust
accent that puts us in cluster 1. It is the one token that sits in both
layers and it will need deciding rather than assuming.

**A reset is a dated boundary, not a repaint.** Archives are immutable
(invariant 5). Eighteen frozen briefs and every past dated piece stay in
the current palette forever, and the new one begins on a date and sits
beside them. That is a decision to take deliberately, with the date
recorded in the ledger, not a side effect of a token change.

## What success looks like

Not "looks human". Two checks:

1. A page from the site, shown without its masthead, is not placed in any
   of the six families above by someone who has not seen it before.
2. The interior pages, not the front page, pass that test. They are what
   gets cited.

## Why this outranks cosmetics

Traffic fell 84% this week to 143 uniques, and citations are the route out
of that. A page that reads as machine-generated does not get cited by the
people whose citation counts. **This is a credibility defect wearing an
aesthetic complaint's clothes.**
