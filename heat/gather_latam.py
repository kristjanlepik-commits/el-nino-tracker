"""Fetch recent years for the viable LatAm stations, and prove identity.

WHAT THIS IS. The survey found 13 stations with a complete baseline and no
present. Every one is a bridge job: the archive holds the history and the
station has been transmitting throughout. This gathers the missing years.

WHOLE YEARS, NOT SEASONS, AND THAT IS DELIBERATE. The existing bridge fetches
May to August because our instrument assumes a northern summer. Ten of these
stations have a hot season of December to January or February, one is August
to October and one is March to May. Fetching a season now would bake the
assumption we are about to remove into the data we gather to remove it. A
whole year costs more requests and cannot be wrong about which months matter.

IDENTITY IS PROVEN, NOT PARSED. The WMO block is not reliably derivable from
the GHCN id: AR000087078 is block 87078, but AR000875850 is block 87585 and
AR000870470 is 87047. Two padding conventions inside one country, and a
wrong block returns another station's perfectly valid data, which is the
Murcia failure exactly.

So candidates are tried and the ARCHIVE decides. Each candidate is fetched
for a year GHCN also holds and compared day by day. A block that reproduces
the archive is the same station; one that does not is discarded however
plausible its number looked. That check refused Aberdeen at p90 0.6 C and
passed Larnaca at 100%, so it works in both directions.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))
import synop  # noqa: E402

SRC = ROOT / "heat" / ".cache" / "src"
LATAM = SRC / "latam"
CACHE = SRC / "synop_latam"
OUT = ROOT / "heat" / "data" / "latam_gather.json"
OGIMET = "https://www.ogimet.com/cgi-bin/getsynop"
AGREE_P90_C = 0.5


def candidates(ghcn_id):
    """Plausible WMO blocks for a GHCN id, most likely first.

    Never one guess. The id carries the number with inconsistent padding, so
    both readings are offered and the archive comparison picks.
    """
    tail = ghcn_id[3:]                       # after the 2-letter country + '0'
    out = []
    for c in (tail[-5:], tail[:5], tail.lstrip("0")[:5]):
        c = c.zfill(5)
        if c not in out and c.isdigit():
            out.append(c)
    return out


def ghcn_days(ghcn_id):
    out = {}
    f = LATAM / f"{ghcn_id}.dly"
    for L in f.read_text(errors="replace").splitlines():
        el = L[17:21]
        if el not in ("TMAX", "TMIN"):
            continue
        y, m = int(L[11:15]), int(L[15:17])
        for d in range(31):
            o = 21 + d * 8
            v, q = L[o:o + 5].strip(), L[o + 6:o + 7]
            if v in ("-9999", "") or q.strip():
                continue
            out.setdefault(f"{y}-{m:02d}-{d + 1:02d}", {})[el] = int(v) / 10.0
    return out


def fetch_year(block, year):
    """One whole year of bulletins, cached, content-checked.

    Size is not shape: an error page over a kilobyte would otherwise be
    cached as though it were data and freeze the failure permanently.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{block}_{year}.txt"
    if f.exists():
        raw = f.read_text(errors="replace")
        if raw.count("AAXX") >= 20:
            return raw
    raw = ""
    for _try in (1, 2, 3):
        raw = subprocess.run(
            ["curl", "-sS", "--max-time", "240",
             f"{OGIMET}?block={block}&begin={year}01010000&end={year}12312359"],
            capture_output=True).stdout.decode("utf-8", "replace")
        if raw.count("AAXX") >= 20:
            f.write_text(raw)
            return raw
        time.sleep(8)
    return raw


def daily(raw):
    """Daily extremes, hours fitted by value rather than assumed."""
    from build_bridge import detect_hours
    hn, hx = detect_hours(raw)
    out = {}
    for d, h, tx, tn in synop.parse_ogimet(raw):
        mn, mx = out.get(d, (None, None))
        if h == hn and tn is not None:
            mn = tn
        if h == hx and tx is not None:
            mx = tx
        out[d] = (mn, mx)
    return out


def identify(ghcn_id, g, probe_year):
    """Which candidate block reproduces the archive? Measured."""
    tried = []
    for block in candidates(ghcn_id):
        raw = fetch_year(block, probe_year)
        if raw.count("AAXX") < 20:
            tried.append({"block": block, "result": "no bulletins"})
            continue
        s = daily(raw)
        common = [d for d in s if d in g and "TMAX" in g[d]
                  and s[d][1] is not None]
        if len(common) < 30:
            tried.append({"block": block, "result": f"only {len(common)} "
                          f"shared days, cannot decide"})
            continue
        dx = sorted(abs(s[d][1] - g[d]["TMAX"]) for d in common)
        p90 = dx[int(0.9 * (len(dx) - 1))]
        tried.append({"block": block, "shared_days": len(common),
                      "p90_c": round(p90, 2),
                      "result": "MATCH" if p90 <= AGREE_P90_C else "different station"})
        if p90 <= AGREE_P90_C:
            return block, tried
        time.sleep(2)
    return None, tried


def main() -> int:
    survey = json.loads(
        (ROOT / "heat" / "data" / "latam_survey.json").read_text())["stations"]
    viable = [r for r in survey if r["verdict"] in ("bridge_job", "present_only")]
    only = sys.argv[1:] or None
    results = []
    for r in viable:
        if only and r["station"] not in only and r["name"].split()[0] not in only:
            continue
        sid = r["station"]
        g = ghcn_days(sid)
        probe = r["record"]["to"]
        block, tried = identify(sid, g, probe)
        entry = {"station": sid, "name": r["name"],
                 "hot_season": r["hot_season"]["months"],
                 "probe_year": probe, "candidates_tried": tried,
                 "wmo_block": block,
                 "identity": "proven" if block else "UNPROVEN"}
        results.append(entry)
        mark = block or "none"
        print(f"  {r['name'][:26]:26s} probe {probe}  block {mark:>6s}  "
              + "  ".join(f"{t['block']}:{t.get('p90_c', t['result'])}"
                          for t in tried))
    OUT.write_text(json.dumps({
        "_readme": ("Identity of each LatAm station's WMO block, PROVEN "
                    "against its own GHCN archive rather than parsed from "
                    "its id. A station without a proven block is not "
                    "gathered, because a wrong block returns another "
                    "station's valid data."),
        "agree_p90_c": AGREE_P90_C,
        "stations": results}, indent=1) + "\n")
    ok = sum(1 for r in results if r["wmo_block"])
    print(f"\n  identity proven for {ok} of {len(results)}")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
