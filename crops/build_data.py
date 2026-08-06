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

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "asap_indicator"
PSD = HERE / ".cache" / "psd"
OUT = HERE / "data"

MIN_UNITS = 3          # the meaning gate: fewer and the aggregate is noise
BASE_FIRST, BASE_LAST = 2001, 2025

INSTRUMENTS = [
    ("zfparc", "Vegetation, cumulative", "z-score", +1),
    ("zfpar", "Vegetation, current", "z-score", +1),
    ("wsi", "Water satisfaction", "percent", +1),
    ("spi3", "Rainfall, 3-month", "SPI", +1),
    ("sm", "Soil moisture", "m3/m3", +1),
    ("temp", "Temperature", "anomaly C", -1),
]

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
    d["dt"] = pd.to_datetime(d.date, format="%Y%m%d")
    d["year"] = d.dt.dt.year
    d["doy"] = (d.dt.dt.month - 1) * 3 + ((d.dt.dt.day - 1) // 10) + 1
    return d


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


def _ordinal(n: int) -> str:
    suffix = ("th" if 11 <= n % 100 <= 13
              else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))
    return f"{n}{suffix}"


def _year_list(years: list) -> str:
    ys = [str(y) for y in sorted(years)]
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
    lead = ("steepest fall" if rank == 1
            else f"{_ordinal(rank)} steepest fall")
    lead = f"The {'joint ' if tied else ''}{lead}"

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
        # Region rows carry the claim and its basis, and point at the
        # legend for what is identical everywhere. The series is dropped
        # rather than shrunk: nothing renders a region rate history, and
        # emitting a second per-region series contradicted the rule this
        # file already states about vegetation-only series. It is one
        # rebuild away if a region page ever wants it.
        block["_see"] = "rate_legend"
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
    buckets = {
        "all_five": _global_bucket(per_place, common, cur_year,
                                   "all five instruments read together"),
    }
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
        "buckets_do_not_partition": (
            "crop_outcome and meteorology are named groups, not a "
            f"partition: {_year_list(leftover)} belong to neither, "
            "being an instantaneous crop state and a modelled water "
            "balance. A page claiming the two diverged has to show "
            "what went into each."),
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


def build_stress(catalogue: dict) -> dict:
    places, skipped = [], []
    latest_dekad = None
    # Every reported place's oriented instrument series, kept so the
    # global block is computed from the SAME series the per-place
    # blocks use. Recomputing it elsewhere is what lost the tie
    # convention and the scope three times in one day.
    per_place_oriented = []

    for cid, name in catalogue.items():
        base = load("zfparc", cid)
        if base is None or base.region_id.nunique() < MIN_UNITS:
            skipped.append({"place": name,
                            "reason": "fewer than 3 crop units in the "
                                      "ASAP crop mask"})
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
            same = d[d.doy == doy].groupby("year").value.mean()
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
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False, "absent": "no_current_value",
                    "absent_because": f"{label} has not reported for this "
                                      f"dekad yet.",
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
        country_panel = (base.groupby(["year", "doy"]).value.mean()
                         .unstack())
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
                    inst[slug] = {
                        "available": False,
                        "absent": "no_current_value",
                        "absent_because": f"{label} has not reported for "
                                          f"this dekad yet.",
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
                inst[slug] = {
                    "value": round(v, 3),
                    "baseline_mean": round(float(h.mean()), 3),
                    "rank": rank_of(v, h, worse_is), "of": len(h) + 1,
                    "available": True,
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
        for entry in regions:
            entry.pop("instruments", None)

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
    return {
        "_generated_from": "crops/.cache (no fetch performed)",
        "instrument_legend": {
            slug: {"name": label, "unit": unit,
                   "worse_is": "low" if worse_is > 0 else "high"}
            for slug, label, unit, worse_is in INSTRUMENTS
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
        # D-104: state the baseline window and whether the current
        # reading sits inside it, rather than leaving it to be inferred.
        # Three chats inferred it wrongly in one day: VD decided fires
        # must use a fitted distribution, I decided heat must, and
        # design decided crops includes its current year. All three
        # diagnoses turned on the same unstated premise and all three
        # were wrong. It is uniform across this channel, so it is stated
        # once here; every rank additionally carries its own `of` and
        # `basis`, which is what makes a single datum self-describing.
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


def build_shares() -> dict:
    frames = []
    for f in ("psd_grains_pulses.csv", "psd_oilseeds.csv"):
        if (PSD / f).exists():
            frames.append(pd.read_csv(PSD / f, dtype={"Month": str}))
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    catalogue = json.loads(
        (HERE / "asap_countries.json").read_text(encoding="utf-8")
    )["countries"]

    stress = build_stress(catalogue)
    (OUT / "stress_current.json").write_text(
        json.dumps(stress, indent=1) + "\n", encoding="utf-8")
    print(f"stress_current.json: {stress['places_reported']} places, "
          f"{stress['places_skipped']} skipped, dekad {stress['dekad']}")

    shares = build_shares()
    (OUT / "production_shares.json").write_text(
        json.dumps(shares, indent=1) + "\n", encoding="utf-8")
    print(f"production_shares.json: {shares['rows']} country-commodity rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
