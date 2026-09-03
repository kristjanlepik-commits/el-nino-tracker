"""Screen USGS gauges for regulation before correlating anything against ONI.

Gauge count is not coverage. A gauge below a dam or inside a managed
canal network records the operator's decisions as much as the weather, so
correlating it against ONI measures reservoir policy. This screen decides
which gauges are allowed into the analysis, and it runs first.

Two filters, both conservative:

  1. USGS peak-streamflow qualification codes. Code 6 means discharge
     affected by regulation or diversion; code 5 means affected to an
     unknown degree. A gauge carrying either on more than REG_MAX_FRAC of
     its annual peaks is out.
  2. Station names indicating built water infrastructure. South Florida
     in particular is a canal network, and its structures are gauged.

A gauge that fails either is excluded and the reason is recorded, so the
exclusions can be read rather than trusted.
"""
import argparse
import json
import os
import time
import urllib.request

SITE_URL = ("https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd={st}"
            "&siteType=ST&hasDataTypeCd=dv&outputDataTypeCd=dv"
            "&parameterCd=00060&siteStatus=all")
PEAK_URL = ("https://nwis.waterdata.usgs.gov/nwis/peak?site_no={site}"
            "&agency_cd=USGS&format=rdb")
CACHE = "floods/.usgs_cache"
REG_CODES = {"5", "6"}
REG_MAX_FRAC = 0.10
MIN_YEARS = 50
MIN_PEAKS = 30
NAME_BAD = ("CANAL", " C-", "C-1", "S-", " L-", "LOCK", "DAM", "SPILLWAY",
            "STRUCTURE", "WEIR", "DIVERSION", "RESERVOIR", "NR DAM",
            "CONTROL", "PUMP", "OUTLET", "INTAKE", "AT S", "BELOW DAM")


def get(url, cache_key, tries=3):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, cache_key)
    if os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read()
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TheLongSwell-floods/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                txt = r.read().decode("utf-8", "replace")
            open(path, "w").write(txt)
            time.sleep(0.25)
            return txt
        except Exception:
            if a == tries - 1:
                return ""
            time.sleep(2 * (a + 1))
    return ""


def rdb(txt):
    rows = [l for l in txt.splitlines() if l and not l.startswith("#")]
    if len(rows) < 3:
        return []
    hdr = rows[0].split("\t")
    return [dict(zip(hdr, r.split("\t"))) for r in rows[2:] if r.strip()]


def years(rec):
    try:
        b = int(rec["begin_date"][:4])
        e = int(rec["end_date"][:4])
        return e - b
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="fl")
    ap.add_argument("--out", default="floods/data/usgs_screen_fl.json")
    args = ap.parse_args()

    sites = rdb(get(SITE_URL.format(st=args.state), f"sites_{args.state}.rdb"))
    best = {}
    for r in sites:
        s = r.get("site_no")
        if not s:
            continue
        if s not in best or years(r) > years(best[s]):
            best[s] = r
    print(f"{args.state.upper()}: {len(sites)} rows, {len(best)} distinct sites")

    longrec = {s: r for s, r in best.items()
               if years(r) >= MIN_YEARS and r.get("end_date", "") >= "2024-01-01"}
    print(f"  with >= {MIN_YEARS} yr and still reporting: {len(longrec)}")

    kept, dropped = [], []
    for i, (s, r) in enumerate(sorted(longrec.items(), key=lambda kv: -years(kv[1])), 1):
        name = (r.get("station_nm") or "").upper()
        rec = {"site": s, "name": r.get("station_nm", ""),
               "begin": r.get("begin_date", ""), "end": r.get("end_date", ""),
               "years": years(r)}
        hit = next((b for b in NAME_BAD if b in name), None)
        if hit:
            rec["excluded"] = f"station name contains {hit.strip()!r}"
            dropped.append(rec)
            continue
        peaks = rdb(get(PEAK_URL.format(site=s), f"peak_{s}.rdb"))
        peaks = [p for p in peaks if p.get("peak_va")]
        if len(peaks) < MIN_PEAKS:
            rec["excluded"] = f"only {len(peaks)} annual peaks on record"
            dropped.append(rec)
            continue
        regd = sum(1 for p in peaks
                   if REG_CODES & set((p.get("peak_cd") or "").split(",")))
        frac = regd / len(peaks)
        rec.update({"n_peaks": len(peaks), "regulated_peaks": regd,
                    "regulated_frac": round(frac, 3)})
        if frac > REG_MAX_FRAC:
            rec["excluded"] = (f"regulation codes on {regd} of {len(peaks)} "
                               f"peaks ({frac:.0%})")
            dropped.append(rec)
        else:
            kept.append(rec)
        if i % 40 == 0:
            print(f"  screened {i}/{len(longrec)}  kept {len(kept)}")

    kept.sort(key=lambda r: -r["years"])
    out = {"state": args.state, "screened": len(longrec),
           "kept": len(kept), "dropped": len(dropped),
           "rules": {"min_years": MIN_YEARS, "min_peaks": MIN_PEAKS,
                     "regulation_codes": sorted(REG_CODES),
                     "max_regulated_fraction": REG_MAX_FRAC,
                     "name_exclusions": list(NAME_BAD)},
           "caveat": ("Peak-flow qualification codes are applied by USGS "
                      "staff and are not exhaustive. A gauge passing this "
                      "screen is not certified natural, only not flagged."),
           "gauges": kept, "excluded": dropped}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"\nKEPT {len(kept)}   DROPPED {len(dropped)}")
    print(f"\n{'site':>10} {'yrs':>4} {'reg%':>6}  name")
    for r in kept[:25]:
        print(f"{r['site']:>10} {r['years']:>4} {r['regulated_frac']:>6.0%}  {r['name'][:52]}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
