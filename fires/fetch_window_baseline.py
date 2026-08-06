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

from fires import _http, _quota

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
                except _http.OverLimit:
                    # Not a retry. The key is over its limit BECAUSE too
                    # many requests arrived; another one deepens it.
                    _quota.wait_for_quota(iso)
                    continue
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



CACHE_DIR = os.path.join(REPO, "fires", "data", "full_history")
COMPLETE_KEY = "_complete"
DEFECTS = os.path.join(REPO, "fires", "data", "archive_defects.json")


def _defective_dates():
    """Dates the SNPP archive is known to be wrong on, thin or absent.

    Authoritative OVER the completeness marker, which is where this was
    getting through. The reader treated a date as satisfied if it was
    present OR its year was marked complete, and the marker is a 300-day
    floor that cannot see a nineteen-day hole: 2024 is missing 19 days,
    still holds 347, and is marked complete, so every absent date inside
    it read as a genuine zero.

    Floods' framing, from the same defect on their channel: check each
    store separately and never the union. Presence and the marker were
    two sources of evidence OR-ed together, and the weaker one was
    answering for the stronger.
    """
    try:
        d = json.load(open(DEFECTS))
    except (OSError, ValueError):
        return set()
    return set(d.get("thin", [])) | set(d.get("absent", []))


DEFECTIVE = _defective_dates()


def load_cache(iso):
    path = os.path.join(CACHE_DIR, f"{iso}.json")
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path))
    except ValueError:
        return {}


def save_cache(iso, doc):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, f"{iso}.json"), "w") as fh:
        json.dump(doc, fh)


def window_dates(start, end, year):
    """The same calendar days as [start, end], inside `year`.

    Returns None for any day that does not exist in that year, which is
    only 29 February. Callers drop that day from EVERY year rather than
    from some, so the sum stays a like-for-like comparison instead of
    silently running six days in leap years and seven elsewhere.
    """
    out = []
    d = start
    while d <= end:
        try:
            out.append(date(year, d.month, d.day))
        except ValueError:
            out.append(None)
        d += timedelta(days=1)
    return out


def window_from_cache(iso, start, end):
    """(hist, missing) for one country, read from the per-day cache.

    hist maps year -> summed detections over the window. missing lists
    (year, date) pairs that are genuinely unfetched, as distinct from
    days that are absent because nothing burned.

    That distinction is the whole reason `_complete` exists. Inside a
    year the batch has finished, an absent date means zero: Malawi 2016
    holds 304 day entries in a 365-day year and all 61 gaps are real.
    Inside a year still being filled a day by day, an absent date means
    unfetched, and summing it as zero would undercount the baseline and
    inflate every multiple computed against it.
    """
    cache = load_cache(iso)
    # Trust the marker only where it is consistent with the file.
    #
    # A year marked complete is licence to read every absent date as a
    # zero, so a WRONGLY marked year silently undercounts the baseline
    # and inflates every multiple computed against it. Platform's
    # validate_baselines.py catches an unparseable file; it cannot catch
    # a parseable file whose marker is a lie, and that is the shape that
    # reaches a page looking like a bigger number.
    #
    # The 300-day floor is the same one build_full_baselines enforces
    # before it stores a year, so this re-checks the producer's promise
    # at the point of use rather than assuming it.
    complete = {y for y in cache.get(COMPLETE_KEY, [])
                if len(cache.get(y, {})) >= 300}
    hist, missing = {}, []
    # 29 February is dropped from every year when the window spans it,
    # so all years sum the same number of calendar days.
    skip = {i for y in YEARS
            for i, d in enumerate(window_dates(start, end, y)) if d is None}
    for y in YEARS:
        days = cache.get(str(y), {})
        total = 0
        for i, d in enumerate(window_dates(start, end, y)):
            if d is None or i in skip:
                continue
            key = d.isoformat()
            if key in DEFECTIVE:
                # Known-defective: not a zero and not fetchable. Excluded
                # from BOTH sides by the caller rather than summed.
                missing.append((y, d))
            elif key in days:
                total += days[key]
            elif str(y) in complete:
                total += 0
            else:
                missing.append((y, d))
        hist[str(y)] = total
    return hist, missing


def fetch_day(iso, day):
    """One calendar day for one country. Bills len(BOX) days."""
    BUCKET.take(1 * len(BOX[iso]))
    frames = []
    for w, s, e, n in BOX[iso]:
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
               f"{KEY}/VIIRS_SNPP_SP/{w},{s},{e},{n}/1/{day.isoformat()}")
        for a in (1, 2, 3):
            try:
                frames.append(_http.read_csv(url))
                break
            except _http.OverLimit:
                _quota.wait_for_quota(iso)
                continue
            except Exception:
                if a == 3:
                    raise RuntimeError(f"{iso} {day} failed 3 tries")
                time.sleep(6 * a)
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 \
        else frames[0]
    if len(df) and "confidence" in df.columns:
        df = df[~df["confidence"].astype(str).str.lower().isin(["l", "low"])]
    if not len(df):
        return 0
    pts = np.column_stack([df["longitude"].values, df["latitude"].values])
    hit = np.zeros(len(pts), bool)
    for r in RINGS[iso]:
        hit |= ray(r, pts[:, 0], pts[:, 1])
    return int(hit.sum())


def fill_missing(iso, missing):
    """Fetch each absent day and write it back, zeros included.

    Zeros are stored EXPLICITLY. In a year the batch has not completed,
    presence of the key is the only evidence a day was ever fetched, so
    a genuine zero has to be recorded rather than left absent.
    """
    if not missing:
        return 0
    doc = load_cache(iso)
    got = 0
    for y, d in missing:
        if d.isoformat() in DEFECTIVE:
            # Unfetchable by design: the archive is wrong on this date and
            # does not heal. 2022-08-01 is still zero in science-quality
            # four years on. Spending quota to re-read a known hole would
            # return the same hole.
            continue
        doc.setdefault(str(y), {})[d.isoformat()] = fetch_day(iso, d)
        got += 1
    save_cache(iso, doc)
    return got


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
    fetched = 0
    for i, iso in enumerate(isos, 1):
        try:
            hist, missing = window_from_cache(iso, start, end)
            if missing:
                fetched += fill_missing(iso, missing)
                hist, still = window_from_cache(iso, start, end)
                if still:
                    # REFUSE rather than sum what we have. A missing day
                    # summed as zero undercounts the baseline, which
                    # inflates the multiple, and an inflated fire anomaly
                    # is the worst number this project could publish.
                    raise RuntimeError(
                        f"{len(still)} day(s) still missing after fetch, "
                        f"first {still[0][1]}")
        except Exception as exc:
            failed.append(iso)
            print(f"  [{i}/{len(isos)}] {iso}: FAILED {exc}", flush=True)
            continue
        mean = sum(hist.values()) / len(hist)
        pv = prev["countries"].get(iso, {})
        out[iso] = {"name": NAMES.get(iso, pv.get("name", iso)),
                    "box": pv.get("box") or BOX[iso][0],
                    "hist": hist, "mean": round(mean, 1)}
        print(f"  [{i}/{len(isos)}] {iso}: mean {mean:,.0f}", flush=True)
    print(f"  fetched {fetched} day-records; the rest came from cache",
          flush=True)

    # A YEAR WITH NO ARCHIVE IS NOT A YEAR WITH NO FIRE.
    #
    # The VIIRS SNPP science-quality archive has gaps. One runs
    # 2022-07-27 to 2022-08-10 inclusive: Angola reads 30,254 detections
    # on 26 July 2022, zero for fifteen days, then 26,487 on 12 August.
    # Every country in the roster reads exactly zero across that window.
    #
    # Counted as a zero, such a year drags the baseline mean down and
    # inflates every multiple computed against it by 14/13, which is
    # 7.7%. That shipped live on 2026-08-04: Greece published at 12.4x
    # when its real figure against the years that exist is 11.5x.
    # Rankings survive, because the bias is identical everywhere, but
    # the numbers do not.
    #
    # Detection is global rather than per country. Malta legitimately
    # reads zero most weeks; ninety-four countries cannot all read zero
    # in the same week, so a year whose GLOBAL total is zero is missing
    # archive, not an absence of fire. That distinction cannot be made
    # from one country's series, which is why this sits here rather than
    # in window_from_cache.
    year_totals = {y: sum(rec["hist"].get(str(y), 0) for rec in out.values())
                   for y in YEARS}
    no_archive = sorted(str(y) for y, t in year_totals.items() if t == 0)
    if no_archive:
        print(f"  YEARS WITH NO ARCHIVE for {win}: {', '.join(no_archive)}. "
              f"Excluded from every baseline rather than counted as zero.",
              flush=True)
        for rec in out.values():
            for y in no_archive:
                rec["hist"].pop(y, None)
            if rec["hist"]:
                rec["mean"] = round(sum(rec["hist"].values())
                                    / len(rec["hist"]), 1)

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
           "years_excluded_no_archive": no_archive,
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
