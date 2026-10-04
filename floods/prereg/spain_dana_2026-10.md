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
