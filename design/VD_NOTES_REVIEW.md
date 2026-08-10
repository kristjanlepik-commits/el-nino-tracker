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

---

# Unrelated, and parked here only because it would otherwise be lost

## The ENSO ladder reorder: science corrected their own evidence

2026-08-10. Science had told me probabilities were static, which was the
argument for leading with observations. **They withdrew it.** This week
moved harder than any since June, on a real August NMME init:

    issue        sup   >2.5   >3.0   >3.5   SST   CWWA
    2026-08-03    98     92     80     55   2.3      -
    2026-08-10   100     98     94     70   2.6    519

Mean absolute weekly move since 2026-06-15: super 0.62, >2.5 2.25,
>3.0 3.50, >3.5 5.60.

**The ladder is not static, it is saturating from the bottom up, and
volatility is now monotonic with height.** The observations-lead
argument survives on its own merits, but a layout that de-emphasises
the probability block as a unit would bury the most alive figure the
site publishes, currently 70 per cent for a peak beyond +3.5 C.

**Design against the field, never against which rung is live.**
Science emits `state` (settled / live) and `saturated`. Hard-coding
"the top rung is the live one" is true today and will stop being true
as saturation climbs, which is the expiring-exception shape that has
bitten this repo repeatedly. Render settled rungs as resolved and live
rungs as the reading, and the layout follows the data upward on its own.

Heat-content precondition is NOT met: +2.96 is still a single July
print, next release early September, so it stays a dated statement
rather than a standing component.

## And a publish-order defect on my surface

`/elnino/` served the previous issue for about twenty minutes after the
2026-08-10 publish, because the channel shell regenerates after
science's commit rather than with it. Kristjan found it by opening the
site. Nothing in the publish path noticed, which makes it the same
class as the front-page freshness guard (D-078) one surface along: the
channel front door can drift out of a publish.

---

# Crops country pages for pinned countries: two changes, both mine

2026-08-10. CRO has built the adapter (a page is generated when a
country has a record-low region OR is in PINNED, importing the list from
the index template rather than copying it) and is HOLDING the commit
until the template lands. Their reason is right: generated-but-unlinked
pages are the stale-page problem in advance rather than in arrears.

## 1. The lede assumes the wrong subject

Every pinned page currently opens:

    0 of 22 crop regions in France are at their worst on record for
    this point in the season. Its highest in any previous year was 0,
    on a recent average of 0.

Correct, and nonsense to read. **France's actual finding is that it is
falling faster than in any year on record, with five of six instruments
at or beside their record**, and the page opens by saying nothing is at
a record. A correct number rendered misleadingly, which is precisely the
gap D-030's sign-off exists to close, so CRO declined to sign it.

The template assumes a country page's subject is a count of record-low
regions. For a pinned country the subject is the country's own
condition and the count is the least interesting thing about it. When
the count is zero that sentence should not be the opening at all.

Requirement is CRO's; the wording is mine and editor's.

## 2. Every region gets a row

Region blocks render empty on all seven pinned pages, because the
template draws only rank-1 regions and these countries have none. This
is VD's ask from the crops index review, and **the data now supports it
channel-wide**: CRO restored per-region instrument layers on all 2,107
regions at `da84e00`, so every region can carry its five layers rather
than only the record lows.

## 3. England still has no page

England is pinned as a REGION and pages are per country. The UK page now
exists and foregrounds nothing. Either region pages become a type, or
the UK page leads with England and shows the other three as the
minor-crop regions they are. CRO's view, which I share, is that the UK
page foregrounding England is honest and cheap while a region page type
is the better long-term shape.

Remember why England is pinned at all: the UK country figure is an
unweighted mean over four regions and England is nearly all the
cropland, so the national number is dominated by three regions holding a
small minority of the crop.

## What is already good, so the rebuild does not lose it

The five country instrument layers render with real values (France:
cumulative vegetation +0.19 at 18th of 26, current vegetation -1.50 at
lowest of 26, water satisfaction 46% at lowest of 26) and the severity
block is present. The substance is there. It is sitting under a lede
that contradicts it.
