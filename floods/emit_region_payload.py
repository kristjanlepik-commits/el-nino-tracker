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


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def load_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def rainfall_series(base_path, region, window_days):
    recs = load_jsonl(base_path)
    by = collections.defaultdict(list)
    for r in recs:
        by[r["year"]].append(r)
    years = {y: v for y, v in by.items() if len(v) == window_days}
    totals = {y: sum(x["mean_mm"] for x in v) for y, v in years.items()}
    return totals, {y: max(x["max_mm"] for x in v) for y, v in years.items()}


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
    ap.add_argument("--flood-baseline", required=True)
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
    totals, peaks = rainfall_series(args.rain_baseline, args.region, expected)
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
            "values_present": expected,
            "baseline_years": len(hist),
            "value": round(cur, 1),
            "basis": {"median": round(med, 1), "x_median": round(cur / med, 2),
                      "rank": rank_of(cur, hist.values()), "of": len(hist) + 1},
            "peak_day_mm": round(peaks[year], 0),
            "verdict": "measured",
        })

    # ---- flood extent ---------------------------------------------------
    fl = flood_series(args.flood_baseline, expected)
    if fl:
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
        payload["series"].append(s)

    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(json.dumps(payload, indent=1))


if __name__ == "__main__":
    sys.exit(main())
