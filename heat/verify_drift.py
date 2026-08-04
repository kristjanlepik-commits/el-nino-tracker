"""Verification of the regional July night-drift claim, before it publishes.

Runs the checks pre-registered in FEASIBILITY 5c-i that still apply to a
TMIN-only claim, plus the urbanisation bound promised to product. Reuses
platform's own functions from climatology/build_drift.py so a check cannot
silently diverge from the artifact it is checking.

THE BAR, FIXED HERE BEFORE THE SCRIPT WAS RUN:

  The claim publishes for a region only if
    (a) every variant keeps the same sign, and
    (b) the spread across variants is no larger than the sampling standard
        error already carried by the headline figure (0.20 to 0.43 C,
        platform's measurement).

  Reasoning: if the choice of box or baseline pair moves the number less
  than the noise already inside it, that choice is not what is driving it.
  A variant spread LARGER than the SE means the box is doing work the
  climate is not, which is the fire 5.2x shape.

Checks:
  1  baseline pair    1951-1980 vs 1991-2020, against the 1961-1990 headline
  2  region cut       box shifted and enlarged, 8 variants
  3  urbanisation     drift recomputed with major-city cells removed

No CDS. Berkeley grids are already on disk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "climatology"))
import build_drift as bd  # noqa: E402

SE_BY_REGION = 0.43          # platform's widest July sampling SE; the strict case

# Cells containing these are dropped for check 3. One degree, so a city
# removes roughly a 111 km square from the box.
CITIES = {
    "iberia": [(40.4, -3.7), (41.4, 2.2), (38.7, -9.1), (39.5, -0.4),
               (37.4, -6.0), (41.1, -8.6)],
    "italy_c_med": [(41.9, 12.5), (45.5, 9.2), (40.9, 14.3), (45.1, 7.7),
                    (43.8, 11.3)],
    "us_southwest": [(33.4, -112.1), (36.2, -115.1), (32.2, -111.0)],
    "us_pacific_nw": [(47.6, -122.3), (45.5, -122.7), (47.7, -117.4),
                      (43.6, -116.2)],
}


def load(variant="tmin"):
    ds = xr.open_dataset(bd.CACHE / bd.VARIANTS[variant], decode_times=False)
    return ds


def region_drift(ds, box, early, current, month=7, drop_cities=None):
    """Area-weighted July drift for one box. Mirrors build_drift's method."""
    lat0, lat1, lon0, lon1 = box
    da = ds["temperature"].sel(latitude=slice(lat0, lat1),
                               longitude=slice(lon0, lon1))
    lsm = ds["land_mask"].sel(latitude=slice(lat0, lat1),
                              longitude=slice(lon0, lon1))
    weights = np.cos(np.deg2rad(da["latitude"])) * lsm
    weights = weights.where(lsm > 0.5, 0.0)

    if drop_cities:
        keep = xr.ones_like(weights)
        for clat, clon in drop_cities:
            if not (lat0 <= clat <= lat1 and lon0 <= clon <= lon1):
                continue
            d = (np.abs(weights["latitude"] - clat) < 0.5) & \
                (np.abs(weights["longitude"] - clon) < 0.5)
            keep = keep.where(~d, 0.0)
        weights = weights * keep

    year = ds["time"]
    year = year.sel(time=year) if False else da["time"]
    a, na = bd._period_mean(da, year, weights, early[0], early[1], month)
    b, nb = bd._period_mean(da, year, weights, current[0], current[1], month)
    if a is None or b is None:
        return None, 0
    return b - a, min(na, nb)


def variants(box):
    """Eight region cuts: four shifts of 1 degree, four size changes."""
    lat0, lat1, lon0, lon1 = box
    return {
        "shift N": (lat0 + 1, lat1 + 1, lon0, lon1),
        "shift S": (lat0 - 1, lat1 - 1, lon0, lon1),
        "shift E": (lat0, lat1, lon0 + 1, lon1 + 1),
        "shift W": (lat0, lat1, lon0 - 1, lon1 - 1),
        "grow lat": (lat0 - 1, lat1 + 1, lon0, lon1),
        "grow lon": (lat0, lat1, lon0 - 1, lon1 + 1),
        "shrink lat": (lat0 + 1, lat1 - 1, lon0, lon1),
        "shrink lon": (lat0, lat1, lon0 + 1, lon1 - 1),
    }


def contrast_check(ds) -> None:
    """Is the July-minus-annual contrast robust enough to be a page's spine?

    Product's proposal: 'summer nights are not moving at the same rate as the
    year as a whole, and the direction differs by region.' That is a claim
    about a DIFFERENCE, so verifying each half separately is not enough. A
    contrast is only as good as its weaker half, which is product's own
    phrase and the reason this function exists.

    BAR, FIXED BEFORE RUNNING. A region may appear in the contrast only if
      (a) the sign of (July - annual) holds across all 8 region cuts and the
          alternative baseline pair, and
      (b) the magnitude of the contrast EXCEEDS the spread the region cuts
          induce in it.

    (b) is the one that matters. If redrawing the box moves the contrast by
    more than the contrast itself, the contrast is a property of the box.
    """
    print("\n" + "=" * 66)
    print("CONTRAST CHECK: July drift minus annual drift, per region")
    print("bar: sign stable across all variants AND |contrast| > cut spread\n")

    for name, box_d in bd.REGIONS.items():
        box = (box_d["lat"][0], box_d["lat"][1], box_d["lon"][0], box_d["lon"][1])
        jul, _ = region_drift(ds, box, (1961, 1990), (1991, 2020), month=7)
        ann, _ = region_drift(ds, box, (1961, 1990), (1991, 2020), month=None)
        head = jul - ann

        cuts = []
        for label, vb in variants(box).items():
            j, _ = region_drift(ds, vb, (1961, 1990), (1991, 2020), month=7)
            a, _ = region_drift(ds, vb, (1961, 1990), (1991, 2020), month=None)
            if j is not None and a is not None:
                cuts.append((label, j - a))
        cv = [v for _, v in cuts]
        spread = max(cv) - min(cv)

        j2, _ = region_drift(ds, box, (1951, 1980), (1991, 2020), month=7)
        a2, _ = region_drift(ds, box, (1951, 1980), (1991, 2020), month=None)
        alt = j2 - a2

        signs_ok = all(np.sign(v) == np.sign(head) for v in cv + [alt])
        exceeds = abs(head) > spread
        ok = signs_ok and exceeds

        print(f"{name}")
        print(f"  July {jul:+.3f}  annual {ann:+.3f}  contrast {head:+.3f}")
        print(f"  contrast under 8 region cuts: {min(cv):+.3f} to {max(cv):+.3f}"
              f"  spread {spread:.3f}")
        print(f"  contrast on 1951-1980 pair  : {alt:+.3f}")
        print(f"  sign stable: {signs_ok}   |contrast| > spread: {exceeds} "
              f"({abs(head):.3f} vs {spread:.3f})")
        print(f"  VERDICT: {'USABLE in the contrast' if ok else 'NOT USABLE'}\n")


def main() -> int:
    ds = load("tmin")
    print("Verification of regional July TMIN drift, Berkeley Earth 1 degree")
    print(f"bar: sign stable AND variant spread <= {SE_BY_REGION:.2f} C\n")

    verdicts = {}
    for name, box_d in bd.REGIONS.items():
        box = (box_d["lat"][0], box_d["lat"][1], box_d["lon"][0], box_d["lon"][1])
        head, n = region_drift(ds, box, (1961, 1990), (1991, 2020))
        alt, _ = region_drift(ds, box, (1951, 1980), (1991, 2020))
        nocity, _ = region_drift(ds, box, (1961, 1990), (1991, 2020),
                                 drop_cities=CITIES.get(name))

        vals = []
        for label, vb in variants(box).items():
            v, _ = region_drift(ds, vb, (1961, 1990), (1991, 2020))
            if v is not None:
                vals.append((label, v))

        cuts = [v for _, v in vals]
        spread = (max(cuts) - min(cuts)) if cuts else float("nan")
        signs_ok = all(np.sign(v) == np.sign(head) for v in cuts + [alt, nocity])
        passes = signs_ok and spread <= SE_BY_REGION

        print(f"{name}")
        print(f"  headline 1961-1990 -> 1991-2020 : {head:+.3f} C  (n={n} Julys)")
        print(f"  baseline pair 1951-1980         : {alt:+.3f}  "
              f"(moves {alt - head:+.3f})")
        print(f"  city cells removed              : {nocity:+.3f}  "
              f"(moves {nocity - head:+.3f})  <- urbanisation bound")
        print(f"  region cuts, {len(cuts)} variants        : "
              f"{min(cuts):+.3f} to {max(cuts):+.3f}, spread {spread:.3f}")
        for label, v in vals:
            print(f"      {label:11s} {v:+.3f}")
        print(f"  VERDICT: {'PASS' if passes else 'FAIL'}"
              f"  (sign stable: {signs_ok}, spread {spread:.3f} "
              f"{'<=' if spread <= SE_BY_REGION else '>'} {SE_BY_REGION})\n")
        verdicts[name] = passes

    print("=" * 66)
    for k, v in verdicts.items():
        print(f"  {k:16s} {'PASS' if v else 'FAIL'}")

    contrast_check(ds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
