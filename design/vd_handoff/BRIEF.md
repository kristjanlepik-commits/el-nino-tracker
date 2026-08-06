# The Long Swell: visual design brief

For Claude Design. Everything needed to work on this is in this folder or
at a public URL; you are not expected to have repo access.

---

## 1. What The Long Swell is

A climate measurement site. We take instrument data (satellite fire
detections, crop stress indicators, station temperature records, ocean
temperature) and report, weekly, how unusual the current reading is
against that place's own history.

The editorial position matters for design because it constrains almost
every visual choice: **we aggregate and cite, we never author a figure,
and we report calm weeks as plainly as extreme ones.** The product's
credibility rests on a reader being able to check us. That is the thing
the design has to communicate before it communicates anything else.

## 2. Look at it live

The whole current surface is seven public URLs:

| Page | URL |
|---|---|
| Front page | https://thelongswell.com/ |
| Fires channel | https://thelongswell.com/fires/ |
| Crops channel | https://thelongswell.com/crops/ |
| El Nino tracker | https://thelongswell.com/elnino/ |
| Weekly issue archive | https://thelongswell.com/briefs/ |
| About | https://thelongswell.com/about.html |
| Methodology | https://thelongswell.com/methodology.html |

Live now: Fires, Crops, El Nino, About.
Landing in the next few weeks: Heat, Notes, Floods, Econ.

So the channel count roughly doubles. That growth is the reason this
brief exists.

## 3. What is in this folder

```
BRIEF.md              this file
tokens.py             THE SOURCE OF TRUTH for the design system
assets/mark.svg       the TLS mark
assets/favicon.svg
assets/avatar-1024.png
assets/world-map.svg  the basemap both channel maps draw on
payloads/             real data, see the warning below
```

### tokens.py

Not a description of the design system, it *is* the design system. Every
page and every chart reads from it at build time. It carries:

- the paper and ink ramp, light and dark
- the five channel colours
- the anomaly colour scale (a nine-step diverging ramp)
- the attribution-chip colours
- type families and letter-spacing constants
- matplotlib trace styles, so charts and pages cannot drift apart

If you propose a change, this is the file it lands in. It is plain Python
and readable top to bottom without running it.

### payloads/

Real output, not mockup data. **Please design against these rather than
against invented examples.** Every genuine defect this site has shipped
came from real data doing something a clean mockup never does: ties,
nulls, a seven-day window that quietly became five days, a country whose
headline read "second-heaviest fire week since 2012" while the note
underneath it said "not unusual today". A layout that has only ever met
tidy data will break on contact.

Specific things in these files worth designing for:

- `fire_events.json` has 22 countries in four different evidence
  classes, of which 8 are explicitly **not** anomalous and still have to
  appear.
- `attribution` is `null` on most rows. That is deliberate, not missing
  data. Untagged means untagged.
- `degraded` records when the window was short. It must be visible to a
  reader, not just logged.
- `heat_city_nights.json` has 15 cities, 8 of them at rank 1 of 78 to 105
  years.

## 4. Fonts

- **Spectral** for prose, SIL OFL 1.1
- **IBM Plex Mono** for data, figures and labels, SIL OFL 1.1
- Inter is vendored but barely used

Both are open licence and freely installable, so they are referenced
rather than copied here. The mono is doing real work: every figure on the
site is set in it with tabular numerals, so numbers line up in columns
and a reader can compare down a list.

## 5. Constraints a screenshot will not show you

These are ratified decisions, not preferences. Several cut directly
against normal dashboard instinct, so they are the most likely thing to
get violated by a redesign that looks better in isolation.

**Calibration, not amplification (D-043).** "Within its historical range"
must read as legibly as "extreme". We are not allowed to make the calm
case visually recessive. This is the single hardest constraint on any
"how bad is it?" visual, because every convention available (red, size,
weight, position) is built to do the opposite. A reader who only notices
our page when it is shouting cannot trust it when it shouts.

**Three attribution strings, no fourth (D-033).** Exactly: "ENSO-loaded
window", "Not ENSO-linked", "Attribution pending". Untagged items get no
chip at all rather than a fourth state meaning "we have not looked".

**No interruption patterns, anywhere, ever.** No modal, no exit-intent,
no scroll trigger, no sticky bar, no sidebar. This was scored as a trust
negative rather than treated as taste: an interruption on a site whose
pitch is that we do not hype spends the credibility everything else
accumulates.

**No social proof.** No testimonials, no subscriber counts, no logos. We
do not have the numbers, and a site whose pitch is measurement must not
lead with an unmeasured claim about itself.

**Dark mode is not optional.** Every page ships light and dark, via
`prefers-color-scheme` plus an explicit `data-theme` override.

**Contrast is already tuned and was hard-won.** `INK_FAINT` sits at
4.50:1. The pending-tag foreground was amended twice for contrast
failures. Any palette revision has to re-clear WCAG AA, and the comments
in `tokens.py` record what previously failed.

**No em-dashes.** House style, enforced by a build guard.

## 6. The three questions

### Q1. The map, and what happens to it at seven channels

The fire map encodes the multiple as marker area, with an open ring for
any marker that is not anomalous. The crops map is a separate map on a
different grammar: 6 lit, 117 faint, denominator visible.

That is already two maps speaking two visual languages, and Heat, Floods
and Econ each arrive with a third, fourth and fifth idea of what "bad"
means. Heat's unit is a rank against a station record. Econ's is money.
Crops is a stress index. They are not commensurable and averaging them
would be exactly the kind of authored figure we refuse to produce.

The question is not "how do we add more pins". It is: **can one map carry
five incommensurable severity scales at all, or is the honest answer one
map per channel on a shared grammar?** And within that, what encodes "how
bad is it?" for a reader who does not know what a z-score is, while still
satisfying D-043.

### Q2. The top of the page

Currently a title text block. The proposal is two containers instead: one
linking to the hottest section, one surfacing content from Notes. Or
possibly a single rolling container.

The constraint is that it must not get messy, and it must not become a
carousel that hides content behind interaction.

### Q3. The one that matters most: we look generic

Kristjan's read, and it is the reason for this brief: our pages look like
a standard AI-generated template. He has a screenshot of an unrelated
blogpost whose chart is near-identical to our fires cumulative chart.

**The ask is a custom visual identity that feels human and less
technical.** Closer to a CVI than a tweak: something nobody could mistake
for a default.

The tension to solve, and it is a real one rather than a brief-writing
flourish: the qualities that make us trustworthy (restraint, tabular
figures, a bone-paper editorial palette, no decoration) are the same
qualities that make us look like a template. Restraint and genericness
are neighbours. We need the first without the second, and we cannot buy
distinctiveness with the things we have ruled out, which is most of the
usual vocabulary: no illustration that implies causation, no photography
we have not licensed, no drama in the colour, no motion that editorialises.

Visual language v1.0, "Bulletin", was ratified 2026-07-26. This is an
invitation to revisit it, not to start from nothing.

## 7. Concrete open decision, needed soonest

`tokens.py` defines five channel colours: `nino`, `fire`, `flood`,
`crop`, `damage`. **Heat and Notes have none.** A heat page is built and
currently blocked on this; I declined to invent a sixth colour rather
than pick one outside the system.

With four more channels landing, the real question is not "pick two more
hues". It is whether a seven-channel palette holds together at all, or
whether channel identity should stop being carried by hue and move to
something that scales: a mark, a rule treatment, typography.

That decision unblocks shipping, so it is the one to answer first if you
answer only one.
