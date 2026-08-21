"""Turn GDACS flood alerts into candidate boxes to point IMERG at.

TASKING ONLY. Nothing here is evidence and nothing here enters a payload.
GDACS tells us WHERE TO LOOK; our own instruments decide what, if
anything, is true. We never write "GDACS reports flooding in Poland",
because that is relaying someone else's claim and it is the line between
using an alert to aim and becoming a slower rebroadcast of one.

WHY IT EXISTS. On 2026-08-21 this channel measured three European basins
and found all three normal. The measurement was right and the aim was
wrong: we measured where our boxes were, not where the water was. Six
pre-screened basins existed, so six got measured, and an event in the
Alps or southern France would have produced nothing and been read as
nothing happening.

TWO MODES, DELIBERATELY. This tasks the fast response. The standing
screened basins keep running regardless. If the feed ever becomes the
only thing that starts a measurement, the channel has quietly become a
GDACS mirror with a longer latency, and can never find what nobody else
noticed, which is the whole reason to own instruments rather than cite
them.

ALERT LEVEL IS LOAD-BEARING. Without alertlevel the API returns 2 events
in 30 days; with Green included it returns 74. Green is where Europe
lives. Verified 2026-08-21.
"""

import argparse
import datetime as dt
import json
import math
import subprocess
import sys

API = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

# THE POINT-TO-BOX DECISION, which is the methodology call in this file.
#
# A GDACS point is a centroid, not a catchment, and box geometry moves the
# measured signal by a factor of four: the 2017 Peru event reads 1.8x the
# median over a regional rectangle and 4.4x over the Piura and Chira
# catchments alone. So a box drawn as a circle around a point is
# SYSTEMATICALLY WEAKER than one drawn on the catchment, and a tasked
# measurement should be read as a floor, not as the region's best answer.
#
# 75 km is a stated default rather than a per-case choice, sized against
# the eastern Pyrenees box that worked (about 155 by 111 km). Too small
# misses the catchment and falls under the count floor, as the Tana did at
# 157 flood pixels a week; too large dilutes the signal with everywhere
# the water did not go.
#
# It is a starting box for a human to redraw on a catchment, never a
# final one.
BOX_RADIUS_KM = 75.0


def get(url, timeout=90):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", str(timeout), url],
                       capture_output=True)
    body = r.stdout.decode("utf-8", "replace")
    if not body.lstrip().startswith(("[", "{")):
        raise SystemExit(f"gdacs: not JSON ({len(body)} bytes). Refusing to "
                         f"treat a non-answer as an answer.")
    return json.loads(body)


def box_around(lon, lat, km=BOX_RADIUS_KM):
    """Degrees for a fixed distance, honest about latitude.

    A degree of longitude shrinks with the cosine of latitude, so a box
    specified in degrees is far wider in Spain than in Norway. Specifying
    it in km and converting keeps the boxes comparable, which matters
    because their totals will be compared against each other's history."""
    dlat = km / 111.32
    dlon = km / (111.32 * max(math.cos(math.radians(lat)), 0.15))
    return (round(lon - dlon, 2), round(lon + dlon, 2),
            round(lat - dlat, 2), round(lat + dlat, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--min-days", type=int, default=3,
                    help="skip events shorter than this; a 14-day rainfall "
                         "window cannot resolve a one-day alert")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    end = dt.date.fromisoformat(args.as_of)
    start = end - dt.timedelta(days=args.days)
    url = (f"{API}?eventlist=FL&fromdate={start}&todate={end}"
           f"&alertlevel=Green;Orange;Red")
    feats = get(url).get("features", [])

    tasks, skipped = [], []
    for f in feats:
        p = f.get("properties", {})
        g = f.get("geometry", {})
        if g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        try:
            f0 = dt.date.fromisoformat(p["fromdate"][:10])
            f1 = dt.date.fromisoformat(p["todate"][:10])
        except Exception:
            continue
        span = (f1 - f0).days + 1
        rec = {
            "eventid": p.get("eventid"), "country": p.get("country", "?"),
            "alertlevel": p.get("alertlevel"),
            "from": f0.isoformat(), "to": f1.isoformat(), "span_days": span,
            "point": [lon, lat],
            "box": list(box_around(lon, lat)),
            "box_radius_km": BOX_RADIUS_KM,
            "box_is_a_catchment": False,
        }
        if span < args.min_days:
            rec["skipped_because"] = (
                f"event spans {span} day(s); a 14-day accumulation window "
                f"cannot resolve it, and D-195 measured this instrument "
                f"under-reading concentrated rainfall by 3 to 5 times")
            skipped.append(rec)
        else:
            tasks.append(rec)

    tasks.sort(key=lambda r: ({"Red": 0, "Orange": 1, "Green": 2}
                              .get(r["alertlevel"], 3), -r["span_days"]))
    out = {
        "role": "TASKING ONLY. Not evidence, never cited, never enters a "
                "payload. It decides where to point an instrument.",
        "second_mode_required": (
            "the standing screened basins keep running regardless. If this "
            "feed becomes the only thing that starts a measurement, the "
            "channel is a GDACS mirror with a longer latency and can never "
            "find what nobody else noticed."),
        "box_caveat": (
            "a GDACS point is a centroid, not a catchment. Box geometry "
            "moves the measured signal by up to 4x, so a circle around a "
            "point reads systematically weaker than a catchment-drawn box. "
            "Treat any tasked measurement as a floor and redraw on the "
            "catchment before publishing."),
        "generated": args.as_of, "window_days": args.days,
        "source_url": url,
        "n_events": len(feats), "n_tasks": len(tasks), "n_skipped": len(skipped),
        "tasks": tasks, "skipped": skipped,
    }
    json.dump(out, open(args.out, "w"), indent=1)

    print(f"  {len(feats)} GDACS flood events in {args.days} days, "
          f"{len(tasks)} taskable, {len(skipped)} too short\n")
    print(f"  {'alert':7}{'country':22}{'span':>5}  {'window':24} box")
    for t in tasks[:14]:
        b = t["box"]
        print(f"  {t['alertlevel']:7}{t['country'][:21]:22}{t['span_days']:5d}  "
              f"{t['from']} to {t['to']}  "
              f"[{b[0]:.1f},{b[1]:.1f},{b[2]:.1f},{b[3]:.1f}]")
    print(f"\n  wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
