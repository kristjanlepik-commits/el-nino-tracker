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


class NoDataForPeriod(Exception):
    """AEMET answered: this station has no data for this period.

    Distinct from a failed request. An empty list cannot tell the two apart,
    and treating "the station did not exist" as "the request failed" makes a
    retry schedule attack a question that has already been answered.
    """
KEY = os.path.expanduser("~/.aemet_key")
MADRID_RETIRO = "3195"          # same thermometer as ECA&D station 230


def _key():
    # Env first, file second, same shape as the London collector. CI has
    # no home directory to keep a key in, and this is the only one of the
    # ten heat fetchers that needs a credential at all, so it is the only
    # thing standing between a weekly refresh and running unattended.
    #
    # Raises rather than returning empty when neither exists: a missing
    # Spanish key would otherwise produce a payload silently short of
    # every Spanish city, which the refresh gate would read as a set
    # change and hold on, for a reason that has nothing to do with the
    # weather.
    env = (os.environ.get("AEMET_API_KEY", "") or "").strip()
    if env:
        return env
    if not os.path.exists(KEY):
        raise SystemExit(
            "AEMET: no key. Set AEMET_API_KEY in the environment (CI) or "
            "write ~/.aemet_key (local). Refusing to continue without one, "
            "because the result would be a payload missing every Spanish "
            "city rather than an error.")
    with open(KEY) as f:
        return f.read().strip()


def _get(url, header=None):
    """AEMET serves LATIN-1, not UTF-8.

    Station names carry accents (MALAGA, VALENCIA, ALCANTARILLA BASE AEREA
    all contain them), so decoding as UTF-8 raises UnicodeDecodeError and,
    if that is swallowed, an encoding fault presents as "no data". Three
    cities were silently lost to exactly that before it was traced.
    """
    cmd = ["curl", "-sS", "--max-time", "60"]
    if header:
        cmd += ["-H", header]
    raw = subprocess.run(cmd + [url], capture_output=True).stdout
    return raw.decode("latin-1")


def window(a, b, station=MADRID_RETIRO):
    """One request. Returns [] and prints the reason on refusal."""
    url = f"{BASE}/fechaini/{a}T00:00:00UTC/fechafin/{b}T23:59:59UTC/estacion/{station}"
    try:
        meta = json.loads(_get(url, f"api_key: {_key()}"))
    except Exception:
        print(f"  {a}..{b}: unparseable response", file=sys.stderr)
        return []
    if "datos" not in meta:
        desc = meta.get("descripcion", "?")
        print(f"  {a}..{b}: {desc}", file=sys.stderr)
        # "No hay datos" is an ANSWER, not a failure: the station did not
        # exist yet. Retrying it burns the whole backoff schedule on a
        # question already answered. Distinguishing the two saved ~8 hours
        # across eight cities, because Palma's record starts in 1972 and the
        # 52 preceding years were each being asked four times.
        if "no hay datos" in desc.lower():
            raise NoDataForPeriod(desc)
        return []
    # AEMET IS TWO-STEP AND THE SECOND FILE IS GENERATED ASYNCHRONOUSLY, so a
    # fetch that arrives too early gets something that is not yet the array,
    # with a perfectly healthy status. A fixed sleep works most of the time
    # and then does not, once, in the middle of something that matters.
    #
    # WORSE, THE OLD CODE RETURNED [] ON ANY PARSE FAILURE. An empty list is
    # exactly what "this station has no data for this period" returns, so a
    # file that was merely not ready yet became a station that observed
    # nothing, and flowed into the series as measured absence. Floods hit the
    # same shape three ways today and named it: ABSENCE PRODUCED BY A FAILURE,
    # PRESENTED AS ABSENCE MEASURED. Their CEDA login pages, my MIDAS HTML fed
    # to a parser, and this. None are network errors; all arrive as HTTP 200.
    #
    # So retry on CONTENT rather than on status or on a timer, and when it
    # still will not parse, RAISE. A caller that cannot get data must not be
    # handed a value that reads as an answer.
    body = None
    for attempt, wait in enumerate((1.2, 3, 8), 1):
        time.sleep(wait)
        body = _get(meta["datos"])
        stripped = (body or "").lstrip()
        if stripped.startswith("["):
            try:
                return json.loads(body)
            except ValueError:
                pass                    # truncated array, try again
        if attempt < 3:
            print(f"  {a}..{b}: data file not ready yet "
                  f"(attempt {attempt}), retrying", file=sys.stderr)
    raise RuntimeError(
        f"{a}..{b}: AEMET data file never became a JSON array after 3 "
        f"attempts. Refusing to return an empty list, which is what a "
        f"station with genuinely no data returns and would be recorded as "
        f"measured absence. First 120 chars: {(body or '')[:120]!r}")


def _months(start: dt.date, end: dt.date, step: int = 3):
    cur = start
    while cur <= end:
        nxt = cur
        for _ in range(step):
            nxt = (nxt.replace(day=28) + dt.timedelta(days=8)).replace(day=1)
        yield cur.isoformat(), min(nxt - dt.timedelta(days=1), end).isoformat()
        cur = nxt


def tmin(rec):
    """AEMET writes decimals with a comma."""
    v = rec.get("tmin")
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def series(start, end, station=MADRID_RETIRO):
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
