"""What fires/data/full_history/ actually covers, per country.

THE DIRECTORY NAME MAKES A CLAIM MOST OF ITS FILES DO NOT SUPPORT.
ARG.json exists, holds fourteen years, and covers 36 days of each:
mid-July to mid-September, the window the weekly baseline needs. A
consumer testing os.path.exists() gets True. One counting years gets
14. Both conclude we have Argentine fire seasonality, and we do not.
Only counting days per year reveals it, and nothing prompts anyone to.

Aftereffects nearly built a LatAm seasonality claim on ARG.json on
2026-08-30 and caught it only by printing days-per-year while looking
for something else. Same family as the heat payload's
is_representative_of_europe flag, and D-227: an instrument should emit
its own coverage rather than rely on a reader thinking to check.

WHY A SIDECAR AND NOT A FIELD IN EACH FILE. The documents are
{year: {date: count}} and several readers iterate that mapping
directly, so a top-level "coverage" key would arrive at build_events
and the check_* scripts as a year whose value is not a day mapping.
The sidecar cannot break a reader that does not know about it.

WHY MEASURED NUMBERS AND NOT A LABEL. The obvious field is
coverage: "annual" | "window". It would be wrong. Day counts cluster
at 15, 36, 128 and 290, and Belgium's 290 days across twelve months is
neither a window nor a full year. A label forces a boundary that the
data does not have, so this records what was counted and lets the
consumer set its own bar.

Regenerate after ANY backfill:

    PYTHONPATH="$PWD" .venv/bin/python fires/history_coverage.py
"""
import collections
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(REPO, "fires", "data", "full_history")
# OUTSIDE full_history/, deliberately. check_map_bar.py:97,
# sweep_archive_defects.py:63 and build_full_baselines.py:337 all
# enumerate that directory, so a file added to it reads as a 98th
# country. A sidecar that breaks three readers is not a sidecar.
OUT = os.path.join(REPO, "fires", "data", "history_coverage.json")


def measure_one(path):
    """Measured extent of one country file. No verdict, no label."""
    doc = json.load(open(path))
    years = {y: v for y, v in doc.items() if isinstance(v, dict)}
    if not years:
        return {"years": 0, "median_days_per_year": 0,
                "min_days_per_year": 0, "months_present": [],
                "first_date": None, "last_date": None}
    counts = sorted(len(v) for v in years.values())
    days = [d for v in years.values() for d in v]
    return {"years": len(years),
            "median_days_per_year": counts[len(counts) // 2],
            "min_days_per_year": counts[0],
            "months_present": sorted({d[5:7] for d in days}),
            "first_date": min(days) if days else None,
            "last_date": max(days) if days else None}


def measure_all():
    out = {}
    for f in sorted(os.listdir(HIST)):
        if not f.endswith(".json") or f.startswith("_"):
            continue
        out[f[:-5]] = measure_one(os.path.join(HIST, f))
    return out


def main():
    cov = measure_all()
    doc = {
        "_what": ("Measured coverage of each file in this directory. The "
                  "directory name says full_history; most files hold a "
                  "seasonal window. Read median_days_per_year before "
                  "making any claim about a country's SEASON, as opposed "
                  "to its current week, which every file supports."),
        "_regenerate": "PYTHONPATH=. python fires/history_coverage.py",
        "_derived": ("Computed from the files themselves, so it cannot "
                     "drift from them. Rerun after any backfill."),
        "countries": cov,
    }
    json.dump(doc, open(OUT, "w"), indent=1, sort_keys=True)

    dist = collections.Counter(c["median_days_per_year"]
                               for c in cov.values())
    print(f"wrote {os.path.relpath(OUT, REPO)} for {len(cov)} countries")
    print("  median days/year -> countries:")
    for days, n in sorted(dist.items()):
        print(f"    {days:>4} days: {n:>3}")
    thin = sorted(k for k, v in cov.items()
                  if v["median_days_per_year"] < 300)
    print(f"  countries that CANNOT support a seasonality claim: "
          f"{len(thin)}")
    print(f"    {' '.join(thin)}")


if __name__ == "__main__":
    main()
