#!/usr/bin/env python3
"""Per-country random-land cropland share. One-off, committed artifact.

WHY THIS IS PRECOMPUTED AND TRACKED. The share of detections on cropland
means nothing on its own; it only carries information against the share
of the COUNTRY that is cropland. That baseline is a property of the
country and the mask, not of this week, so recomputing it every run would
burn time to get the same number and would make the published ratio
depend on a 111 MB file being present at publish time.

Committing it also means the ratio stays auditable: a reader or a future
chat can see what the denominator was when a claim was made, rather than
having to reconstruct it from a raster that has since been revised.

Usage: python fires/build_cropland_baseline.py [--only ISO,ISO] [--n 6000]
"""
from __future__ import annotations

import argparse
import json
import zlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fires.cropland import CropMask, random_points_in, SOURCE_NOTE  # noqa: E402
from fires.build_events import load_rings  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(REPO, "fires", "data", "country_history.json")
OUT = os.path.join(REPO, "fires", "data", "cropland_baseline.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--n", type=int, default=6000)
    args = ap.parse_args()

    mask = CropMask()
    isos = sorted(json.load(open(HISTORY))["countries"])
    if args.only:
        isos = [i for i in args.only.split(",") if i in isos]
    rings_all = load_rings(isos)

    prev = {}
    if os.path.exists(OUT):
        prev = json.load(open(OUT)).get("countries", {})

    out, uncovered = {}, []
    for iso in isos:
        rings = rings_all.get(iso)
        if not rings:
            continue
        # STABLE SEED. hash() on a str is salted per process
        # (PYTHONHASHSEED), so this denominator moved 27.9 to 28.9 for
        # Serbia across three runs of the same code on the same data.
        # A published ratio whose denominator changes when you rerun the
        # builder is not reproducible, and nobody would see it drift
        # because each run looks self-consistent.
        seed = zlib.crc32(iso.encode()) % 10**6
        pts = random_points_in(rings, args.n, seed=seed)
        if len(pts) < args.n // 4:
            continue
        v = mask.sample(pts[:, 0], pts[:, 1])
        v = v[~np.isnan(v)]
        if len(v) == 0:
            continue
        covered = float((v > 0).mean()) >= 0.02
        if not covered:
            # All-zero is a coverage failure, not a country with no
            # fields. Recording it as 0% cropland would make every
            # detection there look "off cropland" for ever.
            uncovered.append(iso)
            out[iso] = {"covered": False, "n": len(v)}
            continue
        out[iso] = {
            "covered": True,
            "n": len(v),
            "mean_crop_pct": round(float(v.mean()), 2),
            "share_over_50": round(float((v > 50).mean()) * 100, 2),
        }
        print(f"  {iso}  mean {v.mean():5.1f}%   >50% {(v>50).mean()*100:5.1f}%")

    # --only MUST MERGE, NOT REPLACE. It did not, and a two-country
    # rerun silently reduced a 94-country baseline to two, which is a
    # denominator quietly vanishing for 92 countries rather than an
    # error anyone would see. `prev` was already loaded and unused.
    merged = dict(prev)
    merged.update(out)

    json.dump({
        "_readme": ("Share of each country's LAND that is cropland, from "
                    "ASAP crop mask v04, sampled at uniform random points "
                    "inside the country polygon. This is the denominator "
                    "for the detections-on-cropland ratio; without it the "
                    "numerator means nothing. 'covered': false means the "
                    "mask has no data there, which is NOT the same as no "
                    "cropland, and the ratio is withheld for that country."),
        "source": SOURCE_NOTE,
        "n_points": args.n,
        "countries": merged,
    }, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"\nwrote {os.path.relpath(OUT, REPO)}: {len(merged)} countries "
          f"in file, {len(out)} recomputed this run, "
          f"{len(uncovered)} without mask coverage")
    if uncovered:
        print("  no coverage:", ", ".join(uncovered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
