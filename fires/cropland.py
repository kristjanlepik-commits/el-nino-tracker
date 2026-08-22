#!/usr/bin/env python3
"""Per-detection cropland fraction, from a published crop mask (D-216 / C).

WHAT THIS ANSWERS. A country can post a record detection week that is
mostly farmers clearing fields, and FIRMS cannot tell that from a forest
fire. Until now this channel had no gate for it at all.

WHY NOT A HAND-DRAWN REGION, which was the cheaper plan. I drew one for
Serbia, a latitude line meant to select Vojvodina, and it was wrong: it
swept in the Djerdap gorge and Homolje highlands, forested mountains on
the wrong side of the line. It produced "53% of detections in the arable
north" when the true figure for Vojvodina is 1.8% against 23.8% of the
land area. That number reached a published post and a product ruling
before the mask refuted it. A stated-as-arbitrary threshold does not
help when the partition itself is meaningless.

THE STATISTIC IS A RATIO, NOT A SHARE, and that is the whole design.
"4% of detections are on cropland" means nothing without knowing what
share of the country IS cropland. So every reading is paired with a
random-land baseline for the same country, and the ratio is what carries
meaning:

    Serbia    3.9% of detections on crop vs 28.7% of random land   0.14
    Romania  49.9%                        vs 34.8%                 1.43

Romania is the positive control. Danube post-harvest burning is
documented there and the method finds enrichment; Serbia comes out
depleted sevenfold. A method that flagged everything, or nothing, would
be useless, and that pair is the evidence it does neither.

THE MASK. ASAP's crop mask v04, a 500 m global raster of percent
cropland per cell, published by the JRC alongside the ASAP warning
system. Read with PIL rather than rasterio: the repo has no geospatial
dependencies and CRO recorded that adding them is platform's call rather
than something to slip in. Only small windows are ever decoded, never
the whole 80640 x 29346 image.

COVERAGE MUST BE VERIFIED, NOT ASSUMED. A mask that stops at a national
border reads as "no cropland" and is indistinguishable from a country
with no fields. That would have fooled me a second time, in the same
direction, so verify_coverage() exists and the baseline builder refuses
a country whose random-land cropland share is implausibly flat.
"""
from __future__ import annotations

import os

import numpy as np

# PROVENANCE IS UNRESOLVED AND THAT IS A REAL GAP, recorded here rather
# than papered over. The raster reached this machine through CRO's work
# on tls-internal#16 and sits in crops/.cache, which is gitignored. No
# script in this repo fetches it and CRO's module has no URL for it.
#
# I first wrote a plausible-looking download URL here from the ASAP site
# and it was WRONG: that endpoint answers HTTP 200 with an HTML page, so
# a fetcher built on it would have written a few KB of markup to a .tif
# and every lookup afterwards would have failed in a way that pointed at
# the mask rather than at the URL. Same shape as the LAADS trap.
#
# Consequence, stated plainly: this channel's cropland block is NOT
# reproducible from a clean checkout today. It works here because the
# file happens to be on this laptop. Before CI can depend on it, someone
# has to establish where it actually comes from. Asked of CRO, who
# downloaded it.
SOURCE_URL = None
SOURCE_NOTE = ("ASAP crop mask v04, 500 m percent cropland. Obtained via "
               "the crops channel; canonical download not yet established.")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ours first. CRO's copy is a fallback because it is gitignored and not
# ours to depend on: a pipeline that silently needs another channel's
# cache is one `rm` away from a field that vanishes without explanation.
CANDIDATES = (
    os.path.join(REPO, "fires", ".cache", "asap_mask_crop_v04.tif"),
    os.path.join(REPO, "crops", ".cache", "asap_reference",
                 "asap_mask_crop_v04.tif"),
)
TILE = 1.0  # degrees; detections are grouped into tiles so each PIL crop
            # covers a cluster rather than the country's whole bounding box


def find_mask() -> str | None:
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return None


class CropMask:
    """Percent-cropland lookup over the ASAP mask. Windows only."""

    def __init__(self, path: str | None = None):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        self.path = path or find_mask()
        if not self.path:
            raise FileNotFoundError(
                "ASAP crop mask not found in fires/.cache/ or "
                "crops/.cache/. " + SOURCE_NOTE + " There is no fetcher "
                "for it yet, so a clean checkout cannot produce this "
                "block; the cropland field is withheld rather than "
                "guessed.")
        self.im = Image.open(self.path)
        tags = self.im.tag_v2
        scale, tie = tags.get(33550), tags.get(33922)
        if not scale or not tie:
            raise ValueError(
                f"{self.path} carries no GeoTIFF georeferencing tags "
                f"(33550 ModelPixelScale, 33922 ModelTiepoint). Without "
                f"them every lookup would be silently at the wrong place.")
        self.sx, self.sy = float(scale[0]), float(scale[1])
        self.ox, self.oy = float(tie[3]), float(tie[4])
        self.w, self.h = self.im.size

    def sample(self, lon, lat) -> np.ndarray:
        """Percent cropland at each (lon, lat). NaN outside the raster."""
        lon = np.asarray(lon, dtype=float)
        lat = np.asarray(lat, dtype=float)
        out = np.full(len(lon), np.nan)
        if not len(lon):
            return out
        px = ((lon - self.ox) / self.sx).astype(int)
        py = ((self.oy - lat) / self.sy).astype(int)
        inside = (px >= 0) & (px < self.w) & (py >= 0) & (py < self.h)
        # Group into tiles so one crop serves many points.
        keys = (np.floor(lon / TILE).astype(int),
                np.floor(lat / TILE).astype(int))
        for kx, ky in set(zip(keys[0].tolist(), keys[1].tolist())):
            m = inside & (keys[0] == kx) & (keys[1] == ky)
            if not m.any():
                continue
            x0, x1 = int(px[m].min()), int(px[m].max()) + 1
            y0, y1 = int(py[m].min()), int(py[m].max()) + 1
            win = np.asarray(self.im.crop((x0, y0, x1, y1)))
            out[m] = win[py[m] - y0, px[m] - x0]
        return out

    def verify_coverage(self, lon, lat, min_nonzero=0.02) -> bool:
        """Is the mask actually populated here?

        A mask that stops at a border returns all zeros, which reads as
        "no cropland anywhere" and is indistinguishable from a genuine
        absence of fields. Anywhere fires are tracked has SOME cropland,
        so an all-zero country is a coverage failure rather than a
        finding.
        """
        v = self.sample(lon, lat)
        v = v[~np.isnan(v)]
        return len(v) > 0 and float((v > 0).mean()) >= min_nonzero


def random_points_in(rings, n, seed=0):
    """Uniform points inside a country's polygon rings."""
    from fires.build_events import contains_points
    rng = np.random.default_rng(seed)
    allpts = np.vstack([r for r in rings])
    lo = allpts.min(axis=0)
    hi = allpts.max(axis=0)
    acc = []
    for _ in range(200):
        if len(acc) >= n:
            break
        cand = rng.uniform(lo, hi, size=(max(4000, n), 2))
        m = np.zeros(len(cand), dtype=bool)
        for r in rings:
            m |= contains_points(r, cand)
        acc.extend(cand[m].tolist())
    return np.asarray(acc[:n]) if acc else np.empty((0, 2))
