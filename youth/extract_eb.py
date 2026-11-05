#!/usr/bin/env python3
"""Pull the index's cells out of the Eurobarometer Volume C workbooks.

    extract_eb.py --tables DIR --flash FILE

DIR holds one folder per wave (103, 104, 105) with the unzipped Volume C
workbooks from the EC open data portal; FILE is Flash 585 Volume A. The
workbooks are 100MB of tables we use six sheets of, so they stay out of the
repo and only the cells used are committed, to youth/data/eb_cells.json.

Sheet and column map: youth/SPEC.md section 13. Rows are bilingual: the
French row holds rounded weighted counts and the English row the share, so
rows are found by English label, never by position.
"""
import argparse
import glob
import json
import re
from pathlib import Path

import openpyxl

EU27 = ("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL "
        "PT RO SE SI SK").split()
COUNTRIES = EU27 + ["UK"]

# wave -> item -> sheet, from the G1 variable table
SHEETS = {
    "103": {"gov": "QA6_10", "parl": "QA6_11", "parties": "QA6_2",
            "democracy": "SD18a", "direction": "D73_1", "direction_life": "D73_4"},
    "104": {"gov": "QA6_7", "parl": "QA6_8", "parties": "QA6_1",
            "democracy": "SD18a", "direction": "D73_1", "direction_life": "D73_4"},
    "105": {"gov": "QA6_10", "parl": "QA6_11", "parties": "QA6_2",
            "democracy": "SD18a", "direction": "D73_1", "direction_life": "D73_4"},
}
ITEM_CHECK = {"gov": "Government", "parl": "PARLIAMENT", "parties": "Political parties",
              "democracy": "democracy works in", "direction": "(OUR COUNTRY)",
              "direction_life": "Your life personally"}
HEADER_ROW, BASE_ROW = 8, 9
COLUMNS = {"total": 2, "y1524": 5, "o55": 8, "gz": 20}
COLUMN_CHECK = {"y1524": "15-24", "o55": "55+", "gz": "1997"}

# item family -> answer labels, (numerator, rest of the base)
ANSWERS = {
    "trust": (("Tend not to trust",), ("Tend to trust",)),
    "democracy": (("Not very satisfied", "Not at all satisfied"),
                  ("Very satisfied", "Fairly satisfied")),
    "direction": (("Things are going in the wrong direction",),
                  ("Things are going in the right direction",)),
}
FAMILY = {"gov": "trust", "parl": "trust", "parties": "trust", "democracy": "democracy",
          "direction": "direction", "direction_life": "direction"}


def clean(value):
    """A share cell: "-" is the tables' zero, anything else non-numeric is an error."""
    if value == "-":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"unexpected cell {value!r}")


def read_sheet(ws, item):
    rows = list(ws.iter_rows(max_row=30, values_only=True))
    text = " ".join(str(v) for r in rows[2:5] for v in r if isinstance(v, str))
    if ITEM_CHECK[item] not in text:
        raise ValueError(f"{ws.title} is not {item}: {text[-80:]}")
    for col, needle in COLUMN_CHECK.items():
        if needle not in str(rows[HEADER_ROW][COLUMNS[col]]):
            raise ValueError(f"{ws.title} column {col} is {rows[HEADER_ROW][COLUMNS[col]]!r}")
    if not str(rows[BASE_ROW][1]).startswith("Weighted Base"):
        raise ValueError(f"{ws.title} base row is {rows[BASE_ROW][1]!r}")
    labelled = {re.sub(r"\s+", " ", str(r[1])).strip(): (r, rows[i + BASE_ROW])
                for i, r in enumerate(rows[BASE_ROW + 1:], 1) if r[1]}
    bad, rest = ANSWERS[FAMILY[item]]
    out = {}
    for col, j in COLUMNS.items():
        num = sum(clean(labelled[a][0][j]) for a in bad)
        den = num + sum(clean(labelled[a][0][j]) for a in rest)
        # The row above each English share holds its weighted count, for check C1.
        count_num = sum(clean(labelled[a][1][j]) for a in bad)
        count_den = count_num + sum(clean(labelled[a][1][j]) for a in rest)
        out[col] = {"share": round(num / den, 6), "base": clean(rows[BASE_ROW][j]),
                    "answered": round(den, 4), "count_num": count_num, "count_den": count_den}
    return out


def read_flash(path):
    """Q18.1, share disagreeing among those answering, and Q7a, share yes.

    Labelled rows here hold weighted counts, with the share unlabelled below,
    so both are computed from counts.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for sheet, key in (("Q18.1", "q18_1_disagree"), ("Q7a", "q7a_yes")):
        rows = list(wb[sheet].iter_rows(max_row=40, values_only=True))
        codes = {v: j for j, v in enumerate(rows[8]) if isinstance(v, str)}
        labelled = {str(r[1]).strip(): r for r in rows[10:] if isinstance(r[1], str)}
        for code, j in codes.items():
            if sheet == "Q18.1":
                bad = clean(labelled["Total 'Disagree'"][j])
                good = clean(labelled["Total 'Agree'"][j])
                value = bad / (bad + good)
            else:
                value = clean(labelled["Yes"][j]) / clean(labelled["Base: Total (weighted)"][j])
            out.setdefault(code, {})[key] = round(value, 6)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--flash", required=True)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "eb_cells.json"))
    args = ap.parse_args()

    cells = {}
    for wave, sheets in SHEETS.items():
        for country in COUNTRIES:
            found = [f for f in glob.glob(f"{args.tables}/{wave}/*")
                     if re.search(rf"[ _]C_{country}\.xlsx$", f)]
            if len(found) != 1:
                raise SystemExit(f"wave {wave} {country}: expected 1 workbook, got {found}")
            wb = openpyxl.load_workbook(found[0], read_only=True, data_only=True)
            for item, sheet in sheets.items():
                cells.setdefault(wave, {}).setdefault(country, {})[item] = read_sheet(wb[sheet], item)
            wb.close()

    Path(args.out).parent.mkdir(exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"source": "Standard Eurobarometer 103, 104, 105, Volume C, EC open data portal, COM_REUSE. "
                   "Flash Eurobarometer 585 Volume A, same licence.",
         "share_is": "share giving the discontented answer, don't-knows and spontaneous 'neither' excluded",
         "cells": cells, "flash585": read_flash(args.flash)}, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
