"""Test whether Heathrow has warmed faster than its neighbours.

WHY. Readers on X challenged London's record on the grounds that Heathrow is
a busier airport than it was in 1949, so the site itself has warmed
independently of the regional climate. Our own payload conceded the point
before they raised it: London's station_disclosure said "Station history not
yet checked."

The challenge is plausible and it is specific to what our metric measures. We
count days above a threshold built from the station's OWN record, which
measures "this thermometer is recording more hot days" and does not by itself
separate a warming climate from a warming site. At an airport that grew around
its own thermometer those can diverge, and Heathrow is the likeliest city in
our set for them to.

THE TEST. Summer mean maxima per year at Heathrow and at neighbours, then the
DIFFERENCE series Heathrow minus neighbour. Differencing removes the shared
weather, so what remains is site and instrument. A trend in the difference is
a site effect; a flat difference means Heathrow warmed with its region and the
challenge is answered with evidence rather than assertion.

Same construction as heat/blend_gate.py, pointed at trend instead of at steps.

NEIGHBOURS CHOSEN FOR CONTRAST, NOT CONVENIENCE:

    Rothamsted   rural Hertfordshire, agricultural research station
    Wisley       rural Surrey, botanical garden
    Kew          suburban west London, botanical garden
    Northolt     another airfield, so a site that grew in the same way

If Heathrow diverges from the rural pair but tracks Northolt, that is an
airport effect. If it diverges from everything, it is Heathrow specifically.
If it tracks all four, the reader's objection does not survive contact.

A RESULT EITHER WAY IS PUBLISHABLE. Confirming the challenge means caveating a
number we already published, which is the more useful outcome of the two.
"""
from __future__ import annotations

import concurrent.futures
import csv
import io
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CEDA = ("https://dap.ceda.ac.uk/badc/ukmo-midas-open/data/"
        "uk-daily-temperature-obs/dataset-version-202607")
TOKEN = Path.home() / ".ceda_token"

STATIONS = {
    "Heathrow":   ("greater-london", "00708_heathrow"),
    "Rothamsted": ("hertfordshire", "00471_rothamsted"),
    "Wisley":     ("surrey", "00719_wisley"),
    "Kew":        ("greater-london", "00721_kew"),
    "Northolt":   ("greater-london", "00709_northolt"),
}
MIN_DAYS = 80          # June-August days needed for a year to count


def _get(url, tok):
    return subprocess.run(
        ["curl", "-sS", "--max-time", "90", "-H", f"Authorization: Bearer {tok}",
         url], capture_output=True).stdout.decode("latin-1", "replace")


def summer_means(county, sdir, tok):
    """Mean June-August daily maximum per year, from the 21h reading."""
    listing = _get(f"{CEDA}/{county}/{sdir}/qc-version-1/", tok)
    files = re.findall(r'href="([^"]*_qcv-1_\d{4}\.csv)"', listing)
    if not files:
        return {}

    def one(f):
        return _get(f"{CEDA}/{county}/{sdir}/qc-version-1/{f}", tok)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        texts = list(ex.map(one, files))

    per = {}
    for txt in texts:
        if "\ndata\n" not in txt:
            continue
        for r in csv.DictReader(io.StringIO(txt.split("\ndata\n", 1)[1])):
            t = (r.get("ob_end_time") or "").strip()
            if len(t) < 13 or (r.get("ob_hour_count") or "").strip() != "12":
                continue
            if t[11:13] != "21":
                continue
            if t[5:7] not in ("06", "07", "08"):
                continue
            v = (r.get("max_air_temp") or "").strip()
            try:
                per.setdefault(int(t[:4]), []).append(float(v))
            except ValueError:
                continue
    return {y: statistics.mean(vs) for y, vs in per.items() if len(vs) >= MIN_DAYS}


def slope(pairs):
    """Least-squares slope in degrees per decade."""
    n = len(pairs)
    if n < 20:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    den = sum((x - mx) ** 2 for x in xs)
    return None if den == 0 else (num / den) * 10


def main() -> int:
    if not TOKEN.exists():
        print("  no CEDA token", file=sys.stderr)
        return 1
    tok = TOKEN.read_text().strip()
    series = {}
    for name, (county, sdir) in STATIONS.items():
        series[name] = summer_means(county, sdir, tok)
        yrs = sorted(series[name])
        print(f"  {name:11s} {len(yrs):3d} summers, "
              f"{yrs[0] if yrs else '-'}-{yrs[-1] if yrs else '-'}")

    h = series["Heathrow"]
    print("\n  Heathrow minus neighbour, June-August mean maximum")
    print(f"  {'neighbour':11s} {'n':>4s} {'slope C/decade':>15s} "
          f"{'early mean':>11s} {'late mean':>10s} {'change':>8s}")
    print("  " + "-" * 62)
    for name in STATIONS:
        if name == "Heathrow":
            continue
        o = series[name]
        common = sorted(set(h) & set(o))
        if len(common) < 20:
            print(f"  {name:11s} {len(common):4d}  too few shared summers")
            continue
        diff = [(y, h[y] - o[y]) for y in common]
        s = slope(diff)
        early = [d for y, d in diff if y <= common[0] + 19]
        late = [d for y, d in diff if y >= common[-1] - 19]
        em, lm = statistics.mean(early), statistics.mean(late)
        print(f"  {name:11s} {len(common):4d} {s:+15.3f} {em:+11.2f} "
              f"{lm:+10.2f} {lm - em:+8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
