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

**Outstanding check, not yet run** (tooling was unavailable at the time
of writing): whether temperature and rainfall have a NEWER published
dekad than cumulative vegetation. They are separate products on
separate cadences, and the whole cache was pulled in a batch rather
than per-instrument, so the cache date and the newest available date
are not the same question.

**This matters specifically for the divergence lead.** That page
compares a meteorology figure against a crop-outcome figure. If the two
instruments publish on different schedules, the comparison is
mixed-vintage, and neither the payload nor the page currently says so.
A divergence between two measures read at different dates is partly a
divergence in when they were read.

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
