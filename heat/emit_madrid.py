"""Emit the Madrid tropical-nights payload design renders from.

D-030 seam. Computed from the two sources, never transcribed.

ONE INSTRUMENT, TWO PUBLISHERS. ECA&D station 230 and AEMET station 3195 are
the same thermometer in the Retiro; ECA&D's blend header names AEMET as its
source. Verified rather than assumed: 332 overlapping days, every one identical
to 0.1 C, maximum difference 0.0. So the historical/current join is not a
cross-source composition and carries no composition caveat.

D-051: every number carries its own qualifier as a field.

TWO COMPARISONS ARE EMITTED, BOTH LABELLED, because they answer different
questions and one of them flatters the claim. The partial-year-against-whole-
year framing (51 so far against a 35 whole-year normal) is arithmetically true
and compares unlike things. The matched framing (both to the same calendar day)
is like-for-like and, as it happens, stronger. Product asked for both so editor
can choose; the matched one is marked preferred.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ECA = ROOT / "heat/.cache/madrid_tn.txt"
AEM = ROOT / "heat/.cache/aemet_madrid_2025_2026.json"
OUT = ROOT / "heat/data/madrid_nights.json"

CUT = (8, 2)          # as-of day: AEMET's latest complete day


def main() -> int:
    tot, miss = defaultdict(int), defaultdict(int)
    full, todate = defaultdict(int), defaultdict(int)
    for line in open(ECA, encoding="latin-1"):
        m = re.match(r"\s*230,\s*\d+,\s*(\d{4})(\d{2})(\d{2}),\s*(-?\d+),\s*(\d)", line)
        if not m:
            continue
        y, mo, d, t, q = (int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))
        tot[y] += 1
        if q == 9:
            miss[y] += 1
            continue
        if t >= 200:                       # 20.0 C, file is in 0.1 C
            full[y] += 1
            if (mo, d) <= CUT:
                todate[y] += 1
    good = [y for y in sorted(tot) if tot[y] - miss[y] >= 330]

    aem = json.load(open(AEM))
    cur = [(d, t) for d, t in aem["2026"] if t >= 20.0]
    n_cur, asof = len(cur), aem["2026"][-1][0]

    def avg(src, a, b):
        s = [src[y] for y in good if a <= y <= b]
        return round(sum(s) / len(s), 1), len(s)

    whole91, _ = avg(full, 1991, 2020)
    match91, n91 = avg(todate, 1991, 2020)
    match61, n61 = avg(todate, 1961, 1990)
    rank = sum(1 for y in good if todate[y] >= n_cur) + 1
    prev = sorted(((todate[y], y) for y in good), reverse=True)[:5]

    payload = {
        "_readme":
            "Nights in Madrid that never dropped below 20 C, per year. The "
            "record of ONE THERMOMETER in the city, city warming included. It "
            "is not a climate measurement and must never be called drift or "
            "share a sentence with one.",
        "channel": "heat", "place": "Madrid",
        "evidence_basis": "Measured",
        "attribution": "Not ENSO-linked",
        "definition": {
            "name": "Tropical night",
            "rule": "daily minimum temperature at or above 20.0 C",
            "standard": "ETCCDI index TR, as published by European met "
                        "services. Not a threshold we chose.",
        },
        "station": {
            "name": "MADRID RETIRO", "km_from_centre": 2, "elevation_m": 667,
            "ids": {"aemet": "3195", "ecad": "230"},
            "note": "One station, 2 km from the centre. Not a grid box and not "
                    "a regional average.",
        },
        "sources": {
            "historical": {"who": "ECA&D blended daily minima, station 230",
                           "covers": f"{good[0]}-{good[-1]}",
                           "file_dated": "2026-07-11"},
            "current": {"who": "AEMET OpenData, station 3195",
                        "covers": "2026", "as_of": asof, "lag_days": 3},
            "same_instrument": True,
            "verification": "332 overlapping days compared day by day; every "
                            "one identical to 0.1 C, maximum difference 0.0. "
                            "ECA&D relays AEMET for this station and names it "
                            "in the blend header. Not a cross-source "
                            "composition.",
        },
        "current_year": {
            "value": n_cur, "as_of": asof,
            "complete": False,
            "note": "Partial year. August and September, which carry most of "
                    "Madrid's hot nights, are not finished.",
        },
        "comparison_matched": {
            "preferred": True,
            "question": "Is this year unusual for this point in the year?",
            "value": n_cur, "as_of": asof,
            "vs_1991_2020": match91, "vs_1961_1990": match61,
            "ratio_1991_2020": round(n_cur / match91, 1),
            "ratio_1961_1990": round(n_cur / match61, 1),
            "n_years_1991_2020": n91, "n_years_1961_1990": n61,
            "rank": rank, "of_years": len(good) + 1,
            "previous_highest_to_date": [{"year": y, "nights": v} for v, y in prev],
            "note": "Like for like: every year counted to the same calendar "
                    "day. This is the defensible framing and it is also the "
                    "stronger one.",
        },
        "comparison_whole_year": {
            "preferred": False,
            "question": "How does this year so far compare to a typical "
                        "complete year?",
            "value_so_far": n_cur, "as_of": asof,
            "whole_year_normal_1991_2020": whole91,
            "warning": "COMPARES A PARTIAL YEAR TO A COMPLETE ONE, which "
                       "favours the claim. Only usable if 'so far' and 'whole "
                       "year' appear in the same breath. The matched "
                       "comparison says more and says it cleanly.",
        },
        "series_full_year": {str(y): full[y] for y in good},
        "series_to_same_day": {str(y): todate[y] for y in good},
        "gaps": [y for y in range(good[0], good[-1] + 1) if y not in good],
        "qualifier": "This is what one thermometer in Madrid recorded. The "
                     "city grew around it and a city warms its own nights; "
                     "that warming is part of what people there experienced "
                     "and belongs in the count. It is not a measure of climate "
                     "and is never presented as one.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(f"  {n_cur} nights to {asof}, rank {rank} of {len(good)+1}")
    print(f"  matched: {match91} (1991-2020), {match61} (1961-1990)")
    print(f"  whole-year normal: {whole91}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
