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


# ---------------------------------------------------------------------------
# PAIRWISE NEIGHBOUR TEST, for stations with no independent second source.
#
# The check above needs the same city measured twice. Six cities in the live
# payload have only one source (Berlin, Cologne, Frankfurt, Hamburg, Munich,
# Vienna) and so were shipping unverified, one of them featured. Prague and
# Warsaw would arrive the same way.
#
# The standard answer in homogenisation is to use NEIGHBOURS rather than a
# second instrument. Summer temperature is regionally coherent, so the
# difference between two stations a few hundred km apart is nearly flat over
# time. A splice at one of them puts a STEP in that difference.
#
# PAIRWISE, NOT AGAINST A COMPOSITE, and the reason matters: a composite
# hides which station moved. If a target disagrees with ONE neighbour, the
# neighbour is the likely culprit; if it disagrees with MOST of them, the
# target is. A composite averages that signal away and can itself be
# contaminated by a spliced member.
#
# ###################################################################
# THIS TEST DOES NOT WORK AND MUST NOT BE USED AS A GATE.
#
# Measured against a null built from 105 pairs of cities INDEPENDENTLY
# VERIFIED CLEAN by the two-source test above:
#
#     clean pairs      0-200 km   median t 9.6, max 11.4
#                    200-400 km   median t 5.9, max 11.1
#                    400-700 km   median t 5.5, max 11.1
#     KNOWN BLEND    vs neighbours         t 8.2 to 10.6
#
# The known splice sits INSIDE the clean distribution. Summer-mean
# differences between cities hundreds of km apart drift genuinely over
# 75 years through station moves, urbanisation and real regional climate,
# and a 1 C splice is smaller than that drift. There is no threshold that
# separates them: any cut catching the blend condemns most clean pairs.
#
# Kept rather than deleted because the negative result is the useful part.
# Without it, the next person reaches for exactly this construction, and
# the version that ships would flag Frankfurt and Vienna on nothing.
#
# WHAT TO DO INSTEAD: read the station METADATA. DWD, GeoSphere and AEMET
# publish station histories including relocations. A splice is a documented
# administrative event, and looking it up beats inferring it from data at
# an effect size below the noise.
# ###################################################################

COORDS = {
    "Seville": (37.4, -6.0), "Malaga": (36.7, -4.5), "Murcia": (38.0, -1.1),
    "Alicante": (38.3, -0.5), "Valencia": (39.5, -0.4), "Palma": (39.6, 2.7),
    "Madrid": (40.4, -3.7), "Barcelona": (41.4, 2.2), "Zaragoza": (41.7, -0.9),
    "Bilbao": (43.3, -2.9), "Nice": (43.7, 7.3), "Marseille": (43.3, 5.4),
    "Montpellier": (43.6, 3.9), "Lyon": (45.8, 4.8), "Vienna": (48.2, 16.4),
    "Munich": (48.1, 11.6), "Paris": (48.9, 2.4), "Frankfurt": (50.1, 8.7),
    "Cologne": (50.9, 7.1), "Berlin": (52.5, 13.4), "Hamburg": (53.6, 10.0),
}

N_NEIGHBOURS = 4
MAJORITY = 0.5          # fraction of neighbours that must agree to blame target


def _km(a, b):
    la, lo = np.radians(COORDS[a]), np.radians(COORDS[b])
    dlat, dlon = lo[0] - la[0], lo[1] - la[1]
    h = (np.sin(dlat / 2) ** 2
         + np.cos(la[0]) * np.cos(lo[0]) * np.sin(dlon / 2) ** 2)
    return float(6371 * 2 * np.arcsin(np.sqrt(h)))


def check_pairwise(target, series_by_city):
    """Flag `target` if it steps against a MAJORITY of its nearest neighbours."""
    others = sorted((c for c in series_by_city if c != target),
                    key=lambda c: _km(target, c))[:N_NEIGHBOURS]
    hits, tested, detail = 0, 0, []
    for n in others:
        r = check(f"{target}~{n}", series_by_city[target], series_by_city[n])
        if r["ok"] is None:
            continue
        tested += 1
        if not r["ok"]:
            hits += 1
        detail.append((n, round(_km(target, n)), r.get("t", 0),
                       r.get("split_year"), r.get("step_c")))
    if not tested:
        return dict(city=target, ok=None, why="no testable neighbour")
    frac = hits / tested
    return dict(city=target, ok=frac <= MAJORITY, tested=tested, flagged=hits,
                detail=detail,
                why="" if frac <= MAJORITY else
                    f"steps against {hits} of {tested} neighbours: the target "
                    f"is the station that moved, not the neighbour")
