"""Gate the AEMET re-source before it replaces ECA&D in the payload.

Two independent checks, because the re-source can fail in two ways and only
one of them is visible in the numbers.

  EQUIVALENCE  Do AEMET and ECA&D agree on the days they share? They are the
               same thermometer, so anything below 100% means the station
               match is wrong, as it was for Murcia at 3/149.

  COVERAGE     Does AEMET have the days at all? A failed request window drops
               a half-year and leaves a plausible shorter series. Seville lost
               April to June that way and read as a quiet summer.

A city passes only on both. Equivalence without coverage is the Seville error;
coverage without equivalence is the Murcia error.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "heat" / ".cache"

MIN_IDENTICAL = 0.999      # same instrument: anything less is a wrong station
MIN_COVERAGE = 0.98        # of the days ECA&D has for the same span


def eca_series(city, staid):
    out = {}
    with open(CACHE / f"h_{city}.txt", encoding="latin-1") as fh:
        for line in fh:
            m = re.match(rf"\s*{staid},\s*\d+,\s*(\d{{4}})(\d{{2}})(\d{{2}}),"
                         rf"\s*(-?\d+),\s*(\d)", line)
            if m and int(m[5]) != 9:
                out[f"{m[1]}-{m[2]}-{m[3]}"] = int(m[4]) / 10.0
    return out


def check(city, staid, aemet_path):
    aem = {d: mn for d, mn, _ in json.loads(Path(aemet_path).read_text())
           if mn is not None}
    eca = eca_series(city, staid)
    if not aem:
        return dict(city=city, ok=False, why="no AEMET data")
    lo, hi = min(aem), max(aem)
    eca_span = {d: v for d, v in eca.items() if lo <= d <= hi}
    shared = [(a, aem[d], eca_span[d]) for d, a in aem.items() if d in eca_span]
    ident = sum(1 for _, a, b in shared if abs(a - b) < 0.05)
    frac_id = ident / len(shared) if shared else 0.0
    cov = len(aem) / len(eca_span) if eca_span else 0.0
    ok = frac_id >= MIN_IDENTICAL and cov >= MIN_COVERAGE
    why = ""
    if frac_id < MIN_IDENTICAL:
        why = f"only {100*frac_id:.1f}% identical: wrong station?"
    elif cov < MIN_COVERAGE:
        why = f"coverage {100*cov:.1f}%: missing request windows"
    return dict(city=city, ok=ok, days=len(aem), shared=len(shared),
                identical=ident, pct_identical=round(100 * frac_id, 2),
                coverage=round(100 * cov, 1), why=why)


def main() -> int:
    pairs = json.loads(Path("/tmp/aemet_pairs.json").read_text())
    match = json.loads((CACHE / "city_match.json").read_text())
    rows = []
    for city in pairs:
        p = Path(f"/tmp/aemet_hist_{city}.json")
        if city == "Madrid":
            p = CACHE / "madrid_aemet_hist.json"
        if not p.exists():
            print(f"  {city:11s} not re-sourced yet")
            continue
        r = check(city, match[city]["eca"]["staid"], p)
        rows.append(r)
        flag = "PASS" if r["ok"] else "FAIL"
        print(f"  {city:11s} {flag}  {r['days']:6d} days  "
              f"{r['pct_identical']:6.2f}% identical  cov {r['coverage']:5.1f}%"
              + (f"  <- {r['why']}" if r["why"] else ""))
    bad = [r["city"] for r in rows if not r["ok"]]
    print(f"\n  {len(rows)-len(bad)}/{len(rows)} pass. "
          + (f"BLOCKED: {bad}" if bad else "clear to re-emit."))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
