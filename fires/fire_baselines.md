# Fire tracker baselines (frozen 2026-07-26)

Frozen reference series for the 2026-27 fire season. Every weekly
number the tracker publishes is a comparison against this document
and its companion dataset `data/baselines_daily.json` (daily counts
per region per season, 2012-2025). Baselines are immutable: a
correction is a dated addendum at the bottom, never an edit.

## Method (applies to every number below)

- Sensor: VIIRS on Suomi-NPP only (SNPP), the longest single-sensor
  record (2012+). NOAA-20 exists only from 2018 and is never mixed
  into cross-year comparisons.
- Product: science-quality archive (VIIRS_SNPP_SP), which lags ~3
  months. In-season 2026 numbers come from the NRT product and are
  restated when the archive catches up.
- Detections with low confidence are excluded, on both sides of
  every comparison.
- One detection is one ~375 m satellite pixel observed actively
  burning on one overpass; weekly counts measure extent and
  persistence together, not the number of fires (see the weekly
  issue boilerplate for the full caveat set).
- Region boxes (versioned; any change is a logged event):

  - Amazon (Brazil, Bolivia, Peru box): 20S-5N, 80-43W
  - Indonesia (Sumatra + Kalimantan box): 7S-7.5N, 94-119.5E
  - US West (CA + PNW box): 32-49N, 125-114W
  - Mediterranean (EU + North Africa box): 34-46N, 10W-30E
  - Australia (continental box; season labeled by start year): 44-10S, 112-154E
- Weekly bins below are fixed calendar-date bins (7 days from the
  season window start, identical dates every year). Operational
  weekly issues compare exact trailing date windows re-pulled from
  the archive; these tables are the frozen reference and season
  totals.
- Pull mechanics: FIRMS area API, 5-day chunks (API cap), pulled
  2026-07-25/26 with MAP_KEY registered to the project.


## Amazon (Brazil, Bolivia, Peru box)

Season window: Aug 01 + 92 days.

### Season totals (SNPP detections, full window)

| Season | Total | vs 2012-25 mean |
|---|---|---|
| 2012 | 1,153,988 | 1.15x |
| 2013 | 548,313 | 0.55x |
| 2014 | 795,125 | 0.79x |
| 2015 | 1,072,876 | 1.07x |
| 2016 | 839,507 | 0.84x |
| 2017 | 1,103,117 | 1.10x |
| 2018 | 629,616 | 0.63x |
| 2019 | 1,118,115 | 1.11x |
| 2020 | 1,275,278 | 1.27x |
| 2021 | 1,005,177 | 1.00x |
| 2022 | 1,087,789 | 1.08x |
| 2023 | 889,427 | 0.89x (analog year) |
| 2024 | 2,002,525 | 2.00x (analog year) |
| 2025 | 525,779 | 0.52x |

2012-25 mean: 1,003,331.

### Analog-year weekly series (fixed date bins)

| Week | 2023 | 2024 | 2012-25 mean |
|---|---|---|---|
| Aug 1-7 | 33,607 | 132,620 | 45,762 |
| Aug 8-14 | 36,056 | 103,213 | 54,300 |
| Aug 15-21 | 67,427 | 129,919 | 74,979 |
| Aug 22-28 | 59,534 | 204,787 | 86,297 |
| Aug 29-Sep 4 | 55,446 | 300,225 | 96,862 |
| Sep 5-11 | 82,266 | 353,878 | 127,408 |
| Sep 12-18 | 86,389 | 185,055 | 110,683 |
| Sep 19-25 | 80,205 | 197,851 | 91,767 |
| Sep 26-Oct 2 | 73,529 | 92,531 | 73,414 |
| Oct 3-9 | 78,929 | 118,372 | 70,759 |
| Oct 10-16 | 67,498 | 87,771 | 66,475 |
| Oct 17-23 | 88,500 | 43,450 | 55,987 |
| Oct 24-30 | 73,189 | 46,661 | 43,630 |

## Indonesia (Sumatra + Kalimantan box)

Season window: Aug 01 + 92 days.

### Season totals (SNPP detections, full window)

| Season | Total | vs 2012-25 mean |
|---|---|---|
| 2012 | 178,755 | 1.46x |
| 2013 | 100,934 | 0.83x |
| 2014 | 203,981 | 1.67x |
| 2015 | 564,037 | 4.62x (analog year) |
| 2016 | 46,099 | 0.38x |
| 2017 | 27,340 | 0.22x |
| 2018 | 83,787 | 0.69x |
| 2019 | 260,110 | 2.13x |
| 2020 | 24,173 | 0.20x |
| 2021 | 18,498 | 0.15x |
| 2022 | 12,479 | 0.10x |
| 2023 | 115,685 | 0.95x (analog year) |
| 2024 | 40,703 | 0.33x |
| 2025 | 32,508 | 0.27x |

2012-25 mean: 122,078.

### Analog-year weekly series (fixed date bins)

| Week | 2015 | 2023 | 2012-25 mean |
|---|---|---|---|
| Aug 1-7 | 7,608 | 5,922 | 4,854 |
| Aug 8-14 | 13,503 | 6,458 | 6,926 |
| Aug 15-21 | 27,770 | 6,823 | 8,342 |
| Aug 22-28 | 28,345 | 3,263 | 8,064 |
| Aug 29-Sep 4 | 55,158 | 13,085 | 10,235 |
| Sep 5-11 | 63,377 | 4,793 | 11,297 |
| Sep 12-18 | 51,569 | 5,315 | 13,561 |
| Sep 19-25 | 61,217 | 9,974 | 14,859 |
| Sep 26-Oct 2 | 45,311 | 21,173 | 11,202 |
| Oct 3-9 | 47,524 | 13,262 | 9,696 |
| Oct 10-16 | 56,742 | 11,377 | 9,329 |
| Oct 17-23 | 72,796 | 5,442 | 8,198 |
| Oct 24-30 | 31,603 | 8,299 | 5,128 |

## US West (CA + PNW box)

Season window: Jun 01 + 153 days.

### Season totals (SNPP detections, full window)

| Season | Total | vs 2012-25 mean |
|---|---|---|
| 2012 | 161,857 | 1.22x |
| 2013 | 81,401 | 0.61x |
| 2014 | 78,491 | 0.59x |
| 2015 | 156,010 | 1.17x |
| 2016 | 64,919 | 0.49x |
| 2017 | 178,037 | 1.34x |
| 2018 | 154,785 | 1.16x |
| 2019 | 37,294 | 0.28x |
| 2020 | 306,578 | 2.31x |
| 2021 | 305,281 | 2.30x |
| 2022 | 80,758 | 0.61x |
| 2023 | 54,093 | 0.41x |
| 2024 | 131,113 | 0.99x |
| 2025 | 71,329 | 0.54x |

2012-25 mean: 132,996.


## Mediterranean (EU + North Africa box)

Season window: Jun 01 + 122 days.

### Season totals (SNPP detections, full window)

| Season | Total | vs 2012-25 mean |
|---|---|---|
| 2012 | 137,479 | 1.94x |
| 2013 | 68,557 | 0.97x |
| 2014 | 61,648 | 0.87x |
| 2015 | 59,250 | 0.84x |
| 2016 | 80,408 | 1.14x |
| 2017 | 103,872 | 1.47x |
| 2018 | 42,425 | 0.60x |
| 2019 | 57,581 | 0.81x |
| 2020 | 56,344 | 0.80x |
| 2021 | 83,369 | 1.18x |
| 2022 | 52,596 | 0.74x |
| 2023 | 46,880 | 0.66x |
| 2024 | 53,659 | 0.76x |
| 2025 | 87,496 | 1.24x |

2012-25 mean: 70,826.


## Australia (continental box; season labeled by start year)

Season window: Nov 01 + 120 days.

### Season totals (SNPP detections, full window)

| Season | Total | vs 2012-25 mean |
|---|---|---|
| 2012-13 | 641,173 | 1.92x |
| 2013-14 | 249,467 | 0.75x |
| 2014-15 | 222,487 | 0.66x |
| 2015-16 | 240,192 | 0.72x (analog year) |
| 2016-17 | 212,649 | 0.64x |
| 2017-18 | 351,261 | 1.05x |
| 2018-19 | 463,552 | 1.39x |
| 2019-20 | 845,275 | 2.53x (Black Summer: NOT an El Nino year; never an analog) |
| 2020-21 | 160,078 | 0.48x |
| 2021-22 | 191,418 | 0.57x |
| 2022-23 | 151,938 | 0.45x |
| 2023-24 | 437,521 | 1.31x (analog year) |
| 2024-25 | 289,819 | 0.87x |
| 2025-26 | 228,263 | 0.68x |

2012-25 mean: 334,650.

### Analog-year weekly series (fixed date bins)

| Week | 2015 | 2023 | 2012-25 mean |
|---|---|---|---|
| Nov 1-7 | 28,772 | 99,055 | 46,822 |
| Nov 8-14 | 27,888 | 59,631 | 39,703 |
| Nov 15-21 | 55,840 | 28,899 | 35,234 |
| Nov 22-28 | 37,005 | 13,285 | 25,064 |
| Nov 29-Dec 5 | 17,812 | 30,973 | 28,808 |
| Dec 6-12 | 11,162 | 61,750 | 29,438 |
| Dec 13-19 | 8,001 | 24,291 | 22,005 |
| Dec 20-26 | 4,678 | 34,556 | 16,603 |
| Dec 27-Jan 2 | 3,964 | 47,200 | 21,227 |
| Jan 3-9 | 10,306 | 11,887 | 16,878 |
| Jan 10-16 | 8,213 | 5,538 | 13,009 |
| Jan 17-23 | 7,671 | 3,998 | 8,339 |
| Jan 24-30 | 4,698 | 2,412 | 7,108 |
| Jan 31-Feb 6 | 1,014 | 3,261 | 7,565 |
| Feb 7-13 | 4,569 | 3,741 | 5,867 |
| Feb 14-20 | 4,048 | 1,774 | 5,063 |
| Feb 21-27 | 4,122 | 4,844 | 5,246 |

Australia analog seasons are 2015-16 and 2023-24 (El Nino years). Weekly dates shown are the analog season's own dates (Nov of the start year onward).

## Standing records and anchors (from research/impact_database_2026-27.md; not re-derived)

- Indonesia 2015: ~2.6 M ha burned; $16.1 B direct (World Bank 2016),
  ~$28 B health-inclusive (Kiely et al. 2021); ~100,300 excess deaths
  (Koplitz et al. 2016). The mortality and cost record.
- Indonesia 1997: ~8 M ha; up to 2.57 Gt C (Page et al. 2002). The
  area and carbon record.
- Amazon 2024: ~2.8 M ha primary-forest fire (MAAP), breaking 2016's
  ~1.7 M ha. Visible in our series: the 2024 Amazon season is the
  largest at 2.0 M SNPP detections, 1.9x the 14-year mean.
- Australia Black Summer 2019-20 (845k detections in our series,
  1.9x mean) was NOT an El Nino year (neutral ENSO, strong +IOD).
  Never presented as an El Nino precedent. By-area record remains
  1974-75 (~117 M ha, grassland).
- Scale anchor: the 1997-98 El Nino cost ~$5.7 T globally over five
  years (Callahan and Mankin 2023).

## Addenda

(none)

