"""Pull HURDAT2 for both North American basins and derive seasonal ACE.

Why this exists: we answered a question about El Nino and hurricanes from
memory, and got a supporting example wrong (Andrew 1992, which was not an
El Nino season at ASO). This makes the claim reproducible.

Scope, stated up front because it is the thing most likely to be
over-read downstream:

  - We derive BASIN ACTIVITY (ACE, storm counts). We do NOT derive US
    landfall. Landfall from HURDAT2 needs a coastline test, and a
    bounding box would produce a confident wrong number. NOAA publishes
    a separate continental-US landfall record; use that if landfall is
    the claim.
  - ACE follows the NOAA convention: sum of v^2/1e4 over the four
    synoptic hours, counting only observations at >= 34 kt while the
    system is tropical (status TS or HU). Subtropical (SS) is excluded.
    We also carry the SS-inclusive figure so the choice is visible
    rather than buried.
  - The Atlantic record starts 1851 and NE Pacific 1949, but neither is
    homogeneous that far back. Aircraft reconnaissance begins ~1944 and
    continuous satellite coverage ~1966. Pre-satellite seasons miss
    storms that stayed at sea, which biases ACE and counts DOWN. Any
    trend statement must start at 1966 or later. We record the full
    series and mark the reliable window rather than silently truncating.
"""
import csv, json, re, sys, urllib.request
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".fetch_cache" / "hurdat"
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://www.nhc.noaa.gov/data/hurdat/"
# Both basins from the same 2026-02-27 release, so the two series end on
# the same season. An asymmetric pair here would be a silent trap: a
# reader comparing basins would be comparing different record lengths.
FILES = {
    "atlantic":   "hurdat2-1851-2025-02272026.txt",
    "east_pacific": "hurdat2-nepac-1949-2025-02272026.txt",
}
SATELLITE_ERA = 1966
SYNOPTIC = {"0000", "0600", "1200", "1800"}
TROPICAL = {"TS", "HU"}          # NOAA ACE convention
TROPICAL_PLUS_SS = {"TS", "HU", "SS"}


def get(fname):
    dest = CACHE / fname
    if dest.exists() and dest.stat().st_size > 100_000:
        print(f"  cached  {fname} ({dest.stat().st_size/1e6:.1f} MB)")
        return dest.read_text()
    print(f"  fetching {fname} ...")
    with urllib.request.urlopen(BASE + fname, timeout=120) as r:
        txt = r.read().decode("utf-8", "replace")
    dest.write_text(txt)
    print(f"  saved   {fname} ({len(txt)/1e6:.1f} MB)")
    return txt


HDR = re.compile(r"^(AL|EP|CP)(\d{2})(\d{4}),")


def parse(txt, basin_label):
    """Walk HURDAT2. Header line names a storm and says how many rows follow."""
    lines = [l.rstrip("\n") for l in txt.splitlines() if l.strip()]
    storms, i, malformed = [], 0, 0
    while i < len(lines):
        m = HDR.match(lines[i])
        if not m:
            malformed += 1
            i += 1
            continue
        parts = [p.strip() for p in lines[i].split(",")]
        code, name, nrows = parts[0], parts[1], int(parts[2])
        year = int(m.group(3))
        obs = []
        for j in range(i + 1, min(i + 1 + nrows, len(lines))):
            f = [p.strip() for p in lines[j].split(",")]
            if len(f) < 7:
                malformed += 1
                continue
            try:
                wind = int(f[6])
            except ValueError:
                continue
            if wind < 0:          # HURDAT2 uses -99 for missing
                continue
            obs.append({"date": f[0], "hour": f[1], "status": f[3], "wind": wind})
        storms.append({"code": code, "name": name, "year": year,
                       "basin": basin_label, "obs": obs})
        i += 1 + nrows
    return storms, malformed


def ace_of(storm, statuses):
    """ACE in 10^4 kt^2, the conventional unit."""
    tot = 0.0
    for o in storm["obs"]:
        if o["hour"] not in SYNOPTIC:
            continue
        if o["status"] not in statuses:
            continue
        if o["wind"] < 34:
            continue
        tot += o["wind"] ** 2
    return tot / 1e4


def peak(storm):
    return max((o["wind"] for o in storm["obs"]), default=0)


def season_stats(storms):
    by_year = defaultdict(list)
    for s in storms:
        by_year[s["year"]].append(s)
    out = {}
    for y, ss in sorted(by_year.items()):
        named = [s for s in ss if peak(s) >= 34]
        hurr = [s for s in ss if peak(s) >= 64]
        major = [s for s in ss if peak(s) >= 96]     # Cat 3 = 96 kt
        out[y] = {
            "ace": round(sum(ace_of(s, TROPICAL) for s in ss), 1),
            "ace_incl_subtropical": round(sum(ace_of(s, TROPICAL_PLUS_SS) for s in ss), 1),
            "named_storms": len(named),
            "hurricanes": len(hurr),
            "major_hurricanes": len(major),
        }
    return out


def load_oni():
    p = ROOT / "data" / "oni_full_history.csv"
    o = defaultdict(dict)
    with open(p) as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            o[int(r["year"])][r["season"].upper()] = float(r["oni"])
    return o


def main():
    print("=== HURDAT2 pull ===")
    basins = {}
    for label, fname in FILES.items():
        txt = get(fname)
        storms, malformed = parse(txt, label)
        yrs = sorted({s["year"] for s in storms})
        print(f"  {label}: {len(storms)} storms, {yrs[0]}-{yrs[-1]}, "
              f"{malformed} unparsed lines")
        basins[label] = {"stats": season_stats(storms),
                         "source_file": fname,
                         "malformed_lines": malformed,
                         "n_storms": len(storms)}

    oni = load_oni()
    payload = {
        "generated": "2026-09-03",
        "source": "NOAA NHC HURDAT2, " + BASE,
        "ace_definition": ("sum of v^2/1e4 over 0000/0600/1200/1800 UTC "
                           "observations at >= 34 kt while status is TS or HU; "
                           "subtropical excluded (NOAA convention). "
                           "Unit: 10^4 kt^2."),
        "not_derived": ("US landfall is not derived FROM THIS FILE. HURDAT2 "
                        "marks landfall generically; isolating continental-US "
                        "landfall from track positions needs a coastline test, "
                        "and a bounding box would give a confident wrong "
                        "number. We now hold AOML's curated continental-US "
                        "landfall record separately, at "
                        "data/us_hurricane_landfalls.json, built by "
                        "scripts/pull_us_landfalls.py. Use that for landfall, "
                        "and note it is a COUNT, not a loss series."),
        "homogeneity_warning": (f"Continuous satellite coverage from ~{SATELLITE_ERA}. "
                                "Earlier seasons undercount storms that stayed at "
                                "sea, biasing ACE and counts DOWN. Do not state a "
                                "trend across the pre-satellite boundary."),
        "reliable_from": SATELLITE_ERA,
        "oni_season_used": "ASO (Aug-Sep-Oct), the peak of both basins' seasons",
        "basins": {},
    }
    for label, b in basins.items():
        rows = []
        for y, st in sorted(b["stats"].items()):
            rows.append({"year": y, **st, "oni_aso": oni.get(y, {}).get("ASO")})
        payload["basins"][label] = {
            "source_file": b["source_file"],
            "record_start": rows[0]["year"],
            "record_end": rows[-1]["year"],
            "n_storms": b["n_storms"],
            "seasons": rows,
        }

    # --- refuse to write a payload that cannot support the comparison ---
    faults = []
    ends = {l: payload["basins"][l]["record_end"] for l in FILES}
    if len(set(ends.values())) != 1:
        faults.append(f"basins end on different seasons {ends}; a cross-basin "
                      "comparison would compare different record lengths")
    for l in FILES:
        b = payload["basins"][l]
        withoni = [r for r in b["seasons"] if r["oni_aso"] is not None]
        if len(withoni) < 60:
            faults.append(f"{l}: only {len(withoni)} seasons carry an ONI value")
        if any(r["ace"] < 0 for r in b["seasons"]):
            faults.append(f"{l}: negative ACE")
    if faults:
        sys.exit("REFUSING TO WRITE:\n  - " + "\n  - ".join(faults))

    dest = ROOT / "data" / "hurricanes.json"
    dest.write_text(json.dumps(payload, indent=1))
    print(f"\n  wrote {dest.relative_to(ROOT)}")
    for l in FILES:
        b = payload["basins"][l]
        n = len([r for r in b["seasons"] if r["oni_aso"] is not None])
        print(f"    {l}: {b['record_start']}-{b['record_end']}, "
              f"{len(b['seasons'])} seasons, {n} with ONI")


if __name__ == "__main__":
    main()
