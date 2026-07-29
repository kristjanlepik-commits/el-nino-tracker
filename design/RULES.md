# Design rules that bind every template

Owned by the design chat. `research/decisions.md` records THAT each of
these was decided; this is where the detail lives, per CLAUDE.md.

Written down because they arrived one channel at a time, in chat, and a
rule that exists only in a code comment binds only the file it sits in.
Every one of these was learned from a defect that reached a rendered
page, and most passed every automated check on the way.

## 1. Incommensurable quantities are never combined

Three channels have now handed me the same rule in three vocabularies,
which is what makes it a system rule rather than a channel preference.

- **Fire.** Detections and burnt area are never merged into one figure
  and never converted into each other. Different instruments, different
  latencies, and they disagree in direction: Algeria is 1.9x on the week
  and 14.2x on the year, Botswana 5.9x and 0.4x.
- **ECON.** Firefighting cost, direct damage and output loss are three
  categories and **adding them double-counts**. A stacked bar is the
  natural treatment and would be a factual error, so the template must
  make it impossible rather than merely not do it.
- **Design.** Two multiples never share a frame, because a reader seeing
  them adjacent reads one as a correction of the other.

The layout is the enforcement. Give each instrument its own column, its
own baseline and its own hero; never a summary line, never a total,
never a stack. If a reader has to be told in a caveat that two numbers
are not comparable, the layout has already failed.

**Corollary, from ECON:** naming what is *uncounted* is what stops a
reader treating a partial total as the cost of an event. Rows with no
figure carry as much weight as rows with one.

## 2. Calibration, not amplification (D-043)

The system must be equally capable of showing "this is within
historical range" as it is of showing "this is extreme". A chart that
can only look alarming has stopped being an instrument.

The test: **would a reader believe this same chart if the line were
unremarkable?**

- The reference case is Botswana rendering in ink at 0.4x, not Spain
  and France, which pass the test but pass by luck because both are
  extreme. A chart of two extreme cases never exercises whether the
  system can show normal.
- Channel hue is spent only where a datum clears the baseline it is
  measured against. Below it, ink. This is a threshold, not a colour
  ramp, so it does not collide with D-016 amendment 4.
- **Stability is a finding.** ECON: Windstorm Goretti moved 2.5% across
  three vintages and the LA fires moved fivefold in four days. If the
  treatment cannot make the 2.5% look as considered as the 200%, that
  is a design defect, not a boring story.

**Corollary, and it generalises past colour:** fading the element that
declines to make a claim is the cheapest way to imply the claim. It
cost us twice, on the `attribution pending` tag at 4.75:1 against 8.2
and 8.8 for the states either side of it, and on the fires index where
a non-anomalous country rendered identically to a record one. A neutral
result reads neutral, at full weight.

## 3. An annotation may state a pattern, never a cause

The attribution tag is the only place on a page where a causal claim
belongs. "Recurs in 2019, 2021 and 2025" is a pattern and is sourced;
"pastoral burning" is an inference, however likely.

If a cause is not in the data with a named source, it does not go on the
chart. This binds the channel handing over copy as much as the render.

## 4. Furniture over a data field carries a paper halo (D-023, D-026)

`paint-order: stroke`, and drawn twice where it must survive both ends
of a diverging scale, because the scale is dark at both ends by design.
Applies to marks as well as labels: an event disc carries a paper ring
*outside* its radius, never a stroke on it, because the radius is the
datum.

Halo is the floor. Where empty plot space exists, move the label too.

## 5. Report clipping; never widen a published scale (D-024)

`OCEAN_SCALE` has already coloured published issues, so widening it
would silently re-scale the meaning of every archived brief's colours.
Draw the scale ends open, state the observed extreme in the caption.

Alpha is not a legitimate softening device on a data mark: a composited
step is a colour the legend does not print, so a reader cannot decode it
and cannot tell which margins to trust.

## 6. A named source is a field, never a literal

12 of 45 fire countries resolve to EFFIS and 33 to GWIS. A hardcoded
source would have named a European instrument for Canadian fires on most
pages, on the block whose entire job is provenance.

## 7. Every emitted field is read, or explicitly declared unused (D-046)

The channel emits flags precisely so a renderer can distinguish cases
that must not look alike. Ignoring one produces a *false* page rather
than a plain one:

- fire's `anomalous` / `volume_context`: DR Congo at 1.0x rendered as an
  event, and the index headline counted it among countries "burning well
  above their own seasonal normal"
- fire's `multiple_unstable`: the UK's 2.9x rests on 407 detections
  against a mean of 138
- ECON's `absence_meaning`: four reasons a figure is missing that look
  identical and mean opposite things
- ECON's `caution`: AccuWeather publishes no methodology and lands two
  to three times above everyone; unread, it renders identically to
  Swiss Re
- ECON's `derived`: marks what is ours rather than an estimator's, which
  is the D-033 Combined label

A validator can enforce that these exist. Only the renderer can enforce
that they are shown.

## 8. Boundary rules come from an explicit class, never from position

`:first-child` and `:first-of-type` break the moment anyone inserts a
block above. The builder sets an explicit class and the CSS depends on
nothing above it.

## 9. Rule weights are px and must not scale with the viewport

Use `vector-effect: non-scaling-stroke` inside a scaled SVG. The
coastline was wired to `LAND_LINE` at 0.4 viewBox units, which rendered
0.72px: present in the markup, invisible on screen, and reported as done
by every check that read the source rather than the result.

## The habit behind most of these

Verify the property you changed, in the rendered result, not the
property that seems related in the source. Three defects this week came
from checking font size instead of contrast, a CSS variable instead of a
computed width, and a working tree instead of a commit.
