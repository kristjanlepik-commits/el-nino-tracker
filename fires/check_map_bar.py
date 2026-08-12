"""Which quantity should the front-page map threshold on? Archive test.

THE QUESTION. The shared map has a limited number of slots, so fires needs a
bar deciding which countries are DRAWN. It shipped as "three times its own
same-week mean or more". Design asked whether 3x was the right level. The
answer turned out to be that the level was not the issue; the QUANTITY was.

WHAT PROMPTED IT, from the live week of 2026-08-05:

    United Kingdom   3.0x   z 8.0   427 detections against thirteen prior
                                    years of 72 to 193, so 2.2x its own
                                    previous record. Cleared a 3x bar by
                                    exactly 0.0.
    Indonesia        3.7x   z 3.1   20,416 against a previous best of
                                    18,075, so 1.13x its own record. Drawn.
    United States    2.6x   z 3.6   rank 1, more extreme than Indonesia.
                                    NOT drawn.

=============================================================================
A MECHANISM I ASSERTED AND THE ARCHIVE REFUTED
=============================================================================

From those cases I told design that a multiple bar "rewards volatility": a
country with an erratic history has a mean dragged down by low years, so it
posts a big multiple for an ordinary week. It is a plausible story and it
fits the three cases above.

IT IS NOT TRUE. Measured over 220 archive weeks, countries drawn by a
multiple bar and by a z bar have the SAME median baseline volatility,
coefficient of variation 0.37 either way. Whatever separates the two bars,
it is not that one preferentially selects erratic countries.

That test is kept in `volatility_of_drawn` below, because a refuted
mechanism is worth keeping next to the one that replaced it. I sent the
wrong reason to another chat before checking it, which is the same error as
reasoning from a striking case to a general rule anywhere else in this
channel.

=============================================================================
THE MECHANISM THAT SURVIVES
=============================================================================

Ask instead what each bar draws THAT THE OTHER DOES NOT, and whether those
marginal picks are at a genuine record. Over 220 weeks:

    countries only the z bar draws           n=112    11% at a record   (12)
    countries only the multiple bar draws    n=112     1% at a record   (1)

    one-sided Fisher exact                   p = 0.001

So the marginal country a multiple bar pulls in is almost never at a record,
and the one it displaces frequently is.

SCALE IT HONESTLY. The two bars agree entirely in most weeks: median overlap
six of six, differing in 43% of weeks and usually by a single country. This
is a marginal improvement, not a dramatic one. The case for it is not that
the map changes much; it is that when it changes, one bar is right and the
other is wrong.

WHAT THIS DOES NOT ARGUE FOR. z is the better instrument for a DRAWING bar,
where the question is "how unusual is this for this place" and slots are
scarce. It is a bad instrument for the GATE, because it has the opposite
weakness: it under-selects genuinely volatile countries, and Canada at 1.8x
scores z = 0.8 because its variance is enormous. The gate stays OR'd
(z OR multiple OR rank 1) so such a country still counts as anomalous and
still appears on the channel page. Only the drawn subset changes.
"""
from __future__ import annotations

import json
import math
import os
import statistics as st
from datetime import date

HERE = os.path.dirname(__file__)
FULL_HISTORY = os.path.join(HERE, "data", "full_history")

NOISE_FLOOR = 150          # matches build_events; below this a multiple is noise
SLOTS = 6                  # marks the shared map gives fires
MIN_BASELINE_YEARS = 8
TARGET_YEARS = ("2019", "2020", "2021", "2023", "2024", "2025")
WEEKS = range(6, 50)


def _week_total(detections: dict, year: str, week: int) -> int:
    total = 0
    for day, count in detections.get(year, {}).items():
        y, m, d = (int(part) for part in day.split("-"))
        if date(y, m, d).isocalendar()[1] == week:
            total += count
    return total


def _load() -> dict:
    out = {}
    for name in os.listdir(FULL_HISTORY):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(FULL_HISTORY, name)) as handle:
            doc = json.load(handle)
        complete = sorted(y for y in doc.get("_complete", [])
                          if len(doc.get(y, {})) >= 300)
        if len(complete) >= MIN_BASELINE_YEARS:
            out[name[:3]] = (doc, complete)
    return out


def _candidates(series: dict, target: str, week: int) -> list[tuple]:
    """(iso, multiple, z, cv, current, best_prior) for one country-week."""
    rows = []
    for iso, (doc, complete) in series.items():
        if target not in complete:
            continue
        hist = [_week_total(doc, y, week) for y in complete
                if y < target]
        hist = [h for h in hist if h > 0]
        if len(hist) < MIN_BASELINE_YEARS:
            continue
        current = _week_total(doc, target, week)
        if current < NOISE_FLOOR:
            continue
        mean = st.mean(hist)
        sd = st.pstdev(hist)
        if not mean or not sd:
            continue
        rows.append((iso, current / mean, (current - mean) / sd,
                     sd / mean, current, max(hist)))
    return rows


def _fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(table at least this extreme | margins fixed)."""
    def logf(n):
        return math.lgamma(n + 1)
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c
    total = 0.0
    for k in range(max(0, c1 - r2), min(r1, c1) + 1):
        p = math.exp(logf(r1) + logf(r2) + logf(c1) + logf(n - c1) - logf(n)
                     - logf(k) - logf(r1 - k) - logf(c1 - k) - logf(r2 - c1 + k))
        if k >= a:
            total += p
    return total


def report() -> None:
    series = _load()
    print(f"{len(series)} countries with at least {MIN_BASELINE_YEARS} "
          f"complete years\n")

    volatility_of_drawn = {"multiple": [], "z": []}
    overlaps, differing, weeks = [], 0, 0
    only_z, only_multiple = [], []

    for week in WEEKS:
        for target in TARGET_YEARS:
            rows = _candidates(series, target, week)
            if len(rows) < SLOTS:
                continue
            weeks += 1
            by_multiple = sorted(rows, key=lambda r: -r[1])[:SLOTS]
            by_z = sorted(rows, key=lambda r: -r[2])[:SLOTS]
            volatility_of_drawn["multiple"] += [r[3] for r in by_multiple]
            volatility_of_drawn["z"] += [r[3] for r in by_z]

            set_m = {r[0] for r in by_multiple}
            set_z = {r[0] for r in by_z}
            overlaps.append(len(set_m & set_z))
            if set_m != set_z:
                differing += 1
                index = {r[0]: r for r in rows}
                only_z += [index[i] for i in (set_z - set_m)]
                only_multiple += [index[i] for i in (set_m - set_z)]

    print(f"{weeks} country-weeks sampled, top {SLOTS} drawn by each rule")
    print(f"  the two bars differ in {differing} of {weeks} weeks "
          f"({100 * differing / weeks:.0f}%), median overlap "
          f"{st.median(overlaps):.0f} of {SLOTS}\n")

    print("THE MECHANISM I ASSERTED, AND ITS REFUTATION.")
    print("  baseline volatility (sd/mean) of the countries each bar draws:")
    for label, values in volatility_of_drawn.items():
        print(f"    {label:<10} median CV {st.median(values):.2f}  "
              f"(n={len(values)})")
    print("  Same. A multiple bar does NOT preferentially draw erratic")
    print("  countries, which is what I told design before measuring it.\n")

    def at_record(rows):
        return sum(1 for r in rows if r[4] >= r[5])

    a, c = at_record(only_z), at_record(only_multiple)
    b, d = len(only_z) - a, len(only_multiple) - c
    print("THE MECHANISM THAT SURVIVES, on the marginal picks only.")
    print(f"    only z draws          n={len(only_z):<5} "
          f"{100 * a / max(1, len(only_z)):.0f}% at a record  ({a})")
    print(f"    only the multiple     n={len(only_multiple):<5} "
          f"{100 * c / max(1, len(only_multiple)):.0f}% at a record  ({c})")
    print(f"    one-sided Fisher exact p = {_fisher_one_sided(a, b, c, d):.3f}")
    print()
    print("  Read the effect size, not just the p value: the bars agree in")
    print("  most weeks, so this changes about one mark in under half of")
    print("  them. The argument is not that the map changes much. It is that")
    print("  when it changes, one bar is right and the other is wrong.")


if __name__ == "__main__":
    report()
