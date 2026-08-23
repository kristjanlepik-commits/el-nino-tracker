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

# The bar the shared front-page map draws at, in z rather than in a
# multiple. Tested over 220 archive weeks; see fires/check_map_bar.py, which
# also keeps the mechanism I proposed for this and then refuted.
#
# A THRESHOLD, not a slot count: what gets drawn should be decided by what
# happened, not by how much room the map has.
DRAW_THRESHOLD = 3.0

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
            "rank_n": rank, "n_compared": len(hist) + 1,
            "z": round((count - mean) / sd if sd else 0.0, 2),
            "persistent_source": ((r.get("persistence") or {}).get("verdict")
                                  == "persistent_source"),
            "persistence": r.get("persistence"),
            "lat": r["lat"], "lon": r["lon"], "centroid_basis": r["basis"],
            "attribution": attribution_for(iso, end.month),
            "title": make_title(rank, multiple, count,
                                hist[prev_year], prev_year,
                                r["hist_expected"] + 1,
                                r["hist_expected"] + 1 - (len(hist) + 1)),
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


def make_title(rank, multiple, count, prev_best, prev_year, n_span, n_excluded):
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
        # NOT "since 2012", which asserts a continuous span we do not have,
        # and wherever a missing year would have outranked the current week
        # that claim is WRONG rather than imprecise. It is also the sentence
        # a reader lifts and quotes on its own, which is what D-051 is
        # about: the qualifier has to survive being quoted alone.
        #
        # AND NOT a bare "of 13" either. Product's argument, which is the
        # better one: "of 15, 2 excluded" SHOWS the gap, while "of 13"
        # hides it inside a smaller number that looks complete. A reader
        # given 13 has no way to know 15 seasons exist.
        #
        # "Excluded" rather than "absent" or "unobserved" on purpose: the
        # two exclusions are different in kind. 2022 has no archive and was
        # never observed; 2021 was observed and dropped deliberately so
        # this week could keep a day it was defective on. "Unobserved"
        # would be false of the second. "Excluded" is true of both, and the
        # payload carries the distinction for anyone who needs it.
        t = (f"{ORDINAL[rank]}-heaviest of {n_span} seasons"
             if not n_excluded else
             f"{ORDINAL[rank]}-heaviest of {n_span}, {n_excluded} excluded")
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
    # Years the baseline dropped deliberately so the current week could keep
    # a day they were defective on. Distinct from years with no archive,
    # which are a genuine gap and stay counted as due.
    years_defective = sorted(hist_doc.get("years_excluded_defective") or [])
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
    # Cropland context, loaded ONCE. A country can post a record
    # detection week that is mostly farmers clearing fields, and FIRMS
    # cannot tell that from a forest fire (tls-internal#31).
    #
    # FAILS SOFT BY DESIGN. Invariant 1 says this pipeline always
    # produces output, so a missing 111 MB raster withholds one optional
    # block rather than stopping a Monday. Withholding is also the
    # correct answer rather than a degraded one: a ratio computed
    # without the mask would not be a worse ratio, it would be a
    # different claim.
    crop_mask, crop_base, crop_unavailable, crop_ver = None, {}, None, {}
    try:
        from fires.cropland import CropMask, vintage as crop_vintage
        crop_mask = CropMask()
        crop_ver = crop_vintage()
        crop_base = json.load(open(os.path.join(
            REPO, "fires", "data", "cropland_baseline.json")))["countries"]
    except Exception as exc:
        # LOUD, BY NAME, ONCE. A missing mask drops this block from 80+
        # countries while every check stays green, which is the same
        # shape as the sign-off gate holding fires quietly for two days:
        # safe, and indistinguishable from healthy. A capability that
        # can vanish without announcing itself is one nobody notices
        # has gone, and this one produces numbers on 80+ country pages.
        crop_unavailable = str(exc)
        print("  " + "!" * 60, file=sys.stderr)
        print(f"  CROPLAND CONTEXT UNAVAILABLE. Every country's cropland "
              f"block will read withheld=mask_unavailable this run.\n"
              f"  Reason: {exc}\n"
              f"  Fetch the ASAP crop mask into fires/.cache/ to restore "
              f"it. See fires/cropland.py.", file=sys.stderr)
        print("  " + "!" * 60, file=sys.stderr)

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
        # Cropland context for this country's detections.
        #
        # THE RATIO IS THE STATISTIC, not the share. "4% of detections
        # are on cropland" is meaningless without knowing what share of
        # the country IS cropland, so every reading carries its own
        # denominator and both numbers are emitted rather than a verdict
        # alone.
        #
        # The label describes the RATIO, never the cause. "enriched"
        # is not "agricultural": it says these detections sit on
        # cropland more often than random land in the same country
        # does. What is burning stays an inference the reader makes.
        # WHY it is absent, never a bare null. These are four different
        # facts and a null renders them identically: the mask is gone,
        # the mask does not cover this country, the country did not burn
        # this week, or the sampling broke. Papua New Guinea carries
        # 8,352 detections and no coverage; reading that as the same
        # thing as Lithuania's zero-detection week would be wrong in
        # both directions.
        if crop_mask is None:
            cropland = {"withheld": "mask_unavailable",
                        "detail": crop_unavailable}
        elif not len(df):
            cropland = {"withheld": "no_detections"}
        elif not (crop_base.get(iso) or {}).get("covered"):
            cropland = {"withheld": "no_mask_coverage",
                        "_note": ("The mask has no data for this country. "
                                  "That is NOT a finding of no cropland, "
                                  "and must not be rendered as one.")}
        else:
            cropland = {"withheld": "sampling_failed"}
        if crop_mask is not None and len(df):
            base = crop_base.get(iso) or {}
            if base.get("covered"):
                try:
                    v = crop_mask.sample(df["longitude"].to_numpy(),
                                         df["latitude"].to_numpy())
                    v = v[~np.isnan(v)]
                    land_pct = float(base["mean_crop_pct"])
                    if len(v) and land_pct > 0:
                        det_pct = float(v.mean())
                        ratio = det_pct / land_pct
                        cropland = {
                            "detections_on_crop_pct": round(det_pct, 2),
                            "country_land_crop_pct": round(land_pct, 2),
                            "ratio": round(ratio, 3),
                            # A VERDICT NEEDS A SAMPLE. 50 is arbitrary
                            # and bounded: it is a threshold on SAMPLE
                            # SIZE, not a partition of the thing being
                            # measured, so the worst it can do is
                            # withhold a label that would have been
                            # right. The latitude line it replaces could
                            # invert a direction. Not the same kind of
                            # arbitrary.
                            #
                            # "insufficient_sample" is a verdict of "we
                            # cannot say", which is not silence: the
                            # numbers ship, only the label is withheld.
                            #
                            # Greece's week in
                            # the first run was 20 detections, its
                            # quietest of 15, and those 20 read
                            # "enriched" at 1.63 on nothing but noise.
                            # The numbers stay; only the label is
                            # withheld, because the label is the part
                            # that gets quoted on its own.
                            "reading": (
                                "insufficient_sample" if len(v) < 50 else
                                "enriched" if ratio > 1.3 else
                                "depleted" if ratio < 0.77 else "neutral"),
                            "n_detections_sampled": int(len(v)),
                            # WHICH MASK THIS NUMBER CAME FROM. The
                            # filename is the only versioning JRC gives,
                            # so a ratio from v04 is a claim ABOUT v04.
                            # If they ship v05 that is a different claim
                            # rather than a refreshed one, and carrying
                            # an old figure forward would be wrong. The
                            # vintage rides ON the number rather than at
                            # document level, per D-051, because the
                            # number gets quoted alone.
                            "source": ("ASAP crop mask %s, 500 m percent "
                                       "cropland, JRC" %
                                       (crop_ver.get("version") or "v04")),
                            "mask_vintage": crop_ver,
                            "_note": (
                                "Ratio of mean percent-cropland under this "
                                "week's detections to that under uniform "
                                "random points in the same country. Above "
                                "1.3 reads enriched, below 0.77 depleted, "
                                "and under 50 detections no label is given. "
                                "Describes WHERE detections fall, not what "
                                "is burning."),
                        }
                except Exception:
                    cropland = None

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
                       # DUE NO LONGER EQUALS EXPECTED ON THE YEAR SERIES,
                       # and the comment above explaining why it always did
                       # was written when the only missing year was 2022,
                       # which is genuinely absent from the archive and so
                       # is a real gap that should be drawn as one.
                       #
                       # Since 2026-08-11 a year can also be dropped ON
                       # PURPOSE, so the current week can keep a day that
                       # year was defective on. That is a comparability
                       # exclusion, exactly like the day-side case, and the
                       # rule there applies here: DUE falls, EXPECTED does
                       # not. Product found the consequence of not doing
                       # this: every country reported 14 due while holding
                       # 12, so two deliberate exclusions read as two gaps.
                       "hist_expected": len(YEARS_EXPECTED),
                       "hist_due": len(YEARS_EXPECTED) - len(years_defective),
                       "hist_excluded_for_comparability": years_defective,
                       "lat": lat, "lon": lon, "basis": basis}
        detail[iso]["cropland"] = cropland

        # PERSISTENT-SOURCE TEST. Needs the raw detections, so it is
        # computed here rather than in qualifies(), which only sees the
        # summarised row.
        #
        # The n floor is the same lesson as the cropland label: Greece's
        # week scored 29% recurrence on 24 detections, where a handful
        # of repeat cells dominates and means nothing. Below the floor
        # the country is judged normally rather than excluded on noise.
        persistent = None
        if len(df) >= 50 and "daynight" in df.columns:
            try:
                cell = (np.round(df["latitude"], 2).astype(str) + "," +
                        np.round(df["longitude"], 2).astype(str))
                days_seen = df.groupby(cell)["acq_date"].nunique()
                recur = float(cell.isin(
                    days_seen[days_seen >= 5].index).mean()) * 100
                night = float((df["daynight"].astype(str).str.upper()
                               == "N").mean()) * 100
                frp_med = float(df["frp"].astype(float).median())
                persistent = {
                    "recur_pct": round(recur, 1),
                    "night_pct": round(night, 1),
                    "frp_median": round(frp_med, 2),
                    "verdict": ("persistent_source"
                                if (recur > 15 and night > 60
                                    and frp_med < 6) else "fire_like"),
                }
            except Exception:
                persistent = None
        detail[iso]["persistence"] = persistent
        prev_year = max(h["hist"], key=lambda y: h["hist"][y])
        prev_best = h["hist"][prev_year]
        vals = list(h["hist"].values())
        sd = (sum((v - h["mean"]) ** 2 for v in vals) / len(vals)) ** 0.5
        z = (count - h["mean"]) / sd if sd else 0.0
        rows.append({
            "iso": iso, "region": h["name"], "count": count,
            # "of 15" WAS HARDCODED HERE, and it is the same defect as the
            # prose one degree deeper: a denominator asserted rather than
            # counted. rebuild_rows next to it derives len(hist) + 1
            # correctly, and rebuild_rows only runs on a DEGRADED week, so
            # the two paths disagreed and the wrong one was the normal one.
            # This week happened to be degraded, which is the only reason
            # the shipped rows were right.
            "multiple": round(multiple, 1),
            "rank": f"{rank} of {len(h['hist']) + 1}",
            "rank_n": rank, "n_compared": len(h["hist"]) + 1,
            # Carried ON the row because qualifies() sees nothing else.
            # A flag left only on `detail` would be computed, emitted
            # and silently ignored. Both this path and rebuild_rows must
            # set it: the comment above records these two disagreeing
            # once already, and rebuild_rows runs only on a degraded
            # week, so a gap here hides until the worst week.
            "persistent_source": ((persistent or {}).get("verdict")
                                  == "persistent_source"),
            "persistence": persistent,
            "z": round(z, 2), "lat": lat, "lon": lon,
            "centroid_basis": basis,
            "attribution": attribution_for(iso, end.month),
            "title": make_title(rank, multiple, count, prev_best, prev_year,
                                len(YEARS_EXPECTED) + 1,
                                len(YEARS_EXPECTED) + 1 - (len(h["hist"]) + 1)),
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
        """Noise floor, then any one significance signal.

        A PERSISTENT SOURCE IS NOT A FIRE SEASON. Saudi Arabia entered
        the qualifying set on 2026-08-23 at rank 1 of 15, on 697
        detections against a previous maximum of 687: a 1.5% "record"
        on a country whose fourteen Augusts all sit between 450 and 687.
        That flatness is the tell. Its detections run 85% at night, FRP
        median 2.8 MW, and 38% of them fall in cells seen on five or
        more of the seven days. A wildfire does not recur in the same
        0.01 degree cell for five consecutive days at 2.8 MW; gas
        flaring does, and Saudi Arabia and Algeria both have large
        fields.

        Measured rather than asserted, and the separation is not a tuned
        threshold. Genuine fire weeks score ZERO on recurrence:

            SAU  38.0% recur  85.5% night  FRP 2.8    persistent
            DZA  57.8%        78.9%        FRP 2.3    persistent
            BIH   0.0%        40.6%        FRP 5.5    fire
            SRB   0.0%        50.0%        FRP 5.9    fire
            MKD   0.0%   PRT  0.0%   ESP 5.1%         fire

        This NARROWS claims, so it ships without editorial sign-off per
        the rule stated above for attribution. It removes a country from
        the qualifying set; it never adds one.
        """
        if r.get("persistent_source"):
            return False
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
            # DUE falls, EXPECTED does not. A day dropped so both sides
            # stay like-for-like is not a gap and must not draw as one.
            #
            # Without this the payload contradicted itself: seven
            # expected, seven due, six values, and nothing saying the
            # missing one was removed on purpose. That is a day excluded
            # for comparability and a day missing from the archive
            # rendering identically, which is the exact failure the slot
            # counts exist to prevent, arriving inside the fix for it.
            r["daily_due"] = r["daily_expected"] - len(defective_md)
            r["daily_excluded_for_comparability"] = sorted(defective_md)

    day_totals = {}
    for r in detail.values():
        for day, v in (r.get("daily") or {}).items():
            day_totals[day] = day_totals.get(day, 0) + v
    dead = []
    if day_totals:
        med = sorted(day_totals.values())[len(day_totals) // 2]
        dead = sorted(d for d, v in day_totals.items()
                      if med and v < med * INCOMPLETE_DAY_FRACTION)

    # ABSENT IS NOT THIN, and only thin was being checked.
    #
    # The test above compares each day's total against the median of the
    # days THAT ARE THERE. A day the archive never returned never becomes a
    # key in day_totals, so it cannot be too low, so `dead` stays empty and
    # `degraded` stays null. On 2026-08-11 the page therefore presented a
    # seven-day window built from five days and disclosed nothing, with the
    # missing pair including yesterday.
    #
    # Set-difference against the calendar, per the same rule floods reached:
    # verify ABSENCE, not just values. Days removed on purpose for
    # comparability are excluded from this, because those are declared
    # elsewhere and are not a gap.
    expected_days = [(end - timedelta(days=offset)).isoformat()
                     for offset in range(window_days - 1, -1, -1)]
    unexplained = [d for d in expected_days
                   if d not in day_totals and d[5:] not in defective_md]
    if unexplained:
        print(f"::error::{win_key} is MISSING {len(unexplained)} of "
              f"{window_days} days entirely, and not for comparability: "
              f"{', '.join(unexplained)}. These are absent from the archive "
              f"rather than thin, so the median test cannot see them. The "
              f"window is reported as degraded.", file=sys.stderr, flush=True)
        dead = sorted(set(dead) | set(unexplained))

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
        # THE DENOMINATOR COMES FROM THE DECLARATION, NOT FROM THE DATA.
        #
        # This read len(day_totals), and day_totals is accumulated from
        # r["daily"], so a day absent from the archive never creates a
        # key and numerator and denominator fell together. It happened to
        # read 6 today only because the comparability exclusion removed
        # exactly one key. Product caught it, and it is the same failure
        # named forty lines above as "the exact failure the slot counts
        # exist to prevent, arriving inside the fix for it". It arrived
        # once more, in the sentence that summarises the work.
        #
        # A NEW SHAPE, worth naming: the spec's case is a constraint
        # emitted for the WHOLE payload being invisible to a page
        # rendering ONE ROW. This is the inverse. A constraint emitted
        # PER ROW was invisible to the sentence summarising the WHOLE.
        #
        # All four states, so the page can add up. A reader was told
        # "5 of 6 days" and "seven whole UTC days" on one page, and the
        # seventh day was unaccounted for anywhere.
        sample = next(iter(detail.values()), {})
        expected = sample.get("daily_expected", window_days)
        comparability = sorted(defective_md)
        degraded = {"days_used": len(live_days),
                    "days_in_window": expected,
                    "days_due": expected - len(comparability),
                    "excluded": dead,
                    "excluded_incomplete_archive": dead,
                    "excluded_for_comparability": comparability}
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

    # COUNTS, PUBLISHED WITH THEIR DEFINITIONS ATTACHED.
    #
    # WHY THIS EXISTS. On 2026-08-12 one sentence on the front page,
    # "N countries are past their own record fire week", produced four
    # different numbers from three chats: 18, 13, 13 and 17. None was an
    # arithmetic error. They counted different populations under different
    # thresholds, and the sentence named neither, so there was no way to
    # tell which was meant, or to check one against another.
    #
    # The replacement sentence was wrong in the other direction within
    # hours: "6 countries burned at three times their own same-week average
    # or more" counted MARKS ON A MAP, and eight countries burned at 3x.
    # The two missing were Lebanon at 5.4x, the highest multiple on the
    # board, and Ireland at 3.5x, both held back by the noise floor. A
    # reader asking which country burned most relative to normal would not
    # have found Lebanon anywhere.
    #
    # Both defects have one cause: a number derived by whoever renders it,
    # from a set they did not define. So fires publishes the counts, every
    # defensible one, each next to the population and rule that produced
    # it. A renderer picks a key and states the matching definition; it
    # never recounts. Same rule as reading a rank rather than re-deriving
    # it, which is the one heat and design have both been bitten by.
    #
    # If more than one is defensible for a given sentence, that is a
    # publishable fact and the page should say both rather than pick one
    # silently.
    with_baseline = [r for r in detail.values() if r.get("hist")]

    def _record(r):
        # At least as high as every prior year. Ties count as records: a
        # tie is not "below the record", and on this window it changes
        # nothing, but the rule has to be stated rather than discovered.
        return r["count"] >= max(r["hist"].values())

    def _multiple(r):
        return (r["count"] / r["mean"]) if r.get("mean") else 0.0

    anomalous_rows = [r for r in rows if r.get("anomalous")]
    counts = {
        "tracked": len(with_baseline),
        "anomalous": len(anomalous_rows),
        "record": sum(1 for r in with_baseline if _record(r)),
        "record_among_anomalous": sum(
            1 for r in anomalous_rows if "record" in (r.get("qualifies_on") or [])),
        "at_least_2x": sum(1 for r in with_baseline if _multiple(r) >= 2),
        "at_least_3x": sum(1 for r in with_baseline if _multiple(r) >= 3),
        "drawn": len(anomalous_rows),
        "_definitions": {
            "tracked": "countries with a same-week baseline this window. "
                       "The population every other count is taken from "
                       "unless it says otherwise.",
            "anomalous": "cleared the marker gate: z >= 2 OR multiple >= 2 "
                         "OR rank 1, after a 150-detection noise floor. A "
                         "GATE, not a significance test.",
            "record": "count at least as high as every prior year in its own "
                      "baseline, over ALL tracked countries. This is the one "
                      "that matches what a reader hears in 'past its own "
                      "record'.",
            "record_among_anomalous": "as `record`, restricted to countries "
                                      "that also cleared the gate. Smaller "
                                      "than `record` because the noise floor "
                                      "removes real records in small "
                                      "countries. Do not use this for a "
                                      "sentence about countries; it is a "
                                      "fact about the marker set.",
            "at_least_2x": "multiple >= 2 over ALL tracked countries.",
            "at_least_3x": "multiple >= 3 over ALL tracked countries. NOT "
                           "the number of marks drawn: marks also require "
                           "the gate, so this is larger.",
            "drawn": "countries in this file's `events` list, which is what "
                     "a map draws.",
            "_ties": "records count ties as records throughout.",
            "_warning": "Every count here is over a stated population. A "
                        "sentence that names none of them is not checkable "
                        "and will disagree with a different reasonable "
                        "reading of itself.",
        },
    }

    # THE MAP BAR, AND THE RULE THAT PRODUCED IT, IN THE PAYLOAD.
    #
    # Design was thresholding on `stat` in the renderer, which is
    # re-deriving this channel's selection rule from this channel's data.
    # Same defect as recounting the events list, and it fails the same way:
    # the day the rule changes, the page keeps applying the old one and
    # nothing errors. So the bar lives here and the page reads it.
    #
    # WHY z AND NOT A MULTIPLE. Tested over 220 archive weeks in
    # check_map_bar.py. When a z bar and a multiple bar disagree, the
    # country only z draws is at a genuine record 11% of the time against
    # 1% for the multiple, twelve against one, one-sided Fisher p = 0.001.
    # The volatility mechanism I first proposed for this is FALSE and the
    # module keeps the refutation; the surviving argument is only about
    # marginal picks. The effect is small: the bars agree in most weeks.
    #
    # A THRESHOLD, NOT A TOP-N, at design's request and they are right. A
    # fixed slot count decides what is drawn by how much room there is
    # rather than by what happened. A busy week should look busy.
    #
    # `caption` is emitted so the page can state the LIVE rule instead of
    # hard-coding a sentence about a bar it no longer applies. `why` is
    # per-member and uniform today, because the rule is a single
    # threshold; it exists so a compound rule later does not need a new
    # field, and so a reader of the payload never has to infer it.
    drawn_rows = [r for r in anomalous_rows if r.get("z", 0) >= DRAW_THRESHOLD]
    drawn_rows.sort(key=lambda r: -r["z"])
    drawn = {
        "rule": {
            "quantity": "z",
            "threshold": DRAW_THRESHOLD,
            "caption": (f"{DRAW_THRESHOLD:g} or more standard deviations "
                        f"above its own same-week mean"),
            "applied_to": "countries that cleared the marker gate, so the "
                          "150-detection noise floor still applies",
            "note": ("z, not a multiple: a multiple measures distance from "
                     "the mean and answers a different question that merely "
                     "correlates. See fires/check_map_bar.py."),
        },
        "members": [{"iso": r["iso"], "region": r["region"],
                     "z": r["z"], "multiple": r["multiple"],
                     "why": "z"} for r in drawn_rows],
        "n": len(drawn_rows),
        # NO SILENT CAPS. The gate caps the anomalous set at MAX_MARKERS as
        # a safety valve against a pathological week, and the drawn set is
        # a subset of it, so the cap can bind here without being visible.
        # If it ever does, the page should be able to say so.
        "gate_cap": MAX_MARKERS,
        "gate_cap_binding": len(anomalous_rows) >= MAX_MARKERS,
    }

    events = {
        "degraded": degraded,
        "counts": counts,
        "drawn": drawn,
        "_readme": [
            "Generated by fires/build_events.py; do not hand-edit.",
            "Window is the trailing seven fully-closed UTC days, so this",
            "file never carries a partial-day number. Titles are the",
            "claim only, without the region, per the design task file.",
            "COUNTS: read `counts`, never recount from `events`. The list",
            "is the gated marker set and is smaller than the tracked set,",
            "so counting it answers a question about the map rather than",
            "about the world. Each count names its own population.",
        ],
        "events": [{
            "date": end.isoformat(),
            "region": r["region"],
            "title": r["title"],
            "stat": f"{r['multiple']:.1f}x",
            # Derived, not "2012-25", which implied fourteen years the same
            # way the title did. The multiple is against the mean of the
            # baseline weeks we actually have.
            "stat_label": f"same-week mean, {r['n_compared'] - 1} yrs",
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
        # STATE THE BASELINE'S OWN PROPERTIES rather than leaving them to
        # be inferred from the data.
        #
        # Design's catch, D-104, after three chats got this wrong in three
        # different directions on one day. If the current year sits INSIDE
        # a baseline, z is bounded by (n-1)/sqrt(n) and a large value is
        # arithmetically impossible; if it sits outside, z has no ceiling.
        # Greece reads z = 13.10 this week, which is either legitimate or
        # a red flag depending entirely on a fact no consumer could see.
        #
        # It is outside. This baseline is 2012 to the year before the
        # current one, and the current year is never in it.
        # Derived across EVERY country, not from the first one.
        #
        # Taking one country's hist as representative of all 94 is the
        # habit I have now shipped three times this week: an artifact
        # standing in for the data it was derived from. Countries do not
        # all carry the same year count, so a single n would be a lie for
        # any that differ, and the lie would be invisible.
        ns = sorted({len(r.get("hist", {})) for r in detail.values()})
        all_years = sorted({y for r in detail.values()
                            for y in r.get("hist", {})})
        exp = sorted({r.get("hist_expected") for r in detail.values()
                      if r.get("hist_expected")})
        json.dump({"window": win_key, "degraded": degraded,
                   # FIRE's own freshness bound, per D-092: platform reports
                   # a missing bound rather than guessing one, because a
                   # guessed number that never fires is worse than none.
                   #
                   # data_as_of is the last day the window covers, which is
                   # yesterday on a healthy run, so the normal age is 1. Two
                   # tolerates a single missed run; three consecutive days
                   # without a pull is not a blip and the pages should stop.
                   #
                   # WHAT THIS DOES NOT CATCH, stated so nobody reads more
                   # into it: it measures whether the pipeline is RUNNING,
                   # not whether what it produced is complete. On 2026-08-11
                   # the window was perfectly current and still built from
                   # five of seven days. That failure is caught by the
                   # calendar set-difference above, not by this.
                   "data_as_of": end.isoformat(),
                   "max_data_age_days": 2,
                   "baseline": {
                       "window": win_key,
                       "years": all_years,
                       "n": ns[0] if len(ns) == 1 else None,
                       "n_range": [ns[0], ns[-1]] if ns else None,
                       "n_varies_by_country": len(ns) > 1,
                       "n_expected": exp[0] if len(exp) == 1 else exp,
                       "current_year_in_baseline": False,
                       "note": ("The current year is never in the baseline, "
                                "so z has no upper bound. A large z is a "
                                "measurement, not an artefact of n."),
                   },
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
