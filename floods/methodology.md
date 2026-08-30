# How the floods channel measures

This page describes what this channel measures, what it refuses to
measure, and how to check it. It is written for a reader who has found
one of our flood pages and wants to know whether to believe it.

**A note on how this page is built.** It contains no counts. Every number
a reader sees on a floods page is read from the payload that page is
rendered from, and this document deliberately avoids restating any of
them. Prose that carries a count goes stale silently, and a stale count
does not read as out of date. It reads as overclaiming.

---

## Two instruments, never merged

We use two, and they answer different questions.

**Rainfall** comes from NASA's GPM IMERG, which combines satellite
microwave and infrared observations into a gridded daily total. It
measures water falling out of the sky.

**Flood extent** comes from NASA's MODIS MCDWD, which detects standing
water outside a river's normal channel. It measures water sitting on the
ground.

Outside major events these two correlate weakly. That is not a fault in
either: flooding depends on how wet the soil already was and on what the
river upstream was doing, neither of which is local weekly rain. **So we
never combine them into a single index**, because the combined number
would be a claim neither instrument makes. Where both are available they
appear side by side and are allowed to disagree.

A third instrument, Copernicus GloFAS river discharge, is used only to
corroborate whether a river actually rose. It is a hydrological model
rather than an observation and is always labelled as modelled.

---

## Every number is a place against its own history

We never compare one region to another. A flood page says how this
catchment's rainfall or flood extent compares with **the same calendar
window in every prior year at the same place**.

That is deliberate. Cross-region comparison would require a common
denominator we do not have, and the instruments' own coverage varies
enough by geography that a league table would rank the sensor rather than
the weather.

The window is fixed before the answer is known: a set number of days
ending at the most recent day the instrument actually holds. Neither the
length nor the end date is chosen after seeing the result.

---

## Observability, and why it is not a flood measure

Optical satellites cannot see through cloud. So every flood-extent
reading carries a second number, **observability**: the fraction of the
region the satellite could actually see.

**Observability is not flooding.** A value of 0.73 means roughly
three-quarters of the region was visible. It does not mean three-quarters
was underwater. It is a statement about the instrument, not about the
ground.

We publish it because it makes blindness measurable. A week with almost
no visibility is a placeholder, not a measurement, and without this
number the two would look identical.

---

## A region can fail, and failing is a result

Before a region gets a flood-extent ranking, its own history has to show
the instrument can see it. Two tests decide:

**Does the measure track the weather instead of the flood?** We correlate
each year's flood reading against how much the satellite could see that
year. Where the two move together, a ranking would be ranking clear skies.

**Is there enough water to measure?** Below a floor derived from where
two versions of the same product stop agreeing with each other, the
reading is noise.

Regions that fail return **cannot say**, with the reason attached. This
is a published result, not a suppressed row.

The clearest case is Manila. Across two decades its flood reading tracks
its visibility almost exactly, and the year of its worst recorded
flooding reads *zero flood pixels* because the cloud that caused the
flood blinded the sensor. A naive ranking would have called that year
unremarkable. **Optical flood detection fails hardest exactly where the
most damaging floods happen**, which is a limit of the method and not a
gap in our effort.

---

## What these instruments systematically miss

Every instrument here averages, over time or over area, and **averaging
pulls both tails toward the middle. It inflates the quiet tail and
flattens the loud one. We only ever publish the loud one.**

Concretely, measured against a dense national gauge network on an extreme
convective event: our rainfall instrument over-reads where little rain
fell and under-reads severely where a great deal fell, on the same field
on the same day. **No correction factor can fix that**, because the bias
runs in opposite directions at the two ends.

The practical consequence is the sentence that matters most on any of our
pages: **rain that falls in a few violent hours can flood without moving
a fortnight's total, so an ordinary total is not evidence that nothing
happened.**

Where a period's rain is concentrated into very few days, our pages say
so and mark the intensity as not measured. Where it is spread out, they
say the instrument fits the event. That judgement is computed from the
data, not asserted.

---

## Whether it flooded is a separate question, and often we do not know

Our instruments measure rainfall and standing water. **Neither
establishes that a flood occurred, and neither counts people, houses or
roads.**

So every page carries a separate field recording whether a flood is known
to have happened, what the source was, and what it said. It has three
states: yes, no, and **unknown**. Unknown appears on the page rather than
being left off it.

This exists because for a long time nothing in this channel asserted a
flood except the channel's own name. A page about rainfall, on a site
section called Floods, at a URL containing the word, was making a claim
no measurement supported. Naming that field was the fix.

---

## Why so few regions

We publish catchments, not countries. A river basin is the unit the
instruments can honestly resolve; a national boundary is not, and
averaging a flood across a country dilutes it toward that country's
normal.

This means the channel covers fewer places than our others, and that is a
methodological choice rather than an unfinished job. A region appears
here only once we have measured that the instrument can see it and built
a multi-decade baseline for the specific weeks in question.

**Box geometry is the single largest lever on the answer.** The same
event can read as unremarkable over a wide rectangle and as extreme over
the catchment that actually flooded. Where we can, we now rank every
model cell in a region against its own history rather than drawing a box
at all, because a box drawn after seeing the data can be aimed at the
answer and a per-cell ranking cannot.

---

## How to check us

Every page states the window, the number of prior years compared, and any
day excluded from the comparison along with the reason. Days absent from
the current period are excluded from **every** year, so the comparison
stays like for like.

Where a ranking is not safe to state, we say so rather than rounding to a
confident sentence. Two separate conditions can withhold a claim: values
too close together to separate, and a baseline so small that a multiple
against it would measure noise. They are different problems and they
withhold different things, so a page may give a rank without a multiple.

Every figure on a floods page comes from a machine-readable payload
committed alongside it. Source datasets are named on each page, and where
we cross between two versions of a product we measure the crossing first
and publish the result.

---

## Version history

Newest first. A **change** alters what this channel would publish from the
same data. A **fix** corrects something that was already wrong. The
distinction matters: a reader comparing two of our pages needs to know
whether the method moved or whether one of them was mistaken.

### 1.4, 30 August 2026

**Changes**

- **River discharge added as a third instrument.** Copernicus GloFAS,
  modelled rather than observed, used only to corroborate whether a river
  actually rose. Its two products are disjoint in time, so the crossing
  between them was measured before use and agreed to within a thousandth.
- **Per-cell ranking replaces drawing a box.** Every model cell in a
  region is ranked against its own record. A box drawn after seeing the
  data can be aimed at the answer; a per-cell ranking cannot. Affects
  where we look, not how we measure.
- **Whether a flood occurred is now a required field.** Three states,
  including *unknown*, which appears on the page rather than being left
  off it. Before this, nothing in a payload asserted a flood except the
  channel's own name.

**Fixes**

- **Two guards were sharing one permission.** A near-zero baseline makes a
  *multiple* meaningless; a near neighbour makes an *ordinal* meaningless.
  The first was suppressing the second, so a region with a perfectly
  separable rank lost it. Rankings withheld under 1.3 may be publishable.
- **The tie test used the wrong denominator.** It measured separation as a
  fraction of the baseline median rather than of the value, so on a dry
  baseline two effectively identical years never registered as tied.
- **A window was chosen from when data arrived rather than from when the
  event happened**, and landed on the falling limb of a flood. One piece
  was withdrawn and rebuilt. No published page was affected.

### 1.3, 21 August 2026

**Changes**

- **Rainfall gained a floor.** Below a small absolute baseline a multiple
  amplifies noise, so the figure is withheld. Flood extent has had an
  equivalent since the channel opened.
- **Event character is emitted with every rainfall finding.** Where a
  period's rain is concentrated into very few days, the page says the
  intensity was not measured.

**Fixes**

- **A source gap deleted the current period instead of the missing day.**
  Days absent from the current period are now excluded from every year, so
  the comparison stays like for like.
- **A missing file was being reported as an empty measurement.** Absence
  of data and absence of a file are different claims and no longer share a
  return value.

### 1.2, 18 August 2026

**Changes**

- **The rainfall instrument was calibrated against gauges** on an extreme
  convective event. It over-reads light rain and under-reads heavy rain on
  the same field on the same day, so no correction factor exists. Pages
  now say when an ordinary total is not evidence that nothing happened.
- **Regions are screened before they are baselined.** Of twenty
  candidates, five can carry a flood-extent ranking. Europe passed none.

### 1.1, 10 August 2026

**Changes**

- **Region qualification became a publish gate.** A region only gets a
  flood-extent verdict if its own history shows the instrument can see it;
  failing returns *cannot say* with the reason attached.
- **Absence became machine-readable.** Distinct states for not assessed,
  awaiting data, and no baseline, so a missing instrument can no longer be
  invisible.

### 1.0, 3 August 2026

The channel opens on two instruments that are never merged, each region
compared only against its own history at the same calendar window.
