"""Pull ASAP per-unit area-averaged indicator time series, one country
at a time.

This is the series section 8 of FEASIBILITY.md says the channel needs:
numeric, crop-masked and season-masked at source, per GAUL1 unit, per
dekad, back to 2001. It replaces the unit-count proxy, which fails on
countries with few admin units and so fails exactly where the signal is
strongest.

JRC serves one country and one indicator per request and asks that bulk
users contact them. This script is therefore deliberately polite:
strictly sequential, one connection, a pause between calls, and fully
resumable so an interrupted run never refetches what it already has.

Usage:
    .venv/bin/python crops/pull_asap_indicator.py [--all] [--set NAME]

Exit codes follow the convention agreed with platform:
    0  fetched something, wrote files
    3  nothing to do, everything already present
    1  a real failure
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = ("https://agricultural-production-hotspots.ec.europa.eu"
        "/export/rum/export.php")
CACHE = Path(__file__).resolve().parent / ".cache" / "asap_indicator"

# FPAR Cumulated z-score, restricted to crop area inside the growing
# cycle. This is the indicator ASAP's own warning classification is
# built from, which is why it is the one worth having as numbers.
INDICATOR = {
    "variable_name": "FPAR Cumulated - zscore",
    "class_name": "Crop during growing cycle",
    "variable_id": "240",
    "class_id": "1",
    "classesset_id": "1",
    "sensor_id": "3",
}
SLUG = "zfparc_crop_growing"

PAUSE_SECONDS = 3
TIMEOUT_SECONDS = 420

# Priority set: every country in the FEASIBILITY.md lead test, every
# country the unit-count gate wrongly dropped, and the major producers
# whose harvests reach an EU or US reader (T11).
PRIORITY = {
    208: "Australia", 138: "Malaysia", 183: "Indonesia", 101: "India",
    191: "Brazil", 166: "Argentina", 189: "Thailand", 134: "Viet Nam",
    126: "Philippines", 185: "Ethiopia", 218: "Zimbabwe", 111: "Zambia",
    163: "Kenya", 141: "South Africa", 33: "Mozambique", 148: "Malawi",
    62: "China", 5: "United States of America", 115: "Ukraine",
    197: "France", 145: "Russian Federation", 188: "Kazakhstan",
    199: "Pakistan", 20: "Bangladesh", 81: "Myanmar", 155: "Nigeria",
    29: "Sudan", 79: "Egypt", 49: "Turkiye", 63: "Mexico",
    192: "Colombia", 206: "Peru", 91: "Uruguay", 178: "Paraguay",
    132: "Cambodia", 140: "Sri Lanka", 51: "Madagascar", 80: "Niger",
    59: "Mali", 156: "Somalia",
}


def fetch_one(country_id: int, name: str) -> str:
    """Return 'skip', 'ok' or 'fail' for one country."""
    out = CACHE / f"{SLUG}_{country_id}.csv"
    if out.exists() and out.stat().st_size > 1000:
        return "skip"

    cmd = ["curl", "-sS", "--max-time", str(TIMEOUT_SECONDS), "-G", BASE,
           "--data-urlencode", "gaul_level=1",
           "--data-urlencode", f"country_id={country_id}"]
    for k, v in INDICATOR.items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    tmp = out.with_suffix(".partial")
    cmd += ["-o", str(tmp), "-w", "%{http_code}"]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    code = (proc.stdout or "").strip()
    if proc.returncode != 0 or code != "200":
        tmp.unlink(missing_ok=True)
        print(f"  FAIL {name} (id {country_id}): "
              f"curl rc={proc.returncode} http={code}", flush=True)
        return "fail"

    # A valid response is a CSV with the documented header. Anything
    # else (an HTML error page, an empty body) must not be cached as if
    # it were data; that is how a hole gets written into a baseline.
    with tmp.open(encoding="utf-8", errors="replace") as fh:
        header = fh.readline().strip()
    if not header.startswith("country_id,country_name,region_id"):
        tmp.unlink(missing_ok=True)
        print(f"  FAIL {name} (id {country_id}): unexpected header "
              f"{header[:60]!r}", flush=True)
        return "fail"

    tmp.rename(out)
    rows = sum(1 for _ in out.open(encoding="utf-8", errors="replace")) - 1
    print(f"  ok   {name:28s} {rows:7,d} rows  "
          f"{out.stat().st_size / 1e6:5.1f} MB", flush=True)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every ASAP country, not just the priority set")
    args = ap.parse_args()

    if args.all:
        print("the --all path needs the full country list from "
              "download.php; not wired yet, use the priority set")
        return 1

    CACHE.mkdir(parents=True, exist_ok=True)
    targets = sorted(PRIORITY.items(), key=lambda kv: kv[1])
    print(f"ASAP indicator pull: {INDICATOR['variable_name']} "
          f"/ {INDICATOR['class_name']}")
    print(f"{len(targets)} countries, sequential, {PAUSE_SECONDS}s apart")
    print(f"cache: {CACHE}\n", flush=True)

    counts = {"ok": 0, "skip": 0, "fail": 0}
    started = time.time()
    for i, (cid, name) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {name}", flush=True)
        result = fetch_one(cid, name)
        counts[result] += 1
        if result == "ok" and i < len(targets):
            time.sleep(PAUSE_SECONDS)

    mins = (time.time() - started) / 60
    print(f"\ndone in {mins:.1f} min: {counts['ok']} fetched, "
          f"{counts['skip']} already present, {counts['fail']} failed",
          flush=True)

    if counts["fail"]:
        return 1
    if counts["ok"] == 0:
        print("::warning::ASAP indicator cache already complete; "
              "nothing fetched")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
