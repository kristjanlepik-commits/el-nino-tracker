"""Emit the Fire channel's data seam for the ECON chat.

ECON builds fast damage context from live channel data and joins to us
on geography and date range. It never asks us to declare an event: event
identity comes from whichever estimator named the event, so nothing here
asserts that a fire "is" an event.

Field set agreed with ECON on 2026-07-28. Their spec section 5 asked for
`event_status: ongoing | ended`, which this channel cannot honestly
emit. Our unit is a country-week, not an event: a country clearing the
gate in successive windows is two rows, not one event with a duration,
so nothing in the data has a start or an end. Worse, "ended" is
unobservable while it matters. The strongest claim the data supports is
"did not clear the gate this window", and a country can fail the gate
for one quiet week and resume. Emitting that as `ended` would let a
mid-event revision be read as post-event knowledge growth, which is the
exact error the field existed to prevent.

Replaced, at ECON's acceptance, by three fields:

    activity_status      active | quiet | dormant
    area_revision_open   true | false
    area_lag_days        int

The second pair is the one that does ECON's actual work. Their case is
AccuWeather's LA estimate rising fivefold in four days while the fires
still burned, so the figure grew partly because the event grew and
partly because knowledge grew, with nothing in the record separating
them. The same confound sits in our hectare series for a different
reason: EFFIS and GWIS map perimeters retrospectively, so year-to-date
area keeps climbing for weeks after fires stop. These two fields say
whether a rise in our number is the hazard developing or the mapping
catching up, per country and per week.

Everything here is D-033 tier 1, Measured: each series runs against its
own history and no number is created by combining sources. Attribution
is passed through untouched, and `pending` never means a weak yes.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAIL = os.path.join(REPO, "fires", "data", "current_week.json")
AREA = os.path.join(REPO, "fires", "data", "burnt_area.json")
AREA_HIST = os.path.join(REPO, "fires", "data", "area_history")
EVENTS = os.path.join(REPO, "data", "events.json")
OUT = os.path.join(REPO, "fires", "data", "econ_seam.json")

# A week counts as in-season if its median burning across prior years
# reaches this fraction of the country's median peak week. Anchoring to
# the country's own peak rather than to an absolute hectare figure is
# what lets one threshold serve both Canada and Portugal. 5% is loose on
# purpose: the cost of calling a burning week dormant is far higher than
# the cost of calling a quiet week in-season, because only `dormant`
# approximates "ended" downstream.
SEASON_FLOOR = 0.05


def season_weeks(years: dict, current_year: int) -> set:
    """Weeks where this country normally burns, from its own record.

    Derived from weekly deltas of the cumulative area series rather than
    from the cumulative values themselves: cumulative area only ever
    rises, so it would mark every week after the first fire as in-season
    for the rest of the year.
    """
    per_week = {}
    for y, weeks in years.items():
        if int(y) >= current_year:
            continue                      # incomplete season, no vote
        ordered = sorted((int(w), v) for w, v in weeks.items())
        prev = 0.0
        for w, cum in ordered:
            per_week.setdefault(w, []).append(max(0.0, cum - prev))
            prev = cum
    if not per_week:
        return set()
    median = {}
    for w, vals in per_week.items():
        s = sorted(vals)
        n = len(s)
        median[w] = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    peak = max(median.values()) or 0.0
    if peak <= 0:
        return set()
    return {w for w, v in median.items() if v >= peak * SEASON_FLOOR}


def main() -> None:
    detail = json.load(open(DETAIL))
    window = detail.get("window", "")
    dets = detail.get("countries") or detail
    try:
        areas = json.load(open(AREA))["countries"]
    except (OSError, ValueError, KeyError):
        areas = {}
    try:
        events = json.load(open(EVENTS))["events"]
    except (OSError, ValueError, KeyError):
        events = []

    # Countries clearing the gate this window. Absence from this set is
    # what separates `active` from the other two, and nothing more: it
    # is a threshold result, not a statement that fires stopped.
    gated = {e["region"] for e in events}
    attribution = {e["region"]: e.get("attribution", "pending")
                   for e in events}
    year = date.today().year
    iso_week = date.today().isocalendar()[1]

    rows = {}
    for iso, det in dets.items():
        name = det.get("name")
        if not name or not det.get("hist"):
            continue
        hist = {int(k): v for k, v in det["hist"].items()}
        now, mean = det["count"], det["mean"]
        area_cur = areas.get(iso)

        years = None
        hist_path = os.path.join(AREA_HIST, f"{iso}.json")
        if os.path.exists(hist_path):
            try:
                years = json.load(open(hist_path))["years"]
            except (OSError, ValueError, KeyError):
                years = None

        # active beats season membership: a country burning outside its
        # normal season is precisely the case worth flagging, so the
        # gate result is read first and the calendar only breaks the tie
        # for countries that are not currently gated.
        if name in gated:
            status = "active"
        elif years and season_weeks(years, year):
            status = "quiet" if iso_week in season_weeks(years, year) \
                else "dormant"
        else:
            status = "quiet"      # no season evidence, so no dormant claim

        row = {
            "event_id": f"fire.{iso}.{window}",
            "geography": {"country": name, "iso3": iso, "admin1": None},
            "window": window,
            "baseline_tier": "measured",
            "attribution": attribution.get(name, "pending"),
            "activity_status": status,
            "detections": {
                "measure": "VIIRS SNPP thermal anomaly detections",
                "units": "count",
                "value": now,
                "instrument": "NASA FIRMS SNPP VIIRS, daily, 375 m",
                "analog_comparison": {
                    "basis": "same calendar window, prior years",
                    "mean": mean,
                    "multiple": round(now / mean, 3) if mean else None,
                    "by_year": hist,
                },
                # Whole UTC days from a static archive, so unlike the
                # area series this number does not move after the fact.
                "revision_open": False,
            },
        }

        if area_cur:
            avg = area_cur.get("avg_ha") or 0
            # Open for the current season only: a completed season's
            # perimeters are mapped and the cumulative figure has
            # stopped moving. This is the flag that tells ECON whether a
            # rise is the hazard or the mapping.
            open_ = bool(area_cur.get("as_of", "").startswith(str(year)))
            row["area"] = {
                "measure": "cumulative burnt area, year to date",
                "units": "hectares",
                "value": area_cur.get("area_ha"),
                "instrument": (f'{area_cur.get("source", "")} mapped '
                               f'perimeters, weekly'),
                "as_of": area_cur.get("as_of"),
                "analog_comparison": {
                    "basis": "same week of prior seasons, computed by "
                             "Copernicus, not by us",
                    "mean": avg,
                    "multiple": area_cur.get("multiple"),
                },
                "area_revision_open": open_,
                "area_lag_days": area_cur.get("lag_days"),
            }
        else:
            row["area"] = None
        rows[iso] = row

    doc = {
        "_readme": [
            "Fire channel seam for ECON. Unit is a country-week, not an",
            "event: this file never declares that an event exists or has",
            "ended. Join on geography and date range.",
            "activity_status: active means clearing our gate this window;",
            "quiet means not clearing it but within the country's normal",
            "burning season; dormant means outside that season. Only",
            "dormant approximates 'ended', and a country can go quiet for",
            "one week and resume.",
            "area_revision_open: the hectare figure is still subject to",
            "upward revision because perimeters are mapped after the fact.",
            "A rise while this is true may be mapping catching up rather",
            "than the hazard developing. Detections do not revise.",
            "attribution 'pending' means not yet examined. It is not a",
            "weak yes and must not collapse into an ENSO-attributed loss.",
        ],
        "generated": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "window": window,
        "evidence_basis": "measured",
        "countries": rows,
    }
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    by_status = {}
    for r in rows.values():
        by_status[r["activity_status"]] = by_status.get(
            r["activity_status"], 0) + 1
    print(f"wrote {len(rows)} countries to {OUT}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())))
    open_n = sum(1 for r in rows.values()
                 if r.get("area") and r["area"]["area_revision_open"])
    print(f"  area_revision_open: {open_n} of "
          f"{sum(1 for r in rows.values() if r.get('area'))} with area")


if __name__ == "__main__":
    main()
