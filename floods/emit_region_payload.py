"""Emit the validated JSON a region page is rendered from.

The channel-to-design handoff under D-030: floods emits data and owns
that it is methodologically correct; design builds the front end. This
never renders anything.

Two instruments travel side by side and are never merged. Rainfall
(IMERG) and flood extent (MODIS MCDWD) correlate at only Spearman +0.23
outside extreme events, so a single blended number would be a claim
neither instrument makes.

Every series carries three counts, per product's ratification of
2026-08-05:

    expected_slots   the full period, fixed before any data arrives
    due_slots        how many COULD exist given as_of AND instrument
                     latency, which is not the same as days elapsed
    values           what we actually have

from which gap (due minus values), not-yet (expected minus due) and end
follow by arithmetic. `due_slots` must account for latency: flood extent
uses a 3-day composite, so yesterday cannot exist yet and computing due
from calendar position would render it a gap.

And every flood-extent slot carries its own observability, because slot
counts make ABSENCE machine-readable and not BLINDNESS. A day present at
0.12 observability is a placeholder, not a measurement.

**The qualification gate is the point of this file.** A region only
gets a flood-extent verdict if its own history shows the instrument can
see it. Manila fails: across 20 complete years the correlation between
observability and the flood measure is +0.82, and 2012, the Habagat
year that put much of Metro Manila underwater, reads ZERO flood pixels
at 0.02 observability. The cloud that caused the flood blinded the
sensor. A naive ranking would have called 2012 an unremarkable year.

So the emitted verdict for such a region is `cannot_say`, with the
reason machine-readable. That is a first-class output, not a
suppressed row.
"""

import argparse
import collections
import datetime as dt
import json
import os
import sys

import numpy as np

# Derived in FEASIBILITY.md section 9, from data rather than imported.
COUNT_FLOOR = 300          # below this the two MODIS products stop agreeing
OBS_DEPENDENCE_MAX = 0.50  # Spearman(observability, measure) above this means
                           # the series is ranking clear skies, not floods
LATENCY_DAYS = {"flood_extent": 3, "rainfall": 1}


# NULL CONTROL, per D-128. The observability-dependence test was run
# against data where the effect is known to be absent: 2000 shuffles of
# the real flood counts against the real observability values. Mean
# -0.000, 95% of nulls within -0.43 to +0.44. Manila's measured +0.82
# exceeds 100% of them.
#
# The trap this avoids, and it is not hypothetical. Fire's first
# observability test correlated a RATE, putting the same term in a
# numerator and a denominator, and returned -0.69 on synthetic data
# where the effect was absent. Had this test used flood-per-observed
# instead of an absolute count, its own null control returns mean
# -0.272 rather than 0.000, and the measurement would have been reading
# Pearson's 1897 spurious correlation of ratios.
#
# So the measure below is an ABSOLUTE pixel count, deliberately, and
# observability is a separate fraction of the box. No shared term.


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def load_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def rainfall_series(base_path, region, window_days, current_year=None):
    """Totals per year, on a window harmonised across every year.

    A SOURCE GAP USED TO DELETE THE CURRENT YEAR SILENTLY. The old rule
    was len(v) == window_days, which drops any year missing a day. IMERG
    published nothing for 2026-08-10, so on the Spanish fortnight that
    rule discarded 2026 itself and the payload would have carried a
    27-year baseline and no current value, with nothing saying why.

    The fix is to compare like with like rather than to drop a year.
    Days absent from the CURRENT year are excluded from EVERY year, so
    all totals are summed over the same calendar days. Dropping the day
    from 2026 alone would dock it one day of rain and bias it low, which
    on a 14-day window is around 7% of the total and enough to move a
    rank.

    The excluded days are returned rather than swallowed, because a
    harmonised window is a smaller claim than the nominal one and the
    page has to be able to say so.
    """
    recs = load_jsonl(base_path)
    by = collections.defaultdict(dict)
    for r in recs:
        by[r["year"]][r["date"][5:]] = r

    # The current year defines the usable window. Without one there is
    # nothing to harmonise against, so fall back to the nominal rule.
    excluded = []
    if current_year is not None and current_year in by:
        usable = set(by[current_year])
        nominal = {d for y in by for d in by[y]}
        excluded = sorted(nominal - usable)
    else:
        usable = None

    years, totals, peaks = {}, {}, {}
    for y, dd in by.items():
        days = usable if usable is not None else set(dd)
        if usable is None and len(dd) != window_days:
            continue
        if usable is not None and not usable.issubset(dd):
            continue          # this year genuinely lacks a day 2026 has
        years[y] = [dd[d] for d in sorted(days)]
        totals[y] = sum(x["mean_mm"] for x in years[y])
        peaks[y] = max(x["max_mm"] for x in years[y])
    return totals, peaks, sorted(usable) if usable else [], excluded


def flood_series(base_path, window_days):
    recs = load_jsonl(base_path)
    by = collections.defaultdict(list)
    for r in recs:
        by[r["year"]].append(r)
    out = {}
    for y, v in by.items():
        if len(v) != window_days:
            continue
        fl = sum(int(x["flood_hist"].get("2", 0)) + int(x["flood_hist"].get("3", 0))
                 for x in v)
        px = sum(x["box_px"] for x in v)
        ob = sum(x["observed_px"] for x in v)
        out[y] = {"flood_px": fl, "observed_frac": round(ob / px, 4) if px else None}
    return out


# ---------------------------------------------------------------------
# WHEN A RANK LICENSES A SUPERLATIVE
#
# Product's split (2026-08-10): design generates the finding line, the
# editor owns the wording, floods decides when the CLAIM is permitted.
# This is that decision, computed rather than judged per page.
#
# Heat's 59-59 Valencia tie is why this is not design's to decide: an
# ordinal is a claim about separation, and separation is a property of
# the data.

MIN_RECORD = 20        # below this, no ordinal. Rank 2 of 8 is not "on record".
TIE_MARGIN = 0.02      # values within 2% of the median apart are not separable
EXTREME_RANK = 3       # top three may carry an ordinal
EXTREME_RATIO = 1.5    # ...but only if the value is actually far from normal


def classify(value, others, median, complete):
    """Decide what class of claim the data permits. Never phrasing."""
    n = len(others) + 1
    margin = TIE_MARGIN * median if median else 0.0
    tied = [o for o in others if abs(o - value) <= margin]
    strictly_above = sum(1 for o in others if o > value + margin)
    rank = strictly_above + 1

    out = {"rank": rank, "of": n, "tied_with_n": len(tied),
           "ordinal_safe": True, "claim": None, "guards": []}

    if n < MIN_RECORD:
        out["ordinal_safe"] = False
        out["guards"].append(f"record is {n} periods, under the {MIN_RECORD} minimum")
    if tied:
        # An ordinal asserts separation. If another year sits inside the
        # margin, "second wettest" is arbitrary between them.
        out["ordinal_safe"] = False
        out["guards"].append(f"{len(tied)} other period(s) within {TIE_MARGIN:.0%} "
                             f"of this value; the ordinal is not separable")

    ratio = value / median if median else None

    # Incompleteness biases a TOTAL downward, so it biases the rank low.
    # That makes a high rank safe (it can only rise) and a calm reading
    # UNSAFE, which is the opposite of the intuition. The dangerous
    # sentence on a short period is the reassuring one.
    if not complete:
        out["guards"].append("period incomplete; the total is understated, so the "
                             "rank is a floor and a calm reading is NOT permitted")

    if ratio is None:
        out["claim"] = "no_baseline"
    elif rank <= EXTREME_RANK and ratio >= EXTREME_RATIO and out["ordinal_safe"]:
        out["claim"] = "extreme_ordinal"        # "second wettest in 27 years"
    elif rank <= EXTREME_RANK and ratio < EXTREME_RATIO:
        # Top of a flat distribution. The ordinal is true and oversells:
        # every year near the top looks like this one.
        out["claim"] = "extreme_flat"
        out["guards"].append(f"top-{EXTREME_RANK} but only {ratio:.2f}x the median; "
                             f"the distribution is flat and an ordinal alone oversells")
    elif rank <= max(3, n // 4):
        out["claim"] = "notable"                # "wetter than most years"
    elif rank >= n - max(3, n // 4) + 1:
        out["claim"] = "low"                    # context, never a headline here
    else:
        out["claim"] = "normal"                 # D-043: this must be sayable
    if not complete and out["claim"] in ("normal", "low"):
        out["claim"] = "incomplete_indeterminate"
    return out


def rank_of(value, others):
    """1 = highest. Rank, not ratio: rank is non-parametric and immune to
    the variance-regime problem Fire hit with a fixed multiple."""
    return 1 + sum(1 for o in others if o > value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--label", required=True, help="human name for the region")
    ap.add_argument("--window", required=True, help="MM-DD:MM-DD")
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    ap.add_argument("--rain-baseline", required=True)
    # Optional since 2026-08-16. Omitting it yields verdict not_assessed
    # on the flood series, never cannot_say, and never silence.
    ap.add_argument("--flood-baseline", default=None)
    ap.add_argument("--flood-current", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w0, w1 = args.window.split(":")
    m0, d0 = (int(x) for x in w0.split("-"))
    m1, d1 = (int(x) for x in w1.split("-"))
    as_of = dt.date.fromisoformat(args.as_of)
    year = as_of.year
    start = dt.date(year, m0, d0)
    end = dt.date(year, m1, d1)
    expected = (end - start).days + 1

    payload = {
        "region_id": args.region,
        "label": args.label,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "as_of": as_of.isoformat(),
        "authorship": "agency",
        "attribution": "attribution_pending",
        "series": [],
        "notes": [],
    }

    # ---- rainfall -------------------------------------------------------
    totals, peaks, used_days, excluded_days = rainfall_series(
        args.rain_baseline, args.region, expected, current_year=year)
    hist_all = {y: v for y, v in totals.items() if y != year}
    if year not in totals and hist_all:
        # A series with a baseline but no current value must still be
        # EMITTED, marked. Omitting it makes the absence invisible, which
        # is the same defect as a short payload that does not say so.
        payload["series"].append({
            "id": "rainfall",
            "instrument": "GPM IMERG Late Run v07",
            "measures": "rainfall, NOT flooding",
            "units": "mm, area mean over the region",
            "expected_slots": expected,
            "due_slots": min(expected, max(0, (as_of - start).days + 1
                                           - LATENCY_DAYS["rainfall"])),
            "values_present": 0,
            "baseline_years": len(hist_all),
            "verdict": "awaiting_data",
        })
    if year in totals:
        hist = hist_all
        cur = totals[year]
        med = float(np.median(list(hist.values())))
        due = min(expected, max(0, (as_of - start).days + 1 - LATENCY_DAYS["rainfall"]))
        payload["series"].append({
            "id": "rainfall",
            "instrument": "GPM IMERG Late Run v07",
            "measures": "rainfall, NOT flooding",
            "units": "mm, area mean over the region",
            "expected_slots": expected,
            "due_slots": due,
            # Was hardcoded to `expected`, which asserted a full window
            # even when the source had a gap. It is the count of days
            # actually summed.
            "values_present": len(used_days) or expected,
            # A harmonised window is a SMALLER claim than the nominal
            # one, so it travels rather than being quietly absorbed. The
            # page must be able to say "13 of 14 days, the same 13 in
            # every year" instead of implying a fortnight.
            "window_days_nominal": expected,
            "window_days_compared": len(used_days) or expected,
            "days_excluded": excluded_days,
            "days_excluded_reason": (
                "absent from the source for the current period, so excluded "
                "from every year to keep the comparison like for like; "
                "excluding them from the current year alone would understate "
                "it and bias its rank low"
            ) if excluded_days else None,
            "baseline_years": len(hist),
            "value": round(cur, 1),
            "basis": {"median": round(med, 1), "x_median": round(cur / med, 2),
                      "rank": rank_of(cur, hist.values()), "of": len(hist) + 1},
            "finding": classify(cur, list(hist.values()), med, True),
            "peak_day_mm": round(peaks[year], 0),
            "verdict": "measured",
        })

    # ---- flood extent ---------------------------------------------------
    # A THIRD STATE, added 2026-08-16 for the Spanish fast-reaction case.
    #
    # This file already distinguishes "we cannot see this region" from "we
    # have not looked yet". A rainfall-only region is neither: the flood
    # baseline was never built, so the instrument has not been assessed at
    # all. Until now that case emitted NO flood series whatsoever, and a
    # page rendering the payload would have shown a rainfall answer with
    # nothing at all saying the second instrument was missing. Silent
    # omission is the one outcome this file exists to prevent, and it was
    # reachable by simply not passing an argument.
    #
    # not_assessed is therefore a first-class verdict. It must never be
    # rendered as cannot_say: cannot_say is a MEASURED claim about the
    # instrument, earned from 20+ years of observability, and borrowing it
    # for "we did not fetch it" would launder an absence into a finding.
    fl = flood_series(args.flood_baseline, expected) if args.flood_baseline else {}
    if not args.flood_baseline:
        payload["series"].append({
            "id": "flood_extent",
            "instrument": "NASA MODIS MCDWD 3-Day composite",
            "measures": "standing water outside the reference water mask",
            "units": "250m pixels",
            "expected_slots": expected,
            "due_slots": 0,
            "values_present": 0,
            "baseline_years": 0,
            "verdict": "not_assessed",
            "not_assessed_reason": [
                "no flood-extent baseline has been built for this region, so "
                "the instrument's ability to see it is unknown and untested"
            ],
            "not_assessed_summary": (
                "we have not measured flooding here; this page reports "
                "rainfall only"
            ),
        })
    if fl:
        # The current year must not sit in its own comparison set. The
        # rainfall path already excluded it; this one did not, so a
        # payload was reporting the current period as tied with itself.
        # Caught by the tie detector on its first real run, which is the
        # detector doing more than it was written to do. Same family as
        # the coverage gate that computed its denominator from the data
        # under test.
        fl.pop(year, None)
        yrs = sorted(fl)
        counts = np.array([fl[y]["flood_px"] for y in yrs], float)
        obs = np.array([fl[y]["observed_frac"] for y in yrs], float)
        dep = spearman(obs, counts)
        med_ct = float(np.median(counts))
        qualifies = (dep <= OBS_DEPENDENCE_MAX) and (med_ct >= COUNT_FLOOR)

        cur_recs = load_jsonl(args.flood_current) if args.flood_current else []
        cur_px = sum(r.get("flood_px", 0) for r in cur_recs) or None
        cur_obs = (round(sum(r["observed_px"] for r in cur_recs)
                         / sum(r["box_px"] for r in cur_recs), 4)
                   if cur_recs else None)
        due = min(expected, max(0, (as_of - start).days + 1 - LATENCY_DAYS["flood_extent"]))

        s = {
            "id": "flood_extent",
            "instrument": "NASA MODIS MCDWD 3-Day composite",
            "measures": "standing water outside the reference water mask",
            "units": "250m pixels",
            "expected_slots": expected,
            "due_slots": due,
            "values_present": len(cur_recs),
            # Declared ON THE FIELD rather than left for a validator to
            # trip over, following the crops pattern in
            # research/spec_series_payload.md. Crops can never have a
            # pending slot; floods has the mirror-image exception.
            "present_may_exceed_due_because": (
                "due_slots is computed from a conservative 3-day composite "
                "latency. When the product publishes sooner, present "
                "legitimately exceeds due. A validator asserting "
                "present <= due would fail this series for being correct."
            ),
            "baseline_years": len(yrs),
            "observability": {
                "current": cur_obs,
                "baseline_median": round(float(np.median(obs)), 3),
                "baseline_min": round(float(obs.min()), 3),
            },
            "qualification": {
                "observability_dependence": round(dep, 2),
                "max_allowed": OBS_DEPENDENCE_MAX,
                "median_count": int(med_ct),
                "count_floor": COUNT_FLOOR,
                "qualifies": bool(qualifies),
            },
        }
        if qualifies and cur_px:
            hist = counts
            s["value"] = cur_px
            s["basis"] = {"median": int(med_ct),
                          "x_median": round(cur_px / med_ct, 2) if med_ct else None,
                          "rank": rank_of(cur_px, hist), "of": len(hist) + 1}
            s["finding"] = classify(cur_px, list(hist), med_ct,
                                    len(cur_recs) >= due)
            s["verdict"] = "measured"
        elif qualifies and not cur_recs:
            s["verdict"] = "awaiting_data"
        elif qualifies:
            # The region CAN be measured; we just do not have the current
            # period yet. Emitting cannot_say here would be the same defect
            # this file exists to prevent: a verdict that is internally
            # consistent and says nothing. "We cannot see this region" and
            # "we have not looked yet" are opposite statements.
            s["verdict"] = "awaiting_data"
        else:
            s["verdict"] = "cannot_say"
            why = []
            if dep > OBS_DEPENDENCE_MAX:
                why.append(
                    f"across {len(yrs)} years the flood measure tracks how much "
                    f"the satellite could see (rank correlation {dep:+.2f}), so a "
                    f"ranking here would rank clear skies rather than floods")
            if med_ct < COUNT_FLOOR:
                why.append(
                    f"the median week holds {int(med_ct)} flood pixels, below the "
                    f"{COUNT_FLOOR} at which the two MODIS products stop agreeing")
            s["cannot_say_reason"] = why
            # Design asked whether they may compress the reasons into one
            # line. They may not compose it; it is a claim about the
            # instrument. So it is authored here, from computed values,
            # and travels as a field.
            s["cannot_say_summary"] = (
                "the satellite that measures flooding here cannot see through "
                "the cloud that causes it"
                if dep > OBS_DEPENDENCE_MAX else
                "there is too little standing water here for the measurement "
                "to be stable")
        payload["series"].append(s)

    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(json.dumps(payload, indent=1))


if __name__ == "__main__":
    sys.exit(main())
