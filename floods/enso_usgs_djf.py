"""DJF peak discharge against ONI, on screened unregulated gauges.

Independence, not count, is the sample-size question. Five gauges on the
Suwannee are one river measured five times, and treating them as five
observations inflates confidence without adding information. So the
selection takes the longest-record surviving gauge per river system and
reports the number of distinct systems alongside the number of gauges.
"""
import argparse, json, os, re, statistics, time, urllib.request
import datetime as dt
from collections import defaultdict

CACHE = "floods/.usgs_cache"
DV = ("https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites={site}"
      "&startDT={s}&endDT={e}&parameterCd=00060&statCd=00003")


def get(url, key, tries=3):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key)
    if os.path.exists(p):
        return open(p, encoding="utf-8", errors="replace").read()
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers={
                "User-Agent": "TheLongSwell-floods/1.0 (research)"})
            with urllib.request.urlopen(r, timeout=180) as resp:
                t = resp.read().decode("utf-8", "replace")
            open(p, "w").write(t); time.sleep(0.3); return t
        except Exception:
            if a == tries - 1: return ""
            time.sleep(3 * (a + 1))
    return ""


def river_of(name):
    n = name.upper()
    n = re.sub(r"\b(NEAR|NR|AT|ABOVE|ABV|BELOW|BLW|US|SR|CR)\b.*", "", n)
    n = re.sub(r"[,.].*", "", n)
    n = re.sub(r"\b(NORTH|SOUTH|EAST|WEST|N|S|E|W|PRONG|FORK|LITTLE|UPPER|LOWER)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def spearman(x, y):
    n = len(x)
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0]*n; i = 0
        while i < n:
            j = i
            while j+1 < n and v[order[j+1]] == v[order[i]]: j += 1
            avg = (i+j)/2 + 1
            for k in range(i, j+1): r[order[k]] = avg
            i = j+1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx)/n, sum(ry)/n
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = (sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry)) ** .5
    return num/den if den else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", default="floods/data/usgs_screen_fl.json")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--start", type=int, default=1950)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--out", default="floods/data/enso_usgs_djf_fl.json")
    args = ap.parse_args()

    scr = json.load(open(args.screen))
    by_river = defaultdict(list)
    for g in scr["gauges"]:
        by_river[river_of(g["name"])].append(g)
    picks = [max(v, key=lambda g: g["years"]) for v in by_river.values()]
    picks.sort(key=lambda g: -g["years"])
    picks = picks[:args.n]
    print(f"{len(scr['gauges'])} screened gauges span {len(by_river)} river systems; "
          f"taking the longest per system, {len(picks)} gauges")

    oni = {}
    for line in open("data/oni_full_history.csv"):
        if line.startswith("#") or line.startswith("year"): continue
        p = line.strip().split(",")
        if len(p) == 3 and p[1] == "DJF":
            oni[int(p[0])] = float(p[2])

    rows = []
    for i, g in enumerate(picks, 1):
        txt = get(DV.format(site=g["site"], s=f"{args.start-1}-12-01",
                            e=f"{args.end}-03-01"), f"dv_{g['site']}.rdb")
        lines = [l for l in txt.splitlines() if l and not l.startswith("#")]
        if len(lines) < 3:
            print(f"  {g['site']} no daily data"); continue
        hdr = lines[0].split("\t")
        di = hdr.index("datetime")
        vi = next((k for k, h in enumerate(hdr) if h.endswith("_00060_00003")), None)
        if vi is None:
            print(f"  {g['site']} no discharge column"); continue
        winter = defaultdict(list)
        for l in lines[2:]:
            f = l.split("\t")
            if len(f) <= max(di, vi): continue
            try: d = dt.date.fromisoformat(f[di]); v = float(f[vi])
            except Exception: continue
            if d.month == 12: winter[d.year+1].append(v)
            elif d.month in (1, 2): winter[d.year].append(v)
        yrs = sorted(y for y, vals in winter.items()
                     if len(vals) >= 80 and args.start <= y <= args.end and y in oni)
        if len(yrs) < 30:
            print(f"  {g['site']} only {len(yrs)} complete winters"); continue
        peaks = [max(winter[y]) for y in yrs]
        o = [oni[y] for y in yrs]
        rho = spearman(o, peaks)
        rows.append({"site": g["site"], "name": g["name"],
                     "river": river_of(g["name"]), "winters": len(yrs),
                     "first": yrs[0], "last": yrs[-1], "spearman": round(rho, 3),
                     "regulated_frac": g["regulated_frac"]})
        print(f"  [{i:>2}] {g['site']} {len(yrs):>3} winters  rho {rho:+.3f}  {g['name'][:44]}")

    rhos = sorted(r["spearman"] for r in rows)
    # The median of an even-length list is the mean of the middle pair.
    # rhos[len//2] takes the upper element instead, which is a different
    # gauge's value wearing the word "median". It reported +0.379, the
    # Withlacoochee-Hillsborough figure, when the median is +0.374.
    med = (statistics.median(rhos) if rhos else None)
    pos = sum(1 for r in rhos if r > 0)
    out = {"question": "does the El Nino winter precipitation signal appear in peak discharge",
           "instrument": "USGS NWIS daily mean discharge, parameter 00060, OBSERVED",
           "oni_source": "data/oni_full_history.csv, CPC ONI, DJF season",
           "method": ("per gauge, the maximum daily mean discharge in each Dec-Feb "
                      "winter, Spearman-correlated against that winter's DJF ONI"),
           "screen": args.screen,
           "gauges": len(rows), "river_systems": len(set(r["river"] for r in rows)),
           "median_spearman": med, "positive": pos, "negative": len(rhos)-pos,
           "results": sorted(rows, key=lambda r: -r["spearman"])}
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"\ngauges {len(rows)}  distinct river systems {out['river_systems']}")
    print(f"median Spearman {med}   positive {pos}  negative {len(rhos)-pos}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
