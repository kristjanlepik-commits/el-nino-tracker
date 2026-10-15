"""Base rate for "twice in three weeks", computed from history only, BEFORE the
second DANA (floods/prereg/spain_dana2_2026-10.md, addendum 297e5366).

A qualifying storm: a day with at least T mm at any of five stations (Fabra,
Reus, Tortosa, Castello, Valencia Aeropuerto); qualifying days within 3 days
of each other are one storm, dated by its first day. "Twice" means a storm
whose first day is 21 days or less after the previous storm's first day.
Counted 1978-2025 at a gradient of thresholds (CPO, 15 Oct), so that the
100 mm choice is not what decides whether "twice" is unusual.

Run:  .venv/bin/python floods/twice_base_rate.py
"""
import datetime as dt
import json
import os

import spain_dana_judge as J

HERE = os.path.dirname(os.path.abspath(__file__))
FIVE = ["0200E", "0016A", "9981A", "8500A", "8414A"]
Y0, Y1 = 1978, 2025
THRESHOLDS = [80, 100, 120, 150]


def storms(rains, t):
    days = sorted({d for r in rains.values() for d, v in r.items()
                   if v is not None and v >= t and Y0 <= d.year <= Y1})
    out = []
    for d in days:
        if out and (d - out[-1][-1]).days <= 3:
            out[-1].append(d)
        else:
            out.append([d])
    return [s[0] for s in out]


def main():
    rains = {sid: J.load(sid) for sid in FIVE}
    gaps = {sid: sum(1 for y in range(Y0, Y1 + 1)
                     for k in range((dt.date(y, 12, 31) - dt.date(y, 1, 1)).days + 1)
                     if rains[sid].get(dt.date(y, 1, 1) + dt.timedelta(k)) is None)
            for sid in FIVE}
    res = {"definition": __doc__.split("\n\n")[1].replace("\n", " "), "span": [Y0, Y1],
           "unreported_days_in_span": gaps, "thresholds": {}}
    print(f"{Y0}-{Y1}, five stations; unreported days in span: {gaps}")
    for t in THRESHOLDS:
        s = storms(rains, t)
        pairs = [(a, b) for a, b in zip(s, s[1:]) if (b - a).days <= 21]
        years = sorted({b.year for _, b in pairs})
        res["thresholds"][str(t)] = {
            "storms": len(s), "storms_per_year": round(len(s) / (Y1 - Y0 + 1), 2),
            "second_storms_within_21_days": len(pairs), "years_with_one": years,
            "pairs": [[a.isoformat(), b.isoformat()] for a, b in pairs]}
        print(f"  >= {t:>3} mm: {len(s):>3} storms ({len(s)/(Y1-Y0+1):.2f}/yr); "
              f"{len(pairs)} times a second came within 21 days, in {len(years)} of "
              f"{Y1-Y0+1} years: {[(a.isoformat(), b.isoformat()) for a, b in pairs]}")
    json.dump(res, open(os.path.join(HERE, "data", "twice_base_rate_1978_2025.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
