"""Build docs/fires/<slug>/ for every country in data/events.json.

Under D-030 the front end is the design chat's, so the layout lives in
templates/country_page.py and this file is the adapter: it reads the
Fire chat's validated JSON, shapes one piece dict per country, and
renders. It contains no layout and no CSS, and the template contains no
knowledge of FIRMS, EFFIS, GWIS or baseline gates. That boundary is the
point: the Fire chat can change its science freely as long as the JSON
shape holds.

Country set comes from data/events.json and is NOT a fixed list. It was
14 yesterday and 12 today, and the Fire chat is about to change the gate
that selects it (it currently ranks on the weekly detection multiple
alone, which leaves Algeria eleventh while leading on year-to-date area
at 14.2x, and Italy with no page at all despite 3.3x for the year).
Directories from a previous, larger set linger under docs/fires/ and are
left alone rather than deleted: this builder owns what it writes, not
what it finds.

Reads, all committed:

    data/events.json                which countries have a page
    fires/data/current_week.json    detections, dailies, same-week history
    fires/data/burnt_area.json      hectares to date, per-country source
    fires/data/area_history/<ISO>   weekly cumulative area, every season
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from templates.country_page import render  # noqa: E402

EVENTS = os.path.join(REPO, "data", "events.json")
DETAIL = os.path.join(REPO, "fires", "data", "current_week.json")
AREA = os.path.join(REPO, "fires", "data", "burnt_area.json")
AREA_HIST = os.path.join(REPO, "fires", "data", "area_history")
OUTDIR = os.path.join(REPO, "docs", "fires")

ORD = {1: "highest", 2: "second-heaviest", 3: "third-heaviest",
       4: "fourth-heaviest", 5: "fifth-heaviest"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def pretty_window(window: str) -> str:
    """"07-21..07-27" into "21 to 27 July"."""
    m = re.match(r"(\d{2})-(\d{2})\.\.(\d{2})-(\d{2})", window or "")
    if not m:
        return window or ""
    m1, d1, m2, d2 = (int(x) for x in m.groups())
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    if m1 == m2:
        return f"{d1} to {d2} {months[m2 - 1]}"
    return f"{d1} {months[m1 - 1]} to {d2} {months[m2 - 1]}"


def pretty_day(iso: str) -> str:
    """"2026-07-24" into "24 July", so prose reads as prose."""
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    try:
        _, m, d = iso.split("-")
        return f"{int(d)} {months[int(m) - 1]}"
    except (ValueError, IndexError):
        return iso


def build_piece(ev, det, area_cur, area_years, window, elsewhere, year):
    name = ev["region"]
    hist = {int(k): v for k, v in det["hist"].items()}
    now, mean = det["count"], det["mean"]
    rank = 1 + sum(1 for v in hist.values() if v > now)
    daily = det.get("daily") or {}
    peak_day, peak_val = (max(daily.items(), key=lambda kv: kv[1])
                          if daily else ("", 0))
    normal = mean / 7.0
    cleared = sum(1 for v in daily.values() if v > normal)

    # The claim leads with whichever timescale is more extreme, and always
    # names which clock it is on.
    #
    # Leading on a fixed timescale buries the story on half the set: at
    # 1.9x on the week against 14.2x on the year, Algeria's own page
    # would open on its least remarkable number, while Botswana at 5.9x
    # against 0.4x would open on a record year it is not having. Naming
    # the timescale is what stops the other one being read as a summary
    # of both, which is the failure the never-adjacent rule exists to
    # prevent one paragraph earlier.
    #
    # It argues from this country's own baselines only. No ENSO framing:
    # most of the live set is tagged pending, and the house context does
    # not travel into a channel page as an assumption.
    week_mult = now / mean if mean else 0.0
    week_claim = (f"{name} had its {ORD.get(rank, str(rank) + 'th-heaviest')} "
                  f"fire week for this point in the year since {min(hist)}")
    claim = week_claim
    if area_cur and area_years:
        year_mult = area_cur.get("multiple") or 0.0
        prev = [y for y in area_years if y != year]
        rec = max(prev, key=lambda y: max(area_years[y].values())) if prev else None
        rec_v = max(area_years[rec].values()) if rec else 0
        beat_record = bool(rec and max(area_years[year].values()) > rec_v)
        # A broken all-time record outranks any ratio. Comparing the two
        # multiples alone put France on its week at 10.2x against 8.9x,
        # which is true but weaker than the fact it displaced: a season
        # that has already passed every completed year on record is a
        # different kind of statement from a large multiple, and no
        # ratio is more extreme than it. Below that, the two multiples
        # decide.
        if beat_record:
            claim = (f"{name} has already burned more this year than in "
                     f"any full year on record")
        elif year_mult > week_mult:
            claim = (f"{name} has burned {year_mult:.1f} times its normal "
                     f"area for this point in the year")

    piece = {
        "region": name,
        "year": year,
        "window_pretty": pretty_window(window),
        "claim": claim,
        "standfirst": (
            "Two questions, side by side. How bad was this week, measured "
            "against every week like it. How bad is the year, measured "
            "against every season on record. Different instruments, "
            "different units, and one of them is not finished."),
        "attribution": ev.get("attribution", "pending"),
        "detections": {
            "count": now,
            "mean": mean,
            "hist": hist,
            "daily": daily,
            "multiple": now / mean if mean else 0.0,
            "baseline_span": f"{min(hist)} to {max(hist)}",
            "instrument": "NASA FIRMS SNPP VIIRS, daily, 375 m",
            "daily_note": (
                f"{cleared} of {len(daily)} days cleared one seventh of a "
                f"normal week. The peak, {peak_val:,} on "
                f"{pretty_day(peak_day)}, is {peak_val / normal:.0f} times "
                f"that line."
                if daily and normal else "Day by day through the window."),
        },
        "elsewhere": elsewhere,
        "what_this_is": (
            "Two measurements of the same fire season at two time scales. "
            "The multiple is a rate: how much fire activity satellites "
            "detected this week against what this week normally looks "
            "like. The hectare figure is a stock: how much land has been "
            "mapped as burnt since January. A country can have an "
            "unremarkable week and still be having a record year, and the "
            "reverse is also true."),
        "what_this_is_not": (
            "Not one number at two zoom levels. The two figures come from "
            "different instruments with different latencies, and they are "
            "not convertible into each other. Not an attribution: fire "
            "seasons are driven by heat, drought, wind and land use, and "
            "the tag on this page states what is and is not established "
            "for this event. Not a forecast of where the season ends."),
    }

    if area_cur and area_years:
        first_year = min(area_years)
        prev = [y for y in area_years if y != year]
        rec = max(prev, key=lambda y: max(area_years[y].values())) if prev else None
        rec_v = max(area_years[rec].values()) if rec else 0
        cur_v = max(area_years[year].values())
        beat = (f"It has already passed {rec}, the previous record season, "
                f"at {rec_v:,.0f} ha." if rec and cur_v > rec_v else
                f"The record season, {rec}, reached {rec_v:,.0f} ha."
                if rec else "")
        weeks_in = max(area_years[year])
        piece["area"] = {
            "area_ha": area_cur["area_ha"],
            "multiple": area_cur.get("multiple") or 0.0,
            "week": area_cur.get("week"),
            "as_of": area_cur.get("as_of"),
            "source": area_cur.get("source", ""),
            "instrument": f'{area_cur.get("source", "")} mapped perimeters, weekly',
            "years": area_years,
            "first_year": first_year,
            "cumulative_note": (
                f"Only this year carries hue; every grey line is one earlier "
                f"season accumulating from January. {beat}"),
            "weekly_note": (
                f"Week by week rather than cumulative, so a single heavy "
                f"week is visible as one. The cell runs to week 52: "
                f"{52 - weeks_in} weeks of this season have not happened "
                f"yet."),
        }
        # Instruments, plural, both named, each with its own baseline. The
        # source is read per country: 33 of 45 resolve to GWIS and 12 to
        # EFFIS, so a literal would name a European instrument for
        # Canadian fires.
        piece["rail_instruments"] = (
            f'NASA FIRMS SNPP VIIRS<br>thermal anomaly counts, daily, 375 m'
            f'<br><br>{area_cur.get("source", "")} burnt area<br>'
            f'mapped perimeters, weekly. Area lands in the week it is '
            f'mapped, which need not be the week it burned.')
        piece["rail_baseline"] = (
            f'Weekly multiple: same-week mean, {min(hist)} to {max(hist)}.'
            f'<br>Cumulative: complete seasons, {first_year} to {year - 1}.')
        piece["rail_revision"] = (
            'Mapped area for recent weeks rises as perimeters are '
            'completed, and a week&rsquo;s area may be mapped after the '
            'week it burned. Published figures are not edited in place; '
            'corrections run forward.')
    else:
        piece["area"] = None
        piece["rail_instruments"] = (
            'NASA FIRMS SNPP VIIRS<br>thermal anomaly counts, daily, 375 m')
        piece["rail_baseline"] = (
            f'Weekly multiple: same-week mean, {min(hist)} to {max(hist)}.')
        piece["rail_revision"] = (
            'Detection counts are whole UTC days and are not revised. '
            'Published figures are not edited in place.')

    tag = piece["attribution"]
    piece["rail_attribution"] = {
        "enso": ('ENSO-loaded window<br>This event falls in a window and '
                 'region where an ENSO teleconnection is established. '
                 'That is a loading, not a cause.'),
        "non_enso": ('not ENSO-linked<br>No established teleconnection '
                     'between ENSO and fire weather in this region. The '
                     'swell raised this; the wave did not.'),
        "pending": ('attribution pending<br>No assessment has been made '
                    'for this event yet. Pending means not yet examined, '
                    'and is not a weak yes.'),
    }[tag if tag in ("enso", "non_enso", "pending") else "pending"]
    return piece


def main() -> None:
    events = json.load(open(EVENTS))["events"]
    detail = json.load(open(DETAIL))
    window = detail.get("window", "")
    dets = detail.get("countries") or detail
    try:
        areas = json.load(open(AREA))["countries"]
    except (OSError, ValueError, KeyError):
        areas = {}
    name2iso = {v.get("name"): k for k, v in dets.items()}
    year = date.today().year

    written = 0
    for ev in events:
        iso = name2iso.get(ev["region"])
        det = dets.get(iso) if iso else None
        if not det or not det.get("hist"):
            print(f"  skip {ev['region']}: no detection detail")
            continue
        area_cur = areas.get(iso)
        # A country can have fire detections and no mapped burnt area at
        # all: Saudi Arabia and Libya both read 0 ha for 2026 across a
        # 21-year EFFIS/GWIS record, because desert fire leaves no
        # mappable perimeter. The row exists, so `areas.get(iso)` is
        # truthy, and every value in it is zero.
        #
        # Passing that through renders an area cell whose series maxes at
        # zero. Treat "no area anywhere" as no area section, which the
        # template already handles, rather than an area section full of
        # zeros. This is an adapter decision about which data exists, not
        # a layout one.
        if area_cur and not (area_cur.get("area_ha") or 0):
            area_cur = None
        area_years = None
        hist_path = os.path.join(AREA_HIST, f"{iso}.json")
        if area_cur and os.path.exists(hist_path):
            try:
                raw = json.load(open(hist_path))["years"]
                area_years = {int(y): {int(w): v for w, v in wk.items()}
                              for y, wk in raw.items()}
                if year not in area_years:
                    area_years = None
            except (OSError, ValueError, KeyError):
                area_years = None
        # events.json hrefs are root-relative because the landing page
        # consumes them from the site root. This page already sits at
        # /fires/<slug>/, so the prefix has to become a sibling hop or
        # the link resolves to /fires/<slug>/fires/<other>/.
        elsewhere = []
        for o in events:
            if o["region"] == ev["region"]:
                continue
            href = o.get("href", "")
            if href.startswith("fires/"):
                href = "../" + href[len("fires/"):]
            elsewhere.append(dict(o, href=href))
            if len(elsewhere) == 3:
                break
        piece = build_piece(ev, det, area_cur, area_years, window,
                            elsewhere, year)
        out = os.path.join(OUTDIR, slugify(ev["region"]))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w") as fh:
            fh.write(render(piece))
        written += 1
    print(f"wrote {written} country page(s) to docs/fires/")


if __name__ == "__main__":
    main()
