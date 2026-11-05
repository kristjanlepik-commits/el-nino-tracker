#!/usr/bin/env python3
"""Compute the youth heat index exactly as pre-registered in youth/SPEC.md.

    build_index.py            the real run, once, onto youth/data/index.json
    build_index.py --dry      random cells instead of real ones, to exercise the code

Refuses the real run unless the pre-registration commit is on the remote,
because a pre-registration only counts once pushed. Every number below that
looks like a judgement (0.4, 1.0, the gate bars, 1.5, the seed) is fixed in
the spec; changing one here without an amendment there breaks the point.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RECIPE_COMMIT = "dfde680dc78292fe7c1adc1c7d30edb560f8d8b5"

EU27 = ("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL "
        "PT RO SE SI SK").split()
WAVES = ["103", "104", "105"]
COMPONENTS = {"distrust": ["gov", "parl", "parties"], "democracy": ["democracy"],
              "direction": ["direction"]}
VIDEO = ["CY", "DK", "MT", "NL", "FI", "SE"]
DEFF, DRAWS, SEED = 1.5, 2000, 20261120
HOT, WARM, COOL = 1.0, 0.4, -0.4
C_HIGH = 0.4
BOUNDARIES = (COOL, WARM, HOT)
BARS = {"V1": 0.5, "V2": 0.7, "V3": 0.4, "V4": 20, "V5": 0.5}


def rank(values):
    """Average ranks, the tied case included, so Spearman needs no extra dependency."""
    values = np.asarray(values, float)
    order = values.argsort()
    ranks = np.empty(len(values))
    ranks[order] = np.arange(len(values), dtype=float)
    for v in np.unique(values):
        ranks[values == v] = ranks[values == v].mean()
    return ranks


def spearman(a, b):
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def component_share(wave_cells, country, comp, group):
    return float(np.mean([wave_cells[country][it][group]["share"] for it in COMPONENTS[comp]]))


def component_base(wave_cells, country, comp, group):
    return float(np.mean([wave_cells[country][it][group]["base"] for it in COMPONENTS[comp]]))


def pool(cells, waves, countries, group):
    """Base-weighted mean across waves. Returns {comp: {country: share}} and summed bases."""
    shares, bases = {}, {}
    for comp in COMPONENTS:
        shares[comp], bases[comp] = {}, {}
        for c in countries:
            w = np.array([component_base(cells[v], c, comp, group) for v in waves])
            s = np.array([component_share(cells[v], c, comp, group) for v in waves])
            shares[comp][c] = float((w * s).sum() / w.sum())
            bases[comp][c] = float(w.sum())
    return shares, bases


def reference(y, o, countries):
    ref = {}
    for comp in COMPONENTS:
        yy = np.array([y[comp][c] for c in countries])
        gg = np.array([y[comp][c] - o[comp][c] for c in countries])
        ref[comp] = {"mean_y": float(yy.mean()), "sd_y": float(yy.std(ddof=1)),
                     "mean_g": float(gg.mean()), "sd_g": float(gg.std(ddof=1))}
    return ref


def legs(y, o, ref, country):
    c = np.mean([(y[k][country] - ref[k]["mean_y"]) / ref[k]["sd_y"] for k in COMPONENTS])
    b = np.mean([((y[k][country] - o[k][country]) - ref[k]["mean_g"]) / ref[k]["sd_g"] for k in COMPONENTS])
    return float(c), float(b)


def tier(score):
    if score >= HOT:
        return "hot"
    if score >= WARM:
        return "warm"
    if score >= COOL:
        return "mild"
    return "cool"


def scale_factor(cells, countries, young, older):
    """R from the spec: wave-to-wave variance against analytic variance, floored at 1."""
    spread, analytic = [], []
    for group, pooled, bases in (("gz", *young), ("o55", *older)):
        for comp in COMPONENTS:
            for c in countries:
                vals = [component_share(cells[v], c, comp, group) for v in WAVES]
                spread.append(np.var(vals, ddof=1) / 3)
                p = pooled[comp][c]
                analytic.append(DEFF * p * (1 - p) / bases[comp][c])
    r = float(np.sqrt(np.mean(spread) / np.mean(analytic)))
    return r, max(r, 1.0)


def simulate(y, o, ny, no, ref, country, scale, rng):
    zy, zo = rng.standard_normal(DRAWS), rng.standard_normal(DRAWS)
    scores, gaps = np.zeros(DRAWS), np.zeros(DRAWS)
    for k in COMPONENTS:
        py, po = y[k][country], o[k][country]
        sy = scale * np.sqrt(DEFF * py * (1 - py) / ny[k][country])
        so = scale * np.sqrt(DEFF * po * (1 - po) / no[k][country])
        ys, os_ = py + sy * zy, po + so * zo
        scores += ((ys - ref[k]["mean_y"]) / ref[k]["sd_y"]
                   + ((ys - os_) - ref[k]["mean_g"]) / ref[k]["sd_g"]) / 2
        gaps += ys - os_
    n = len(COMPONENTS)
    return np.percentile(scores / n, [5, 95]), float(np.percentile(gaps / n, 5))


def score_set(cells, waves, countries, group="gz"):
    y, ny = pool(cells, waves, countries, group)
    o, no = pool(cells, waves, countries, "o55")
    ref = reference(y, o, countries)
    out = {c: legs(y, o, ref, c) for c in countries}
    return y, o, ny, no, ref, out


def full_run(cells, flash):
    y, o, ny, no, ref, base = score_set(cells, WAVES, EU27)
    r, scale = scale_factor(cells, EU27, (y, ny), (o, no))
    rng = np.random.default_rng(SEED)

    results = {}
    for c in EU27 + ["UK"]:
        if c == "UK":
            yu, nyu = pool(cells, WAVES, ["UK"], "gz")
            ou, nou = pool(cells, WAVES, ["UK"], "o55")
            ys, os_, nys, nos = yu, ou, nyu, nou
        else:
            ys, os_, nys, nos = y, o, ny, no
        cc, bb = legs(ys, os_, ref, c)
        score = (cc + bb) / 2
        (lo, hi), gap_p5 = simulate(ys, os_, nys, nos, ref, c, scale, rng)
        crossed = sum(1 for x in BOUNDARIES if lo < x <= hi)
        placed = crossed <= 1
        clear = gap_p5 > 0
        high = cc >= C_HIGH
        kind = {(True, True): "youth revolt", (True, False): "angry country",
                (False, True): "generational gap", (False, False): "calm"}[(high, clear)]
        results[c] = {
            "score": round(score, 3), "interval": [round(float(lo), 3), round(float(hi), 3)],
            "C": round(cc, 3), "B": round(bb, 3),
            "raw_gap_points": round(100 * float(np.mean([ys[k][c] - os_[k][c] for k in COMPONENTS])), 1),
            "gap_clearly_positive": bool(clear),
            "tier": tier(score) if placed else None, "type": kind if placed else None,
            "too_noisy_to_place": not placed,
            "components": {k: {"young": round(100 * ys[k][c], 1), "older": round(100 * os_[k][c], 1),
                               "young_eu_mean": round(100 * ref[k]["mean_y"], 1),
                               "n_young": round(nys[k][c]), "n_older": round(nos[k][c])}
                           for k in COMPONENTS},
            "interview_mode_mark": c in VIDEO,
            "in_reference": c != "UK",
        }

    gates = {}
    pairs = [("distrust", "democracy"), ("distrust", "direction"), ("democracy", "direction")]
    v1 = [spearman([y[a][c] for c in EU27], [y[b][c] for c in EU27]) for a, b in pairs]
    gates["V1"] = {"values": dict(zip(["-".join(p) for p in pairs], np.round(v1, 3).tolist())),
                   "stat": float(np.median(v1))}
    v2, v3 = [], []
    for held in WAVES:
        rest = [w for w in WAVES if w != held]
        one, two = score_set(cells, [held], EU27)[-1], score_set(cells, rest, EU27)[-1]
        v2.append(spearman([one[c][0] for c in EU27], [two[c][0] for c in EU27]))
        v3.append(spearman([one[c][1] for c in EU27], [two[c][1] for c in EU27]))
    gates["V2"] = {"values": np.round(v2, 3).tolist(), "stat": float(np.median(v2))}
    gates["V3"] = {"values": np.round(v3, 3).tolist(), "stat": float(np.median(v3))}
    gates["V4"] = {"stat": sum(1 for c in EU27 if results[c]["tier"])}
    gates["V5"] = {"stat": spearman([results[c]["C"] for c in EU27],
                                    [flash[c]["q18_1_disagree"] for c in EU27])}
    for name, g in gates.items():
        g["bar"] = BARS[name]
        g["pass"] = bool(g["stat"] >= BARS[name])
    passed = all(g["pass"] for g in gates.values())

    # Side checks: disclosure only, they change nothing above.
    _, _, _, _, _, young_alt = score_set(cells, WAVES, EU27, "y1524")
    alt_tiers = {c: tier(sum(young_alt[c]) / 2) for c in EU27}
    moved = [c for c in EU27 if results[c]["tier"] and alt_tiers[c] != tier(results[c]["score"])]
    keep = [c for c in EU27 if c not in VIDEO]
    ref_no_video = reference(y, o, keep)
    no_video = {c: tier(sum(legs(y, o, ref_no_video, c)) / 2) for c in EU27}
    moved_video = [c for c in EU27 if results[c]["tier"] and no_video[c] != tier(results[c]["score"])]

    return {
        "recipe_commit": RECIPE_COMMIT, "mode": "index" if passed else "plan_b",
        "waves": WAVES, "young": "born 1997 or later", "older": "55+",
        "se_scale": {"R": round(r, 3), "applied": round(scale, 3)},
        "reference": {k: {m: round(v, 4) for m, v in d.items()} for k, d in ref.items()},
        "gates": gates,
        "side_checks": {
            "young_15_24": {"tiers_changed": len(moved), "countries": moved, "tiers": alt_tiers},
            "reference_without_video_countries": {"tiers_changed": len(moved_video), "countries": moved_video},
        },
        "countries": results,
    }


def remote_has_recipe():
    subprocess.run(["git", "fetch", "-q", "origin"], check=True)
    out = subprocess.run(["git", "branch", "-r", "--contains", RECIPE_COMMIT],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def synthetic():
    """Random cells of the real shape. Exercises every path; means nothing."""
    rng = np.random.default_rng(1)
    items = ["gov", "parl", "parties", "democracy", "direction", "direction_life"]
    cells = {w: {c: {it: {g: {"share": float(rng.uniform(.2, .8)), "base": float(rng.integers(60, 600))}
                          for g in ("total", "y1524", "o55", "gz")} for it in items}
                 for c in EU27 + ["UK"]} for w in WAVES}
    return cells, {c: {"q18_1_disagree": float(rng.uniform(.3, .8))} for c in EU27}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if args.dry:
        res = full_run(*synthetic())
        print("dry run on random cells, nothing written:", res["mode"],
              {k: round(g["stat"], 2) for k, g in res["gates"].items()})
        return

    if not remote_has_recipe():
        raise SystemExit(f"{RECIPE_COMMIT[:7]} is not on the remote. Push the pre-registration first.")
    out = HERE / "data" / "index.json"
    if out.exists():
        raise SystemExit(f"{out} exists. The index runs once; see SPEC section 13 before removing it.")
    data = json.loads((HERE / "data" / "eb_cells.json").read_text())
    res = full_run(data["cells"], data["flash585"])
    out.write_text(json.dumps(res, indent=1))
    print(f"wrote {out}: mode {res['mode']}")


if __name__ == "__main__":
    main()
