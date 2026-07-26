"""Build the landing-page event list and fire map markers.

Emits `data/events.json` (task 3) and `data/fire_markers.json`
(task 4) from live FIRMS data plus the frozen same-week country
history in `fires/data/country_history.json`.

Window rule: one pull a day at 06:00 UTC, always whole days
-----------------------------------------------------------
The window is the seven UTC days ending yesterday. Nothing here is
ever a partial day, which is what makes the number safe to render at
40px on the landing page with no room to qualify it.

Why 06:00 UTC works for every region at once: FIRMS near-real-time
processing lags an overpass by up to about three hours, so the latest
a detection stamped with UTC date D can arrive is 23:59 on D plus
three hours, that is roughly 03:00 UTC on D+1. After that, day D is
closed at every longitude. No per-region overpass reasoning is needed
and the 06:00 slot leaves a three-hour margin.

This replaces judging completeness from overpass timestamps, which is
not reliable: at mid-latitudes consecutive VIIRS orbits overlap, so a
country keeps gaining detections after its nominal afternoon pass. On
2026-07-26 Spain read 4,524 at 15:15 UTC, 4,700 at 15:55 and 4,725 at
18:28, and France moved from 9.6x to 10.1x after its day looked done.

Bonus property: run on a Monday, the window is exactly the previous
Monday to Sunday, so the weekly issue and the daily page share one
window definition rather than two.

Marker gate
-----------
Eligibility is not a multiple alone. A multiple is unbounded and
unstable at small baselines, which is the raw-count trap inverted: a
country averaging 20 detections that records 400 shows 20x and would
dwarf Canada at 65,905. So a count floor and a rank clause come with
it. See `research/reply_fire_to_design.md` section 3.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.expanduser("~/.firms_map_key")
HISTORY = os.path.join(REPO, "fires", "data", "country_history.json")
GEOJSON = os.path.join(REPO, "fires", "data", "countries.geo.json")

# Gate thresholds. Tunable; stated here rather than buried in code.
MIN_COUNT = 500
MIN_MULTIPLE = 1.5
STRONG_MULTIPLE = 2.0
MAX_RANK = 3
MAX_MARKERS = 8

ATTRIBUTION = {
    "ESP": "non_enso", "FRA": "non_enso", "GBR": "non_enso",
    "ITA": "non_enso", "CAN": "non_enso",
}
DISPLAY = {
    "ESP": "Spain", "FRA": "France", "GBR": "United Kingdom",
    "ITA": "Italy", "CAN": "Canada",
}
SLUG = {
    "ESP": "spain", "FRA": "france", "GBR": "uk",
    "ITA": "italy", "CAN": "canada",
}


def contains_points(ring, pts):
    """Even-odd ray casting. ring (N,2) closed lon/lat, pts (M,2)."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    x1, y1 = ring[:-1, 0], ring[:-1, 1]
    x2, y2 = ring[1:, 0], ring[1:, 1]
    for i in range(len(x1)):
        cond = (y1[i] > y) != (y2[i] > y)
        if not cond.any():
            continue
        xint = (x2[i] - x1[i]) * (y - y1[i]) / (y2[i] - y1[i]) + x1[i]
        inside ^= cond & (x < xint)
    return inside


def load_rings(isos):
    geo = json.load(open(GEOJSON))
    rings = {}
    for feat in geo["features"]:
        if feat["id"] in isos:
            g = feat["geometry"]
            polys = ([g["coordinates"]] if g["type"] == "Polygon"
                     else g["coordinates"])
            rings[feat["id"]] = [
                np.vstack([np.array(r[0]), np.array(r[0])[:1]])
                for r in polys]
    return rings


def fetch_window(key, box, rings, start, days):
    """Return the detections inside the country for a date window."""
    w, s, e, n = box
    frames = []
    cur, left = start, days
    while left > 0:
        chunk = min(5, left)  # API caps a request at 5 days
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/"
               f"VIIRS_SNPP_NRT/{w},{s},{e},{n}/{chunk}/{cur.isoformat()}")
        for attempt in (1, 2):
            try:
                df = pd.read_csv(url)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(8)
        if len(df) and "confidence" in df.columns:
            df = df[~df["confidence"].astype(str).str.lower()
                    .isin(["l", "low"])]
        if len(df):
            pts = np.column_stack([df["longitude"].values,
                                   df["latitude"].values])
            mask = np.zeros(len(pts), dtype=bool)
            for ring in rings:
                mask |= contains_points(ring, pts)
            frames.append(df[mask])
        cur += timedelta(days=chunk)
        left -= chunk
        time.sleep(1)
    return pd.concat(frames) if frames else pd.DataFrame()


def centroid(df, rings):
    """Count-weighted centroid, with a containment fallback.

    The plain weighted mean fails on multi-cluster countries: Canada
    burning in the Northwest Territories, Ontario and Quebec at once
    puts the mean in Hudson Bay. So test containment and fall back to
    the densest 5-degree cell.
    """
    if not len(df):
        return None, None, "none"
    lon = float(df["longitude"].mean())
    lat = float(df["latitude"].mean())
    inside = any(contains_points(r, np.array([[lon, lat]]))[0]
                 for r in rings)
    if inside:
        return round(lat, 2), round(lon, 2), "weighted"
    cells = (df.assign(cla=(df["latitude"] // 5 * 5),
                       clo=(df["longitude"] // 5 * 5))
             .groupby(["cla", "clo"]).size().sort_values(ascending=False))
    (cla, clo) = cells.index[0]
    sub = df[(df["latitude"] // 5 * 5 == cla)
             & (df["longitude"] // 5 * 5 == clo)]
    return (round(float(sub["latitude"].mean()), 2),
            round(float(sub["longitude"].mean()), 2), "largest_cluster")


ORDINAL = {2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth"}


def make_title(rank, multiple, count, prev_best, prev_year):
    """Region-free claim, under the 45-character citable ceiling.

    Region-free because the landing page renders the region separately
    in a heavier weight (design task file, task 3). Short because
    citable.py collides titles with the number past ~45 characters.

    Records are split by their margin over the previous best, because
    "highest on record" alone made four of five rows read identically
    while the underlying stories differ by a lot: France cleared its
    old record by 4x, Italy edged past its own by 8 percent.

    These are defaults. Per the events.json schema note, title wording
    is editor-chat surface; this generates something correct to review,
    not final copy.
    """
    if rank == 1 and prev_best:
        margin = count / prev_best
        if margin >= 2.5:
            t = f"{margin:.1f}x its previous record week"
        elif margin >= 1.2:
            t = f"Well clear of its {prev_year} record week"
        else:
            t = f"Just past its {prev_year} record week"
    elif rank in ORDINAL:
        t = f"{ORDINAL[rank]}-heaviest fire week since 2012"
    else:
        t = f"Fire week at {multiple:.1f}x the seasonal norm"
    assert len(t) <= 45, f"title too long for citable: {len(t)}"
    return t


def main():
    key = open(KEY_PATH).read().strip()
    hist_doc = json.load(open(HISTORY))
    window_days = 7
    now_utc = datetime.now(timezone.utc)

    # Yesterday is only guaranteed closed once NRT processing has caught
    # up, about 03:00 UTC. The scheduled slot is 06:00 UTC; refuse to
    # run inside the danger window so a retry or a manual run at 01:00
    # cannot quietly publish an unfinished day.
    if now_utc.hour < 3:
        raise SystemExit(
            f"refusing to run at {now_utc:%H:%M} UTC: yesterday is not "
            "guaranteed processed until ~03:00 UTC. Scheduled slot is "
            "06:00 UTC.")

    end = now_utc.date() - timedelta(days=1)    # last fully closed day
    start = end - timedelta(days=window_days - 1)
    win_key = f"{start.strftime('%m-%d')}..{end.strftime('%m-%d')}"

    if hist_doc["window"] != win_key:
        raise SystemExit(
            f"history covers window {hist_doc['window']} but the trailing "
            f"complete window is {win_key}; refresh the history first")

    isos = list(hist_doc["countries"])
    rings = load_rings(isos)
    rows = []
    for iso in isos:
        h = hist_doc["countries"][iso]
        df = fetch_window(key, tuple(h["box"]), rings[iso], start,
                          window_days)
        count = int(len(df))
        mean = h["mean"]
        multiple = count / mean
        rank = 1 + sum(1 for v in h["hist"].values() if v > count)
        lat, lon, basis = centroid(df, rings[iso])
        prev_year = max(h["hist"], key=lambda y: h["hist"][y])
        prev_best = h["hist"][prev_year]
        rows.append({
            "iso": iso, "region": DISPLAY[iso], "count": count,
            "multiple": round(multiple, 1), "rank": f"{rank} of 15",
            "rank_n": rank, "lat": lat, "lon": lon,
            "centroid_basis": basis,
            "attribution": ATTRIBUTION[iso],
            "title": make_title(rank, multiple, count, prev_best, prev_year),
            "href": f"fires/{SLUG[iso]}/",
        })
        print(f"{iso}: {count:,} x{multiple:.1f} rank {rank} "
              f"({lat}, {lon}) {basis}", flush=True)

    eligible = [r for r in rows
                if r["count"] >= MIN_COUNT
                and r["multiple"] >= MIN_MULTIPLE
                and (r["multiple"] >= STRONG_MULTIPLE
                     or r["rank_n"] <= MAX_RANK)]
    eligible.sort(key=lambda r: -r["multiple"])
    eligible = eligible[:MAX_MARKERS]

    end_fmt = "%-d" if start.month == end.month else "%b %-d"
    win_label = f"wk {start.strftime('%b %-d')}-{end.strftime(end_fmt)}"
    source = f"NASA FIRMS SNPP, {win_label}"

    events = {
        "_readme": [
            "Generated by fires/build_events.py; do not hand-edit.",
            "Window is the trailing seven fully-closed UTC days, so this",
            "file never carries a partial-day number. Titles are the",
            "claim only, without the region, per the design task file.",
        ],
        "events": [{
            "date": end.isoformat(),
            "region": r["region"],
            "title": r["title"],
            "stat": f"{r['multiple']:.1f}x",
            "stat_label": "same-week 2012-25 mean",
            "attribution": r["attribution"],
            "source": source,
            "href": r["href"],
        } for r in eligible],
    }
    markers = {
        "_readme": [
            "Generated by fires/build_events.py; do not hand-edit.",
            "area proportional to multiple; see reply_fire_to_design.md",
            "sections 2 and 3 for the centroid basis and the gate.",
        ],
        "window": win_key,
        "complete": True,
        "markers": [{
            "region": r["region"], "lat": r["lat"], "lon": r["lon"],
            "multiple": r["multiple"], "count": r["count"],
            "rank": r["rank"], "attribution": r["attribution"],
            "centroid_basis": r["centroid_basis"], "href": r["href"],
        } for r in eligible],
    }
    os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
    with open(os.path.join(REPO, "data", "events.json"), "w") as f:
        json.dump(events, f, indent=2)
        f.write("\n")
    with open(os.path.join(REPO, "data", "fire_markers.json"), "w") as f:
        json.dump(markers, f, indent=2)
        f.write("\n")
    print(f"wrote {len(eligible)} events and markers for {win_key}")


if __name__ == "__main__":
    main()
