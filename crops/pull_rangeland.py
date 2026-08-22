"""Pull ASAP's RANGELAND class for one country and emit it as data.

WHY THIS EXISTS. A reader asked on LinkedIn why Switzerland was missing
from /crops and pointed at Alpine pasture drought. Two separate reasons,
and only one of them is about Switzerland:

  1. ASAP treats Switzerland as ONE crop unit, below the three-unit
     minimum the sub-national method needs. Liberia is published on
     five; Switzerland has one.
  2. The story is PASTURE. Every indicator this channel pulls is
     "Crop during growing cycle". ASAP also publishes "Rangeland during
     growing cycle" over its own rangeland mask, and we have never
     pulled it for any country.

For Switzerland the second is the bigger one: 9,251 km2 of rangeland
against 5,772 of cropland, and ASAP's own reference table flags
an_range=1, so JRC analyses it.

WHAT THIS IS NOT. Not a channel. It emits one country's series so a
finding can be checked and drawn from committed data rather than from a
scratch file on one laptop, which is the provenance failure fires caught
in crops/asap_reference.py the same week. Whether rangeland becomes a
published instrument is product's call, not this script's.

Method is the channel's: same dekad-of-year, ranked against 2001-2025,
worse-is direction from INSTRUMENTS.

Usage:
    .venv/bin/python crops/pull_rangeland.py 216 Switzerland
"""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from pull_asap_indicator import BASE, INDICATORS, as_rangeland  # noqa: E402
from crops.build_data import BASE_FIRST, BASE_LAST, INSTRUMENTS, rank_of  # noqa: E402

CACHE = HERE / ".cache" / "asap_rangeland"
OUT = HERE / "data" / "rangeland.json"
WORSE = {s: w for s, _l, _u, w in INSTRUMENTS}
LABEL = {s: l for s, l, _u, _w in INSTRUMENTS}


def fetch(slug: str, cid: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{slug}_range_{cid}.csv"
    if out.exists() and out.stat().st_size > 0:
        return out
    tmp = out.with_suffix(".partial")
    cmd = ["curl", "-sS", "--max-time", "420", "-G", BASE,
           "--data-urlencode", "gaul_level=1",
           "--data-urlencode", f"country_id={cid}"]
    for k, v in as_rangeland(INDICATORS[slug]).items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    cmd += ["-o", str(tmp), "-w", "%{http_code}"]
    code = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    if code != "200" or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{slug}: HTTP {code}")
    tmp.replace(out)
    return out


def main() -> int:
    cid, name = sys.argv[1], sys.argv[2]
    doc = json.loads((HERE / "data" / "stress_current.json").read_text())
    dekad = doc["dekad"]
    anchor = pd.Timestamp(dekad)
    doy = (anchor.month - 1) * 3 + ((anchor.day - 1) // 10) + 1
    cur_year = anchor.year

    out = {
        "_what": "ASAP's RANGELAND class for one country, same method as "
                 "the crop channel: each instrument against its own "
                 f"{BASE_FIRST}-{BASE_LAST} record at the same "
                 "dekad-of-year.",
        "_not": "a published channel instrument. Emitted so a finding can "
                "be checked and drawn from committed data rather than "
                "from a scratch file. Whether rangeland gets published is "
                "product's call.",
        "_class": "Rangeland during growing cycle (ASAP class_id 2)",
        "_authorship": "tls_built",
        "_evidence_basis": "measured",
        "dekad": dekad,
        "places": {},
    }
    if OUT.exists():
        out = json.loads(OUT.read_text())
        out["dekad"] = dekad

    place = {"asap0_id": int(cid), "instruments": {}}
    for slug in INDICATORS:
        base = slug.replace("_crop_growing", "")
        try:
            f = fetch(slug, cid)
        except RuntimeError as e:
            place["instruments"][base] = {"available": False,
                                          "absent": "fetch_failed",
                                          "absent_because": str(e)}
            continue
        d = pd.read_csv(f, usecols=["region_name", "date", "value"])
        if d.empty:
            place["instruments"][base] = {
                "available": False, "absent": "not_published_for_class",
                "absent_because": f"{LABEL[base]} is not published for the "
                                  f"rangeland class here."}
            continue
        dt = pd.to_datetime(d.date, format="%Y%m%d")
        d["year"] = dt.dt.year
        d["doy"] = (dt.dt.month - 1) * 3 + ((dt.dt.day - 1) // 10) + 1
        s = d[d.doy == doy].groupby("year").value.mean()
        h = s[(s.index >= BASE_FIRST) & (s.index <= BASE_LAST)]
        if cur_year not in s.index:
            place["instruments"][base] = {
                "available": False, "absent": "no_current_value",
                "absent_because": f"{LABEL[base]} has {len(h)} comparable "
                                  f"years here but no value for this dekad."}
            continue
        if len(h) < 20:
            place["instruments"][base] = {
                "available": False, "absent": "too_few_comparable_years",
                "absent_because": f"Fewer than 20 comparable years."}
            continue
        rk = rank_of(float(s[cur_year]), h, WORSE[base])
        place["instruments"][base] = {
            "label": LABEL[base],
            "value": round(float(s[cur_year]), 3),
            "baseline_mean": round(float(h.mean()), 3),
            "baseline_sd": (round(float(h.std()), 3)
                            if float(h.std()) > 1e-6 else None),
            "rank": rk, "of": len(h) + 1,
            "worse_is": "low" if WORSE[base] > 0 else "high",
            "regions": int(d.region_name.nunique()),
            "series": {int(y): round(float(v), 3) for y, v in s.items()},
            "available": True,
        }
    out["places"][name] = place
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    got = sum(1 for v in place["instruments"].values() if v.get("available"))
    print(f"rangeland.json: {name}, {got} of {len(INDICATORS)} instruments, "
          f"dekad {dekad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
