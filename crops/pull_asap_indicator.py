"""Pull ASAP per-unit area-averaged indicator time series, one country
and one indicator at a time.

This is the series section 8 of FEASIBILITY.md needs: numeric,
crop-masked and season-masked at source, per GAUL1 unit, per dekad,
back to 2001. It replaces the unit-count proxy, which fails on
countries with few admin units and so fails exactly where the signal is
strongest.

Why more than one indicator. Every qualified pair currently rests on a
single instrument, so a bad-looking season cannot be separated from a
sensor artifact, and water stress cannot be separated from heat stress.
WSI and SPI-3 are the water-balance and rainfall instruments behind the
same signal; temperature is the other failure mode. Corroboration
across instruments is what makes a number citable rather than plausible.

JRC serves one country and one indicator per request and asks that bulk
users contact them. This script is therefore deliberately polite:
strictly sequential, one connection, a pause between calls, and fully
resumable so an interrupted run never refetches what it already has.
Never run two copies at once.

Usage:
    .venv/bin/python crops/pull_asap_indicator.py                 # priority set, zFPARc
    .venv/bin/python crops/pull_asap_indicator.py --all           # all countries
    .venv/bin/python crops/pull_asap_indicator.py --all --batch   # all countries, the 5 corroborating indicators
    .venv/bin/python crops/pull_asap_indicator.py --all --indicator wsi_crop_growing

Exit codes follow the convention agreed with platform:
    0  fetched something, wrote files
    3  nothing to do, everything already present
    1  a real failure
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = ("https://agricultural-production-hotspots.ec.europa.eu"
        "/export/rum/export.php")
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "asap_indicator"

# The four ids per indicator are internal to ASAP and are not in the
# public manual; they were read from the download page's own catalogue
# on 2026-07-28. Passing readable names alone returns HTTP 400.
#
# Every entry below is the "Crop during growing cycle" class, meaning
# crop-masked AND restricted to the growing season at source. That is
# what removes the denominator problem the unit-count proxy had.
INDICATORS = {
    # The spine. ASAP's own warning classification is built from this.
    "zfparc_crop_growing": {
        "variable_name": "FPAR Cumulated - zscore",
        "class_name": "Crop during growing cycle",
        "variable_id": "240", "class_id": "1",
        "classesset_id": "1", "sensor_id": "3",
    },
    # Water balance: the drought instrument proper.
    "wsi_crop_growing": {
        "variable_name": "Water Satisfaction Index (WSI)",
        "class_name": "Crop during growing cycle",
        "variable_id": "160", "class_id": "1",
        "classesset_id": "1", "sensor_id": "5",
    },
    # Rainfall anomaly over 3 months.
    "spi3_crop_growing": {
        "variable_name": "SPI - 3 months",
        "class_name": "Crop during growing cycle",
        "variable_id": "40", "class_id": "1",
        "classesset_id": "1", "sensor_id": "4",
    },
    # Instantaneous FPAR anomaly, to sit alongside the cumulated one.
    "zfpar_crop_growing": {
        "variable_name": "FPAR - zscore",
        "class_name": "Crop during growing cycle",
        "variable_id": "220", "class_id": "1",
        "classesset_id": "1", "sensor_id": "3",
    },
    "sm_crop_growing": {
        "variable_name": "Soil Moisture (gapfilled historical time series)",
        "class_name": "Crop during growing cycle",
        "variable_id": "190", "class_id": "1",
        "classesset_id": "1", "sensor_id": "7",
    },
    # Heat stress is a different failure mode from water stress, and
    # FPAR alone conflates them.
    "temp_crop_growing": {
        "variable_name": "Temperature",
        "class_name": "Crop during growing cycle",
        "variable_id": "140", "class_id": "1",
        "classesset_id": "1", "sensor_id": "4",
    },
}

# Approved 2026-07-28: the five corroborating instruments, roughly four
# hours across all countries. zfparc is excluded because it is already
# in the cache.
BATCH = ["wsi_crop_growing", "spi3_crop_growing", "zfpar_crop_growing",
         "sm_crop_growing", "temp_crop_growing"]

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


def fetch_one(slug: str, spec: dict, country_id: int, name: str) -> str:
    """Return 'skip', 'ok' or 'fail' for one country and one indicator."""
    out = CACHE / f"{slug}_{country_id}.csv"
    # Presence alone means done. Size is not the test: a country with no
    # crop area inside a growing cycle legitimately returns a header and
    # nothing else, and a size gate would refetch it on every run
    # forever.
    if out.exists():
        return "skip"

    cmd = ["curl", "-sS", "--max-time", str(TIMEOUT_SECONDS), "-G", BASE,
           "--data-urlencode", "gaul_level=1",
           "--data-urlencode", f"country_id={country_id}"]
    for k, v in spec.items():
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
    note = "  (no crop units)" if rows == 0 else ""
    print(f"  ok   {name:28s} {rows:7,d} rows  "
          f"{out.stat().st_size / 1e6:5.1f} MB{note}", flush=True)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every ASAP country, not just the priority set")
    ap.add_argument("--indicator", default="zfparc_crop_growing",
                    choices=sorted(INDICATORS),
                    help="a single indicator slug")
    ap.add_argument("--batch", action="store_true",
                    help="the five corroborating indicators, in order")
    args = ap.parse_args()

    if args.all:
        ref = HERE / "asap_countries.json"
        catalogue = json.loads(ref.read_text(encoding="utf-8"))["countries"]
        targets = sorted(((int(k), v) for k, v in catalogue.items()),
                         key=lambda kv: kv[1])
    else:
        targets = sorted(PRIORITY.items(), key=lambda kv: kv[1])

    slugs = BATCH if args.batch else [args.indicator]
    CACHE.mkdir(parents=True, exist_ok=True)

    totals = {"ok": 0, "skip": 0, "fail": 0}
    run_started = time.time()

    for slug_no, slug in enumerate(slugs, 1):
        spec = INDICATORS[slug]
        print(f"\n{'=' * 70}")
        print(f"[indicator {slug_no}/{len(slugs)}] {slug}")
        print(f"  {spec['variable_name']} / {spec['class_name']}")
        print(f"  {len(targets)} countries, sequential, "
              f"{PAUSE_SECONDS}s apart")
        print(f"{'=' * 70}", flush=True)

        counts = {"ok": 0, "skip": 0, "fail": 0}
        started = time.time()
        for i, (cid, name) in enumerate(targets, 1):
            print(f"[{i}/{len(targets)}] {name}", flush=True)
            result = fetch_one(slug, spec, cid, name)
            counts[result] += 1
            totals[result] += 1
            if result == "ok" and i < len(targets):
                time.sleep(PAUSE_SECONDS)

        mins = (time.time() - started) / 60
        print(f"\n{slug}: done in {mins:.1f} min, {counts['ok']} fetched, "
              f"{counts['skip']} present, {counts['fail']} failed",
              flush=True)

        # An indicator that fails wholesale is a wrong id or a changed
        # endpoint, not bad luck. Stop rather than grind through four
        # more the same way.
        if counts["fail"] and counts["ok"] == 0:
            print(f"::error::{slug} produced no data at all; stopping "
                  f"before the remaining indicators", flush=True)
            return 1

    mins = (time.time() - run_started) / 60
    print(f"\nrun complete in {mins:.1f} min: {totals['ok']} fetched, "
          f"{totals['skip']} already present, {totals['fail']} failed",
          flush=True)

    if totals["fail"]:
        return 1
    if totals["ok"] == 0:
        print("::warning::ASAP indicator cache already complete; "
              "nothing fetched")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
