#!/usr/bin/env python3
"""Build the youth stress index prototype, SPEC section 18.

    build_stress.py

Writes youth/data/stress_index.json. Young people's own levels only, never the
gap to older people, so a country is not called calm because its old are angrier
(the flaw D-349 found in the dropped index). Recipe committed in 1ea5973 before
this file first ran; a change to the components or arithmetic is a new section.
"""
import json
from pathlib import Path

import numpy as np

from build_index import EU27, WAVES

DATA = Path(__file__).parent / "data"
CAP = 2.5
CLASSES = [(60, "very high"), (53, "high"), (47, "around average"), (40, "low"), (-999, "very low")]

# key -> (label, item in eb_cells.json)
MOOD = {
    "M1": ("Dissatisfied with how democracy works in the country", "democracy"),
    "M2": ("Tend not to trust the national government", "gov"),
    "M3": ("Country going in the wrong direction", "direction"),
    "M4": ("Own life going in the wrong direction", "direction_life"),
}
# key -> (series in eurostat.json, sign): sign -1 where a higher value means less stress
PRESSURE = {
    "P1": ("life_young", -1),
    "P2": ("unemployment", 1),
    "P3": ("poverty", 1),
    "P4": ("housing", 1),
    "P5": ("with_parents", 1),
}


def mood_values(cells):
    """Born 1997 or later, three waves pooled by count."""
    out = {}
    for key, (_, item) in MOOD.items():
        out[key] = {}
        for c in cells[WAVES[0]]:
            num = sum(cells[w][c][item]["gz"]["count_num"] for w in WAVES)
            den = sum(cells[w][c][item]["gz"]["count_den"] for w in WAVES)
            out[key][c] = {"value": num / den * 100, "base": den}
    return out


def pressure_values(eurostat):
    out = {}
    for key, (series, _) in PRESSURE.items():
        s = eurostat["series"][series]
        out[key] = {g: {"value": v["value"], "flag": v["flag"]} for g, v in s["values"].items()
                    if g != "EU27_2020"}
    return out


def zscores(values, sign):
    eu = np.array([values[c]["value"] for c in EU27])
    mean, sd = eu.mean(), eu.std(ddof=0)
    return {c: float(np.clip(sign * (v["value"] - mean) / sd, -CAP, CAP)) for c, v in values.items()}


def label(score):
    return next(name for floor, name in CLASSES if score >= floor)


def main():
    cells = json.loads((DATA / "eb_cells.json").read_text())["cells"]
    eurostat = json.loads((DATA / "eurostat.json").read_text())
    mood, pressure = mood_values(cells), pressure_values(eurostat)
    z = {k: zscores(v, 1) for k, v in mood.items()}
    z.update({k: zscores(pressure[k], PRESSURE[k][1]) for k in PRESSURE})

    countries = {}
    for c in sorted(cells[WAVES[0]]):
        m = float(np.mean([z[k][c] for k in MOOD]))
        has_p = all(c in z[k] for k in PRESSURE)
        p = float(np.mean([z[k][c] for k in PRESSURE])) if has_p else None
        index = (m + p) / 2 if has_p else m
        score = 50 + 15 * index
        countries[c] = {
            "score": round(score, 1), "score_display": round(score), "class": label(score),
            "mood": round(m, 2), "pressure": None if p is None else round(p, 2),
            "mood_only": not has_p,
            "components": {
                **{k: {"label": MOOD[k][0], "value": round(mood[k][c]["value"], 1),
                       "z": round(z[k][c], 2)} for k in MOOD},
                **{k: {"label": eurostat["series"][PRESSURE[k][0]]["label"],
                       "ages": eurostat["series"][PRESSURE[k][0]]["ages"],
                       "value": pressure[k][c]["value"], "flag": pressure[k][c]["flag"],
                       "z": round(z[k][c], 2)} for k in PRESSURE if c in pressure[k]},
            },
        }
    ranked = sorted((c for c in countries if c in EU27), key=lambda c: -countries[c]["score"])
    for i, c in enumerate(ranked, 1):
        countries[c]["rank_eu27"] = i
    mood_eu = [countries[c]["mood"] for c in EU27]
    press_eu = [countries[c]["pressure"] for c in EU27]
    doc = {
        "status": "prototype, SPEC section 18; not on any page",
        "recipe_commit": "1ea5973",
        "pillar_correlation_eu27": round(float(np.corrcoef(mood_eu, press_eu)[0, 1]), 2),
        "classes": [{"from": f, "name": n} for f, n in CLASSES],
        "countries": countries,
    }
    (DATA / "stress_index.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(f"pillar correlation, EU27: {doc['pillar_correlation_eu27']}")
    for c in ranked + [c for c in countries if c not in EU27]:
        r = countries[c]
        print(f"{c} {r['score']:5.1f} {r['class']:15} mood {r['mood']:+.2f} pressure "
              f"{'' if r['pressure'] is None else format(r['pressure'], '+.2f')}")


if __name__ == "__main__":
    main()
