#!/usr/bin/env python3
"""Pull the 2019 reference for the since-2019 marker into youth/data/eb_2019.json.

    extract_2019.py --zips DIR

DIR holds the Standard Eurobarometer 91 and 92 Volume C archives from the EC open
data portal: 91_at-hu.zip, 91_ie-wg.zip (zips of zips) and 92_AL-IE.zip, 92_IT-UK.zip.
These are .xls, so this one script needs xlrd, which is not in the project venv.

Both periods use 15-24 for the marker: a generation ages, an age band does not.
SD18a is absent from the tables checked, so the marker covers distrust and direction.
"""
import argparse
import io
import json
import re
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import xlrd

EU27 = ("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL "
        "PT RO SE SI SK").split()
COUNTRIES = EU27 + ["UK"]
OUT = Path(__file__).parent / "data" / "eb_2019.json"
ITEMS = {"gov": r"\(NATIONALITY\) Government", "parl": r"NATIONALITY PARLIAMENT|\(NATIONALITY\) Parliament",
         "parties": r"Political parties"}
ANSWERS = {"trust": ("Tend not to trust", "Tend to trust"),
           "direction": ("Things are going in the wrong direction", "Things are going in the right direction")}


def workbooks(zip_dir):
    """Yield (wave, country, xls bytes) through the nesting of both archive styles."""
    for name in ("91_at-hu.zip", "91_ie-wg.zip", "92_AL-IE.zip", "92_IT-UK.zip"):
        wave = name[:2]
        outer = zipfile.ZipFile(Path(zip_dir) / name)
        stack = [outer]
        while stack:
            z = stack.pop()
            for member in z.namelist():
                if member.endswith(".zip"):
                    if "eb_92_volume_C.zip" not in member:
                        stack.append(zipfile.ZipFile(io.BytesIO(z.read(member))))
                    continue
                m = re.search(r"[ _]C_([A-Za-z]{2,5})\.xls$", member)
                if m and m.group(1).upper() in COUNTRIES:
                    yield wave, m.group(1).upper(), z.read(member)


def read_sheet(sh, family):
    text = " ".join(str(sh.cell_value(r, c)) for r in range(min(8, sh.nrows))
                    for c in range(min(14, sh.ncols)) if isinstance(sh.cell_value(r, c), str))
    header = next(r for r in range(sh.nrows) if "15-24" in [str(v).strip() for v in sh.row_values(r)])
    col = [str(v).strip() for v in sh.row_values(header)].index("15-24")
    bad, good = ANSWERS[family]
    values, base = {}, None
    for r in range(header + 1, min(sh.nrows, header + 30)):
        label = next((str(v).strip() for v in sh.row_values(r)[:3] if isinstance(v, str) and v.strip()), "")
        cell = sh.cell_value(r, col)
        if base is None and isinstance(cell, (int, float)) and cell > 1:
            base = cell
        norm = re.sub(r"\s+", " ", label)
        if norm in (bad, good):
            values[norm] = 0.0 if cell == "-" else float(cell)
    return text, values[bad] / (values[bad] + values[good]), base


def read_book(job):
    wave, country, blob = job
    wb = xlrd.open_workbook(file_contents=blob, on_demand=True)
    out = {}
    for name in wb.sheet_names():
        if re.match(r"^QA6[a-z]?[._]\d+$", name):
            sh = wb.sheet_by_name(name)
            head = " ".join(str(v) for r in range(min(8, sh.nrows)) for v in sh.row_values(r) if isinstance(v, str))
            for item, pattern in ITEMS.items():
                if re.search(pattern, head):
                    _, share, base = read_sheet(sh, "trust")
                    out[item] = {"share": share, "base": base}
        elif re.match(r"^D73[a-z]?[._]1$", name):
            _, share, base = read_sheet(wb.sheet_by_name(name), "direction")
            out["direction"] = {"share": share, "base": base}
    return wave, country, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True)
    args = ap.parse_args()
    cells = {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        for wave, country, items in pool.map(read_book, workbooks(args.zips), chunksize=1):
            cells.setdefault(wave, {})[country] = items
            print(wave, country, sorted(items), flush=True)
    missing = [(w, c) for w in ("91", "92") for c in COUNTRIES
               if set(cells.get(w, {}).get(c, {})) != {"gov", "parl", "parties", "direction"}]
    OUT.write_text(json.dumps({
        "source": "Standard Eurobarometer 91 (June-July 2019) and 92 (Nov-Dec 2019), Volume C, 15-24",
        "missing": missing, "cells": cells}, indent=1))
    print("missing", missing)


if __name__ == "__main__":
    main()
