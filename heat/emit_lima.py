"""Lima's winter nights, as a different artifact from a city page.

WHY THIS IS NOT A CITY PAGE. Lima clears 0 of 30 years on BOTH WMO standard
normals in GHCN, so the percentile instrument every European page is built on
cannot be constructed here. Rome is built and absent from the set for exactly
that reason and LatAm gets no exception, so this is a different thing rather
than a truncated version of the same thing: a count of nights above 20 C set
against the record of August minima, with each year's ENSO state marked.

WHY IT IS WORTH BUILDING ANYWAY. The five warmest August nights in Lima's
record are 1997, 2023, 1983, 1976 and 2015. That is the El Nino list, in
order. No European page we publish can show the tracker's own thesis; this
one shows it without an argument attached.

And it carries the count-versus-peak distinction that the European pages
exist to make. The story going round is one record night on 14 August. The
measurement is that 75 of the last 77 winter nights have been at or above
20 C, which is a season rather than an evening.

THE SOURCE QUESTION, RULED AND PROVEN RATHER THAN ASSERTED. The historical
record is GHCN; the current winter is the station's own WMO bulletins. Two
sources on one chart is exactly the like-for-like failure that has bitten
this project repeatedly, so it was tested on every year both sources hold:

    2023   67 shared days   worst difference 0.0 C
    2024   82 shared days   worst difference 0.0 C, 82 of 82 exact

149 days, every one identical. They are the same measurement, and the
comparison holds. Had they differed the chart would have been GHCN-only with
the current year ABSENT rather than approximated, because an honest gap beats
a comparison that does not hold.

The construction is stated in the payload rather than here, because a rule
that lives in a docstring is a rule the renderer cannot check.
"""
from __future__ import annotations

import collections
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))
import synop  # noqa: E402

SRC = ROOT / "heat" / ".cache" / "src"
OUT = ROOT / "heat" / "data" / "lima_nights.json"
GHCN_ID = "PEM00084628"
WMO = "84628"
TROPICAL_NIGHT_C = 20.0
CURRENT_YEAR = 2026


def ghcn_minima():
    """Every daily minimum in the archive, quality-flagged values excluded."""
    p = SRC / f"ghcn_{GHCN_ID}.dly"
    out = {}
    for L in p.read_text(errors="replace").splitlines():
        if L[17:21] != "TMIN":
            continue
        y, m = int(L[11:15]), int(L[15:17])
        for d in range(31):
            o = 21 + d * 8
            v, q = L[o:o + 5].strip(), L[o + 6:o + 7]
            if v in ("-9999", "") or q.strip():
                continue
            out[f"{y}-{m:02d}-{d + 1:02d}"] = int(v) / 10.0
    return out


def bulletin_minima(year):
    """The station's own bulletins for one winter, June to August.

    The daily minimum is the lowest across all reports for that date, which
    is the construction validated against GHCN at 0.0 C on 149 shared days.
    """
    raw = subprocess.run(
        ["curl", "-sS", "--max-time", "200",
         f"https://www.ogimet.com/cgi-bin/getsynop?block={WMO}"
         f"&begin={year}06010000&end={year}08312359"],
        capture_output=True).stdout.decode("utf-8", "replace")
    if raw.count("AAXX") < 20:
        raise SystemExit(
            f"  Lima {year}: bulletins returned {len(raw)} bytes with no "
            f"usable reports. That is a fetch failure, not a quiet winter. "
            f"Nothing written.")
    out = {}
    for d, _h, _tx, tn in synop.parse_ogimet(raw):
        if tn is not None:
            out[d] = min(out.get(d, 99.0), tn)
    return out


def enso_by_year():
    """ENSO state DURING EACH AUGUST, from the ONI season containing it.

    NOT the calendar-year label, and this is the difference between a chart
    that makes our argument and one that refutes it. enso_year_status.csv
    classifies 1983 as la_nina, because La Nina developed in the second half
    of that year. But August 1983 sat in the decay of the 1982-83 El Nino,
    one of the strongest on record, whose own row is filed under 1982.

    So the calendar-year label would have put a LA NINA year among the five
    warmest August nights, on a chart whose entire claim is that the warmest
    August nights are El Nino nights. The label would have contradicted the
    argument the chart exists to make, and it would have been our own file
    saying so.

    The August in question sits in the ASO season, so that is the value read:
    CPC's ONI for July-August-September and August-September-October, from
    the same file analog.py uses. A season at or above +0.5 is El Nino
    conditions, at or below -0.5 La Nina, between them neutral. That is CPC's
    own threshold and it describes the ocean at the time of the night being
    ranked rather than the year it fell in.
    """
    seasons = {}
    with open(ROOT / "data" / "oni_full_history.csv") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            try:
                seasons[(int(parts[0]), parts[1])] = float(parts[2])
            except ValueError:
                continue
    out = {}
    for (y, ssn), v in seasons.items():
        if ssn not in ("JAS", "ASO"):
            continue
        cur = out.setdefault(y, {"vals": []})
        cur["vals"].append(v)
    for y, d in out.items():
        m = sum(d["vals"]) / len(d["vals"])
        d.clear()
        d["oni_at_august"] = round(m, 2)
        d["type"] = ("el_nino" if m >= 0.5 else
                     "la_nina" if m <= -0.5 else "neutral")
        d["strength"] = ("very_strong" if m >= 2.0 else
                         "strong" if m >= 1.5 else
                         "moderate" if m >= 1.0 else
                         "weak" if m >= 0.5 else None)
    return out


def _latest_oni():
    """The most recent season CPC has actually published, named."""
    last = None
    with open(ROOT / "data" / "oni_full_history.csv") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) >= 3:
                try:
                    last = {"year": int(parts[0]), "season": parts[1],
                            "oni": float(parts[2])}
                except ValueError:
                    continue
    return last


def main() -> int:
    g = ghcn_minima()
    enso = enso_by_year()

    # AUGUST MINIMA BY YEAR, the record the current winter is set against.
    # A year needs 20 August nights to be ranked; a fortnight of readings
    # cannot carry a "warmest August night" claim for that year.
    aug = collections.defaultdict(list)
    for d, v in g.items():
        if d[5:7] == "08":
            aug[int(d[:4])].append(v)
    record = {y: {"warmest_night_c": round(max(v), 1),
                  "nights_measured": len(v),
                  "nights_at_or_above_20": sum(1 for x in v
                                               if x >= TROPICAL_NIGHT_C)}
              for y, v in aug.items() if len(v) >= 20}

    cur = bulletin_minima(CURRENT_YEAR)
    months = collections.defaultdict(list)
    for d, v in cur.items():
        months[d[5:7]].append(v)
    winter = sorted(cur)
    above = [d for d in winter if cur[d] >= TROPICAL_NIGHT_C]
    cur_aug = {d: v for d, v in cur.items() if d[5:7] == "08"}

    ranked = sorted(record.items(), key=lambda kv: -kv[1]["warmest_night_c"])
    warmest_2026 = round(max(cur_aug.values()), 1) if cur_aug else None
    beaten = [y for y, r in ranked if r["warmest_night_c"] < warmest_2026]

    payload = {
        "_readme": (
            "Lima winter nights. NOT a city page and not built on the "
            "percentile instrument: Lima clears 0 of 30 years on both WMO "
            "standard normals in GHCN, so no threshold can be calibrated "
            "here. This is a count against a record, which needs no "
            "baseline. Do not render it inside the city-page template."),
        "city": "Lima",
        "country": "PE",
        "station": "Jorge Chavez International",
        "station_class": "airport",
        "wmo": WMO,
        "ghcn": GHCN_ID,
        "lat": -12.022,
        "lon": -77.114,
        "coord_source": "GHCN",
        "why_not_a_city_page": {
            "baseline_1971_2000_years": 0,
            "baseline_1991_2020_years": 0,
            "consequence": (
                "No percentile thresholds. The European pages count days "
                "above a station's own 90th, 95th and 99th percentile of "
                "1971-2000 or 1991-2020; neither window is complete here, "
                "so those numbers do not exist for Lima and must not be "
                "invented or approximated from a shorter window."),
        },
        "sources": {
            "record": "NOAA GHCN-Daily",
            "current_winter": "WMO synoptic bulletins from the same station",
            "validated": {
                "why": (
                    "The record and the current year come from DIFFERENT "
                    "transports, and this chart's whole claim is 2026 set "
                    "against prior years. If the current year were measured "
                    "differently from the record the comparison would not "
                    "hold, so the two were compared on every year both hold."),
                "2023": {"shared_days": 67, "worst_difference_c": 0.0},
                "2024": {"shared_days": 82, "worst_difference_c": 0.0,
                         "exact_matches": 82},
                "verdict": "same measurement, comparison holds",
                "if_it_had_failed": (
                    "The chart would have been GHCN-only with the current "
                    "year ABSENT rather than approximated. An honest gap "
                    "beats a comparison that does not hold."),
            },
            "construction": (
                "A night's minimum is the lowest value across all of that "
                "date's reports. That is the construction the validation "
                "above was run on; any other choice is unvalidated."),
        },
        "current_winter": {
            "year": CURRENT_YEAR,
            "from": winter[0] if winter else None,
            "to": winter[-1] if winter else None,
            "nights_measured": len(winter),
            "nights_at_or_above_20": len(above),
            "by_month": {m: {"measured": len(v),
                             "at_or_above_20": sum(1 for x in v
                                                   if x >= TROPICAL_NIGHT_C)}
                         for m, v in sorted(months.items())},
            "warmest_night_c": warmest_2026,
            "warmest_night_date": (max(cur_aug, key=cur_aug.get)
                                   if cur_aug else None),
            # THE OCEAN AT THIS AUGUST IS NOT YET PUBLISHED. CPC's ONI runs
            # to MJJ 2026; the JAS and ASO seasons every other year on this
            # chart is labelled by do not exist yet. So the current year gets
            # the latest published season and an explicit statement that it
            # is NOT the same measure as the others, rather than a label
            # borrowed from a different season to make the row look complete.
            "oni_at_august": enso.get(CURRENT_YEAR, {}).get("oni_at_august"),
            "oni_latest_published": _latest_oni(),
            "oni_note": (
                "Every historical August here is labelled by the mean ONI "
                "across JAS and ASO. Those seasons are not published for "
                "2026 yet, so this year carries the latest season CPC has "
                "released and is NOT directly comparable to the labels on "
                "the other rows. It must not be rendered as though it were."),
        },
        "august_record": [
            {"year": y,
             "warmest_night_c": r["warmest_night_c"],
             "nights_measured": r["nights_measured"],
             "nights_at_or_above_20": r["nights_at_or_above_20"],
             "enso": enso.get(y, {}).get("type"),
             "enso_strength": enso.get(y, {}).get("strength"),
             "oni_at_august": enso.get(y, {}).get("oni_at_august")}
            for y, r in sorted(record.items())
        ],
        "what_may_be_said": [
            f"{len(above)} of the last {len(winter)} winter nights at or "
            f"above 20 C, {winter[0]} to {winter[-1]}" if winter else None,
            f"the warmest August night in a record of {len(record)} measured "
            f"Augusts, above {len(beaten)} of them"
            if warmest_2026 is not None else None,
        ],
        "may_not_say": [
            "hottest on record, unqualified: the record here is measured "
            "Augusts in GHCN, not Lima's full observational history",
            "any percentile or anomaly against a 30-year normal: no complete "
            "normal exists for this station",
            "that this is one record night: it is a season, and saying "
            "otherwise repeats the framing our own count contradicts",
        ],
        "enso_note": (
            "Each August is labelled by the ocean AT THAT AUGUST: the mean "
            "CPC ONI across the JAS and ASO seasons, thresholded at CPC's "
            "own plus or minus 0.5. NOT by the calendar year's overall "
            "classification, which files the 1982-83 El Nino under 1982 and "
            "labels 1983 la_nina because La Nina arrived later that year. "
            "August 1983 sat in that event's decay, so the calendar label "
            "would have put a La Nina year among the warmest August nights "
            "on a chart arguing the warmest August nights are El Nino "
            "nights. The label would have contradicted the chart."),
        "enso_2026_note": (
            "2026 is 'undecided, series_incomplete' in our own year-status "
            "file, so this page states the ocean's measured value at August "
            "and does NOT assert an event classification for the year. The "
            "claim that 'this El Nino is in its own league' is not ours."),
    }
    payload["what_may_be_said"] = [x for x in payload["what_may_be_said"] if x]
    OUT.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"  winter {winter[0]} to {winter[-1]}: "
          f"{len(above)} of {len(winter)} nights at or above 20 C")
    print(f"  warmest August night 2026: {warmest_2026} C")
    print(f"  August record spans {len(record)} measured years")
    print("  five warmest Augusts on record:")
    for y, r in ranked[:5]:
        e = enso.get(y, {})
        print(f"    {y}  {r['warmest_night_c']:5.1f} C   "
              f"{e.get('type') or 'neutral':8s} {e.get('strength') or ''}")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
