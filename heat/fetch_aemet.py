"""Fetch daily minimum temperature from AEMET for a Spanish station.

Why this exists. ECA&D holds Madrid back to 1920 but its series ends 29 May
2026, and Madrid's hot nights fall between June and September, so the season
the channel is about is absent. AEMET is where ECA&D gets that station: the
blend header names AEMET as the source and participant.

VERIFIED IDENTICAL, not merely correlated. 332 overlapping days between the
two sources, every one matching to 0.1 C, maximum difference 0.0. So joining
ECA&D history to AEMET current is one instrument from two publishers, not a
cross-source composition, and needs no composition caveat.

Latency measured 2026-08-05: AEMET ran to 2 August, a 3-day lag, against
ECA&D's six weeks.

Key at ~/.aemet_key, free, expires 2026-11-13. Two-step API: the first call
returns a URL, the data comes from that. Date ranges are capped, so requests
are chunked at 3 months; longer ranges return an error rather than truncating,
which is the failure mode to watch for.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time

BASE = ("https://opendata.aemet.es/opendata/api/valores/climatologicos"
        "/diarios/datos")
KEY = os.path.expanduser("~/.aemet_key")
MADRID_RETIRO = "3195"          # same thermometer as ECA&D station 230


def _key() -> str:
    with open(KEY) as f:
        return f.read().strip()


def _get(url: str, header: str | None = None) -> str:
    cmd = ["curl", "-sS", "--max-time", "60"]
    if header:
        cmd += ["-H", header]
    return subprocess.run(cmd + [url], capture_output=True, text=True).stdout


def window(a: str, b: str, station: str = MADRID_RETIRO) -> list[dict]:
    """One request. Returns [] and prints the reason on refusal."""
    url = f"{BASE}/fechaini/{a}T00:00:00UTC/fechafin/{b}T23:59:59UTC/estacion/{station}"
    try:
        meta = json.loads(_get(url, f"api_key: {_key()}"))
    except Exception:
        print(f"  {a}..{b}: unparseable response", file=sys.stderr)
        return []
    if "datos" not in meta:
        print(f"  {a}..{b}: {meta.get('descripcion', '?')}", file=sys.stderr)
        return []
    time.sleep(1.2)                     # be polite to a free public API
    try:
        return json.loads(_get(meta["datos"]))
    except Exception:
        return []


def _months(start: dt.date, end: dt.date, step: int = 3):
    cur = start
    while cur <= end:
        nxt = cur
        for _ in range(step):
            nxt = (nxt.replace(day=28) + dt.timedelta(days=8)).replace(day=1)
        yield cur.isoformat(), min(nxt - dt.timedelta(days=1), end).isoformat()
        cur = nxt


def tmin(rec: dict) -> float | None:
    """AEMET writes decimals with a comma."""
    v = rec.get("tmin")
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def series(start: dt.date, end: dt.date, station: str = MADRID_RETIRO):
    out = []
    for a, b in _months(start, end):
        out += [(r["fecha"], tmin(r)) for r in window(a, b, station)
                if tmin(r) is not None]
        time.sleep(1.2)
    return sorted(set(out))


if __name__ == "__main__":
    y = int(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today().year
    s = series(dt.date(y, 1, 1), min(dt.date(y, 12, 31), dt.date.today()))
    trop = sum(1 for _, t in s if t >= 20.0)
    print(f"{y}: {len(s)} days, {trop} tropical nights, "
          f"latest {s[-1][0] if s else 'none'}")
