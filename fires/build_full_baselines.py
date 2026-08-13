"""Full-year daily detection baselines per country, 2012-2025.

WHY THIS EXISTS. build_events.py compares a trailing seven-day window
against a frozen same-week baseline. The trailing window moves every
day; a single-week baseline does not. So the two line up on exactly
one day in seven and the daily job correctly refuses on the other six.
Daily updates therefore need every day of history, not one week of it.
Paid once, because the science-quality archive is static.

It also unlocks the cumulative season-to-date view, since daily counts
sum to any window or any year to date.

RUNNING IT

    python fires/build_full_baselines.py

No arguments. Needs ~/.firms_map_key. Expect two to three days of
machine-awake time for all 45 countries; run under `caffeinate -i -m`
so idle sleep does not kill it. Note that caffeinate does NOT prevent
lid-close sleep on macOS.

RESUME. Safe to kill and restart at any point, and safe to run on a
machine that sleeps. Each country is one file under
fires/data/full_history/<ISO3>.json, written the moment its last year
completes. On restart, a country whose file already holds all 14 years
is skipped entirely, and a partially built country resumes at its
first missing year. Nothing is ever re-fetched.

COMMITTING BETWEEN SESSIONS. Output lands inside the repo precisely so
each night's progress can be committed:

    git add fires/data/full_history && git commit -m "fires: baselines, N countries"

Partial progress is valid and useful: the countries present are
complete, the rest are absent. Nothing half-written is ever stored.

THROUGHPUT AND THE RATE LIMIT. Single-threaded this ran at ~0.2
requests/second against an API that permits more, so Angola alone took
85 minutes. The work is latency-bound, hence the thread pool.

The allowance is 5,000 transactions per rolling 10 minutes, and a 5-day
request bills more than one transaction. Tuning the pool from 8 to 3
did not move consumption: the key sat near 4,970 either way. Two things
were happening at once and it took a while to separate them. Some of it
was genuine saturation. The rest was Russia, whose bounding box
collapsed to -180..180 because Chukotka crosses the antimeridian, so
every Russia request pulled a global-width strip and timed out. See the
BOX construction below.
"""
import concurrent.futures as cf
import json
import os
import threading
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from fires import _http, _quota

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.expanduser("~/.firms_map_key")
GEO = os.path.join(REPO, "fires", "data", "countries.geo.json")
SEED = os.path.join(REPO, "fires", "data", "country_history.json")
OUTDIR = os.path.join(REPO, "fires", "data", "full_history")

YEARS = list(range(2012, 2026))   # SNPP science-quality archive
# 8 workers consumed 4,982 of the 5,000-per-10-minute allowance and
# produced 43 failed chunks in three hours. A 5-day request counts as
# several transactions, not one, so concurrency has to sit well below
# the naive requests-per-second figure.
WORKERS = 3

# Throttle on the billed unit rather than on request count, because
# requests are not what is billed. Each lobe-day costs one token, so a
# 5-day chunk for a one-box country costs 5 and the same chunk for a
# two-box country costs 10, which is what it actually spends.
#
# 6.0/s is 72% of the 8.3/s ceiling, leaving headroom for the retry
# traffic that failures generate. Without headroom a failure spike
# becomes self-sustaining: retries push consumption up, which causes
# more failures, which produces more retries.
DAYS_PER_SEC = 6.0


class _Bucket:
    """Token bucket over billed lobe-days, shared by every worker."""

    def __init__(self, rate):
        self.rate = rate
        self.tokens = rate
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
os.makedirs(OUTDIR, exist_ok=True)
KEY = open(KEY_PATH).read().strip()


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def ray(ring, x, y):
    ins = np.zeros(len(x), bool)
    x1, y1 = ring[:-1, 0], ring[:-1, 1]
    x2, y2 = ring[1:, 0], ring[1:, 1]
    for i in range(len(x1)):
        c = (y1[i] > y) != (y2[i] > y)
        if not c.any():
            continue
        ins ^= c & (x < (x2[i]-x1[i])*(y-y1[i])/(y2[i]-y1[i]) + x1[i])
    return ins


geo = json.load(open(GEO))
RINGS, BOX = {}, {}
for f in geo["features"]:
    g = f["geometry"]
    ps = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    rings = [np.vstack([np.array(p[0]), np.array(p[0])[:1]]) for p in ps]
    allv = np.vstack(rings)
    RINGS[f["id"]] = rings
    lon, lat = allv[:, 0], allv[:, 1]
    s_, n_ = float(lat.min()), float(lat.max())
    # A country crossing the antimeridian collapses min/max longitude to
    # the whole globe. Russia is the case that exposed this: Chukotka
    # sits just past 180, so RUS came out as -180..180, a 14,436 sq deg
    # request against Canada's 3,672, and it timed out on all 14 years.
    # Results were never wrong (point-in-polygon still filters correctly)
    # but every request pulled most of the planet.
    #
    # Split into the two real lobes instead. Detection is a span wider
    # than any genuine country, not a hardcoded ISO list, so Fiji and
    # anything else added later is covered without a second fix.
    if float(lon.max()) - float(lon.min()) > 340:
        west = lon[lon < 0]
        east = lon[lon >= 0]
        BOX[f["id"]] = [[-180.0, s_, float(west.max()), n_],
                        [float(east.min()), s_, 180.0, n_]]
    else:
        BOX[f["id"]] = [[float(lon.min()), s_, float(lon.max()), n_]]


def _chunk(iso, cur, days):
    """One request, capped at 5 days by the API. Failures return {}."""
    # BOX[iso] is a LIST of boxes: one normally, two for a country that
    # crosses the antimeridian. Every lobe must succeed or the chunk
    # fails, for the same reason a partial year is refused below.
    BUCKET.take(days * len(BOX[iso]))
    frames = []
    for w, s, e, n in BOX[iso]:
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/"
               f"VIIRS_SNPP_SP/{w},{s},{e},{n}/{days}/{cur.isoformat()}")
        for a in (1, 2, 3):
            try:
                frames.append(_http.read_csv(url))
                break
            except _http.OverLimit:
                # Does NOT consume an attempt. The key is over its limit
                # because too many requests arrived, so another request
                # deepens the hole rather than escaping it. Measured on
                # 2026-07-29: pinned at 5000/5000, two countries built in
                # nine minutes, the log nothing but FAILED.
                _quota.wait_for_quota(iso)
                continue
            except Exception:
                if a == 3:
                    # MUST raise, never return {}. Swallowing a failed
                    # chunk writes the year as complete with a silent
                    # hole in it: the parallel rewrite did exactly that
                    # and produced a Canada 2024 with one day and 28
                    # detections, which looked like a finished country.
                    # A year is either whole or absent.
                    raise RuntimeError(
                        f"{iso} {cur} chunk failed after 3 tries")
                time.sleep(6 * a)
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 \
        else frames[0]
    if len(df) and "confidence" in df.columns:
        df = df[~df["confidence"].astype(str).str.lower().isin(["l", "low"])]
    if not len(df):
        return {}
    pts = np.column_stack([df["longitude"].values, df["latitude"].values])
    hit = np.zeros(len(pts), bool)
    for r in RINGS[iso]:
        hit |= ray(r, pts[:, 0], pts[:, 1])
    return {str(d): int(len(g)) for d, g in df[hit].groupby("acq_date")}


def pull_year(iso, year):
    cur, end = date(year, 1, 1), date(year, 12, 31)
    jobs = []
    while cur <= end:
        days = min(5, (end - cur).days + 1)
        jobs.append((cur, days))
        cur += timedelta(days=days)
    out = {}
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for f in cf.as_completed([ex.submit(_chunk, iso, c, d)
                                  for c, d in jobs]):
            for k, v in f.result().items():
                out[k] = out.get(k, 0) + v
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*",
                    help="restrict to these ISO codes. Without it the run "
                         "covers the whole roster, which after the skip fix "
                         "below means every country that was previously "
                         "skipped, so scope it deliberately.")
    ap.add_argument("--plan", action="store_true",
                    help="report what would be fetched and exit")
    args = ap.parse_args()

    targets = list(json.load(open(SEED))["countries"])
    if args.only:
        targets = [i for i in targets if i in set(args.only)]
    t0 = time.time()
    done = 0
    plan = {}
    for i, iso in enumerate(targets, 1):
        path = os.path.join(OUTDIR, f"{iso}.json")
        doc = {}
        if os.path.exists(path):
            try:
                doc = json.load(open(path))
            except ValueError:
                doc = {}

        # SKIP ON THE MARKER, NOT ON THE KEY.
        #
        # This read `str(y) not in doc`, so a year KEY existing counted as
        # that year being done. The daily job writes this same file as a
        # per-day window cache, and it creates year keys holding about
        # FIFTEEN days. So every country whose window cache was written
        # before its full-year build was permanently skipped: the key was
        # there, the year was not.
        #
        # It left 65 of 94 countries holding a file that looks populated
        # and carries a fortnight per year. Estonia was one, which is how
        # it surfaced: its 14 year keys held 15 days each and no analysis
        # could use any of them.
        #
        # `_complete` is the right test and the file already says so
        # thirty lines down: it exists because a fire-free day and an
        # unfetched day are both simply absent, so completeness has to be
        # recorded rather than inferred from how full a year looks. The
        # skip inferred it anyway.
        complete = set(doc.get("_complete", []))
        todo = [y for y in YEARS if str(y) not in complete]
        if not todo:
            continue
        plan[iso] = todo
        if args.plan:
            continue
        for y in todo:
            try:
                got = pull_year(iso, y)
                # A country with no fire on a given day simply has no
                # rows, so a short year is normal; a year missing most of
                # its days is a swallowed failure. 300 is well below any
                # plausible real count and well above a corrupted one.
                # WHAT THIS GUARD IS ACTUALLY FOR, restated because the old
                # version tested a proxy that only holds for busy countries.
                #
                # It read `len(got) < 300`, on the reasoning that a year
                # missing most of its days is a swallowed failure. That is
                # true in Angola, which burns a million detections a year and
                # has rows on nearly every day. It is FALSE in Estonia, which
                # has detections on 155 days of 2012 and is simply a small,
                # cold, wet country where most days have no fire at all. A
                # day with no fire has no rows, so it is absent, so it looked
                # like a gap. Estonia could not be archived at all.
                #
                # The thing the guard was reaching for is "did the fetch
                # cover the year", and that is already known: pull_year
                # chunks every day of the year and _chunk raises after three
                # failed tries, so a return means every chunk succeeded.
                #
                # What remains worth catching is the SILENT EMPTY: an
                # upstream that answers 200 with no rows for a range that
                # should have them. That shows up as a year of exactly zero
                # against a country whose other years are not zero, which is
                # a test that works at both ends of the size range.
                others = [sum(v.values()) for k, v in doc.items()
                          if not k.startswith("_") and isinstance(v, dict)]
                if sum(got.values()) == 0 and any(t > 0 for t in others):
                    raise RuntimeError(
                        f"{iso} {y}: zero detections across the whole year "
                        f"while other years are non-zero. Refusing to store; "
                        f"this is the silent-empty upstream case, not a "
                        f"quiet year.")
                doc[str(y)] = got
                # Record the year as WHOLE. The daily job reads this same
                # file as a per-day cache and cannot otherwise tell a
                # fire-free day (absent, and correct) from an unfetched
                # one (absent, and a silent undercount that inflates
                # every multiple computed against it). Malawi 2016 holds
                # 304 day entries in a 365-day year and all 61 gaps are
                # real zeros, so the distinction has to be recorded
                # rather than inferred from how full the year looks.
                doc["_complete"] = sorted(
                    set(doc.get("_complete", [])) | {str(y)})
                json.dump(doc, open(path, "w"))
            except Exception as exc:
                log(f"{iso} {y}: FAILED {exc}")
        done += 1
        tot = sum(sum(v.values()) for v in doc.values())
        log(f"[{i}/{len(targets)}] {iso}: {len(doc)} years, {tot:,} "
            f"detections ({(time.time()-t0)/60:.0f} min elapsed, "
            f"{done} built this run)")
    if args.plan:
        total = sum(len(v) for v in plan.values())
        log(f"PLAN: {len(plan)} countries, {total} country-years to fetch")
        for iso, years in sorted(plan.items()):
            log(f"  {iso}: {len(years)} years  {years[0]}..{years[-1]}")
        return
    log(f"FULLBASELINESDONE {len(os.listdir(OUTDIR))} countries on disk")


if __name__ == "__main__":
    main()
