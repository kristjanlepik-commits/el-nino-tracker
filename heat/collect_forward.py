"""Accumulate observations for cities we cannot fetch a history for.

WHY THIS EXISTS. Some cities have a good archive and no current data, and no
amount of cleverness recovers a day that was never recorded. Tallinn is the
case: the only long record reaching 2026 is ECA&D-sourced and non-commercial,
the commercially clear one stopped feeding in August 2025, and Estonia's own
service publishes history through a web interface rather than an API.

So the archive can wait and the current days cannot. This runs daily, costs
one small request, and needs no credentials.

WHAT IT PRODUCES IS NOT AN OFFICIAL DAILY MINIMUM, and that distinction has
to survive into whatever renders it. A national service computes Tmin from a
continuous minimum thermometer over a defined 24-hour window. This samples an
instantaneous temperature whenever it runs, so the daily minimum derived from
it is the lowest SAMPLE, which is warmer than the true minimum by however much
the sampling missed. The more often it runs the closer it gets and it never
arrives.

Consequences, both of which belong in the payload when this data is used:

  the derived minimum is BIASED WARM, so a tropical-night count from it
  UNDERSTATES rather than overstates, which is the safe direction

  it is not comparable with the archive years, which are true daily minima,
  so a rank mixing the two is a cross-instrument comparison of the kind that
  produced the Murcia error

RUN IT OFTEN OR NOT AT ALL. A daily minimum built from one sample a day is
not a minimum, it is a reading. Hourly is the minimum useful cadence and the
scheduling belongs to platform, not here; this script does one fetch and
exits so it can be driven by anything.

RAW SAMPLES ARE STORED, NOT DERIVED DAILIES. The derivation will improve, the
observations will not come again. Appending raw means a better method can be
applied retrospectively; storing a computed minimum would freeze today's
method into the record permanently.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# COMMITTED, not cached. The first version wrote into heat/.cache/, which is
# gitignored, so the one kind of data that genuinely cannot be re-fetched
# would have existed on a single laptop and nowhere else. These samples are
# the artifact; they belong in the repo from the first run.
OUT = ROOT / "heat" / "data" / "collected"

SOURCES = {
    # LONDON. Met Office DataHub, Land Observations, free tier.
    #
    # MEASURED RETENTION: 48 HOURS. Confirmed 2026-08-09 by reading the
    # response rather than the documentation, which is a JavaScript shell
    # that returns nothing to a fetcher. That single fact is why London is a
    # build-forward city: its 2026 summer exists nowhere we can reach, and no
    # archive will ever have it.
    #
    # BETTER THAN THE TALLINN COLLECTOR, and the difference matters. Each call
    # returns 48 HOURLY records, not one instantaneous reading. So a daily run
    # captures every hour with a full day of redundancy, and a derived daily
    # minimum is the lowest of 24 hourly values rather than of one sample.
    # Still not a true minimum-thermometer reading, and much closer to one.
    #
    # Queried by GEOHASH, not station id. gcpsvg covers west London near
    # Heathrow. Recorded because the neighbouring cell gcpsve returns 404 and
    # a future reader would otherwise assume the geohash was mistyped.
    "London": {
        "url": "https://data.hub.api.metoffice.gov.uk/observation-land/1/gcpsvg",
        "station": "geohash gcpsvg, west London",
        "wmo": None,
        "service": "Met Office DataHub, Land Observations",
        "licence": "free tier, wdh_cdp_landobs_free",
        "key_file": "~/.metoffice_key",
        "header": "apikey",
        "kind": "json_hourly",
        "retention_hours": 48,
    },
    "Tallinn": {
        "url": "https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php",
        "station": "Tallinn-Harku",
        "wmo": "26038",
        "service": "Riigi Ilmateenistus / Keskkonnaagentuur",
        "licence": "open, cite Keskkonnaagentuur as source",
        # Same station as GHCN EN000026038, whose archive runs 1936 to
        # 2025-08. So the collector and the eventual history are one
        # thermometer, which is the only reason joining them will be legal
        # in the Murcia sense.
    },
}


def _london(cfg):
    """Met Office returns a JSON list of hourly observations."""
    import os
    key = open(os.path.expanduser(cfg["key_file"])).read().strip()
    raw = subprocess.run(
        ["curl", "-sS", "--max-time", "60",
         "-H", f"{cfg['header']}: {key}",
         "-H", "accept: application/json", cfg["url"]],
        capture_output=True).stdout.decode("utf-8", "replace")
    try:
        rows = json.loads(raw)
    except Exception:
        return []
    out = []
    for r in rows:
        if r.get("temperature") is None or not r.get("datetime"):
            continue
        out.append({"dt": r["datetime"], "t": float(r["temperature"]),
                    "station": cfg["station"]})
    return out


def sample(city):
    cfg = SOURCES[city]
    if cfg.get("kind") == "json_hourly":
        return _london(cfg)
    raw = subprocess.run(["curl", "-sS", "--max-time", "60", cfg["url"]],
                         capture_output=True).stdout.decode("utf-8", "replace")
    ts = re.search(r'timestamp="(\d+)"', raw)
    block = re.search(
        r"<station>(?:(?!</station>).)*?<name>%s</name>.*?</station>"
        % re.escape(cfg["station"]), raw, re.S)
    if not (ts and block):
        return None
    t = re.search(r"<airtemperature>([-\d.]*)</airtemperature>", block.group(0))
    if not t or not t.group(1):
        return None
    return {"ts": int(ts.group(1)), "t": float(t.group(1)),
            "station": cfg["station"], "wmo": cfg["wmo"]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rc = 0
    for city in (sys.argv[1:] or SOURCES):
        s = sample(city)
        if s is None:
            print(f"  {city}: no observation returned", file=sys.stderr)
            rc = 1
            continue
        if isinstance(s, list):
            # Hourly batches overlap by design, so dedupe on timestamp. The
            # file is the artifact; writing the same hour twice would corrupt
            # any later derivation of a daily minimum.
            p = OUT / f"{city}.jsonl"
            have = set()
            if p.exists():
                for line in open(p):
                    try:
                        have.add(json.loads(line)["dt"])
                    except Exception:
                        pass
            new = [r for r in s if r["dt"] not in have]
            with open(p, "a") as fh:
                for r in new:
                    fh.write(json.dumps(r) + "\n")
            print(f"  {city}: {len(s)} returned, {len(new)} new, "
                  f"{len(have) + len(new)} on file")
            continue
        p = OUT / f"{city}.jsonl"
        # Append-only. A collector that rewrites its own file can lose
        # everything to one bad run, and these days cannot be re-fetched.
        with open(p, "a") as fh:
            fh.write(json.dumps(s) + "\n")
        n = sum(1 for _ in open(p))
        print(f"  {city}: {s['t']} C at ts {s['ts']}, {n} samples on file")
    return rc


if __name__ == "__main__":
    sys.exit(main())
