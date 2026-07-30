"""Refresh country_history.json for the CURRENT trailing complete window.

THE DEFECT THIS FIXES. The same-week baseline was built once, for one
window, by a one-off job. The trailing complete window advances every
day. After the day the baseline was built the two never align again, so
build_events.py refused every run with "nothing to do" and the
detections layer on the live site froze while the hectares layer kept
updating around it. It sat frozen from 27 to 29 July 2026. Nothing
crashed and nothing was wrong on the page except that it was old, which
is why it went unnoticed: a partial failure that leaves a plausible
page is worse than a crash.

The guard in build_events.py was right to refuse. What was missing was
any way to give it a baseline for today's window, which is what this
does. Run it before build_events.py, every day.

COST. 45 countries x 14 years x 7 days = 4,410 billed days, roughly 12
minutes at the throttled rate. That is affordable daily. It is not
affordable to run this concurrently with build_full_baselines.py: two
processes each throttling to 6 days/s sum to 12/s against a ceiling
near 8.3/s, so both would fail. Pause one or run them in sequence.

Superseded by full daily history once fires/data/full_history/ covers
all 45 countries, since daily counts sum to any window without a fetch.
Until then this is the bridge, and it is deliberately the same shape:
same sensor, same confidence filter, same point-in-polygon assignment.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import threading
import time
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from fires import _http

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.path.join(REPO, "fires", "data", "countries.geo.json")
OUT = os.path.join(REPO, "fires", "data", "country_history.json")
ROSTER = os.path.join(REPO, "fires", "data", "tracked_countries.json")
KEY = open(os.path.expanduser("~/.firms_map_key")).read().strip()

YEARS = list(range(2012, 2026))
WORKERS = 3
DAYS_PER_SEC = 6.0


class _Bucket:
    """Token bucket over billed lobe-days. See build_full_baselines."""

    def __init__(self, rate):
        self.rate, self.tokens = rate, rate
        self.t = time.monotonic()
        self.lock = threading.Lock()

    def take(self, n):
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.rate * 10,
                                  self.tokens + (now - self.t) * self.rate)
                self.t = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                wait = (n - self.tokens) / self.rate
            time.sleep(wait)


BUCKET = _Bucket(DAYS_PER_SEC)


def ray(ring, x, y):
    ins = np.zeros(len(x), bool)
    x1, y1 = ring[:-1, 0], ring[:-1, 1]
    x2, y2 = ring[1:, 0], ring[1:, 1]
    for i in range(len(x1)):
        c = (y1[i] > y) != (y2[i] > y)
        if not c.any():
            continue
        ins ^= c & (x < (x2[i] - x1[i]) * (y - y1[i]) / (y2[i] - y1[i])
                    + x1[i])
    return ins


def load_geo():
    geo = json.load(open(GEO))
    rings, boxes, names = {}, {}, {}
    for f in geo["features"]:
        g = f["geometry"]
        ps = ([g["coordinates"]] if g["type"] == "Polygon"
              else g["coordinates"])
        rs = [np.vstack([np.array(p[0]), np.array(p[0])[:1]]) for p in ps]
        allv = np.vstack(rs)
        lon, lat = allv[:, 0], allv[:, 1]
        s_, n_ = float(lat.min()), float(lat.max())
        # Same antimeridian split as build_full_baselines: Russia would
        # otherwise request a global-width strip and time out.
        if float(lon.max()) - float(lon.min()) > 340:
            box = [[-180.0, s_, float(lon[lon < 0].max()), n_],
                   [float(lon[lon >= 0].min()), s_, 180.0, n_]]
        else:
            box = [[float(lon.min()), s_, float(lon.max()), n_]]
        rings[f["id"]], boxes[f["id"]] = rs, box
        names[f["id"]] = f["properties"]["name"]
    return rings, boxes, names


RINGS, BOX, NAMES = load_geo()


def trailing_window(today: date) -> tuple:
    """Last 7 whole UTC days ending yesterday.

    Whole days only, never a partial one. A day is only complete after
    its final afternoon overpass has cleared processing everywhere, so
    including today would publish a half-day count that reads as a
    die-down.
    """
    end = today - timedelta(days=1)
    return end - timedelta(days=6), end


def fetch_one(iso, start: date, year: int) -> int:
    """Same calendar window in one prior year, one country."""
    total = 0
    for off, days in ((0, 5), (5, 2)):
        cur = date(year, start.month, start.day) + timedelta(days=off)
        BUCKET.take(days * len(BOX[iso]))
        frames = []
        for w, s, e, n in BOX[iso]:
            url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                   f"{KEY}/VIIRS_SNPP_SP/{w},{s},{e},{n}/{days}/"
                   f"{cur.isoformat()}")
            for a in (1, 2, 3):
                try:
                    frames.append(_http.read_csv(url))
                    break
                except Exception:
                    if a == 3:
                        # Same rule as the full builder: a year is whole
                        # or absent. A silently short baseline year
                        # inflates every multiple computed against it.
                        raise RuntimeError(f"{iso} {cur} failed 3 tries")
                    time.sleep(6 * a)
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 \
            else frames[0]
        if len(df) and "confidence" in df.columns:
            df = df[~df["confidence"].astype(str).str.lower()
                    .isin(["l", "low"])]
        if not len(df):
            continue
        pts = np.column_stack([df["longitude"].values,
                               df["latitude"].values])
        hit = np.zeros(len(pts), bool)
        for r in RINGS[iso]:
            hit |= ray(r, pts[:, 0], pts[:, 1])
        total += int(hit.sum())
    return total


def main() -> None:
    today = date.today()
    start, end = trailing_window(today)
    win = f"{start:%m-%d}..{end:%m-%d}"
    # Iterate the ROSTER, never the previous output.
    #
    # This read `list(prev["countries"])`, which made the tracked set a
    # ratchet: a country that failed one run was absent from the next
    # run's input and could never be retried. On 2026-07-30 Algeria,
    # Iraq, Mexico and Namibia were lost exactly that way, Algeria while
    # carrying the highest year-to-date burnt-area anomaly in the set at
    # 14.2x, and nothing anywhere reported it. The drop-on-failure rule
    # below is still right; what was wrong was that the drop was
    # permanent rather than for one window.
    prev = json.load(open(OUT))
    roster = json.load(open(ROSTER))["countries"]
    isos = [i for i in roster if i in BOX]
    if len(isos) != len(roster):
        print(f"  roster entries with no polygon, skipped: "
              f"{sorted(set(roster) - set(isos))}", file=sys.stderr)
    # "Window already covered" is not the same as "nothing to do". A
    # country added to the roster today has no baseline at any window,
    # and the early return would skip it until the window happened to
    # roll, which is how a roster edit could look applied and do nothing.
    absent = [i for i in isos if i not in prev.get("countries", {})]
    if prev.get("window") == win and not absent:
        print(f"baseline already covers {win}, nothing to do")
        return
    if prev.get("window") == win and absent:
        # Only the new ones need fetching; the rest are already correct
        # for this window, so do not spend the quota again.
        print(f"window {win} already covered; building {len(absent)} new "
              f"roster entries: {', '.join(absent)}", flush=True)
        isos = absent
        out_seed = dict(prev["countries"])
    else:
        out_seed = {}
        print(f"building baseline for {win} across {len(isos)} countries",
              flush=True)

    out, failed = dict(out_seed), []
    for i, iso in enumerate(isos, 1):
        try:
            with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = {y: ex.submit(fetch_one, iso, start, y)
                        for y in YEARS}
                hist = {str(y): f.result() for y, f in futs.items()}
        except Exception as exc:
            # Carry the previous window's year forward? No. A baseline
            # mixing two windows is silently wrong in a way no reader
            # could detect, which is exactly the class of defect this
            # file exists to end. Drop the country instead.
            failed.append(iso)
            print(f"  [{i}/{len(isos)}] {iso}: FAILED {exc}", flush=True)
            continue
        mean = sum(hist.values()) / len(hist)
        # A country new to the roster has no previous entry, so fall
        # back to the geometry rather than indexing prev and failing.
        pv = prev["countries"].get(iso, {})
        out[iso] = {"name": NAMES.get(iso, pv.get("name", iso)),
                    "box": pv.get("box") or BOX[iso][0],
                    "hist": hist, "mean": round(mean, 1)}
        print(f"  [{i}/{len(isos)}] {iso}: mean {mean:,.0f}", flush=True)

    # One retry pass before writing. A failure here costs the country a
    # whole window, and most failures are transient: a Malawi request
    # that failed three times in the full builder returned data on the
    # next attempt minutes later.
    if failed:
        print(f"  retrying {len(failed)}: {', '.join(failed)}", flush=True)
        still = []
        for iso in failed:
            try:
                with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
                    futs = {y: ex.submit(fetch_one, iso, start, y)
                            for y in YEARS}
                    hist = {str(y): f.result() for y, f in futs.items()}
            except Exception as exc:
                still.append(iso)
                print(f"  {iso}: FAILED AGAIN {exc}", flush=True)
                continue
            mean = sum(hist.values()) / len(hist)
            pv = prev["countries"].get(iso, {})
            out[iso] = {"name": NAMES.get(iso, pv.get("name", iso)),
                        "box": pv.get("box") or BOX[iso][0],
                        "hist": hist, "mean": round(mean, 1)}
            print(f"  {iso}: recovered, mean {mean:,.0f}", flush=True)
        failed = still

    if len(out) < len(roster) * 0.8:
        print(f"REFUSING to write: only {len(out)}/{len(roster)} countries "
              f"built. A baseline this thin would drop countries from the "
              f"page silently.", file=sys.stderr)
        raise SystemExit(1)

    doc = {"window": win, "sensor": "VIIRS_SNPP_SP", "years": "2012-2025",
           "built": datetime.utcnow().isoformat(timespec="seconds") + "Z",
           "countries": out}
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"wrote {len(out)} countries for window {win}")
    if failed:
        print(f"dropped: {', '.join(failed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
