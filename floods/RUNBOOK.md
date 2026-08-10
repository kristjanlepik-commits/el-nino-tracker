# Floods: answering a flood in the news, from a standing start

Written after Manila, 2026-08-10, which is the only time this has been
done end to end. Region did not exist in the codebase at 11:00 and was
answered by 13:00. Everything below is what that run actually cost,
not an estimate.

This exists so the path does not depend on whoever happens to be in the
conversation.

## The short version

    1. draw the box on the catchment          5 min
    2. rainfall baseline, 27 years            25 min,  5 MB
    3. flood baseline, 23 years               55 min,  2.3 GB per tile
    4. current week, both instruments         10 min
    5. emit the payload                       seconds

Steps 2 and 3 run in parallel. **Answer exists in about two hours.**

## 1. Draw the box

On the catchment, not on the country. This is the single largest lever
on the answer: the same 2017 Peru event reads 1.8x the median over a
regional rectangle and 4.4x over the Piura and Chira catchments alone.
A box drawn around a country dilutes the signal with everywhere the
water did not go.

But not too small either. The Tana at 157 flood pixels a week sits
below the count floor and its ranking is noise. There is a workable band
and it has not been mapped precisely; two 10-degree tiles is a
reasonable default.

Check the tile count before committing, because cost is per tile:

    lon -> h = (lon + 180) // 10        lat -> v = (90 - lat) // 10

Two tiles is 4.6 GB. Six tiles is 13.9 GB and about three hours.

Add the box to `REGIONS` in `fetch_mcdwd_baseline.py`,
`fetch_imerg_baseline.py` and `compare_products.py`. Same id in all
three.

## 2. Rainfall baseline

    .venv/bin/python floods/fetch_imerg_baseline.py \
      --region <id> --start MM-DD --end MM-DD \
      --years 2000-2026 --product GPM_3IMERGDL

**Use the Late Run, not the Final Run.** Final is roughly ten months
behind and cannot answer a news event at all. Late reaches back to 2000,
so the whole comparison uses one product, which matters: a Final-Run
baseline against a Late-Run current week measures the product change
rather than the weather.

Late Run runs about two days behind, so a window ending yesterday will
be short. Say so rather than stretching it.

## 3. Flood-extent baseline

    ~/tls-floods-capture/bin/venv/bin/python floods/fetch_mcdwd_baseline.py \
      --region <id> --start MM-DD --end MM-DD --years 2003-2025 --workers 6

Needs `pyhdf`, which is why it runs from the pinned venv rather than
the repo one. Resumable: rerun it after any failure and it picks up
where it stopped. Announce it in `.running-jobs` and hold a
duration-based `caffeinate` covering the WORST case, not the estimate.

2003 is the start, not 2000: Aqua launched mid-2002 and the archive is
Terra-only before that.

## 4. Current week

    ~/tls-floods-capture/bin/venv/bin/python floods/compare_products.py \
      --region <id> --products mcdwd_l3_nrt --start YYYY-MM-DD --end YYYY-MM-DD

The archive product stops at 2025, so the current period comes from the
near-real-time one. They agree: 20 paired days in December 2025 gave a
ratio of 1.007 with identical observability, so this crossing is safe.

**Wait for it to finish before reading the file.** On the Manila run I
read it mid-write and emitted a payload from five of seven days. The
slot counts caught it, but they should not have had to.

## 5. Emit

    .venv/bin/python floods/emit_region_payload.py \
      --region <id> --label "<human name>" --window MM-DD:MM-DD \
      --as-of YYYY-MM-DD --rain-baseline <...> --flood-baseline <...> \
      --flood-current <...> --out floods/data/payload_<id>_<date>.json

## Reading the result

The payload decides, not you. Each instrument returns one of:

    measured        a value with rank and basis
    cannot_say      the region's own history says the instrument cannot
                    see it; carries machine-readable reasons
    awaiting_data   the region qualifies, the period has not arrived

**A `cannot_say` on flood extent is a result, not a failure.** Manila
returned it because across 20 years its flood measure tracks how much
the satellite could see at +0.82, and 2012, the Habagat, reads zero
flood pixels at 0.02 observability. Publishing a ranking there would
have called the worst flood in the record unremarkable.

Expect it in the wet tropics. Optical flood detection fails hardest
exactly where the most damaging floods happen, so a region that floods
catastrophically is more likely than average to be one we cannot see.

## If the region fails the gate

Ship the rainfall answer alone and say plainly that flood extent could
not see the region this week, with the observability figure. That is a
publishable piece: Manila was rank 2 of 27 on rainfall, behind only
2012, and the fact that the flood instrument was blind during the
Habagat is more interesting than a flood-extent ranking would have been.

Do not substitute a different flood product to get an answer. The
comparison would then be against a baseline that product never built.

## What this cannot do

- **Answer the same day for a six-tile region.** Three hours of
  fetching, so start it before the news cycle turns.
- **Answer for the current day.** Flood extent uses a 3-day composite
  and the capture runs two days behind; rainfall is one to two days
  behind. A window ending today does not exist yet.
- **Compare across regions.** Every number is a region against its own
  history. There is no cross-region ranking and building one would need
  a land mask we do not have; 72% of globally record-wet cells are open
  ocean.
