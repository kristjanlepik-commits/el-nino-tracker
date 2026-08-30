"""Emit the crops channel's validated JSON.

Two artifacts, both requested by design and product on 2026-07-29:

  data/stress_current.json      per-country cropland stress for the
                                latest published dekad, ranked against
                                that country's own record for the SAME
                                dekad since 2001
  data/production_shares.json   each country's share of world production
                                per commodity, with USDA's own vintage
                                stamp, so a condition index can be
                                expressed as a supply number

Design note. The indicator is FPAR *cumulated* z-score over the growing
cycle, so a single dekad's value already encodes the season to date.
That is why one dekad ranked against the same dekad in prior years is
the right comparison and no season-start lookup is needed: the
accumulation is in the number.

Shape follows crops/PAYLOAD_PROPOSAL.md. Every number carries its own
qualifiers as a field per D-051, and a pair below its earliest
publishable dekad is emitted with publishable false rather than omitted,
so the gate is visible on the page.

This reads only from crops/.cache/ and never fetches. Fetching is
pull_asap_indicator.py's job, per the platform contract's rule that a
fetcher must never run inside a publish.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Imported both ways on purpose: this file runs as a script, when
# crops/ is on the path, and is imported as crops.build_data by
# build_history.py and by test harnesses, when the repo root is.
try:
    from crops.asap_reference import crop_areas
except ModuleNotFoundError:  # pragma: no cover
    from asap_reference import crop_areas

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "asap_indicator"
PSD = HERE / ".cache" / "psd"
OUT = HERE / "data"

# WAS 3 UNTIL 2026-08-30. Kristjan's call (D-245): single-unit countries
# can be published.
#
# The old comment read "the meaning gate: fewer and the aggregate is
# noise", and that reasoning was about the AGGREGATE. It does not hold
# for the claim this channel actually makes. Every published claim is
# one unit against its OWN 26 years at the same dekad-of-year, and that
# comparison is exactly as sound for a country ASAP reports whole as for
# one it splits into eighteen. Estonia against 26 Estonias is not a
# weaker statement than Huambo against 26 Huambos.
#
# What a single unit cannot support is the CROSS-REGION reading: where
# inside a country the stress sits, and how many of its regions are at a
# record. Those sentences needed guarding; the country's presence on the
# site did not. The per-place `caveat` field already says so: "this
# country figure IS <region>, which is the country's only crop region.
# There is no weighting choice to make."
#
# Admits 42 countries, 40 with one unit and 2 with two. 123 places
# becomes 165.
MIN_UNITS = 1
BASE_FIRST, BASE_LAST = 2001, 2025

INSTRUMENTS = [
    ("zfparc", "Vegetation, cumulative", "z-score", +1),
    ("zfpar", "Vegetation, current", "z-score", +1),
    ("wsi", "Water satisfaction", "percent", +1),
    ("spi3", "Rainfall, 3-month", "SPI", +1),
    ("sm", "Soil moisture", "m3/m3", +1),
    ("temp", "Temperature", "anomaly C", -1),
]

# slug -> (what the number summarises, that window in dekads, display order)
#
# The observation window of each published index, which is a documented
# property checkable against JRC's definitions rather than a judgement of
# ours. It exists so a page can order these rows WITHOUT ordering them by
# what moved: a row order that tracks observed movement makes the page
# the author of a sequence, and with `driver` unidentified in most places
# we cannot support one.
#
# display_order is window ascending, ties broken by the order above,
# which is arbitrary and is recorded as arbitrary rather than dressed up.
# Note this is NOT the order this file emits instruments in: that one is
# spine-first, so the slowest instrument sits first and the two fastest
# sit second and last. Freezing the emitted order and calling it response
# time would have been a tidy false explanation.
#
# A shorter window moves sooner. That is the whole content of the
# ordering and it is true in a calm week as well as a moving one.
SUMMARISES = {
    "zfpar": ("this dekad", 1, 1),
    "sm": ("this dekad", 1, 2),
    "temp": ("this dekad", 1, 3),
    "spi3": ("the past 3 months", 9, 4),
    "zfparc": ("the season so far, from sowing", 30, 5),
    "wsi": ("the season so far, as a water balance", 30, 6),
}

# Countries where vegetation and the water instruments agree, so the
# stress can be described as water-driven. Elsewhere the honest claim
# stops at "below its own record" with no driver named. This is a CLAIM
# tier, not a validity tier: see FEASIBILITY.md section 6k.
WATER_DRIVEN_MIN = 0.30


def load(slug: str, cid: str):
    f = CACHE / f"{slug}_crop_growing_{cid}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, usecols=["region_id", "region_name", "date", "value"])
    if d.empty:
        return None
    # STRIP THE REGION NAME AT THE DOOR. ASAP's CSVs pad 34 of them,
    # "Ryazanskaya " and "Carlos Ibanez " among them, and this passed
    # the pad straight into the published payload, where it was both a
    # dirty display string and a join key that silently missed. Design
    # hit it joining cropland areas for tls-internal#16: 34 regions in
    # Russia and Chile got no area at all, which is exactly the input
    # that turns a weighted mean back into something else.
    #
    # Fixed here rather than at each join, because every consumer would
    # otherwise have to know to strip, and one of them will not.
    d["region_name"] = d.region_name.str.strip()
    d["dt"] = pd.to_datetime(d.date, format="%Y%m%d")
    d["year"] = d.dt.dt.year
    d["doy"] = (d.dt.dt.month - 1) * 3 + ((d.dt.dt.day - 1) // 10) + 1
    return d


def area_weighted(d, weights: dict, by: list):
    """Mean over regions weighted by ASAP's own cropland area.

    tls-internal#16, open since launch. Every country figure was an
    UNWEIGHTED mean over its regions, so England carried a quarter of
    the UK number while holding 85.6% of its cropland, and Northern
    Ireland carried the same quarter on 0.6%. Over-weighted 42-fold.

    THE WEIGHTS APPLY TO EVERY YEAR, not just the current one. A 2026
    value weighted by cropland and ranked against an unweighted history
    would compare two different quantities, and ranks would move for
    reasons that have nothing to do with weather.

    FALLS BACK TO UNWEIGHTED when the reference data is absent, so a
    checkout without crops/.cache/asap_reference/ builds exactly as it
    did before rather than failing. The payload records which happened;
    a silent fallback would be the worse half of this.

    ZERO-AREA REGIONS GET ZERO WEIGHT, which excludes them, and that is
    disclosed rather than silent. 71 regions carry km2_crop of exactly
    0 while ASAP still publishes crop indicators for them: Suriname has
    6 of 7, Gabon 4 of 5. A region with no cropland in ASAP's own mask
    should not vote on a crop average, but a country losing most of its
    regions to that is a different figure from the one it was, and a
    reader is entitled to know.
    """
    if not weights:
        return d.groupby(by).value.mean(), None
    w = d.region_name.map(weights).fillna(0.0)
    if float(w.sum()) <= 0:
        return d.groupby(by).value.mean(), None
    tmp = d.assign(_w=w, _wv=d.value * w)
    g = tmp.groupby(by)
    num, den = g._wv.sum(), g._w.sum()
    out = (num / den).where(den > 0)
    used = sorted({r for r in d.region_name.unique()
                   if (weights.get(r) or 0) > 0})
    return out, used


def _rank_statement(rank: int, of: int, last: int,
                    worse_is: str = "low") -> str:
    """Value and basis in one string so they cannot be separated.
    Called at country and region level from one place, so the two
    cannot drift apart.

    worse_is is NOT optional in meaning even though it defaults. rank is
    rank-by-worseness, so for temperature rank 1 is the HOTTEST. This
    function previously hardcoded "lowest" and would have published
    Tunisia at +5.34 C as "lowest of 26 observations". The rank was
    right; the sentence built from it dropped the one field that sets
    its direction.
    """
    end = "lowest" if worse_is == "low" else "highest"
    if rank == 1:
        lead = end
    else:
        # 23th is the kind of thing a reader notices and a checker does
        # not, so the suffix is computed rather than assumed to be "th".
        suffix = ("th" if 11 <= rank % 100 <= 13
                  else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th"))
        lead = f"{rank}{suffix} {end}"
    return (f"{lead} of {of} observations for this point in the "
            f"season, {BASE_FIRST}-{last}")


def rank_of(current: float, history: pd.Series, worse_is: int) -> int:
    """1 = most stressed on record."""
    if worse_is > 0:
        return int((history < current).sum()) + 1
    return int((history > current).sum()) + 1


def series_span(series: dict, first: int, last: int) -> dict:
    """What the series SHOULD contain, beside what it does.

    Product's ask across all four measuring channels, and it is a
    data-integrity requirement rather than a drawing device: a consumer
    cannot currently tell a GAP from an END. Twenty-four values in a
    twenty-six-year record and twenty-four values in a twenty-four-year
    record are the same payload, so a renderer stretches what it has to
    fill the frame and silently turns "two years are missing" into "this
    is the whole record".

    `missing` rather than only a count, because the years that are
    absent are strictly more useful than how many, and it lets design
    draw an empty slot where the gap actually falls.

    Emitted as a sibling rather than by wrapping `series` in
    {expected_slots, values}: the live country pages read `series` as a
    year-keyed mapping, and changing its shape would break 41 published
    pages to add metadata beside them.
    """
    have = {int(y) for y in series}
    want = list(range(first, last + 1))
    # Only the VARYING part per datum. first, last and expected_slots
    # are identical on every series in the file, so they are declared
    # once in `series_declaration` at the top level. Repeating three
    # constant fields across 2,122 regions cost 0.3 MB and took the file
    # to 4.99 against a 5.00 guard, which is the same mistake that cost
    # 4.6 MB earlier today. Constant properties belong to the measure.
    return {
        "present": len(have),
        "missing": [y for y in want if y not in have],
    }


def _ordinal(n: int) -> str:
    suffix = ("th" if 11 <= n % 100 <= 13
              else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))
    return f"{n}{suffix}"


def _year_list(years: list) -> str:
    """Empty is a real input and used to raise IndexError, which took
    the whole build down on the HEALTHY case. Callers must still not
    build a sentence around an empty list; see the partition note."""
    ys = [str(y) for y in sorted(years)]
    if not ys:
        return ""
    if len(ys) == 1:
        return ys[0]
    return ", ".join(ys[:-1]) + " and " + ys[-1]


def severity_block(oriented: dict, cur_year: int) -> dict:
    """How far into its own extremes a country's instruments sit, read
    together. The counted measure, regions at their worst, is binary:
    it cannot separate bad from horrible. This can.

    Each instrument is converted to its position within its OWN history
    at this dekad, then the positions are averaged with equal weights.
    Equal weights need no defence, because we are not claiming to know
    which instrument matters more; any weights we invented would be the
    arbitrary part rather than the rigorous one.

    Denominator is n-1, worse than k of the OTHER 25 years, which is
    design's convention and better than the n I first used: a record
    year reads 1.000 rather than 0.962, and it agrees with rank, since
    rank 1 of 26 means beating all 25 others.

    THIS IS COMBINED UNDER D-033, NOT MEASURED. Every input is measured,
    but no source states the average.

    And read `_not_comparable_across_places` before using `value` to
    order countries. It does not do that job.
    """
    if len(oriented) < 2:
        return {
            "available": False,
            "absent": "too_few_instruments",
            "absent_because": "Fewer than two instruments have a full "
                              "record at this point in the season, and "
                              "an average across one instrument is that "
                              "instrument.",
        }

    years = sorted(set.intersection(*[set(s.index) for s in oriented.values()]))
    means = {}
    for y in years:
        pos = []
        for s in oriented.values():
            others = s.drop(index=y)
            pos.append(int((others < s.loc[y]).sum()) / (len(s) - 1))
        # Rounded BEFORE anything is ranked off it, deliberately. Each
        # position is k/25, so a mean over k instruments can only land
        # on a multiple of 1/(25k), at least 0.0067. Rounding to 3dp
        # therefore cannot merge two genuinely different years, and it
        # does stop two arithmetically EQUAL years differing in the
        # last bit of a float. Ranking the raw floats made Chad 3rd or
        # 4th depending on summation order.
        means[int(y)] = round(float(np.mean(pos)), 3)

    cur = means.get(cur_year)
    if cur is None:
        return {
            "available": False,
            "absent": "no_current_value",
            "absent_because": "No instrument has reported for this "
                              "dekad yet.",
        }
    prior = [v for y, v in means.items() if y != cur_year]
    rank = sum(1 for v in prior if v > cur) + 1
    of = len(prior) + 1

    # Ties are not an edge case here, they are a quarter of the page.
    # The measure lands on multiples of 1/125, so two years collide
    # often: 29 of 123 places on 2026-07-11, three of them at rank 1.
    # "The most stressed of 26 observations" is a strict-maximum claim,
    # and for Ethiopia 2002 sits at exactly the same value. Competition
    # ranking keeps the rank honest; the word "joint" and the year keep
    # the sentence honest. Emitted as a field as well, so a renderer
    # can show the tie without parsing the sentence.
    tied = sorted(int(y) for y, v in means.items()
                  if y != cur_year and v == cur)
    lead = ("most stressed" if rank == 1
            else f"{_ordinal(rank)} most stressed")
    lead = f"The {'joint ' if tied else ''}{lead}"

    # The spread of a country's own 26 values, which is what makes the
    # value un-comparable across places. It is set almost entirely by
    # how far this country's instruments move together: across the 123
    # reported places, co-movement against spread is r = 0.97. Where
    # they co-move, extreme averages are the ordinary shape of a bad
    # year; where they do not, an extreme average is unprecedented.
    # Emitted because it is the basis for the qualifier below, the same
    # way `basis` is emitted beside a rank.
    spread = round(float(np.std(list(means.values()))), 3)

    return {
        "available": True,
        "value": cur,
        "rank": rank,
        "of": of,
        "worse_is": "high",
        "series": means,
        "series_span": series_span(means, BASE_FIRST, cur_year),
        "spread": spread,
        "tied_with": tied,
        # The place's OWN median, emitted rather than left to be looked
        # up. Three times in one day someone reached for a fixed 0.5
        # instead: 0.5 is the mean of every place's series BY
        # CONSTRUCTION, so it is a property of the method and not of
        # the place, and quoting it invites reading 0.584 as "17% above
        # normal" when the observed range here is 0.392 to 0.640. A
        # stated constant is easier to reach for than a per-place
        # lookup, so the fix is the field, not more care.
        "own_median": round(float(np.median(list(means.values()))), 3),
        "instruments_used": sorted(oriented),
        "instruments_possible": len(INSTRUMENTS),
        "statement": (f"{lead} of {of} observations for this point in "
                      f"the season, {BASE_FIRST}-{cur_year}, across "
                      f"{len(oriented)} instruments read together"
                      + (f", level with {_year_list(tied)}" if tied else "")),
        # IS_NOT, at product's request after four
        # consumer-reaches-for-the-wrong-field defects in two days, one
        # of them mine reaching for my own. A field that says what it is
        # NOT, and points at the fields answering the questions it does
        # not answer, is a structural fix where renaming is not
        # available.
        #
        # This one exists because my own guidance here was incomplete
        # and design followed it correctly. `not_comparable_across_places`
        # says the value cannot order countries and that "the rank is the
        # comparable figure". True, and it omits that the rank has 26
        # levels and about one country in seven sits on level 1, so
        # ordering by it produces a large tied block broken by payload
        # order. Telling somebody which of two fields to order by, when
        # neither orders well, is worse than saying neither does.
        # SATURATION_RATE is filled by _fill_saturation_rate() once every
        # place exists, because the figure is a property of the whole
        # published set and is unknowable here. It was typed as "roughly
        # one country in seven" and went stale the moment the channel grew
        # from 123 places to 165.
        "is_not": "a cross-place ordering. The value places a country "
                  "against ITSELF, and the rank saturates: SATURATION_RATE "
                  "sit at rank 1, so sorting on it "
                  "yields a large tied block broken by payload order. "
                  "For how much of a country is abnormal, use "
                  "`regions_at_record`, which is a proportion and "
                  "therefore comparable between places. For how fast, "
                  "use `rate`.",
        "method": (f"Each of {len(oriented)} instruments placed within "
                   f"its own {of - 1} prior years at this dekad, then "
                   f"averaged with equal weights. No instrument is "
                   f"weighted above another."),
        "evidence_basis": "combined",
        "authorship": "tls_built",
        "qualifiers": [
            {
                "kind": "combined_not_measured",
                "text": "Every input is measured against its own "
                        "record, but no source publishes this average. "
                        "It is our combination, not an observation.",
            },
            {
                "kind": "not_comparable_across_places",
                "text": (f"This value places the country against "
                         f"itself, so it does not rank countries "
                         f"against each other. Its year-to-year spread "
                         f"here is {spread}, and that spread differs by "
                         f"place, so a higher value elsewhere can be a "
                         f"less unusual year than this one. The rank is "
                         f"the comparable figure."),
            },
            {
                "kind": "reading_not_forecast",
                "text": "A reading of conditions to date. It carries no "
                        "statement about the rest of the season.",
            },
        ],
    }


# The two named buckets the divergence claim is made between. They do
# NOT partition the five: "Vegetation, current" and "Water
# satisfaction" sit in neither, being an instantaneous crop state and a
# modelled water balance rather than either a season-cumulative crop
# outcome or pure meteorology. Emitted by name, and the leftovers
# emitted too, because a page asserting that two things diverged is
# unverifiable if the reader cannot see what was put in each.
BUCKETS = {
    "crop_outcome": ["Vegetation, cumulative"],
    "meteorology": ["Rainfall, 3-month", "Temperature"],
}


def _detrend(ser: pd.Series) -> pd.Series:
    """Least-squares linear trend removed, keeping the index.

    Not optional here. Temperature worsens in 67 of the 123 reported
    places and improves in NONE, so a percentile against a place's own
    history puts recent years high by construction. Trap 16.
    """
    x = np.asarray(sorted(ser.index), dtype=float)
    y = np.asarray([ser.loc[i] for i in sorted(ser.index)], dtype=float)
    slope, intercept, *_ = stats.linregress(x, y)
    return pd.Series(y - (slope * x + intercept),
                     index=[int(v) for v in x])


def _percentiles(oriented: dict) -> dict:
    """Per-year mean percentile over whatever instruments are passed.
    Same construction as severity_block, called from one place so the
    global figures and the per-place ones cannot drift apart.
    """
    years = sorted(set.intersection(*[set(s.index) for s in oriented.values()]))
    out = {}
    for y in years:
        pos = []
        for s in oriented.values():
            others = s.drop(index=y)
            pos.append(int((others < s.loc[y]).sum()) / (len(s) - 1))
        out[int(y)] = round(float(np.mean(pos)), 3)
    return out


# Dekads of lookback for the rate. FIXED IN ADVANCE, and the reason is
# recorded because it is the difference between a finding and an
# overfit: 4 is what the England case used before any global number had
# been computed. The 3-dekad window scores better on the baseline (0 of
# 25 prior years at or above, against 1 of 25 here), and choosing it
# after seeing that is exactly the sweep this channel bans. Sensitivity
# across 1 to 8 dekads is recorded in FEASIBILITY 13d.
RATE_BACK = 4


def rate_legend() -> dict:
    """Everything about the rate that is true of the MEASURE rather than
    of any one place, emitted once.

    D-051 says a qualifier is a property of the datum, never of the
    layout, and this does not breach it. The distinction that matters is
    whether the text VARIES: `absent_because` differs per datum and the
    severity comparability qualifier interpolates each place's own
    spread, so both stay bound to their datum. These two strings are
    byte-identical on every rate block ever emitted, which makes them a
    property of the measure. Repeating them 2,122 times cost 1.7 MB and
    told a reader nothing extra.

    Country-level rate blocks still carry the full text, because that is
    where the headline claim is made and 123 copies are free.
    """
    return {
        "measures": "change in cumulative FPAR z-score over the "
                    f"{RATE_BACK} dekads ending at the reported one",
        "window_dekads": RATE_BACK,
        "worse_is": "low",
        "applies_to": "every `rate` block in this file, at country and "
                      "region level alike",
        "method": (f"Cumulative FPAR z-score now minus the same "
                   f"indicator {RATE_BACK} dekads earlier, ranked "
                   f"against the same window in each prior year. A rate "
                   f"of change, not a level: a place can be ordinary "
                   f"and falling faster than in any year on record."),
        "qualifiers": _RATE_QUALIFIERS,
        "_start_control_note": (
            "Every rate block carries `_start_control`. `holds` is true "
            "when the place is still rank 1 once the level it fell from "
            "is controlled for. NINE of the twenty rank-1 places on "
            "2026-07-11 do not hold, so roughly half of rate-based "
            "leads are inflated by construction. `adjusted_rank` is a "
            "FITTED quantity and must never reach a reader: publish "
            "`start_value` and `start_rank`, which are measured. The "
            "underscore prefix marks the whole block as pipeline "
            "guidance that never renders."),
    }


_RATE_QUALIFIERS = [
    {
        "kind": "rate_not_level",
        "text": "This ranks how fast the reading is moving, not how bad "
                "it is. A steep fall from a good starting point can "
                "still leave a place in ordinary condition, and the "
                "level field says which.",
    },
    {
        "kind": "canopy_not_cause",
        "text": "ASAP observes the crop canopy, not what stressed it. "
                "Heat, drought, disease and late planting are not "
                "separable in this measurement.",
    },
]


def _licensed_fall_claim(rank: int, of: int, start_rank, holds,
                         rose: bool = False) -> str:
    """The short rate sentence that is safe to print, in every case.

    Built only from MEASURED quantities, the raw rank and the start
    rank. Never from the fitted residual: `_start_control.adjusted_rank`
    is a diagnostic, and a fitted number on a public page is original
    modelling, which this project does not do.

    When the control fails, the honest short form is not a different
    rank. It is the same rank with the reason it does not stand, bound
    into the same sentence so the two cannot be separated by a layout.
    """
    # A RISE IS NOT A SHALLOW FALL. `rank` is a position in a list
    # ordered by fall steepness, so a place that ROSE sits near the
    # bottom of it and renders "25th steepest fall of 26": a true rank
    # carrying a false verb.
    #
    # This was invisible for as long as every pinned country was
    # deteriorating, and appeared the moment Poland was pinned as a
    # counter-example on 2026-08-30. Its row said Poland fell, which is
    # the opposite of the reason it is on the page. 42 of 123 countries
    # and 861 of 2,066 region rate claims were affected.
    #
    # The rank is kept, because it is measured and it is the same
    # number. Only the verb changes, and the start level is still bound
    # into the sentence: a rise from a low start is regression toward
    # the mean exactly as a fall from a high one is.
    if rose:
        base = (f"rose over this window, ranking {_ordinal(rank)} of {of} "
                f"by fall steepness")
        if start_rank:
            base += (f", from the {_ordinal(start_rank)} highest starting "
                     f"level of those {of}")
        return base
    base = f"{_ordinal(rank)} steepest fall of {of}"
    if not start_rank or holds:
        return base
    return (f"{base}, but from the {_ordinal(start_rank)} highest "
            f"starting level of those {of}, so it is not a record fall "
            f"once that is accounted for")


def rate_block(pv: pd.DataFrame, doy: int, cur_year: int,
               full: bool = True) -> dict:
    """How fast a place is deteriorating, ranked against its own record.

    The level answers "how bad is it", and cumulative FPAR answers that
    while INTEGRATING FROM SEASON START, so it dilutes exactly the thing
    a reader most needs to know: a fast deterioration in progress.
    England read +0.150 on 11 July 2026, an ordinary level, after the
    steepest 1 June to 11 July fall in its 26-year record. The level
    said nothing was happening.

    So "conditions are ordinary" is least reliable precisely when a
    situation is deteriorating fastest, which is the one circumstance
    where being wrong costs most. This is the field that fixes that.

    Differencing removes a linear trend by construction, which is why
    this survives the detrend that halved the level count: only 25 of
    122 places carry any residual trend in the rate, against 67 of 123
    warming in the temperature level. Trap 16 barely bites here.
    """
    a, b = doy - RATE_BACK, doy
    if pv is None or a < 1:
        return {
            "available": False,
            "absent": "window_precedes_season",
            "absent_because": f"The {RATE_BACK} dekads before this one "
                              f"fall outside the season, and a "
                              f"cumulative indicator does not carry "
                              f"across a season boundary.",
        }
    if a not in pv.columns or b not in pv.columns:
        return {
            "available": False,
            "absent": "window_not_reported",
            "absent_because": f"One of the two dekads bounding the "
                              f"{RATE_BACK}-dekad window has not been "
                              f"reported here.",
        }
    ch = (pv[b] - pv[a]).dropna()
    ch = ch[(ch.index >= BASE_FIRST) & (ch.index <= cur_year)]
    if cur_year not in ch.index or len(ch) < 20:
        return {
            "available": False,
            "absent": "too_few_comparable_years",
            "absent_because": f"Fewer than 20 comparable years of "
                              f"{RATE_BACK}-dekad change at this dekad.",
        }
    ch = ch.round(3)
    cur = float(ch.loc[cur_year])
    prior = ch.drop(index=cur_year)
    rank = int((prior < cur).sum()) + 1
    of = len(ch)
    tied = sorted(int(y) for y in prior.index[prior == cur])
    # Same defect as _licensed_fall_claim above, in the long-form
    # sentence. Both are fixed together because a page that renders one
    # of them beside the other would otherwise disagree with itself.
    rose = cur > 0
    if rose:
        lead = (f"A {'joint ' if tied else ''}rise, ranking "
                f"{_ordinal(rank)} of {of} by fall steepness")
    else:
        _l = ("steepest fall" if rank == 1
              else f"{_ordinal(rank)} steepest fall")
        lead = f"The {'joint ' if tied else ''}{_l}"

    # The level the fall STARTED from, emitted beside the fall itself.
    # A high June level predicts a steeper subsequent fall: median
    # correlation -0.384 across the 122 places, -0.429 in England.
    # England is rank 1 on the raw change by a margin of 0.025 and rank
    # 2 once the starting level is controlled for, because it began the
    # summer at its third-highest June value on record. A page showing
    # "steepest fall on record" without the base it fell from is making
    # a claim the data supports less than it appears to.
    #
    # Emitted MEASURED, not modelled: the start value and its rank, not
    # a regression-adjusted rank. The adjustment is a fitted quantity
    # and closer to original modelling than this channel goes, so it
    # stays a diagnostic run before claims ship rather than a field.
    start = pv[a].dropna()
    start = start[(start.index >= BASE_FIRST) & (start.index <= cur_year)]
    start_value = start_rank = None
    if cur_year in start.index and len(start) >= 20:
        sv = float(start.loc[cur_year])
        start_value = round(sv, 3)
        # 1 = highest starting level, since that is the direction that
        # flatters a subsequent fall.
        start_rank = int((start.drop(index=cur_year) > sv).sum()) + 1

    # The start-level control, as an UNDERSCORE-PREFIXED DIAGNOSTIC.
    # Product asked for "holds rank 1 after the control" in the payload
    # rather than in a message, and they are right that a figure passed
    # around in chat gets handled four different ways. But the adjusted
    # rank is FITTED, and a fitted number on a page is original
    # modelling, which the build philosophy forbids outright.
    #
    # The underscore prefix is this repo's existing answer to exactly
    # that: pipeline guidance that never renders. So an editor can see
    # which leads survive, and no renderer can put the number in front
    # of a reader. D-051 is untouched, because this qualifies our
    # CONFIDENCE in a claim rather than qualifying the claim itself.
    control = None
    if start_rank is not None:
        idx = [y for y in ch.index if y in start.index]
        if len(idx) >= 20:
            cs, cc = start.loc[idx], ch.loc[idx]
            slope, icept, *_ = stats.linregress(cs.values, cc.values)
            res = cc - (slope * cs + icept)
            adj = int((res.drop(index=cur_year) < res.loc[cur_year]).sum()) + 1
            nxt = float(ch.drop(index=cur_year).min())
            control = {
                "holds": bool(adj == rank),
                "adjusted_rank": adj,
                "gap_to_next_year": round(cur - nxt, 3),
                "start_change_corr": round(
                    float(np.corrcoef(cs.values, cc.values)[0, 1]), 3),
            }
            # The warning text lives ONCE in rate_legend, not on all
            # 2,228 blocks. Putting it on each one added 0.74 MB and
            # took the file back over the size guard within an hour of
            # my having removed 4.6 MB of exactly this. A constant
            # string is a property of the measure; that rule did not
            # stop applying because the string was a warning.

    block = {
        "available": True,
        "value": round(cur, 3),
        "start_value": start_value,
        "start_rank": start_rank,
        "start_of": len(start) if start_rank else None,
        "_start_control": control,
        # PUBLIC, because design needed this and had to reach into the
        # private dict to get it. `_start_control` is a diagnostic and
        # underscore-prefixed means it never renders, yet the pinned row
        # was reading `_start_control.adjusted_rank` and printing it.
        # That is a FITTED number on a page, which check_rate_lead.py
        # calls never publishable and which the aggregator posture
        # forbids: we cite, we do not author.
        #
        # Design were not wrong to do it. Printing rank 1 for a place
        # whose control fails publishes the exact figure the control
        # exists to discount, so with only a raw rank and a private
        # diagnostic they had to choose between two bad options. The
        # missing thing was a publishable form, and that is mine.
        #
        # So: `control_holds` says whether the rank stands on its own,
        # and `licensed_claim` is the short sentence that is safe to
        # print either way. Both are built from MEASURED quantities,
        # rank and start_rank, never from the fit.
        "control_holds": bool(control.get("holds")),
        "licensed_claim": _licensed_fall_claim(rank, of, start_rank,
                                               control.get("holds"), rose),
        "start_means": "the level this fall began from, ranked 1 = "
                       "highest on record. A steep fall from a high "
                       "start is partly regression toward the mean.",
        "window_dekads": RATE_BACK,
        "rank": rank,
        "of": of,
        "worse_is": "low",
        "tied_with": tied,
        # The start is bound into the sentence, ALWAYS, not above a
        # threshold. "The steepest fall of 26 observations" read alone
        # is the claim that misleads, and a threshold would drop the
        # qualifier on exactly the borderline cases where a reader most
        # needs it. Stating it every time costs a clause and cannot be
        # dropped in layout, which is the same reason `basis` is bound
        # into every rank statement on this channel.
        "statement": (f"{lead} over {RATE_BACK} dekads of {of} "
                      f"observations for this point in the season, "
                      f"{BASE_FIRST}-{cur_year}"
                      + (f", level with {_year_list(tied)}" if tied else "")
                      + (", from the "
                         + ("highest" if start_rank == 1
                            else f"{_ordinal(start_rank)} highest")
                         + f" starting level of those {len(start)}"
                         if start_rank else "")),
        "authorship": "tls_built",
        "evidence_basis": "measured",
    }
    if full:
        block["measures"] = rate_legend()["measures"]
        block["method"] = rate_legend()["method"]
        block["qualifiers"] = _RATE_QUALIFIERS
        block["series"] = {int(y): float(v) for y, v in ch.items()}
    else:
        # Region rows carry the claim, its basis and the diagnostic, and
        # NOTHING that is identical on every row. Third time today I
        # have had to strip constants from a per-datum block: they are
        # cheap to add, invisible in review, and 2,107 regions turns
        # 250 bytes into 0.7 MB against a 5 MB guard.
        #
        # `available` IS NOT IN THIS LIST AND MUST NOT GO BACK IN.
        # It was, and it cost the channel its best story. It is True on
        # every block that carries a value, so it looks exactly like the
        # constants above. It is not one: an absent rate emits
        # `available: False` with a reason, so a consumer tests
        # `available` to tell a real rate from a missing one. Stripping
        # it made a present rate indistinguishable from an absent one.
        #
        # What that did: design's pinned row gates on
        # `r.get("available") and r.get("rank")`. England's region rate
        # carried rank 1, the steepest fall in its 26 year record,
        # holding under every control, and rendered as "England within
        # its own normal range" because the boolean was missing. The one
        # country in the news, told to the reader as a null.
        #
        # THE TEST FOR A CONSTANT IS NOT "DOES THE VALUE VARY". It is
        # "does any consumer branch on it". A field whose value never
        # changes can still be load-bearing, because what the consumer
        # reads is its PRESENCE.
        for k in ("window_dekads", "worse_is", "authorship",
                  "evidence_basis", "start_means", "start_of"):
            block.pop(k, None)
        # The series stays dropped: nothing renders a region rate
        # history, and emitting a second per-region series contradicted
        # the rule this file already states about vegetation-only
        # series. One rebuild away if a region page ever wants it.

    return block


def _global_bucket(per_place: list, names: list, cur_year: int,
                   label: str) -> dict:
    """Median across places of the mean percentile over `names`, per
    year, raw and detrended.

    BOTH forms are emitted, never one. Detrending moves the two headline
    figures in OPPOSITE directions and by different amounts, so either
    alone is a different claim about the world:

      meteorology    rank  1 of 26 raw  ->  rank 3 of 26 detrended
      crop outcome   rank 20 of 26 raw  ->  rank 8 of 26 detrended

    Raw says the weather is unprecedented and the crops are better than
    typical. Detrended says the weather is high and the crops are
    mildly bad. Both are true statements about different questions:
    raw is what a season actually delivered, detrended is that season
    against the trend it sits on. Emitting one would let a page pick
    the answer without the reader seeing there was a choice.
    """
    out = {"instruments": list(names), "label": label}
    for mode in ("raw", "detrended"):
        per_year = {}
        for oriented in per_place:
            use = {k: v for k, v in oriented.items() if k in names}
            if len(use) != len(names):
                continue
            if mode == "detrended":
                use = {k: _detrend(v) for k, v in use.items()}
            for y, v in _percentiles(use).items():
                per_year.setdefault(y, []).append(v)
        if not per_year:
            continue
        med = {y: round(float(np.median(v)), 3)
               for y, v in sorted(per_year.items())}
        cur = med.get(cur_year)
        if cur is None:
            continue
        prior = [v for y, v in med.items() if y != cur_year]
        rank = sum(1 for v in prior if v > cur) + 1
        of = len(prior) + 1
        tied = sorted(y for y, v in med.items()
                      if y != cur_year and v == cur)
        lead = ("most stressed" if rank == 1
                else f"{_ordinal(rank)} most stressed")
        lead = f"The {'joint ' if tied else ''}{lead}"
        out[mode] = {
            "value": cur,
            "rank": rank,
            "of": of,
            "tied_with": tied,
            "series": med,
            "places_counted": len(per_year[cur_year]),
            "statement": (
                f"{lead} of {of} observations for this point in the "
                f"season, {BASE_FIRST}-{cur_year}, taken as the median "
                f"across {len(per_year[cur_year])} places of "
                f"{label.lower()}"
                + (", " + ("on instruments with their linear trend "
                           "removed" if mode == "detrended"
                           else "on the instruments as published"))
                + (f", level with {_year_list(tied)}" if tied else "")),
        }
    return out


def build_global(per_place: list, cur_year: int) -> dict:
    """The page-level frame: how the typical place is doing, and the
    split the divergence claim is made across.

    The median across places is a legitimate aggregate and the proof is
    structural rather than empirical: each instrument's leave-one-out
    percentiles across the record are a permutation of {0/25 ... 25/25},
    so every place's own series averages exactly 0.5. Co-movement
    between a place's instruments sets the SPREAD of its values and
    never their centre, so it cannot tilt any single year's median.
    """
    assigned = {n for names in BUCKETS.values() for n in names}
    # Whatever every place actually carries, rather than the full
    # INSTRUMENTS list: soil moisture publishes a dekad behind and is
    # absent from all 123 today, and a bucket must be built from what
    # is present or its member list describes a different number.
    common = sorted(set.intersection(*[set(o) for o in per_place]))
    # LABEL COMPUTED, NEVER ASSERTED. `common` is the strict
    # intersection across places, so one place missing an instrument
    # drops it for everyone. On 2026-07-11 that left five; it can leave
    # three. Hardcoding "all five" would have published a statement
    # saying five while averaging three, which the crash below was
    # hiding. Same defect as every other one this week: correct
    # arithmetic wearing a false description.
    n = len(common)
    word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six"}.get(n, str(n))
    buckets = {
        "all_available": _global_bucket(
            per_place, common, cur_year,
            f"all {word} instruments available everywhere, read together"),
    }
    # The old key kept as an alias, deliberately. templates/crops_index.py
    # iterates ["all_five", ...] and CONTINUES past a missing key, so a
    # straight rename would have silently dropped a row from the live
    # table with nothing saying so. Same precedent as notable and
    # selected_for_display: emit both across a switch, migrate, remove.
    buckets["all_five"] = dict(buckets["all_available"],
                               _deprecated="renamed to all_available on "
                                           "2026-08-07 because it is not "
                                           "always five. Read that key; "
                                           "this one goes after design "
                                           "has migrated.")
    for key, names in BUCKETS.items():
        buckets[key] = _global_bucket(
            per_place, names, cur_year,
            "the season-cumulative crop outcome" if key == "crop_outcome"
            else "the purely meteorological instruments")

    leftover = sorted(set(common) - assigned)
    return {
        "measures": "median across reported places of each place's own "
                    "percentile position, per year, at this dekad",
        "buckets": buckets,
        "unassigned_instruments": leftover,
        # Emitted ONLY when it is true. This sentence explains why the
        # two named groups do not cover everything, and when they DO
        # cover everything it described a state we were not in, then
        # crashed trying to name the empty set. A note that only makes
        # sense in a state you are not in does not belong in the payload
        # when you are not in it.
        "buckets_do_not_partition": (
            "crop_outcome and meteorology are named groups, not a "
            f"partition: {_year_list(leftover)} "
            + ("belongs" if len(leftover) == 1 else "belong")
            + " to neither. A page claiming the two diverged has to "
              "show what went into each."
            if leftover else None),
        "buckets_partition_everything": not leftover,
        "qualifiers": [
            {
                "kind": "trend_sensitive",
                "text": "Detrending moves these two figures in opposite "
                        "directions, so raw and detrended are both "
                        "emitted and neither stands alone. Temperature "
                        "worsens almost everywhere and cropland greens, "
                        "so the raw gap between them is widened by two "
                        "secular trends rather than by this season "
                        "alone.",
            },
            {
                "kind": "no_theoretical_null",
                "text": "0.5 is the mean of every place's own series by "
                        "construction and is not a normal to compare "
                        "against. Use the observed range across the "
                        "record, which is what the series carries.",
            },
            {
                "kind": "season_incomplete",
                "text": "The crop outcome instrument is cumulative over "
                        "the growing cycle, so at this dekad it "
                        "integrates a season that has not finished. It "
                        "is a reading of conditions to date and carries "
                        "no statement about the rest of the season.",
            },
        ],
    }


SEASON_STARTS = json.loads(
    (HERE / "season_starts.json").read_text(encoding="utf-8")
)["starts"] if (HERE / "season_starts.json").exists() else {}


# Soil moisture publishes one dekad behind the others, every dekad, on
# purpose. That is the ONLY instrument allowed to lag, and it is allowed
# to lag by exactly one publication.
# slug -> the most dekads behind the spine that is NORMAL for it.
#
# Soil moisture publishes behind the others, so requiring equality would
# block every build. But an UNBOUNDED exemption cannot tell a normal lag
# from a stalled product. Measured 2026-08-14: sm sat THREE dekads
# (about 30 days) behind the spine, having not advanced since 6 August
# while the spine advanced twice, and nothing reported it because the
# exemption was total. FRESHNESS.md still documented that lag as one.
#
# Same shape as the ASAP staleness rule in CLAUDE.md: an absolute bound,
# never an open-ended allowance. Exceeding it is REPORTED, not fatal,
# because sm is emitted absent rather than averaged into severity, so a
# stall degrades the composite from six instruments to five rather than
# corrupting it. A wrong number would justify refusing; a stated absence
# justifies saying how big it is.
LAGS_BY_DESIGN = {"sm": 1}


def _newest_ordinal(df) -> int:
    """Absolute dekad number for a loaded panel, so lags subtract.

    36 dekads a year on the 1st, 11th and 21st. Without this a lag has
    to be eyeballed from two dates, which is how "a dekad behind" stayed
    in the docs while the real gap grew to three.
    """
    if df is None or len(df) == 0:
        return None
    y = int(df.year.max())
    dy = int(df.loc[df.year == y, "doy"].max())
    return y * 36 + dy


def newest_dekad(slug: str, cid: str):
    """The MAXIMUM date in a cached file, or None if it holds no rows.

    Not the last line. The export is ordered by region, not by date, and
    a region whose instrument legitimately stops early puts an old date
    at the end of the file. Egypt is the case: SPI is undefined in
    hyper-arid regions outside the winter dekads, so Luxor's last row is
    March while the file as a whole reaches July. Reading the last line
    reported Egypt as four months stale and would have blocked every
    build with a false positive.
    """
    f = CACHE / f"{slug}_crop_growing_{cid}.csv"
    if not f.exists():
        return None
    best = None
    with f.open(encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            parts = line.split(",")
            if len(parts) > 10:
                d = parts[10].strip()
                if d and (best is None or d > best):
                    best = d
    return best


def check_instruments_agree(catalogue: dict) -> list:
    """Every instrument for a place must be read at the same dekad.

    WHY THIS REFUSES RATHER THAN WARNS. A partial pull does not produce
    a wrong number here, it produces a MISSING one: the instrument has
    no value at the newer dekad, so it is emitted absent with
    "has not reported for this dekad yet". That sentence is a claim
    about ASAP, and when the cause is our own incomplete fetch it is
    FALSE. The page would blame the source for our gap, which is the
    same defect as the skipped-reason conflation and reaches a reader
    the same way.

    It also silently guts the composite: five instruments a dekad behind
    leaves severity with one, so severity disappears and the page looks
    like an ASAP outage.

    Requested by platform after crops_refresh.yml was found pulling only
    zfparc, which would have put every country in this state every
    dekad. Their fix protects against the mistake they made; this
    protects against the next one nobody has made yet.

    Cache only. A fetcher must never run inside a publish, so this
    compares instruments against each other rather than against ASAP.
    """
    bad = []
    for cid, name in catalogue.items():
        spine = newest_dekad("zfparc", cid)
        if spine is None:
            continue                     # no crop data here at all
        for slug, label, _unit, _w in INSTRUMENTS:
            if slug == "zfparc" or slug in LAGS_BY_DESIGN:
                continue
            got = newest_dekad(slug, cid)
            if got is None:
                continue                 # absent everywhere, stated already
            if got < spine:
                bad.append({"place": name, "instrument": label,
                            "holds": got, "spine_holds": spine})
    return bad


def _ord_from_label(d) -> int:
    """Absolute dekad number from a YYYYMMDD dekad label."""
    d = int(d)
    y, m, day = d // 10000, (d // 100) % 100, d % 100
    return y * 36 + (m - 1) * 3 + min((day - 1) // 10, 2) + 1


def check_expected_lags(catalogue: dict) -> list:
    """Instruments exempted by LAGS_BY_DESIGN that exceed their bound.

    WARNS, it does not refuse, and the split is deliberate.
    check_instruments_agree refuses because an instrument silently a
    dekad behind guts the composite while the page still looks healthy.
    Here the instrument is already emitted absent with its reason, so a
    stall costs the composite one input and states that it did. Refusing
    would take the whole channel down for a source problem we cannot fix
    and have already disclosed.

    What it catches is the thing an unbounded exemption cannot: a
    product that has stopped rather than one that is merely behind.
    """
    over = []
    for cid, name in catalogue.items():
        spine = newest_dekad("zfparc", cid)
        if spine is None:
            continue
        for slug, label, _unit, _w in INSTRUMENTS:
            allowed = LAGS_BY_DESIGN.get(slug)
            if allowed is None:
                continue
            got = newest_dekad(slug, cid)
            if got is None:
                continue
            behind = _ord_from_label(spine) - _ord_from_label(got)
            if behind > allowed:
                over.append({"place": name, "instrument": label,
                             "holds": got, "spine_holds": spine,
                             "dekads_behind": behind, "expected": allowed})
    return over


def aggregate_weighting(regions: list, published_rank: int,
                        of: int, weights: dict = None) -> dict:
    """State how the country figure is built. Do NOT claim to measure
    how wrong it is, because that cannot be measured from what we hold.

    Every country value here is an UNWEIGHTED mean across its GAUL1
    regions, so each region counts equally regardless of cropland area.
    Where regions are very unequal that can invert the answer: the UK
    publishes rank 18 of 26 while England, nearly all of its cropland,
    is rank 12 and the three small-crop regions are 19, 20 and 21.

    TWO SENSITIVITY MEASURES WERE BUILT AND BOTH FAILED. Recording them
    so the next person does not rebuild either.

      Extreme reweighting, the rank under 100% weight on one region:
      fires on 62 of 123 countries and MISSES THE UK. With 80 regions
      some region is always rank 1 and some always 26, so it measures
      region count rather than risk.

      Leave-one-region-out: discriminates properly, UK swings 3 and
      Turkiye 0, but UNDERSTATES. Dropping to three equal regions never
      approaches England's real share, so it reports 3 ranks of exposure
      where the true error is about 6.

    A flag that fires everywhere is useless and a flag that understates
    is worse than none, because it looks like reassurance. So this
    emits the METHOD, which is true, and the region count, which is a
    real if crude measure of how much one region can carry. It does not
    emit a sensitivity score. Fixing it needs crop area per GAUL1 unit,
    which the ASAP export does not return and gaul_level=0 refuses with
    HTTP 400. Tracked as tls-internal#16.
    """
    n = len([r for r in regions if isinstance(r.get("rank"), int)])
    _w = {r["region"]: weights[r["region"]]
          for r in regions
          if weights and (weights.get(r.get("region")) or 0) > 0} if weights else {}
    # WHICH region carries the share, not just how much. Design asked:
    # one_region_carries was a bare number, so a page printing "England
    # holds 86%" would take the entity from a chat message and the
    # number from a field. Now both come from the field.
    _largest_name = (max(_w, key=_w.get) if _w else None)
    _nzero = (sum(1 for r in regions
                  if (weights or {}).get(r.get("region"), 0) <= 0)
              if weights else 0)
    return {
        # WAS "unweighted mean across regions, NOT area-weighted", and
        # that sentence became false the moment weighting shipped. A
        # field describing the method has to change when the method
        # does; this is the defect class the channel keeps finding
        # elsewhere.
        "method": ("mean across regions weighted by ASAP's own cropland "
                   "area, km2_crop" if _w else
                   "unweighted mean across regions: the cropland "
                   "reference data was not present at build time"),
        "area_weighted": bool(_w),
        "largest_region": _largest_name,
        "regions_averaged": n,
        # The REAL share the largest region carries, not 1/n. For the UK
        # that is England at 0.856 where the unweighted answer said
        # 0.25, understating it more than threefold.
        "one_region_carries": (round(max(_w.values()) / sum(_w.values()), 3)
                               if _w and sum(_w.values()) > 0
                               else (round(1 / n, 3) if n else None)),
        # Regions ASAP publishes crop indicators for whose crop-mask
        # area is exactly zero, so weighting gives them no vote.
        # Disclosed rather than silent: Suriname loses 6 of 7 this way,
        # Gabon 4 of 5, and that is a different figure from the one it
        # was.
        "regions_zero_area": sum(
            1 for r in regions
            if (weights or {}).get(r.get("region"), 0) <= 0) if weights else 0,
        "published_rank": published_rank,
        "of": of,
        # THE READER-FACING FORM OF `method`, AND IT WENT STALE THE
        # SAME WAY. When weighting shipped I rewrote `method` and walked
        # straight past this, which is the reader-facing sentence design
        # actually prints, and it disagreed with the computed
        # one_region_carries on 122 of 123 places: Suriname's caveat
        # said 14% where the field said 100%.
        #
        # Design caught it, having had the identical thing done to them
        # by me an hour earlier on the UK page. A field or a sentence
        # that DESCRIBES the method has to change when the method
        # changes, and this is now the third instance in two days.
        #
        # Computed from the same values it describes, so it cannot
        # disagree with them again.
        "caveat": (
            # The sentence changes shape at the top end, because
            # "mostly its largest region" understates a figure that IS
            # that region, and "the smallest regions barely move it" is
            # false when they have no vote at all. Design flagged
            # exactly this for Liberia, Gabon and Suriname.
            ((f"this country figure IS {_largest_name}"
              + (f", the only region with any cropland in ASAP's mask. "
                 f"The other {_nzero} region"
                 f"{'s' if _nzero != 1 else ''} "
                 f"do{'' if _nzero != 1 else 'es'} not enter it."
                 if _nzero else
                 ", which is the country's only crop region. There is "
                 "no weighting choice to make.")
              if _w and len(_w) == 1 else
              f"weighted by cropland area, so {_largest_name} carries "
              f"{round(100 * max(_w.values()) / sum(_w.values()))}% of this "
              f"figure and the smallest regions barely move it"
              + (f". {_nzero} of the {n} regions have no cropland in "
                 f"ASAP's mask and get no vote" if _nzero else "")
              + ". The national number is mostly its largest crop region "
                "by construction.")
             if _w and sum(_w.values()) > 0 else
             f"each of the {n} regions counts equally, so one carries "
             f"{round(100 / n)}% of this figure whatever its cropland "
             f"area: the cropland reference data was absent at build "
             f"time, so this figure is NOT area-weighted")
            if n else "single region, no weighting choice"),
    }


def rate_count_baseline(panels: list, doy: int, cur_year: int) -> dict:
    """How many places reach rank 1 on the rate in a normal year.

    Design withheld the rate block rather than render "13 countries" bare,
    which was right: a count without its distribution is the error this
    channel's own chance_baseline exists to prevent, and it reached our
    headline four hours earlier. They also refused to type the 10 and the
    2.6 out of a chat message, which is the rule we agreed after a figure
    went through four people and came out four different numbers.

    Computed the same way as the current year, for every year, so the
    comparison is like for like: rank 1 on the change AND rank 1 after the
    starting level is controlled for. The gate matters here as much as it
    does live: on the raw rank alone 2026 reads 25, and roughly half of
    those are a steep fall from a high start rather than news.
    """
    raw, start_c, time_c, both_c = {}, {}, {}, {}
    a, b = doy - RATE_BACK, doy
    n = 0
    for pv in panels:
        if pv is None or a not in pv.columns or b not in pv.columns:
            continue
        ch = (pv[b] - pv[a]).dropna().round(3)
        st = pv[a].dropna()
        idx = [y for y in ch.index.intersection(st.index)
               if BASE_FIRST <= y <= cur_year]
        if cur_year not in idx or len(idx) < 20:
            continue
        n += 1
        ch, st = ch.loc[idx], st.loc[idx]
        yrs = np.array(idx, dtype=float)

        def _resid(cols):
            A = np.column_stack([np.ones(len(ch))] + cols)
            beta, *_ = np.linalg.lstsq(A, ch.values, rcond=None)
            return pd.Series(ch.values - A @ beta, index=ch.index)

        res = {"start": _resid([st.values]),
               "time": _resid([yrs]),
               "both": _resid([st.values, yrs])}
        # CONJUNCTION, deliberately: a place counts only if it is rank 1
        # on the raw change AND still rank 1 once the control is applied.
        # The alternative is an independent argmin on the residual, which
        # is a different statistic and gives different numbers. Both are
        # defensible; mixing them is not, and every variant here uses the
        # same convention so the baselines stay like for like.
        for y in idx:
            if int((ch.drop(index=y) < ch.loc[y]).sum()) + 1 != 1:
                continue
            raw[y] = raw.get(y, 0) + 1
            for store, key in ((start_c, "start"), (time_c, "time"),
                               (both_c, "both")):
                r = res[key]
                if int((r.drop(index=y) < r.loc[y]).sum()) + 1 == 1:
                    store[y] = store.get(y, 0) + 1

    out = {"places_counted": n, "window_dekads": RATE_BACK}
    # Each variant names what it is MISSING, not what it has. A reader of
    # the payload needs to know why a figure cannot carry a superlative,
    # and "controls for starting level" does not say that "drift" is still
    # unhandled. The fully controlled row names its controls instead.
    variants = (("raw", raw, False,
                 "starting level or drift in the series"),
                ("holding_the_control", start_c, False,
                 "drift in the series"),
                ("time_detrended", time_c, False, "starting level"),
                ("both_controls", both_c, True,
                 "starting level and drift in the series"))
    for label, c, fully, controls in variants:
        prior = [c.get(y, 0) for y in range(BASE_FIRST, cur_year)]
        cur = c.get(cur_year, 0)
        at_or_above = sum(1 for v in prior if v >= cur)
        survives = bool(fully and at_or_above == 0)
        if not fully:
            licence = (
                "NO SUPERLATIVE FROM THIS VARIANT AT ANY COUNT. It does not "
                f"control for {controls}, so a count that tops it is not a "
                "record, however large the margin, and "
                "prior_years_at_or_above being 0 here does not license one. "
                "Comparison only.")
        elif survives:
            licence = (
                f"Licensed: this many places are falling faster over "
                f"{RATE_BACK} dekads than in any year of the record, after "
                f"controlling for {controls}.")
        else:
            licence = (
                "NOT LICENSED AS A RECORD. The publishable form is 'at or "
                "near the top of the record on every reading'. "
                f"{at_or_above} prior year(s) of {len(prior)} match or beat "
                "this count once fully controlled.")
        out[label] = {
            "this_year": cur,
            "prior_mean": round(float(np.mean(prior)), 1) if prior else None,
            "prior_max": max(prior) if prior else None,
            "prior_min": min(prior) if prior else None,
            "prior_years_at_or_above": at_or_above,
            "prior_years_counted": len(prior),
            "fully_controlled": fully,
            "superlative_survives_controls": survives,
            "licensed_claim": licence,
            "series": {int(y): c.get(y, 0)
                       for y in range(BASE_FIRST, cur_year + 1)},
        }
    out["publish"] = "both_controls"
    out["_why"] = (
        "the raw count includes places whose steep fall is a fall from a "
        "high start, which is arithmetic rather than news; and the 4-dekad "
        "change carries an across-year trend, so a bare rank is partly "
        "drift. Both controls are needed and 13i measures why. Every "
        "variant carries superlative_survives_controls and licensed_claim "
        "because knowing WHICH figure to publish is not the same as knowing "
        "WHAT it licenses: on 2026-08-13 the correct variant was rendered "
        "and a record superlative shipped anyway, one control short.")
    out["_whole_set"] = ("this compares a COUNT against the history of "
                         "the same count, so it needs no multiplicity "
                         "correction. It does NOT establish any single "
                         "country: rank 1 of 26 has p = 1/26, so a set "
                         "this size produces about four by chance.")
    return out


def build_stress(catalogue: dict, allow_mixed: bool = False) -> dict:
    # Loaded once. crop_areas() reads a 131 MB zip's attribute table, so
    # doing it per country would read it 168 times.
    _AREAS = crop_areas()
    over = check_expected_lags(catalogue)
    if over:
        worst = max(r["dekads_behind"] for r in over)
        by_inst = sorted({r["instrument"] for r in over})
        print(f"  WARNING: {len(over)} place-instrument pair(s) exceed the "
              f"lag we treat as normal, worst {worst} dekads behind: "
              f"{', '.join(by_inst)}.", flush=True)
        print(f"  Not fatal. These are emitted absent with the gap stated "
              f"per datum, so the composite loses an input rather than "
              f"carrying a stale one. But a lag this size is a stalled "
              f"product, not a publication schedule, and the bound exists "
              f"so it cannot pass unremarked.", flush=True)

    stale = check_instruments_agree(catalogue)
    if stale and not allow_mixed:
        worst = sorted(stale, key=lambda r: r["place"])[:8]
        lines = "\n".join(
            f"    {r['place']}: {r['instrument']} holds {r['holds']}, "
            f"cumulative vegetation holds {r['spine_holds']}"
            for r in worst)
        raise SystemExit(
            f"REFUSING TO EMIT: {len(stale)} instrument-place pair(s) are "
            f"read at an older dekad than the spine.\n{lines}"
            + (f"\n    ... and {len(stale) - len(worst)} more"
               if len(stale) > len(worst) else "")
            + "\n  A place whose instruments disagree about their date "
              "publishes absences that blame ASAP for our own gap, and "
              "guts the composite.\n  Re-run crops/pull_asap_indicator.py "
              "--all --batch to finish the pull. Override with "
              "--allow-mixed-dekads only if you know why.")
    places, skipped = [], []
    latest_dekad = None
    # Every reported place's oriented instrument series, kept so the
    # global block is computed from the SAME series the per-place
    # blocks use. Recomputing it elsewhere is what lost the tie
    # convention and the scope three times in one day.
    per_place_oriented = []
    rate_panels = []

    for cid, name in catalogue.items():
        # ASAP's own cropland area per region, for tls-internal#16.
        # Empty dict when the reference data is absent, and
        # area_weighted then falls back to the unweighted mean.
        _area_w = _AREAS.get(str(cid), {})
        base = load("zfparc", cid)
        # Three different things used to share one reason, and one of
        # them is OUR failure reported as a fact about ASAP. A missing
        # cache file means nothing was fetched; it does not mean the
        # crop mask is empty. Zero places hit that branch today, so this
        # is latent rather than live, which is the cheapest moment to
        # fix it. Same discipline as `absent_because` on an instrument.
        if not (CACHE / f"zfparc_crop_growing_{cid}.csv").exists():
            skipped.append({"place": name, "reason": "no data was "
                            "fetched for this place", "ours": True})
            continue
        if base is None:
            skipped.append({"place": name, "reason": "ASAP reports no "
                            "cropland inside a growing cycle here",
                            "ours": False})
            continue
        if base.region_id.nunique() < MIN_UNITS:
            skipped.append({"place": name,
                            "reason": f"fewer than {MIN_UNITS} crop units "
                                      f"in the ASAP crop mask",
                            "ours": False})
            continue

        latest = base.dt.max()
        doy = int(base.loc[base.dt == latest, "doy"].iloc[0])
        latest_dekad = latest_dekad or str(latest.date())

        instruments, water_agree, loaded, oriented = [], {}, {}, {}
        for slug, label, unit, worse_is in INSTRUMENTS:
            d = load(slug, cid)
            loaded[slug] = d
            if d is None:
                # An absent instrument is emitted, never omitted. A key
                # that is simply missing makes "not measured here" and
                # "nothing to report" look identical, and those are
                # opposite claims. D-051 applied to a gap.
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False,
                    "unavailable_because": "ASAP does not publish this "
                                           "indicator for this country",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            same, _used = area_weighted(
                d[d.doy == doy], _area_w, ["year"])
            hist = same[(same.index >= BASE_FIRST) & (same.index <= BASE_LAST)]
            cur = same.get(latest.year, np.nan)
            # Absences are stated here too. This used to `continue`,
            # which silently dropped soil moisture from every country
            # while the region rows below said explicitly that it had
            # not reported. Same fix as the region level, one level up,
            # and it was invisible until the layers were due to render.
            if same.empty:
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False, "absent": "undefined_at_this_dekad",
                    "absent_because": f"{label} is not defined for this "
                                      f"country at this point in the season.",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            if np.isnan(cur):
                # STATE THE SIZE OF THE GAP, not just that there is one.
                # This said "has not reported for this dekad yet", and
                # "yet" implies the next dekad will bring it. On
                # 2026-08-14 soil moisture was THREE dekads behind and
                # had not moved since 6 August while the spine advanced
                # twice, so the sentence described a 30 day stall as a
                # normal wait. An absence carries its magnitude or a
                # reader supplies their own.
                own = _newest_ordinal(d)
                behind = (latest.year * 36 + doy - own
                          if own is not None else None)
                if behind and behind > 0:
                    because = (
                        f"{label} has not reported for this dekad. Its "
                        f"newest observation is {behind} dekad"
                        f"{'s' if behind > 1 else ''} behind the "
                        f"crop-outcome instrument.")
                else:
                    because = (f"{label} has not reported for this dekad "
                               f"yet.")
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False, "absent": "no_current_value",
                    "absent_because": because,
                    "dekads_behind_spine": behind,
                    "expected_lag_dekads": LAGS_BY_DESIGN.get(slug, 0),
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            if len(hist) < 20:
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False,
                    "absent": "too_few_comparable_years",
                    "absent_because": f"Fewer than 20 comparable years of "
                                      f"{label.lower()} at this dekad.",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            instruments.append({
                "name": label,
                "value": round(float(cur), 3),
                "unit": unit,
                "baseline_mean": round(float(hist.mean()), 3),
                # Same reason as the region rows; null where degenerate.
                "baseline_sd": (round(float(hist.std()), 3)
                                if float(hist.std()) > 1e-6 else None),
                "baseline_span": f"{BASE_FIRST}-{BASE_LAST}, same dekad",
                "rank": rank_of(cur, hist, worse_is),
                "of": len(hist) + 1,
                "worse_is": "low" if worse_is > 0 else "high",
                # Five layers each showing a bare rank is the missing
                # basis multiplied by five. Bound here as it is on
                # magnitude and on region rows.
                "statement": _rank_statement(
                    rank_of(cur, hist, worse_is), len(hist) + 1,
                    latest.year, "low" if worse_is > 0 else "high"),
                "source": "JRC ASAP, GAUL1 indicator statistics, "
                          "crop mask, growing cycle",
                "authorship": "agency",
                "available": True,
                "qualifiers": [],
            })
            # Fed to severity_block from INSIDE the success branch, so
            # the instruments it averages are exactly the instruments
            # the page shows as available. Collecting them separately
            # would let the two drift, and a severity number built on
            # an instrument the page reports as absent is the same
            # class of defect as a qualifier separated from its number.
            span = same[(same.index >= BASE_FIRST) & (same.index <= latest.year)]
            oriented[label] = -span if worse_is > 0 else span

            if slug in ("zfparc", "wsi", "spi3"):
                ann = d.groupby("year").value.mean()
                water_agree[slug] = ann

        if not instruments:
            skipped.append({"place": name,
                            "reason": "no instrument had 20 years at "
                                      "this dekad"})
            continue

        # Is the stress describable as water-driven?
        driver = "not identified"
        if all(k in water_agree for k in ("zfparc", "wsi", "spi3")):
            def corr(a, b):
                j = pd.concat([a.rename("a"), b.rename("b")],
                              axis=1).dropna()
                j = j[(j.index >= 2002) & (j.index <= BASE_LAST)]
                return j.a.corr(j.b) if len(j) >= 18 else np.nan
            cw = corr(water_agree["zfparc"], water_agree["wsi"])
            cr = corr(water_agree["zfparc"], water_agree["spi3"])
            if cw >= WATER_DRIVEN_MIN and cr >= WATER_DRIVEN_MIN:
                driver = "water"

        # Sub-national. The country aggregate hides regions: Turkiye
        # ranks 23 of 26 nationally on 2026-07-11 while four of its
        # southeastern provinces are at their worst on record. Reporting
        # only at country level would have lost that entirely.
        # Year x dekad panels for the rate. Country level is the mean
        # across regions, matching how the country instruments above are
        # built, so the level and the rate describe the same aggregate.
        country_panel = area_weighted(
            base, _area_w, ["year", "doy"])[0].unstack()
        region_panels = {
            reg: g.groupby(["year", "doy"]).value.mean().unstack()
            for reg, g in base.groupby("region_name")
        }

        regions = []
        same_all = base[base.doy == doy]
        for reg, g in same_all.groupby("region_name"):
            # Region NAMES are not unique across region_ids in ASAP, so
            # a name can carry two rows per year. Aggregate before
            # indexing or the year lookup returns a Series.
            s = g.groupby("year").value.mean()
            hist_r = s[(s.index >= BASE_FIRST) & (s.index <= BASE_LAST)]
            if latest.year not in s.index or len(hist_r) < 20:
                continue
            cur_r = float(s[latest.year])
            rk = rank_of(cur_r, hist_r, +1)
            of = len(hist_r) + 1
            regions.append({
                "region": reg,
                "value": round(cur_r, 3),
                "baseline_mean": round(float(hist_r.mean()), 3),
                "rank": rk,
                "of": of,
                # A region row used to declare rank and of but NOT its
                # basis, and the basis lived only on the country object.
                # The claim that reached copy and was wrong for 7 of
                # Chad's 8 regions was a REGION claim, so the writer had
                # no basis field in front of them to drop.
                "basis": f"same dekad, {BASE_FIRST}-{BASE_LAST}",
                # And the value and its basis bound into one computed
                # field, so dropping the basis is visibly dropping half
                # of a field rather than trimming a sentence. Computed,
                # never typed, per the ban on free text that stops
                # tracking its data.
                "statement": _rank_statement(rk, of, latest.year),
                # The region's own record, so a region page can show it
                # against itself the way the country block shows Chad.
                # Same shape as the country chance_baseline series.
                "series": {int(y): round(float(v), 3)
                           for y, v in s.items()
                           if BASE_FIRST <= y <= latest.year},
                "series_span": series_span(
                    {int(y): v for y, v in s.items()
                     if BASE_FIRST <= y <= latest.year},
                    BASE_FIRST, latest.year),
                # The rate belongs at region level too, and this is the
                # level the England case was found at: England is the
                # steepest 4-dekad fall in its own record while the UK
                # national figure is only second, because Scotland and
                # Northern Ireland were flat and the average buries it.
                "rate": rate_block(region_panels.get(reg), doy,
                                   latest.year, full=False),
            })
        # Per-region driver. The country-level driver is evidence about
        # the country, and rendering it on a region page asserts
        # something about that region. Namibia is water-driven as a
        # country and Hardap is not: veg~rainfall is 0.15 there against
        # 0.30 required. That is the same fault as "driest" over Cairo,
        # a country property worn by a region, so the test is run per
        # region and the region carries its own answer.
        # Per-region summary for every instrument, absences included.
        # Series stay vegetation-only: stress_current.json is git-tracked
        # and rewritten wholesale each dekad, and JSON full of changed
        # floats deltas badly, so a second series is repo growth for
        # charts nothing renders yet.
        # THE SPINE GOES IN THE INSTRUMENTS DICT TOO, duplicating the
        # region's own top-level value. It is not redundant, it is the
        # fix for a defect that has now misled two desks.
        #
        # Cumulative vegetation is the region's TOP-LEVEL value, rank and
        # statement, while the other five sit in `instruments`. Nothing
        # in that shape says so. Socials read each region's top-level
        # rank and reported that no French region was at a record, which
        # was a cumulative-vegetation fact stated as a general one. Then,
        # looking for the same instrument in `instruments`, they found no
        # `zfparc` key and reported that a real measured zero was an
        # unmeasured one, on a card already live.
        #
        # Both errors are the same missing thing, and `instruments` is
        # where anybody sensible looks for an instrument. A consumer that
        # iterates this dict now sees all six with one shape and never
        # has to know the spine lives elsewhere. The top-level fields
        # stay for existing consumers.
        for entry in regions:
            entry.setdefault("instruments", {})["zfparc"] = {
                "value": entry["value"],
                # baseline_mean too, or zfparc is the ONE instrument of
                # five whose baseline is not where the other four keep
                # theirs, and a consumer has to know the layout for
                # exactly one row. Socials hit this shading the France
                # map and reported it rather than working around it.
                # Same omission, same false justification as the region
                # baselines themselves: "recoverable from elsewhere".
                "baseline_mean": entry["baseline_mean"],
                "rank": entry["rank"],
                "of": entry["of"],
                "statement": entry["statement"],
            }

        for slug, label, unit, worse_is in INSTRUMENTS:
            if slug == "zfparc":
                continue
            dd = loaded.get(slug)
            for entry in regions:
                inst = entry.setdefault("instruments", {})
                if dd is None:
                    inst[slug] = {
                        "available": False,
                        "absent": "not_published_for_country",
                        "absent_because": f"ASAP does not publish "
                                          f"{label.lower()} for this country.",
                    }
                    continue
                sub = dd[(dd.doy == doy) & (dd.region_name == entry["region"])]
                ser = sub.groupby("year").value.mean()
                if ser.empty:
                    # Never defined here at this point in the season, as
                    # opposed to defined-but-late. SPI is undefined in
                    # hyper-arid regions when the accumulation window
                    # holds no measurable rain: Luxor carries SPI only
                    # in winter dekads. Calling that "not reported yet"
                    # would read as temporary and it is seasonal.
                    inst[slug] = {
                        "available": False,
                        "absent": "undefined_at_this_dekad",
                        "absent_because": f"{label} is not defined for "
                                          f"this region at this point in "
                                          f"the season.",
                    }
                    continue
                h = ser[(ser.index >= BASE_FIRST) & (ser.index <= BASE_LAST)]
                if latest.year not in ser.index:
                    # Temporary by wording as well as by fact: this
                    # instrument publishes behind the others and will
                    # report. "Not measured here" would be permanent and
                    # false.
                    # Accurate reason. Soil moisture publishes one dekad
                    # behind the vegetation indicators, so it has full
                    # history here and no value for the dekad reported.
                    # "Too few years" would have been false.
                    # SAME FIX AS THE COUNTRY ROW, and it did not reach
                    # here first time. "yet" implies the next dekad
                    # brings it; soil moisture is three dekads behind
                    # and has not moved since 6 August. A per-region
                    # absence that understates the gap is the same
                    # defect as a per-country one, multiplied by 2,122.
                    own_o = _newest_ordinal(dd)
                    behind_r = (latest.year * 36 + doy - own_o
                                if own_o is not None else None)
                    inst[slug] = {
                        "available": False,
                        "absent": "no_current_value",
                        "absent_because": (
                            f"{label} has not reported for this dekad. "
                            f"Its newest observation is {behind_r} dekad"
                            f"{'s' if behind_r > 1 else ''} behind the "
                            f"crop-outcome instrument."
                            if behind_r and behind_r > 0 else
                            f"{label} has not reported for this dekad "
                            f"yet."),
                        "dekads_behind_spine": behind_r,
                        "expected_lag_dekads": LAGS_BY_DESIGN.get(slug, 0),
                    }
                    continue
                if len(h) < 20:
                    inst[slug] = {
                        "available": False,
                        "absent": "too_few_comparable_years",
                        "absent_because": f"Fewer than 20 comparable "
                                          f"years of {label.lower()} at "
                                          f"this dekad.",
                    }
                    continue
                v = float(ser[latest.year])
                # Keyed by slug and stripped of anything constant per
                # instrument. name, unit and worse_is live once in the
                # top-level legend rather than 2,122 times each: this
                # file is git-tracked and rewritten every dekad, so
                # repeated strings are repo growth, not just size.
                # Region layers are emitted for 2,122 regions x 5
                # instruments, so every constant or derivable field here
                # costs about 0.2 MB against a 5 MB guard. `available`
                # is implied by the presence of a value. Rank and `of`
                # stay because a rank without its denominator is the
                # defect this channel exists to avoid.
                #
                # BASELINE_MEAN IS BACK, and the reason it was dropped
                # was wrong. This said it was "recoverable from the
                # country block". It is not: a region's baseline is its
                # own 26-year mean at this dekad, and the country
                # baseline is a mean ACROSS regions. You cannot recover
                # one from the other, and 22 French regions have 22
                # different baselines.
                #
                # What it costs to omit, found by socials: their region
                # maps had to shade by RANK, because rank was the only
                # magnitude-ish field present. So Languedoc-Roussillon,
                # which beat its own record by 0.02, painted identically
                # to Limousin, which beat its by 1.31. A 65-fold
                # difference in margin rendered the same colour. That is
                # the rank-without-magnitude defect built into a colour
                # ramp, where there is no wording for a reader to argue
                # with.
                _rk = rank_of(v, h, worse_is)
                inst[slug] = {
                    "value": round(v, 3),
                    # baseline_sd so an instrument in NATURAL UNITS can be put
                    # on the same scale as one already standardised. Socials'
                    # France card draws vegetation (a z-score) beside water
                    # satisfaction (percentage points), and there is no
                    # principled exchange rate between "1.5 standard deviations"
                    # and "25 percentage points". They had to pick an endpoint,
                    # and the pick made the water panel darker than the
                    # vegetation panel on a country with 19 of 22 regions at a
                    # vegetation record and 18 of 22 at a water record. Every
                    # number correct, the picture saying the opposite.
                    #
                    # NULL WHERE DEGENERATE, never zero. 9 of 2,097 water
                    # histories have no variance at all, regions where the
                    # crop's water need is always met, and a consumer dividing
                    # by that gets an infinite z. A missing field stops them;
                    # a zero does not.
                    "baseline_sd": (round(float(h.std()), 3)
                                    if float(h.std()) > 1e-6 else None),
                    "baseline_mean": round(float(h.mean()), 3),
                    "rank": _rk, "of": len(h) + 1,
                    # Bound here for the same reason the country rows
                    # bind it: a rank separated from its basis gets
                    # reassembled by whoever renders it. Design was
                    # composing "1st lowest of 26" in the template from
                    # rank, of and worse_is, which is the composition
                    # defect one field along, and they declined to ship
                    # until this existed. Built by the SAME helper as
                    # the country rows, so the two cannot drift.
                    "statement": _rank_statement(
                        _rk, len(h) + 1, latest.year,
                        "low" if worse_is > 0 else "high"),
                }

        # ...and then dropped again, deliberately. NOTHING READS IT.
        # The country template draws country instruments, region
        # `series` and severity; no consumer touches a region's
        # per-instrument block, because the region page it was built for
        # does not exist. Carrying 1.1 MB per dekad in git history for a
        # page that may never be built is what the size guard is for,
        # and git history cannot be trimmed later without a force-push.
        #
        # The computation stays because the absence reasons above are
        # load-bearing knowledge that took two wrong answers to get
        # right, and because restoring the emit is one line and one
        # 38-second rebuild with no fetch. Delete this block, not the
        # loop, when a region page exists.
        # RESTORED 2026-08-09. Dropped on 08-06 because nothing read it;
        # the pinned European set now needs per-region layers, and none
        # of those seven countries has a single region at a record low,
        # so without this their pages have nothing to show. The reason
        # for dropping it was sound and it stopped being true.

        _wsi = loaded.get("wsi")
        _spi = loaded.get("spi3")
        if _wsi is not None and _spi is not None:
            zr = base.groupby(["region_name", "year"]).value.mean()
            wr = _wsi.groupby(["region_name", "year"]).value.mean()
            sr = _spi.groupby(["region_name", "year"]).value.mean()
            for entry in regions:
                nm = entry["region"]
                try:
                    j = pd.concat([zr[nm].rename("a"), wr[nm].rename("b"),
                                   sr[nm].rename("c")], axis=1).dropna()
                except KeyError:
                    entry["driver"] = "not identified"
                    continue
                j = j[(j.index >= 2002) & (j.index <= BASE_LAST)]
                ok = (len(j) >= 18
                      and j.a.corr(j.b) >= WATER_DRIVEN_MIN
                      and j.a.corr(j.c) >= WATER_DRIVEN_MIN)
                entry["driver"] = "water" if ok else "not identified"
        else:
            for entry in regions:
                entry["driver"] = "not identified"

        regions.sort(key=lambda r: r["rank"])

        # HOW MUCH OF THE COUNTRY IS AT ONCE, PER INSTRUMENT.
        #
        # Asked for by socials, and the reason they asked is the reason
        # it ships. They spent an hour inside this file, read each
        # region's top-level `rank`, found none at 1, and told Kristjan
        # no French region was at a record. The number was right and the
        # claim was wrong by a wide margin: the region's top-level rank
        # IS cumulative vegetation, where France is 0 of 22, while
        # current vegetation is 19 of 22 and water satisfaction 18 of 22.
        # Nothing in the shape said which instrument the top-level rank
        # measured. Trap 18 again, and this time it fooled a chat with
        # the file open, so a reader has no chance.
        #
        # Derivable, and emitted anyway. Deriving it requires knowing
        # that the spine sits at the top level while the other five sit
        # in a sub-dict, which is exactly the knowledge whose absence
        # caused the error. A consumer that has to know our layout to
        # count correctly will eventually count wrongly.
        #
        # The denominator is per instrument, not the region count: soil
        # moisture is absent everywhere right now, and "0 of 22" would
        # read as 22 regions checked and none at a record rather than
        # none checked.
        _labels = {s: l for s, l, _u, _w in INSTRUMENTS}
        at_record = {}
        if regions:
            at_record["zfparc"] = {
                "label": _labels.get("zfparc", "Vegetation, cumulative"),
                "at_record": sum(1 for r in regions if r.get("rank") == 1),
                "of": len(regions),
            }
            for _slug, _lab, _u, _w in INSTRUMENTS:
                if _slug == "zfparc":
                    continue
                got = [v for v in
                       ((r.get("instruments") or {}).get(_slug)
                        for r in regions)
                       if isinstance(v, dict) and v.get("rank") is not None]
                if not got:
                    continue
                at_record[_slug] = {
                    "label": _lab,
                    "at_record": sum(1 for v in got if v["rank"] == 1),
                    "of": len(got),
                }

        # THE ORDERING KEY. Kristjan, 2026-08-19: "Our goal is to show
        # where something is abnormal and we have failed at this, the
        # cumulative is the totally wrong instrument for showing that."
        # Product ruled extent orders the list and intensity is the
        # reading, and said they would prefer a CONTINUOUS extent to a
        # share-at-record if it could be built. It can.
        #
        # Mean position of every region-instrument reading within its
        # own 2001-2025 history, 1.0 being the worst on record, over the
        # FAST instruments only. Cumulative vegetation is excluded by
        # the ruling: it integrates from sowing, so it cannot answer
        # "abnormal now" and 13r shows what that does. It is still
        # published, prominently, as the outcome measure.
        #
        # WHY CONTINUOUS RATHER THAN SHARE-AT-RECORD. Binary extent
        # cannot separate "just crossed" from "smashed it", which is the
        # problem severity_block was built for. Measured both: Haiti has
        # 2% of readings at a record and ranks 84th on the binary share,
        # and 18th here, because almost every region sits just below its
        # own record. Mauritania has NOTHING at a record and ranks 52nd.
        # The binary version calls both of those quiet.
        #
        # DERIVED FROM THE PUBLISHED RANKS, not recomputed from the
        # cache, so the key cannot drift from the numbers on the page.
        # position = (of - rank) / (of - 1).
        #
        # COVERAGE IS EMITTED, after the grid taught us what a collapsed
        # denominator does. `of` is per instrument per dekad, so a mean
        # over two readings and a mean over eighty are not the same
        # claim. Today 4 of 123 countries are below full coverage and
        # none below 75%, but that is a fact about this dekad.
        _FAST = [s_ for s_, _l, _u, _w in INSTRUMENTS if s_ not in ("zfparc", "sm")]
        # AREA-WEIGHTED, same as every other country figure, because
        # "how much of a country" means how much of its cropland and not
        # how many of its administrative units. England is 85.6% of UK
        # cropland and was one vote of four.
        _pos, _wts, _at, _atw = [], [], 0, 0.0
        for _r in regions:
            _rw = float((_area_w or {}).get(_r.get("region"), 0.0) or 0.0)
            if _area_w and _rw <= 0:
                continue          # no cropland in ASAP's own mask
            for _slug in _FAST:
                _v = (_r.get("instruments") or {}).get(_slug)
                if not isinstance(_v, dict):
                    continue
                _rk, _of = _v.get("rank"), _v.get("of")
                if _rk is None or not _of or _of < 2:
                    continue
                _p = (_of - _rk) / (_of - 1)
                _pos.append(_p)
                _wts.append(_rw if _area_w else 1.0)
                if _rk == 1:
                    _at += 1
                    _atw += (_rw if _area_w else 1.0)
        _possible = len(regions) * len(_FAST)
        _wsum = float(np.sum(_wts)) if _wts else 0.0
        ranking_key = {
            "available": bool(len(_pos) >= 8),
            # NULL WHEN NOT AVAILABLE, not merely flagged. Suriname
            # emitted value 0.77 beside available: false, computed from
            # 4 readings of a possible 28 because 6 of its 7 regions
            # have no cropland. A number sitting next to the flag that
            # says not to use it is the exact trap `is_not` exists for,
            # and I built it into the field carrying `is_not`.
            "value": (round(float(np.average(_pos, weights=_wts)), 4)
                      if _pos and _wsum > 0 and len(_pos) >= 8 else None),
            "area_weighted": bool(_area_w),
            "readings": len(_pos),
            "readings_possible": _possible,
            "coverage": (round(len(_pos) / _possible, 3)
                         if _possible else None),
            "instruments": [_labels[s_] for s_ in _FAST],
            "excludes": "Vegetation, cumulative, by product's ruling: it "
                        "integrates from sowing so it cannot say what is "
                        "abnormal NOW. Still published as the outcome "
                        "measure.",
            "share_at_record": (round(_atw / _wsum, 4)
                                if _pos and _wsum > 0 else None),
            "method": "mean position of each region-instrument reading "
                      "within its own 2001-2025 history at this dekad, "
                      "1.0 = worst on record. Derived from the published "
                      "ranks so it cannot drift from them.",
            # CORRECTED 2026-08-26. This said "NOT an intensity
            # reading", which was true of the binary share-at-record
            # this replaced and false of a mean of positions. Design
            # asked whether it was safe to paint a choropleth with,
            # since a choropleth reads as intensity by default, and the
            # answer is yes: the field IS an intensity. My label had not
            # changed when the quantity did, which is the same defect I
            # have sent back to two other chats this week.
            "is_not": "a COUNT, and not the same aggregation as "
                      "`severity`. It IS an intensity: the "
                      "cropland-weighted mean of how far each region "
                      "sits into its own history, so a choropleth of it "
                      "reads correctly. It differs from `severity` in "
                      "aggregation order, averaging region-level "
                      "positions and weighting them by cropland where "
                      "severity averages instrument positions of the "
                      "country-level values. For a count of regions at "
                      "their record use `share_at_record`; for how fast "
                      "conditions are moving, use `rate`.",
            "evidence_basis": "combined",
            "authorship": "tls_built",
        }

        # The empirical chance baseline, per place. Design needs this
        # as a drawn object rather than a sentence, and product's
        # adopted preference is to quote the TRAJECTORY where the series
        # allows it rather than a baseline. Both need the per-year
        # series, so it is emitted rather than left to be recomputed.
        #
        # Never units/26. The uniform assumption fails wherever a series
        # trends, and it fails in different directions in different
        # places: Europe 4.0x, globally 1.39x, Chad and neighbours 0.1
        # to 0.4x. It cannot be corrected, only counted.
        panel = (base[base.doy == doy]
                 .groupby(["region_id", "year"]).value.mean().unstack())
        panel = panel.dropna()
        worst_by_year = panel.idxmin(axis=1).value_counts()
        series = {int(y): int(worst_by_year.get(y, 0))
                  for y in range(BASE_FIRST, latest.year + 1)}
        recent = [v for y, v in series.items()
                  if 2014 <= y <= BASE_LAST]
        empirical = {
            "measures": "admin units at their worst on record for this "
                        "dekad, per year",
            "series": series,
            "recent_mean": round(float(np.mean(recent)), 2) if recent else None,
            "recent_min": int(min(recent)) if recent else None,
            "recent_max": int(max(recent)) if recent else None,
            "this_year": series.get(latest.year, 0),
            "_uniform_would_say": round(len(panel) / 26, 1),
            "_note": "uniform_would_say is shown only to be argued "
                     "with. Use recent_mean.",
        }
        # The bar product adopted 2026-07-29: a count is notable when it
        # clears the place's OWN recent maximum, not when it clears a
        # mean. Sharper than a mean because it needs no distributional
        # assumption, and it is what separated Chad and Sudan from
        # Rwanda, Eritrea, Mali and Burundi.
        empirical["clears_own_recent_max"] = bool(
            recent and empirical["this_year"] > max(recent))

        # Ordering key, for design, replacing a floor they wrote
        # themselves. Neither of their two suggestions survives the data:
        # a share excess ranks China's 0-to-1 above Turkiye's 2-to-4
        # because it rewards small denominators, and an absolute excess
        # has the many-units bias they identified.
        #
        # What works is a floor plus a share. The floor removes the
        # noise cases, which are all "went from 1 to 2" or "0 to 1", and
        # the share orders what survives without a size bias. A
        # materiality threshold is domain knowledge and belongs here
        # rather than in the renderer, per the platform contract.
        _mx = max(recent) if recent else 0
        empirical["excess_abs"] = empirical["this_year"] - _mx
        empirical["excess_share"] = round(
            (empirical["this_year"] - _mx) / len(panel), 4) if len(panel) else 0.0
        # Renamed. "notable" invited being read as a finding, and it
        # was: an h1 claimed six such countries were more than their own
        # history explains, when six is the 57th percentile of the last
        # 35 dekads. The field decides what to SHOW, never what is true.
        # Both keys emitted for one dekad so nothing breaks mid-switch.
        _sel = bool(empirical["clears_own_recent_max"]
                    and empirical["this_year"] >= 3)
        empirical["selected_for_display"] = _sel
        empirical["notable"] = _sel   # deprecated, remove after 2026-08-14
        empirical["_order_by"] = ("filter on selected_for_display, order by "
                                  "excess_share. Never order on "
                                  "clears_own_recent_max alone: it is a "
                                  "boolean over a small sample and puts "
                                  "1-against-0 beside 8-against-3. And "
                                  "the COUNT of selected places is not a "
                                  "finding: it sits at the 57th "
                                  "percentile of the last 35 dekads.")

        # Seasonality. The season window is derived from ASAP's static
        # phenology, and the static-ness is the point here. Section 6i
        # disqualified these windows for drift precisely because they
        # cannot change; a seasonality claim needs a climatology rather
        # than an observation, so the same property qualifies them. This
        # says WHEN a season opens, never what will happen in it.
        # The off-season flag lives in the warnings series, not the
        # indicator files, so the table is built once by
        # crops/season_starts.json rather than recomputed per place.
        # ALWAYS a list, never a bare int. Five countries here are
        # genuinely bimodal (Kenya's long and short rains, Somalia's Gu
        # and Der, Cote d'Ivoire, Egypt, Guyana), and emitting an int
        # for the rest made the field's type depend on the data. A
        # consumer testing `v in window` silently drops every bimodal
        # country; one testing `any(x in window for x in v)` keeps them.
        # That alone produced three different counts of the same thing
        # across two chats.
        _raw = SEASON_STARTS.get(name)
        season_starts = ([] if _raw is None
                         else _raw if isinstance(_raw, list) else [_raw])
        # And the scalar a renderer actually wants: the next opening
        # from the dekad being reported, wrapping through the year.
        next_open = None
        if season_starts:
            ahead = sorted(((x - doy) % 36, x) for x in season_starts)
            next_open = ahead[0][1]

        head = instruments[0]
        quals = [{
            "kind": "canopy_not_cause",
            "text": "ASAP observes the crop canopy, not what stressed "
                    "it. Heat, drought, disease and late planting are "
                    "not separable in this measurement.",
        }]
        if driver == "not identified":
            quals.append({
                "kind": "driver_not_identified",
                "text": "Vegetation and the water instruments do not "
                        "co-vary here, so this stress cannot be "
                        "described as water-driven. The reading is the "
                        "condition only.",
            })

        places.append({
            "place": name,
            "asap0_id": int(cid),
            "crop_units": int(base.region_id.nunique()),
            "dekad": str(latest.date()),
            "magnitude": {
                "kind": "rank",
                # WHAT THIS MEASURES, NAMED INSIDE IT.
                #
                # `magnitude` is ONE instrument's level, cumulative
                # vegetation, and nothing in the name said so. It is
                # also the most inviting field on the place record, so
                # it is the one a renderer reaches for first.
                #
                # For France it reads 12 of 26 while severity.rank reads
                # 1 of 26. That is the calmest number about the country
                # sitting under the most attractive name, on the country
                # whose cumulative index is 12th only because it banked
                # a near-record spring and has spent 98% of it (13r).
                # Design used severity for the standfirst by judgement,
                # and judgement is not a mechanism.
                #
                # Not renamed yet: `magnitude` is read by shipped
                # templates and breaking them at midnight to improve a
                # name is the wrong trade. Named in place now, renamed
                # with design.
                "instrument": "zfparc",
                "instrument_label": "Vegetation, cumulative",
                "is_not": "the composite. This is the crop-outcome "
                          "instrument's LEVEL alone, and it is the "
                          "slowest of the six. For how stressed a place "
                          "is across all reporting instruments use "
                          "`severity.rank`; for how fast it is "
                          "deteriorating use `rate`.",
                "value": head["rank"],
                "of": head["of"],
                "direction": "low",
                "basis": f"same dekad, {BASE_FIRST}-{BASE_LAST}",
                # Same binding as the region rows. basis alone is a
                # field a renderer can show the value without; statement
                # cannot be separated from what it describes, so a page
                # missing the basis is missing a field rather than being
                # subtly wrong.
                "statement": _rank_statement(head["rank"], head["of"], latest.year),
            },
            "driver": driver,
            # "N of 22 regions at their own record", per instrument, each
            # row naming the instrument it counted. The headline
            # `magnitude` above is cumulative vegetation, which is the
            # crop-OUTCOME measure and also the SLOWEST, so a country can
            # sit mid-table there while most of its regions are at a
            # record on the drivers. France on this dekad: magnitude 12th
            # of 26, and 19 of 22 regions at a record on current
            # vegetation, 18 of 22 on water satisfaction.
            "regions_at_record": at_record,
            # What the channel index orders on, per Kristjan and
            # product's ruling of 2026-08-19.
            "ranking_key": ranking_key,
            # How exposed this country's figure is to a weighting we do
            # not have. Free: it reuses the region ranks already emitted.
            "aggregate": aggregate_weighting(
                regions, head["rank"], head["of"], _area_w),
            # The counted measure answers "how many regions", the rank
            # answers "how unusual", and neither answers "how deep".
            # This does. Country level only: the per-instrument region
            # data is already in `regions` if a region view ever wants
            # to build the same thing.
            "severity": severity_block(oriented, latest.year),
            # Level and rate side by side, deliberately. Either alone
            # is a different claim: "ordinary" and "falling faster than
            # in any year on record" are both true of England on
            # 2026-07-11, and a page carrying only the first would have
            # said nothing was happening.
            "rate": rate_block(country_panel, doy, latest.year),
            "evidence_basis": "measured",
            # D-076: "attribution pending" comes off crops. It is a
            # work state, not a finding, and it rendered on every
            # untagged row, so it carried no information. Emitted only
            # when one of the two real ENSO strings applies, which for
            # crops is currently never.
            "attribution": None,
            "authorship": "tls_built",
            "publishable": True,
            "instruments": instruments,
            "regions": regions,
            "regions_worst_3": sum(1 for r in regions if r["rank"] <= 3),
            "chance_baseline": empirical,
            "season_opens_dekads": season_starts,
            "next_season_opens_dekad": next_open,
            "qualifiers": quals,
        })
        if oriented:
            per_place_oriented.append(oriented)
        rate_panels.append(country_panel)

    places.sort(key=lambda p: (p["magnitude"]["value"],
                               -p["magnitude"]["of"]))

    # Aggregate chance baseline over the REPORTED places only.
    #
    # This exists because a figure computed over a wider set than the
    # page shows is not like-for-like, and the error is invisible: the
    # current count is identical either way, because the 45 skipped
    # places contribute no record-worst units this dekad, while the
    # historical years they do contribute inflate the baseline. Design
    # caught it by failing to reproduce 60.1 from the payload and
    # refusing to print a verdict off a number they could not rebuild.
    #
    # Emitting it guarantees the comparison is over the same set as the
    # blocks it frames, and it cannot go stale the way a hard-coded
    # figure would.
    agg = {}
    for pl in places:
        for y, v in pl["chance_baseline"]["series"].items():
            agg[int(y)] = agg.get(int(y), 0) + v
    rec_years = [y for y in range(2014, BASE_LAST + 1)]
    rec_vals = [agg.get(y, 0) for y in rec_years]
    this_year = agg.get(max(agg), 0) if agg else 0
    aggregate = {
        "measures": "regions at their worst on record for this dekad, "
                    "summed across reported places, per year",
        "series": {int(y): int(v) for y, v in sorted(agg.items())},
        "this_year": this_year,
        "recent_mean": round(float(np.mean(rec_vals)), 1) if rec_vals else None,
        "recent_min": int(min(rec_vals)) if rec_vals else None,
        "recent_max": int(max(rec_vals)) if rec_vals else None,
        "recent_years_below_this": int(sum(1 for v in rec_vals
                                           if v < this_year)),
        "recent_years_counted": len(rec_vals),
        "_scope": "reported places only, never the full catalogue. A "
                  "baseline over a wider set than the page shows is not "
                  "like-for-like and the discrepancy is invisible in the "
                  "current year.",
    }
    _fill_saturation_rate(places)

    return {
        "_generated_from": "crops/.cache (no fetch performed)",
        # A VERSION, so a week-over-week diff can tell a method change
        # from weather. Invariant 3 in CLAUDE.md requires this of the
        # ENSO brief and the reason applies here: on 2026-08-19 country
        # figures stopped being unweighted means over regions and became
        # weighted by ASAP's cropland area, and only 7 of 119 places
        # kept their position in the ordering. Nothing about the world
        # changed that day.
        # D-092: the age bound platform will not guess. Flagged as
        # undeclared, so crops pages were shipping unchecked for age.
        #
        # THIRTY, AND THE CONVERSION IS THE WHOLE POINT. FRESHNESS.md
        # sets the reader-relevance bound at 21 days from the END of the
        # newest observation window. Platform measures age from
        # `dekad`, which is the window's LABEL, not its close. A 1st-of-
        # month dekad covers the 1st to the 10th, so the close is the
        # label plus nine, and 21 days past that is the label plus 30.
        #
        # Three clocks on this channel have already been quoted as one
        # number by somebody: the label, the window close, and actual
        # publication. That cost a false staleness alarm and a
        # correction that propagated to two other chats. So the bound is
        # written here with its arithmetic rather than as a bare 30.
        #
        # It fires on a missed ASAP cycle and on a source running late,
        # which is correct: being level with a slow publisher is not a
        # defence.
        "max_data_age_days": 30,
        "max_data_age_measured_from": "the dekad label. 21 days of "
                                      "reader relevance past the window "
                                      "close, plus the 9 days from label "
                                      "to close.",
        "methodology_version": "2.0",
        "methodology_changed": {
            "2.0": "Country figures are area-weighted by ASAP's km2_crop "
                   "(tls-internal#16). Previously an unweighted mean over "
                   "regions, so England carried a quarter of the UK "
                   "figure while holding 85.6% of its cropland. Affects "
                   "every country value, and therefore severity, "
                   "magnitude, rate and ranking_key. Ranks are computed "
                   "on weighted values for EVERY year, so the comparison "
                   "stays like for like. Regions with zero crop-mask "
                   "area get no vote and the count is disclosed per "
                   "place in `aggregate.regions_zero_area`.",
            "1.0": "Unweighted mean over regions, launch to 2026-08-19.",
        },
        "instrument_legend": {
            slug: {"name": label, "unit": unit,
                   "worse_is": "low" if worse_is > 0 else "high",
                   "summarises": SUMMARISES[slug][0],
                   "window_dekads": SUMMARISES[slug][1],
                   "display_order": SUMMARISES[slug][2]}
            for slug, label, unit, worse_is in INSTRUMENTS
        },
        # THE ORDER IS DATA, NOT A RENDERER'S CHOICE, and that is the
        # point rather than a convenience.
        #
        # Product's fix for the causal-reading trap is right: if a page
        # sorts rows by when they moved, the page authors the sequence
        # and a reader is correct to read authorship as assertion. So the
        # order must be fixed, identical on every country, and a property
        # of the instruments rather than of the event.
        #
        # But it cannot be the order this file happened to emit. That one
        # is spine-first: zfparc, which summarises the whole season and
        # is the SLOWEST, sits first, and temp and zfpar, which summarise
        # a single dekad and are the fastest, sit last and second. Fixing
        # that in place would freeze a jumble and then explain it as
        # response time.
        #
        # So the ordering rule is stated and the sort key is emitted:
        # ascending by how much time the number summarises, shortest
        # first. That is a documented property of each index, checkable
        # against JRC's definitions, and it is true in a calm week as
        # well as a moving one. Ties are broken by the legend's own
        # order, which is arbitrary and fixed, and said to be arbitrary
        # rather than dressed as meaning.
        "instrument_order": {
            "by": "window_dekads ascending, then legend order",
            "means": "shortest observation window first. An instrument "
                     "that summarises one dekad moves sooner than one "
                     "that integrates a season, so a fixed order shows "
                     "which instruments CAN move first. That is a fact "
                     "about the instruments and not about any event.",
            "not": "sorted by what moved. Never order these rows by "
                   "observed movement: the ordering would then be a "
                   "claim about sequence, and with `driver` unidentified "
                   "in most places we cannot support one.",
            "order": [s for s, _w, _d, _o in sorted(
                ((s,) + SUMMARISES[s] for s, _l, _u, _x in INSTRUMENTS),
                key=lambda r: r[3])],
        },
        "absence_reasons": {
            "no_current_value": "the instrument has history here but no "
                                "value for the dekad being reported, "
                                "usually because it publishes behind the "
                                "others",
            "undefined_at_this_dekad": "the instrument is never defined "
                                       "for this region at this point in "
                                       "the season, which is seasonal "
                                       "rather than late",
            "too_few_comparable_years": "fewer than 20 comparable years "
                                        "at this dekad",
            "not_published_for_country": "ASAP does not publish this "
                                         "indicator for this country",
        },
        "chance_baseline_aggregate": aggregate,
        # Editor needs "11 days ago" computed at render, and the 9 and
        # the 18 of the cadence were about to become typed constants in
        # a template, which is a number nobody owns. Emitted here with
        # its provenance, because the two figures are not the same kind
        # of thing: one is measured and one is an upper bound.
        "publication_cadence": {
            "publications_per_year": 36,
            "publishes_on": "the 1st, 11th and 21st of each month",
            "window_days": "10, except the 21st which runs to month end",
            "observed_lag_days": {
                "2026-07-21": {"value": 9, "basis": "measured: window "
                               "closed 31 July, first seen published "
                               "2026-08-09 by crops/probe_asap.py"},
                "2026-07-11": {"value": 8, "basis": "UPPER BOUND, not a "
                               "measurement: present in a cache pull "
                               "dated 28 July, so published by then"},
            },
            "age_days": {
                "floor": 9, "peak": 19,
                "means": "the age of the newest observation CYCLES. It "
                         "is at the floor the day a dekad publishes and "
                         "grows by one each day until the next lands, "
                         "roughly ten days later. Quoting the floor as "
                         "the property is the error corrected in D-148.",
            },
            "_render": "the CURRENT age must be computed at render from "
                       "`dekad` against today, never stored. A stored "
                       "age is wrong the day after it is written.",
        },
        # D-104: state the baseline window and whether the current
        # reading sits inside it, rather than leaving it to be inferred.
        # Three chats inferred it wrongly in one day: VD decided fires
        # must use a fitted distribution, I decided heat must, and
        # design decided crops includes its current year. All three
        # diagnoses turned on the same unstated premise and all three
        # were wrong. It is uniform across this channel, so it is stated
        # once here; every rank additionally carries its own `of` and
        # `basis`, which is what makes a single datum self-describing.
        # Product's gap-versus-end requirement, stated once because it
        # is identical for every series here. A consumer reads expected
        # slots from this, present and missing from the datum.
        "series_declaration": {
            "first": BASE_FIRST,
            "last": int(latest_dekad[:4]),
            "expected_slots": int(latest_dekad[:4]) - BASE_FIRST + 1,
            # due_slots exists so the contract is uniform across
            # channels, and for crops it EQUALS expected_slots. Stated
            # rather than defaulted, because product asked to be told.
            #
            # Every series here is indexed by YEAR at one fixed dekad,
            # not by period within a season. A year's slot becomes due
            # the moment that dekad is published, and the series is only
            # emitted once the current year's value exists. So there is
            # no NOT YET state: a slot is due or it is outside the
            # window. The four states collapse to three here.
            #
            # The not-yet case product describes is real for a series
            # indexed by dekad WITHIN a season, which is the shape of
            # the England trajectory. Crops does not emit one. If it
            # ever does, due_slots stops equalling expected_slots and
            # this comment is the thing to delete.
            "due_slots": int(latest_dekad[:4]) - BASE_FIRST + 1,
            "due_equals_expected_because": "these series are indexed by "
                                           "year at one fixed dekad, so "
                                           "a slot is never pending. "
                                           "There is no NOT YET state in "
                                           "this channel's series.",
            "applies_to": "every `series` in this file, at country and "
                          "region level. Each carries `series_span` with "
                          "`present` and `missing`.",
            "blindness": "a slot that is present but is not a "
                         "measurement is marked at the DATUM, not "
                         "counted here. Instruments carry `absent` and "
                         "`absent_because` across four states; places "
                         "that never enter `places` carry a reason and "
                         "an `ours` flag in `skipped`, which separates "
                         "our own fetch failure from a fact about ASAP.",
            "why": "24 values in a 26-year record and 24 values in a "
                   "24-year record are otherwise the same payload, so a "
                   "renderer stretches what it has and turns a gap into "
                   "an end.",
        },
        "baseline": {
            "basis": f"{BASE_FIRST}-{BASE_LAST}, same dekad of each year",
            "first": BASE_FIRST,
            "last": BASE_LAST,
            "n": BASE_LAST - BASE_FIRST + 1,
            "current_year_in_baseline": False,
            "unit": "same dekad of each year, never a rolling window",
            "means": f"every rank, percentile and z on this channel is "
                     f"computed against {BASE_LAST - BASE_FIRST + 1} "
                     f"prior observations, {BASE_FIRST}-{BASE_LAST}, at "
                     f"the SAME dekad. The current year is NOT in the "
                     f"baseline, so a z has no (n-1)/sqrt(n) ceiling. "
                     f"A rank of `N of 26` counts the 25 baseline years "
                     f"plus the current one.",
        },
        "rate_legend": rate_legend(),
        "rate_count_baseline": rate_count_baseline(
            rate_panels,
            (int(latest_dekad[5:7]) - 1) * 3
            + ((int(latest_dekad[8:10]) - 1) // 10) + 1,
            int(latest_dekad[:4])) if rate_panels else None,
        "global": build_global(per_place_oriented,
                               int(latest_dekad[:4])) if per_place_oriented
                  else None,
        "dekad": latest_dekad,
        # Two forms, because the footer has a length budget and a
        # renderer truncating the long one lands mid-sentence on
        # "The indicator is". Choosing where to cut a methods line is a
        # decision about what a reader must not lose, so it belongs
        # here rather than in a character count.
        "method_short": "FPAR cumulated z-score, ASAP crop mask, "
                        "growing cycle only",
        "method": "FPAR cumulated z-score, ASAP crop mask, restricted "
                  "to the growing cycle. The indicator is cumulative "
                  "over the season, so one dekad encodes the season to "
                  "date.",
        "places_reported": len(places),
        "places_skipped": len(skipped),
        "skipped": skipped,
        "places": places,
    }


def build_shares():
    """Country-commodity production shares from USDA PSD.

    RETURNS None WHEN THE PSD CACHE IS ABSENT, and that is the whole
    point of this docstring. It used to guard each file with .exists()
    and then concat unconditionally, so with neither file present it
    raised "No objects to concatenate".

    crops/.cache/psd is gitignored, so in CI neither file is ever there.
    The scheduled refresh therefore failed five days running, 25 to 29
    August, each after pulling for about an hour and three quarters. It
    had built stress_current.json correctly BEFORE reaching this
    function, and then exited 1, so the whole dekad was discarded over
    an artifact that does not change dekad to dekad: PSD is ANNUAL
    production data.

    The channel sat on 2026-08-01 for five days with 2026-08-11
    published, one day short of its own staleness bound, because a
    yearly reference table was missing from a machine that never had it.
    """
    frames = []
    for f in ("psd_grains_pulses.csv", "psd_oilseeds.csv"):
        if (PSD / f).exists():
            frames.append(pd.read_csv(PSD / f, dtype={"Month": str}))
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    d = d[d.Attribute_Description == "Production"]

    rows = []
    for com, g in d.groupby("Commodity_Description"):
        year = int(g.Market_Year.max()) - 1      # last complete year
        y = g[g.Market_Year == year]
        world = y[y.Country_Name.isin(["World"])].Value.sum()
        if world <= 0:
            world = y[~y.Country_Name.isin(
                ["World", "European Union"])].Value.sum()
        if world <= 0:
            continue
        for _, r in y.iterrows():
            if r.Country_Name in ("World",):
                continue
            if r.Value <= 0:
                continue
            rows.append({
                "commodity": com,
                "country": r.Country_Name,
                "market_year": year,
                "production": float(r.Value),
                "unit": r.Unit_Description,
                "world_total": float(world),
                "share_of_world": round(float(r.Value) / float(world), 5),
                "vintage": f"{int(r.Calendar_Year)}-{r.Month}",
                "source": "USDA FAS PSD",
                "authorship": "agency",
                "qualifiers": [{
                    "kind": "no_revision_history",
                    "text": "USDA PSD holds one current estimate per "
                            "cell, not a vintage series. The stamp is "
                            "when this figure last changed, not a "
                            "revision history.",
                }],
            })
    rows.sort(key=lambda r: (r["commodity"], -r["share_of_world"]))
    return {
        "_generated_from": "crops/.cache/psd (no fetch performed)",
        "_note": "Shares let a condition index be expressed as a supply "
                 "number. Arithmetic over a published table, never a "
                 "forecast.",
        "rows": len(rows),
        "shares": rows,
    }


def _fill_saturation_rate(places: list) -> None:
    """Substitute the real rank-1 share into every severity.is_not.

    The share is a property of the PUBLISHED SET, so it cannot be known
    while an individual place is being built, which is why it was typed
    in the first place.

    It read "roughly one country in seven" and went stale the moment
    MIN_UNITS dropped to 1: 123 places became 165 and the true figure
    moved to about one in nine. A hand-typed statistic inside a string
    whose whole job is to describe a statistic is the defect this
    channel keeps finding, and it is the reason `caveat` and the rate
    claims are computed rather than written.

    Refuses loudly on an unmatched anchor rather than skipping it. A
    substitution that silently matches nothing leaves a stale number
    reading as a fresh one, which is exactly the failure being fixed.
    """
    ranked = [q for q in places if (q.get("severity") or {}).get("rank")]
    at1 = [q for q in ranked if q["severity"]["rank"] == 1]
    if not ranked:
        return
    one_in = round(len(ranked) / len(at1)) if at1 else 0
    WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
             12: "twelve"}
    phrase = (f"{len(at1)} of the {len(ranked)} published countries, "
              f"about one in {WORDS.get(one_in, str(one_in))},")
    missed = [q["place"] for q in places
              if "is_not" in (q.get("severity") or {})
              and "SATURATION_RATE" not in q["severity"]["is_not"]]
    for q in places:
        sev = q.get("severity") or {}
        if "SATURATION_RATE" in sev.get("is_not", ""):
            sev["is_not"] = sev["is_not"].replace("SATURATION_RATE", phrase)
    if missed:
        raise SystemExit(
            f"_fill_saturation_rate: {len(missed)} severity block(s) carry "
            f"no SATURATION_RATE anchor, first {missed[:3]}. The sentence "
            "has been edited without the anchor, so its figure is now "
            "hand-typed and will go stale. Refusing rather than emitting "
            "a payload where some copies are computed and some are not.")
    print(f"  severity saturation: {phrase.rstrip(',')}")

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-mixed-dekads", action="store_true",
                    help="emit even when a place's instruments are read "
                         "at different dekads. Only with a reason.")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    catalogue = json.loads(
        (HERE / "asap_countries.json").read_text(encoding="utf-8")
    )["countries"]

    stress = build_stress(catalogue, allow_mixed=args.allow_mixed_dekads)
    (OUT / "stress_current.json").write_text(
        json.dumps(stress, indent=1) + "\n", encoding="utf-8")
    print(f"stress_current.json: {stress['places_reported']} places, "
          f"{stress['places_skipped']} skipped, dekad {stress['dekad']}")

    # NOTHING BELOW THIS LINE MAY FAIL THE PROCESS.
    #
    # stress_current.json is on disk above, complete and correct. The CI
    # job commits crops/data/ in a SEPARATE, LATER step, so a non-zero
    # exit here does not merely skip an enrichment: `set -e` fails the
    # build step and Actions then skips the commit entirely, discarding a
    # payload that was already written and already right.
    #
    # Not hypothetical. build_shares() raised on a missing gitignored
    # cache and did exactly this on five consecutive runs, 25 to 30
    # August 2026. The channel served a three-week-old dekad throughout
    # and every automated check stayed green, because nothing compared
    # what the source had published against what we held. That gap is
    # now crops/check_pipeline.py; this is the other half.
    #
    # The workflow cannot fix this from its side. It sees one exit code
    # and cannot know which half of the script produced it, so only this
    # file can say which work is optional. The guarantee belongs here.
    #
    # A missing enrichment leaves the previous committed artifact in
    # place: stale, but internally consistent, and PSD is annual so it
    # does not move dekad to dekad anyway. A discarded payload stops the
    # channel. Those two costs are not close.
    try:
        shares = build_shares()
        if shares is None:
            # Loud, and NOT fatal. The dekad payload above is already
            # written and correct; the committed production_shares.json
            # stays as it is rather than being replaced by nothing.
            print("  NOTE: crops/.cache/psd is absent, so production_shares.json "
                  "was NOT rebuilt and the committed one is unchanged. That is "
                  "correct in CI, where the cache is gitignored: PSD is annual "
                  "and does not change dekad to dekad. Refresh it deliberately "
                  "rather than as a side effect of a dekad build.")
        else:
            (OUT / "production_shares.json").write_text(
                json.dumps(shares, indent=1) + "\n", encoding="utf-8")
            print(f"production_shares.json: {shares['rows']} country-commodity rows")
    except Exception as exc:
        # Kept DISTINCT from the shares-is-None branch above on purpose.
        # "The cache was absent" and "the code raised" are two different
        # claims about why the file did not change, and collapsing them
        # would report a bug as a routine CI condition.
        print(f"::warning::production_shares.json was NOT rebuilt: {exc!r}")
        print("::warning::This is not fatal and the dekad is unaffected: "
              "stress_current.json is written and correct, and remains "
              "committable. The committed production_shares.json is "
              "unchanged. Worth a look, because this path means a bug "
              "rather than an absent cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
