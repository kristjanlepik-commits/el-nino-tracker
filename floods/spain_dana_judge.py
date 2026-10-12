"""Judge the eastern Spain DANA against each declared station's own record,
exactly as pre-registered in floods/prereg/spain_dana_2026-10.md (rules
e9a2aa3f, addendum 5272debe). Every declared station is reported, record or
not.

Run:  .venv/bin/python floods/spain_dana_judge.py
"""
import datetime as dt
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".aemet_cache")
STATIONS = [("0200E", "Barcelona, Fabra", "principal"), ("0076", "Barcelona Aeropuerto", "principal"),
            ("0016A", "Reus Aeropuerto", "principal"), ("9981A", "Tortosa (Roquetes)", "principal"),
            ("8500A", "Castello - Almassora", "principal"), ("8414A", "Valencia Aeropuerto", "principal"),
            ("8175", "Albacete Base Aerea", "principal"),
            ("8178D", "Albacete (nearest Madrigueras)", "body text only"),
            ("8300X", "Carcaixent (nearest Alzira)", "body text only")]
WIN0, WIN1 = dt.date(2026, 9, 27), dt.date(2026, 10, 5)
COMPLETE = 0.90


def load(sid):
    rain = {}
    for f in sorted(glob.glob(os.path.join(CACHE, sid, "*.json"))):
        for day, v in json.load(open(f)):
            rain[dt.date.fromisoformat(day)] = v
    return rain


def unbroken_from(rain):
    """First year of the run of years with >= 90% of days reported, ending 2025."""
    def ok(y):
        n = (dt.date(y, 12, 31) - dt.date(y, 1, 1)).days + 1
        got = sum(1 for d, v in rain.items() if d.year == y and v is not None)
        return got / n >= COMPLETE
    if not ok(2025):
        return None
    y = 2025
    while ok(y - 1):
        y -= 1
    return y


def totals(rain, n):
    """Every n-day total with all n days reported, keyed by first day."""
    out = {}
    for d in rain:
        days = [d + dt.timedelta(k) for k in range(n)]
        vals = [rain.get(x) for x in days]
        if all(v is not None for v in vals):
            out[d] = sum(vals)
    return out


def decluster(t, n):
    """Keep a window only if no overlapping window is higher (ties: earliest)."""
    if n == 1:
        return t
    keep = {}
    for d, v in t.items():
        rivals = [t.get(d + dt.timedelta(k)) for k in range(-(n - 1), n) if k != 0]
        if all(r is None or r < v or (r == v and k > 0)
               for k, r in zip([k for k in range(-(n - 1), n) if k != 0], rivals)):
            keep[d] = v
    return keep


def judge(rain, n, since):
    t = totals(rain, n)
    in_storm = {d: v for d, v in t.items()
                if any(WIN0 <= d + dt.timedelta(k) <= WIN1 for k in range(n))}
    if not in_storm:
        return {"status": "no complete total in the storm window"}
    d0 = max(in_storm, key=in_storm.get)
    v = in_storm[d0]
    hist = {d: x for d, x in decluster(t, n).items() if d.year <= 2025}
    higher = [d for d, x in hist.items() if x > v]
    higher_unbroken = [d for d in higher if since and d.year >= since]
    last_higher = max(higher).year if higher else None
    return {"start": d0.isoformat(), "mm": round(v, 1),
            "rank_full": 1 + len(higher), "n_full": len(hist) + 1,
            "full_from": min(hist).year,
            "rank_unbroken": (1 + len(higher_unbroken)) if since else None,
            "unbroken_since": since,
            "most_since": last_higher, "record_full": not higher,
            "record_unbroken": bool(since) and not higher_unbroken}


def main():
    out = {"prereg": "floods/prereg/spain_dana_2026-10.md", "window": [WIN0.isoformat(), WIN1.isoformat()],
           "stations": []}
    for sid, name, role in STATIONS:
        rain = load(sid)
        missing = sorted(d.isoformat() for d in rain if WIN0 <= d <= WIN1 and rain[d] is None)
        absent = [(WIN0 + dt.timedelta(k)).isoformat() for k in range((WIN1 - WIN0).days + 1)
                  if (WIN0 + dt.timedelta(k)) not in rain]
        since = unbroken_from(rain)
        row = {"id": sid, "name": name, "role": role, "unbroken_since": since,
               "storm_days_unreported": missing + absent,
               "1day": judge(rain, 1, since), "3day": judge(rain, 3, since)}
        # Does the 90% completeness rule drive the result? Emitted, not argued
        # (CPO, 2026-10-12): the verdict at every threshold from 70% to 100%.
        global COMPLETE
        keep, sens = COMPLETE, {}
        for th in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98, 1.00):
            COMPLETE = th
            s_ = unbroken_from(rain)
            sens[f"{th:.2f}"] = {k: {"since": s_, "rank": judge(rain, n, s_).get("rank_unbroken"),
                                     "record": judge(rain, n, s_).get("record_unbroken")}
                                 for k, n in (("1day", 1), ("3day", 3))}
        COMPLETE = keep
        row["completeness_sensitivity"] = sens
        out["stations"].append(row)
        print(f"\n{sid} {name} [{role}]  unbroken since {since}; first data {min(rain).year}"
              + (f"; UNREPORTED storm days {missing + absent}" if missing or absent else ""))
        for k in ("1day", "3day"):
            j = row[k]
            if "mm" not in j:
                print(f"   {k}: {j['status']}"); continue
            tag = ("RECORD (full record)" if j["record_full"] else
                   "record within unbroken run" if j["record_unbroken"] else f"most since {j['most_since']}")
            print(f"   {k}: {j['mm']:6.1f} mm from {j['start']}  rank {j['rank_unbroken']} in unbroken run "
                  f"since {since}, rank {j['rank_full']} in full record from {j['full_from']}  -> {tag}")
    json.dump(out, open(os.path.join(HERE, "data", "spain_dana_2026-10_stations.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
