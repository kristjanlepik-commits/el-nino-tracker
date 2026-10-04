"""Full daily precipitation history for declared AEMET stations.

AEMET caps a daily-values request at six months, so a century is about 250
requests per station. Each half-year is cached on its own, so a dropped
connection costs one chunk, not a station. A half-year AEMET answers with
"no data" is cached as empty and not retried: that is a statement about the
archive. A transport error is NOT cached, so it retries next run. Mixing
the two would turn an outage into a gap in the record.

Run:  .venv/bin/python floods/fetch_aemet_history.py 0200E 0076 ...
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_intensity as V

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aemet_cache")
FIRST, LAST = 1900, 2025


def val(p):
    if p in ("", None):
        return None           # not reported: never a zero
    if p == "Ip":
        return 0.0            # AEMET "inapreciable", a trace
    return float(str(p).replace(",", "."))


def main():
    for sid in sys.argv[1:]:
        d = os.path.join(CACHE, sid); os.makedirs(d, exist_ok=True)
        held = empty = err = 0
        for y in range(FIRST, LAST + 1):
            for a, b, tag in (("01-01", "06-30", "H1"), ("07-01", "12-31", "H2")):
                out = os.path.join(d, f"{y}{tag}.json")
                if os.path.exists(out):
                    held += 1; continue
                try:
                    r = V._aemet(f"valores/climatologicos/diarios/datos/fechaini/"
                                 f"{y}-{a}T00:00:00UTC/fechafin/{y}-{b}T23:59:59UTC/estacion/{sid}")
                    json.dump([[x["fecha"], val(x.get("prec"))] for x in r], open(out, "w"))
                    held += 1
                except SystemExit:
                    json.dump([], open(out, "w")); empty += 1
                except Exception as e:
                    err += 1; print(sid, y, tag, "ERROR", type(e).__name__, flush=True); time.sleep(5)
        print(f"{sid}: held {held}, archive-empty {empty}, errors {err}"
              + ("  INCOMPLETE, rerun" if err else ""), flush=True)


if __name__ == "__main__":
    main()
