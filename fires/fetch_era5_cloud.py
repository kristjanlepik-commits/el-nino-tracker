"""Country-mean cloud cover at the SNPP overpass, for the D-121 cloud test.

WHAT THIS IS FOR. `check_observability.py` returned a negative result for
smoke, but could only test suppression that VARIES WITH FIRE SIZE. Cloud
does not vary with fire size, so no fuel-type or scaling test can see it,
and the channel still cannot distinguish a cloud-covered day from a calm
one. This measures the cloud so that gap can be closed with data instead
of left open with a caveat.

WHY ERA5 AND NOT THE MODIS CLOUD PRODUCT. Strategy offered ValidCounts
from MCDWD (D-132), a direct satellite observation and the better
instrument in principle. Two reasons it is not the first pass:

  COST. Fire countries are continental, not river boxes. Measured against
  the real sinusoidal tiling: Russia is 92 tiles per composite day, the 28
  test countries are 393 between them, and the full 13-year test is about
  204,000 tile downloads, roughly 698 GB. Even a 4-country 5-year cut is
  ~37 GB. ERA5 is about 1 to 2 GB for the same span and needs no new
  dependency, since cdsapi already runs here for the ENSO fetchers.

  ENDOGENEITY, which is the more interesting reason. The MODIS cloud mask
  has a documented tendency to flag thick smoke AS cloud. Smoke is produced
  by the fire being measured, so ValidCounts is partly caused by the thing
  it is meant to control for. ERA5 cloud is meteorological reanalysis and
  is not caused by the fire, so it is exogenous.

That makes the two layers complementary rather than substitutes:

    ERA5 coefficient        meteorological blinding
    ValidCounts coefficient cloud + smoke blinding
    the difference          the smoke effect

which is the D-121 question, and neither layer reaches it alone.

CONSTRUCTION RULE, from D-132 and non-negotiable. Cloud enters the model
as a TERM alongside log(area). It is never a denominator. Detections per
cloud-free look would rebuild the exact ratio trap that made the first
version of the smoke test return a confident wrong answer, and per the
asymmetry floods identified it would bias toward a NULL, hiding a real
cloud effect while looking clean. A false positive gets investigated; a
false negative gets filed and never revisited.

=============================================================================
THREE THINGS THAT LOOK LIKE DETAILS AND ARE NOT
=============================================================================

THE DIURNAL CYCLE, which is the one that would have quietly wrecked this.
SNPP crosses at about 13:30 LOCAL solar time, so the UTC hour of the
overpass depends on longitude. Sampling a country at one fixed UTC hour
works for Italy and is badly wrong for Russia, which spans eleven time
zones: at 07:00 UTC its local time runs from 08:20 in the west to 19:00 in
the east, and cloud has a strong diurnal cycle, with convective cloud
peaking in the afternoon. A single-hour sample would therefore measure
morning cloud in one half of the country and evening cloud in the other,
and the resulting covariate would be a noisy proxy for the cloud actually
present at overpass.

That noise is not neutral. It attenuates the regression coefficient toward
zero, which is precisely the false-negative direction, and a null from it
would get filed as "cloud is fine" and never revisited.

So each cell is sampled at the UTC hour matching ITS OWN local 13:30, not
the country's. Several hours are requested per country and the per-cell
value is selected from the matching one. Countries spanning one time zone
cost one hour; Russia costs eleven.

THE DATELINE. Russia's polygon crosses the antimeridian at Chukotka, so a
naive min/max bounding box is [-180, 41, 180, 81]: the entire globe from
41N to 81N. This channel has already paid for that bug once, on the FIRMS
side, where Russia's global-width box was a real cause of the rate-limit
failures I first misdiagnosed as concurrency. Countries that cross the
dateline are requested as TWO lobes and recombined by a count-weighted
mean, never as one box.

THE CENTROID. Any representative longitude comes from the bounding box,
never from a mean of polygon vertices. A vertex mean is weighted by vertex
density, so the USA reads -122.0, the Pacific coast, because Alaska's
coastline carries the most vertices. Any country with one intricate
coastline and one smooth interior has this problem; it is not specific to
the USA. Per-cell hour selection makes this mostly moot, and the rule is
recorded because the naive version looked right in testing.

SCOPE. Only countries where the test can actually RUN are fetched, meaning
those with enough paired area-and-detection weeks in
`check_observability.measure`. That is 28 of the 94 countries holding both
instruments. Fetching the other 66 would be 924 country-years no
regression could use.

The mean is taken over cells INSIDE the country polygon, not the bounding
box, and over all cells rather than only cells with fire. Conditioning on
where fires are would make the covariate endogenous in the same way
ValidCounts is.

RESUMABLE. One cached JSON per country-year. A rerun skips what exists, so
an interrupted pull costs minutes rather than the whole window.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import sys
import tempfile
import threading

import numpy as np

from fires.build_events import contains_points, load_rings

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "era5_cloud")

DATASET = "reanalysis-era5-single-levels"
VARIABLE = "total_cloud_cover"
GRID = [1.0, 1.0]           # ~110 km. A country-mean cloud fraction does not
                            # need finer, and per-cell hour selection
                            # multiplies the download by the time-zone span,
                            # so this is what keeps Russia tractable.
OVERPASS_LOCAL_HOUR = 13.5  # SNPP ascending node, local solar time
YEARS = [str(y) for y in range(2012, 2026)]
ALL_MONTHS = [f"{m:02d}" for m in range(1, 13)]
ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]

DATELINE_SPAN = 350.0   # a bbox this wide means the polygon wrapped
DATELINE_EDGE = 170.0   # and has vertices near both edges


def testable_countries() -> list[str]:
    """Only countries the regression could actually use.

    Derived from the same measurement the smoke test runs on, so the two
    stay consistent by construction rather than by a hand-maintained list
    that would drift the first time the baseline grew.
    """
    from fires.check_observability import measure
    return sorted(row[0] for row in measure())


def local_overpass_hour(lon):
    """UTC hour whose local solar time is nearest 13:30 at this longitude."""
    return np.round(OVERPASS_LOCAL_HOUR - np.asarray(lon) / 15.0).astype(int) % 24


def crosses_dateline(lons: np.ndarray) -> bool:
    return (float(lons.max() - lons.min()) > DATELINE_SPAN
            and bool((lons > DATELINE_EDGE).any())
            and bool((lons < -DATELINE_EDGE).any()))


def lobes(rings: list[np.ndarray]) -> list[tuple[float, float, float, float]]:
    """One (west, south, east, north) box, or two if the polygon wraps."""
    lons = np.concatenate([r[:, 0] for r in rings])
    lats = np.concatenate([r[:, 1] for r in rings])
    south, north = float(lats.min()), float(lats.max())
    if not crosses_dateline(lons):
        return [(float(lons.min()), south, float(lons.max()), north)]
    east_lobe = lons[lons >= 0]
    west_lobe = lons[lons < 0]
    return [(float(east_lobe.min()), south, 180.0, north),
            (-180.0, south, float(west_lobe.max()), north)]


def hours_for_box(west: float, east: float) -> list[int]:
    """Every UTC hour needed to sample this longitude span at local 13:30."""
    step = GRID[1]
    lons = np.arange(west - step, east + step + 1e-9, step)
    return sorted(set(int(h) for h in local_overpass_hour(lons)))


def hours_for_boxes(boxes) -> list[int]:
    out: set[int] = set()
    for west, _s, east, _n in boxes:
        out.update(hours_for_box(west, east))
    return sorted(out)


def _retrieve(area, year: str, hours: list[int], path: str) -> None:
    import cdsapi
    cdsapi.Client(quiet=True, progress=False).retrieve(
        DATASET,
        {
            "product_type": ["reanalysis"],
            "variable": [VARIABLE],
            "year": [year],
            "month": ALL_MONTHS,
            "day": ALL_DAYS,
            "time": [f"{h:02d}:00" for h in hours],
            "data_format": "netcdf",
            "area": area,
            "grid": GRID,
        },
        path,
    )


def _masked_sums(path: str, rings: list[np.ndarray]) -> dict[str, tuple[float, int]]:
    """Per date: (sum of cloud fraction, cell count) inside the polygon.

    Each cell contributes the value from the UTC hour matching its OWN
    local 13:30, so a wide country is not sampled at one wrong local time.

    Sums rather than means, so two lobes of a wrapped country recombine by
    a count-weighted average instead of an unweighted one that would treat
    Chukotka as equal in area to Siberia.
    """
    import xarray as xr

    with xr.open_dataset(path) as ds:
        name = "tcc" if "tcc" in ds else list(ds.data_vars)[0]
        field = ds[name]
        lat_name = "latitude" if "latitude" in field.dims else "lat"
        lon_name = "longitude" if "longitude" in field.dims else "lon"
        lons = field[lon_name].values
        lats = field[lat_name].values
        time_name = [d for d in field.dims if d not in (lat_name, lon_name)][0]

        grid_lon, grid_lat = np.meshgrid(lons, lats)
        pts = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])

        # A multipolygon country is the union of its rings. Holes are not
        # modelled; at 1 degree they fall below the grid for every country
        # in the roster, and counting them as land biases nothing directional.
        inside = np.zeros(len(pts), dtype=bool)
        for ring in rings:
            inside |= contains_points(ring, pts)
        mask = inside.reshape(grid_lat.shape)
        if not mask.any():
            return {}

        target_hour = local_overpass_hour(grid_lon)
        values = field.values
        times = field[time_name].values

        out: dict[str, list] = {}
        for i, when in enumerate(times):
            stamp = np.datetime64(when)
            day = str(stamp.astype("datetime64[D]"))
            hour = int((stamp - stamp.astype("datetime64[D]"))
                       / np.timedelta64(1, "h"))
            selected = mask & (target_hour == hour)
            if not selected.any():
                continue
            cells = values[i][selected]
            cells = cells[np.isfinite(cells)]
            if not cells.size:
                continue
            acc = out.setdefault(day, [0.0, 0])
            acc[0] += float(cells.sum())
            acc[1] += int(cells.size)
        return {day: (total, count) for day, (total, count) in out.items()}


def fetch_country_year(iso: str, year: str, rings, boxes, hours) -> str:
    """Returns 'cached', 'fetched', or an error string. Never raises."""
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, f"{iso}_{year}.json")
    if os.path.exists(dest):
        return "cached"

    pad = GRID[0]
    totals: dict[str, list] = {}
    try:
        for west, south, east, north in boxes:
            # ERA5 wants [North, West, South, East]. Pad by one cell so a
            # country never loses its edge row to rounding, and clamp so the
            # pad cannot push a lobe back across the dateline it was split at.
            area = [min(90.0, north + pad), max(-180.0, west - pad),
                    max(-90.0, south - pad), min(180.0, east + pad)]
            handle, tmp = tempfile.mkstemp(suffix=".nc")
            os.close(handle)
            try:
                _retrieve(area, year, hours, tmp)
                for day, (total, count) in _masked_sums(tmp, rings).items():
                    acc = totals.setdefault(day, [0.0, 0])
                    acc[0] += total
                    acc[1] += count
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)

        series = {day: round(total / count, 4)
                  for day, (total, count) in totals.items() if count}
        if not series:
            return "empty series"
        with open(dest, "w") as fh:
            json.dump({"iso": iso, "year": year, "utc_hours": hours,
                       "grid_deg": GRID[0], "variable": VARIABLE,
                       "lobes": len(boxes), "cloud_fraction": series}, fh)
        return "fetched"
    except Exception as exc:                     # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"[:180]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch ERA5 cloud covariate.")
    parser.add_argument("--only", nargs="*", help="restrict to these ISO codes")
    parser.add_argument("--years", nargs="*", help="restrict to these years")
    parser.add_argument("--plan", action="store_true",
                        help="print the plan and exit without fetching")
    parser.add_argument("--workers", type=int, default=4,
                        help="concurrent CDS requests. The bottleneck is "
                             "queue wait, not bandwidth, so this is close to "
                             "a linear speedup. Kept low on purpose: CDS caps "
                             "concurrent requests per user and being throttled "
                             "is slower than not asking.")
    args = parser.parse_args()

    isos = args.only if args.only else testable_countries()
    years = args.years if args.years else YEARS

    rings = load_rings(set(isos))
    missing = [i for i in isos if i not in rings]
    if missing:
        print(f"No geometry for {len(missing)}: {' '.join(missing)}")
    isos = [i for i in isos if i in rings]

    plan = {}
    for iso in isos:
        boxes = lobes(rings[iso])
        plan[iso] = (boxes, hours_for_boxes(boxes))

    hour_total = sum(len(h) for _b, h in plan.values())
    print(f"{len(isos)} countries x {len(years)} years = "
          f"{len(isos) * len(years)} country-years.")
    print(f"{hour_total} UTC hours across the roster, "
          f"{hour_total / max(1, len(isos)):.1f} per country on average.")
    wrapped = [i for i, (b, _h) in plan.items() if len(b) == 2]
    if wrapped:
        print(f"Dateline-split (two lobes each): {' '.join(wrapped)}")

    if args.plan:
        print(f"\n{'iso':<6}{'hours':>7}  utc sample times")
        for iso in sorted(isos, key=lambda i: -len(plan[i][1])):
            _boxes, hours = plan[iso]
            shown = " ".join(f"{h:02d}" for h in hours)
            print(f"{iso:<6}{len(hours):>7}  {shown}")
        return 0
    print()

    # LONGEST FIRST. Russia is 12 UTC hours over a continental box and costs
    # far more than Botswana's single hour. Submitted in cost order so the
    # expensive countries start immediately instead of straggling alone at
    # the end while every worker but one sits idle.
    def cost(iso: str) -> float:
        boxes, hours = plan[iso]
        span = sum((east - west) * (north - south)
                   for west, south, east, north in boxes)
        return len(hours) * span

    work = [(iso, year) for iso in sorted(isos, key=cost, reverse=True)
            for year in years]
    total = len(work)
    failures, done, fetched = [], 0, 0
    lock = threading.Lock()

    def run(job):
        iso, year = job
        boxes, hours = plan[iso]
        return iso, year, hours, fetch_country_year(iso, year, rings[iso],
                                                    boxes, hours)

    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for iso, year, hours, status in pool.map(run, work):
            with lock:
                done += 1
                if status not in ("cached", "fetched"):
                    failures.append((iso, year, status))
                    print(f"  [{done}/{total}] {iso} {year} FAILED {status}",
                          flush=True)
                elif status == "fetched":
                    fetched += 1
                    print(f"  [{done}/{total}] {iso} {year} ok "
                          f"({len(hours)} hours)", flush=True)

    print(f"\n{done} country-years processed, {fetched} newly fetched, "
          f"{len(failures)} failed.")
    if failures:
        print("Failures are RESUMABLE: rerun and cached years are skipped.")
        for iso, year, status in failures[:20]:
            print(f"  {iso} {year}  {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
