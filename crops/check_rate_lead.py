"""Gate: never lead on a rate claim without running this first.

Roughly HALF of all rate-based leads are inflated by construction. Of
the 20 places at rank 1 on the raw 4-dekad change on 2026-07-11, nine
lose rank 1 once the level they fell from is controlled for, and
fourteen started in their top four June levels on record. England was
rank 1 by a margin of 0.025 and rank 2 adjusted; South Africa goes from
rank 1 to rank 23.

This exists as a command rather than as a rule in a document because
the person who needs it next will not think to look for it. Trap 17.

    .venv/bin/python crops/check_rate_lead.py England France Hungary
    .venv/bin/python crops/check_rate_lead.py --all-rank1

Regions are matched too, so `England` works as well as `France`.

WHAT IT PRINTS AND WHY. The adjusted rank is a FITTED quantity: it
removes a linear fit of change on starting level. It is a diagnostic
and must never reach a page, because publishing a fitted number is
original modelling, which the build philosophy forbids. What may be
published is start_value and start_rank, which are measured, and which
the emitted statement already carries.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "asap_indicator"
DATA = HERE / "data" / "stress_current.json"
BASE_FIRST = 2001
BACK = 4


def _panels(cid):
    f = CACHE / f"zfparc_crop_growing_{cid}.csv"
    if not f.exists():
        return None, None
    d = pd.read_csv(f, usecols=["region_name", "date", "value"])
    if d.empty:
        return None, None
    d["dt"] = pd.to_datetime(d.date, format="%Y%m%d")
    d["year"] = d.dt.dt.year
    d["doy"] = (d.dt.dt.month - 1) * 3 + ((d.dt.dt.day - 1) // 10) + 1
    country = d.groupby(["year", "doy"]).value.mean().unstack()
    regions = {r: g.groupby(["year", "doy"]).value.mean().unstack()
               for r, g in d.groupby("region_name")}
    return country, regions


def diagnose(pv, doy, cur_year):
    a, b = doy - BACK, doy
    if pv is None or a not in pv.columns or b not in pv.columns:
        return None
    ch = (pv[b] - pv[a]).dropna().round(3)
    st = pv[a].dropna()
    idx = ch.index.intersection(st.index)
    idx = [y for y in idx if BASE_FIRST <= y <= cur_year]
    if cur_year not in idx or len(idx) < 20:
        return None
    ch, st = ch.loc[idx], st.loc[idx]
    cur = float(ch.loc[cur_year])
    raw = int((ch.drop(index=cur_year) < cur).sum()) + 1
    runner = ch.drop(index=cur_year).min()
    slope, ic, *_ = stats.linregress(st.values, ch.values)
    res = ch - (slope * st + ic)
    adj = int((res.drop(index=cur_year) < res.loc[cur_year]).sum()) + 1
    srank = int((st.drop(index=cur_year) > st.loc[cur_year]).sum()) + 1
    return {"change": cur, "raw": raw, "adjusted": adj, "of": len(idx),
            "start": float(st.loc[cur_year]), "start_rank": srank,
            "margin": cur - runner,
            "corr": float(np.corrcoef(st.values, ch.values)[0, 1])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--all-rank1", action="store_true")
    args = ap.parse_args()

    doc = json.loads(DATA.read_text(encoding="utf-8"))
    cur_year = int(doc["dekad"][:4])
    cat = json.loads((HERE / "asap_countries.json").read_text(
        encoding="utf-8"))["countries"]
    by = {v: k for k, v in cat.items()}

    targets = list(args.names)
    if args.all_rank1:
        targets += [p["place"] for p in doc["places"]
                    if p.get("rate", {}).get("rank") == 1]
    if not targets:
        print("name at least one place, or pass --all-rank1")
        return 2

    print(f"{'place':30s} {'change':>8s} {'raw':>5s} {'adj':>5s} "
          f"{'start':>7s} {'srank':>6s} {'margin':>8s}  verdict")
    failed = 0
    for want in targets:
        hit = None
        for p in doc["places"]:
            doy = None
            if p["place"] == want or want in p["place"]:
                cid = by.get(p["place"])
                c, _ = _panels(cid) if cid else (None, None)
                doy = (int(p["dekad"][5:7]) - 1) * 3 + \
                      ((int(p["dekad"][8:10]) - 1) // 10) + 1
                hit = (p["place"], diagnose(c, doy, cur_year))
                break
            for r in p["regions"]:
                if r["region"] == want:
                    cid = by.get(p["place"])
                    _, regs = _panels(cid) if cid else (None, None)
                    doy = (int(p["dekad"][5:7]) - 1) * 3 + \
                          ((int(p["dekad"][8:10]) - 1) // 10) + 1
                    hit = (f"{p['place']}/{want}",
                           diagnose((regs or {}).get(want), doy, cur_year))
                    break
            if hit:
                break
        if not hit or hit[1] is None:
            print(f"{want:30s}  no rate available")
            continue
        nm, d = hit
        # Truncating from the left hides WHICH place a row describes:
        # England and Wales both rendered as "U.K. of Great Britain and
        # Nort". On a tool whose only job is keeping a number attached
        # to its place, that is the wrong thing to lose, so the
        # distinguishing end is the end that survives.
        if len(nm) > 30:
            nm = "..." + nm[-27:]
        ok = d["adjusted"] == d["raw"]
        if not ok:
            failed += 1
        verdict = ("holds" if ok else
                   f"INFLATED: rank {d['raw']} raw, {d['adjusted']} adjusted")
        print(f"{nm[:30]:30s} {d['change']:+8.3f} {d['raw']:5d} "
              f"{d['adjusted']:5d} {d['start']:+7.3f} {d['start_rank']:6d} "
              f"{d['margin']:+8.3f}  {verdict}")

    print()
    print("  srank 1 = highest starting level on record. A steep fall from "
          "a high start is\n  partly regression toward the mean: correlation "
          "of start against change is about\n  -0.38 across the reported "
          "places.")
    print("  margin is the gap to the next-steepest year. A small margin on "
          "a rank-1 claim\n  is a claim that a rounding decision could move.")
    print("  ADJUSTED RANK IS A DIAGNOSTIC AND NEVER PUBLISHABLE: it is "
          "fitted, and a fitted\n  number on a page is original modelling. "
          "Publish start_value and start_rank.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
