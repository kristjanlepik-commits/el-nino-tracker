#!/usr/bin/env python3
"""Build the page's data under Plan B (D-349): one unblended measure, no score.

    build_plan_b.py

Writes youth/data/map.json and youth/data/countries/<ISO>.json. Working shape
per D-030, not a contract. youth/data/index.json is the audit record of the
dropped index and is deliberately not read for any score here; only its error
scale R carries over, because that is a fact about the waves.

Blocks not built yet: the 2019 marker, block 4, life satisfaction and pressures
from Eurostat, the "now" marker, nearest contrast. Check C4 is therefore open
and every country stays grey until it closes.
"""
import json
from pathlib import Path

import numpy as np

from build_index import COMPONENTS, DEFF, EU27, VIDEO, WAVES, component_base, component_share, pool

HERE = Path(__file__).parent
DATA = HERE / "data"
Z90 = 1.645

NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "EL": "Greece", "ES": "Spain",
    "FI": "Finland", "FR": "France", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland",
    "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SE": "Sweden",
    "SI": "Slovenia", "SK": "Slovakia", "UK": "United Kingdom",
}
WORDING = {
    "democracy": "Not very or not at all satisfied with the way democracy works in their country",
    "distrust": "Tend not to trust the national government, parliament and political parties (mean of the three)",
    "direction": "Things are going in the wrong direction in their country",
}
SOURCE = ("Standard Eurobarometer 103, 104, 105, Volume C. Fieldwork 26 Mar to 10 May 2025, "
          "9 Oct to 5 Nov 2025, 12 Mar to 1 Apr 2026.")
YOUNG = "born 1997 or later"
OLDER = "55 and over"
COMPARATOR = "average of the 27 EU countries, each counted once"


def pct(x):
    return round(100 * x, 1)


def share_se(p, n, scale):
    return scale * np.sqrt(DEFF * p * (1 - p) / n)


def dots(y, o, ny, no, c, k, eu_mean, scale, cells):
    """One measure for one country: young, older, the gap and how sure we are of it.

    "Clear" takes both the 90% interval and the same sign in all three waves. With
    27 countries a 90% interval alone gives about 1.4 false calls per direction.
    """
    sy, so = share_se(y[k][c], ny[k][c], scale), share_se(o[k][c], no[k][c], scale)
    gap = y[k][c] - o[k][c]
    half = Z90 * np.sqrt(sy ** 2 + so ** 2)
    by_wave = [component_share(cells[v], c, k, "gz") - component_share(cells[v], c, k, "o55")
               for v in WAVES]
    if gap - half > 0 and min(by_wave) > 0:
        read = "young higher"
    elif gap + half < 0 and max(by_wave) < 0:
        read = "older higher"
    else:
        read = "no clear difference"
    return {
        "wording": WORDING[k],
        "young_pct": pct(y[k][c]),
        "young_interval90": [pct(y[k][c] - Z90 * sy), pct(y[k][c] + Z90 * sy)],
        "older_pct": pct(o[k][c]),
        "gap_points": pct(gap),
        "gap_interval90": [pct(gap - half), pct(gap + half)],
        "gap_read": read,
        "gap_by_wave_points": [pct(g) for g in by_wave],
        "comparator": {"label": COMPARATOR, "young_pct": pct(eu_mean[k])},
        "n_young": round(ny[k][c]),
        "n_older": round(no[k][c]),
    }


def life_against_country(cells, c):
    """Block 3, Eurobarometer half: wrong direction for my life, against for my country."""
    out = {}
    for label, group in (("young", "gz"), ("older", "o55")):
        for item, key in (("direction_life", "my_life"), ("direction", "my_country")):
            w = [cells[v][c][item][group]["base"] for v in WAVES]
            s = [cells[v][c][item][group]["share"] for v in WAVES]
            out.setdefault(label, {})[key + "_wrong_pct"] = pct(float(np.average(s, weights=w)))
    return out


def main():
    source = json.loads((DATA / "eb_cells.json").read_text())
    cells, flash = source["cells"], source["flash585"]
    scale = json.loads((DATA / "index.json").read_text())["se_scale"]["applied"]

    y, ny = pool(cells, WAVES, EU27, "gz")
    o, no = pool(cells, WAVES, EU27, "o55")
    yu, nyu = pool(cells, WAVES, ["UK"], "gz")
    ou, nou = pool(cells, WAVES, ["UK"], "o55")
    for k in COMPONENTS:
        y[k].update(yu[k]); ny[k].update(nyu[k]); o[k].update(ou[k]); no[k].update(nou[k])
    eu_mean = {k: float(np.mean([y[k][c] for c in EU27])) for k in COMPONENTS}

    (DATA / "countries").mkdir(exist_ok=True)
    rows = {}
    for c in EU27 + ["UK"]:
        block2 = {k: dots(y, o, ny, no, c, k, eu_mean, scale, cells) for k in COMPONENTS}
        checks = {"C1": True, "C2": True, "C3": True, "C4": False, "C5": False}
        common = checks["C1"] and checks["C2"] and checks["C3"] and checks["C4"]
        rows[c] = {
            "name": NAMES[c],
            "level": "common" if common else "grey",
            "grey_reason": None if common else "Eurostat blocks not built yet",
            "map_value_pct": block2["democracy"]["young_pct"],
            "map_interval90": block2["democracy"]["young_interval90"],
            "older_pct": block2["democracy"]["older_pct"],
            "gap_read": block2["democracy"]["gap_read"],
            "interview_mode_mark": c in VIDEO,
            "in_eu27_average": c != "UK",
        }
        page = {
            "iso": c, "name": NAMES[c], "young": YOUNG, "older": OLDER, "source": SOURCE,
            "checks": checks,
            "interview_mode_mark": c in VIDEO,
            "block2_discontent": block2,
            "block3_life_against_country": life_against_country(cells, c),
        }
        if c in flash:
            page["block6_action_to_change_society"] = {
                "wording": "Took action to change society in the past year, for example a petition, "
                           "a rally or a letter to a politician. A petition counts, so this is not protest.",
                "young_pct": pct(flash[c]["q7a_yes"]),
                "ages": "15-30",
                "fieldwork": "19 Jun to 1 Jul 2026",
                "source": "Flash Eurobarometer 585, Volume A",
                "comparator": {"label": "EU27 as published", "young_pct": pct(flash["EU27"]["q7a_yes"])},
            }
        (DATA / "countries" / f"{c}.json").write_text(json.dumps(page, indent=1))

    (DATA / "map.json").write_text(json.dumps({
        "mode": "plan_b",
        "ruling": "D-349",
        "measure": {
            "wording": WORDING["democracy"], "young": YOUNG, "older": OLDER, "source": SOURCE,
            "newest_fieldwork_ends": "2026-04-01",
            "display": "Whole numbers. The source rounds each wave to a point, so a decimal here is not real.",
            "comparator": {"label": COMPARATOR, "young_pct": pct(eu_mean["democracy"])},
            "limits": ["Stops before the autumn 2026 protests.",
                       "Covers nationals and EU citizens resident in each country; young people "
                       "from outside the EU are not in it.",
                       "Measures dissatisfaction with democracy, not anger. We found no free survey that "
                       "asks about anger by age in every EU country."],
        },
        "interview_mode_note": "In wave 104, Cyprus, Denmark, Malta, the Netherlands, Finland and Sweden "
                               "were interviewed by remote video, the rest in person.",
        "countries": rows,
    }, indent=1))
    print(f"wrote map.json and {len(rows)} country files; scale {scale}")


if __name__ == "__main__":
    main()
