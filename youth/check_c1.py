#!/usr/bin/env python3
"""Check C1 from youth/SPEC.md: the Volume C totals we extracted match Volume A.

    check_c1.py --volume-a DIR

DIR holds 103_A.xlsx, 104_A.xlsx, 105_A.xlsx from the EC open data portal.
Volume A is a separate table of the same wave, so a misread sheet, column or
row in the extractor shows up as a mismatch. Exits non-zero on any cell more
than 0.5 points out.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import openpyxl

from extract_eb import ANSWERS, COUNTRIES, FAMILY, SHEETS, clean

TOLERANCE = 0.005


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--volume-a", required=True)
    args = ap.parse_args()

    cells = json.loads((Path(__file__).parent / "data" / "eb_cells.json").read_text())["cells"]
    checked, bad = 0, []
    for wave, sheets in SHEETS.items():
        wb = openpyxl.load_workbook(f"{args.volume_a}/{wave}_A.xlsx", read_only=True, data_only=True)
        for item, sheet in sheets.items():
            rows = list(wb[sheet].iter_rows(max_row=30, values_only=True))
            header = {str(v).split("\n")[-1].strip(): j for j, v in enumerate(rows[8]) if v}
            # Count rows sit above the share rows. Compared on counts, because shares are
            # rounded to a point and a value at x.5 flips between the two tables on its own.
            labelled = {re.sub(r"\s+", " ", str(r[1])).strip(): rows[i + 8]
                        for i, r in enumerate(rows[9:], 1) if r[1]}
            bad_labels, rest = ANSWERS[FAMILY[item]]
            for country in COUNTRIES:
                j = header[country]
                num = sum(clean(labelled[a][j]) for a in bad_labels)
                den = num + sum(clean(labelled[a][j]) for a in rest)
                total = cells[wave][country][item]["total"]
                checked += 1
                diff = abs(num / den - total["count_num"] / total["count_den"])
                if diff > TOLERANCE:
                    bad.append((wave, country, item, round(diff, 4)))
    print(f"C1: {checked} cells checked, {len(bad)} more than {TOLERANCE * 100} points out")
    for row in bad[:20]:
        print(" ", row)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
