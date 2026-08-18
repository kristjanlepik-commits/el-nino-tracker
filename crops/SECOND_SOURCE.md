# A second source for crops: what is reachable, and what it would buy

CRO, 2026-08-18, at Kristjan's request. Measured rather than surveyed:
every latency below comes from a live probe on the date above.

**Read section 1 first.** Most of this question has already been
answered on this channel and the answers are good. The new part is
small and specific.

## 1. What we already concluded, so nobody re-derives it

- **The instrument side is already corroborated six ways** and the
  outcome side against FAOSTAT: median correlation on year-to-year
  deviations 0.91, with 5 of 22 pairs failing, and every failure a minor
  crop in its own country (FEASIBILITY 6f). So "we are single-sourced"
  is not true in general.
- **`FRESHNESS.md` already names the right purchase**: USDA Crop
  Progress, because it is faster **in kind** rather than merely faster.
  The reasoning holds and I am not reopening it: cumulative FPAR
  integrates from season start, so a zero-latency vegetation feed would
  still have understated England in July. **A faster driver cannot fix
  an outcome lag.**
- **`research/brief_drift_instrument.md` flags two ERA5 problems.** Both
  are scoped to **pre-1979**: the satellite-era production boundary, and
  erroneous Iberian snow in 1977-12 to 1979-03. **Crops' baseline is
  2001-2025, entirely inside the satellite era, so it inherits
  neither.** Heat's concern was a 1961-1990 baseline. Ours is not.

## 2. What is actually reachable, measured 2026-08-18

| source | newest available | lag | kind |
|---|---|---|---|
| **ASAP soil moisture (ours)** | 2026-07-01 | **48 days** | modelled, STALLED |
| ASAP spine (ours) | 2026-08-01 | 17 days | modelled |
| ESA CCI satellite soil moisture | 2026-07-31 | 18 days | **satellite observation** |
| AgERA5 agromet indicators | 2026-08-10 | 8 days | reanalysis |
| ERA5-Land daily statistics | 2026-08-12 | **6 days** | reanalysis |

All four Copernicus products are in the CDS catalogue and **our existing
`~/.cdsapirc` authenticates**, so there is no new account to open.

**USDA NASS Quick Stats is live and needs a free API key**: an invalid
key returns HTTP 401, not 404. Registration is an email round trip, so
it is a Kristjan task if we pursue it.

## 3. The distinction that changes the answer

`FRESHNESS.md` ruled against buying a faster driver layer. That ruling
is about **acceleration** and it stands.

**Soil moisture is now a different question: replacement, not
acceleration.** It has not published since 1 July, is 48 days behind,
and the composite has been running on five instruments of six for weeks
(tls-internal#23). We are not choosing between a fast driver and the
current setup; we are choosing between a stalled instrument and a
working one. Nothing in the earlier ruling bars that.

**But swapping one model for another is substitution, not
corroboration.** ASAP's soil moisture is modelled and so is ERA5-Land.
Replacing one with the other gives a current number and buys no
independence. **ESA CCI is the one that buys independence**, because it
is a satellite observation rather than a model, at the cost of being 18
days behind rather than 6.

So they answer different questions and we should be clear which we are
asking:

- *"Our sixth instrument is missing"* -> ERA5-Land, 6 days, modelled.
- *"Is ASAP right?"* -> ESA CCI, 18 days, independent in method as well
  as institution.

## 4. The blocker, and it is the same blocker as tls-internal#16

**Every method on this channel ranks a region against its own record
over ASAP's crop mask.** A gridded product only substitutes if we can
aggregate it the same way. Otherwise we would be comparing a 9 km grid
cell average against a crop-masked GAUL1 statistic and calling them the
same instrument, which is the mixed-basis defect one layer down.

`FEASIBILITY.md` already records the same gap from the other side:
weighting country aggregates by cropped area **needs the crop mask**,
and not having it is why the UK's four regions each carry 25% regardless
of cropland (tls-internal#16).

So the crop mask unlocks both, and it is the thing to find out about
before anything else.

**RESOLVED 2026-08-18, same day, and it was never a human task.** I
wrote that `download.php` "needs a human looking at that page" because
curl saw no links. It is JavaScript-driven, so a browser sees all 186 of
them. **I was also one directory off**: the files live under `/files/`
and I had guessed `/data/`.

Everything is freely downloadable, no key, verified by HTTP HEAD:

| file | size | what it buys |
|---|---|---|
| `files/asap_mask_crop_v04.tif` | 106 MB | **the crop mask.** Area-weighted country aggregates (tls-internal#16), and aggregating any gridded second source over the same cropland |
| `files/gaul1_asap_v05.zip` | 131 MB | **our own region geometry.** Socials had to draw England from Eurostat NUTS-1 and caveat that the shapes and the data came from different places |
| `files/crop_calendar_gaul1.zip` | 26 KB | per-crop season windows, 3,068 rows |
| `files/asap_mask_rangeland_v04.tif` | 375 MB | rangeland mask, not ours |
| `files/phenos*_v04.tif` | ~130 MB each | phenology rasters |

**THE CALENDAR IS NOT THE UNBLOCK IT LOOKS LIKE, and I nearly reported
it as one.** It is genuinely per-CROP, which is the distinction 6d said
was missing: `crop_name` is a column, with "Wheat (Spring)", "Rice
(Boro)", "Maize (Meher)" and 90 others. But it covers **74 countries and
995 GAUL1 units, all of them food-security countries**. Mexico, Ukraine,
Argentina, Canada and Australia, the five 6d lists as blocked, are all
ABSENT. So is France, and so is the UK.

I first reported the UK as present with 39 rows. That was my own regex:
`str.contains("U.K.")` treats `.` as any character, so it matched
**Burkina Faso**. Trap 18 again, in my own verification, an hour after
writing it up.

So the calendar helps the food-security half of the channel and does
nothing for the European story currently carrying it.

## 5. Recommendation

1. ~~Find out whether the ASAP crop mask is downloadable.~~ **DONE, it
   is, 106 MB at `files/asap_mask_crop_v04.tif`.** The work it gates is
   now the item: area-weighted aggregates (tls-internal#16) and gridded
   aggregation for any second source. Pulling it plus the GAUL1 geometry
   is 237 MB and needs nobody's permission but the disk.
2. **If it is: ERA5-Land for the stalled instrument, ESA CCI as the
   check.** Both via credentials we already hold.
3. **USDA Crop Progress remains the right answer to the OUTCOME lag**,
   unchanged from `FRESHNESS.md`, and needs a free NASS key. US-only,
   which is worth stating plainly: it does nothing for the UK and France
   story that is currently carrying this channel.

**What I would not do:** add a second source to look better corroborated.
The outcome side is already checked against FAOSTAT and the instrument
side six ways. The only genuine gaps are a stalled instrument and an
outcome lag that no vegetation feed can close.
