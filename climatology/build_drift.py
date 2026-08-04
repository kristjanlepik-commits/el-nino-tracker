#!/usr/bin/env python3
"""Baseline drift: how far the normal itself has moved, per region.

WHAT THIS IS. D-068's minimum shippable version. Not the shared
climatology service D-045 describes; deliberately not. Product took the
region-reconciliation question that made the full service large, on the
grounds that "what geography does a reader get an answer about" is a
product decision before it is a data one. This computes only what Heat's
drift sentence needs, from one dataset, for a handful of named boxes.

THE CLAIM IT SUPPORTS, and only this one:

    the night-time normal for <region> moved +X degrees between
    1961-1990 and 1991-2020

Heat separated three claims that had been wearing two sentences:
  A  July 2026 nights against 1991-2020        ERA5, theirs
  B  the 1961-1990 to 1991-2020 shift          THIS FILE
  C  July 2026 ranked inside 1961-1990         unsupported here

Only B lives here. C needs a current value in the same series as the
distribution, and cannot come from this dataset (see below).

WHY A FROZEN DATASET IS THE RIGHT ONE, which is counterintuitive.
Berkeley's 1 degree grids stopped updating: measured from the S3
headers, TMIN is dated 2025-01-10 and TMAX 2024-10-17, and the file
itself runs 1850.04 to 2024.79. That kills claim C outright. It does not
touch B at all, because 1961-1990 and 1991-2020 are CLOSED periods that
can never change. So for B this dataset is not merely adequate today, it
is permanently adequate, and there is no refresh cadence, no publication
lag, and no staleness guard to design around.

Checked from the artifact rather than the product description, after
that exact mistake was made twice in one day by two chats on two
datasets: the description says 1833 to present, the file says 1850 to
2024.

WHY THE ANOMALY FIELD RATHER THAN ABSOLUTE TEMPERATURE. Berkeley ships
`temperature` as an anomaly against its own internal climatology, plus
that `climatology` separately. The difference between two period means
of the anomaly equals the difference of the absolute means, because the
climatology term cancels. So B is computable without ever reconstructing
absolute temperature, and the answer does not depend on which reference
period Berkeley happened to use.

Run:  .venv/bin/python climatology/build_drift.py
Out:  climatology/data/drift.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "climatology" / ".cache"
OUT = ROOT / "climatology" / "data" / "drift.json"

EARLY = (1961, 1990)
CURRENT = (1991, 2020)

# Heat's provisional set, explicitly NOT a contract. These follow the
# live anomaly rather than a channel design, and Heat flagged that their
# ERA5 anomaly boxes are different geography again: 38-56N/7W-17E and
# 28-45N/115-76W, the latter stopping at 115W and not reaching the
# Pacific Northwest. A page showing both must not imply one region.
REGIONS = {
    "iberia":            {"lat": (36, 44), "lon": (-9, 3)},
    "italy_c_med":       {"lat": (37, 46), "lon": (7, 18)},
    "us_southwest":      {"lat": (31, 40), "lon": (-120, -108)},
    "us_pacific_nw":     {"lat": (42, 49), "lon": (-125, -116)},
}

VARIANTS = {"tmin": "Complete_TMIN_LatLong1.nc",
            "tmax": "Complete_TMAX_LatLong1.nc"}


def _period_mean(da: xr.DataArray, year: xr.DataArray,
                 weights: xr.DataArray, lo: int, hi: int):
    """Area-weighted mean anomaly over a closed year range.

    cos(latitude) weighting is not optional: a 1 degree cell at 49N has
    about two thirds the area of one at 31N, and an unweighted mean over
    a tall box silently over-counts the poleward end.
    """
    sel = da.where((year >= lo) & (year <= hi + 0.999), drop=True)
    if sel.time.size == 0:
        return None, 0
    # Mean over time first, then weighted mean over space, so months
    # with partial coverage do not bias the spatial weighting.
    tmean = sel.mean("time", skipna=True)
    w = weights.where(np.isfinite(tmean))
    total = float(w.sum())
    if total <= 0:
        return None, 0
    return float((tmean * w).sum() / total), int(sel.time.size)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out: dict = {
        "_readme": (
            "Baseline drift only: how far the 1961-1990 to 1991-2020 normal "
            "moved, per region. This is claim B in Heat's decomposition. It "
            "is NOT a current anomaly and NOT a ranking of any recent month; "
            "those need a different series. Do not add this number to an "
            "ERA5 anomaly to produce a counterfactual, which would be "
            "arithmetic across sources."
        ),
        "source": "Berkeley Earth, Complete_{TMIN,TMAX}_LatLong1.nc, 1 degree",
        "source_note": (
            "The 1 degree grids are no longer updated (TMIN dated 2025-01-10, "
            "TMAX 2024-10-17; data runs to 2024.79). That is irrelevant to "
            "this file: both baselines are closed historical periods and can "
            "never change, so this product is permanently adequate for drift "
            "and permanently unable to support a current-year claim."
        ),
        "baselines": {"early": f"{EARLY[0]}-{EARLY[1]}",
                      "current": f"{CURRENT[0]}-{CURRENT[1]}"},
        "units": "degrees Celsius",
        "computed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regions": {},
    }

    for variant, fname in VARIANTS.items():
        path = CACHE / fname
        if not path.exists():
            print(f"  missing {path}, skipping {variant}")
            continue
        ds = xr.open_dataset(path, decode_times=False)
        temp = ds["temperature"]
        year = ds["time"]
        lat = ds["latitude"]
        # cos(latitude) for cell area, times land fraction. The land term
        # matters less than it looks and the measurement is worth keeping:
        # Berkeley's gridding extends over coastal water, so the Italy and
        # central Mediterranean box has 65 finite cells against only 39
        # that are more than half land. Applying the mask moves the drift
        # by +0.020 C there and by 0.006 or less everywhere else, because
        # a systematic marine offset largely cancels in a DIFFERENCE of
        # two period means.
        #
        # Applied anyway, since this is a land-temperature claim and the
        # cost is nothing. Recorded so nobody re-derives the sensitivity:
        # it was measured, not assumed, after a neighbouring channel
        # published rainfall averaged over ocean.
        weights = (np.cos(np.deg2rad(lat)).broadcast_like(temp.isel(time=0))
                   * ds["land_mask"])

        for name, box in REGIONS.items():
            la, lo_ = box["lat"], box["lon"]
            sub = temp.sel(latitude=slice(*la), longitude=slice(*lo_))
            w = weights.sel(latitude=slice(*la), longitude=slice(*lo_))

            early, n_e = _period_mean(sub, year, w, *EARLY)
            curr, n_c = _period_mean(sub, year, w, *CURRENT)
            row = out["regions"].setdefault(name, {"box": box})
            if early is None or curr is None:
                row[variant] = {"error": "no data in one or both periods"}
                continue
            row[variant] = {
                "drift_c": round(curr - early, 3),
                "early_anom_c": round(early, 3),
                "current_anom_c": round(curr, 3),
                "months_early": n_e,
                "months_current": n_c,
            }
        ds.close()

    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for name, row in out["regions"].items():
        bits = []
        for v in ("tmin", "tmax"):
            d = row.get(v, {})
            bits.append(f"{v} {d['drift_c']:+.2f}" if "drift_c" in d else f"{v} n/a")
        print(f"  {name:16} {'  '.join(bits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
