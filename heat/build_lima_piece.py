"""Lima as a fast-reaction piece, built from heat/data/lima_nights.json.

NOT A CITY PAGE, and the payload says why in its own why_not_a_city_page:
Lima clears 0 of 30 on BOTH WMO normals, so it has no percentile
thresholds, no bands and no rank of the kind every European page carries.
Those fields are absent rather than null.

KRISTJAN'S RULINGS, applied:

  4A  lead with the COUNT, 75 of 79, not the record night. The story
      going round is one night; the measurement is a season.
  5A  mark which Augusts were El Nino and claim nothing further in prose.
      The reader connects; we do not.

EVERY NUMBER IS READ FROM THE PAYLOAD. The first draft of the mockup
typed "75 of 77" and "16 of 18" from a chat message; the file says 79 and
20. Nothing here is retyped, including the length of the record.

WHAT THE PAGE MAY NOT SAY, from the payload's own may_not_say: no
unqualified "hottest on record", since the record is 36 measured Augusts
in GHCN rather than Lima's full observational history; no percentile or
anomaly against a 30-year normal, because none exists here; and not that
this is one record night, which is the framing our own count contradicts.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from templates.fast_reaction import render  # noqa: E402

D = json.loads((ROOT / "heat/data/lima_nights.json").read_text())
REC = sorted(D["august_record"], key=lambda r: -(r["warmest_night_c"] or 0))
CW = D["current_winter"]


def piece():
    top5 = REC[:5]
    cur_year = str(CW["year"])
    # Six bars: the five warmest Augusts and this one. Kristjan ruled on
    # this chart. Heat has since emitted the full 36-year record, which is
    # the more honest picture and is offered separately rather than
    # swapped in under a ruling.
    # `mark` colours the bar; the chart carries the word once in
    # mark_label rather than repeating it over every marked bar.
    # THE WHOLE RECORD, not the top five. The tally strip draws the record's
    # own shape, so feeding it six points drew six strokes and threw away
    # the thing the form exists to show. The six-bar chart was a constraint
    # of the old form; heat emits all 36 Augusts and the strip wants them.
    series = [{"x": str(r["year"]), "y": r["warmest_night_c"],
               "mark": r["enso"] == "el_nino"}
              for r in REC if r.get("warmest_night_c") is not None]
    series.append({"x": cur_year, "y": CW["warmest_night_c"]})

    n_nino = sum(1 for r in top5 if r["enso"] == "el_nino")
    # 2026 CARRIES NO ENSO LABEL. CPC's ONI runs to MJJ 2026 and every
    # other row is labelled by the JAS and ASO seasons, which do not exist
    # yet. Colouring or annotating 2026 as an El Nino August would assert
    # what we cannot support.
    # 2026 IS DELIBERATELY UNMARKED. CPC's ONI runs to MJJ 2026 and every
    # other bar is labelled by the JAS and ASO seasons, which do not exist
    # yet, so marking it would assert what we cannot support.

    mo = CW["by_month"]
    months = ", ".join(
        "%s %d of %d" % (nm, mo[k]["at_or_above_20"], mo[k]["measured"])
        for k, nm in (("06", "June"), ("07", "July"), ("08", "August"))
        if k in mo)

    return {
        "channel": "heat",
        "region": "Lima",
        "window": "1 June to %s" % _pretty(CW["to"]),
        "measured": "published " + _pretty(CW["to"]),
        "path": "/heat/lima-%s/" % CW["to"],
        "claim": ("Lima has had %d of its last %d winter nights at or above "
                  "20 degrees." % (CW["nights_at_or_above_20"],
                                   CW["nights_measured"])),
        "standfirst": (
            "%s. The warmest, %.1f degrees on 14 August, is the warmest "
            "August night in a record of %d measured Augusts. This is a "
            "season rather than a night: the count is the measurement and "
            "the single warmest night is one reading inside it."
            % (months, CW["warmest_night_c"], len(REC))),
        "value": {
            "display": "%d of %d" % (CW["nights_at_or_above_20"],
                                     CW["nights_measured"]),
            "caption": "winter nights at or above 20 degrees, %s to %s"
                       % (_pretty(CW["from"]), _pretty(CW["to"])),
        },
        "chart": {
            "label": "Every August in the record, on its own axis",
            "series": series,
            "current_x": cur_year,
            "baseline": None,
            "unit": " \u00b0C",
            "noun": "August",
            "noun_plural": "Augusts",
            "current_kicker": cur_year + ", ATTRIBUTION PENDING",
            "diverging": False,
            "decimals": 1,
            "mark_label": "El Nino",
            "annotations": [],
        },
        "instruments": [
            {"name": "Night temperature", "detail": "GHCN, station 84628",
             "value": "%.1f C" % CW["warmest_night_c"],
             "rank": "warmest of %d Augusts" % len(REC), "state": "measured"},
            {"name": "Percentile threshold",
             "detail": "no complete WMO normal exists for this station",
             "value": "not available", "rank": "", "state": "not_assessed",
             "caveat": "Lima clears 0 of 30 years on both WMO normals, so "
                       "the percentile bands every European city page "
                       "carries cannot be built here. This page counts "
                       "against a fixed 20 degrees instead, which needs no "
                       "baseline."},
        ],
        "source": {
            "name": "GHCN daily, station 84628 (Jorge Chavez)",
            "detail": "current winter from the station's own bulletins, "
                      "reconciled against GHCN on 149 days both hold, every "
                      "one identical",
            "as_of": _pretty(CW["to"]),
        },
        "attribution": "pending",
        "notes": {
            "what_this_is": (
                "Nights at or above 20 degrees, counted from 1 June, against "
                "every August in this station's GHCN record. %d of the five "
                "warmest August nights fell in an El Nino August, marked on "
                "the chart. Each August is labelled by the ocean AT THAT "
                "AUGUST, the mean CPC ONI across JAS and ASO, not by its "
                "calendar year." % n_nino),
            "what_this_is_not": (
                "Not the hottest on record unqualified: the record here is "
                "%d measured Augusts in GHCN, not Lima's full observational "
                "history. Not a percentile or an anomaly, because no "
                "complete 30-year normal exists for this station. And 2026 "
                "carries no El Nino label: CPC has published its index to "
                "MJJ 2026, and the seasons every other year is labelled by "
                "do not exist yet." % len(REC)),
        },
    }


MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def _pretty(iso):
    y, m, d = iso.split("-")
    return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)


if __name__ == "__main__":
    p = piece()
    out = ROOT / "docs" / p["path"].strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(p, root_prefix="../../"))
    print("wrote %s" % out.relative_to(ROOT))
