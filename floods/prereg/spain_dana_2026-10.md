# Pre-registration: eastern Spain DANA, autumn 2026

Written and committed BEFORE any event-period station data was pulled, so
that the claim rule provably precedes the look (D-318 clause 3). The commit
time of this file is the evidence. Nothing below may be edited after the
event data is read; a change gets a new dated section explaining why.

## Instrument for the claim

AEMET OpenData daily climatological precipitation, `prec`, the day as AEMET
defines it. IMERG is tasking only: it chose the region, and no IMERG
millimetre value is quoted for this piece (D-318 clause 4: convective rain,
a day or less, at a point).

## Durations, fixed

- **1 day**
- **3 consecutive days**

No other window. In particular not "28 Sep to 2 Oct", which is bounded by
the storm's own dates (D-318 clause 3).

## Stations, fixed, and the rule that chose them

Rule: AEMET's principal station or stations in each province where the
storm was reported (Barcelona, Tarragona, Castellón, Valencia, Albacete),
resolved by name from AEMET's inventory, without reading any rainfall.
Where a province has two principal stations, both are listed.

| id | station | province | role |
|---|---|---|---|
| 0200E | Barcelona, Fabra | Barcelona | principal |
| 0076 | Barcelona Aeropuerto | Barcelona | principal |
| 0016A | Reus Aeropuerto | Tarragona | principal |
| 9981A | Tortosa (Roquetes) | Tarragona | principal |
| 8500A | Castelló - Almassora | Castellón | principal |
| 8414A | Valencia Aeropuerto | Valencia | principal |
| 8175 | Albacete Base Aérea | Albacete | principal |
| 8178D | Albacete | Albacete | nearest to Madrigueras, 24.9 km |
| 8300X | Carcaixent | Valencia | nearest to Alzira, 4.3 km |

The two "nearest" stations are body text only. A storm cell a few km wide
can miss a station 25 km away entirely, so they say what the station
recorded, never what the town received.

## What is reported

**Every station above, record or not.** A station that sets nothing is
reported as setting nothing. This is the protection against a list that
quietly shrinks to its winners.

For each station and each duration: the largest total in the storm,
ranked against every total of the same duration in that station's record,
**any time of year**. A "for the date" ranking, if used, is a separate
claim and never merged with it.

## The length of a record

"Since [year]" is the first year of an unbroken record for that station
(D-318 clause 1). A missing year either restarts the clock or is named in
the claim. Headline only at 30 unbroken years or more (clause 2); shorter
reads "highest in the station's N years", body text.

## Already seen, disclosed

Barcelona Fabra (0200E), 29 Sep 2026, 1 day: 79.8 mm. Read on 2026-10-04
while testing station history. Against September and October days only,
1920 to 2025, it ranks 10th of 5,918. Fabra's record has nine missing years
in that span (1923, 1928, 1929, 1960, 1962, 1991, 2006, 2015, 2024).
No other declared station's event-period value has been read.

## The comparison with October 2024

The volume ratio does not ship (D-318). If the 2024 DANA is used at all,
it is gauge data over one area and duration fixed here: the area receiving
more than 100 mm in 3 days, 2026 against 2024.

## 2026-10-12 addendum, written before the remaining event data is read

The sections above left three things undefined. They are fixed here, before
any event-period value other than the disclosed Fabra day has been read.
Nothing above is changed.

1. **The storm window.** A 1-day or 3-day total belongs to the storm if at
   least one of its days falls between 27 September and 5 October 2026.
   That is the reported storm (28 September to 4 October) plus a day each
   side. It bounds where to look, not the durations, which stay 1 and 3
   days.
2. **An unbroken year.** A calendar year counts if at least 90% of its
   days are reported (a trace, AEMET "Ip", counts as reported). "Since
   [year]" is the first year of the run of qualifying years that ends in
   2025. History before a break is named separately ("records from 1920,
   with gaps"), never folded in.
3. **Ranking.** Against every total of the same duration in the station's
   record, any time of year. A 3-day total needs all three days reported.
   Overlapping 3-day windows are declustered: a window counts only if no
   overlapping window is higher, so one storm is one entry. For each
   station and duration the output gives: the storm's total; its rank in
   the unbroken record and in the full record; and "the most since
   [year]", the last year with a higher total, or "a record" if none.

## 2026-10-12, later: the history was incomplete, and what changed

No rule above changed. The data under them did.

**The defect.** `fetch_aemet_history.py` cached every `SystemExit` from
`_aemet` as "archive empty". `_aemet` raises the same exception when AEMET's
data file never arrives, which its own docstring says is not an empty
result. So transient failures were stored as permanent gaps. Found because
CPO's check of Tortosa's "missing" January to June 1957 led to a live
re-request, and AEMET served all 181 days.

**The repair.** Only AEMET's explicit reply "No hay datos que satisfagan esos
criterios" is now cached as empty. All 1,027 cached-empty half-years were
re-requested live: 55 held real data and were filled; 972 were answered
"no data". The 11 of those that fall inside a station's operating span were
asked a second time and answered "no data" again.

**What the first judgement (42fae50c) said, and the final one says.**

| station | first | final |
|---|---|---|
| Tortosa (Roquetes) | unbroken since 1958; record in that run | unbroken since 1920; 3rd wettest day, most since 1943 |
| Barcelona Fabra | unbroken since 2007 (body text) | unbroken since 1978; wettest day and wettest 3 days in that run |
| Barcelona Aeropuerto | no unbroken run | unbroken since 2011; 2nd (body text) |

The stations with nothing remarkable are unchanged in verdict.

**Claim wording, and why it moved twice.** CPO first proposed "since 1943,
complete from 1940 except January to June 1957", which science cleared on
the condition that no January-to-June day came near 179.2 mm (it did not:
137.2 mm, January 2020). That gap no longer exists, so the condition is
moot and the claim needs no named gap: "Tortosa's wettest day since 1943, in
a complete record from 1920."

**Sensitivity, emitted per station in the payload.** Tortosa and Fabra give
the same start year and rank at every completeness threshold from 70% to
100%. Barcelona Aeropuerto does not (unbroken from 1940 at 85% or lower,
from 2011 at 90%), and is body text either way. In both headline runs every
September to November day is reported.
