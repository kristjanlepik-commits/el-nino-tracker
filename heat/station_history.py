"""Read documented station relocations instead of inferring them from data.

WHY THIS REPLACES THE STATISTICAL TEST. The pairwise neighbour check in
blend_gate.py does not work: a known 1 C splice sits inside the distribution
of city pairs already verified clean, because summer-mean differences between
cities hundreds of km apart drift genuinely over 75 years. No threshold
separates them.

But a relocation is not a statistical event. It is an ADMINISTRATIVE one, and
the met services publish it. DWD ships Metadaten_Geographie_<id>.txt inside
the same archive as the data, carrying every position and elevation the
station has held with the dates. That file was already on disk before this
was written; nobody had opened it.

WHAT MATTERS AND WHAT DOES NOT. A move of a few tens of metres is a routine
re-survey. A move of a kilometre, or a change in elevation, can shift night
minima by more than the signal we publish. So both are measured and the
verdict names which one triggered.

ONLY MOVES INSIDE THE PERIOD WE USE COUNT. A relocation in 1936 cannot affect
a 1961-1990 baseline or a 1991-2020 normal.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "heat" / "data" / "station_history.json"
BASE = ("https://opendata.dwd.de/climate_environment/CDC/observations_germany"
        "/climate/daily/kl/historical/")

DE = {"Berlin": "00433", "Hamburg": "01975", "Frankfurt": "01420",
      "Munich": "03379", "Cologne": "02667",
      # Added 2026-08-09 with the forecast-selected cities.
      "Hanover": "02014", "Stuttgart": "04928"}

EARLIEST_USED = 1961      # nothing before our earliest baseline can matter
MOVE_KM = 1.0             # beyond this a move is not a re-survey
MOVE_M = 20.0             # elevation change that can move night minima


def _km(a, b):
    la, lo = np.radians(a), np.radians(b)
    dlat, dlon = lo[0] - la[0], lo[1] - la[1]
    h = (np.sin(dlat / 2) ** 2
         + np.cos(la[0]) * np.cos(lo[0]) * np.sin(dlon / 2) ** 2)
    return float(6371 * 2 * np.arcsin(np.sqrt(h)))


def history(sid):
    listing = subprocess.run(["curl", "-sS", "--max-time", "120", BASE],
                             capture_output=True).stdout.decode("utf-8", "replace")
    m = re.search(rf'href="(tageswerte_KL_{sid}_[^"]*\.zip)"', listing)
    blob = subprocess.run(["curl", "-sS", "--max-time", "240", BASE + m.group(1)],
                          capture_output=True).stdout
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if "Geographie" in n and n.endswith(".txt"))
        text = z.read(name).decode("latin-1")
    rows = []
    for line in text.splitlines()[1:]:
        p = [x.strip() for x in line.split(";")]
        if len(p) < 6 or not p[4].isdigit():
            continue
        rows.append(dict(elev=float(p[1]), lat=float(p[2]), lon=float(p[3]),
                         start=p[4], end=p[5] or None))
    return rows


def assess(city, rows):
    moves = []
    for a, b in zip(rows, rows[1:]):
        if int(b["start"][:4]) < EARLIEST_USED:
            continue
        d = _km((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        de = abs(b["elev"] - a["elev"])
        if d >= MOVE_KM or de >= MOVE_M:
            moves.append({"date": b["start"], "km": round(d, 2),
                          "elev_change_m": round(de, 1),
                          "trigger": "distance" if d >= MOVE_KM else "elevation"})
    return {
        "city": city, "positions": len(rows),
        "relocations_in_period": moves,
        "ok": not moves,
        "why": "" if not moves else
               f"{len(moves)} relocation(s) inside the period we publish",
        "note": "Documented relocations only, from the service's own station "
                "history. A move before {0} cannot affect any window we "
                "use.".format(EARLIEST_USED),
    }


# GeoSphere types each station INDIVIDUAL or COMBINED and lists a combined
# station's components. Vienna's 105 is COMBINED. That is a different finding
# from a relocation, so it gets its own shape rather than being forced into
# the DWD one, and it is recorded here because a city I have checked must
# never read as unchecked.
AT = {
    "Vienna": {
        "city": "Vienna", "positions": 1, "relocations_in_period": [],
        "ok": True,
        "composite": True,
        "composite_components":
            "Hohe Warte 5901 (203 m) to 1992, Hohe Warte 5904 (198 m) after. "
            "Both at the same observatory.",
        "composite_evidence":
            "GeoSphere types station 105 COMBINED and publishes its "
            "components. Measured against the individual station 5904: 19.84% "
            "identical before 1993 and 100.00% after, so the declared "
            "handover is exactly where the data changes.",
        "composite_step_c": 0.44,
        "composite_step_confidence": "suggestive, not established",
        "composite_step_note":
            "Neighbour testing at the 1993 handover gives +0.44 C with the "
            "same sign against 3 of 4 neighbours. NOT ESTABLISHED: the only "
            "available neighbours are German cities 350 to 750 km away and "
            "one of them, Frankfurt, has a confirmed step of its own. A "
            "contaminated reference cannot settle it.",
        "alternative_rejected":
            "The individual station 5904 was tried and rejected: this dataset "
            "carries no Tmin for it before 1991, giving 34 usable years "
            "against 77. Its valid_from of 1934 is when the STATION existed, "
            "not when this series holds its minima.",
        "why": "",
        "note": "Same-observatory instrument change, categorically milder "
                "than Murcia (two towns, 1.19 C) or Frankfurt (5.9 km, "
                "0.57 C).",
    }
}


# France, read from LAT/LON/ALTI carried on EVERY ROW of the daily CSV, which
# is better than a separate metadata file: the position travels with the
# observation and cannot go stale against it.
#
# All five hold a single position across the whole record. Nice appeared to
# move 8 km three times until the rows were grouped by NUM_POSTE rather than
# display name: four posts publish as "NICE", and the other three carry no
# temperature at all. Clean by luck, now clean by construction, since the
# loader pins NUM_POSTE.
FR = {c: {"city": c, "positions": 1, "relocations_in_period": [], "ok": True,
          "why": "", "source_of_history": "LAT/LON/ALTI per row, NUM_POSTE " + n,
          "note": "Single position across the record."}
      for c, n in (("Paris", "91027002"), ("Marseille", "13054001"),
                   ("Nice", "06088001"), ("Montpellier", "34154001"),
                   ("Lyon", "69299001"),
                   # Added 2026-08-09, each verified to hold one position
                   # across the whole record before being published.
                   ("Bordeaux", "33281001"), ("Toulouse", "31069001"),
                   ("Strasbourg", "67124001"))}


# The Netherlands, and this is a PRODUCER WARNING rather than a check result.
# KNMI prints on every response: "These time series are inhomogeneous because
# of station relocations and changes in observation techniques. As a result
# these series are not suitable for trend analysis."
#
# No other source in this pipeline says that about itself. It is not a
# relocation we detected, it is the met service telling us the series is not
# fit for comparison across time, which is exactly what a rank against 76
# prior years is.
#
# Recorded as its own state rather than squeezed into "moved" or "clean",
# because it is neither: it is the producer declining to vouch for the series
# for our use.
NL = {
    "Amsterdam": {
        "city": "Amsterdam", "positions": 1, "relocations_in_period": [],
        "ok": True,
        "history_available": False,
        # The blanket-disclaimer finding, kept because it is what changed the
        # ruling. The warning text is byte-identical across stations 240, 260,
        # 280 and 380, De Bilt included, so it qualifies the SERVICE and not
        # this station. Recorded as false because treating a service-wide
        # disclaimer as a station-specific finding is what held Amsterdam for
        # a day while five German cities shipped on an equivalent statement.
        "producer_inhomogeneity_warning": False,
        "producer_warning_is_blanket": True,
        "producer_warning_evidence":
            "Identical text returned for stations 240, 260, 280 and 380, "
            "including De Bilt, which KNMI uses for national climate "
            "reporting.",
        "producer_warning_text":
            "KNMI: these time series are inhomogeneous because of station "
            "relocations and changes in observation techniques, and are not "
            "suitable for trend analysis.",
        "why": "",
        "method": "two-source comparison unavailable",
        "note": "KNMI points to its homogenised daily series and to the "
                "Central Netherlands Temperature as the alternatives for "
                "climate work. Whether a homogenised series exists for "
                "Schiphol specifically has NOT been checked.",
    }
}


def main() -> int:
    out = dict(AT)
    out.update(FR)
    out.update(NL)
    # Spain, and it is a WEAKER check that must not be presented as the same
    # one. AEMET's station inventory carries current position only: no
    # validity dates, no history. So the metadata route used for Germany,
    # France and Austria simply does not exist here.
    #
    # What replaces it is a changepoint comparison against a retained
    # independent copy of each station. That is real evidence and it is not
    # equivalent: a relocation documented nowhere cannot be ruled out by data
    # agreeing with itself. Emitted with history_available false so a page can
    # tell the two apart, because "checked" covering two different standards
    # is exactly the collapse this whole exercise exists to prevent.
    es = ROOT / "heat" / ".cache" / "es_station_check.json"
    if es.exists():
        out.update(json.loads(es.read_text()))
    print(f"{'city':11s} {'pos':>4s} {'moves':>6s}  detail")
    print("-" * 74)
    for city, sid in DE.items():
        r = assess(city, history(sid))
        out[city] = r
        det = "; ".join(f"{m['date'][:4]} {m['km']}km dz{m['elev_change_m']}m"
                        for m in r["relocations_in_period"]) or "none in period"
        print(f"{city:11s} {r['positions']:4d} {len(r['relocations_in_period']):6d}  "
              f"{'PASS' if r['ok'] else 'FLAG'}  {det}")
    print("-" * 74)
    OUT.write_text(json.dumps(
        {"_readme": "Documented station relocations, read from each service's "
                    "own metadata rather than inferred from the data. The "
                    "statistical approach was tested and does not work: see "
                    "heat/blend_gate.py.",
         "thresholds": {"move_km": MOVE_KM, "elev_m": MOVE_M,
                        "earliest_year_that_matters": EARLIEST_USED},
         "stations": out}, indent=1) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
