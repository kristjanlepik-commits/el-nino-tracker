# Heat: what data we actually have

For visual design. Generated from `heat/data/city_nights.json`, so every
number below is the live payload rather than a description of it.

**This is an inventory, not a proposal.** No layout is implied.

## What the channel measures

**Tropical night**: daily minimum temperature at or above 20.0 C.

ETCCDI index TR, as published by European met services. Not a threshold we chose.

> Nights that never fall below 20 C, per European city, each against its own record. One thermometer per city, city warming included. Not a climate measurement and never presented as one.

**Coverage.** Spain and France. This metric does not work in northern Europe, where tropical nights are near zero and ratios divide by almost nothing.

**Attribution tag.** `Not ENSO-linked` (one of three permitted strings).
**Evidence basis.** Measured.

## Scope

- **15 cities**, Spain and France
- **8 at an outright record**, 14 in the warmest twentieth of their own history, 15 in the warmest tenth
- Station records run from **1920** to 2025; the longest is 105 years, the shortest 51
- Two sources: AEMET OpenData, Meteo-France, via data.gouv.fr. Both permit commercial reuse.
- Featured cities, chosen by the channel: **Paris, Madrid, Bilbao**

All published sources permit commercial reuse. ECA&D is used for verification only, never as a published source, because it is non-commercial. Every city was verified day-by-day against its own independent historical record before use.

## THREE separate time series per city, and they are not interchangeable

This is the part most likely to be missed. Every city carries three
full histories, and only one of them is currently drawn anywhere.

| series | what it is | length (Madrid) | currently used |
|---|---|---|---|
| `series_to_same_date.values` | nights so far, every prior year cut at the same calendar day | 104 years | yes |
| `full_year_series` | nights across the whole year, complete seasons only | 104 years | **no** |
| `warmest_night_c` | the single warmest night of each year, in degrees | 104 years | **no** |

`warmest_night_c` is a different quantity entirely: an intensity in degrees
rather than a count of nights. Madrid's runs 25.7, 25.7, 26.1 for 2023 to 2025.
It answers "how hot did the hottest night get" where the counts answer
"how many hot nights were there". Nothing on the site uses it.

`full_year_series` versus the to-date series is the honest way to show that
2026 is unfinished: Madrid has 51 nights to 2026-08-02, its to-date record was 40, and its full-year 2025 was 66.

## Per city, everything emitted

| city | nights 2026 | rank | of years | normally | margin | source | as of | cov |
|---|---|---|---|---|---|---|---|---|
| Lyon | 31 | 1 | 51 | 6.9 | +12 | Meteo-France | 2026-08-03 | 100% |
| Zaragoza | 44 | 1 | 76 | 13.8 | +11 | AEMET OpenData | 2026-08-02 | 100% |
| Madrid | 51 | 1 | 105 | 21.0 | +11 | AEMET OpenData | 2026-08-02 | 99% |
| Bilbao | 16 | 1 | 78 | 1.2 | +8 | AEMET OpenData | 2026-08-02 | 100% |
| Montpellier | 41 | 1 | 81 | 17.6 | +6 | Meteo-France | 2026-08-03 | 100% |
| Paris | 17 | 1 | 81 | 1.5 | +4 | Meteo-France | 2026-08-03 | 100% |
| Murcia | 56 | 1 | 85 | 34.3 | +2 | AEMET OpenData | 2026-08-02 | 100% |
| Malaga | 56 | 1 | 80 | 34.2 | +1 | AEMET OpenData | 2026-08-02 | 100% |
| Alicante | 55 | 2 | 88 | 35.9 | n/a | AEMET OpenData | 2026-08-02 | 100% |
| Nice | 56 | 2 | 84 | 30.7 | n/a | Meteo-France | 2026-08-03 | 100% |
| Valencia | 59 | 2 | 89 | 39.7 | n/a | AEMET OpenData | 2026-08-02 | 100% |
| Seville | 47 | 3 | 76 | 30.0 | n/a | AEMET OpenData | 2026-08-02 | 99% |
| Barcelona | 53 | 3 | 86 | 29.2 | n/a | AEMET OpenData | 2026-08-02 | 97% |
| Palma | 58 | 3 | 52 | 42.8 | n/a | AEMET OpenData | 2026-08-02 | 100% |
| Marseille | 33 | 7 | 103 | 21.5 | n/a | Meteo-France | 2026-08-03 | 100% |

`margin` is nights beyond that city's own previous record, and is **null**
rather than 0 where no record was set. Null means "did not beat it"; 0 would
mean "tied it".

## What a renderer may NOT do

These ride with the data as fields, not as conventions. Each is a build
failure in the mockup rather than something to remember.

**`rank.requires_series: true`.** This rank may not be rendered without the series below it. A bare rank is an alarm; the same rank beside its ordinary years is a calibrated statement, which is the only thing on the page we ask a reader not to take on trust.

**`headline_requires_baseline: true`.** The count of 8 may not
appear without its baseline: a typical year produces 0, and with no trend the expected number is 0.19.

**`may_not_say`.** 2026 is NOT the worst year on this measure. 2003 produced 12 on the same to-date basis and is inside living memory for this readership.

**`series_to_same_date.cut_note`.** Every year counted to this calendar day, matching this city's own as-of date. NOT comparable to a figure cut at a different day: one day in early August is worth about 0.66 nights in Marseille. Cities from different sources have different cuts, so a cross-city ranking cannot use a single one.

**`rank.matched_note`.** Every prior year is counted to the same calendar day as 2026, so this is not a partial year against complete ones.

**Never open `heat/crosscheck/city_histories_ECAD.json`.** It is ECA&D, which
is non-commercial and is used for verification only. The payload is AEMET and
Meteo-France. Mixing them puts two sources inside one figure.

## Why the lead is not the record count

The channel emits its own lead: **"Not one of these cities is having an ordinary summer for hot nights."**

> Product's ruling 2026-08-06. The record count can legitimately change through a data update: Malaga leads by ONE night and loses the record if the cut advances a day. This framing cannot move on a revision, and 'there is no normal city here' is a stronger claim than 'some cities broke records'.

## What is NOT in the payload

- No standard deviation, so no z. Only rank and percentile.
- No sub-annual detail: no daily or monthly values, only annual counts.
- No cities outside Spain and France, and the metric does not travel north.
- No projection, no forecast, no attribution beyond the single tag.
- No population or exposure figures, so nothing supports a harm claim.

