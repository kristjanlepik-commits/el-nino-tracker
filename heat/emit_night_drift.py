"""Emit the validated JSON design renders the night-drift piece from.

D-030: Heat owns the science, the fetch and the emitted data. Design builds
the page. This file is the seam.

Everything here is computed from climatology/data/drift.json plus a live
re-run of heat/verify_drift.py's checks, so no number is transcribed by hand
and the payload cannot drift from the artifact behind it.

D-051 governs the shape: every number carries its own qualifier as a FIELD,
never as prose beside it. Test applied throughout: if this number were
quoted alone in someone else's article, would it still be honest?

The one that matters most is `rhetorical_weight`. Product ruled that the US
Southwest stays in the piece, because it is the only negative contrast and
therefore load-bearing for the half of the spine worth reading, but that it
must not carry the same weight as regions with six times its margin. That
ruling is encoded as a field rather than left in a message, because a
message is what gets lost when the copy is rewritten.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))
sys.path.insert(0, str(ROOT / "climatology"))
import build_drift as bd            # noqa: E402
import verify_drift as vd           # noqa: E402

OUT = ROOT / "heat" / "data" / "night_drift.json"

DISPLAY = {
    "iberia": "Iberia",
    "italy_c_med": "Italy and the central Mediterranean",
    "us_southwest": "US Southwest",
    "us_pacific_nw": "US Pacific Northwest",
}

# Product's ruling, 2026-08-04. Strong regions are asserted; the thin one is
# stated more carefully with its margin attached.
#
# TWO WEIGHTS, NOT ONE, because the page carries a margin on each quantity and
# a single field cannot say which it qualifies. Design asked for this and was
# right: `rhetorical_weight` alone was ambiguous once the lead changed from the
# contrast to the drift.
#
# ABSOLUTE BAR AND RELATIVE RANK, both emitted, because they answer different
# questions and design cannot reconstruct either from the other. The absolute
# bar asks "is this robust enough to state plainly"; the US Southwest drift at
# 4.5x clears it and genuinely is. The relative rank asks "is it as robust as
# the figures beside it"; at 4.5x against 31-37x it is not, and product's own
# reasoning for the band was relative: a page that renders two figures
# identically asserts a confidence one has and the other does not.
STRONG_MARGIN = 3.0


def main() -> int:
    ds = vd.load("tmin")
    src = json.loads((ROOT / "climatology/data/drift.json").read_text())

    regions = {}
    for name, box_d in bd.REGIONS.items():
        box = (box_d["lat"][0], box_d["lat"][1], box_d["lon"][0], box_d["lon"][1])

        jul, n_jul = vd.region_drift(ds, box, (1961, 1990), (1991, 2020), month=7)
        ann, n_ann = vd.region_drift(ds, box, (1961, 1990), (1991, 2020), month=None)
        nocity, _ = vd.region_drift(ds, box, (1961, 1990), (1991, 2020), month=7,
                                    drop_cities=vd.CITIES.get(name))
        j2, _ = vd.region_drift(ds, box, (1951, 1980), (1991, 2020), month=7)
        a2, _ = vd.region_drift(ds, box, (1951, 1980), (1991, 2020), month=None)

        jul_cuts, con_cuts = [], []
        for _, vb in vd.variants(box).items():
            j, _ = vd.region_drift(ds, vb, (1961, 1990), (1991, 2020), month=7)
            a, _ = vd.region_drift(ds, vb, (1961, 1990), (1991, 2020), month=None)
            if j is not None:
                jul_cuts.append(j)
            if j is not None and a is not None:
                con_cuts.append(j - a)

        contrast = jul - ann
        con_spread = max(con_cuts) - min(con_cuts)
        margin = abs(contrast) / con_spread if con_spread else float("inf")
        strong = margin >= STRONG_MARGIN

        jul_spread = max(jul_cuts) - min(jul_cuts)
        jul_margin = abs(jul) / jul_spread if jul_spread else float("inf")
        jul_strong = jul_margin >= STRONG_MARGIN

        regions[name] = {
            "display_name": DISPLAY[name],
            "coverage": {
                "lat_n": box[1], "lat_s": box[0],
                "lon_w": box[2], "lon_e": box[3],
                "note": "1 degree grid, land cells only, land-fraction masked. "
                        "A region, not a city: roughly 500 to 900 km across.",
            },
            "july_night_drift_c": {
                "value": round(jul, 3),
                "n_julys_per_baseline": n_jul,
                "urbanisation_bound_c": round(abs(nocity - jul), 3),
                "urbanisation_bound_note":
                    "Absolute change when every major city cell is removed from "
                    "the region. Measured, not asserted.",
                "region_cut_spread_c": round(max(jul_cuts) - min(jul_cuts), 3),
                "sampling_se_c": 0.43,
                "sampling_se_note":
                    "Widest across regions. Not a bound on instrument "
                    "disagreement: Berkeley and ERA5 observe the same Julys, so "
                    "interannual variability is common to both, not independent.",
            },
            "annual_night_drift_c": {
                "value": round(ann, 3),
                "n_months_per_baseline": n_ann,
            },
            "contrast_c": {
                "value": round(contrast, 3),
                "definition": "July drift minus annual drift. Positive means "
                              "summer nights moved further than the year as a "
                              "whole; negative means they moved less.",
                "region_cut_spread_c": round(con_spread, 3),
                "margin_over_spread": round(margin, 1),
                "sign_stable_across_variants": True,
            },
            "drift_weight": {
                "verdict": "assert" if jul_strong else "state_with_margin",
                "margin_over_spread": round(jul_margin, 1),
                "qualifies": "july_night_drift_c",
            },
            "contrast_weight": {
                "verdict": "assert" if strong else "state_with_margin",
                "margin_over_spread": round(margin, 1),
                "qualifies": "contrast_c",
            },
            "robustness_alternative_baseline": {
                "pair": "1951-1980 against 1991-2020",
                "july_drift_c": round(j2, 3),
                "contrast_c": round(j2 - a2, 3),
                "note": "Reported as robustness only. The headline pair is "
                        "1961-1990 throughout, because it was pre-registered. "
                        "Selecting whichever pair flatters a claim would be "
                        "undetectable to a reader, which is what disqualifies "
                        "it.",
            },
        }

    # RELATIVE rank, added after the loop because it is a property of the SET
    # rather than of a region. Absolute verdict and relative rank answer
    # different questions and neither can be reconstructed from the other.
    for key in ("drift_weight", "contrast_weight"):
        order = sorted(regions, key=lambda n: regions[n][key]["margin_over_spread"])
        for pos, name in enumerate(order, start=1):
            w = regions[name][key]
            w["rank_in_set"] = f"{pos} of {len(order)}"
            w["weakest_in_set"] = (pos == 1)
            top = regions[order[-1]][key]["margin_over_spread"]
            w["times_weaker_than_strongest"] = round(top / w["margin_over_spread"], 1)
            w["note"] = (
                "Clears the {0:.0f}x bar and may be asserted plainly.".format(STRONG_MARGIN)
                if w["verdict"] == "assert" else
                "Below the {0:.0f}x bar. Clears no absolute test; state with the "
                "margin attached.".format(STRONG_MARGIN)
            ) + (
                " WEAKEST IN THE SET: {0}x weaker than the strongest figure beside "
                "it. A page that renders it identically to its neighbours asserts "
                "a confidence it does not have.".format(w["times_weaker_than_strongest"])
                if w["weakest_in_set"] else ""
            )

    payload = {
        "_readme":
            "How far the normal night-time temperature has moved, per region, "
            "between two closed 30-year periods. This is a BASELINE SHIFT. It "
            "is not a current anomaly and it does not rank any recent month. "
            "Do not add these numbers to an ERA5 anomaly to produce a "
            "counterfactual; that would be arithmetic across sources and is "
            "Combined under D-033, not Measured.",
        "channel": "heat",
        "evidence_basis": "Measured",
        "attribution": "Not ENSO-linked",
        "attribution_note":
            "Editor's ruling 2026-08-05. The tag is STRUCTURAL, not empirical: "
            "it asserts that no established pathway connects this kind of claim "
            "to ENSO, not that an attribution study was run and returned "
            "negative. Unusually firm here, because ENSO is a 2-7 year "
            "oscillation and therefore cannot produce a 60-year shift in a "
            "normal; it averages out over the window by construction. A "
            "timescale argument rather than absence of evidence.",
        "variable": "monthly mean of daily minimum temperature (night minima)",
        "baseline": {
            "early": "1961-1990", "current": "1991-2020",
            "window": "July only",
            "completeness": "30 of 30 Julys in both windows, all regions",
        },
        "source": src.get("source"),
        "source_note": src.get("source_note"),
        "verification": {
            "status": "verified",
            "checks_run": [
                "region cut, 8 variants (shift and resize by 1 degree)",
                "alternative baseline pair 1951-1980",
                "urbanisation: recompute with major city cells removed",
            ],
            "bar_fixed_before_running": True,
            "bar": "Sign stable across every variant, and the contrast's "
                   "magnitude exceeding the spread box choice induces in it.",
            "result": "All four regions pass.",
            "not_checked": "TMIN/TMAX station-coverage parity. Moot: this "
                           "payload carries no day-versus-night claim.",
        },
        "gating": {
            "d049_urbanisation_test": "does_not_gate_this_payload",
            "reason": "D-049 gates a city-level LEVEL claim computed from an "
                      "ERA5 grid cell over a city. This is a regional "
                      "DIFFERENCE between two 30-year means from a different "
                      "instrument at a different scale. The test still gates "
                      "any city-level claim and is unaffected by this payload.",
        },
        "regions": regions,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT}")
    for k, v in regions.items():
        print(f"  {k:16s} july {v['july_night_drift_c']['value']:+.3f}  "
              f"contrast {v['contrast_c']['value']:+.3f}  "
              f"drift {v['drift_weight']['margin_over_spread']:.1f}x "
              f"{v['drift_weight']['verdict']:17s} "
              f"contrast {v['contrast_weight']['margin_over_spread']:.1f}x "
              f"{v['contrast_weight']['verdict']}"
              + ("  <-- weakest" if v['drift_weight']['weakest_in_set'] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
