"""Render the fast-reaction template with two channels' data.

The visual chat's test, and the reason this file exists: a template
reviewed against one channel encodes that channel's assumptions. Fires
think in multiples of a mean, in counts, over a 15-year satellite
record. El Nino has no multiple; its magnitude is an anomaly in degrees
that can be negative. If both render without either looking wrong, it is
a template. If only one does, it is a page with variables.

Both cases are built from committed data only, never from a comp and
never from a working tree:

    fires/data/current_week.json    France, detections this week
    data/oni_historical.csv         Nino 3.4 ONI, every develop year

Writes to .fast-reaction-preview/ which is gitignored. This is a
design harness, not a publish path: it writes nothing into docs/.

    .venv/bin/python templates/validate.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from templates.fast_reaction import render  # noqa: E402

OUT = ROOT / ".fast-reaction-preview"


def fire_piece() -> dict:
    """France, a magnitude series: counts against a same-week mean."""
    data = json.loads((ROOT / "fires" / "data" / "current_week.json").read_text())
    fr = (data.get("countries") or data)["FRA"]
    hist = {int(k): v for k, v in fr["hist"].items()}
    now, mean = fr["count"], fr["mean"]
    series = ([{"x": y, "y": hist[y]} for y in sorted(hist)]
              + [{"x": 2026, "y": now}])
    prev_max = max(hist.values())
    return {
        "channel": "fire",
        "region": fr["name"],
        "window": data.get("window", ""),
        "claim": (f"{fr['name']} had {now / mean:.1f} times its normal "
                  f"fire activity for this week of the year"),
        "standfirst": (
            "One question: how unusual is this week, measured against the "
            "same week in every year the satellite has flown. The baseline "
            "is drawn behind the bars, so the multiple can be checked by "
            "eye rather than taken on trust."),
        "value": {
            "display": f"{now / mean:.1f}×",
            "caption": (f"active-fire detections against the same-week mean "
                        f"of {mean:,.0f}, 2012 to 2025"),
        },
        "chart": {
            "label": "Against the same week, every year",
            "series": series,
            "current_x": 2026,
            "baseline": {"value": mean, "label": f"same-week mean {mean:,.0f}"},
            "unit": "detections",
            "diverging": False,
            "annotations": [{"x": 2026,
                             "text": f"{now / prev_max:.1f}× the "
                                     f"previous highest"}],
        },
        "source": {"name": "NASA FIRMS SNPP VIIRS",
                   "detail": "thermal anomaly counts, daily, 375 m",
                   "as_of": data.get("end", "")},
        "attribution": "non_enso",
        "notes": {
            "what_this_is": (
                "A rate. How much fire activity satellites detected this "
                "week against what this week normally looks like in this "
                "country. Every year is measured by the same sensor, so "
                "the comparison is like for like."),
            "what_this_is_not": (
                "Not burnt area, which is a different instrument measuring "
                "a different thing. Not an attribution: western European "
                "fire seasons are driven by heat, drought, wind and land "
                "use, and this event carries no established link to the "
                "developing El Nino."),
        },
    }


def enso_piece() -> dict:
    """Nino 3.4, a diverging series: anomalies that can run negative."""
    rows = []
    with (ROOT / "data" / "oni_historical.csv").open() as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            for year, season, oni in csv.reader([line]):
                try:                       # the file carries a header row
                    rows.append((int(year), season.strip(), float(oni)))
                except ValueError:
                    continue
    season = rows[-1][1]
    same = [(y, v) for y, s, v in rows if s == season]
    if len(same) < 6:                      # fall back to the fullest season
        counts = {}
        for _, s, _v in rows:
            counts[s] = counts.get(s, 0) + 1
        season = max(counts, key=counts.get)
        same = [(y, v) for y, s, v in rows if s == season]
    same.sort()
    cur_y, cur_v = same[-1]
    series = [{"x": y, "y": v} for y, v in same]
    return {
        "channel": "elnino",
        "region": "Niño 3.4",
        "window": f"{season} season, {cur_y}",
        "claim": (f"The {season} Niño 3.4 anomaly is "
                  f"{cur_v:+.1f} °C, against a threshold of "
                  f"+0.5"),
        "standfirst": (
            "The same question in a different unit. There is no multiple "
            "here: the magnitude is an anomaly in degrees, and it runs "
            "negative in La Niña years, so the series hangs from zero "
            "rather than sitting on it."),
        "value": {
            "display": f"{cur_v:+.1f} °C",
            "caption": (f"Niño 3.4 ONI for {season}, three-month "
                        f"running mean, ERSST.v5 against the 1991-2020 "
                        f"climatology"),
        },
        "chart": {
            "label": f"{season} anomaly, every develop year on record",
            "series": series,
            "current_x": cur_y,
            "baseline": {"value": 0.5, "label": "El Niño threshold +0.5"},
            "unit": "°C",
            "diverging": True,
            "annotations": [],
        },
        "source": {"name": "NOAA CPC ONI",
                   "detail": "three-month running mean, ERSST.v5",
                   "as_of": f"{season} {cur_y}"},
        "attribution": "enso",
        "notes": {
            "what_this_is": (
                "An anomaly. How far the Niño 3.4 region sits above or "
                "below its own 1991-2020 average, in degrees Celsius, for "
                "one three-month season."),
            "what_this_is_not": (
                "Not a forecast, and not a probability. This is the "
                "observed state of one index for one season; what it "
                "implies for the winter peak is the weekly brief's "
                "question, not this one."),
        },
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, piece in (("fire.html", fire_piece()),
                        ("enso.html", enso_piece())):
        html = render(piece, root_prefix="../docs/")
        (OUT / name).write_text(html)
        ch = piece["chart"]
        ys = [p["y"] for p in ch["series"]]
        print(f"  {name:10} {piece['region']:12} "
              f"{len(ch['series']):>3} points, "
              f"range {min(ys):+.2f} to {max(ys):+.2f}, "
              f"diverging={ch['diverging']}, {len(html):,} bytes")
    print(f"wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
