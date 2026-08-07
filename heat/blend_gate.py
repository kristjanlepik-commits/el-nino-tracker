"""Detect a spliced station record before it becomes a city page.

WHY THIS EXISTS. ECA&D publishes Murcia under the name of an air base while
splicing the city station in for recent decades. Our pairing matched by name,
so the history came from one thermometer and the current year from another,
and the published rank compared the two. A whole-record identity score reads
100.00% for the early era and 2.01% for the late one, averaging to something
that merely looks like a wrong station.

**A blended series agrees perfectly with its first component right up to the
splice.** That is what makes it invisible to any check scoring the record as a
whole, and it is why the era of a disagreement identifies its cause:

    wrong station      disagrees from the first shared day
    blended reference  agrees perfectly, then diverges at a splice
    adjusted series    disagrees smoothly, usually everywhere

At fifteen cities a splice was findable by hand. GHCN-Daily is a compilation
like ECA&D and carries merged records, so at twenty-seven it will not be.

THE TEST. A standard changepoint statistic on the difference between the
candidate and a reference series. Differencing removes the shared weather, so
what remains is instrument and siting; a splice shows up as a STEP rather than
a trend. This is the same construction as the SNHT used in homogenisation, run
as a GATE rather than as a correction: we do not adjust anything, we refuse it.

VALIDATED ON A KNOWN ANSWER, which is the part that makes it trustworthy. The
ECA&D Murcia series is a confirmed splice and must fail. AEMET single-station
records are clean and must pass. A detector never tested against a case whose
answer is known is a detector nobody should believe.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "heat" / ".cache"

MIN_YEARS = 25          # below this a changepoint statistic is not meaningful
EDGE = 5                # ignore splits within this many years of either end
T_CRIT = 6.0            # flag above this; calibrated on the controls below


def annual_summer_mean(daily):
    """Mean June-August Tmin per year. Summer because that is what we publish."""
    per = defaultdict(list)
    for d, v in daily.items():
        if v is not None and d[5:7] in ("06", "07", "08"):
            per[int(d[:4])].append(v)
    return {y: float(np.mean(vs)) for y, vs in per.items() if len(vs) >= 80}


def changepoint(diff):
    """Largest two-sample t statistic over all interior split points.

    Returns (t, year). A step in the difference series is a splice signature;
    a trend is not, which is why this tests means either side rather than a
    slope.
    """
    ys = sorted(diff)
    if len(ys) < MIN_YEARS:
        return None, None
    vals = np.array([diff[y] for y in ys])
    best = (0.0, None)
    for i in range(EDGE, len(ys) - EDGE):
        a, b = vals[:i], vals[i:]
        sa, sb = a.std(ddof=1), b.std(ddof=1)
        n1, n2 = len(a), len(b)
        se = np.sqrt(sa**2 / n1 + sb**2 / n2)
        if se <= 0:
            continue
        t = abs(a.mean() - b.mean()) / se
        if t > best[0]:
            best = (float(t), ys[i])
    return best


def check(name, cand, ref):
    """cand and ref are {date: value}. ref is an independent record."""
    ca, ra = annual_summer_mean(cand), annual_summer_mean(ref)
    common = sorted(set(ca) & set(ra))
    diff = {y: ca[y] - ra[y] for y in common}
    t, yr = changepoint(diff)
    if t is None:
        return dict(name=name, ok=None, n_years=len(common),
                    why="too few overlapping years to test")
    ok = t < T_CRIT
    step = None
    if yr is not None:
        a = [diff[y] for y in common if y < yr]
        b = [diff[y] for y in common if y >= yr]
        step = round(float(np.mean(b) - np.mean(a)), 3)
    return dict(name=name, ok=ok, n_years=len(common), t=round(t, 2),
                split_year=yr, step_c=step,
                why="" if ok else
                    f"step of {step:+.2f} C at {yr}, t={t:.1f}: the record "
                    f"changes instrument partway through")


def _eca(city, staid):
    out = {}
    for line in open(CACHE / f"h_{city}.txt", encoding="latin-1"):
        m = re.match(rf"\s*{staid},\s*\d+,\s*(\d{{4}})(\d{{2}})(\d{{2}}),"
                     rf"\s*(-?\d+),\s*(\d)", line)
        if m and int(m[5]) != 9:
            out[f"{m[1]}-{m[2]}-{m[3]}"] = int(m[4]) / 10.0
    return out


def _src(fname):
    return {d: mn for d, mn, _ in
            json.loads((CACHE / "src" / fname).read_text())}


def controls() -> int:
    """Run the detector against cases whose answer is already known."""
    match = json.loads((CACHE / "city_match.json").read_text())
    rows = []

    # POSITIVE CONTROL. ECA&D Murcia is a confirmed splice: 100.00% identical
    # to the city station from 1990 and 2.01% to the air base it is named
    # after. It MUST fail.
    rows.append(("ECA&D Murcia vs AEMET air base  (KNOWN SPLICE, must FAIL)",
                 check("murcia_eca", _eca("Murcia", match["Murcia"]["eca"]["staid"]),
                       _src("aemet_Murcia.json"))))

    # NEGATIVE CONTROLS. Single AEMET stations against their ECA&D twins,
    # verified 100.00% identical day by day. They MUST pass.
    for city in ("Madrid", "Barcelona", "Seville", "Zaragoza"):
        rows.append((f"ECA&D {city} vs AEMET  (KNOWN CLEAN, must PASS)",
                     check(city.lower(), _eca(city, match[city]["eca"]["staid"]),
                           _src(f"aemet_{city}.json"))))

    print(f"{'control':52s} {'verdict':>8s} {'t':>7s} {'split':>6s} {'step':>7s}")
    print("-" * 86)
    bad = 0
    for label, r in rows:
        v = "n/a" if r["ok"] is None else ("PASS" if r["ok"] else "FAIL")
        expect_fail = "must FAIL" in label
        wrong = (r["ok"] is None) or (expect_fail == r["ok"])
        bad += wrong
        print(f"{label:52s} {v:>8s} {r.get('t', 0):7.2f} "
              f"{str(r.get('split_year') or ''):>6s} "
              f"{str(r.get('step_c') if r.get('step_c') is not None else ''):>7s}"
              + ("   <-- DETECTOR WRONG" if wrong else ""))
    print("-" * 86)
    print(f"controls failed: {bad}. "
          + ("Detector behaves as specified." if not bad
             else "DO NOT USE until this is zero."))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(controls())
