#!/usr/bin/env python3
"""Build the page's data under Plan B (D-349): one unblended measure, no score.

    build_plan_b.py

Writes youth/data/map.json and youth/data/countries/<ISO>.json. Working shape
per D-030, not a contract. youth/data/index.json is the audit record of the
dropped index and is deliberately not read for any score here; only its error
scale R carries over, because that is a fact about the waves.

Display fields are rounded here, from raw shares, so design never rounds and
nothing is rounded twice. Not built here: `headline` (editor), `now_marker`
(EOS and News), `helpline` (vetted list). Absent means "not yet measured".
"""
import json
import math
from pathlib import Path

import numpy as np

from build_index import COMPONENTS, DEFF, EU27, VIDEO, WAVES, component_base, component_share, pool

HERE = Path(__file__).parent
DATA = HERE / "data"
Z90 = 1.645
OLD_WAVES = ["91", "92"]
TOP_ISSUES = 5
PRESSURES = ["housing", "poverty", "unemployment", "with_parents", "age_leaving"]
ALIKE_WITHIN = 1.5   # about half the typical distance between two EU countries (2.7)
CONTRAST_AT_LEAST = 0.15   # one map class: a smaller difference is no contrast

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
CONFIDENCE = {
    "block2": "Three waves of a face-to-face or video survey, margins shown. Young samples are small.",
    "block3": "Same survey; life satisfaction from official Eurostat statistics, 2025.",
    "block4": "Same survey. Noisy: treat close bars as ties.",
    "block5": "Official Eurostat statistics. Not on the map, and no cause is claimed.",
    "block6": "Flash Eurobarometer 585, online, June to July 2026, ages 15-30.",
    "block7": "Chosen by a fixed rule, not by hand.",
}


def pct(x):
    return round(100 * x, 1)


def whole(x):
    """Half up from the raw share, so 58.46 is 58 and never 59 by way of 58.5."""
    return int(math.floor(100 * x + 0.5))


def share_se(p, n, scale):
    return scale * np.sqrt(DEFF * p * (1 - p) / n)


def dots(y, o, ny, no, c, k, eu_mean, eu_older, scale, cells):
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
    low, high = y[k][c] - Z90 * sy, y[k][c] + Z90 * sy
    return {
        "wording": WORDING[k],
        "young_pct": pct(y[k][c]),
        "young_display": whole(y[k][c]),
        "young_interval90": [pct(low), pct(high)],
        "young_interval90_display": [whole(low), whole(high)],
        "older_pct": pct(o[k][c]),
        "older_display": whole(o[k][c]),
        "gap_points": pct(gap),
        "gap_interval90": [pct(gap - half), pct(gap + half)],
        "gap_read": read,
        "gap_by_wave_points": [pct(g) for g in by_wave],
        "comparator": {"label": COMPARATOR, "young_pct": pct(eu_mean[k]), "young_display": whole(eu_mean[k]),
                       "older_pct": pct(eu_older[k]), "older_display": whole(eu_older[k])},
        "n_young": round(ny[k][c]),
        "n_older": round(no[k][c]),
    }


def since_2019(cells, old, c, scale):
    """The marker: 15-24 now against 15-24 in 2019, raw points, distrust and direction."""
    out = {"ages": "15-24 in both periods", "mode_changed": c in VIDEO,
           "then": "Standard Eurobarometer 91 and 92, 2019"}
    for k in ("distrust", "direction"):
        now_w = [component_base(cells[v], c, k, "y1524") for v in WAVES]
        now_s = [component_share(cells[v], c, k, "y1524") for v in WAVES]
        items = COMPONENTS[k]
        old_w = [float(np.mean([old[w][c][it]["base"] for it in items])) for w in OLD_WAVES]
        old_s = [float(np.mean([old[w][c][it]["share"] for it in items])) for w in OLD_WAVES]
        now, then = np.average(now_s, weights=now_w), np.average(old_s, weights=old_w)
        half = Z90 * np.sqrt(share_se(now, sum(now_w), scale) ** 2 + share_se(then, sum(old_w), scale) ** 2)
        change = now - then
        read = "higher than 2019" if change - half > 0 else "lower than 2019" if change + half < 0 else "no clear change"
        out[k] = {"wording": WORDING[k], "now_pct": pct(now), "now_display": whole(now), "then_pct": pct(then),
                  "then_display": whole(then), "change_points": pct(change),
                  "change_interval90": [pct(change - half), pct(change + half)], "read": read}
    return out


def life_against_country(cells, c, series):
    """Block 3: wrong direction for my life against my country, plus life satisfaction."""
    out = {}
    for label, group in (("young", "gz"), ("older", "o55")):
        for item, key in (("direction_life", "my_life"), ("direction", "my_country")):
            w = [cells[v][c][item][group]["base"] for v in WAVES]
            s = [cells[v][c][item][group]["share"] for v in WAVES]
            share = float(np.average(s, weights=w))
            out.setdefault(label, {})[key + "_wrong_pct"] = pct(share)
            out[label][key + "_wrong_display"] = whole(share)
    young, adults = series["life_young"]["values"], series["life_all"]["values"]
    if c in young:
        v, a, eu = young[c], adults[c], young["EU27_2020"]
        out["life_satisfaction"] = {
            "young": v["value"], "all_adults": a["value"], "eu_young": eu["value"],
            "ages": "young 16-29, all adults 16 and over", "scale": "0 to 10",
            "year": series["life_young"]["year"], "flag": v["flag"],
            "source": "Eurostat ilc_pw01",
            "sentence": f"Young people here rate their lives {v['value']:.1f} out of 10, all adults "
                        f"{a['value']:.1f}. Young people across the EU: {eu['value']:.1f}.",
        }
    return out


def clean_issue(label):
    return label.replace("(OUR COUNTRY)", "this country")


def pooled_issues(issues, c, key):
    bases = [issues[w][c][key]["base"] for w in WAVES]
    labels = set.intersection(*(set(issues[w][c][key]["shares"]) for w in WAVES))
    return {l: float(np.average([issues[w][c][key]["shares"][l] for w in WAVES], weights=bases))
            for l in labels}, sum(bases)


def issues_block(issues, c, scale):
    out, widths = {}, []
    for key, name in (("issues_personal", "personal"), ("issues_country", "national")):
        shares, base = pooled_issues(issues, c, key)
        eu = {l: float(np.mean([pooled_issues(issues, x, key)[0].get(l, np.nan) for x in EU27]))
              for l in shares}
        rows = []
        for label, value in sorted(shares.items(), key=lambda kv: -kv[1])[:TOP_ISSUES]:
            half = Z90 * share_se(value, base, scale)
            widths.append(100 * half)
            rows.append({"label": clean_issue(label), "value_pct": pct(value), "value_display": whole(value),
                         "interval90_display": [whole(max(value - half, 0)), whole(value + half)],
                         "eu_young_pct": pct(eu[label]), "eu_young_display": whole(eu[label])})
        out[name] = {"rows": rows, "n_young": round(base)}
    question = {"personal": "The two most important issues you are facing personally",
                "national": "The two most important issues facing this country"}
    return {"rows": out["personal"]["rows"], "personal": {**out["personal"], "question": question["personal"]},
            "national": {**out["national"], "question": question["national"]},
            "comparator": COMPARATOR, "young": YOUNG, "source": SOURCE}, widths


def starting_out(c, series):
    values = {k: series[k]["values"] for k in PRESSURES}
    if c not in values["housing"]:
        return None
    rows = []
    for k in PRESSURES:
        s, v, eu = series[k], values[k][c], values[k]["EU27_2020"]
        row = {"key": k, "label": s["label"], "ages": s["ages"], "year": s["year"], "unit": s["unit"],
               "value": v["value"], "eu_value": eu["value"], "flag": v["flag"],
               "source": f"Eurostat {s['dataset']}"}
        if s["unit"] == "%":
            row.update(value_pct=v["value"], value_display=int(math.floor(v["value"] + 0.5)),
                       eu_display=int(math.floor(eu["value"] + 0.5)))
        rows.append(row)
    return {"rows": rows}


def contrasts(series, y):
    """Block 7, by rule: of the countries alike on block 5, the one furthest on the map.

    A country with no close match, or none that differs by a map class, gets no contrast:
    a forced pair is how the mockup came to call Spain "just as content".
    """
    matrix = np.array([[series[k]["values"][c]["value"] for k in PRESSURES] for c in EU27])
    z = (matrix - matrix.mean(axis=0)) / matrix.std(axis=0, ddof=1)
    out = {}
    for i, c in enumerate(EU27):
        dist = np.sqrt(((z - z[i]) ** 2).sum(axis=1))
        alike = [EU27[j] for j in range(len(EU27)) if j != i and dist[j] <= ALIKE_WITHIN]
        far = [x for x in alike if abs(y["democracy"][x] - y["democracy"][c]) >= CONTRAST_AT_LEAST]
        out[c] = max(far, key=lambda x: abs(y["democracy"][x] - y["democracy"][c])) if far else None
    return out


def main():
    source = json.loads((DATA / "eb_cells.json").read_text())
    cells, flash, issues = source["cells"], source["flash585"], source["issues"]
    old = json.loads((DATA / "eb_2019.json").read_text())["cells"]
    series = json.loads((DATA / "eurostat.json").read_text())["series"]
    scale = json.loads((DATA / "index.json").read_text())["se_scale"]["applied"]

    y, ny = pool(cells, WAVES, EU27, "gz")
    o, no = pool(cells, WAVES, EU27, "o55")
    yu, nyu = pool(cells, WAVES, ["UK"], "gz")
    ou, nou = pool(cells, WAVES, ["UK"], "o55")
    eu_mean = {k: float(np.mean([y[k][c] for c in EU27])) for k in COMPONENTS}
    eu_older = {k: float(np.mean([o[k][c] for c in EU27])) for k in COMPONENTS}
    contrast = contrasts(series, y)
    for k in COMPONENTS:
        y[k].update(yu[k]); ny[k].update(nyu[k]); o[k].update(ou[k]); no[k].update(nou[k])

    (DATA / "countries").mkdir(exist_ok=True)
    rows, widths = {}, []
    for c in EU27 + ["UK"]:
        block2 = {k: dots(y, o, ny, no, c, k, eu_mean, eu_older, scale, cells) for k in COMPONENTS}
        block4, w = issues_block(issues, c, scale)
        widths += w
        checks = {"C1": True, "C2": True, "C3": True, "C4": True, "C5": False}
        rows[c] = {
            "name": NAMES[c],
            "level": "common",
            "grey_reason": None,
            "map_value_pct": block2["democracy"]["young_pct"],
            "map_value_display": block2["democracy"]["young_display"],
            "map_interval90": block2["democracy"]["young_interval90"],
            "map_interval90_display": block2["democracy"]["young_interval90_display"],
            "older_pct": block2["democracy"]["older_pct"],
            "older_display": block2["democracy"]["older_display"],
            "gap_read": block2["democracy"]["gap_read"],
            "interview_mode_mark": c in VIDEO,
            "in_eu27_average": c != "UK",
        }
        page = {
            "iso": c, "name": NAMES[c], "young": YOUNG, "older": OLDER, "source": SOURCE,
            "checks": checks,
            "interview_mode_mark": c in VIDEO,
            "block_confidence": CONFIDENCE,
            "block2_discontent": block2,
            "block2_since_2019": since_2019(cells, old, c, scale),
            "block3_life_against_country": life_against_country(cells, c, series),
            "block4_issues": block4,
        }
        pressures = starting_out(c, series)
        if pressures:
            page["block5_starting_out"] = pressures
        if c in contrast and contrast[c] is None:
            page["block7_contrast"] = {"none": "No EU country with similar figures differs clearly on the map."}
        elif c in contrast:
            other = contrast[c]
            page["block7_contrast"] = {
                "iso": other, "name": NAMES[other],
                "rule": "Of the EU countries closely alike on the Starting out figures, the one furthest "
                        "from this country on the map measure, if at least 15 points apart.",
                "rows": [{"label": WORDING["democracy"], "this_display": whole(y["democracy"][c]),
                          "other_display": whole(y["democracy"][other])}]
                        + [{"label": series[k]["label"], "unit": series[k]["unit"],
                            "this_value": series[k]["values"][c]["value"],
                            "other_value": series[k]["values"][other]["value"]} for k in PRESSURES],
            }
        if c in flash:
            q7a = flash[c]["q7a_yes"]
            page["block6_action_to_change_society"] = {
                "wording": "Took action to change society in the past year, for example a petition, "
                           "a rally or a letter to a politician. A petition counts, so this is not protest.",
                "young_pct": pct(q7a),
                "young_display": whole(q7a),
                "ages": "15-30",
                "fieldwork": "19 Jun to 1 Jul 2026",
                "source": "Flash Eurobarometer 585, Volume A",
                "comparator": {"label": "EU27 as published", "young_pct": pct(flash["EU27"]["q7a_yes"]),
                               "young_display": whole(flash["EU27"]["q7a_yes"])},
            }
        (DATA / "countries" / f"{c}.json").write_text(json.dumps(page, indent=1))

    (DATA / "map.json").write_text(json.dumps({
        "mode": "plan_b",
        "ruling": "D-349",
        "measure": {
            "wording": WORDING["democracy"], "young": YOUNG, "older": OLDER, "source": SOURCE,
            "newest_fieldwork_ends": "2026-04-01",
            "display": "Whole numbers. The source rounds each wave to a point, so a decimal here is not real.",
            "comparator": {"label": COMPARATOR, "young_pct": pct(eu_mean["democracy"]),
                           "young_display": whole(eu_mean["democracy"]),
                           "older_pct": pct(eu_older["democracy"]),
                           "older_display": whole(eu_older["democracy"])},
            "limits": ["Stops before the autumn 2026 protests.",
                       "Covers nationals and EU citizens resident in each country; young people "
                       "from outside the EU are not in it.",
                       "Measures dissatisfaction with democracy, not anger. We found no free survey that "
                       "asks about anger by age in every EU country."],
        },
        "clear_test_note": "We call a difference between young people and over-55s clear only if it passes "
                           "two tests: the 90% margin of error around it does not include zero, and it points "
                           "the same way in all three surveys. We added the second test after seeing the data, "
                           "because the first alone would have named Hungary, where the difference changed "
                           "direction between surveys. Draft for editor.",
        "interview_mode_note": "In wave 104, Cyprus, Denmark, Malta, the Netherlands, Finland and Sweden "
                               "were interviewed by remote video, the rest in person.",
        "countries": rows,
    }, indent=1))
    print(f"wrote map.json and {len(rows)} country files; scale {scale}")
    print(f"block 4 margins, points: median {np.median(widths):.1f}, max {np.max(widths):.1f}")


if __name__ == "__main__":
    main()
