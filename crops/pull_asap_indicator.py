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


MANIFEST = CACHE / "_fetched_for.json"


def _manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def _save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")


def newest_dekad_in(path: Path):
    """The last date in a cached CSV, or None if it holds no rows.

    None is NOT an error. A country with no crop area inside a growing
    cycle legitimately returns a header and nothing else, which is why
    size was never the freshness test.
    """
    best = None
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            fh.readline()                      # header
            for line in fh:
                parts = line.split(",")
                if len(parts) > 10:
                    d = parts[10].strip()
                    if d and (best is None or d > best):
                        best = d
    except OSError:
        return None
    return best


def probe_newest(indicator: str = "zFPARc"):
    """ASAP's newest PUBLISHED dekad, or None if the probe fails.

    None means unknown, and unknown must not be treated as "nothing new".
    Callers fall back to skipping rather than to a 30 MB re-download on a
    guess.
    """
    import datetime as _dt
    today = _dt.date.today()
    cands = []
    y, m = today.year, today.month
    for _ in range(4):
        for day in (21, 11, 1):
            cands.append(_dt.date(y, m, day))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    for d in sorted([c for c in cands if c <= today], reverse=True):
        url = (f"https://agricultural-production-hotspots.ec.europa.eu"
               f"/getIndicatorsInfo.php?dekad={d:%Y%m%d}"
               f"&indicator_name={indicator}")
        pr = subprocess.run(["curl", "-sS", "--max-time", "30", url],
                            capture_output=True, text=True)
        if pr.returncode != 0:
            return None
        body = (pr.stdout or "").strip()
        if body.startswith("{"):
            return f"{d:%Y%m%d}"
        if not body.startswith("["):
            return None
    return None


def fetch_one(slug: str, spec: dict, country_id: int, name: str,
              target: str = None, manifest: dict = None) -> str:
    """Return 'skip', 'ok' or 'fail' for one country and one indicator.

    PRESENCE USED TO MEAN DONE, and that was right for a one-shot
    backfill and wrong for a refresh. Every file exists after the first
    run, so the puller skipped all 168 and reported success while
    fetching nothing: the probe would correctly detect a new dekad, the
    puller would fetch none of it, and the build would rebuild the old
    payload and look healthy. /crops could not advance.

    Now presence means done only for the dekad we already hold. The
    export returns the FULL series every time, so a refetch is a
    whole-file replace rather than an append.

    Two properties kept from the old rule, both load-bearing:

      An EMPTY file is legitimate, so it cannot be the refetch trigger.
      It has no dates to compare, so the manifest records which target
      it was fetched for and it is skipped until the target moves.

      A FAILED refetch must never destroy the good file we hold. The
      download goes to .partial and is renamed only after the header
      check passes, so a failure leaves the previous dekad in place.
    """
    out = CACHE / f"{slug}_{country_id}.csv"
    key = f"{slug}_{country_id}"
    manifest = manifest if manifest is not None else {}

    if out.exists():
        if target is None:
            return "skip"                      # probe failed: do not guess
        if manifest.get(key) == target:
            return "skip"                      # already fetched for this one
        have = newest_dekad_in(out)
        if have is not None and have >= target:
            manifest[key] = target
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

    # SHRINKAGE REFUSED, adopted from heat's safe_write.py 2026-08-13.
    # The header check above catches an HTML error page and an empty
    # body. It does NOT catch a well-formed CSV with rows missing, and
    # that is the failure that does the damage: heat truncated
    # Nottingham to 222 rows of a 28,714-row record, which is 0.8% and
    # sails through any emptiness test.
    #
    # This export returns the FULL series every time, so row count only
    # grows. A decrease means a partial response or a mask revision, and
    # both deserve a human rather than a silent overwrite of good data.
    def _rows(f):
        with f.open(encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh) - 1
    new_rows = _rows(tmp)
    if out.exists():
        old_rows = _rows(out)
        if new_rows < old_rows:
            tmp.unlink(missing_ok=True)
            print(f"  FAIL {name} (id {country_id}): response has "
                  f"{new_rows:,} rows against {old_rows:,} already on "
                  f"disk. REFUSING to overwrite good data with a shorter "
                  f"file. Re-run to retry; use --allow-shrink only if a "
                  f"mask revision genuinely removed regions.", flush=True)
            return "fail"

    tmp.rename(out)
    if target:
        manifest[key] = target
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
    ap.add_argument("--dekad", default=None,
                    help="target dekad YYYYMMDD; probed from ASAP when "
                         "omitted")
    ap.add_argument("--allow-shrink", action="store_true",
                    help="accept a response with fewer rows than the "
                         "cached file. Only for a real mask revision.")
    ap.add_argument("--no-refresh", action="store_true",
                    help="old behaviour: presence alone means done")
    args = ap.parse_args()

    # The target is what "up to date" MEANS for this run. If the probe
    # fails we pass None, and fetch_one then skips anything present
    # rather than re-downloading 168 countries on a guess. Unknown is
    # not the same as "nothing new", and the expensive direction is the
    # one that must never be taken by default.
    target = None if args.no_refresh else (args.dekad or probe_newest())
    if args.no_refresh:
        print("refresh disabled: presence alone means done")
    elif target:
        print(f"target dekad {target} "
              f"({'given' if args.dekad else 'probed from ASAP'}); "
              f"files older than this will be refetched")
    else:
        print("::warning::could not determine the newest published dekad; "
              "treating every present file as current rather than "
              "re-downloading on a guess")
    manifest = _manifest()

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
            result = fetch_one(slug, spec, cid, name, target, manifest)
            counts[result] += 1
            totals[result] += 1
            # Save after every success, not once per indicator. Saving at
            # the end of the loop means a kill 29 countries in leaves 29
            # refreshed files and NO record that they were refreshed, so
            # the re-run fetches them again and the cache sits at mixed
            # dekads with nothing on disk explaining why. Measured: that
            # is exactly what a 2 minute timeout did on 2026-08-13. One
            # small write per 3 second pause costs nothing.
            if result == "ok":
                _save_manifest(manifest)
                if i < len(targets):
                    time.sleep(PAUSE_SECONDS)
        mins = (time.time() - started) / 60
        print(f"\n{slug}: done in {mins:.1f} min, {counts['ok']} fetched, "
              f"{counts['skip']} present, {counts['fail']} failed",
              flush=True)

        # An indicator that fails wholesale is a wrong id or a changed
        # endpoint, not bad luck. Stop rather than grind through four
        # more the same way.
        #
        # skip == 0 IS LOAD BEARING. Without it this reads "nothing
        # succeeded" when the truth is "nothing needed doing", which is
        # the normal state of a resumed run. Measured 2026-08-13: a
        # retry after a network drop reported zfpar 0 fetched, 167
        # present, 1 failed, and this guard called that "no data at
        # all" and stopped before sm and temp. Every retry would have
        # stopped in the same place, so the supervisor could never
        # finish the run: a livelock built out of a safety check.
        # Wholesale failure means nothing succeeded AND nothing was
        # already there.
        if counts["fail"] and counts["ok"] == 0 and counts["skip"] == 0:
            print(f"::error::{slug} produced no data at all; stopping "
                  f"before the remaining indicators", flush=True)
            return 1

    mins = (time.time() - run_started) / 60
    print(f"\nrun complete in {mins:.1f} min: {totals['ok']} fetched, "
          f"{totals['skip']} already present, {totals['fail']} failed",
          flush=True)

    if totals["fail"]:
        return 1
    _save_manifest(manifest)
    if totals["ok"] == 0:
        # Exit 3 means "nothing to do", and it is only honest when we
        # KNEW what up to date meant. Without a target we skipped
        # everything by policy rather than by comparison, and reporting
        # that as nothing-to-do is how a stalled channel looks healthy.
        if target is None and not args.no_refresh:
            print("::error::skipped everything without knowing the newest "
                  "published dekad. This is not 'nothing to do'.")
            return 1
        print("::warning::ASAP indicator cache already current for "
              f"{target}; nothing fetched")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
