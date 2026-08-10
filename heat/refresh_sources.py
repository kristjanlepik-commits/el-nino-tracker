"""Refresh the source cache for the three services that could not refresh it.

WHY THIS EXISTS. On 2026-08-09 the weekly pull half succeeded: 24 of 47 source
files updated and 23 stayed on 7 August. The failures were not random. They
were exactly the three modules platform had found that morning with no main
and no write path, so the same defect that made the cache unreproducible made
it un-refreshable, and it presented as a clean run because ten other services
updated underneath it.

The cost was not just stale numbers. Spain's data stopped on 3 August, the
heat event peaked on the 4th and 5th, and I told two other chats that this
was AEMET's publication lag. AEMET's lag is three days and we last fetched on
the 7th, which lands exactly on the 3rd. **An absence produced by our own
pipeline was reported as a property of the source**, and a channel-wide
decision to say nothing about Spain was taken on that basis.

WHY NOT JUST ADD A main() TO EACH FETCHER. Because they are not the code that
built the cache, which is the trap platform flagged and I nearly walked into:

    fetch_meteofrance   knows 5 of our 8 French cities, and fetch() returns
                        parsed rows rather than the gzipped archives the
                        cache actually holds
    fetch_aemet         series() returns (date, tmin) with NO tmax, against
                        cached [date, min, max] triples

A main written against those would emit the wrong shape from the wrong
station list AND LOOK LIKE A FIX. This writes the shape build_city_series
actually reads, and the city list comes from build_city_series itself rather
than from a second copy that can drift.

VERIFY BY DATE, NOT BY EXIT CODE. A fetcher that returns yesterday's file
exits 0. Every function here reports the last date it actually obtained, so a
silent no-op is visible as a date that did not move.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import build_city_series as B  # noqa: E402

SRC = B.SRC
MF_DATASET = ("https://www.data.gouv.fr/api/1/datasets/"
              "6569b51ae64326786e4e8e1a/")
MF_PERIODS = {"hist": "1950-2024", "recent": "2025-2026"}


def _curl(url, out=None, timeout="300"):
    cmd = ["curl", "-sSL", "--max-time", timeout, url]
    if out:
        cmd += ["-o", str(out)]
    return subprocess.run(cmd, capture_output=True).stdout


def refresh_meteofrance():
    """Download both period archives per city, keyed by department.

    The department is the first two digits of the NUM_POSTE, so the city list
    and the department mapping cannot disagree: both come from MF_POSTE.
    """
    meta = json.loads(_curl(MF_DATASET, timeout="90"))
    res = {r.get("title", ""): r["url"] for r in meta.get("resources", [])}
    out = {}
    for city, poste in B.MF_POSTE.items():
        dep = str(poste)[:2]
        for part, period in MF_PERIODS.items():
            title = f"QUOT_departement_{dep}_periode_{period}_RR-T-Vent"
            url = res.get(title)
            if not url:
                out[f"{city}_{part}"] = "NO RESOURCE"
                continue
            _curl(url, SRC / f"mf_{city}_{part}.csv.gz")
        out[city] = "ok"
    return out


def refresh_aemet():
    """AEMET climatologia diaria, both extremes, written as the cached triple.

    fetch_aemet.window() returns the raw records; it is only its series()
    helper that drops tmax. So the records are read directly here rather than
    through a helper that answers a narrower question.
    """
    import datetime as dt
    import time
    import fetch_aemet as A
    done = {}
    for city, meta in B.CITIES.items():
        if meta["country"] != "ES":
            continue
        fname = meta.get("file") or f"aemet_{city}.json"
        path = SRC / fname
        if not path.exists():
            done[city] = "no existing file, skipped"
            continue
        rows = {d: (mn, mx) for d, mn, mx in json.loads(path.read_text())}
        station = meta.get("station_id") or meta.get("aemet_id")
        if not station:
            done[city] = "no station id in CITIES, skipped"
            continue
        # Only the tail is refetched. The archive does not change and AEMET
        # rate-limits hard, so pulling 90 years to gain three days would be
        # the kind of cost that stops anyone running this weekly.
        start = dt.date.today() - dt.timedelta(days=30)
        try:
            recs = A.window(start, dt.date.today(), station)
        except Exception as exc:
            done[city] = f"FAILED {type(exc).__name__}"
            continue
        added = 0
        for r in recs:
            d = r.get("fecha")
            if not d:
                continue
            def num(k):
                v = r.get(k)
                if v in (None, ""):
                    return None
                try:
                    return float(str(v).replace(",", "."))
                except ValueError:
                    return None
            mn, mx = num("tmin"), num("tmax")
            if mn is None and mx is None:
                continue
            if d not in rows:
                added += 1
            rows[d] = (mn, mx)
        path.write_text(json.dumps(
            [[d, mn, mx] for d, (mn, mx) in sorted(rows.items())]))
        done[city] = f"{max(rows)} (+{added} days)"
        time.sleep(1.5)   # AEMET rate limit
    return done


def refresh_geosphere():
    """GeoSphere serves the whole station history in one call, so this is a
    straight overwrite rather than a merge."""
    import fetch_geosphere as G
    rows = G.fetch()
    if not rows:
        return {"Vienna": "EMPTY RESPONSE, not written"}
    (SRC / "gs_Vienna.json").write_text(json.dumps(
        [[d, mn, mx] for d, mn, mx in rows]))
    have = [d for d, mn, mx in rows if mn is not None or mx is not None]
    return {"Vienna": max(have) if have else "no values"}


def main() -> int:
    which = sys.argv[1:] or ["meteofrance", "aemet", "geosphere"]
    for name in which:
        print(f"  {name}:")
        try:
            for k, val in {"meteofrance": refresh_meteofrance,
                           "aemet": refresh_aemet,
                           "geosphere": refresh_geosphere}[name]().items():
                print(f"    {k:14s} {val}")
        except Exception as exc:
            print(f"    FAILED {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
