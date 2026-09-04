"""The recharge-discharge cycle: where an El Nino's fuel comes from and goes.

Kristjan asked how discharging happens and how we would measure it this
year. This computes both from CPC's own heat content index.

THE COLUMN CHOICE IS THE WHOLE ANALYSIS AND IS EASY TO GET WRONG.
The source carries three columns. Our published headline uses 180W-100W,
the EASTERN box, because that is where an El Nino's surface signature
lives. That column is useless for discharge: it RISES during an event, as
warm water sloshes east. It measures arrival, not stock.

Discharge is a statement about the whole equatorial reservoir, so it needs
130E-80W, the basin-wide column. Using the eastern box here would show a
reservoir filling at the exact moment it is emptying.

The physics, which is textbook and cited rather than established here
(Jin 1997, the recharge oscillator): trade winds pile warm water into the
western Pacific and deepen the thermocline, charging the basin. During an
El Nino the trades weaken, the thermocline flattens, and poleward
transport moves warm water OUT of the equatorial band. The reservoir
empties. That emptying is what ends the event and preconditions La Nina.

So basin-wide heat content leads the surface. What we measure is when it
turns over, and how far it falls.
"""
import csv, collections, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".fetch_cache" / "heat_content_index.txt"
URL = ("https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ocean/"
       "index/heat_content_index.txt")
ORD = ['DJF','JFM','FMA','MAM','AMJ','MJJ','JJA','JAS','ASO','SON','OND','NDJ']

EVENTS = [(1982,"1982-83","super"), (1997,"1997-98","super"),
          (2009,"2009-10","moderate"), (2014,"2014-15","weak"),
          (2015,"2015-16","super"), (2023,"2023-24","strong"),
          (2026,"2026-27","current")]


def get():
    if CACHE.exists() and CACHE.stat().st_size > 10_000:
        return CACHE.read_text()
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode("utf-8", "replace")
    CACHE.write_text(txt)
    return txt


def main():
    basin, east = {}, {}
    for line in get().splitlines():
        p = line.split()
        if len(p) == 5 and p[0].isdigit():
            y, m = int(p[0]), int(p[1])
            basin[(y, m)] = float(p[2])     # 130E-80W, the reservoir
            east[(y, m)] = float(p[4])      # 180W-100W, our headline box
    mk = lambda y, m: y * 12 + m

    oni = collections.defaultdict(dict)
    with open(ROOT / "data" / "oni_full_history.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            oni[int(r["year"])][r["season"].upper()] = float(r["oni"])

    rows = []
    for y, label, kind in EVENTS:
        dev = [(k, v) for k, v in basin.items() if k[0] == y]
        if not dev:
            continue
        pk = max(dev, key=lambda t: t[1])
        t0 = mk(*pk[0])
        after = [(k, v) for k, v in basin.items() if t0 < mk(*k) <= t0 + 18]
        cand = [(s, oni[yy][s]) for yy in (y, y+1) for s in ORD
                if oni.get(yy, {}).get(s) is not None]
        onipk = max(cand, key=lambda t: t[1]) if cand else (None, None)
        rec = {"event": label, "kind": kind,
               "ohc_peak": pk[1], "ohc_peak_month": f"{pk[0][0]}-{pk[0][1]:02d}",
               "oni_peak": onipk[1], "oni_peak_season": onipk[0]}
        if after and kind != "current":
            lo = min(after, key=lambda t: t[1])
            rec["trough"] = lo[1]
            rec["trough_month"] = f"{lo[0][0]}-{lo[0][1]:02d}"
            rec["discharge"] = round(lo[1] - pk[1], 2)
            rec["months_peak_to_trough"] = mk(*lo[0]) - t0
        else:
            rec["discharge"] = None
            rec["note"] = "has not turned over yet"
        rows.append(rec)

    ranked = sorted(basin.items(), key=lambda kv: -kv[1])[:10]
    span = sorted(basin)
    payload = {
        "generated": "2026-09-04",
        "source": URL,
        "column_used": ("130E-80W, basin-wide. NOT the 180W-100W eastern box "
                        "our headline uses: that column rises during an event "
                        "and would show a reservoir filling while it empties."),
        "mechanism_is_cited_not_established": (
            "The recharge oscillator (Jin 1997) is textbook. This file shows "
            "the STATE of the reservoir and when it turns over. It does not "
            "establish the mechanism and must not be cited as doing so."),
        "record_span": f"{span[0][0]}-{span[-1][0]}",
        "n_months": len(basin),
        "top_10_months": [{"month": f"{y}-{m:02d}", "value": v}
                          for (y, m), v in ranked],
        "entering_state": {
            "why_this_field_exists": (
                "A desk read 2026's ENTERING value off the eastern box "
                "(-0.03) and concluded this event had 'no head start'. On the "
                "eastern box 2026 does group with 1997 and 2023, all negative. "
                "On the RESERVOIR it does not: 2026 entered fullest of the "
                "three. A head start is a claim about fuel, so it belongs to "
                "the basin-wide column. Both are given here so the comparison "
                "cannot be made on the wrong one again."),
            "prior_december": [
                {"event": lab, "basin_wide": basin[(y-1, 12)],
                 "eastern_box": east[(y-1, 12)]}
                for y, lab, _ in EVENTS if (y-1, 12) in basin
            ],
        },
        "record_margin": {
            "basin_wide": ("2026-08 at %.2f against the previous high of %.2f "
                           "(1997-06), a margin of %.2f"
                           % (basin[(2026,8)], 1.55, basin[(2026,8)] - 1.55)),
            "eastern_box": ("2026-08 at %.2f against the previous high of %.2f "
                            "(1997-10), a margin of %.2f"
                            % (east[(2026,8)], 2.56, east[(2026,8)] - 2.56)),
            "reading": ("The record holds on EITHER column, with a margin near "
                        "0.65 on both. That is wider than the gap between 1997 "
                        "and third place, and it is the durable part of the "
                        "claim. The entering state is not."),
        },
        "events": rows,
        "current": {
            "latest_month": f"{span[-1][0]}-{span[-1][1]:02d}",
            "basin_wide": basin[span[-1]],
            "eastern_box": east[span[-1]],
            "still_rising": basin[span[-1]] > basin[span[-2]],
        },
    }

    faults = []
    hist = [r for r in rows if r["discharge"] is not None]
    if not hist:
        faults.append("no completed event has a discharge figure")
    if any(r["discharge"] > 0 for r in hist):
        faults.append("a completed event discharged upward, so the trough "
                      "search window is wrong")
    cur = next((r for r in rows if r["kind"] == "current"), None)
    if cur and cur["discharge"] is not None:
        faults.append("the current event is reported as having discharged; it "
                      "has not turned over and must not carry a figure")
    if faults:
        sys.exit("REFUSING TO WRITE:\n  - " + "\n  - ".join(faults))

    dest = ROOT / "data" / "recharge_discharge.json"
    dest.write_text(json.dumps(payload, indent=1))
    print(f"  wrote {dest.relative_to(ROOT)}")
    print(f"  {len(basin)} months, {span[0][0]}-{span[-1][0]}")
    print(f"  latest: basin-wide {payload['current']['basin_wide']:+.2f}, "
          f"eastern box {payload['current']['eastern_box']:+.2f}, "
          f"still rising: {payload['current']['still_rising']}")
    for r in rows:
        d = f"{r['discharge']:+.2f}" if r["discharge"] is not None else "ongoing"
        print(f"    {r['event']:<8} {r['kind']:<9} peak {r['ohc_peak']:+.2f} "
              f"({r['ohc_peak_month']})  discharge {d}")


if __name__ == "__main__":
    main()
