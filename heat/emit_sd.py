"""Emit the z-score and band VD's instrument renders, from the published basis.

Design's definition, unmodified: sample sd (n-1) of nights-per-year counted
to each city's OWN cut, over 1991-2020, with the current year EXCLUDED from
the window.

THREE THINGS THAT ARE DECISIONS, NOT DEFAULTS, so they are fields.

`current_year_in_baseline: false`. This is why z has no in-sample ceiling of
(n-1)/sqrt(n). Three chats each inferred the opposite in one day, VD of
fires' 13.10, crops of Bilbao's 7.90, design of crops. An unstated premise
that three people get wrong is a field.

`baseline_window` fixed at 1991-2020 rather than each station's full record.
Heat's ruling 2026-08-07. A 106-year Madrid sd would span a warming climate
and measure trend PLUS variability, inflating the sd and understating z. The
quantity wanted is the spread of the CURRENT climate, which is what the WMO
standard normal brackets. Consequence, stated because VD expected otherwise:
n is 30 everywhere, so every band is identically wide and a long record buys
no extra precision here.

`usable_to_cut` filters the baseline. A year too thin to rank is too thin to
carry a baseline, the same principle that keeps an unusable slot from being
drawn as a gap.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "heat" / "data" / "city_series.json"
OUT = ROOT / "heat" / "data" / "city_sd.json"
LO, HI = 1991, 2020


def main() -> int:
    S = json.loads(SERIES.read_text())
    out = {}
    for c, v in S["cities"].items():
        cur = max(int(y) for y in v["years"])
        base = {int(y): d["nights_to_cut"] for y, d in v["years"].items()
                if LO <= int(y) <= HI and int(y) != cur and d["usable_to_cut"]}
        n = len(base)
        if n < 2:
            continue
        mean = statistics.mean(base.values())
        sd = statistics.stdev(base.values())
        n26 = v["years"][str(cur)]["nights_to_cut"]
        out[c] = {
            "n": n, "mean": round(mean, 2), "sd": round(sd, 2),
            "z": round((n26 - mean) / sd, 2) if sd else None,
            "band_rel": round(1 / math.sqrt(2 * (n - 1)), 4),
            "excluded_years": sorted(set(range(LO, HI + 1)) - set(base)),
            "cut_at": v["counted_to"][5:],
            "source": v["source"],
        }
    payload = {
        "_readme":
            "Standardised departure of 2026 from each city's 1991-2020 "
            "normal, with the relative error on the sd estimate. Nights per "
            "year counted to each city's own cut.",
        "definition": {
            "quantity": "nights per year counted to this city's own cut",
            "baseline_window": f"{LO}-{HI}",
            "sd_kind": "sample standard deviation, n-1 denominator",
            "current_year_in_baseline": False,
            "current_year_note":
                "2026 is EXCLUDED from the baseline. z is therefore an "
                "out-of-sample departure and is NOT bounded by the in-sample "
                "ceiling of (n-1)/sqrt(n). A z above that ceiling is not "
                "evidence of a fitted or erroneous value.",
            "baseline_completeness":
                "A baseline year must clear the same usability bar as a "
                "ranked year: 90% of days from 1 May to the cut. A year too "
                "thin to rank is too thin to carry a baseline.",
            "why_fixed_window":
                "Fixed at 1991-2020 rather than each station's full record. "
                "A full-record sd for a 106-year station spans a warming "
                "climate and measures trend PLUS variability, inflating the "
                "sd and understating z. The quantity wanted is the spread of "
                "the current climate. CONSEQUENCE: n is 30 for nearly every "
                "city, so band width is near-identical across cities and a "
                "long record buys no extra precision on this figure.",
            "band_rel_meaning":
                "1/sqrt(2(n-1)), the relative standard error of the sd "
                "estimate. It qualifies the sd, not the city.",
        },
        "cities": out,
    }
    (Path(sys.argv[1]) if len(sys.argv) > 1 else OUT).write_text(
        json.dumps(payload, indent=1) + "\n")
    print(f"{'city':12s} {'n':>3s} {'mean':>7s} {'sd':>6s} {'z':>6s} {'band':>7s}  excluded")
    print("-" * 68)
    for c, d in sorted(out.items()):
        print(f"{c:12s} {d['n']:3d} {d['mean']:7.2f} {d['sd']:6.2f} "
              f"{d['z']:6.2f} {d['band_rel']*100:6.1f}%  {d['excluded_years'] or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
