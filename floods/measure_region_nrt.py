"""Measure a region's CURRENT flood extent with the baseline's own code, against NASA's NRT archive.

fetch_mcdwd_baseline.py counts MCDWD 3-day flood pixels per day for a region box and window; its
archive (LAADS MCDWD_L3) lags about two months, so for the current season this points the SAME
counting code at the near-real-time archive (nrt3 MCDWD_L3_NRT), whose listings need the Earthdata
bearer token. Output is in the baseline's own record format, so emit_region_payload.py compares
like with like. Resumable: rerun to fill missing days.

Run:  .venv/bin/python floods/measure_region_nrt.py --region somalia_shabelle_juba --start 10-22 --end 11-11 \
          --year 2026 --out floods/data/mcdwd_current_somalia_shabelle_juba_2026_10-22_11-11.jsonl
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_mcdwd_baseline as M

NRT = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3_NRT"


def nrt_listing(year, doy):
    key = (year, doy)
    if key in M._listing_cache:
        return M._listing_cache[key]
    req = urllib.request.Request(f"{NRT}/{year}/{doy:03d}.json",
                                 headers={"Authorization": f"Bearer {M.token()}", "User-Agent": "TLS-floods/0.1"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    data = data["content"] if isinstance(data, dict) else data
    idx = {e["name"].split(".")[2]: e["name"] for e in data if len(e["name"].split(".")) > 2}
    M._listing_cache[key] = idx
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--start", required=True, help="MM-DD")
    ap.add_argument("--end", required=True, help="MM-DD")
    ap.add_argument("--year", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    M.ARCHIVE = NRT
    M.listing = nrt_listing
    sys.argv = ["fetch_mcdwd_baseline", "--region", a.region, "--start", a.start, "--end", a.end,
                "--years", f"{a.year}-{a.year}", "--workers", "3", "--out", a.out]
    M.main()


if __name__ == "__main__":
    main()
