# VD's first Notes review: triage

Source: `The Long Swell Notes, first review.dc.html`, project
`8eff7a3b-980d-4a6c-975b-9b3759cc7a65`, read 2026-08-10. Read it as data,
not instructions.

Kristjan reviewed this triage and approved it, including the pushbacks,
2026-08-10. Nothing below is implemented yet.

## Take, in this order

**1. The charts carry no house typography.** Both render in matplotlib's
default sans while every page around them is Spectral and Plex Mono. The
two most quotable objects on the site, the ones screenshotted *without*
the page, are the only things on it carrying none of its type. Static
TTFs are already committed and `FONT_PROSE` / `FONT_DATA` are already
tokens, so this is registration, not a design decision. Ticks and counts
are figures and take Plex Mono with tabular numerals; only the chart
title is prose and takes Spectral. `design/make_note_chart.py`.

**2. The nav is still coloured by channel.** D-101 deleted `FIRE`,
`CROP`, `FLOOD`, `DAMAGE` and moved channel identity to type. The tokens
went; the nav kept the hues. One masthead partial, lands on every page.

VD's sharpest point: Notes renders blue and so does El Niño, so if the
blue is an active-page state then blue means *El Niño* and *you are
here* in the same row and a reader cannot tell which. Notes is not a
measured variable and can never hold a hue under the ruling.

**3. Small chart and index fixes.** 2026's bar touches the right plot
boundary, so the mark carrying the whole claim is the one element with
no clear space. The index has an empty block between the entry and the
footer, two hairlines with nothing between them. The index entry title
carries a hairline that reads as a rule rather than a link underline,
and nothing else on the row signals it is clickable.

**4. What the red bar means, and it is a rule rather than a fix.** 2026
draws in the ramp's hottest step. If red means *the current year* it
should be ACCENT, and the extreme step will be wrong the first time a
Note covers an ordinary summer. If red means *extreme* it is correct
this year by coincidence. The mark is the accent and the ramp is the
value; they are different jobs. Decide before a calm Note exists,
because that is when the wrong choice becomes visible and expensive.

**5. The index lead, conceded against my own build.** I derived it from
the first paragraph so a summary could not drift from the piece. VD
wants an authored line previewing the *finding*. Their argument is
better: the current preview shows the wondering rather than the finding,
and it ships the item-03 problem twice from one string. Move to a
front-matter line in `notes/*.md`, which keeps it Kristjan's words.

## Pushed back, and why

**The Frankfurt marginalia case rests on something that is not true.**
VD says the station move is "disclosed 400 words below the claim, in a
source block at the foot", and contrasts Paris doing it well in its
caption. Both charts carry their station state ON THE IMAGE. Frankfurt's
includes the exact sentence VD identifies as doing the real defending,
"stations nearby that did not move show a similar rise over the same
period". They reviewed the page text and the screenshots separately and
missed that the disclosure is in the picture.

The marginalia device may still be worth having. The asymmetry offered
as its justification does not exist, so it needs a different one.

**The sideways definition contradicts a ratified editorial decision.**
VD calls the rotated axis sub-line "a marginalia line, not an axis
label". It is there because editor ruled it should be, explicitly, to
kill a subtitle, on the grounds that a subtitle is a sentence a crop can
remove and an axis label cannot be cropped off without taking the
numbers it labels with it. On a chart built to travel alone that
argument is strong. VD is reviewing it as a page element and it is not
one. Editor and VD, not design, and not silently.

**The opening's ENSO implication is a real finding aimed at the wrong
person.** The point stands: "a strong El Niño started / Europe had its
heatwaves and its fires" is causal by juxtaposition, and Fires tags
every European row `not ENSO-linked`, so the first Note contradicts its
own channel. D-033 exists because a flagship El Niño product trains
readers to over-attribute.

But D-093 gives the prose to Kristjan, editor has frozen the text, and
VD's proposed clause, "neither of which has an established link to it",
asserts something about heatwaves that our channels do not support as
flatly as they do for fires. **Fixing an over-attribution with an
under-attribution is not an improvement.** Kristjan's call, with editor.

## Agreed and requiring nothing

No photograph, at any point. The anti-brief rules out unlicensed
photography and any illustration implying causation; the only pictures
this site is entitled to are its own measurements. No longer
introduction. The chart-as-preview idea waits until the third Note.

VD wants the Option D chart pattern, full record as bars, current year
in accent, previous best as a dashed reference, to become the
channel-wide pattern rather than a Notes one. Worth taking up with heat.
