# Youth heat map: spec and pre-registration

Status: **PRE-REGISTRATION, frozen 2026-11-05.** Rulings D-347 and D-348;
G1 done on documents with values masked; no score computed at the time of
this commit. Changes go in a dated amendment at the end (section 13).

Owner: TLS Youth chat (index, inputs, validated JSON, sign-off).
Rendering: design. Copy: editor. Publishing: platform. Research: EOS,
Kristjan's separate research workspace, thread soc/gen-z-west.
Rulings so far: D-345 (one test page, no menu item, live before the 20
November strikes), D-346 (heat is a generated index with legs B and C).

## 1. What this measures, in one paragraph

**No source measures anger.** What exists, asked identically in all 27
countries with an age split, is political discontent: distrust of
national institutions, dissatisfaction with democracy, and the sense
that the country is heading the wrong way. So heat means: **how far a
country's young people reject the way their country is being run,
compared with young people across Europe and with older people at
home.** It is a proxy, and the page says so. It is also dated: the
newest data was collected from 12 March to 1 April 2026, so **it cannot
contain the autumn 2026 protests.** Those get a separate marker (section
7) and never enter the score.

## 2. Inputs

### Why these sources

| Candidate | All 27, same question? | Age split by country? | Usable? |
|---|---|---|---|
| **Standard Eurobarometer, Volume C tables** (EC open data portal) | Yes, about 1,000 per country; 500 in LU, MT, CY | Published per country, no login | **Yes: the source** |
| Eurobarometer microdata via GESIS | Yes | Yes, any age band | **No.** Its terms (valid 4 Feb 2026) allow scientific use only, bar commercial use, and prohibit processing the data with AI systems |
| European Social Survey round 11 (has protest participation) | No: secondary sources suggest about 22 of 27, unverified | Microdata, login | Not in the index (D-346: a leg or item missing for some countries makes scores incomparable). Candidate for country pages after EOS confirms coverage and terms |
| Eurostat `ilc_pw03` | Yes | Yes | No: the table now holds trust in OTHERS only, not trust in politics |
| Eurostat `ilc_pw01` life satisfaction | Yes | Yes | Not in the index: a personal measure, not anger at anything, and its values are already known to us (section 12). On the page, block 3 |
| Eurostat `ilc_pw10` feeling left out | No Germany, 2022 only | Yes | No |
| Eurostat `ilc_scp19` active citizenship | 25 of 27 in 2022 | Yes | No: coverage, and it blends activities |
| Flash Eurobarometer 585 (youth and democracy, 19 June to 1 July 2026, ages 15-30) | Yes | Young only, no older group | Not in the index, since B cannot be built from it. Used to validate (V5) and on country pages |
| National polls, Ipsos and similar | No | Varies | Country pages only (D-346) |
| Emigration statistics | Registers differ by country | Yes | Country pages only |
| ACLED | n/a | No ages | **Not used.** Its terms restrict commercial entities, require transformative publication, and bar use as AI input without written consent |

### Waves

Pool the three newest waves in the portal, all under the Commission
reuse licence:

- Standard Eurobarometer 103, spring 2025
- Standard Eurobarometer 104, autumn 2025
- Standard Eurobarometer 105, spring 2026

Fieldwork: 26 March to 10 May 2025; 9 October to 5 November 2025; 12
March to 1 April 2026. Standard Eurobarometer 106 is not in scope for
launch. Its arrival is a new issue of the index, not an edit of this one.

**Two limits of the survey, printed on the page.** It covers nationals and
EU citizens resident in each country, so young people from outside the EU
are not in it. And in wave 104, the one wave whose method note we have
read, interviews were in person except in Cyprus, Denmark, Malta, the
Netherlands, Finland and Sweden, which used remote video. The question is
identical; the setting is not. Those six carry a mark on their pages, and
the run also reports how many tiers change if they are left out of the
reference. That report is disclosure, not a gate.

### Items

| Component | Question | Scored as |
|---|---|---|
| DISTRUST | QA6: tend to trust or not: national government, national parliament, political parties | Share "tend not to trust" among those answering either way, averaged over the three |
| DEMOCRACY | SD18a: satisfaction with the way democracy works in (our country) | Share "not very" plus "not at all" among the four substantive answers |
| DIRECTION | D73.1: things going in the right or wrong direction in (our country) | Share "wrong" among right plus wrong |

Don't-knows are excluded from the base, and spontaneous "neither" with
them, because both differ by age. Three components, equal weight: the
three trust items share one component so that three versions of one
question do not outvote the other two.

Confirmed at G1: all five items, in all 27 countries and the UK, in all
three waves (variable table, section 13).

### Ages

**Young = born 1997 or later. Older = 55+.** Across these waves the young
band is ages 15 to 28 in 2025 and 15 to 29 in 2026, the Gen Z frame EOS
works in, with about 45% more respondents than 15-24. D-347 first ruled
15-24, because that looked like all the tables publish; Kristjan moved it
once G1 found the generation column, before any score existed.

**The known risk is dilution:** if the anger sits with teenagers, the
25-29s could mute it. So the run also computes the whole recipe with 15-24
as the young band and reports how many countries change tier. That side
check never changes the map and is not a gate.

### Real sample sizes, and the plus or minus 12

From the published weighted bases, three waves pooled. Only weighted bases
are published. Gap interval is 95%, at 50%, with an assumed design effect
of 1.5.

| Three waves pooled | Born 1997+ | 55+ | Gap, born 1997+ | Gap, 15-24 side check |
|---|---|---|---|---|
| Median of 27 | 527 | 1,229 | +/-6.2 | +/-7.1 |
| Germany | 838 | 2,007 | +/-4.9 | +/-5.9 |
| Sweden | 336 | 1,342 | +/-7.3 | +/-8.7 |
| Malta | 277 | 498 | +/-9.0 | +/-10.8 |

Product's guess of about +/-12 was right for one wave of 15-24s. Pooling
is what makes leg B possible, and whether it is enough is tested, not
assumed (V3).

## 3. The recipe

For country i and component k, with y = young share, o = older share,
g = y minus o, each pooled across waves weighted by base:

    C(i,k) = (y(i,k) - mean y(k)) / sd y(k)
    B(i,k) = (g(i,k) - mean g(k)) / sd g(k)
    C(i)   = mean of C(i,k) over the three components
    B(i)   = mean of B(i,k) over the three components
    SCORE  = (C(i) + B(i)) / 2

Mean and sd are unweighted across the EU27 (each country one vote),
computed once and frozen. A country that is later greyed or corrected
does not move anyone else's score. A non-EU country (the UK, if its
items exist in all three waves) is scored against that frozen reference
and never enters it.

**Tiers, fixed now:** HOT at +1.0 or above; WARM +0.4 to +1.0; MILD -0.4
to +0.4; COOL below -0.4. No quota: nothing forces a country into any
tier. Countries appear in tiers, not ranks.

**Type label, beside the score:**

| | Gap clearly positive | Gap not clearly positive |
|---|---|---|
| C(i) at +0.4 or above | youth revolt | angry country |
| C(i) below +0.4 | generational gap | calm |

"Gap clearly positive" uses the raw gap in points, the mean of g(i,k),
with the 90% interval above zero. So it answers the plain question: are
the young more discontented than their own elders?

**Three properties of this recipe, stated so nobody finds them later:**

1. **The score is relative.** It says hot compared with the rest of the
   EU now. It cannot say Europe as a whole got angrier, and some country
   is nearly always warm. The A marker is the only absolute signal.
2. **Leg B in the score is centred on the typical European gap.** Where
   the young are less discontented than their elders almost everywhere,
   a country can score high on B while its young are still below its
   old. That is why the type label uses the raw gap: the score ranks,
   the label says what is true.
3. **Reporting habits only half cancel.** D-346 is right that B cancels
   national habits. C does not, and C is half the score.

**Noise.** SE of a pooled share p is sqrt(1.5 p (1-p) / n), n the summed
weighted base, design effect 1.5 assumed. If the wave to wave spread is
larger, all SEs are scaled up: R squared is the mean over countries and
components of (variance of the three wave values / 3) over the mean of the
squared SE, and SEs are multiplied by R when R exceeds 1. 90% interval by
simulation, 2,000 draws, seed 20261120: one normal shock per country per
age group, shared by that group's components (fully correlated,
conservative), scored against the frozen reference. "Gap clearly positive"
means the 5th percentile of the simulated mean gap is above zero. A country
whose score interval crosses more than one tier boundary is shown as "too
noisy to place": it keeps its numbers and gets no tier or type.

**Pooling.** A share is computed per wave with don't-knows excluded, then
averaged across the three waves weighted by that column's weighted base.
Answer cells shown as "-" count as zero.

**Side checks, reported with the result, never changing it:** tiers changed
under 15-24; tiers changed if the six video-interview countries are left
out of the reference.

## 4. Leg A, under D-346's rule

D-346: A joins as an equal third leg only if the same items are repeated
across all countries; otherwise it is a marker.

**Result at G1, on documents alone: A stays a marker.** The 2019 reference
waves (Standard Eurobarometer 91 and 92) were all in person. Six countries
were interviewed by video in wave 104, so mode does not match. The first
2019 table opened also has no SD18a sheet, so the democracy item may not
repeat either. The extra reliability condition proposed in the draft is
therefore moot.

Every country shows a hotter or cooler marker in raw points against 2019,
on DISTRUST and DIRECTION where both periods exist, using 15-24 in both
periods whatever the young band above (a generation ages, an age band
does not). The six video countries carry the mode mark on it. The marker
never enters the score.

## 5. Gates, fixed before seeing any score

Run once, on the full data. For V2 and V3, each of the three waves in turn
is scored alone and the other two pooled, each set standardised within
itself; the bar applies to the median of the three Spearman values. V1 is
the median of the three pairwise values on pooled y. **Any failure drops
the index and the page moves to Plan B (section 6).** A map that looks wrong but passes every
gate is **published as it is.** That is D-347's reading of "dropped or published
as it is": numbers decide which, not how the map looks.

| Gate | Test | Bar | Why |
|---|---|---|---|
| V1 coherence | Median Spearman among the three components of y, across 27 | 0.5 or above | EOS argues against blending because its distress measures do not move together (0.03). This tests the same objection on these items |
| V2 C reliability | Each wave against the other two pooled, median Spearman on C | 0.7 or above | Implies about 0.84 reliability for three waves pooled |
| V3 B reliability | Same, on B | 0.4 or above | Implies about 0.6 pooled. Gaps between two small samples may be noise; if so, D-346's B leg cannot be built from this data |
| V4 placement | Countries with a tier | 20 of 27 or more | A map that is mostly "too noisy" is not a map |
| V5 outside check | Spearman of C(i) against Flash Eurobarometer 585 Q18.1, share disagreeing that policymakers in (our country) take the long-term consequences of their decisions into account, don't-knows excluded, across 27 | 0.5 or above | Independent sample, later date (June-July 2026), different wording. Replaces the draft's Flash 556, which is not in the portal search and is older |

## 6. Plan B, if a gate fails

**The page still ships before 20 November.** The map is coloured by one
unblended measure: share of young people born 1997 or later dissatisfied
with how democracy works in their country, three waves pooled. No score, tier or type. Older-age
dots stay on country pages. Every other block is unchanged, so design
builds one map that takes either colouring and no build work is lost.

## 7. The "now" marker

Separate from the score, and labelled as separate on the page. Per
country: dated youth-involving protest events since 1 September 2026,
each with a named source, crowd figure with who counted it, and ages only
where an official or stated source gives them. From EOS protest findings
that have passed its scope check, and from the News desk's routed items.
Hand-curated: 27 countries, not an event database.

Absence reads "none found as of [date]", never "calm". A country nobody
has checked reads "not checked".

## 8. Country page slots

A number counts as abnormal only with a comparator. The validator fails
a block whose number claims abnormality without one.

| # | Block | Source | Exists for |
|---|---|---|---|
| 1 | Name, tier, type, score in small print, data date, one headline | Common layer; editor's words | 27 |
| 2 | **The discontent, moved up (working name "the anger"; editor to name):** each component, young against older against young Europeans, as dots; A marker | Eurobarometer | 27 |
| 3 | **My life against my country:** personal direction (D73.4) against country direction (D73.1) by age, plus life satisfaction against the EU and against all adults | Eurobarometer, Eurostat `ilc_pw01` | 27 |
| 4 | **What it is about:** top issues, personally and nationally (QA3, QA4), with a European marker on each bar; national surveys beneath, labelled as national | Eurobarometer; EOS deep dive | 27 / deep-dive countries |
| 5 | **Renamed from "Why here" (editor to name; working title "What they are up against"):** housing, poverty, jobs, age leaving home, each against the EU. Stated plainly: not in the score | Eurostat | 27 |
| 6 | **Right now:** the section 7 marker, with the next date; share of young people who took action to change society in the past year, against the EU (Flash 585 Q7a, a petition counts as well as a rally, so never called protest) | EOS, News; Flash 585 | Where checked; Flash 585 for 27 |
| 7 | **Nearest contrast, chosen by rule, not by hand:** the country most alike on block 5 and most different on C(i) | Computed | 27 |
| 8 | Trust and care: source per number, confidence per block, the recipe, national helpline | All | 27 |

Dashed "not yet measured" marks stay for anything absent. A page with no
deep dive says so. QA3 and QA4 by age are noisy per country and are
checked for that before block 4 relies on them; if too noisy, block 4
falls back to deep-dive countries only.

### Corrections to the Germany mockup

- **Headline changes.** It omits that German 16-29s are joint lowest in
  the EU on life satisfaction, 7.2 against 7.5 (Eurostat `ilc_pw01`,
  2025). Highest among German ages and near the bottom among young
  Europeans are both true, and the page must say both. Re-read from
  source before use.
- **"Spain: just as content" is wrong:** Spain 7.6, Germany 7.2. Nearest
  contrast becomes computed (block 7).
- Keep: young-against-older dots, "my life against my country", dashed
  marks, nearest contrast.
- **The German stressor bars** (Jugend in Deutschland 2026) are marked
  as read through a summary. Unusable until EOS has opened the study.
- **The comparator rule, by example:** the French figure is 79% who have
  considered living elsewhere and 34% seriously, online panel, no
  comparator. It may appear as that, in those words. It is not "80% want
  to leave", and it carries no heat.

## 9. Publishing levels and the grey fallback

| Level | What shows | Requires |
|---|---|---|
| Grey | Country outline, "not yet checked", reason | Default |
| Common | Tier, type, blocks 1-3, 5, 7, 8, templated headline | Checks C1 to C4 |
| Full | Adds deep-dive parts of blocks 4 and 6, written headline | Also C5 |

- **C1** Every Eurobarometer cell re-read: the Volume C total column
  matches Volume A within 0.5 points (catches a misread table).
- **C2** All items present in all three waves, with bases.
- **C3** Interval places the country, or it is shown "too noisy" (its
  numbers still pass).
- **C4** Eurostat values re-pulled on build, against a stored copy.
- **C5** Each deep-dive number traces to an EOS finding that passed its
  scope check, with wording, ages, year and comparator. EOS corrected 94
  of 148 findings, numbers mostly right, so a matched number is not a
  pass. **France stays at Common until its pending fixes land.**

Realistic launch: 27 at Common if the data behaves, and Full for at most
Germany, Spain, Italy plus any new rows EOS has checked by the cut-off.
Grey is for failed checks, not for "no deep dive yet".

## 10. Data contract (working shape, per D-030 not a contract yet)

`youth/data/index.json`: recipe commit hash, waves and fieldwork dates,
frozen reference, gate results, mode (`index` or `plan_b`), and per
country: level, tier, type, score, interval, C, B, A marker, grey reason.
`youth/data/countries/<ISO>.json`: the blocks, each number carrying value,
comparator, ages, year, wording, source and confidence.
`youth/validate.py` fails the build on a number with no comparator
claiming abnormality, a missing source, or an em-dash.

## 11. Timeline to 20 November

| Date | Step | Who |
|---|---|---|
| Thu 5 Nov | This spec | Youth |
| Fri 6 Nov | Rulings; G1 on documents, values masked; freeze and push | Kristjan, Youth |
| Sat 7 to Mon 9 | First and only run, gates, index or Plan B known | Youth |
| Tue 10 | JSON and recipe text to design and editor | Youth |
| Tue 10 to Fri 13 | Template built; copy; preview | Design, editor |
| Mon 16 | Cut-off for EOS rows at Full. Later rows ship after launch | EOS, Youth |
| Tue 17 | Preview review; sign-off with no conditions, or sent back | Youth |
| Wed 18 | Publish, verify live, reading the `age` header | Platform |
| Thu 19 | Buffer | |
| Fri 20 | Strikes. Page is up | |

Menu item is discussed only after the first week (D-345). The Plausible
Stats API has been off since at least 4 October and the flood explainer
published 16 October, so its first-week number exists only on the
dashboard and has to be read from there.

Not yet agreed with anyone: design's and editor's capacity for those
dates. Platform also needs a `youth` entry in `SIGNOFF_INPUTS`; byte hash
suits a page whose data moves only on a new wave.

## 12. What we had already seen when this was written

A pre-registration is worth what its author had not yet seen.

- **Not seen by this chat:** any Eurobarometer country-by-age cell for
  these items, or any Flash 585 value. Structure checks printed labels and
  base rows only, every other number masked. Base sizes were seen; they
  say nothing about opinion.
- **Seen:** EOS's country values for life satisfaction, left out,
  depressive symptoms and teen overwhelm, which is one reason none of
  them is in the index. Also near the index: Flash 556 Italy (young
  dissatisfied with democracy, 52 to 46) and a Spanish national survey of
  15-29s (68% little or no satisfaction), plus one search-result title
  about low institutional trust in Cyprus.
- **Generally known:** Kristjan, product and EOS have read five country
  rows and hold priors about which countries are angry. Nobody here is
  blind to Europe, only to these cells.

## 13. Freezing and amending

1. **G1, documents only (done 2026-11-05).** Volume C structure with
   values masked: age bands, bases, item codes in each wave, modes,
   licence, the UK, the validator. No item failed.
2. Commit this file, push, and record the commit hash in the ledger.
3. `youth/build_index.py` refuses to run unless that commit is on the
   remote.
4. Run once. Gates decide (section 5).
5. **Amendments:** a dated section at the end, never an edit above. After
   the run, any change to items, weights, cut-offs or gates is labelled
   post hoc on the page and needs Kristjan. A parser bug fix is not an
   amendment, but it is logged.

### Variable table (filled at G1)

Standard Eurobarometer Volume C, one workbook per country, sheet names:

| Item | Wave 103 | Wave 104 | Wave 105 |
|---|---|---|---|
| Trust national government | QA6_10 | QA6_7 | QA6_10 |
| Trust national parliament | QA6_11 | QA6_8 | QA6_11 |
| Trust political parties | QA6_2 | QA6_1 | QA6_2 |
| Satisfaction with democracy | SD18a | SD18a | SD18a |
| Direction, own country | D73_1 | D73_1 | D73_1 |
| Direction, own life (block 3) | D73_4 | D73_4 | D73_4 |

The mapping is the same in all 27 and the UK. Columns (zero-indexed): 2
total, 5 is 15-24, 8 is 55+, 20 is born 1997 or later. Header row 8, base
row 9, labelled weighted. Answer rows are bilingual, so rows are found by
their English label, never by position. Workbooks are in the `volume C`
archives on the EC open data portal, licence COM_REUSE. The UK has all
items in all three waves, so it is scored against the frozen reference.

## 14. Rulings

D-347: product's rules ratified; open Eurobarometer tables as the source;
freeze without waiting for the anger inventory; gates decide "dropped or
published as it is", with Plan B if dropped. D-348: young means born 1997
or later, with 15-24 as a published side check.

## 15. Amendments

None.

## 16. Result of the run (2026-11-05)

One run, on commit `dfde680`'s recipe. Full output: `youth/data/index.json`.

| Gate | Result | Bar | |
|---|---|---|---|
| V1 coherence | 0.64 | 0.5 | Pass |
| V2 C reliability | 0.92 | 0.7 | Pass |
| V3 B reliability | 0.80 | 0.4 | Pass |
| V4 placement | 20 of 27 | 20 | Pass, exactly at the bar |
| V5 outside check | 0.41 | 0.5 | **Fail** |

**Under section 5 the index is dropped and the page moves to Plan B.** No
threshold, item or validator has been changed after seeing this. V5's
validator was itself swapped for Flash 556 before the run, without seeing
any value; it is a differently worded question, and the failure may say as
much about that choice as about the index. That is a reason to test again
on new data, not to re-read this result. Overriding it would need Kristjan
and a post hoc label on the page (section 13).

Standard errors were scaled by R = 1.41, since waves differ by more than
sampling alone implies. Side checks: 3 tiers change under 15-24 (AT, FR,
HR), 2 if video-interview countries leave the reference (AT, DK).

## 17. Log after the run (2026-11-05)

Kristjan ruled Plan B (D-349). `youth/data/index.json` stays as the audit
record and is not the page's data; the page reads `youth/data/map.json`.
Nothing in sections 2 to 6 changed.

Three logged corrections, none touching the index result:

- **C1 compares weighted counts, not rounded shares.** On shares, 2 of 504
  cells were 1 point out, both Croatia in wave 103: the two published tables
  differ slightly there (base 1,016 against 1,020) and values at x.5 round
  differently. On counts all 504 pass. The small source discrepancy is
  noted, not corrected. **Correction:** commit `b0edab0` said this while C1
  was still failing, because a row offset meant both scripts compared shares
  and not counts. Fixed in the next commit. A deliberately wrong table makes
  the check fail (165 of 504), so it can catch a misread. No share, base or
  index input changed in either fix.
- **Flash 585 Q7a parser bug fixed.** It read a weighted count as a share.
  It was not an index input. V5's Q18.1 was computed from counts, correctly.
- **`youth/data/` carries whole-number display guidance**, since the source
  rounds each wave to a point.
