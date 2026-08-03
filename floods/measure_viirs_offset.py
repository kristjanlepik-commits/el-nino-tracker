"""Measure the MODIS-to-VIIRS flood-extent offset, per region.

MODIS is switched off during the event (Aqua ~Aug 2026, Terra ~Jan
2027) and the 23-year baseline is a MODIS record, so every future
number depends on a conversion between the two instruments. One
measurement of that conversion exists: 1.85x over the Ganges at
observability above 0.70. Generalising a single region's ratio to the
world is the exact shape of a claim already retracted once in this
channel, so this measures it independently per tile.

Method. VIIRS weekly totals are already held from the D-038 global
capture. This pulls the matching MODIS near-real-time tiles from LAADS
for the same days, reduces them identically, and reports the ratio per
tile alongside observability, so a ratio computed where neither
instrument could see is visible as such rather than averaged in.

Bounded on purpose: a fixed tile list, one week, about 0.8 GB. Product
asked for eight tiles and not a sweep.
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np

LAADS = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3_NRT"
LAYERS = ("Flood_3Day_250m", "ValidCounts_3Day_250m")


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def http_json(u):
    rq = urllib.request.Request(u, headers={"User-Agent": "TLS-floods/0.1"})
    return json.load(urllib.request.urlopen(rq, timeout=60))["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True, help="comma separated, e.g. h27v06,h11v08")
    ap.add_argument("--year", default="2026")
    ap.add_argument("--doys", default="202,203,204,205,206,207,208")
    ap.add_argument("--viirs-dir", required=True)
    ap.add_argument("--tmp", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tiles = args.tiles.split(",")
    doys = args.doys.split(",")
    os.makedirs(args.tmp, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    out = args.out or os.path.join(here, "data", "viirs_modis_offset.json")

    tok = open(os.path.expanduser("~/.earthdata_token")).read().strip()

    # VIIRS side, already captured: weekly flood and observed per tile.
    vf, vo = {}, {}
    for doy in doys:
        p = os.path.join(args.viirs_dir, f"vcdwd_0p1deg_{args.year}{doy}.npz")
        if not os.path.exists(p):
            log(f"VIIRS {doy} missing, skipped")
            continue
        z = np.load(p)
        for t in tiles:
            if t in z.files:
                a = z[t]
                vf[t] = vf.get(t, 0) + int(a[0].sum())
                vo[t] = vo.get(t, 0) + int(a[3].sum())

    # MODIS side: fetch, reduce, discard.
    mf, mo = {}, {}
    from pyhdf.SD import SD, SDC
    for doy in doys:
        try:
            listing = {f["name"].split(".")[2]: f["name"]
                       for f in http_json(f"{LAADS}/{args.year}/{doy}.json")
                       if len(f["name"].split(".")) > 2}
        except Exception as exc:
            log(f"MODIS {doy}: listing failed {repr(exc)[:70]}")
            continue
        cfg = os.path.join(args.tmp, "_curl.cfg")
        want = [t for t in tiles if t in listing]
        with open(cfg, "w") as fh:
            fh.write(f'header = "Authorization: Bearer {tok}"\n')
            for t in want:
                fh.write(f'url = "{LAADS}/{args.year}/{doy}/{listing[t]}"\n')
                fh.write(f'output = "{os.path.join(args.tmp, t + ".hdf")}"\n')
        subprocess.call(["curl", "-sS", "-L", "--fail", "-Z", "--parallel-max", "6",
                         "--retry", "3", "--connect-timeout", "60", "--max-time", "900",
                         "-K", cfg])
        os.unlink(cfg)
        for t in want:
            p = os.path.join(args.tmp, t + ".hdf")
            if not os.path.exists(p):
                continue
            try:
                hdf = SD(p, SDC.READ)
                fl = hdf.select(LAYERS[0]).get()
                va = hdf.select(LAYERS[1]).get().astype(np.int16)
                hdf.end()
                va[va == 255] = 0
                mf[t] = mf.get(t, 0) + int(((fl == 2) | (fl == 3)).sum())
                mo[t] = mo.get(t, 0) + int((va > 0).sum())
            except Exception as exc:
                log(f"MODIS {doy} {t}: {repr(exc)[:70]}")
            finally:
                os.unlink(p)
        log(f"{doy} done ({len(want)} tiles)")

    rows = []
    for t in tiles:
        if t not in mf or t not in vf or not mf[t]:
            rows.append(dict(tile=t, status="no_pair_or_zero_modis",
                             modis_flood=mf.get(t), viirs_flood=vf.get(t)))
            continue
        rows.append(dict(
            tile=t, status="ok",
            modis_flood=mf[t], viirs_flood=vf[t],
            ratio=round(vf[t] / mf[t], 3),
            modis_obs=round(mo[t] / (4800 * 4800 * len(doys)), 3),
            viirs_obs=round(vo[t] / (100 * 100 * 2304 * len(doys)), 3),
            obs_adjusted=round((vf[t] / max(vo[t], 1)) / (mf[t] / max(mo[t], 1)), 3),
        ))
    with open(out, "w") as fh:
        json.dump(rows, fh, indent=2)
    log(f"wrote {out}")
    for r in rows:
        print("   " + json.dumps(r))


if __name__ == "__main__":
    sys.exit(main())
