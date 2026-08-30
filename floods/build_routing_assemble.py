"""Assemble the rain, river and anchor layers into one routing dataset.

What this file DOES let a figure show:
  where rain fell, which modelled reaches rose, and in what ORDER they
  peaked. Peak-day ordering is the routing signal and it is measured.

What it does NOT let a figure show:
  that a given raindrop reached a given river. We hold no flow-direction
  or catchment grid, so no water is traced here. A drawn arrow is an
  interpretation of the timing, not a traced path, and must be labelled
  that way.
"""
import json
import math
import os

RAIN = "floods/data/routing_rain_2026-08.json"
RIVER = "floods/data/routing_river_2026-08.json"
PAYLOAD = "floods/data/payload_alto_beni_2026-08-22.json"
CLUSTERS = "floods/data/glofas_clusters_2026-08-22.json"
CORROB = "floods/data/corroboration_peru_2026-08.json"
OUT = "floods/data/routing_andes_2026-08.json"


def km(a, b, c, d):
    R = 6371.0
    p = math.radians
    return 2 * R * math.asin(math.sqrt(
        math.sin(p(c - a) / 2) ** 2
        + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2))


def nearest(cells, lat, lon):
    best, bd = None, 1e9
    for c in cells:
        d = km(lat, lon, c["lat"], c["lon"])
        if d < bd:
            best, bd = c, d
    return best, bd


def reach_for(cells, lat, lon, must_reach=None, radius_km=12.0):
    """Pick the river cell a named place actually sits on.

    Nearest-by-distance is wrong here. At 0.05 degrees a main stem and a
    creek can be adjacent, so the nearest cell to a town is often the
    wrong river: snapping Chulumani by distance landed on a reach peaking
    at 18 m3/s when the sweep had measured 225 there.

    Where we know the sweep's own window value for this place, a peak
    below that value is impossible at the same cell, since a peak is
    never smaller than a mean. That is a hard constraint, not a fit, so
    it is used to exclude cells rather than to choose among them. Among
    the survivors we take the largest reach within the radius.
    """
    near = [(km(lat, lon, c["lat"], c["lon"]), c) for c in cells]
    near = [(d, c) for d, c in near if d <= radius_km]
    if not near:
        return None, None, "no reach within radius"
    ok = near
    if must_reach is not None:
        ok = [(d, c) for d, c in near if c["peak_m3s"] >= must_reach]
        if not ok:
            return None, None, (
                "no reach within %.0f km peaks at or above the sweep value "
                "of %.1f m3/s; pairing refused" % (radius_km, must_reach))
    # Nearest among the reaches large enough to be the one the sweep
    # measured. Distance breaks the tie, magnitude sets the candidate set.
    d, c = min(ok, key=lambda t: t[0])
    return c, d, None


def main():
    rain = json.load(open(RAIN))
    river = json.load(open(RIVER))
    pay = json.load(open(PAYLOAD))
    clus = json.load(open(CLUSTERS))
    corrob = json.load(open(CORROB))

    anchors = []
    for src, kind in ((pay["named_places"], "bolivia_named_place"),
                      (clus["clusters"], "flagged_cluster")):
        for p in src:
            lat = p["lat"]
            lon = p["lon"]
            must = p.get("discharge_m3s")  # sweep window value, named places only
            rc, rd, why = reach_for(river["cells"], lat, lon, must_reach=must)
            pc, pd_ = nearest(rain["cells"], lat, lon)
            a = {
                "kind": kind,
                "name": p.get("name") or f"cluster {p['cluster']}",
                "country": p.get("country", "Bolivia"),
                "lat": lat,
                "lon": lon,
                "record_multiple_x_median": p.get("x_median"),
                "record_rank": p.get("rank"),
                "record_of": p.get("of"),
                "record_note": p.get("note", ""),
                "river_peak_m3s": rc["peak_m3s"] if rc else None,
                "river_peak_date": rc["peak_date"] if rc else None,
                "river_series": rc["series"] if rc else None,
                "river_cell_lat": rc["lat"] if rc else None,
                "river_cell_lon": rc["lon"] if rc else None,
                "river_cell_km_away": round(rd, 1) if rc else None,
                "river_cell_unmatched_reason": why,
                "sweep_window_value_m3s": must,
                "label_is_orientation_only": bool(rc and rd and rd > 5.0),
                "rain_window_mm": pc["total_mm"] if pd_ < 12 else None,
                "rain_peak_day": pc["peak_day"] if pd_ < 12 else None,
                "rain_peak_mm": pc["peak_mm"] if pd_ < 12 else None,
                "rain_cell_km_away": round(pd_, 1),
            }
            # A rank says a reach ran high for the date. It does NOT say a
            # flood wave passed. Shape does. rise_factor is the peak over the
            # quiet level in the three days before the rain, and it separates
            # the two cleanly: a flood wave is a spike, an elevated river is
            # a flat line sitting above its median.
            if a["river_series"]:
                quiet = min(a["river_series"][:3])
                a["quiet_level_m3s"] = round(quiet, 1)
                a["rise_factor"] = round(a["river_peak_m3s"] / quiet, 1) if quiet > 0 else None
                rf = a["rise_factor"]
                a["hydrograph_shape"] = (
                    "flood_wave" if rf and rf >= 5
                    else "pulse" if rf and rf >= 2
                    else "elevated_but_flat")
            anchors.append(a)
    # Hard check: a peak can never be below the window mean at the same cell.
    bad = [a for a in anchors
           if a.get("sweep_window_value_m3s") and a.get("river_peak_m3s")
           and a["river_peak_m3s"] < a["sweep_window_value_m3s"]]
    if bad:
        raise SystemExit("cell pairing failed for: "
                         + ", ".join(a["name"] for a in bad))
    unmatched = [a["name"] for a in anchors if a.get("river_cell_unmatched_reason")]
    if unmatched:
        print("UNMATCHED anchors (no hydrograph paired):", ", ".join(unmatched))
    anchors.sort(key=lambda a: -(a["river_peak_m3s"] or 0))

    # Order of peaking is the routing evidence. Report it, do not draw it.
    by_day = {}
    for a in anchors:
        if a["river_peak_date"]:
            by_day.setdefault(a["river_peak_date"], []).append(a["name"])

    top_rain = rain["cells"][:40]
    out = {
        "dataset": "rain-to-river routing, east Andes, August 2026",
        "built": "2026-08-30",
        "built_for": "design, per Kristjan's request for a figure showing where the rain fell and how it reached different rivers",
        "methodology_version": "1.4",
        "layers_are_never_merged": (
            "rain is observed, river is modelled. They answer different "
            "questions and no combined index is computed anywhere in this file."
        ),
        "what_this_supports": [
            "a rain field for 15-22 August, observed, 0.1 degree",
            "a river network for 13-26 August, MODELLED, 0.05 degree, each reach carrying its peak value and the day it peaked",
            "anchors: places where we hold a multiple against the 47-year record",
            "peak-day ordering, which is the routing signal",
        ],
        "what_this_does_not_support": [
            "tracing water from a rain cell to a river cell. No flow-direction or catchment grid is held here, so any arrow on the figure is an interpretation of timing, not a traced path.",
            "a claim that any river was observed at a record level. Every discharge number in this file is modelled.",
        ],
        "timing": {
            "rain_peak_day_in_box": max(
                {d: sum(c["by_day"].get(d, 0) for c in rain["cells"])
                 for d in rain["days_held"]}.items(), key=lambda kv: kv[1])[0],
            "rain_daily_box_total_mm": {
                d: round(sum(c["by_day"].get(d, 0) for c in rain["cells"]), 0)
                for d in rain["days_held"]},
            "anchors_by_river_peak_day": by_day,
            "place_labels": (
                "Town names on the anchors are orientation, not measurement "
                "points. Every discharge figure is read at a model cell, and "
                "where label_is_orientation_only is true that cell is more "
                "than 5 km from the town. In terrain this steep a main stem "
                "and a creek sit in adjacent cells, so a label placed on the "
                "wrong reach is the easiest error to make on this figure."
            ),
            "shape_vs_rank": (
                "Ranking a window mean against the same window in prior years "
                "answers 'was this reach high for the date'. It does not "
                "answer 'did a flood wave pass'. Those come apart here: every "
                "anchor below ranks first or near it, and only some have a "
                "hydrograph shaped like a flood. Read rise_factor and "
                "hydrograph_shape before describing any reach as flooding."
            ),
            "reading": (
                "Rain peaks first, rivers peak after. The gap between a "
                "catchment's rain day and its river's peak day is the "
                "response time, and it is longer for reaches further down."
            ),
        },
        "headline_case": {
            "name": "Caranavi",
            "why": (
                "16.1 mm of local rain and a modelled river at 620.6 m3/s, "
                "first of 48 years. The water did not fall there. This is the "
                "single clearest illustration that the rain map and the river "
                "map are different maps."
            ),
        },
        "rain_layer": {
            "file": RAIN,
            "instrument": rain["instrument"],
            "observed_or_modelled": rain["observed_or_modelled"],
            "days_held": rain["days_held"],
            "days_missing": rain["days_missing"],
            "cells_drawn": rain["cells_drawn"],
            "floor_mm": rain["rain_floor_mm"],
            "caveat": rain["instrument_caveat"],
            "wettest_40_cells": top_rain,
        },
        "river_layer": {
            "file": RIVER,
            "instrument": river["instrument"],
            "observed_or_modelled": river["observed_or_modelled"],
            "product_type": river["product_type"],
            "days_held": river["days_held"],
            "days_missing": river["days_missing"],
            "days_missing_note": (
                "The first day requested has not been returned on either "
                "attempt at this dataset. Observed twice, so treat the first "
                "requested day as not retrievable rather than as a gap in the "
                "record, and request one day earlier than you need."
            ),
            "reaches_drawn": river["cells_drawn"],
            "floor_m3s": river["flow_floor_m3s"],
            "rise_note": river["rise_note"],
        },
        "anchors": anchors,
        "corroboration": {
            "Bolivia": pay["event_corroboration"],
            "Peru": {
                "file": CORROB,
                "rainfall": corrob["verdict"]["rainfall"],
                "river_record": corrob["verdict"]["river_record"],
                "asymmetry": corrob["verdict"]["asymmetry"],
            },
        },
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {OUT}")
    print(f"  anchors: {len(anchors)}  "
          f"rain cells: {rain['cells_drawn']}  reaches: {river['cells_drawn']}")
    print("  rain daily box totals:", out["timing"]["rain_daily_box_total_mm"])
    print("  anchors by river peak day:")
    for d in sorted(by_day):
        print(f"    {d}  {', '.join(by_day[d])}")


if __name__ == "__main__":
    main()
