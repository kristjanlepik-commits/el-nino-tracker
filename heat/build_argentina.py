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
from safe_write import RefusedWrite, write_series
import builder_status as ST  # noqa: E402  # noqa: E402
# WRITES TO heat/data/sources/, NOT the cache. See source_file() in
# build_city_series: this file is expensive to regenerate and is tracked.
import build_city_series as _B  # noqa: E402


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
CURRENT_YEAR = dt.date.today().year
FIRST_BRIDGE_YEAR = 2003        # where these archives thin, not where they end


def build(city, ghcn_id, meta, full=False):
    """Bridge the archive with the station's own bulletins.

    SAME REDUCTION AS build_bridge AND FOR THE SAME REASON. This walked every
    year from FIRST_BRIDGE_YEAR to now on every run, re-fetching bulletins to
    fill gaps the archive leaves, while the bridged result was already
    committed in heat/data/sources/<city>.json. On a cold runner that is 24
    years times seven cities of pulls reconstructing rows the checkout already
    held, and on 2026-09-07 it was roughly half of an 83 minute builder step
    that a 90 minute ceiling then cancelled.

    Order is the correctness, exactly as in build_bridge: the fresh archive
    wins, the tracked series fills gaps in PAST years only, fresh bulletins
    fill what is left in the current year. The current year is deliberately
    not seeded from the tracked copy, which is last run's bulletins, because
    letting it fill a gap first would freeze a value the fresh pull would
    have corrected.

    `full` walks every year and is the audit path; a city with no tracked
    series gets it automatically, which is what a newly added city needs.
    """
    rows = {}
    for d, e in G.ghcn_days(ghcn_id).items():
        rows[d] = (e.get("TMIN"), e.get("TMAX"))

    tracked = {}
    if not full:
        _p = _B.source_file(f"{city.lower().replace(' ', '_')}.json")
        if _p.exists():
            tracked = {d: (mn, mx) for d, mn, mx in json.loads(_p.read_text())}
    for d, (mn, mx) in tracked.items():
        # DO NOT DELETE THIS SKIP. It looks like an oversight in a loop whose
        # job is filling gaps, and removing it reintroduces the bug this whole
        # change exists to avoid. The tracked series holds LAST RUN'S bulletins
        # for the current year. Let them fill a current-year gap here and they
        # win over the fresh pull that follows, so a value freezes at whatever
        # was first fetched and every later run confirms it. That is exactly
        # how Rome sat at 2026-08-14 for three and a half weeks while every
        # build reported success, and it would be that bug reintroduced
        # through the fix for it.
        #
        # Past years are safe to seed precisely because they are finished:
        # their bulletins cannot change, which is the property the whole
        # reduction rests on.
        if int(d[:4]) == CURRENT_YEAR:
            continue
        omn, omx = rows.get(d, (None, None))
        rows[d] = (omn if omn is not None else mn,
                   omx if omx is not None else mx)

    block, shift = meta["wmo_block"], meta["date_shift"]
    # The archive's own maximum bounds what its bulletins may claim.
    ceiling = G.station_ceiling(G.ghcn_days(ghcn_id))
    last_ghcn = max(int(d[:4]) for d in rows)
    added = 0
    years = (range(FIRST_BRIDGE_YEAR, CURRENT_YEAR + 1)
             if full or not tracked else [CURRENT_YEAR])
    for year in years:
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
    path = _B.source_file(f"{city.lower().replace(' ', '_')}.json")
    # GUARDED for the same reason as build_london: this now runs weekly in CI
    # against a tracked file, and these cities are assembled from GHCN plus
    # per-year SYNOP fetches, so a partial bulletin response shrinks the
    # series without failing. Unguarded, that shrink would be committed.
    write_series(path, out, label=city)
    per = {}
    for d, mn, mx in out:
        if mn is not None and mx is not None:
            per[int(d[:4])] = per.get(int(d[:4]), 0) + 1
    return path, len(out), last_ghcn, added, per


def main() -> int:
    full = "--full" in sys.argv[1:]
    if full:
        print("  --full: walking every year. Audit path, not the weekly one.")
    gather = {r["station"]: r
              for r in json.loads(GATHER.read_text())["stations"]}
    # ONE CITY'S FAILURE MUST NOT COST THE OTHERS. This loop is now run
    # weekly in CI (platform, d0475cbc), and an exception here would skip
    # every city after it while the payload still built from their stale
    # tracked files: a silent partial refresh, which is the exact failure the
    # isolated fetch loop one level up exists to prevent. Named loudly and
    # counted; a non-zero exit so the step reports it rather than passing.
    failed = []
    held = []
    ST.open_status("build_argentina", list(CITIES))
    for city, gid in CITIES.items():
        meta = gather.get(gid)
        if not meta or not meta.get("wmo_block"):
            print(f"  {city}: NO PROVEN BLOCK, skipped", file=sys.stderr)
            continue
        try:
            path, n, last, added, per = build(city, gid, meta, full=full)
        except RefusedWrite as exc:
            # A REFUSED WRITE IS THE GUARD WORKING, NOT THE BUILDER FAILING,
            # and conflating them cost a whole step on 2026-09-07. Budapest
            # refused to shrink by ONE row in 18380, safe_write kept the good
            # file exactly as designed, and my exit code reported the builder
            # as failed. Platform's step then counted it among "4 of 4
            # builders failed" and errored the job, on a run where five of six
            # bridge cities had refreshed correctly.
            #
            # This is platform's own rule about the refresh gate, one level
            # down: a hold is the guard working, and turning it red trains
            # everyone to ignore red. Held cities keep their previous series
            # and are named; only an unexpected exception is a failure.
            held.append(city)
            ST.set_status("build_argentina", city, "held", str(exc)[:200])
            print(f"  {city}: HELD by the write guard, previous series kept. "
                  f"{exc}", file=sys.stderr)
            continue
        except Exception as exc:
            failed.append(city)
            ST.set_status("build_argentina", city, "failed",
                          f"{type(exc).__name__}: {exc}"[:200])
            print(f"  {city:22s} FAILED {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        # ALWAYS `checked` RATHER THAN `unchanged`, because G.fetch_year has
        # no cache: this builder cannot complete without going to the source
        # for the current year. If that ever gains a cache, this line has to
        # learn the difference the way build_bridge did, or it becomes the
        # silence that hid Rome.
        ST.set_status("build_argentina", city,
                      "advanced" if added else "checked",
                      f"{n} rows, {added} bulletin days added")
        recent = [y for y in range(2017, 2027) if per.get(y, 0) >= 200]
        print(f"  {city:22s} {n:6d} rows, GHCN to {last}, "
              f"{added:5d} bulletin days added, recent {len(recent)}/10")
    if held:
        print(f"\n  {len(held)} city/cities HELD by the write guard and kept "
              f"their previous series: {', '.join(held)}. Not a failure.",
              file=sys.stderr)
    if failed:
        print(f"\n  {len(failed)} of {len(CITIES)} city/cities FAILED and kept "
              f"their previous series: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
