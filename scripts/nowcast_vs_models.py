"""What the observed ocean says, against forecasts that predate it.

Kristjan asked how CPC, SEAS5 and NMME might move, given all three were
issued around a month before the brief that carries them. This estimates
the gap from observations they did not have.

TWO THINGS THAT ARE EASY TO GET WRONG AND ARE THE POINT OF THE FILE.

1. The ANCHOR is not a month stale. It is CPC's strength bins converted
   through the LIVE RONI-to-ONI offset, which re-derives weekly from
   OISST. Only the CONSENSUS (SEAS5 plus NMME) is genuinely frozen.
   Calling the whole headline "a month old" overstates it.

2. The weekly-to-ONI gap CANNOT be calibrated across eras. The ONI uses a
   CENTRED 30-year base, so 1997 and 2015 sit on cooler climatologies than
   the weekly series' fixed 1991-2020 base, and their gap has the opposite
   SIGN to 2026's for that reason alone. Only the current year's own gap
   is usable. Using the analogs' gap here would push the nowcast the wrong
   way by roughly a quarter of a degree.

A season is used only when EVERY month in it has weekly data. A partial
season averaged as if complete is how a rising series reads high.
"""
import collections, csv, json, re, statistics as st, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEKLY_URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
MON = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,
       'SEP':9,'OCT':10,'NOV':11,'DEC':12}
SEASONS = [('AMJ',(4,5,6)),('MJJ',(5,6,7)),('JJA',(6,7,8)),
           ('JAS',(7,8,9)),('ASO',(8,9,10))]


def weekly():
    req = urllib.request.Request(WEEKLY_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode("utf-8", "replace")
    out = collections.defaultdict(list)
    for line in txt.splitlines():
        p = line.split()
        if len(p) == 9 and re.match(r"^\d{2}[A-Z]{3}\d{4}$", p[0]):
            out[(int(p[0][5:]), MON[p[0][2:5]])].append(float(p[6]))
    return out


def main(year=2026):
    wk = weekly()
    cache = json.loads((ROOT / ".fetch_cache" / "oni_history_last_good.json").read_text())
    oni_cur = cache["payload"]["by_year"][str(year)]
    hist = collections.defaultdict(dict)
    with open(ROOT / "data" / "oni_full_history.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            hist[int(r["year"])][r["season"].upper()] = float(r["oni"])

    gaps, complete_seasons = [], []
    for lab, mos in SEASONS:
        if not all(wk.get((year, m)) for m in mos):
            continue
        w = st.mean([x for m in mos for x in wk[(year, m)]])
        v = oni_cur.get(lab)
        complete_seasons.append((lab, w, v))
        if v is not None:
            gaps.append(v - w)
    if len(gaps) < 2:
        sys.exit("REFUSING: fewer than two complete seasons with both a weekly "
                 "mean and a published ONI; the gap cannot be calibrated")
    gap = st.mean(gaps)

    last_month = max(m for (y, m) in wk if y == year)
    latest = st.mean(wk[(year, last_month)])
    implied_aso = latest + gap
    gains = {a: hist[a]["NDJ"] - hist[a]["ASO"] for a in (1997, 2015)}

    print(f"=== {year} weekly-to-ONI calibration, complete seasons only ===")
    for lab, w, v in complete_seasons:
        s = f"ONI {v:+.2f}   gap {v-w:+.2f}" if v is not None else "ONI not yet published"
        print(f"  {lab}: weekly {w:+.2f}   {s}")
    print(f"  mean gap: {gap:+.2f} on n={len(gaps)}")
    print(f"\n=== nowcast ===")
    print(f"  latest complete month {year}-{last_month:02d}: weekly {latest:+.2f}")
    print(f"  implied ONI on that month's basis: {implied_aso:+.2f}")
    print(f"  analog ASO-to-NDJ gain: " +
          ", ".join(f"{a} {g:+.2f}" for a, g in gains.items()))
    lo, hi = min(gains.values()), max(gains.values())
    print(f"  => NDJ peak {implied_aso+lo:+.2f} to {implied_aso+hi:+.2f}, "
          f"IF Sep and Oct hold near {latest:+.2f}")
    print(f"\n  Caveats that belong with the number:")
    print(f"    the gap is WIDENING ({', '.join(f'{v-w:+.2f}' for _, w, v in complete_seasons if v is not None)}), "
          f"so a constant gap may read high")
    print(f"    the ASO-to-NDJ gain is n=2")
    print(f"    this is a SURFACE extrapolation. It cannot see the subsurface,")
    print(f"    which is at a 47-year record and is the models' strongest")
    print(f"    argument for a higher peak than this produces.")


if __name__ == "__main__":
    main()
