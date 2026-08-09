"""Per-city facts for social posts, computed rather than written.

WHY A SCRIPT AND NOT A LIST. Kristjan asked for city-specific posts during a
live heat event, which is exactly when a typed number goes stale: a fact
written on Monday can be false by Wednesday, and the failure is silent and
always in the flattering direction. Everything here is derived on each run
from the daily series, so a post assembled from this file is true when it is
assembled or it is not emitted at all.

WHAT MAKES A FACT USABLE HERE. It has to be checkable by a reader against
their own service's numbers, carry its own denominator, and survive the cut
advancing. "Hottest day since 1950" survives. "Third hottest day this
century" does not, because next week it may be fourth.

THE BOUND TRAVELS WITH THE FACT. Every record claim carries record_scope, the
first year of OUR record, because these stations mostly observed before our
series starts. Vienna is the live case: 39.8 C on 2026-08-04 is the hottest
in the record we hold from 1950, and Hohe Warte observed well before 1950.
"Vienna's hottest day ever" is false. A social post is the single most likely
place for that bound to be dropped for length, which is why it is a field
here rather than a note.

WHAT THIS FILE MUST NOT BE USED FOR. Our 36 cities were chosen because they
sit in the hot part of the map (Kristjan, 2026-08-08). So a count across
cities is a fact about OUR SET and never about Europe. Any post of the form
"N European cities..." is false. Per-city posts do not have this problem,
which is the main reason they are the right unit for this.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import build_city_series as B  # noqa: E402

OUT = ROOT / "heat" / "data" / "social_facts.json"
CUR = B.CURRENT_YEAR


def daily_max(city, meta):
    """{date: tmax} for the whole record, from whichever loader the city uses."""
    if meta["country"] == "FR":
        _tn, tx = B.load_mf(city, meta.get("station"))
        return {f"{y}-{m:02d}-{d:02d}": v
                for y, dd in tx.items() for (m, d), v in dd.items()
                if v is not None}
    f = meta.get("file")
    if not f:
        for cand in os.listdir(B.SRC):
            if cand.endswith(f"_{city}.json"):
                f = cand
                break
    if not f or not os.path.exists(B.SRC / f):
        return {}
    return {d: mx for d, mn, mx in json.loads((B.SRC / f).read_text())
            if mx is not None}


def daily_min(city, meta):
    if meta["country"] == "FR":
        tn, _tx = B.load_mf(city, meta.get("station"))
        return {f"{y}-{m:02d}-{d:02d}": v
                for y, dd in tn.items() for (m, d), v in dd.items()
                if v is not None}
    f = meta.get("file")
    if not f:
        for cand in os.listdir(B.SRC):
            if cand.endswith(f"_{city}.json"):
                f = cand
                break
    if not f or not os.path.exists(B.SRC / f):
        return {}
    return {d: mn for d, mn, mx in json.loads((B.SRC / f).read_text())
            if mn is not None}


def facts(city, meta):
    tx, tn = daily_max(city, meta), daily_min(city, meta)
    if not tx:
        return None
    years = sorted({int(d[:4]) for d in tx})
    ranked = sorted(tx.items(), key=lambda kv: -kv[1])

    # THE LEADING RUN. How many of the hottest days on record are this year,
    # counting from the top until a different year appears. A count, never a
    # constant: a sixth hot day makes it six, a cool week leaves it where it
    # is. This is the fact behind "the N hottest days in our record are all
    # this summer" and it is the strongest thing in this file, because a rank
    # carries its own denominator and needs no adjective.
    run = 0
    for d, _v in ranked:
        if not d.startswith(str(CUR)):
            break
        run += 1

    hottest_d, hottest_v = ranked[0]
    prev = next(((d, v) for d, v in ranked if not d.startswith(str(CUR))),
                (None, None))

    # Tropical nights, LIKE FOR LIKE, and the first version of this was
    # wrong in a way worth recording. It counted the current year to date
    # against FULL historical years, so Palma read 59 against a "typical" 89
    # and looked like a quiet summer. It is August. Every historical year had
    # another four months to accumulate nights and 2026 did not.
    #
    # That error runs in the reassuring direction, which is the one nobody
    # queries, and it would have produced a confident "fewer tropical nights
    # than usual" post out of nothing but the calendar.
    #
    # So every year is cut to the same day of the year as the current one.
    _last = max(d[5:] for d in tx if d.startswith(str(CUR)))
    tn_by_year = {}
    for d, v in tn.items():
        if v >= 20.0 and d[5:] <= _last:
            tn_by_year[int(d[:4])] = tn_by_year.get(int(d[:4]), 0) + 1
    cur_tn = tn_by_year.get(CUR, 0)
    tn_hist = sorted(tn_by_year.get(y, 0) for y in years if y != CUR)
    tn_median = (tn_hist[len(tn_hist) // 2] if tn_hist else 0)

    return {
        "city": city,
        "country": meta["country"],
        "station": meta["station"],
        "record_scope": {
            "from_year": min(years),
            "text": f"our series, from {min(years)}",
            "is_all_time": False,
            "may_not_say": ["hottest ever", "all-time record",
                            "hottest since records began"],
        },
        "hottest_day": {"date": hottest_d, "c": hottest_v,
                        "is_current_year": hottest_d.startswith(str(CUR))},
        # TOP TEN INDIVIDUAL DAYS, one basis, dates included. Editor asked
        # for this because the sentence the Note leads on is a day-level
        # ranking and nothing in the payload exposed one, so the visual that
        # matches the claim could not be built. The two series that do exist
        # cannot substitute and disagree by construction: warmest_day_c is
        # full-year and has no 2026 entry, warmest_day_to_cut_c is cut and
        # reads 37.4 for the year the record was actually 38.5.
        #
        # BASIS STATED ON THE FIELD, because that is the whole problem this
        # solves: every day in the record, no cut, no seasonal window. It is
        # the same basis the five-hottest-days claim is made on, so a reader
        # can check the claim against this list directly.
        "hottest_days": {
            "basis": "every individual day in the record, uncut and with no "
                     "seasonal window. NOT comparable with warmest_day_c "
                     "(full-year maxima) or warmest_day_to_cut_c (cut).",
            "top": [{"date": d, "c": t, "year": int(d[:4])}
                    for d, t in ranked[:10]],
        },
        # PREVIOUS HIGH, WITH WHETHER THE CHART CAN SHOW IT. Editor found
        # this on Vienna: the previous high is 38.5 on 2013-08-08, and
        # Vienna's cut is 08-07, so the to-cut series reads 37.4 for 2013.
        # Both figures are correct and they are different facts, exactly as
        # warmest_note says. The trap is that copy cites the full-record
        # high while the chart underneath plots the to-cut series, and the
        # page then disagrees with itself with nothing to explain it.
        #
        # It is 11 of 36 cities, not a Vienna quirk, and the gaps reach
        # 9.3 C at Bilbao. So it is a field: a renderer or a writer can see
        # that the cited record is INVISIBLE in the chart beside it.
        "previous_high": {
            "date": prev[0], "c": prev[1],
            "visible_in_to_cut_series": (
                bool(prev[0]) and prev[0][5:] <= _last),
            "if_not_visible": (
                "the day this record was set falls AFTER this city's cut, "
                "so the to-cut series cannot show it. Do not caption a "
                "to-cut chart with this value: the chart will contradict "
                "the caption. Cite it only against the full-record ranking."
                if prev[0] and prev[0][5:] > _last else None),
        },
        "leading_run": {
            "n": run,
            "dates": [d for d, _ in ranked[:run]],
            "next_rank_year": (int(ranked[run][0][:4])
                               if run < len(ranked) else None),
            "post_form": (
                f"{city}'s {run} hottest days since {min(years)} all fell in "
                f"{CUR}." if run >= 2 else None),
            "is_a_count": "recompute every run. Never write the number into "
                          "copy as a literal.",
        },
        "tropical_nights": {
            # NAMED median_to_cut, NOT median_year. Editor caught the first
            # name: it held a to-cut value while saying year, which is the
            # exact trap that produced the Palma error one field earlier.
            # The next person to use it under time pressure would have used
            # it as an annual figure and the arithmetic would have looked
            # fine.
            "current": cur_tn, "median_to_cut": tn_median,
            "counted_to": _last,
            "basis": f"median of {min(years)}-{max(y for y in years if y != CUR)}"
                     f", each year counted to the same date",
            "metric_reaches_city": tn_median >= 3,
            # NEVER RANK THESE ACROSS CITIES, and the reason is not the one
            # the gate covers. Night records start in different years:
            # Lyon 1975, Palma 1978, Murcia 1984 against Zaragoza 1951 and
            # Madrid 1920. A city whose "typical" is drawn from a warmer era
            # has a smaller multiple for the same real change, so Lyon's
            # 6.4 and Zaragoza's 6.4 are not the same quantity. Editor's
            # finding, and it is the 24-thermometers argument again.
            #
            # The direction is at least safe: a short warm baseline
            # UNDERSTATES, so a city with a late record start has a real
            # change larger than its multiple shows.
            "comparable_across_cities": False,
            "why_not_comparable": "baselines start in different years, so a "
                                  "city with a late record start has a "
                                  "warmer 'typical' and a smaller multiple "
                                  "for the same real change. Never order "
                                  "cities by this, in copy or in a thread.",
            "baseline_from_year": min(years),
            "why_gated": "below about three nights in a typical year the "
                         "ratio divides by almost nothing and the metric "
                         "says more about the denominator than the summer.",
            # THE GATE WORKS AGAINST WHOEVER IS WRITING THE POST, which is
            # socials' finding and the reason it is stated on the datum
            # rather than in a note somewhere. The BIGGEST multiples sit
            # almost entirely on cities where this is false, because a thin
            # base is exactly what produces a large ratio: Paris 18 nights
            # against a typical 1, Toulouse 31 against 2, Lugano 42 against
            # 2. Anyone scanning this file for a striking number finds the
            # unpostable ones FIRST.
            # BASIS NAMED IN THE STRING, at editor's instruction, because
            # the city pages state a different "typical" for the same city:
            # Valencia reads 26.6 there (1961-1990 mean, to cut) and 29 here
            # (all-year median, to cut). Both are defensible and neither is
            # wrong, but published the same week on two surfaces with
            # nothing to distinguish them, one number looks like it changed.
            # Two measures visibly labelled read as two measures.
            #
            # NO MULTIPLE STATED. "51 against 10" is punchier than "five
            # times" and it cannot be wrong. "By this date" is what stops
            # the Palma error; neither phrase may be cut for length. A post
            # that cannot fit them runs without the comparison, not without
            # the basis.
            "post_form": (
                f"{city}: {cur_tn} nights so far this year that never "
                f"dropped below 20 C. By this date in a typical year "
                f"across its {min(years)}-"
                f"{max(y for y in years if y != CUR)} record: {tn_median}."
                if tn_median >= 3 and cur_tn > tn_median else None),
            "not_postable_reason": (
                None if tn_median >= 3 else
                "the typical count is too small for a ratio to mean "
                "anything. A big multiple here is a fact about the "
                "denominator. Do not post it however striking it looks."),
        },
    }


def main() -> int:
    out = {}
    for city, meta in B.CITIES.items():
        f = facts(city, meta)
        if f:
            out[city] = f
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    runs = sorted(((v["leading_run"]["n"], c) for c, v in out.items()),
                  reverse=True)
    print(f"  {len(out)} cities")
    print("  strongest leading runs:")
    for n, c in runs[:8]:
        if n:
            print(f"    {c:12s} {n} hottest days on record are {CUR}")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
