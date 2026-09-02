<!--
  EDITOR'S PROSE PASS on the science desk's Mediterranean SST piece.
  Draft 2026-09-02. NOT for publish. ONE blocker left, and it is new.

  RESOLVED. The figures now come from `data/med_sst.json` (Science,
  291dad28), so every number here is checkable. The record scope is
  correctly 1991-2026 and the payload's own `record_window.means` says
  so; the piece must never say "the ERA5 record" while computing 36 of
  its 86 years. The rank track is confirmed from the build.

  OPEN, and it is a like-for-like fault the piece explicitly claims not
  to have. **2026's August mean is computed over 28 days; every other
  year uses 31.** The series ends at day 240, 28 August. Late August
  cools, so a mean that stops on the 28th is biased warm against a
  full-month mean, and the record margin is 0.08 on that mixed basis.

  Cut every year to 28 August and the record HOLDS, so nothing here
  collapses:

      1-28 Aug   2026 27.675   2024 27.614   margin 0.060
      1-31 Aug   2026 27.675 (28d)  2024 27.599   margin 0.076

  Two consequences, both in the body below. The margin is six
  hundredths, not eight. And the sentence claiming every year is
  measured the same way was false as computed: the sampling matched,
  the window length did not. Heat solved this with
  `series_to_same_date`; the same fix applies.

  Marked [SCIENCE] where a recut payload changes the wording.
-->

## headline

A warm sea does not make more storms. It loads the ones that come.

## standfirst

The Mediterranean has just had its hottest August since at least 1991.
The gap between a warm sea and cooling air is widest in October.

## body

On 1 April the Mediterranean was the eighth warmest it had been on that
date since 1991. By 1 June it was the warmest, and it has stayed there
ever since. Measured to 28 August it is averaging 27.68 °C, about 1.8 °C
above its 1991-2020 August normal.

The sea was furthest above its own normal on 1 July, at +2.50 °C. **A
record August is the aftermath of something that happened in early
summer.**

**The record is thin.** Measured to the same date, 2024 sits six
hundredths of a degree behind, and a different sea surface product could
order the two the other way round. [SCIENCE: 0.060 on a 28 August cut] The anomaly is not thin. 2026 and 2024 both sit
more than half a degree clear of every other year in the series, and the
five warmest Augusts are 2026, 2024, 2022, 2003 and 2018.

Every year here is sampled the same way, daily at 12:00 UTC over the same
box, and every year is cut to the same calendar day, so this is a
like-for-like comparison rather than a warm year measured one way against
a cool year measured another. [SCIENCE: true once the payload cuts every
year to 28 August; as built, 2026 uses 28 days and the rest use 31]

### Why autumn and not August

The Mediterranean is at its warmest in August. The air above it starts
cooling in September. The gap between the two is widest in autumn, and
that gap is what feeds the region's heaviest rain.

A warmer sea gives a passing weather system three things: more evaporated
water, roughly seven percent more per degree; more latent heat to convert
into intensity; and a less stable air column when cold air arrives on top.

**None of that makes a storm more likely to form. It changes what one can
do if it does.** A record-warm sea does not make an autumn cut-off low
more likely to form. It makes whatever forms capable of dropping more
water.

### Where it lands

Not on the big rivers. Basin-scale flooding needs prolonged moderate rain
on ground that is already wet, and the soil does most of the work: across
2,370 gauges in 33 countries, antecedent soil moisture contributes most to
the smaller and more frequent floods, with rainfall taking over only for
the rare ones.

It lands on small, steep catchments, in a few hours. **Past a certain
rainfall intensity the ground stops mattering at all**, because water
arrives faster than any soil can take it, wet or dry. Valencia, on 29
October 2024, ran frequently above 100 mm an hour. The familiar
explanation for that flood, that three years of drought had left the
ground unable to absorb the rain, does not appear in the peer-reviewed
hydrology of the event, and at those intensities it would not have
mattered if it had.

*The gauge study, the Valencia intensities and the point about the drought
narrative come from this week's literature search and have not been
reproduced by this desk.*

### When

Mid-September to mid-November, with October the peak. Valencia, 29
October 2024. Storm Daniel, early September 2023. Vaia, late October
2018. Genoa's flood events run October into November.

The sea was 27.61 °C on 28 August, the latest reading we hold. Water
gives up heat slowly, so most of that will still be there in October.

### What this is not

**Not an El Niño story.** The teleconnection from El Niño to European
autumn is weak, and nothing in the current event supports a link. The
Mediterranean record stands on its own.

**And not a forecast.** We are describing the state of the sea and what
that state does to rainfall when a system arrives. Whether one arrives,
and where, is weather, and nobody can tell you that in September for
October.
