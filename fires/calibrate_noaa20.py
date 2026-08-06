"""Derive the SNPP-equivalent scale factor for VIIRS NOAA-20.

WHY THIS EXISTS, AND WHY IT IS URGENT RATHER THAN NICE.

Suomi NPP data ceases on 2026-11-01 at 13:00 UTC. NOAA's cessation
notice directs users to NOAA-21 as primary and NOAA-20 as secondary.
Every fetcher in this channel pulls VIIRS_SNPP_NRT and the whole
fourteen-year baseline is VIIRS_SNPP_SP, so this is an end-of-life
migration with a hard date, not a contingency.

The same factor also fills the outage days SNPP keeps producing. Its
defect rate has gone from 1.4 days a year in 2012-2019 to 9.2 in
2022-2025, 26 days in 2024 alone, and NASA's outage log attributes them
to GPS anomalies, L0 data gaps and DMU hardware failures on a spacecraft
fifteen years into a five-year design life.

WHAT A SCALE FACTOR CAN AND CANNOT DO. It converts a NOAA-20 count into
an SNPP-equivalent count so a filled day can be compared against an SNPP
baseline. It does NOT make the two records interchangeable: NOAA-20
launched in late 2017, so its own history is about eight years against
SNPP's fourteen, and a rank-on-record computed from it means something
different. That is a separate decision.

METHOD, and every step of it exists because the first attempt got it
wrong.

  1. Sample across biomes, not just the big burners. The ratio could
     plausibly vary with fire size, canopy or latitude, and the only way
     to know is to measure countries that differ.

  2. EXCLUDE KNOWN-DEFECTIVE SNPP DATES. The first attempt included
     2021-08-03, which is itself a partial SNPP day, and it dragged the
     pooled ratio from 1.003 to 0.949 and the spread from 12% to 20%. A
     calibration set contaminated by the defect it is meant to work
     around is the easiest mistake here.

  3. Detect contamination that the register has not yet caught, by the
     same median-ratio-per-date test used to find the register's
     entries. A date where most countries read low against NOAA-20 is a
     bad SNPP day, not a real signal.

  4. Report the SPREAD, not just the central value. A filled day carries
     its own error and that error belongs in the payload, per D-051: a
     qualifier is a property of the number and has to survive the number
     being quoted alone.
"""
from __future__ import annotations

import io
import json
import os
import statistics as st
import sys
import urllib.request
from datetime import date, timedelta

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.path.join(REPO, "fires", "data", "countries.geo.json")
DEFECTS = os.path.join(REPO, "fires", "data", "archive_defects.json")
OUT = os.path.join(REPO, "fires", "data", "noaa20_calibration.json")
KEY = open(os.path.expanduser("~/.firms_map_key")).read().strip()

# Spread across biome and fire regime, not ranked by volume. A factor
# derived only from savanna would not be known to hold in boreal forest.
COUNTRIES = {
    "AGO": "southern African savanna",
    "COD": "central African savanna",
    "BRA": "tropical forest and cerrado",
    "BOL": "tropical forest",
    "CAN": "boreal forest",
    "RUS": "boreal forest",
    "USA": "temperate mixed",
    "AUS": "northern savanna and eucalypt",
    "IDN": "peatland and tropical forest",
    "IND": "agricultural and dry forest",
    "GRC": "mediterranean",
    "ESP": "mediterranean",
    "ZAF": "fynbos and grassland",
    "MEX": "dry tropical forest",
}

# Dates across the seasonal cycle and the overlap years, so the factor is
# not derived from one month of one hemisphere's fire season.
DATES = []
for year in range(2019, 2026):
    for mmdd in ("02-15", "05-20", "08-03", "10-12"):
        DATES.append(f"{year}-{mmdd}")

MIN_COUNT = 80          # below this the ratio is dominated by counting noise
CONTAM_RATIO = 0.8      # a date whose median ratio falls under this is a
                        # bad SNPP day, not a signal


def load_boxes():
    geo = json.load(open(GEO))
    out = {}
    for f in geo["features"]:
        if f["id"] not in COUNTRIES:
            continue
        g = f["geometry"]
        ps = ([g["coordinates"]] if g["type"] == "Polygon"
              else g["coordinates"])
        lon = [p[0] for poly in ps for p in poly[0]]
        lat = [p[1] for poly in ps for p in poly[0]]
        # Antimeridian countries would request a global strip; skip rather
        # than complicate, since the sample has boreal cover from Canada.
        if max(lon) - min(lon) > 340:
            continue
        out[f["id"]] = f"{min(lon)},{min(lat)},{max(lon)},{max(lat)}"
    return out


def count(sensor: str, box: str, day: str):
    url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/"
           f"{sensor}/{box}/1/{day}")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            df = pd.read_csv(io.StringIO(r.read().decode("utf-8", "replace")))
    except Exception:
        return None
    if len(df) and "confidence" in df.columns:
        df = df[~df["confidence"].astype(str).str.lower().isin(["l", "low"])]
    return len(df)


def main() -> int:
    try:
        d = json.load(open(DEFECTS))
        defective = set(d.get("thin", [])) | set(d.get("absent", []))
    except (OSError, ValueError):
        defective = set()
    boxes = load_boxes()
    dates = [x for x in DATES if x not in defective]
    print(f"{len(boxes)} countries x {len(dates)} dates "
          f"({len(DATES) - len(dates)} skipped as known-defective)",
          flush=True)

    obs = []          # (iso, date, snpp, noaa20, ratio)
    for iso, box in boxes.items():
        for day in dates:
            a = count("VIIRS_SNPP_SP", box, day)
            b = count("VIIRS_NOAA20_SP", box, day)
            if not a or not b or a < MIN_COUNT or b < MIN_COUNT:
                continue
            obs.append((iso, day, a, b, a / b))
        print(f"  {iso}: {sum(1 for o in obs if o[0] == iso)} usable days",
              flush=True)

    # Contamination the register has not caught yet.
    by_date = {}
    for iso, day, a, b, r in obs:
        by_date.setdefault(day, []).append(r)
    bad_dates = {d for d, rs in by_date.items()
                 if len(rs) >= 3 and st.median(rs) < CONTAM_RATIO}
    if bad_dates:
        print(f"\nexcluded as likely partial SNPP days, not in the register "
              f"yet: {', '.join(sorted(bad_dates))}", file=sys.stderr)
    clean = [o for o in obs if o[1] not in bad_dates]

    if len(clean) < 20:
        print(f"only {len(clean)} usable observations; refusing to publish "
              f"a factor from a sample this thin", file=sys.stderr)
        return 1

    ratios = [o[4] for o in clean]
    mean, sd = st.mean(ratios), st.pstdev(ratios)
    per_country = {}
    for iso in boxes:
        rs = [o[4] for o in clean if o[0] == iso]
        if len(rs) >= 3:
            per_country[iso] = {"biome": COUNTRIES[iso],
                                "mean": round(st.mean(rs), 4),
                                "cv": round(st.pstdev(rs) / st.mean(rs), 3),
                                "n": len(rs)}

    print(f"\n{'country':<8}{'biome':<32}{'ratio':>8}{'cv':>7}{'n':>5}")
    for iso, v in sorted(per_country.items(), key=lambda kv: kv[1]["mean"]):
        print(f"{iso:<8}{v['biome'][:30]:<32}{v['mean']:>8.3f}"
              f"{v['cv']:>7.2f}{v['n']:>5}")
    spread = [v["mean"] for v in per_country.values()]
    print(f"\nPOOLED  {mean:.4f}  sd {sd:.4f}  cv {sd/mean:.3f}  n={len(clean)}")
    print(f"per-country means range {min(spread):.3f} to {max(spread):.3f}")

    doc = {
        "_readme": [
            "SNPP-equivalent scale factor for VIIRS NOAA-20, derived from",
            "the 2018-2025 overlap. A NOAA-20 count multiplied by",
            "scale_factor is comparable with an SNPP count.",
            "",
            "WHY IT EXISTS: Suomi NPP data ceases 2026-11-01 13:00 UTC, and",
            "SNPP outages are already frequent enough to need filling now.",
            "",
            "WHAT IT DOES NOT DO: it does not make the two records",
            "interchangeable. NOAA-20 launched late 2017, so a",
            "rank-on-record from it spans eight years against SNPP's",
            "fourteen and means something different.",
            "",
            "scale_cv is the spread on a SINGLE filled day, one sigma. It",
            "travels with any filled datum, per D-051: a qualifier is a",
            "property of the number and must survive being quoted alone.",
            "",
            "Known-defective SNPP dates are excluded from the calibration.",
            "Including one dragged the first attempt from 1.003 to 0.949",
            "and the spread from 12% to 20%.",
        ],
        "derived": date.today().isoformat(),
        "from_sensor": "VIIRS_NOAA20",
        "to_sensor": "VIIRS_SNPP",
        "scale_factor": round(mean, 4),
        "scale_sd": round(sd, 4),
        "scale_cv": round(sd / mean, 3),
        "n_observations": len(clean),
        "n_countries": len(per_country),
        "date_range": [min(dates), max(dates)],
        "excluded_dates": sorted(bad_dates),
        "per_country": per_country,
    }
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
