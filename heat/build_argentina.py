"""Assemble the Argentine cities: GHCN history bridged with WMO bulletins.

SAME CONSTRUCTION AS LARNACA, and the same validation. What differs is the
season: these stations peak in December and January, so the bridge's
May-to-August fetch would have collected their winter. Whole years are
fetched instead and the season is derived downstream, which is why the
derivation had to land before this could.

IDENTITY AND DATE OFFSET BOTH COME FROM heat/data/latam_gather.json, where
each block was proven against its own station's GHCN archive rather than
parsed from an id. AR000870470 is block 87047 and AR000875850 is 87585: two
padding conventions in one country, and a wrong block returns another
station's perfectly valid data.

THE DATE SHIFT IS NOT COSMETIC. These stations bulletin their maximum at 00Z,
which is 21:00 the previous evening in Argentina, so the report stamped the
15th carries the 14th's local maximum. Compared same-date the archive and the
bulletins look like different stations, at p90 5.5 to 7.8 C. Shifted one day
they are the same thermometer, 319 of 360 days exact on Mendoza.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))
import gather_latam as G  # noqa: E402

SRC = ROOT / "heat" / ".cache" / "src"
GATHER = ROOT / "heat" / "data" / "latam_gather.json"

# The six with a complete 30/30 baseline. Trelew is proven but sits at 29/30
# and is held pending the shortfall test; Tlaxcala is proven, Mexican, and
# held on its own questions. Named here rather than filtered silently, so the
# set is a decision someone made rather than whatever passed a threshold.
CITIES = {
    "Santiago del Estero": "AR000087129",
    "Parana": "AR000087374",
    "Laboulaye": "AR000087534",
    "Mar del Plata": "AR000087692",
    "Neuquen": "AR000087715",
    "Salta": "AR000870470",
    # Trelew is proven and sits at 29/30. Built so the shortfall test can be
    # run against real data rather than estimated from the gather summary.
    "Trelew": "AR000087828",
}
FIRST_BRIDGE_YEAR = 2003        # where these archives thin, not where they end


def build(city, ghcn_id, meta):
    rows = {}
    for d, e in G.ghcn_days(ghcn_id).items():
        rows[d] = (e.get("TMIN"), e.get("TMAX"))

    block, shift = meta["wmo_block"], meta["date_shift"]
    # The archive's own maximum bounds what its bulletins may claim.
    ceiling = G.station_ceiling(G.ghcn_days(ghcn_id))
    last_ghcn = max(int(d[:4]) for d in rows)
    added = 0
    for year in range(FIRST_BRIDGE_YEAR, 2027):
        raw = G.fetch_year(block, year)
        if raw.count("AAXX") < 20:
            continue
        for d, (mn, mx) in G.daily(raw, ceiling).items():
            # Attribute to the LOCAL day, using the offset proven per station.
            k = (dt.date.fromisoformat(d) + dt.timedelta(days=shift)).isoformat()
            omn, omx = rows.get(k, (None, None))
            # The archive wins where it exists; bulletins fill gaps only.
            new = (omn if omn is not None else mn,
                   omx if omx is not None else mx)
            if new != (omn, omx):
                added += 1
            rows[k] = new

    out = [[d, mn, mx] for d, (mn, mx) in sorted(rows.items())]
    path = SRC / f"{city.lower().replace(' ', '_')}.json"
    path.write_text(json.dumps(out))
    per = {}
    for d, mn, mx in out:
        if mn is not None and mx is not None:
            per[int(d[:4])] = per.get(int(d[:4]), 0) + 1
    return path, len(out), last_ghcn, added, per


def main() -> int:
    gather = {r["station"]: r
              for r in json.loads(GATHER.read_text())["stations"]}
    for city, gid in CITIES.items():
        meta = gather.get(gid)
        if not meta or not meta.get("wmo_block"):
            print(f"  {city}: NO PROVEN BLOCK, skipped", file=sys.stderr)
            continue
        path, n, last, added, per = build(city, gid, meta)
        recent = [y for y in range(2017, 2027) if per.get(y, 0) >= 200]
        print(f"  {city:22s} {n:6d} rows, GHCN to {last}, "
              f"{added:5d} bulletin days added, recent {len(recent)}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
