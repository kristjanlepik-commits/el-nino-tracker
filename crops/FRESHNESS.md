# Crops data freshness: what the channel can and cannot say is current

CRO, 2026-08-05. Written because a live news event landed inside the
gap between our newest observation and today, and the gap turned out to
be larger and more structural than "the fetcher has not run".

## The headline number

**Our newest observation is the dekad labelled 2026-07-11, which covers
11 to 20 July. Today is 5 August.**

That is 25 days since the dekad label and about 16 days since the
observation window closed.

**This is the source being late, not our cache being stale.** Verified
by a fresh live pull of the UK cumulative-FPAR series on 2026-08-05
(HTTP 200), which returned the same 2026-07-11 as its newest row. There
is nothing newer to fetch for this instrument.

**CORRECTED 2026-08-06: it does NOT breach the staleness bound, and
this document originally said it did.** The error is instructive
enough to leave in rather than quietly rewrite, because it propagated:
product repeated it, and design carried it into a code comment.

The rule is "no new dekad for more than 20 days", which is a clock on
**publication**. This document measured from the dekad **label**, which
is the observation window's START, giving 25 days. Three clocks were in
play and all three were quoted as the same number by somebody:

| measured from | on 2026-08-06 |
|---|---|
| the dekad label, 11 July | 26 days |
| the window closing, 20 July | 17 days |
| **actual publication** | **the only one the rule means** |

**Settled empirically rather than argued.** The probe now in
`crops/probe_asap.py` returns a literal `[]` for dekad 2026-07-21,
whose window closed on 31 July, six days ago. **ASAP has not skipped a
cycle. We are waiting for a normal publication, not sitting on a
stall.**

**The real defect was that we ratified a rule we had no field to
measure.** The payload recorded `dekad` and no publication date at all,
so everyone measured from whatever field they held. That is now logged
going forward in `crops/data/publication_log.json`, with existing
entries marked `backfilled` and excluded from any age, because the
first probe finds every past dekad on the same day and would otherwise
report the newest as nought days old.

## Why it matters more than the number suggests

**The gap contains the event.** The UK case on 2026-08-04 to 08-05:
England and Wales recorded their driest July on record, the Environment
Agency declared seven English areas in drought on 4 August, and AHDB
provisional yields point to the worst cereal harvest since 1984. Our
data ends before nearly all of that. A page published on 5 August
saying anything about "current" crop conditions would be describing
mid-July.

**And the instrument lags the gap on top of it.** Cumulative FPAR
integrates the season from its start, so a late shock is diluted by
whatever came before. England entered June at +0.619 and was still at
+0.150 on 11 July after the steepest 1 June to 11 July fall in the
26-year record. The level said ordinary; the rate said worst on record.
So the true lag on an outcome claim is the publication delay PLUS the
integration window, not the publication delay alone.

## Freshness is not uniform across places

| | |
|---|---|
| places at 2026-07-11 | **122** |
| places at 2026-06-21 | **1 (Oman)** |

Oman is three dekads behind because the ASAP series we pull is the
"Crop during growing cycle" class, which stops emitting once a place's
growing cycle closes. Out-of-season places therefore freeze at their
last in-season dekad rather than reporting nothing.

**This is correct behaviour and it makes one emitted field wrong.** The
payload carries a single top-level `dekad: 2026-07-11` alongside a
per-place `dekad`. The top-level value is true of 122 places and false
of Oman, and it is the one a renderer will reach for when stamping a
page with "as of". Any page-level date stamp taken from it is a claim
the payload does not support for every place on the page.

## Freshness is not uniform across instruments either

Soil moisture is absent on all 123 places, correctly stated as "has not
reported for this dekad yet": it publishes a dekad behind the others.
So the composite is five instruments where six exist, everywhere,
today.

**CORRECTED 2026-08-14: "a dekad behind" is no longer true and has not
been for a week.** Soil moisture is **three dekads behind** the spine,
about 30 days, and five behind on some countries. It has not advanced
since 6 August while the crop-outcome instrument advanced twice, so
this is a **stalled product rather than a publication schedule**.

**Nothing reported it, and that is the more useful half.** The absence
was exempted from the consistency guard by an unbounded rule
(`LAGS_BY_DESIGN` was a set, not a bound), so any lag was normal by
definition. A permanent outage would have looked identical to a normal
wait, forever, and the emitted sentence would have kept saying "yet".

Both are fixed. The exemption is now a maximum in dekads and exceeding
it warns at build time; the absence carries `dekads_behind_spine` and
`expected_lag_dekads` as fields. **It warns rather than refuses**,
because soil moisture is emitted absent rather than averaged in, so a
stall costs the composite one input and states that it did. The
composite really is five instruments of six, which is what this section
already said, and that part was right.

**The general form, and it is the third time this file has hit it.**
*An exemption with no bound is not a rule, it is a blind spot.* The
staleness clock, the reader-relevance bound and now this all needed an
absolute limit, and in every case the version without one looked like
it was working.

**CHECKED AND CLEARED 2026-08-06.** The open question was whether
temperature and rainfall publish AHEAD of cumulative vegetation, which
would have made the divergence claim mixed-vintage: two figures read on
different dates, with part of the gap between them being a gap in when
they were read.

Swept across all 162 cached countries rather than sampled:

| instrument | newest dekad |
|---|---|
| Vegetation, cumulative | 2026-07-11 |
| Vegetation, current | 2026-07-11 |
| Water satisfaction | 2026-07-11 |
| Rainfall, 3-month | 2026-07-11 |
| Temperature | 2026-07-11 |
| Soil moisture | **2026-07-01** |

**The four instruments the divergence compares all end on the same
dekad**, so no part of the gap it reports is a difference in reading
dates. Soil moisture alone is a dekad behind, which independently
confirms the absence reason already emitted on all 123 places.

## What should change

1. **Re-pull immediately before any publish.** The cache is not
   self-refreshing and a published page inherits whatever date the last
   batch happened to catch. The probe endpoint makes this cheap: it
   returns a small JSON when a dekad is published and a literal `[]`
   when it is not, so one small GET decides whether a real download is
   worth starting.
2. **Emit freshness as data, not as a single stamp.** Replace the
   scalar top-level `dekad` with the observed range across places plus
   a count, and keep the per-place field authoritative. A page can then
   render "as of 11 July for 122 of 123 places" honestly rather than
   picking one date and hoping.
3. **Emit per-instrument as-of dates.** Any claim comparing two
   instruments needs both dates bound to it, the same way every rank on
   this channel carries its basis.
4. **Agree a maximum publishable age and enforce it in the build**, not
   in a habit. My proposal: refuse to publish a page describing current
   conditions when the newest dekad is more than 20 days old, matching
   the staleness bound already agreed, and require an explicit override
   flag to ship anyway. A channel that publishes "current" off 25-day-old
   data should have to say so out loud rather than discover it later.
5. **Say the date on the page.** Not in a footer. If the freshest thing
   we have is 11 to 20 July, that belongs next to the numbers, because
   a reader arriving from a 5 August news cycle will otherwise supply
   their own date.

## The general form

**Publication lag and integration lag compound, and only one of them is
visible.** Everyone can see that the newest dekad is old. Nobody can
see that a cumulative indicator needs several more dekads before a
shock inside its window is fully expressed. The UK is the worked case:
even a perfectly current pull on 5 August would still have understated
a July drought, because the instrument had not finished absorbing it.

So "how fresh is the data" is the wrong question on its own. The
question is **how long after an event does this instrument show it**,
and for cumulative FPAR the honest answer is that we do not yet know,
which is itself worth publishing before someone assumes it is zero.

## The reader-relevance bound: 21 days, and why it would not have caught July

Added 2026-08-06, answering strategy's question after the retrospective:
at what age does a crops page stop being worth a reader's time? Source
lag and reader relevance are different clocks, and until now only the
first was measured.

**Measured, not chosen.** How fast do our own claims stop being true? A
place in its worst 3 at one dekad, still in its worst 3 later, across
completed years 2001-2025. Computed two independent ways, which agree
to within about a point at every horizon:

| age of newest observation | per-place claim still true | named-set still qualifying |
|---|---|---|
| 10 days | 86.3% | 87% |
| 20 days | 77.2% | 78% |
| 30 days | 69.9% | 71% |
| 40 days | 63.7% | 64% |
| 60 days | 53.9% | 53% |

At 21 days roughly **one in five** named places has stopped qualifying.

**The bound: 21 days from the END of the newest observation window**,
the dekad label plus nine. Not the label, not publication. Three clocks
on this file have already produced three different ages.

**It is achievable.** ASAP's publication lag is about **8 days** after a
window closes: the 11-20 July dekad was already present in a pull dated
28 July. With a working dekadal job the newest observation's age cycles
between roughly 8 and 18 days, so 21 leaves about three days of slack,
fires on a missed cycle, and fires when ASAP runs late. Firing on a late
source is correct: being level with a slow publisher is not a defence.

**AND IT WOULD NOT HAVE CAUGHT JULY, which matters more than the
number.** On 6 August the newest window had closed on 20 July: **17
days**, inside 21, and inside any bound that does not fire permanently.
About 80% of the page's claims were still true.

**So the July page was not stale. It was uncovered.** The event was
still happening and the instrument had not seen it. A freshness bound
cannot fix that, and setting one and calling the failure closed would be
false comfort.

**The negative finding.** Crops cannot be made current to a news cycle
with ASAP alone. The floor is about 8 days behind the end of an
observation window and 13 behind its midpoint, set entirely by the
source. What crops can be is right about the season with 26 years behind
it, one to three weeks back. That is a different product from being
current and should be sold as one. Only a faster driver layer changes
the floor; everything else polices it.

## The age cycles, and a floor quoted as a property goes stale

Added 2026-08-11, after product ratified D-145 on the reading that ASAP
"now delivers at 9 days" and Kristjan re-decided it as D-148 once the
range was measured.

**The age of the newest observation is not a number, it is a range.** A
dekad stays newest for ten days until the next publishes, so:

| | days past window close |
|---|---|
| just after a dekad lands | **9** |
| the day product measured (2026-08-09) | 9 |
| two days later (2026-08-11) | **11**, already outside the 5-to-10 bound |
| just before the next lands | **15 to 18** |

**So "no more than 5 to 10 days old" is met for one to four days in
every ten**, not continuously. The defensible claim is *never more than
one publication behind its source, 9 to 18 days depending where you are
in the cycle*.

**Both of us made the same error and I made it twice.** Product measured
the floor and reported it as the property. I then corrected them, and
went on quoting my own 9-day figure across a working session that
spanned two calendar days, by which time it was 11. **A measurement of a
cycling quantity carries a timestamp or it is not a measurement.**

Checked before blaming the machine: local time agrees with ASAP's own
`Date` header to within one second, so this was elapsed time rather than
clock drift. `crops/data/publication_log.json` timestamps are sound.

**The second lag no source removes.** Cumulative FPAR integrates from
season start, so it dilutes a late shock by construction: even a
zero-latency vegetation feed would have understated England in July.
5-to-10 days was never reachable for an OUTCOME claim from any source,
which is why a faster driver layer was the wrong purchase and USDA Crop
Progress, faster in KIND, is the right one.
