"""Fetch ERA5's land-sea mask for the test boxes.

The frozen ring definition (FEASIBILITY 1b-i) excludes cells more than 50
percent water on ERA5's land-sea mask. The temperature pull does not carry
that field, so it is fetched here.

Static field: one timestep is the whole thing. Tiny request, and it runs
alongside the main pull without competing for anything meaningful.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_night_minima import CACHE, REGIONS  # noqa: E402

DATASET = "reanalysis-era5-single-levels"


def path_for(region: str) -> str:
    return os.path.join(CACHE, f"lsm_{region}.nc")


def fetch(region: str) -> str:
    out = path_for(region)
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return out
    import cdsapi
    tmp = out + ".part"
    cdsapi.Client(quiet=True, progress=False).retrieve(
        DATASET,
        {
            "product_type": ["reanalysis"],
            "variable": ["land_sea_mask"],
            "year": ["2020"], "month": ["01"], "day": ["01"],
            "time": ["00:00"],
            "data_format": "netcdf",
            "area": REGIONS[region]["area"],
        },
        tmp,
    )
    os.replace(tmp, out)
    return out


if __name__ == "__main__":
    for r in sys.argv[1:] or list(REGIONS):
        p = fetch(r)
        import xarray as xr
        with xr.open_dataset(p) as ds:
            var = "lsm" if "lsm" in ds else list(ds.data_vars)[0]
            land = float((ds[var].squeeze() > 0.5).mean()) * 100
            print(f"{r}: {p}  dims={dict(ds.sizes)}  {land:.0f}% of cells are land")
