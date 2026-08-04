"""Gate 0: does ERA5 resolve a static urban heat island at all?

Pre-registered in heat/FEASIBILITY.md 1c and ratified as D-067 before any
data existed. This runs FIRST and it is not the hypothesis test.

Why it exists. A flat city-minus-ring TREND has two readings that look
identical in the output: ERA5 sees a city and sees no growth in it, which
is clean; or ERA5 never resolved the city, in which case the trend test had
no power and proves nothing. Gate 0 separates them by asking whether the
city cell is measurably warmer at night than its ring in LEVEL, in any era.

If growth cities show no level difference, the D-049 test is uninformative
about contamination and the real finding is that a 31 km cell is not the
reader's city.

Reports per city and by era. Does NOT compute the growth-versus-flat trend
differential, which waits for the full 192-chunk set.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import xarray as xr

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

# Frozen set, FEASIBILITY 1b-i. EU half only; US chunks still pulling.
CITIES = {
    "Madrid":    {"lat": 40.42, "lon": -3.70, "group": "growth", "region": "eu"},
    "Munich":    {"lat": 48.14, "lon": 11.58, "group": "growth", "region": "eu"},
    "Leipzig":   {"lat": 51.34, "lon": 12.37, "group": "flat",   "region": "eu"},
    "Liverpool": {"lat": 53.41, "lon": -2.98, "group": "flat",   "region": "eu"},
    "Naples":    {"lat": 40.85, "lon": 14.27, "group": "flat",   "region": "eu"},
}

# Ring annulus, in DEGREES OF GREAT-CIRCLE DISTANCE. See note in main().
RING_INNER_DEG, RING_OUTER_DEG = 0.75, 1.5
KM_PER_DEG = 111.32
LAND_THRESHOLD = 0.5


def great_circle_deg(lat1, lon1, lat2, lon2):
    """Angular separation in degrees. Arrays broadcast."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    a = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl)
    return np.degrees(np.arccos(np.clip(a, -1.0, 1.0)))


def load_lsm(region: str):
    p = os.path.join(CACHE, f"lsm_{region}.nc")
    if not os.path.exists(p):
        raise SystemExit(f"missing land-sea mask {p}; run heat/fetch_lsm.py {region}")
    with xr.open_dataset(p) as ds:
        var = "lsm" if "lsm" in ds else list(ds.data_vars)[0]
        return ds[var].squeeze(drop=True).load()


def cell_masks(lsm, lat_c, lon_c):
    """Return (city selector, ring boolean mask) for one city."""
    lats, lons = lsm["latitude"].values, lsm["longitude"].values
    LON, LAT = np.meshgrid(lons, lats)
    dist = great_circle_deg(LAT, LON, lat_c, lon_c)
    land = lsm.values > LAND_THRESHOLD

    ij = np.unravel_index(np.argmin(dist), dist.shape)
    ring = (dist >= RING_INNER_DEG) & (dist <= RING_OUTER_DEG) & land
    return ij, ring, dist


def daily_night_min(da: xr.DataArray) -> xr.DataArray:
    """Minimum over the sampled night hours, per calendar day."""
    tname = "valid_time" if "valid_time" in da.dims else "time"
    return da.groupby(f"{tname}.date").min(dim=tname)


def main() -> int:
    region = "eu"
    lsm = load_lsm(region)
    files = sorted(glob.glob(os.path.join(CACHE, f"nightT_{region}_*.nc")))
    if not files:
        raise SystemExit("no EU chunks found")
    print(f"gate 0, region {region}: {len(files)} chunks\n")

    geom = {}
    for name, c in CITIES.items():
        if c["region"] != region:
            continue
        ij, ring, dist = cell_masks(lsm, c["lat"], c["lon"])
        geom[name] = (ij, ring)
        print(f"  {name:10s} city cell at {lsm['latitude'].values[ij[0]]:.2f}N "
              f"{lsm['longitude'].values[ij[1]]:.2f}E, ring = {int(ring.sum())} land cells "
              f"({RING_INNER_DEG}-{RING_OUTER_DEG} deg = "
              f"{RING_INNER_DEG*KM_PER_DEG:.0f}-{RING_OUTER_DEG*KM_PER_DEG:.0f} km)")
    print()

    series = {n: {} for n in geom}          # name -> {date: (city, ringmean)}
    for k, f in enumerate(files, 1):
        with xr.open_dataset(f) as ds:
            t2m = ds["t2m"]
            dmin = daily_night_min(t2m).load()
            dates = dmin["date"].values
            arr = dmin.values                       # (day, lat, lon)
            for name, (ij, ring) in geom.items():
                city = arr[:, ij[0], ij[1]]
                rmean = arr[:, ring].mean(axis=1)
                for d, cv, rv in zip(dates, city, rmean):
                    series[name][d] = (float(cv), float(rv))
        if k % 24 == 0:
            print(f"  ...{k}/{len(files)} chunks read")

    print("\n" + "=" * 74)
    print("GATE 0: city cell minus rural ring, night minima, LEVEL (degrees C)")
    print("=" * 74)
    print(f"{'city':11s} {'group':7s} {'years':6s} {'mean':>8s} {'se':>7s} "
          f"{'t':>7s} {'1950-59':>8s} {'2010+':>8s}")

    out = {}
    for name in geom:
        recs = series[name]
        years = sorted({d.year for d in recs})
        annual = []
        for y in years:
            vals = [c - r for d, (c, r) in recs.items() if d.year == y]
            if len(vals) > 200:
                annual.append((y, float(np.mean(vals))))
        ys = np.array([a[0] for a in annual])
        vs = np.array([a[1] for a in annual])
        mean, se = vs.mean(), vs.std(ddof=1) / np.sqrt(len(vs))
        early = vs[ys < 1960].mean() if (ys < 1960).any() else np.nan
        late = vs[ys >= 2010].mean() if (ys >= 2010).any() else np.nan
        out[name] = (mean, se, len(vs), ys, vs)
        print(f"{name:11s} {CITIES[name]['group']:7s} {len(vs):<6d} "
              f"{mean:+8.3f} {se:7.3f} {mean/se:+7.1f} {early:+8.3f} {late:+8.3f}")

    growth = [n for n in geom if CITIES[n]["group"] == "growth"]
    gm = np.array([out[n][0] for n in growth])
    print("\n" + "-" * 74)
    print(f"Growth cities ({', '.join(growth)}): mean level difference "
          f"{gm.mean():+.3f} C")
    print("\nGATE 0 READS:")
    if all(abs(out[n][0]) > 3 * out[n][1] for n in growth):
        print("  PASS. ERA5 resolves a level difference at the city cell for every")
        print("  growth city. The trend test has power and its result is meaningful.")
    else:
        print("  FAIL. The level difference is not distinguishable from zero for at")
        print("  least one growth city. The trend test is UNINFORMATIVE about")
        print("  contamination; a flat trend would mean 'no city resolved', not")
        print("  'no contamination'. See FEASIBILITY 1c and section 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
