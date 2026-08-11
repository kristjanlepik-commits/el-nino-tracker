"""Assemble Tallinn from Keskkonnaagentuur's archive, Harku only.

HARKU ONLY, AND THE OMISSION IS THE WHOLE FILE. The archive Keskkonnaagentuur
sent on 2026-08-11 contains FOUR Tallinn stations in relay:

    Majakas    1919-1949        Ulemiste   1937-1980
    Kose       1948-1964        Harku      1980-2026

Reading them as one 107-year Tallinn record is the obvious thing to do and it
is the Murcia error at four times the scale. Harku is the station that reports
today, so Harku is the only one we may rank a 2026 value against.

THE ROUTE THIS REPLACES WAS THE ERROR ITSELF. GHCN EN000026038 advertises
1936-2025 with a full baseline, which is why it looked like the answer before
the archive arrived. Measured against Keskkonnaagentuur:

    GHCN vs Harku     1980-1989   100.00% identical
    GHCN vs Harku     1990-2025    66.90%
    GHCN vs Ulemiste  1960-1979    75.89%

Perfect agreement with one station for one decade and then divergence: the
blend signature. A Tallinn built on GHCN would have ranked a 2026 Harku value
against a history that is not Harku.

WHAT HARKU ALONE COSTS, and why this file is not yet wired in:

    1971-2000   our percentile baseline    21/30   BELOW THE BAR OF 27
    1991-2020   WMO current normal         30/30   complete
    1981-2010   previous WMO normal        30/30   complete

So Tallinn needs a per-city baseline period, which is a change to a constant
product ratified, and it is with them. This builder writes the series either
way; nothing here depends on the ruling. If the answer is no, Tallinn waits
for Harku to accumulate baseline years and this file waits with it.

The hourly collector is retired. It sampled instantaneous temperature, which
sits warm against a true minimum, so its days could never have joined this
archive without reproducing the cross-instrument error a second time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
BOOK = ROOT / "heat" / "data" / "official" / "tallinn_keskkonnaagentuur.xlsx"
OUT = SRC / "tallinn.json"
PROV = ROOT / "heat" / "data" / "tallinn_provenance.json"

# Column indices in the supplied workbook. Harku's minimum and maximum only.
# The other six columns are three other stations and are deliberately unread.
HARKU_MIN, HARKU_MAX = 3, 4


def main() -> int:
    if not BOOK.exists():
        print(f"  missing {BOOK.relative_to(ROOT)}", file=sys.stderr)
        return 1
    import openpyxl
    rows = list(openpyxl.load_workbook(BOOK, data_only=True)["Leht1"]
                .iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and r[0] == "Aasta")
    out = {}
    for r in rows[hdr + 1:]:
        if not r or r[0] is None:
            continue
        try:
            y, m, d = int(r[0]), int(r[1]), int(r[2])
        except (TypeError, ValueError):
            continue

        def num(i):
            v = r[i] if i < len(r) else None
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        mn, mx = num(HARKU_MIN), num(HARKU_MAX)
        if mn is None and mx is None:
            continue
        out[f"{y}-{m:02d}-{d:02d}"] = (mn, mx)

    OUT.write_text(json.dumps([[d, mn, mx] for d, (mn, mx) in sorted(out.items())]))
    yrs = sorted({int(d[:4]) for d in out})

    def usable(lo, hi):
        per = {}
        for d, (mn, mx) in out.items():
            if mn is not None and mx is not None and d[5:7] in ("05", "06", "07", "08"):
                per[int(d[:4])] = per.get(int(d[:4]), 0) + 1
        return sum(1 for y in range(lo, hi + 1) if per.get(y, 0) >= 100)

    d26 = sorted(d for d in out if d.startswith("2026"))
    PROV.write_text(json.dumps({
        "station": "Tallinn-Harku, WMO 26038",
        "source": "Keskkonnaagentuur, Estonian Environment Agency",
        "attribution": "Source: Keskkonnaagentuur",
        "history": f"{min(yrs)}-{max(yrs)}",
        "stations_in_archive_NOT_used": ["Tallinn-Majakas 1919-1949",
                                         "Tallinn-Kose 1948-1964",
                                         "Tallinn-Ulemiste 1937-1980"],
        "why_not_used": "four stations in relay are not one record. Ranking a "
                        "2026 Harku value against another station's history "
                        "is the Murcia error.",
        "baseline_coverage": {"1971-2000": usable(1971, 2000),
                              "1981-2010": usable(1981, 2010),
                              "1991-2020": usable(1991, 2020)},
        "blocked_on": "a per-city baseline period, with product",
        "season_2026": {"days": len(d26),
                        "first": d26[0] if d26 else None,
                        "last": d26[-1] if d26 else None},
    }, indent=1) + "\n")
    print(f"  Harku {min(yrs)}-{max(yrs)}, {len(out)} days")
    print(f"  baseline usable: 1971-2000 {usable(1971,2000)}/30, "
          f"1981-2010 {usable(1981,2010)}/30, 1991-2020 {usable(1991,2020)}/30")
    print(f"  2026: {len(d26)} days, {d26[0] if d26 else '-'} to "
          f"{d26[-1] if d26 else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
