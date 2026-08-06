"""Build the landing-page event list and fire map markers.

Emits `data/events.json` (task 3) and `data/fire_markers.json`
(task 4) from live FIRMS data plus the frozen same-week country
history in `fires/data/country_history.json`.

Window rule: one pull a day, always whole days
----------------------------------------------
The window is the seven UTC days ending yesterday. Nothing here is
ever a partial day, which is what makes the number safe to render at
40px on the landing page with no room to qualify it.

Why one daily slot works for every region at once: FIRMS near-real-time
processing lags an overpass by up to about three hours, so the latest
a detection stamped with UTC date D can arrive is 23:59 on D plus
three hours, that is roughly 03:00 UTC on D+1. After that, day D is
closed at every longitude, so no per-region overpass reasoning is
needed. The guard below enforces that 03:00 boundary. WHICH hour the
job actually fires is platform's, in .github/workflows/, and is
deliberately not repeated here: it has already moved once and every
copy of it went stale.

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
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from fires import _http, _quota

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.expanduser("~/.firms_map_key")
HISTORY = os.path.join(REPO, "fires", "data", "country_history.json")
GEOJSON = os.path.join(REPO, "fires", "data", "countries.geo.json")

# Gate thresholds. Tunable; stated here rather than buried in code.
#
# Structure, Kristjan's call 2026-07-29: a noise floor, then the
# significance signals combined with OR rather than AND.
#
# The old gate ANDed a count floor of 500 with a 1.5x multiple. Both
# were doing work they were not fit for. A count floor cannot measure
# significance: it excluded the UK at its highest same-week value in
# fourteen years because 407 detections is a small number in a small
# country. A single multiple cannot either: 1.5x is 8.9 standard
# deviations in Mozambique and 0.5 in Canada, so one bar means opposite
# things in different places.
#
# The three signals fail in different directions, which is why they are
# OR and not AND:
#   z         catches stable countries, misses volatile ones. Canada at
#             1.8x scores z=0.8 because its own variance is enormous.
#   multiple  catches volatile countries, misses stable ones. DR Congo
#             could have its worst year on record and read 1.10x.
#   rank 1    catches records the other two round away, and is
#             distribution-free.
# Any one of them is evidence. Requiring all three would select only
# the countries where nothing subtle is happening.
NOISE_FLOOR = 150      # not a significance test: enough pixels that a
                       # handful of false positives cannot read as 20x
Z_THRESHOLD = 2.0
STRONG_MULTIPLE = 2.0
RECORD_RANK = 1
MIN_MULTIPLE = 1.5     # retained for the volume-context class below
# Was 8, then 12 on 2026-07-27 when the sweep widened to 45 countries,
# then 20 on 2026-07-29. It was never a map constraint, just a number,
# and it was quietly excluding real cases: Saudi Arabia at rank 1 of 15
# and Libya at rank 3 both cleared every threshold and were cut by the
# cap alone. 20 is above the eligible count at present, so the cap is
# now a safety valve against a pathological week rather than a routine
# filter. If it starts binding again, raise it rather than let it
# silently decide the page.
MAX_MARKERS = 20
HIGH_VOLUME = 20000

# A day holding less than this fraction of the window's median is treated
# as unfinished archive rather than a quiet day. 0.5 is deliberately
# loose: a genuinely calm day sits near 0.8 of median in this record,
# while the two observed incomplete days sat at 0.03 and 0.28.
INCOMPLETE_DAY_FRACTION = 0.5

# Countries that always appear, gate or no gate.
#
# Kristjan's call, 2026-07-29: readers come to check their own country,
# and a tracker that shows nothing for the UK because the UK is having
# an ordinary week fails that reader. These five are where the audience
# is. A pinned country is NOT a claim that something is happening
# there; it carries whatever its real numbers say, including "normal",
# and ships a pinned flag so design can render it distinctly from an
# anomaly. Rendering the two identically would turn this into exactly
# the over-claiming the gate exists to prevent.
PINNED = {"GBR", "USA", "CAN", "FRA", "ESP"}

# Attribution is an editorial judgment per country, from the fixed
# three-value vocabulary. Anything not assessed defaults to "pending",
# which is what that tag exists for: the sweep now surfaces countries
# faster than they can be assessed, and an unassessed country must not
# silently inherit a claim.
#
# Assessed so far: the Mediterranean is the declared non-ENSO control,
# Canada is boreal with a weak link, southern African savanna burning is
# routine agriculture, and Australian fire in July is northern savanna
# outside the tracked Nov-Feb window.
#
# An "enso" tag is WINDOW-GATED, not region-gated. The teleconnection
# that justifies it is seasonal: Indonesia is an R5 ENSO region in
# fires/SPEC.md for Aug-Oct, Australia for Nov-Feb. Outside those months
# the region is the same and the mechanism is not, so the tag reverts to
# "pending" rather than asserting a loading nobody has assessed.
#
# This was a live defect, found by ECON on 2026-07-29. Indonesia was
# tagged "enso" statically. The tag sat dormant while Indonesia missed
# the gate and went live automatically the day it cleared, on 29 July,
# three days outside its own declared window, with no human looking at
# it. It would equally have carried an ENSO loading in February. The
# comment here already promised Australia would "flip when the window
# opens"; that was never implemented for either country.
#
# Widening a claim needs editorial sign-off. Narrowing one does not,
# which is why this ships now: "pending" means not yet examined and
# cannot over-claim.
ATTRIBUTION_ALWAYS = {
    "ESP": "non_enso", "FRA": "non_enso", "GBR": "non_enso",
    "ITA": "non_enso", "CAN": "non_enso", "AGO": "non_enso",
    "COD": "non_enso", "ZMB": "non_enso", "USA": "non_enso",
}
# iso -> (first_month, last_month) inclusive, when "enso" applies.
ATTRIBUTION_ENSO_WINDOW = {
    "IDN": (8, 10),
    "AUS": (11, 2),
    "BRA": (8, 10),
}
# Outside its ENSO window, a listed country falls back to this.
ATTRIBUTION_OFF_WINDOW = {"AUS": "non_enso"}
# D-076, 2026-08-04: "pending" comes off reader-facing surfaces. It is a
# WORK STATE, not a finding, and it was this function's default fallback,
# so it rendered on anything untagged and therefore carried no
# information at all. Kristjan: it confuses the reader and reads as
# ENSO-researcher design rather than reader-value design.
#
# null rather than a softer word, and the field is kept rather than
# removed so a real ENSO string can occupy it later. Absence of a tag
# means we have not assessed it, which is true and is not the reader's
# problem. The two ENSO strings are unchanged.
DEFAULT_ATTRIBUTION = None


def attribution_for(iso, month):
    """Tag for one country in one month, from the fixed vocabulary."""
    if iso in ATTRIBUTION_ALWAYS:
        return ATTRIBUTION_ALWAYS[iso]
    win = ATTRIBUTION_ENSO_WINDOW.get(iso)
    if win:
        lo, hi = win
        inside = lo <= month <= hi if lo <= hi else (month >= lo or month <= hi)
        if inside:
            return "enso"
        return ATTRIBUTION_OFF_WINDOW.get(iso, DEFAULT_ATTRIBUTION)
    return DEFAULT_ATTRIBUTION



CACHE_DIR = os.path.join(REPO, "fires", "data", "full_history")


def subset_hist(iso, keep_md, cur_year):
    """Baseline over ONLY the surviving calendar days of the window.

    keep_md is a list of (month, day). Returns {year: total} summed over
    exactly those dates in each prior year, or None if any date is
    genuinely unfetched, in which case the caller keeps the seven-day
    baseline rather than silently comparing five days against seven.

    Presence of a date key means it was fetched, because the day cache
    writes zeros explicitly. Inside a year the batch marked complete, an
    absent date means zero: Malawi 2016 holds 304 entries in a 365-day
    year and all 61 gaps are real.
    """
    path = os.path.join(CACHE_DIR, f"{iso}.json")
    if not os.path.exists(path):
        return None
    try:
        doc = json.load(open(path))
    except ValueError:
        return None
    complete = {y for y in doc.get("_complete", [])
                if len(doc.get(y, {})) >= 300}
    out = {}
    for year in range(2012, cur_year):
        days = doc.get(str(year))
        if days is None:
            continue                      # no archive for that year
        total = 0
        for m, d in keep_md:
            key = f"{year:04d}-{m:02d}-{d:02d}"
            if key in days:
                total += days[key]
            elif str(year) in complete:
                total += 0
            else:
                return None               # unfetched, not zero
        out[str(year)] = total
    return out or None


def rebuild_rows(detail, end):
    """Re-derive the ranked rows after the counts and baselines moved."""
    rows = []
    for iso, r in detail.items():
        hist = r["hist"]
        count, mean = r["count"], r["mean"]
        multiple = count / mean if mean else 0.0
        rank = 1 + sum(1 for v in hist.values() if v > count)
        vals = list(hist.values())
        sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        prev_year = max(hist, key=lambda y: hist[y])
        rows.append({
            "iso": iso, "region": r["name"], "count": count,
            "multiple": round(multiple, 1), "rank": f"{rank} of {len(hist) + 1}",
            "rank_n": rank, "z": round((count - mean) / sd if sd else 0.0, 2),
            "lat": r["lat"], "lon": r["lon"], "centroid_basis": r["basis"],
            "attribution": attribution_for(iso, end.month),
            "title": make_title(rank, multiple, count,
                                hist[prev_year], prev_year),
            "href": f"fires/{slugify(r['name'])}/",
        })
    return rows


def slugify(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


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
                df = _http.read_csv(url)
                break
            except _http.OverLimit:
                # Does NOT consume an attempt. This step runs straight
                # after the baseline refresh, which walks 48 countries
                # and leaves the key near its ceiling, so over-limit here
                # is structural rather than exceptional. Retrying into it
                # is what produced the HTTP 400 that failed the whole
                # publish on 2026-07-30.
                # No label: fetch_window does not receive the ISO, and
                # a NameError here would fire only when over-limit
                # actually happened, which is the one moment the guard
                # has to work.
                _quota.wait_for_quota()
                continue
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
    # The years a complete baseline WOULD span. Compared against what
    # each country's hist actually holds, so a consumer can see 13 of 14
    # rather than inferring a 13-year record.
    YEARS_EXPECTED = list(range(2012, datetime.now(timezone.utc).year))
    now_utc = datetime.now(timezone.utc)

    # Yesterday is only guaranteed closed once NRT processing has caught
    # up, about 03:00 UTC. Refuse to run inside that window so a retry or
    # a manual run at 01:00 cannot quietly publish an unfinished day.
    #
    # Deliberately says nothing about WHEN the job is scheduled. It said
    # "Scheduled slot is 06:00 UTC" for a week after the slot moved to
    # 03:10 with an 05:30 backstop, so anyone tripping this at 02:00 was
    # told to expect a run three hours later than it happens. This file
    # owns the physical constraint, which is the NRT processing lag;
    # platform owns the schedule, and a number that lives in both places
    # goes stale in one of them.
    if now_utc.hour < 3:
        raise SystemExit(
            f"refusing to run at {now_utc:%H:%M} UTC: yesterday is not "
            "guaranteed processed until ~03:00 UTC. Re-run after that, or "
            "wait for the next scheduled slot in .github/workflows/.")

    end = now_utc.date() - timedelta(days=1)    # last fully closed day
    start = end - timedelta(days=window_days - 1)
    win_key = f"{start.strftime('%m-%d')}..{end.strftime('%m-%d')}"

    if hist_doc["window"] != win_key:
        # Exit 3 is the house convention for "nothing to do", distinct
        # from a generic failure: the caller warns and skips rather than
        # going red. See research/handover_platform_contract.md section 3.
        #
        # This path is the NORMAL one on roughly six days in seven,
        # because the trailing window moves daily while the baseline is
        # frozen to one week. Refusing is correct: comparing a fresh week
        # against a stale baseline would silently publish a wrong
        # multiple. The fix is the full-year baseline, not a looser check.
        print(f"nothing to do: history covers window {hist_doc['window']} "
              f"but the trailing complete window is {win_key}",
              file=sys.stderr)
        raise SystemExit(3)

    isos = list(hist_doc["countries"])
    rings = load_rings(isos)
    rows, detail = [], {}
    for iso in isos:
        h = hist_doc["countries"][iso]
        df = fetch_window(key, tuple(h["box"]), rings[iso], start,
                          window_days)
        count = int(len(df))
        mean = h["mean"]
        multiple = count / mean
        rank = 1 + sum(1 for v in h["hist"].values() if v > count)
        lat, lon, basis = centroid(df, rings[iso])
        # EVERY day of the window, zeros written explicitly.
        #
        # groupby emits a row only for dates that HAVE detections, so a
        # day on which a country did not burn was simply absent. The
        # country page then charted six bars for a seven-day window and
        # captioned it "5 of 6 days", and Kristjan spotted the missing
        # 4 August on Greece.
        #
        # The miscount is the smaller half. A zero day is not a missing
        # day, it is a country whose fires STOPPED, and omitting it hides
        # exactly the die-down the page exists to show: Greece went to
        # zero on 4 August and the chart ended on a modest bar on the
        # 3rd instead. Same shape as the archive gap and the day cache,
        # where absence and zero were rendered indistinguishable.
        seen = (df.groupby("acq_date").size().to_dict() if len(df) else {})
        daily = {}
        for k in range(window_days):
            day = (start + timedelta(days=k)).isoformat()
            daily[day] = int(seen.get(day, 0))
        detail[iso] = {"iso": iso, "name": h["name"], "count": count,
                       "mean": h["mean"], "hist": h["hist"],
                       "daily": daily,
                       # EXPECTED slot counts, carried ON the series.
                       #
                       # A consumer cannot otherwise tell a GAP from an
                       # END: five values in a seven-day week and five in
                       # a five-day week are the same payload, and a
                       # renderer resolves the ambiguity by stretching
                       # five to fill the frame, which turns "a day is
                       # missing" into "this is what the week looked
                       # like".
                       #
                       # We already say this at document level in
                       # `degraded`, which is not enough: D-051, a
                       # qualifier is a property of the number and has to
                       # survive the number being quoted alone. A chart
                       # handed `daily` and nothing else must still know
                       # a day is absent.
                       #
                       # hist_expected is 14 while the delivered dict is
                       # often 13, because 2022 has no archive over most
                       # windows. That difference is the point: 13 of 14
                       # is a fact about the record, not a shorter record.
                       #
                       # DUE equals EXPECTED on both series, always, and
                       # that is a property of the window rather than a
                       # coincidence. The window is seven WHOLE days
                       # ending yesterday, so no slot is ever "not yet":
                       # a partial day is never published, which is the
                       # rule the 03:00 guard exists to enforce. Every
                       # absent slot here is a GAP and should be drawn as
                       # one.
                       #
                       # Emitted anyway rather than omitted, so a
                       # consumer reads the same three counts from every
                       # channel and never special-cases fire. A field
                       # that is absent for one channel is the kind of
                       # thing a renderer resolves by guessing.
                       "daily_expected": window_days,
                       "daily_due": window_days,
                       "hist_expected": len(YEARS_EXPECTED),
                       "hist_due": len(YEARS_EXPECTED),
                       "lat": lat, "lon": lon, "basis": basis}
        prev_year = max(h["hist"], key=lambda y: h["hist"][y])
        prev_best = h["hist"][prev_year]
        vals = list(h["hist"].values())
        sd = (sum((v - h["mean"]) ** 2 for v in vals) / len(vals)) ** 0.5
        z = (count - h["mean"]) / sd if sd else 0.0
        rows.append({
            "iso": iso, "region": h["name"], "count": count,
            "multiple": round(multiple, 1), "rank": f"{rank} of 15",
            "rank_n": rank, "z": round(z, 2), "lat": lat, "lon": lon,
            "centroid_basis": basis,
            "attribution": attribution_for(iso, end.month),
            "title": make_title(rank, multiple, count, prev_best, prev_year),
            "href": f"fires/{slugify(h['name'])}/",
        })
        print(f"{iso}: {count:,} x{multiple:.1f} rank {rank} "
              f"({lat}, {lon}) {basis}", flush=True)

    def signals(r):
        """Which of the three significance signals this country clears.

        Emitted rather than recomputed downstream, because design was
        about to re-derive the gate in the renderer to decide ordering,
        and two copies of a threshold drift.

        The list is the useful form rather than a boolean. Design found
        that ordering the page by the MULTIPLE puts Portugal fifth at
        2.3x with z = 0.81, inside one standard deviation of its own
        normal, while Saudi Arabia sits seven rows lower at 1.5x with
        z = 4.3. Checking it showed the multiple is the outlier measure
        rather than a competing preference: rank and z agree with each
        other to 1.3 places while the multiple differs from both by 3.6.

        A country clearing ONLY the multiple is the weak case. Not a
        country clearing only one signal: Venezuela clears one, and it is
        a fourteen-year record, which is a strong claim.
        """
        if r["count"] < NOISE_FLOOR:
            return []
        out = []
        if r["z"] >= Z_THRESHOLD:
            out.append("z")
        if r["multiple"] >= STRONG_MULTIPLE:
            out.append("multiple")
        if r["rank_n"] <= RECORD_RANK:
            out.append("record")
        return out

    def qualifies(r):
        """Noise floor, then any one significance signal."""
        return bool(signals(r))

    # A DAY THE ARCHIVE HAS NOT FINISHED IS NOT A QUIET DAY.
    #
    # The 03:00 UTC guard assumes NRT processing closes a day within
    # about three hours of midnight. On 2026-08-05 that failed: 3 August
    # held 1,881 detections across the whole roster against a median of
    # 62,886, and 4 August held 17,919. Angola burns every day in August
    # and logged 20,678 on the 1st; it read exactly zero on the 4th.
    # Confirmed against the independent global feed. And it does NOT
    # backfill: 3 August gained one detection in nineteen hours.
    #
    # DEGRADE, DO NOT REFUSE. My first version refused the window, which
    # would have taken the channel offline for a week, because a dead day
    # sits inside every window for seven days after it. That is the
    # frozen-detections defect of 29 July, self-inflicted. Refuse or
    # publish is a false binary.
    #
    # Instead drop the dead days from BOTH sides: this week's count and
    # the baseline are computed over the same surviving calendar days.
    # Five days against the same five days of each prior year is
    # like-for-like; it invents nothing and dilutes nothing. Only the
    # per-day cache makes this possible, and it did not exist a week ago.
    #
    # Roster-wide detection, for the same reason the no-archive year
    # check is: one country can legitimately read zero, ninety-four
    # cannot collapse together. Measured against the window's own median
    # so it holds in any season.
    # The baseline dropped these calendar days from every prior year
    # because the archive is defective on them in at least one year. The
    # current window must drop the same days or the two sides stop being
    # like-for-like, which is the whole point of the exclusion.
    defective_md = set(hist_doc.get("days_excluded_defective") or [])
    if defective_md:
        print(f"  matching the baseline's dropped days: "
              f"{', '.join(sorted(defective_md))}", file=sys.stderr)
        for r in detail.values():
            r["daily"] = {k: v for k, v in r["daily"].items()
                          if k[5:] not in defective_md}
            r["count"] = sum(r["daily"].values())

    day_totals = {}
    for r in detail.values():
        for day, v in (r.get("daily") or {}).items():
            day_totals[day] = day_totals.get(day, 0) + v
    dead = []
    if day_totals:
        med = sorted(day_totals.values())[len(day_totals) // 2]
        dead = sorted(d for d, v in day_totals.items()
                      if med and v < med * INCOMPLETE_DAY_FRACTION)

    degraded = None
    if dead:
        live_days = [d for d in sorted(day_totals) if d not in dead]
        # Loud, because a run that degrades three days running is
        # something a person should be told rather than something a log
        # should hold.
        print(f"::error::{win_key} degraded to {len(live_days)} of "
              f"{len(day_totals)} days. Incomplete in the archive: "
              f"{', '.join(f'{d} ({day_totals[d]:,} vs median {med:,})' for d in dead)}. "
              f"Both this week's counts and the baselines are recomputed "
              f"over the surviving days.", file=sys.stderr, flush=True)
        keep_md = [tuple(int(x) for x in d.split("-")[1:]) for d in live_days]
        for iso, r in detail.items():
            r["count"] = sum(v for k, v in (r.get("daily") or {}).items()
                             if k not in dead)
            hist = subset_hist(iso, keep_md, end.year)
            if hist:
                r["hist"] = hist

        # A year with no archive is not a year with no fire, AGAIN.
        #
        # subset_hist reads the per-day cache directly, so it does not
        # inherit the no-archive-year exclusion that fetch_window_baseline
        # applies when it writes country_history.json. Without this, the
        # 2022 hole (27 July to 10 August, no SNPP science archive at all)
        # returns as a zero and inflates every multiple by 14/13, exactly
        # the 7.7% corrected yesterday. Greece read 15.7x instead of 14.6x.
        #
        # Same roster-wide test as before: one country can legitimately
        # sum to zero across five days, ninety-four cannot.
        year_tot = {}
        for r in detail.values():
            for y, v in r["hist"].items():
                year_tot[y] = year_tot.get(y, 0) + v
        no_archive = sorted(y for y, t in year_tot.items() if t == 0)
        if no_archive:
            print(f"  excluding years with no archive over these days: "
                  f"{', '.join(no_archive)}", file=sys.stderr, flush=True)
        for r in detail.values():
            for y in no_archive:
                r["hist"].pop(y, None)
            if r["hist"]:
                r["mean"] = round(sum(r["hist"].values())
                                  / len(r["hist"]), 1)
        degraded = {"days_used": len(live_days),
                    "days_in_window": len(day_totals),
                    "excluded": dead}
        # rows were built from the pre-degradation numbers, so rebuild
        rows = rebuild_rows(detail, end)

    def strength(r):
        """Verdict to branch on, components to print.

        Design's shape, copied from heat's drift_weight rather than
        invented: the LIST alone forces the renderer to write
        `qualifies_on == ["multiple"]`, which puts this channel's gate
        rule in design's code. It agrees today and drifts silently the
        first time the gate changes, because the comparison keeps
        evaluating and keeps returning something. The VERDICT alone is
        safe and says nothing, and the page needs to state WHY those
        countries sit below the line rather than assert it.

        multiple_only is the weak case: above twice its own average, but
        inside the ordinary variation of its own record, so the multiple
        is the only measure calling it unusual. Not "one signal":
        Venezuela clears one and it is a fourteen-year record.
        """
        sig = signals(r)
        if not sig:
            verdict = "none"
        elif sig == ["multiple"]:
            verdict = "multiple_only"
        elif sig == ["z"]:
            verdict = "z_only"
        elif sig == ["record"]:
            verdict = "record_only"
        else:
            verdict = "corroborated"
        return {"verdict": verdict, "signals": sig,
                "z": r["z"], "multiple": r["multiple"],
                "rank_in_record": r["rank_n"]}

    for r in rows:
        r["qualifies_on"] = signals(r)
        r["strength"] = strength(r)
    eligible = [r for r in rows if qualifies(r)]
    eligible.sort(key=lambda r: -r["multiple"])
    eligible = eligible[:MAX_MARKERS]
    anomalous = {r["iso"] for r in eligible}
    # The three flags are ORTHOGONAL and a country can carry more than
    # one. Spain is pinned AND at a fourteen-year record; Canada is
    # pinned AND merely large. Collapsing them into a single class would
    # render those two identically, which is the whole failure this
    # split exists to prevent, so `anomalous` is recorded separately
    # rather than inferred from the absence of the other two.
    for r in eligible:
        r["anomalous"] = True

    # Volume context is a SEPARATE class, not a way through the gate.
    #
    # Yesterday I made volume a qualifying path so Canada would appear.
    # That was wrong, and the numbers say so: Canada reads 1.8x with
    # z=0.8 and rank 4 of 15, which is large and slightly above normal,
    # not abnormal. It put a country that is not anomalous onto a map of
    # anomalies. Worse, ORing volume into the gate also admitted Russia
    # at 0.3x, a country having a notably QUIET week.
    #
    # But DR Congo at 75,849 detections and exactly 1.0x is still the
    # single most important thing on a world fire map, and saying
    # nothing about it is its own distortion. So it ships flagged, and
    # design renders it as context rather than as news. One symbol
    # cannot mean both "this is unusual" and "this is where fire is".
    for r in rows:
        if (r["iso"] not in anomalous and r["count"] >= HIGH_VOLUME
                and r["multiple"] >= MIN_MULTIPLE * 0.6):
            r["volume_context"] = True
            eligible.append(r)

    # Pinned countries are appended after the gate has run, never merged
    # into it, so nothing about them changes what "qualified" means.
    #
    # multiple_unstable is the honest half of this. The UK reads 2.9x on
    # 407 detections against a mean of 138, below MIN_COUNT, and the
    # count floor exists precisely because a multiple on a baseline that
    # thin swings wildly on a handful of pixels. Pinning the UK does not
    # make that number sturdy, it makes it visible, so it ships flagged
    # and design decides whether to lead with rank instead.
    chosen = {r["iso"] for r in eligible}
    for r in rows:
        if r["iso"] in PINNED and r["iso"] not in chosen:
            r["pinned"] = True
            r["multiple_unstable"] = r["count"] < NOISE_FLOOR * 4
            eligible.append(r)
    for r in eligible:
        r.setdefault("anomalous", False)
        r.setdefault("pinned", r["iso"] in PINNED)
        r.setdefault("volume_context", False)
        r.setdefault("multiple_unstable", r["count"] < NOISE_FLOOR * 4)
    eligible.sort(key=lambda r: (-r["multiple"]))

    end_fmt = "%-d" if start.month == end.month else "%b %-d"
    win_label = f"wk {start.strftime('%b %-d')}-{end.strftime(end_fmt)}"
    source = f"NASA FIRMS SNPP, {win_label}"

    events = {
        "degraded": degraded,
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
            "anomalous": r["anomalous"],
            "qualifies_on": r.get("qualifies_on", []),
            "strength": r.get("strength"),
            "pinned": r["pinned"],
            "volume_context": r["volume_context"],
            "multiple_unstable": r["multiple_unstable"],
            "z": r["z"],
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
        "degraded": degraded,
        "complete": True,
        "markers": [{
            "region": r["region"], "lat": r["lat"], "lon": r["lon"],
            "multiple": r["multiple"], "count": r["count"],
            "rank": r["rank"], "attribution": r["attribution"],
            "anomalous": r["anomalous"],
            "qualifies_on": r.get("qualifies_on", []),
            "strength": r.get("strength"),
            "pinned": r["pinned"],
            "volume_context": r["volume_context"],
            "multiple_unstable": r["multiple_unstable"],
            "z": r["z"],
            "centroid_basis": r["centroid_basis"], "href": r["href"],
        } for r in eligible],
    }
    with open(os.path.join(REPO, "fires", "data",
                           "current_week.json"), "w") as f:
        json.dump({"window": win_key, "degraded": degraded,
                   "source": source, "countries": detail}, f, indent=1)
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
