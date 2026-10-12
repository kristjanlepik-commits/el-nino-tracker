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
NO_DATA = "No hay datos que satisfagan esos criterios"   # AEMET's own "no data" reply


def val(p):
    if p in ("", None):
        return None           # not reported: never a zero
    if p == "Ip":
        return 0.0            # AEMET "inapreciable", a trace
    return float(str(p).replace(",", "."))


def fetch_half(sid, y, a, b, out):
    """One half-year. Returns "held", "empty" or "error".

    Only AEMET's own "no data" reply is cached as empty, because only that is
    a statement about the archive. Everything else, including _aemet's
    "data file never arrived" and a reply that parses to no rows, is an
    error and writes nothing, so the next run asks again. Caching a failure
    as an absence once turned 55 half-years of real data into gaps (found
    2026-10-12, Tortosa 1957 H1). Writes go through a temp file so an
    interrupted write cannot leave a truncated cache entry either."""
    try:
        r = V._aemet(f"valores/climatologicos/diarios/datos/fechaini/"
                     f"{y}-{a}T00:00:00UTC/fechafin/{y}-{b}T23:59:59UTC/estacion/{sid}")
    except SystemExit as e:
        if NO_DATA in str(e):
            _write(out, []); return "empty"
        print(sid, y, out[-7:-5], "ERROR", str(e)[:80], flush=True); return "error"
    except Exception as e:
        print(sid, y, out[-7:-5], "ERROR", type(e).__name__, flush=True); return "error"
    if not r:
        print(sid, y, out[-7:-5], "ERROR reply parsed to no rows; not cached", flush=True)
        return "error"
    _write(out, [[x["fecha"], val(x.get("prec"))] for x in r])
    return "held"


def _write(out, rows):
    tmp = out + ".tmp"
    json.dump(rows, open(tmp, "w"))
    os.replace(tmp, out)


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    for sid in sys.argv[1:]:
        d = os.path.join(CACHE, sid); os.makedirs(d, exist_ok=True)
        n = {"held": 0, "empty": 0, "error": 0}
        for y in range(FIRST, LAST + 1):
            for a, b, tag in (("01-01", "06-30", "H1"), ("07-01", "12-31", "H2")):
                out = os.path.join(d, f"{y}{tag}.json")
                if os.path.exists(out):
                    n["held"] += 1; continue
                got = fetch_half(sid, y, a, b, out)
                n[got] += 1
                if got == "error":
                    time.sleep(5)
        print(f"{sid}: held {n['held']}, archive-empty {n['empty']}, errors {n['error']}"
              + ("  INCOMPLETE, rerun" if n["error"] else ""), flush=True)


def selftest():
    """A guard that has only ever passed is untested. Prove each failure
    shape writes nothing, and only AEMET's "no data" writes an empty entry."""
    import tempfile
    real = V._aemet
    cases = [("AEMET no data", SystemExit(f"AEMET refused: {NO_DATA}"), "empty", []),
             ("data file never arrived", SystemExit("AEMET: data file never became a JSON array."), "error", None),
             ("other refusal", SystemExit("AEMET refused: Limite de peticiones"), "error", None),
             ("transport error", ConnectionError("reset"), "error", None),
             ("empty array reply", [], "error", None),
             ("real data", [{"fecha": "1957-01-01", "prec": "1,5"}], "held", [["1957-01-01", 1.5]])]
    ok = True
    with tempfile.TemporaryDirectory() as td:
        for k, (name, reply, want, rows) in enumerate(cases):
            out = os.path.join(td, f"{k}H1.json")
            def fake(path, reply=reply):
                if isinstance(reply, BaseException):
                    raise reply
                return reply
            V._aemet = fake
            got = fetch_half("TEST", 1957, "01-01", "06-30", out)
            wrote = json.load(open(out)) if os.path.exists(out) else None
            good = got == want and wrote == rows
            ok &= good
            print(f"  {name:<26} -> {got:<6} cache {'none' if wrote is None else wrote}   {'ok' if good else 'WRONG'}")
    V._aemet = real
    if not ok:
        sys.exit("SELFTEST FAILED: a failure can be cached as an absence")
    print("  self-test passed: only AEMET's own no-data reply is cached as empty")


if __name__ == "__main__":
    main()
