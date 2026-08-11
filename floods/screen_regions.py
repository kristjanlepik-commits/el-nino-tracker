"""Screen candidate catchments before paying for a baseline.

Phase 2 under D-120. A full 23-year flood-extent baseline costs about
2.3 GB per tile and roughly an hour, so committing to a region before
knowing whether the instrument can see it is the expensive mistake.
Manila cost 4.6 GB to discover it fails.

This screens for free. The global VIIRS capture already holds
observability for every 0.1 degree cell on Earth, so the leading
indicator of the region-qualification gate can be read off data we
already have, for any box, instantly.

**THE FIRST VERSION OF THIS SCREEN WAS WRONG, and the control caught
it.** It read observability from the VIIRS capture, because that was
free. But the baseline is MODIS, and the two instruments do not see
equally: across the European tiles VIIRS ran 0.84 to 0.99 where MODIS
ran 0.52 to 0.71. Manila, included deliberately as a known-fail control,
scored 0.705 and read "promising" against a MODIS baseline median of
0.23. A screen that passes a region we have already proven fails is
worse than no screen.

So the screen now samples the MODIS ARCHIVE, in the region's own flood
season, which is the right instrument and the right month. It costs
about 260 MB per region against 4.6 GB for a full baseline, so a
twenty-region screen is affordable and a twenty-region commitment is
not.

**What this screens for, and what it cannot.** The gate has two
criteria: observability dependence (a rank correlation across baseline
years, which needs many years and cannot be estimated from one week)
and a count floor. What CAN be read from one week is the observability
LEVEL, and level is the leading indicator: Manila fails at a baseline
median of 0.23 and Somalia passes at 0.93. A region that cannot be seen
in a clear-ish week will not be seen in its flood season, when there is
more cloud rather than less.

So a low score here is close to disqualifying, and a high score is
permission to spend the fetch budget, not a pass. The gate itself still
runs on the full baseline.

**The season caveat, stated because it is the honest limit.** The
captured window is late July. For a catchment whose flood season is
January, this measures the wrong month, and July observability will
generally be an OPTIMISTIC estimate for a monsoon basin and a
PESSIMISTIC one for a Mediterranean winter basin. Regions are therefore
scored and ranked, never accepted or rejected, on this alone.
"""

import argparse
import glob
import json
import os
import sys

import datetime as dt

import numpy as np

# Candidates, drawn on catchments rather than as regional rectangles,
# following the Peru finding that box geometry moves the measured signal
# by a factor of four. Europe and the US are included from the start per
# product's requirement; most weeks they will read normal, and that is
# the point rather than a cost.
CANDIDATES = {
    # --- Europe -----------------------------------------------------
    "po_basin":         (8.0, 12.5, 44.5, 46.0, "Po basin, Italy", "autumn"),
    "rhine_meuse":      (4.5, 8.0, 49.5, 52.0, "Rhine and Meuse", "winter"),
    "danube_middle":    (17.0, 21.5, 44.5, 48.0, "Middle Danube", "spring"),
    "ebro_iberian":     (-2.0, 1.0, 41.0, 43.0, "Ebro basin, Spain", "autumn"),
    "severn_thames":    (-4.0, 0.5, 51.0, 53.0, "Severn and Thames", "winter"),
    "vistula_oder":     (15.0, 21.5, 50.0, 53.0, "Vistula and Oder", "summer"),
    # --- United States ----------------------------------------------
    "lower_mississippi": (-92.0, -88.0, 30.0, 35.0, "Lower Mississippi", "spring"),
    "upper_midwest":    (-96.0, -90.0, 38.0, 43.0, "Upper Midwest", "spring"),
    "central_valley":   (-122.0, -119.0, 36.0, 40.0, "Central Valley, CA", "winter"),
    "texas_gulf":       (-97.0, -94.0, 28.0, 31.0, "Texas Gulf coast", "summer"),
    "carolinas":        (-81.0, -77.0, 33.0, 36.0, "Carolinas", "autumn"),
    # --- Tropics and elsewhere --------------------------------------
    "somalia_shabelle_juba": (42.0, 46.5, 1.0, 6.5, "Juba and Shabelle", "Deyr"),
    "peru_ecuador_coast": (-82.0, -75.0, -12.0, 2.0, "Coastal Peru", "Mar"),
    "ganges_brahmaputra": (86.0, 92.0, 21.0, 26.5, "Ganges delta", "monsoon"),
    "mekong_lower":     (104.0, 107.0, 10.0, 13.5, "Lower Mekong", "monsoon"),
    "niger_inner_delta": (-6.0, -2.0, 13.5, 16.5, "Niger inner delta", "autumn"),
    "zambezi_lower":    (33.0, 36.5, -18.5, -15.5, "Lower Zambezi", "Jan-Mar"),
    "parana_lower":     (-60.0, -57.0, -34.0, -27.0, "Lower Parana", "summer"),
    "murray_darling":   (142.0, 148.0, -36.0, -30.0, "Murray-Darling", "winter"),
    "manila_luzon_west": (119.5, 121.5, 13.5, 16.0, "Manila (known fail)", "monsoon"),
}


ARCHIVE = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3"

# WRONG, AND THE CONTROL PROVED IT TWICE.
#
# Three sample years cannot estimate observability when the year-to-year
# spread is large. Manila ranges 0.01 to 0.83 between years; a 3-year
# sample has median error 0.085 and 90th-percentile error 0.165 against
# the truth, which is enough to cross the decision boundary. The three
# years this used happened to include 2016 at 0.74 and a clear 2024, so
# Manila screened at 0.539 against a true 0.232 and read "marginal"
# rather than "likely fails".
#
# Compounding it, the estimate below POOLS: total observed over total
# pixels, which is a mean weighted toward clear years, where the gate
# uses the median of per-year values.
#
# The fix is ONE DAY IN EVERY YEAR rather than three days in three
# years. Same idea, opposite axis: cover the variance, not the window.
# It recovers Manila's 0.232 exactly, costs about 660 MB for a two-tile
# region, and yields enough paired years to estimate the dependence
# correlation as well, which a 3-year sample never could.
#
# Retained rather than deleted because the wrong version is the reason
# the right one is shaped as it is.
SAMPLE_YEARS = tuple(range(2003, 2026))   # every year, one day each

# Each region is sampled in ITS OWN flood season. Screening a
# Mediterranean winter basin in July measures the wrong month and would
# flatter it exactly as the VIIRS version flattered Manila.
SEASON_WINDOW = {
    "autumn": (10, 15), "winter": (1, 15), "spring": (4, 15),
    "summer": (7, 15), "monsoon": (8, 5), "Deyr": (11, 12),
    "Mar": (3, 24), "Jan-Mar": (2, 10),
}


def sample_modis(lo0, lo1, la0, la1, season, tok, ndays=1):
    """One day in EVERY year, returning PER-YEAR values.

    Returns (per_year_observability, per_year_flood_counts). The caller
    takes medians and the dependence correlation, so the estimate matches
    what the gate actually computes: a median of per-year values and a
    rank correlation across years. Pooling would weight clear years and
    read high, which is half of why the first version passed Manila."""
    import subprocess, tempfile, urllib.request
    from pyhdf.SD import SD, SDC
    mon, day = SEASON_WINDOW.get(season, (8, 5))
    tiles = {}
    for h in range(int((lo0 + 180) // 10), int((lo1 + 180) // 10) + 1):
        for v in range(int((90 - la1) // 10), int((90 - la0) // 10) + 1):
            tl0, tt1 = -180 + 10 * h, 90 - 10 * v
            r0 = max(0, int((tt1 - min(la1, tt1)) / (10 / 4800)))
            r1 = min(4800, int(np.ceil((tt1 - max(la0, tt1 - 10)) / (10 / 4800))))
            c0 = max(0, int((max(lo0, tl0) - tl0) / (10 / 4800)))
            c1 = min(4800, int(np.ceil((min(lo1, tl0 + 10) - tl0) / (10 / 4800))))
            if r1 > r0 and c1 > c0:
                tiles[f"h{h:02d}v{v:02d}"] = (r0, r1, c0, c1)
    per_year_obs, per_year_flood = {}, {}
    for yr in SAMPLE_YEARS:
        F = O = P = 0
        for k in range(ndays):
            doy = (dt.date(yr, mon, day) + dt.timedelta(days=k)).timetuple().tm_yday
            try:
                rq = urllib.request.Request(f"{ARCHIVE}/{yr}/{doy:03d}.json",
                                            headers={"User-Agent": "TLS/0.1"})
                L = {f["name"].split(".")[2]: f["name"]
                     for f in json.load(urllib.request.urlopen(rq, timeout=60))["content"]
                     if len(f["name"].split(".")) > 2}
            except Exception:
                continue
            for t, sl in tiles.items():
                if t not in L:
                    continue
                fd, tmp = tempfile.mkstemp(suffix=".hdf")
                os.close(fd)
                rc = subprocess.call(["curl", "-sS", "-L", "--fail", "-m", "600",
                                      "-H", f"Authorization: Bearer {tok}",
                                      "-o", tmp, f"{ARCHIVE}/{yr}/{doy:03d}/{L[t]}"])
                try:
                    if rc == 0 and os.path.getsize(tmp) > 1000:
                        hdf = SD(tmp, SDC.READ)
                        r0, r1, c0, c1 = sl
                        st, ct = (r0, c0), (r1 - r0, c1 - c0)
                        fla = hdf.select("Flood_3Day_250m").get(start=st, count=ct)
                        va = hdf.select("ValidCounts_3Day_250m").get(start=st, count=ct).astype(np.int16)
                        hdf.end()
                        va[va == 255] = 0
                        F += int(((fla == 2) | (fla == 3)).sum())
                        O += int((va > 0).sum())
                        P += int(fla.size)
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
        if P:
            per_year_obs[yr] = O / P
            per_year_flood[yr] = F
    return per_year_obs, per_year_flood


def load_capture(d):
    fl, ob, nd = {}, {}, {}
    files = sorted(glob.glob(os.path.join(d, "vcdwd_0p1deg_*.npz")))
    for f in files:
        z = np.load(f)
        for t in z.files:
            a = z[t]
            fl[t] = fl.get(t, 0) + a[0].astype(np.int64)
            ob[t] = ob.get(t, 0) + a[3].astype(np.int64)
            nd[t] = nd.get(t, 0) + a[2].astype(np.int64)
    return fl, ob, nd, len(files)


def box_stats(fl, ob, nd, lo0, lo1, la0, la1):
    F = O = N = 0
    for h in range(int((lo0 + 180) // 10), int((lo1 + 180) // 10) + 1):
        for v in range(int((90 - la1) // 10), int((90 - la0) // 10) + 1):
            t = f"h{h:02d}v{v:02d}"
            if t not in fl:
                continue
            tl0, tt1 = -180 + 10 * h, 90 - 10 * v
            i0, i1 = max(0, int((lo0 - tl0) / 0.1)), min(100, int(np.ceil((lo1 - tl0) / 0.1)))
            j0, j1 = max(0, int((tt1 - la1) / 0.1)), min(100, int(np.ceil((tt1 - la0) / 0.1)))
            if i1 > i0 and j1 > j0:
                F += int(fl[t][i0:i1, j0:j1].sum())
                O += int(ob[t][i0:i1, j0:j1].sum())
                N += int(nd[t][i0:i1, j0:j1].sum())
    return F, O, N


def tiles_for(lo0, lo1, la0, la1):
    return len({(h, v)
                for h in range(int((lo0 + 180) // 10), int((lo1 + 180) // 10) + 1)
                for v in range(int((90 - la1) // 10), int((90 - la0) // 10) + 1)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-dir", help="VIIRS capture; free but WRONG INSTRUMENT")
    ap.add_argument("--modis", action="store_true",
                    help="sample the MODIS archive in each region's own season. "
                         "This is the valid screen; the VIIRS one flattered Manila.")
    ap.add_argument("--only", help="comma separated region ids")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cands = CANDIDATES
    if args.only:
        keep = set(args.only.split(","))
        cands = {k: v for k, v in CANDIDATES.items() if k in keep}

    if args.modis:
        tok = open(os.path.expanduser("~/.earthdata_token")).read().strip()
        print(f"MODIS screen: {len(SAMPLE_YEARS)} sample years x 3 days, "
              f"each region in its own flood season\n", flush=True)
        print(f"{'region':26s}{'season':>9s}{'tiles':>6s}{'GB':>6s}{'obs':>7s}"
              f"{'obs dep':>9s}{'est wk px':>11s}  gate", flush=True)
        rows = []
        for rid, (lo0, lo1, la0, la1, label, season) in cands.items():
            F, O, P = sample_modis(lo0, lo1, la0, la1, season, tok)
            if P == 0:
                print(f"{label:26s}   no data"); continue
            obs = O / P
            dens = F / O * 1e6 if O else 0.0
            nt = tiles_for(lo0, lo1, la0, la1)
            gb = round(nt * 7 * 23 * 14.4 / 1000, 1)
            read = ("promising" if obs >= 0.60 else
                    "marginal" if obs >= 0.40 else "likely fails")
            rows.append(dict(region_id=rid, label=label, season=season,
                             box=[lo0, lo1, la0, la1], tiles=nt, baseline_gb=gb,
                             modis_observability=round(obs, 3),
                             flood_per_million_observed=round(dens, 1), read=read))
            print(f"{label:26s}{season:>9s}{nt:6d}{gb:6.1f}{obs:7.3f}{dens:12.1f}  {read}", flush=True)
        rows.sort(key=lambda r: (not r["predicted_qualify"], -r["modis_observability"]))
        if args.out:
            json.dump({"screen": "MODIS archive, region's own flood season",
                       "sample_years": list(SAMPLE_YEARS),
                       "note": "Screens observability LEVEL, the leading indicator. "
                               "The dependence criterion needs the full baseline. "
                               "Manila is included as a known-fail control.",
                       "candidates": rows}, open(args.out, "w"), indent=1)
            print(f"\nwrote {args.out}")
        return 0

    fl, ob, nd, ndays = load_capture(args.capture_dir)
    if not fl:
        print("no capture files found")
        return 2
    print(f"screening against {ndays} captured global days, {len(fl)} tiles\n")
    print(f"{'region':26s}{'tiles':>6s}{'GB':>6s}{'obs':>7s}{'flood/Mobs':>12s}  read")
    rows = []
    for rid, (lo0, lo1, la0, la1, label, season) in cands.items():
        F, O, N = box_stats(fl, ob, nd, lo0, lo1, la0, la1)
        if O + N == 0:
            print(f"{label:26s}   no data")
            continue
        obs = O / (O + N)
        dens = F / O * 1e6 if O else 0.0
        nt = tiles_for(lo0, lo1, la0, la1)
        gb = round(nt * 7 * 23 * 14.4 / 1000, 1)
        read = ("promising" if obs >= 0.70 else
                "marginal" if obs >= 0.50 else
                "likely fails")
        rows.append(dict(region_id=rid, label=label, season=season,
                         box=[lo0, lo1, la0, la1], tiles=nt, baseline_gb=gb,
                         observability=round(obs, 3),
                         flood_per_million_observed=round(dens, 1), read=read))
        print(f"{label:26s}{nt:6d}{gb:6.1f}{obs:7.3f}{dens:12.1f}  {read}")

    rows.sort(key=lambda r: -r["observability"])
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"captured_days": ndays,
                       "caveat": "late-July window; optimistic for monsoon basins, "
                                 "pessimistic for Mediterranean winter basins. Ranks "
                                 "candidates, never accepts or rejects them.",
                       "candidates": rows}, fh, indent=1)
        print(f"\nwrote {args.out}")
    print(f"\ntotal baseline cost if all screened regions were built: "
          f"{sum(r['baseline_gb'] for r in rows):.0f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
