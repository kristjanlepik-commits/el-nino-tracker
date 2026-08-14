"""Assemble London's daily series from the MIDAS baseline and the 2026 season.

WHY A SEPARATE BUILDER. Every other city has one service supplying both its
history and its current year. London does not: MIDAS Open publishes annually
in arrears and stops at 2025, so the current season has to come from the
SYNOP bulletins the same station transmits. This writes both into the ordinary
[date, tmin, tmax] cache file, so London enters build_city_series as a normal
city and the eventual source swap is a regeneration of one file rather than a
change anywhere downstream.

THE JOIN IS LEGAL AND THAT WAS MEASURED, NOT ASSUMED. Both halves are the same
thermometer, Heathrow:

    MIDAS   observation_station heathrow, midas_station_id 00708, 51.479,-0.453
    SYNOP   WMO 03772 London/Heathrow Airport, 51.479,-0.451

and both are the same 12-hour climatological day. Validated against MIDAS on
two independent years, 2024 and 2025:

    Tmin @ 06Z   100% of days within 0.5 C, bias +0.01, worst 0.5
    Tmax @ 18Z   100% of days within 0.5 C, bias +0.00, worst 0.1

So this is not the cross-instrument join that produced the Murcia error. It is
one instrument reaching us by two transports.

WHY 06Z AND 18Z rather than the 09Z/21Z pair that matches MIDAS more tightly:
the main synoptic hours are the ones the WMO Unified Data Policy attaches core
status to, and they cost nothing here. Same coverage, same headline figures.

PROVENANCE IS A FIELD, NOT A COMMENT. Every day carries which transport it
came from, so a page can disclose that the 2026 season is bulletin-sourced and
provisional while the history is MIDAS under the Open Government Licence. When
the Met Office Library file arrives, rerun with --official and the season is
replaced in place; nothing downstream needs to know.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import synop  # noqa: E402

SRC = ROOT / "heat" / ".cache" / "src"
MIDAS = SRC / "midas_London"
OUT = SRC / "london.json"
PROV = ROOT / "heat" / "data" / "london_provenance.json"

WMO = "03772"
OGIMET = "https://www.ogimet.com/cgi-bin/getsynop"


def from_midas():
    """09h minimum and 21h maximum, the climatological day, per calendar date.

    Derived rather than assumed: against GHCN over 11,000 shared days the
    same-calendar-day reading scores 66% and the shifted alternative 2%.
    """
    out = {}
    for path in sorted(MIDAS.glob("*.csv")):
        txt = path.read_text(encoding="latin-1")
        if "\ndata\n" not in txt:
            continue
        for r in csv.DictReader(io.StringIO(txt.split("\ndata\n", 1)[1])):
            t = (r.get("ob_end_time") or "").strip()
            if len(t) < 13 or (r.get("ob_hour_count") or "").strip() != "12":
                continue
            d, hh = t[:10], t[11:13]

            def f(k):
                v = (r.get(k) or "").strip()
                try:
                    return float(v)
                except ValueError:
                    return None
            mn, mx = out.get(d, (None, None))
            if hh == "09" and f("min_air_temp") is not None:
                mn = f("min_air_temp")
            if hh == "21" and f("max_air_temp") is not None:
                mx = f("max_air_temp")
            out[d] = (mn, mx)
    return out


def from_synop(begin, end):
    """06Z minimum and 18Z maximum from the station's own bulletins."""
    raw = subprocess.run(
        ["curl", "-sS", "--max-time", "250",
         f"{OGIMET}?block={WMO}&begin={begin}&end={end}"],
        capture_output=True).stdout.decode("utf-8", "replace")
    out = {}
    for d, h, tx, tn in synop.parse_ogimet(raw):
        mn, mx = out.get(d, (None, None))
        if h == "06" and tn is not None:
            mn = tn
        if h == "18" and tx is not None:
            mx = tx
        out[d] = (mn, mx)
    return out


OFFICIAL = ROOT / "heat" / "data" / "official" / "Heathrow_Jan_2026-Present.xlsx"


def from_official():
    """The Met Office's own daily maxima and minima, when they have sent them.

    THIS IS THE SOURCE, and the SYNOP season is the fallback. It arrived
    2026-08-11 from the Met Office National Meteorological Library and
    Archive, covering 1 January to 9 August 2026, with the station stated as
    HEATHROW at 51.47895, -0.45158, which matches MIDAS to four decimals.

    It also settles the licence. The workbook's INFO sheet states the data
    is provided under the Met Office's re-use obligations and that re-use in
    a product requires acknowledgement of the source under Crown Copyright.
    That is permission with a condition, not silence.

    ONE CAVEAT THAT DID NOT EXIST BEFORE: the same sheet says values are
    subject to QC changes for up to twelve months from capture. So these
    numbers can move, and a page quoting them is quoting a figure that may
    be revised. That is a better problem than an unlicensed one and it is
    still a real one.
    """
    if not OFFICIAL.exists():
        return {}
    import datetime as _dt
    import openpyxl
    ws = openpyxl.load_workbook(OFFICIAL, data_only=True)["HEATHROW_DAILY"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and r[0] == "Date and time")
    out = {}
    for r in rows[hdr + 1:]:
        if not r or r[0] in (None, ""):
            continue
        d = r[0]
        if isinstance(d, _dt.datetime):
            key = d.strftime("%Y-%m-%d")
        else:
            s = str(d).strip().split()[-1]
            try:
                dd, mm, yy = s.split("/")
            except ValueError:
                continue
            key = f"{yy}-{mm}-{dd}"
        try:
            out[key] = (float(r[2]), float(r[1]))
        except (TypeError, ValueError):
            continue
    return out


def main() -> int:
    hist = from_midas()
    if not hist:
        print("  no MIDAS baseline found; expected heat/.cache/src/midas_London",
              file=sys.stderr)
        return 1
    cur = {}
    official = from_official()
    if official:
        cur = dict(official)
        season_source = "official"
        # EXTEND WITH BULLETINS PAST THE WORKBOOK'S LAST DAY, rather than
        # stopping there. The workbook is sent by hand and reached 10 August
        # while Heathrow was recording 34.0 C on the 12th and 37.7 C on the
        # 13th. A page that stops four days short during the days people are
        # actually looking is a worse artifact than one that says which days
        # came by which transport.
        #
        # THIS IS ONLY LEGAL BECAUSE THE TWO AGREE. The bulletins reproduce
        # the official series on their overlap, which is the same test that
        # made London publishable and the same one that would have caught
        # Murcia. It is re-run below on every build rather than remembered:
        # if they ever diverge, the extension is dropped and the page stops
        # at the workbook, because a disagreement means one of them is wrong
        # and we do not know which.
        last = max(official)
        y, m, d = (int(x) for x in last.split("-"))
        tail = from_synop(f"{y}{m:02d}010000", f"{y}1231 2359".replace(" ", ""))
        overlap = [k for k in tail if k in official
                   and official[k][1] is not None and tail[k][1] is not None]
        worst = max((abs(tail[k][1] - official[k][1]) for k in overlap),
                    default=None)
        agree = len(overlap) >= 5 and worst is not None and worst <= 0.5
        added = []
        if agree:
            for k, v in sorted(tail.items()):
                if k > last and v[0] is not None and v[1] is not None:
                    cur[k] = v
                    added.append(k)
        season_provenance = {
            "official_to": last,
            "synop_days": added,
            "overlap_days": len(overlap),
            "overlap_worst_c": None if worst is None else round(worst, 1),
            "agree": agree,
            "note": ("Days after the workbook come from the station's own WMO "
                     "bulletins, checked against the official series where "
                     "they overlap. Not applied when they disagree."),
        }
        print(f"  official to {last}; bulletins agree on {len(overlap)} days "
              f"(worst {worst} C); extended by {len(added)}: {added}")
    else:
        season_provenance = {"official_to": None, "synop_days": [],
                             "agree": None, "note": "No workbook; season is "
                             "entirely bulletin-sourced."}
        for a, b in (("202605010000", "202605312359"),
                     ("202606010000", "202607312359"),
                     ("202608010000", "202608312359")):
            cur.update(from_synop(a, b))
        season_source = "synop"
    # 2026 never overwrites history and history never reaches 2026, so the
    # provenance of any given day is unambiguous by construction.
    merged = dict(hist)
    merged.update({d: v for d, v in cur.items() if d.startswith("2026")})
    rows = [[d, mn, mx] for d, (mn, mx) in sorted(merged.items())]
    OUT.write_text(json.dumps(rows))

    days26 = [d for d, mn, mx in rows
              if d.startswith("2026") and mn is not None and mx is not None]
    PROV.parent.mkdir(parents=True, exist_ok=True)
    PROV.write_text(json.dumps({
        "station": "Heathrow, WMO 03772, MIDAS 00708",
        "history": {
            "source": "Met Office MIDAS Open",
            "licence": "Open Government Licence, commercial reuse permitted",
            "from": min(hist), "to": max(hist),
            "convention": "09h minimum and 21h maximum, climatological day",
        },
        "current_season": {
            "source": ("Met Office National Meteorological Library and "
                       "Archive, daily maxima and minima"
                       if season_source == "official" else
                       "Met Office observations, SYNOP bulletins"),
            "transport": ("supplied directly by the Met Office"
                          if season_source == "official" else
                          "OGIMET, a one-time archival pull"),
            "licence_status": ("Crown Copyright. Provided under the Met "
                               "Office's re-use obligations; re-use in a "
                               "product requires acknowledgement of the "
                               "source. RESOLVED."
                               if season_source == "official" else
                               "UNRESOLVED, asked of the Met Office"),
            "provisional": season_source != "official",
            "subject_to_qc_revision": (
                "Met Office state values may change under quality control "
                "for up to twelve months from capture."
                if season_source == "official" else None),
            "hours": "06Z minimum, 18Z maximum",
            "validated": "against MIDAS 2024 and 2025, 100% of days within "
                         "0.5 C, worst 0.1 on maxima",
            "days_with_both": len(days26),
            "first": min(days26) if days26 else None,
            "last": max(days26) if days26 else None,
        },
        "same_thermometer": True,
        "why_not_a_splice": "one instrument, two transports, same 12-hour "
                            "climatological day. Not the cross-instrument "
                            "join that produced the Murcia error.",
    }, indent=1) + "\n")
    print(f"  wrote {OUT.relative_to(ROOT)}  {len(rows)} days, "
          f"{min(merged)} to {max(merged)}")
    print(f"  2026 days with both extremes: {len(days26)}"
          + (f", {min(days26)} to {max(days26)}" if days26 else ""))
    print(f"  wrote {PROV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
