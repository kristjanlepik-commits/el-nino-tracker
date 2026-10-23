"""Judge the second DANA (16-21 Oct 2026) against each declared station's own record, exactly as
pre-registered in floods/prereg/spain_dana2_2026-10.md (7f242975, addenda 297e5366 and 8c684a9c).
All 27 stations reported, record or not, with the test count beside every result.

Rules carried from the first storm unchanged (spain_dana_judge.py): unbroken year = 90% of days
reported; ranks against the record through 2025; 3-day totals need all three days; overlapping
windows declustered; headline only at 30 unbroken years; completeness sensitivity 70-100% emitted.
Added by the prereg: the first storm's value where it was higher; "twice in three weeks" per the
297e5366 definition; Almeria stations body text only (declared at their warned onset).

PROVISIONAL while AEMET has not published every window day: each station states which of
16-21 Oct are in, and the run is repeated when they arrive.

Run:  .venv/bin/python floods/spain_dana2_judge.py
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spain_dana_judge as J

J.WIN0, J.WIN1 = dt.date(2026, 10, 16), dt.date(2026, 10, 21)
STORM1 = (dt.date(2026, 9, 27), dt.date(2026, 10, 5))
STATIONS = [("0367", "Girona Aeropuerto"), ("0370B", "Girona, Antic Institut"), ("0200E", "Barcelona, Fabra"),
            ("0076", "Barcelona Aeropuerto"), ("0016A", "Reus Aeropuerto"), ("9981A", "Tortosa (Roquetes)"),
            ("8500A", "Castello - Almassora"), ("8414A", "Valencia Aeropuerto"), ("8416", "Valencia"),
            ("8019", "Alicante-Elche Aeropuerto"), ("8025", "Alacant/Alicante"), ("7031", "San Javier Aeropuerto"),
            ("7228", "Alcantarilla, Base Aerea"), ("7178I", "Murcia"), ("6155A", "Malaga Aeropuerto"),
            ("6156X", "Malaga, Centro Meteorologico"), ("B954", "Ibiza Aeropuerto"), ("B957", "Eivissa"),
            ("B278", "Palma de Mallorca Aeropuerto"), ("B228", "Palma, Puerto"), ("B893", "Menorca Aeropuerto"),
            ("8058X", "Oliva"), ("8293X", "Xativa"), ("8050X", "Javea / Xabia"),
            ("6325O", "Almeria Aeropuerto"), ("6332X", "Carboneras"), ("6367B", "Huercal-Overa")]
ALMERIA = {"6325O", "6332X", "6367B"}
TWICE_FIVE = ["0200E", "0016A", "9981A", "8500A", "8414A"]


def storm1_best(rain, n):
    t = J.totals(rain, n)
    v = [x for d, x in t.items() if any(STORM1[0] <= d + dt.timedelta(k) <= STORM1[1] for k in range(n))]
    return round(max(v), 1) if v else None


def main():
    out = {"prereg": "floods/prereg/spain_dana2_2026-10.md (7f242975, 297e5366, 8c684a9c)",
           "window": [J.WIN0.isoformat(), J.WIN1.isoformat()], "stations": []}
    records, headline, body = 0, [], []
    for sid, name in STATIONS:
        rain = J.load(sid)
        days = [(J.WIN0 + dt.timedelta(k)) for k in range((J.WIN1 - J.WIN0).days + 1)]
        reported = [d.isoformat() for d in days if rain.get(d) is not None]
        row = {"id": sid, "name": name, "window_days_reported": reported,
               "role": "body text only (declared at the warned onset)" if sid in ALMERIA else "declared"}
        if not reported:
            row["status"] = "no window day published by AEMET yet"
            out["stations"].append(row)
            print(f"{sid:6} {name:30} NO WINDOW DATA PUBLISHED YET")
            continue
        since = J.unbroken_from(rain)
        row["unbroken_since"] = since
        for k, n in (("1day", 1), ("3day", 3)):
            j = J.judge(rain, n, since)
            s1 = storm1_best(rain, n)
            if s1 is not None and "mm" in j and s1 > j["mm"]:
                j["storm1_higher_mm"] = s1
            row[k] = j
            # A record counts toward the summary only where the unbroken run is long enough to
            # headline (D-318 clause 2: 30 years through 2025). A "record" in a one-year run
            # (Alicante, unbroken only since 2025) is not a finding, and counting it was a bug.
            if j.get("record_unbroken") and since and since <= 1996 and sid not in ALMERIA:
                records += 1; headline.append(f"{sid} {k} {j['mm']} mm, unbroken since {since}")
            if j.get("record_full") and not j.get("record_unbroken"):
                body.append(f"{sid} {k} {j['mm']} mm, most in records from {j['full_from']} (with gaps)")
        keep, sens = J.COMPLETE, {}
        for th in (0.70, 0.80, 0.90, 0.95, 1.00):
            J.COMPLETE = th
            s_ = J.unbroken_from(rain)
            sens[f"{th:.2f}"] = {k: J.judge(rain, n, s_).get("rank_unbroken") for k, n in (("1day", 1), ("3day", 3))}
        J.COMPLETE = keep
        row["completeness_sensitivity"] = sens
        out["stations"].append(row)
        a, b = row["1day"], row["3day"]
        tag = lambda x: ("RECORD since %s" % since if x.get("record_unbroken") else
                         "rank %s since %s, most since %s" % (x.get("rank_unbroken"), since, x.get("most_since")))
        print(f"{sid:6} {name:30} days in {len(reported)}/6 | unbroken {since} | 1d {a.get('mm')} ({a.get('start')}) "
              f"{tag(a) if 'mm' in a else a.get('status')} | 3d {b.get('mm')} {tag(b) if 'mm' in b else b.get('status')}"
              + (" | storm1 1d higher %s" % a["storm1_higher_mm"] if a.get("storm1_higher_mm") else ""))
    twice = []
    for sid in TWICE_FIVE:
        rain = J.load(sid)
        twice += [(sid, d.isoformat(), v) for d, v in rain.items() if J.WIN0 <= d <= J.WIN1 and v is not None and v >= 100]
    n_st = sum(1 for s in out["stations"] if "1day" in s)
    out["summary"] = {"stations_declared": len(STATIONS), "stations_with_window_data": n_st,
                      "tests_declared": 2 * len(STATIONS), "tests_run": 2 * n_st,
                      "headline_records_30y_unbroken": records, "headline_records": headline,
                      "body_text_records_in_gapped_records": body,
                      "twice_in_three_weeks": {"qualifying_days_at_five_stations": twice,
                                               "qualifies": bool(twice)}}
    json.dump(out, open(os.path.join(HERE, "data", "spain_dana2_2026-10_stations.json"), "w"), indent=1)
    print("\nSUMMARY", json.dumps(out["summary"]))


if __name__ == "__main__":
    main()
