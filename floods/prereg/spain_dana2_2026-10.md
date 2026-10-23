# Pre-registration: second Mediterranean DANA, 17 to 20 October 2026

Written and committed on 15 October 2026, BEFORE the storm. AEMET's
"Nota informativa. Precipitaciones intensas en Baleares y área
mediterránea" (15 Oct, 13:54) forecasts it for Saturday 17 to Tuesday 20
October, worst Sunday 18 to Monday 19, with 150 to 250 mm "en pocas horas"
possible in some areas. The commit time of this file is the evidence that
the stations and durations below precede the rain (D-318 clause 3). Nothing
below may be edited after event data is read; a change gets a new dated
section explaining why, as in floods/prereg/spain_dana_2026-10.md.

## Instrument for the claim

AEMET OpenData daily climatological precipitation, `prec`, the day as AEMET
defines it. No satellite millimetre value is quoted (D-318 clause 4, D-322).

## Durations, fixed

- **1 day**
- **3 consecutive days**

Same as the first storm, so the two can be compared like for like. AEMET's
"in a few hours" is sub-daily; the daily archive cannot rank it and this
piece will not try.

## The storm window

A total belongs to the storm if at least one of its days falls between
**16 and 21 October 2026**: AEMET's forecast days plus one each side. It
bounds where to look, not the durations.

## Stations, fixed, and the rule that chose them

Rule: every province containing an area AEMET's note names (eastern and
southern Catalonia; the coast north of Cabo de La Nao; the Alicante and
Murcia coasts; the Costa del Sol; the Pitiusas and the rest of the
Balearics). In each, the airport station and the provincial capital's city
station, resolved by NAME from AEMET's inventory on 15 Oct without reading
any rainfall. Where the first storm's pre-registration already fixed a
province's stations, they are kept. Castellón is included because "north of
Cabo de La Nao" can be read to reach it; including more stations is safe
because every one is reported.

| id | station | province |
|---|---|---|
| 0367 | Girona Aeropuerto | Girona |
| 0370B | Girona, Antic Institut | Girona |
| 0200E | Barcelona, Fabra | Barcelona |
| 0076 | Barcelona Aeropuerto | Barcelona |
| 0016A | Reus Aeropuerto | Tarragona |
| 9981A | Tortosa (Roquetes) | Tarragona |
| 8500A | Castelló - Almassora | Castellón |
| 8414A | Valencia Aeropuerto | Valencia |
| 8416 | València | Valencia |
| 8019 | Alicante-Elche Aeropuerto | Alicante |
| 8025 | Alacant/Alicante | Alicante |
| 7031 | San Javier Aeropuerto | Murcia |
| 7228 | Alcantarilla, Base Aérea | Murcia |
| 7178I | Murcia | Murcia |
| 6155A | Málaga Aeropuerto | Málaga |
| 6156X | Málaga, Centro Meteorológico | Málaga |
| B954 | Ibiza, Aeropuerto | Balearics (Pitiusas) |
| B957 | Eivissa | Balearics (Pitiusas) |
| B278 | Palma de Mallorca, Aeropuerto | Balearics |
| B228 | Palma, Puerto | Balearics |
| B893 | Menorca, Aeropuerto | Balearics |

Not included: 7020C Murcia Aeropuerto (Corvera, opened 2019, cannot reach
the 30-year headline floor) and 7031X (a second identifier for San Javier).

## What is reported

**Every station above, record or not**, including any the storm misses.
AEMET's own note says the low's position is highly uncertain, so many of
these stations may record little; they are reported anyway.

## Rules carried over unchanged from the first storm

From floods/prereg/spain_dana_2026-10.md and its 12 October addendum:
- An unbroken year has at least 90% of its days reported (a trace counts).
  "Since [year]" is the first year of the run of such years ending in 2025.
  Completeness sensitivity from 70% to 100% is emitted per station.
- Ranked against every total of the same duration, any time of year, in the
  record through 2025. 3-day totals need all three days; overlapping windows
  are declustered.
- Headline only at 30 unbroken years or more (D-318 clause 2).
- Gauges not listed here may confirm or qualify a reading and are never
  claimed.

One addition, because 2026 already has a storm in the record: if the first
storm (27 Sep to 5 Oct 2026) was higher at the same station and duration,
that is stated beside the result.

## Already seen, disclosed

Nothing from 16 October onward has been read for any station. The first
storm's values at the six stations shared with its pre-registration
(0200E, 0076, 0016A, 9981A, 8500A, 8414A) are known and published in
floods/data/spain_dana_2026-10_stations.json.

## 2026-10-15 addendum, before the rain: "twice in three weeks", and the test count

Added on CPO's point that "twice" is a frequency claim and needs its
definition fixed before the storm. No station history has been ranked or
counted for this definition yet.

**A qualifying storm** is a day on which at least one of five stations
records **100 mm or more** in one day: Barcelona Fabra (0200E), Reus
(0016A), Tortosa (9981A), Castelló (8500A), Valencia Aeropuerto (8414A).
These are the first storm's declared principal stations with an unbroken
record since at least 1978; Barcelona Aeropuerto is left out because its
unbroken run starts in 2011. Days within 3 days of each other are one storm.
100 mm is a round threshold chosen with the first storm's values already
known (159.1 and 179.2 mm both clear it); it is disclosed as such.

**"Twice in three weeks"** means two qualifying storms whose first days are
21 days apart or less. The comparison is a count of how often that has
happened at these five stations from 1978 to 2025, any time of year. It may
be quoted only if the second storm itself qualifies at these five stations
under this definition. A qualifying reading at any of the other 16 stations
does not count toward it.

**The test count.** The payload will carry the number of stations, the
number of station-duration tests (21 x 2 = 42), and how many of them set a
record, so that any record is reported as one result among 42, never alone.

## 2026-10-17 addendum (Saturday, about 12:00 local): six stations where AEMET now points the peak

AEMET's warnings of 17 Oct (routed by TLS News) put the peak where none of
the 21 stations sit: orange for Sunday 18 and Monday 19 in Litoral sur de
Valencia (La Safor), Interior sur de Valencia and Litoral norte de Alicante,
with "300 mm en algunos puntos" probable in 24 h; AEMET special warning
35/2026 names Cabo de La Nao; and orange for Almería from Saturday 17 12:00.

**Rule.** In each of those orange zones, every station in AEMET's inventory
that carries a WMO synoptic index (AEMET's principal stations), resolved on
17 Oct from the inventory's name, location and `indsinop` fields only. No
rainfall was read. Where two identifiers share one synoptic index, the first
AEMET lists.

| id | station | zone | WMO |
|---|---|---|---|
| 8058X | Oliva | Litoral sur de Valencia (La Safor) | 08282 |
| 8293X | Xàtiva | Interior sur de Valencia | 08290 |
| 8050X | Jávea / Xàbia | Litoral norte de Alicante (Cabo de La Nao) | 08370 |
| 6325O | Almería Aeropuerto | Poniente y Almería Capital | 08487 |
| 6332X | Carboneras | Levante almeriense | 08488 |
| 6367B | Huércal-Overa | Levante almeriense | 08428 |

**Timing, stated plainly.** For the Valencia and Alicante stations this
precedes the warned rain (from Sunday 00:00) and any data. For the three
Almería stations it is committed at about the warned onset (Saturday 12:00),
after news of the warnings, so **an Almería result can be body text only,
never a headline**, whatever it shows. No station value for 16 October
onward has been read for any station.

Everything else in this file applies unchanged. The test count becomes 27
stations x 2 durations = 54, reported with every result.
