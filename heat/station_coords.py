"""Resolve each city's mark to the coordinates of its actual station.

WHY THIS EXISTS. `emit_city_nights.COORDS` was 36 pairs I typed by hand to one
decimal place, with no source. Platform found the payload and design's own
`city_coords.json` disagreeing, and proposed emitting 2 dp so the two would
dedupe. Formatting an unsourced number to more places would have made it look
more precise while staying just as wrong, so this resolves them instead.

Measured against the DWD station list, the hand-typed values are off by 3 to
15 km. Frankfurt is the worst at 15.2 km, because I typed the city centre and
the station is the airport. That is not a rounding error; it is marking a
different place from the one the page names in its station disclosure.

THE MARK IS THE STATION, NOT THE CITY. Every number on a city page comes from
one thermometer, the disclosure names it, and the completeness bar is measured
on it. So the point on the map is where that instrument is. A city centroid
would be a fourth thing, agreeing with neither the data nor the disclosure.

PROVENANCE IS A FIELD, NOT A README LINE (D-051). Each entry carries
`coord_source`, so a city still on a hand-typed value is visibly so in the
payload rather than silently mixed in with the resolved ones. Nine of
thirty-six are resolved as this lands; the rest are marked `hand_typed` and
are not quietly presented as sourced.

Services are checked one at a time because each publishes its station list in
its own shape, exactly as the fetchers do. Add one, run it, commit it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DWD_STATIONS = ("https://opendata.dwd.de/climate_environment/CDC/observations_"
                "germany/climate/daily/kl/historical/"
                "KL_Tageswerte_Beschreibung_Stationen.txt")


def _dwd():
    """DWD publishes a fixed-column station list; columns 5 and 6 are lat/lon.

    Station ids are zero-padded in filenames and unpadded here, the same
    asymmetry fetch_dwd already handles.
    """
    from fetch_dwd import CITIES
    want = {sid.lstrip("0"): c for c, (sid, _) in CITIES.items()}
    raw = subprocess.run(["curl", "-sS", "--max-time", "120", DWD_STATIONS],
                         capture_output=True).stdout.decode("latin-1", "replace")
    out = {}
    for line in raw.splitlines():
        p = line.split()
        if len(p) < 7 or not p[0].isdigit():
            continue
        sid = p[0].lstrip("0")
        if sid not in want:
            continue
        try:
            out[want[sid]] = (float(p[4]), float(p[5]))
        except ValueError:
            continue
    return out


# Each entry becomes one service resolver. Unresolved cities keep their
# hand-typed value AND say so in the payload, rather than disappearing or
# being presented as sourced.
def _met_office():
    """Heathrow, verified rather than resolved from a list.

    MIDAS station metadata gives 51.479,-0.453 and OSCAR/Surface gives
    51-28-45N 000-27-02W for WMO 03772. They agree to three decimals, and
    that agreement is what established that the MIDAS history and the SYNOP
    season are one thermometer rather than two.
    """
    return {"London": (51.479, -0.451),
            # From the Met Office workbook headers, matching both the MIDAS
            # records and the SYNOP stations to four decimals.
            "Nottingham": (53.00528, -1.24969),
            "Belfast": (54.66357, -6.22436),
            "Aberdeen": (57.20506, -2.20370)}


def _meteofrance():
    """Coordinates from the station's OWN rows in the archive we read.

    The QUOT files carry LAT and LON per NUM_POSTE, so this reads the mark
    out of the same rows the temperatures come from. That makes a coordinate
    and a reading incapable of describing different places, which is the
    failure hand-typing produced: Frankfurt 15 km out because I typed the
    city and the station is the airport.
    """
    import csv as _csv, gzip as _gzip
    from build_city_series import MF_POSTE, SRC as _SRC
    out = {}
    for city, poste in MF_POSTE.items():
        f = _SRC / f"mf_{city}_recent.csv.gz"
        if not f.exists():
            continue
        with _gzip.open(f, "rt", encoding="latin-1") as fh:
            for r in _csv.DictReader(fh, delimiter=";"):
                if (r.get("NUM_POSTE") or "").strip() != str(poste):
                    continue
                try:
                    out[city] = (float(r["LAT"]), float(r["LON"]))
                except (KeyError, ValueError):
                    pass
                break
    return out


def _aemet():
    """AEMET's own station inventory, keyed by the VERIFIED station ids.

    Keyed on ES_STATION_ID rather than on the station name. The name is what
    put an air base's history under Murcia's, and the ids in that table were
    each checked against our cached series before being trusted.
    """
    import json as _json
    import fetch_aemet as A
    from build_city_series import ES_STATION_ID
    key = A._key()
    meta = _json.loads(A._get(
        "https://opendata.aemet.es/opendata/api/valores/climatologicos/"
        f"inventarioestaciones/todasestaciones/?api_key={key}"))
    inv = {r["indicativo"]: r for r in _json.loads(A._get(meta["datos"]))}

    def dms(v):
        # AEMET writes 404924N, degrees minutes seconds then a hemisphere.
        h = v[-1]
        d, m, sec = int(v[0:2]), int(v[2:4]), int(v[4:6])
        val = d + m / 60 + sec / 3600
        return -val if h in ("S", "W") else val
    out = {}
    for city, sid in ES_STATION_ID.items():
        r = inv.get(sid)
        if not r:
            continue
        try:
            out[city] = (round(dms(r["latitud"]), 4), round(dms(r["longitud"]), 4))
        except Exception:
            continue
    return out


def _ghcn():
    """Larnaca and Tallinn, from the GHCN station list they are built from.

    Both cities read GHCN for their history, so this takes the mark from the
    same inventory as the data rather than from a second source that could
    disagree with it.
    """
    ids = {"Larnaca": "CY000176090", "Tallinn": "EN000026038"}
    raw = subprocess.run(
        ["curl", "-sS", "--max-time", "180",
         "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"],
        capture_output=True).stdout.decode("utf-8", "replace")
    want = {v: k for k, v in ids.items()}
    out = {}
    for line in raw.splitlines():
        sid = line[:11]
        if sid in want:
            try:
                out[want[sid]] = (float(line[12:20]), float(line[21:30]))
            except ValueError:
                continue
    return out


RESOLVERS = {
    "DWD": _dwd,
    "MIDAS/OSCAR": _met_office,
    "Meteo-France": _meteofrance,
    "AEMET": _aemet,
    "GHCN": _ghcn,
}

# STILL HAND-TYPED, listed rather than left implicit. Each needs its service's
# station list, the same one-service-at-a-time pattern the fetchers use:
#   AEMET (11)        Seville Malaga Murcia Alicante Valencia Palma Madrid
#                     Barcelona Zaragoza Bilbao, plus MurciaCity
#   Meteo-France (8)  Paris Nice Marseille Montpellier Lyon Bordeaux
#                     Toulouse Strasbourg. Pin by NUM_POSTE, never by name:
#                     four postes share the display name NICE.
#   MeteoSwiss (4)    Zurich Geneva Basel Lugano
#   GeoSphere (1)     Vienna.  KNMI (1) Amsterdam.  SMHI (1) Stockholm.
#   CHMI (1)          Prague.  FMI (1) Helsinki.


def resolve():
    """Return {city: (lat, lon, source)} for every city we can resolve."""
    out = {}
    for name, fn in RESOLVERS.items():
        try:
            for city, (lat, lon) in fn().items():
                out[city] = (lat, lon, name)
        except Exception as exc:
            # A failed resolver must not silently downgrade cities to
            # hand-typed without saying so, which is why this prints.
            print(f"  {name}: resolver failed, {exc}", file=sys.stderr)
    return out


def main() -> int:
    import json
    got = resolve()
    from emit_city_nights import COORDS
    rows = {}
    for city, (hl, hn) in COORDS.items():
        if city in got:
            lat, lon, src = got[city]
            rows[city] = {"lat": round(lat, 4), "lon": round(lon, 4),
                          "coord_source": src}
        else:
            rows[city] = {"lat": hl, "lon": hn, "coord_source": "hand_typed"}
    path = ROOT / "heat" / "data" / "station_coords.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    n = sum(1 for r in rows.values() if r["coord_source"] != "hand_typed")
    print(f"  resolved {n} of {len(rows)}; "
          f"{len(rows) - n} still hand-typed and marked as such")
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
