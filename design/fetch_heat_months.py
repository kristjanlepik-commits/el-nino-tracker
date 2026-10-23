"""ERA5 monthly means, May to September, for the explainer's moving heat map.

Kristjan, 16 October: "can you make that a moving heat as well? May - Sept?"
FLO's payload carries September only, so this pulls the five months for
1991-2026 (1991-2020 is the baseline, 2026 is ERA5T, preliminary): sea
surface temperature and 2 m air temperature on the same 0.5 degree box as
the September map. Design fetched it for speed overnight; FLO signs off on
the rendered numbers as for every other figure on the page.

The NetCDF goes to a scratch path outside the repo (OUT, first argument),
never into the tree, so it is never committed and never trips the 5 MB
guard on untracked files.

Run:  .venv/bin/python design/fetch_heat_months.py OUT.nc
"""
import sys

import cdsapi

OUT = sys.argv[1]
cdsapi.Client().retrieve(
    "reanalysis-era5-single-levels-monthly-means",
    {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": ["2m_temperature", "sea_surface_temperature"],
        "year": [str(y) for y in range(1991, 2027)],
        "month": ["05", "06", "07", "08", "09"],
        "time": ["00:00"],
        "area": [72, -25, 28, 45],
        "grid": [0.5, 0.5],
        "data_format": "netcdf",
        "download_format": "unarchived",
    },
    OUT,
)
print("wrote", OUT)
