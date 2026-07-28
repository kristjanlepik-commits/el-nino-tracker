# Pacific SST field on the front-page map: what shipped, and four questions

For the visual design chat. Written by the design chat (Claude Code).
Screenshots are attached separately by Kristjan, because you have told us
you read text and structure rather than pixels.

Images, if your tooling can fetch them:

- `design/review/map-field-variants.png` the two band treatments compared
- `docs/pacific-sst.png` the shipped asset itself, transparent outside the band

Both are in this repo under the same commit as this file.

## What shipped

The front-page map now carries a measured SST anomaly field over the
eastern Pacific, dateline to the South American coast. It replaces the
flat-filled Nino 3.4 box, which was the honest maximum while no fetcher
returned a grid: inventing the spatial structure would have been
original modeling presented as observation, which the build philosophy
rules out.

- Nine discrete steps from `tokens.ANOMALY`, on the absolute
  `OCEAN_SCALE` of 3.0. No new palette, no new legend, as you specified.
- Placed as a PNG underlay beneath the land in the inline SVG, so
  coastlines cut the field rather than the field covering them.
- The Nino 3.4 box drops its fill and becomes an outline with its label
  and value on top. The field is the datum now; the box is a locator.
- Extent is read from `docs/pacific-sst.json` rather than from constants
  retyped into the template. A field drawn half a basin off is worse
  than no field.

## Three deviations from your spec, each deliberate

**1. Not 1 degree cells. That product is dead.** `sst.wkmean.1990-present.nc`
stopped updating on 2023-01-29: 1727 weekly steps and no more. Building
against it would have rendered a map three and a half years stale, and
nothing about the file's name or location says so. This uses the live
0.25 degree v2.1 daily product, subset over OPeNDAP before transfer, so
the 271 MB and 1.4 GB whole-file sizes are not what moves. Worth
checking your other source assumptions against actual last-updated
dates; this one looked entirely current from the outside.

**2. Eastern Pacific only, not the whole basin.** Kristjan's call, and
rendering it both ways vindicated it. The western half sits across the
map's antimeridian seam, so drawing the full basin put a second
disconnected copy of the same event against Australia, with the cold
tongue at one edge and the warm pool at the other. One side reads as a
crop that continues past the edge. This is an intrigue generator on a
global map; the full basin belongs on the El Nino page, where it can be
Pacific-centred without the shared map paying for it.

**3. Not in the weekly pipeline.** `design/make_pacific_sst.py` is run by
hand and writes a committed asset plus a JSON. Promoting it to a fetcher
is the ENSO tracker's call on their surface, not something design should
smuggle into the pipeline. Two consequences: the caption states the
observation date, because a static picture of a moving field that does
not say how old it is goes quietly wrong, and the map renders fine when
the asset is absent, so a missing file cannot break a Monday.

## Four questions

### a. The halo, and whether it should become a stated rule

Your underlay proposal had a failure mode neither of us named. The
anomaly scale reaches near-black at both ends, so ink furniture on top
of it is unreadable exactly where the event is strongest. In the first
render the box outline vanished completely and both labels sat dark on
dark.

Fixed by giving all three a paper-coloured stroke behind the fill via
`paint-order: stroke`. The box is two rects rather than one, because a
single stroke cannot be legible against both a near-paper ocean and a
near-black anomaly: a paper hairline disappears over pale water, an ink
one disappears over the cold tongue.

Should "any furniture drawn over the anomaly scale carries a paper halo"
become a stated rule alongside D-016 amendment 4? It is the same
collision that amendment already names, met on a label rather than on a
mark, and it will recur on every chart that puts a value on top of a
field.

### b. The fade breaks decodability, and we are not sure that is acceptable

The band fades to transparent across the outer 28% of its height so it
sits in the ocean instead of looking like a rectangle pasted onto it.
That fade is what made Kristjan choose this version over the hard-edged
crop, and he is right that it reads better.

But a semi-transparent step composited over paper is no longer the
colour the legend prints. Near the top and bottom of the band a reader
cannot decode a value off the ramp. The colour itself is never altered,
only its alpha, so no value is moved into a neighbouring step, and the
faded margins are the weakest part of the field rather than its core.

Is that an acceptable trade for furniture at this scale, or does it
cross into misrepresenting the scale? We can also fade to the band edge
only where values are near zero, which would be honest but more complex.

### c. The legend now under-describes the data

**6.07% of cells in this crop exceed the +/-3.0 scale and clip into the
end steps**, with a maximum of +5.71 C off the South American coast. The
printed ramp currently implies nothing exceeds +/-3, which is false by a
wide margin, and the understatement is at the hot end where it matters
most.

The form is yours: an open-ended arrow at the ramp ends, a stated note,
or raising `OCEAN_SCALE`. Raising it has a cost we would rather you
weigh, since the same scale drives the ocean-heat bars on the issue
page and a wider scale flattens those.

### d. Two dates on one page

The issue is dated 2026-07-27. The SST observation is the seven days to
2026-07-26. Both are true, both are now visible on the front page, and
they will normally differ by a day or two.

Correctly precise, or confusing? We lean towards keeping both, on the
grounds that one date covering two different things is how a stale
number hides.

## Not asked, but worth flagging

The nine steps are visible as bands in the render. That is deliberate
and we think it is a feature: it does not look like every other NOAA
plot, which was Kristjan's original brief for the whole system. If you
disagree and want a smooth ramp, say so, because it changes the legend
from hard stops to labelled stops on a continuous scale, and the two
have to move together.
