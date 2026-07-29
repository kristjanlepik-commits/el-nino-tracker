"""Global same-week rainfall anomaly: where was last week unusual?

Answers the "where should I look" question at global scale, which is the
question Fire's map answers for fire and which no flood product can
answer directly yet (see FEASIBILITY.md section 7: the flood-extent
baselines exist for three regions, and a global flood baseline is 287
tiles x 7 days x 23 years).

Rainfall can do it now because IMERG is one global file per day rather
than tiles, and because the Late Run reaches back to 2000, so the whole
comparison uses a single product with no near-real-time versus
science-quality boundary to cross. That matters: the Final Run is ten
months behind, so a Final-Run baseline against a Late-Run current week
would be comparing two products and calling it weather.

What this is NOT. It measures rainfall, not flooding, and the two
correlate at only Spearman +0.23 outside extreme events. A wet week is
not a flood: that depends on antecedent soil moisture, river state and
terrain. This says where the water fell, which is where to look next,
not what happened.

Resolution. Native 0.1 degree is block-averaged to 0.5 degree, which is
2,500 times fewer cells to compare and still far finer than any
statement we would publish. Averaged, not subsampled, so extremes are
diluted rather than missed.

Output is a single npz of week totals per year per cell, about 28 MB,
from which ratio-to-median and rank-on-record are arithmetic.
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
TOKEN_PATH = os.path.expanduser("~/.earthdata_token")
AGG = 5                     # 0.1 deg -> 0.5 deg
NLON, NLAT = 3600 // AGG, 1800 // AGG


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def token():
    return open(TOKEN_PATH).read().strip()


def granule_url(day, short="GPM_3IMERGDL", ver="07", tries=4):
    p = {"short_name": short, "version": ver,
         "temporal": f"{day}T00:00:00Z,{day}T23:59:59Z", "page_size": 1}
    rq = urllib.request.Request(f"{CMR}?{urllib.parse.urlencode(p)}",
                                headers={"User-Agent": "TLS-floods/0.1"})
    # CMR returns intermittent 500s. An unretried one killed a 27-year
    # run at year 25, which is a lot of bandwidth to lose to a blip.
    for attempt in range(tries):
        try:
            e = json.load(urllib.request.urlopen(rq, timeout=60))["feed"]["entry"]
            break
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    if not e:
        return None
    for l in e[0].get("links", []):
        h = l.get("href", "")
        if h.startswith("https://") and h.endswith(".nc4") and "opendap" not in h:
            return h
    return None


def fetch_days(days, tmp, tok, workers):
    """curl in parallel. Same reasoning as capture_viirs_global: a
    subprocess fails with an exit code, a thread pool hangs."""
    cfg, want = os.path.join(tmp, "_curl.cfg"), []
    with open(cfg, "w") as fh:
        fh.write(f'header = "Authorization: Bearer {tok}"\n')
        for d in days:
            dest = os.path.join(tmp, f"{d}.nc4")
            if os.path.exists(dest):
                continue
            u = granule_url(d)
            if not u:
                log(f"  {d}: no granule")
                continue
            fh.write(f'url = "{u}"\noutput = "{dest}"\n')
            want.append(d)
    if want:
        subprocess.call(["curl", "-sS", "-L", "--fail", "-Z",
                         "--parallel-max", str(workers), "--retry", "3",
                         "--connect-timeout", "60", "--max-time", "900", "-K", cfg])
    os.unlink(cfg)
    return want


def week_grid(days, tmp):
    """Sum a week of daily global rainfall onto the 0.5 degree grid.

    Returns the total and a per-cell count of days that actually had a
    retrieval. IMERG carries a fill value of -9999.9 where there is no
    retrieval, which is common at high latitudes, and netCDF4 hands it
    back inside the array rather than as NaN. Averaging it in produced
    week totals of minus 130 mm on the first attempt.

    Zero-filling would be the other wrong answer: it would turn "we do
    not know" into "it did not rain", which is the same failure the
    ValidCounts discipline exists to prevent on the flood side. So
    validity is counted per cell and travels with the total.
    """
    total = np.zeros((NLON, NLAT), dtype=np.float32)
    valid = np.zeros((NLON, NLAT), dtype=np.uint8)
    got = 0
    import netCDF4
    for d in days:
        p = os.path.join(tmp, f"{d}.nc4")
        if not os.path.exists(p):
            continue
        try:
            ds = netCDF4.Dataset(p)
            a = np.array(ds.variables["precipitation"][:]).squeeze()
            ds.close()
        except Exception as exc:
            log(f"  {d}: unreadable, {repr(exc)[:70]}")
            os.unlink(p)
            continue
        ok = np.isfinite(a) & (a > -100.0)
        a = np.where(ok, a, 0.0)
        # A coarse cell counts as observed only if every native cell in
        # it had a retrieval, so a partly-missing cell never reads as a
        # dry one.
        cell_ok = ok.reshape(NLON, AGG, NLAT, AGG).all(axis=(1, 3))
        total += np.where(
            cell_ok, a.reshape(NLON, AGG, NLAT, AGG).mean(axis=(1, 3)), 0.0
        ).astype(np.float32)
        valid += cell_ok.astype(np.uint8)
        got += 1
        os.unlink(p)
    return total, valid, got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="07-21", help="MM-DD")
    ap.add_argument("--end", default="07-27", help="MM-DD")
    ap.add_argument("--years", default="2000-2026")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--tmp", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    os.makedirs(args.tmp, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    out = args.out or os.path.join(here, "data",
                                   f"imerg_global_week_{args.start}_{args.end}.npz")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    y0, y1 = (int(x) for x in args.years.split("-"))
    m0, d0 = (int(x) for x in args.start.split("-"))
    m1, d1 = (int(x) for x in args.end.split("-"))

    grids = dict(np.load(out)) if os.path.exists(out) else {}
    tok = token()

    for year in range(y0, y1 + 1):
        key = str(year)
        if key in grids:
            continue
        day, last, days = dt.date(year, m0, d0), dt.date(year, m1, d1), []
        while day <= last:
            days.append(day.isoformat())
            day += dt.timedelta(days=1)
        fetch_days(days, args.tmp, tok, args.workers)
        total, valid, got = week_grid(days, args.tmp)
        if got == 0:
            log(f"{year}: nothing retrieved, skipping")
            continue
        if got < len(days):
            log(f"{year}: only {got}/{len(days)} days, EXCLUDED to keep weeks comparable")
            continue
        grids[key] = total
        grids[key + "_validdays"] = valid
        np.savez_compressed(out, **grids)
        full = valid == len(days)
        log(f"{year}: {got}/{len(days)} days, week mean {float(total[full].mean()):.2f} mm "
            f"over {100*full.mean():.0f}% fully-observed cells "
            f"[{len(grids)//2} years stored]")

    log(f"done -> {out}, {len(grids)} years")


if __name__ == "__main__":
    sys.exit(main())
