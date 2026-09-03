"""Continental-US hurricane landfalls, 1851-2025, from AOML's curated table.

Written after telling aftereffects that a landfall count was "a separate
source and a real pull". The source turned out to be a machine-readable
table, so the pull is cheap. Correcting that is the point of this file.

What this is: AOML/HRD's own chronological list of continental-US
hurricane landfalls. It is CURATED, not derived by us from track data,
which is exactly why we use it. Deriving landfall from HURDAT2 positions
would need a coastline test, and a bounding box would produce a
confident wrong number.

Columns, per the source's own legend:
  Year | Month | States affected and category by state |
  Highest Saffir-Simpson US category | Central pressure (mb) |
  Max wind (kt) | Name

Two limits that must travel with any count from this file:

  - It counts HURRICANES AT US LANDFALL. Tropical storms are excluded,
    and so is any hurricane that stayed offshore however close. It is
    not a damage series and must never be used as one.
  - Landfall counts are small numbers. The Atlantic basin signal is
    computed on 10-16 storms a season; this is computed on 0-6 events a
    season, so the same ENSO effect has far less room to show itself.
    A null here is weak evidence, not evidence of absence.
"""
import csv, json, re, sys, urllib.request
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".fetch_cache" / "hurdat"
CACHE.mkdir(parents=True, exist_ok=True)
URL = "https://www.aoml.noaa.gov/hrd/hurdat/All_U.S._Hurricanes.html"
# Month may be a cross-month label: 1929 carries "Sp-Oc" and 1933 "Jl-Au".
# A fixed twelve-name alternation silently drops both, which is the same
# bug shape as the fires deadline cross-month window (71c543c8).
MONTH = r"[A-Za-z]{2,3}(?:-[A-Za-z]{2,3})?"

# Category is 1-5 for a hurricane landfall, but the table also carries TS
# rows (Nicole 2022 reached the continental US as a tropical storm). We
# capture TS so it can be excluded VISIBLY rather than vanishing into a
# skipped-line count.
# The name field is genuinely absent on some rows (1924), so it is optional.
ROW = re.compile(
    rf"^(1[89]\d\d|20\d\d)\s+({MONTH})\s+(.*?)\s+([1-5]|TS)\s+"
    r"(\d{3,4}|-+)\s+(\d{2,3}|-+)(?:\s+(.*))?$")

# Years the table explicitly marks as having no landfall. These are DATA,
# not parse failures: 2025 is one of them.
NONE_ROW = re.compile(r"^(1[89]\d\d|20\d\d)\s+None\s*$")


def get():
    dest = CACHE / "all_us_hurricanes.html"
    if dest.exists() and dest.stat().st_size > 50_000:
        print(f"  cached  {dest.name}")
        return dest.read_text(encoding="utf-8", errors="replace")
    print("  fetching AOML continental-US landfall table ...")
    # AOML times out on urllib's default user agent while serving curl
    # normally. Send a real one rather than treating it as a flaky host.
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=90) as r:
        txt = r.read().decode("utf-8", "replace")
    dest.write_text(txt)
    print(f"  saved   {dest.name} ({len(txt)/1e3:.0f} KB)")
    return txt


def parse(html):
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = re.sub(r"&nbsp;?", " ", txt)
    rows, zero_years, ts_excluded, skipped = [], [], [], []
    for raw in txt.splitlines():
        line = " ".join(raw.split())
        if not re.match(r"^(1[89]\d\d|20\d\d)\s", line):
            continue
        z = NONE_ROW.match(line)
        if z:
            zero_years.append(int(z.group(1)))
            continue
        m = ROW.match(line)
        if not m:
            skipped.append(line)
            continue
        y, mon, states, cat, pres, wind, name = m.groups()
        rec = {
            "year": int(y), "month": mon, "states": states.strip(" *#&"),
            "category": cat,
            "pressure_mb": None if set(pres) == {"-"} else int(pres),
            "wind_kt": None if set(wind) == {"-"} else int(wind),
            "name": (name or "").strip().strip('"') or None,
        }
        if cat == "TS":
            ts_excluded.append(rec)      # reached the US below hurricane strength
            continue
        rec["category"] = int(cat)
        rows.append(rec)
    return rows, zero_years, ts_excluded, skipped


def load_oni():
    o = defaultdict(dict)
    with open(ROOT / "data" / "oni_full_history.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            o[int(r["year"])][r["season"].upper()] = float(r["oni"])
    return o


def main():
    rows, zero_years, ts_excluded, skipped = parse(get())
    yrs = [r["year"] for r in rows]
    covered = sorted(set(yrs) | set(zero_years))
    print(f"  parsed {len(rows)} hurricane landfalls over {min(yrs)}-{max(yrs)}")
    print(f"  {len(zero_years)} years explicitly marked None (zero landfalls); "
          f"latest {max(zero_years)}")
    print(f"  {len(ts_excluded)} row(s) excluded as tropical-storm landfall: "
          + ", ".join(f"{r['name']} {r['year']}" for r in ts_excluded))
    print(f"  coverage {min(covered)}-{max(covered)}, {len(skipped)} lines skipped")
    for sk in skipped:
        print(f"    skipped: {sk[:90]}")

    oni = load_oni()
    seasons = {}
    for y in range(min(covered), max(covered) + 1):
        ev = [r for r in rows if r["year"] == y]
        seasons[y] = {
            "landfalls": len(ev),
            "major_landfalls": len([r for r in ev if r["category"] >= 3]),
            "max_category": max((r["category"] for r in ev), default=0),
            "oni_aso": oni.get(y, {}).get("ASO"),
        }

    payload = {
        "generated": "2026-09-03",
        "source": URL,
        "what_this_counts": ("hurricanes at continental-US landfall, curated by "
                             "AOML/HRD. Tropical storms excluded. Hurricanes that "
                             "stayed offshore excluded however close."),
        "not_a_damage_series": ("Counts landfalls, not losses. A single Cat 3 into "
                                "a metro area outweighs several into open coast. "
                                "Any damage statement needs a named normalised "
                                "loss series, which this is not."),
        "small_number_warning": ("0-6 events a season against 10-16 storms in the "
                                 "basin, so an ENSO effect has far less room to "
                                 "show here. A null is weak evidence, not absence."),
        "reliable_from": 1966,
        "record_start": min(covered), "record_end": max(covered),
        "zero_landfall_years": zero_years,
        "note_2025": ("2025 is present in the source and marked None: zero "
                      "continental-US hurricane landfalls. The last year with "
                      f"any landfall is {max(yrs)}. Reading the record as "
                      "ending then would understate coverage and mismatch the "
                      "HURDAT2 series, which also runs to 2025."),
        "excluded_tropical_storm_landfalls": ts_excluded,
        "n_landfalls": len(rows),
        "seasons": [{"year": y, **s} for y, s in sorted(seasons.items())],
        "events": rows,
    }

    faults = []
    if payload["record_end"] != 2025:
        faults.append(f"record ends {payload['record_end']}, expected 2025 to "
                      "match the HURDAT2 release we already hold")
    if len(rows) < 250:
        faults.append(f"only {len(rows)} landfalls parsed; the table has ~300")
    if len(skipped) > 2:
        faults.append(f"{len(skipped)} unparsed year-leading lines; every one "
                      "should be accounted for, not assumed to be a footnote")
    if faults:
        sys.exit("REFUSING TO WRITE:\n  - " + "\n  - ".join(faults))

    dest = ROOT / "data" / "us_hurricane_landfalls.json"
    dest.write_text(json.dumps(payload, indent=1))
    print(f"  wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
