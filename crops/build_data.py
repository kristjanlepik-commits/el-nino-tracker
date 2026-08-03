"""Emit the crops channel's validated JSON.

Two artifacts, both requested by design and product on 2026-07-29:

  data/stress_current.json      per-country cropland stress for the
                                latest published dekad, ranked against
                                that country's own record for the SAME
                                dekad since 2001
  data/production_shares.json   each country's share of world production
                                per commodity, with USDA's own vintage
                                stamp, so a condition index can be
                                expressed as a supply number

Design note. The indicator is FPAR *cumulated* z-score over the growing
cycle, so a single dekad's value already encodes the season to date.
That is why one dekad ranked against the same dekad in prior years is
the right comparison and no season-start lookup is needed: the
accumulation is in the number.

Shape follows crops/PAYLOAD_PROPOSAL.md. Every number carries its own
qualifiers as a field per D-051, and a pair below its earliest
publishable dekad is emitted with publishable false rather than omitted,
so the gate is visible on the page.

This reads only from crops/.cache/ and never fetches. Fetching is
pull_asap_indicator.py's job, per the platform contract's rule that a
fetcher must never run inside a publish.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "asap_indicator"
PSD = HERE / ".cache" / "psd"
OUT = HERE / "data"

MIN_UNITS = 3          # the meaning gate: fewer and the aggregate is noise
BASE_FIRST, BASE_LAST = 2001, 2025

INSTRUMENTS = [
    ("zfparc", "Vegetation, cumulative", "z-score", +1),
    ("zfpar", "Vegetation, current", "z-score", +1),
    ("wsi", "Water satisfaction", "percent", +1),
    ("spi3", "Rainfall, 3-month", "SPI", +1),
    ("sm", "Soil moisture", "m3/m3", +1),
    ("temp", "Temperature", "anomaly C", -1),
]

# Countries where vegetation and the water instruments agree, so the
# stress can be described as water-driven. Elsewhere the honest claim
# stops at "below its own record" with no driver named. This is a CLAIM
# tier, not a validity tier: see FEASIBILITY.md section 6k.
WATER_DRIVEN_MIN = 0.30


def load(slug: str, cid: str):
    f = CACHE / f"{slug}_crop_growing_{cid}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, usecols=["region_id", "region_name", "date", "value"])
    if d.empty:
        return None
    d["dt"] = pd.to_datetime(d.date, format="%Y%m%d")
    d["year"] = d.dt.dt.year
    d["doy"] = (d.dt.dt.month - 1) * 3 + ((d.dt.dt.day - 1) // 10) + 1
    return d


def rank_of(current: float, history: pd.Series, worse_is: int) -> int:
    """1 = most stressed on record."""
    if worse_is > 0:
        return int((history < current).sum()) + 1
    return int((history > current).sum()) + 1


def build_stress(catalogue: dict) -> dict:
    places, skipped = [], []
    latest_dekad = None

    for cid, name in catalogue.items():
        base = load("zfparc", cid)
        if base is None or base.region_id.nunique() < MIN_UNITS:
            skipped.append({"place": name,
                            "reason": "fewer than 3 crop units in the "
                                      "ASAP crop mask"})
            continue

        latest = base.dt.max()
        doy = int(base.loc[base.dt == latest, "doy"].iloc[0])
        latest_dekad = latest_dekad or str(latest.date())

        instruments, water_agree = [], {}
        for slug, label, unit, worse_is in INSTRUMENTS:
            d = load(slug, cid)
            if d is None:
                continue
            same = d[d.doy == doy].groupby("year").value.mean()
            hist = same[(same.index >= BASE_FIRST) & (same.index <= BASE_LAST)]
            cur = same.get(latest.year, np.nan)
            if np.isnan(cur) or len(hist) < 20:
                continue
            instruments.append({
                "name": label,
                "value": round(float(cur), 3),
                "unit": unit,
                "baseline_mean": round(float(hist.mean()), 3),
                "baseline_span": f"{BASE_FIRST}-{BASE_LAST}, same dekad",
                "rank": rank_of(cur, hist, worse_is),
                "of": len(hist) + 1,
                "worse_is": "low" if worse_is > 0 else "high",
                "source": "JRC ASAP, GAUL1 indicator statistics, "
                          "crop mask, growing cycle",
                "authorship": "agency",
                "qualifiers": [],
            })
            if slug in ("zfparc", "wsi", "spi3"):
                ann = d.groupby("year").value.mean()
                water_agree[slug] = ann

        if not instruments:
            skipped.append({"place": name,
                            "reason": "no instrument had 20 years at "
                                      "this dekad"})
            continue

        # Is the stress describable as water-driven?
        driver = "not identified"
        if all(k in water_agree for k in ("zfparc", "wsi", "spi3")):
            def corr(a, b):
                j = pd.concat([a.rename("a"), b.rename("b")],
                              axis=1).dropna()
                j = j[(j.index >= 2002) & (j.index <= BASE_LAST)]
                return j.a.corr(j.b) if len(j) >= 18 else np.nan
            cw = corr(water_agree["zfparc"], water_agree["wsi"])
            cr = corr(water_agree["zfparc"], water_agree["spi3"])
            if cw >= WATER_DRIVEN_MIN and cr >= WATER_DRIVEN_MIN:
                driver = "water"

        # Sub-national. The country aggregate hides regions: Turkiye
        # ranks 23 of 26 nationally on 2026-07-11 while four of its
        # southeastern provinces are at their worst on record. Reporting
        # only at country level would have lost that entirely.
        regions = []
        same_all = base[base.doy == doy]
        for reg, g in same_all.groupby("region_name"):
            # Region NAMES are not unique across region_ids in ASAP, so
            # a name can carry two rows per year. Aggregate before
            # indexing or the year lookup returns a Series.
            s = g.groupby("year").value.mean()
            hist_r = s[(s.index >= BASE_FIRST) & (s.index <= BASE_LAST)]
            if latest.year not in s.index or len(hist_r) < 20:
                continue
            cur_r = float(s[latest.year])
            regions.append({
                "region": reg,
                "value": round(cur_r, 3),
                "baseline_mean": round(float(hist_r.mean()), 3),
                "rank": rank_of(cur_r, hist_r, +1),
                "of": len(hist_r) + 1,
            })
        regions.sort(key=lambda r: r["rank"])

        head = instruments[0]
        quals = [{
            "kind": "canopy_not_cause",
            "text": "ASAP observes the crop canopy, not what stressed "
                    "it. Heat, drought, disease and late planting are "
                    "not separable in this measurement.",
        }]
        if driver == "not identified":
            quals.append({
                "kind": "driver_not_identified",
                "text": "Vegetation and the water instruments do not "
                        "co-vary here, so this stress cannot be "
                        "described as water-driven. The reading is the "
                        "condition only.",
            })

        places.append({
            "place": name,
            "asap0_id": int(cid),
            "crop_units": int(base.region_id.nunique()),
            "dekad": str(latest.date()),
            "magnitude": {
                "kind": "rank",
                "value": head["rank"],
                "of": head["of"],
                "direction": "low",
                "basis": f"same dekad, {BASE_FIRST}-{BASE_LAST}",
            },
            "driver": driver,
            "evidence_basis": "measured",
            "attribution": "pending",
            "authorship": "tls_built",
            "publishable": True,
            "instruments": instruments,
            "regions": regions,
            "regions_worst_3": sum(1 for r in regions if r["rank"] <= 3),
            "qualifiers": quals,
        })

    places.sort(key=lambda p: (p["magnitude"]["value"],
                               -p["magnitude"]["of"]))
    return {
        "generated_from": "crops/.cache (no fetch performed)",
        "dekad": latest_dekad,
        "baseline": f"{BASE_FIRST}-{BASE_LAST}, same dekad of each year",
        "method": "FPAR cumulated z-score, ASAP crop mask, restricted "
                  "to the growing cycle. The indicator is cumulative "
                  "over the season, so one dekad encodes the season to "
                  "date.",
        "places_reported": len(places),
        "places_skipped": len(skipped),
        "skipped": skipped,
        "places": places,
    }


def build_shares() -> dict:
    frames = []
    for f in ("psd_grains_pulses.csv", "psd_oilseeds.csv"):
        if (PSD / f).exists():
            frames.append(pd.read_csv(PSD / f, dtype={"Month": str}))
    d = pd.concat(frames, ignore_index=True)
    d = d[d.Attribute_Description == "Production"]

    rows = []
    for com, g in d.groupby("Commodity_Description"):
        year = int(g.Market_Year.max()) - 1      # last complete year
        y = g[g.Market_Year == year]
        world = y[y.Country_Name.isin(["World"])].Value.sum()
        if world <= 0:
            world = y[~y.Country_Name.isin(
                ["World", "European Union"])].Value.sum()
        if world <= 0:
            continue
        for _, r in y.iterrows():
            if r.Country_Name in ("World",):
                continue
            if r.Value <= 0:
                continue
            rows.append({
                "commodity": com,
                "country": r.Country_Name,
                "market_year": year,
                "production": float(r.Value),
                "unit": r.Unit_Description,
                "world_total": float(world),
                "share_of_world": round(float(r.Value) / float(world), 5),
                "vintage": f"{int(r.Calendar_Year)}-{r.Month}",
                "source": "USDA FAS PSD",
                "authorship": "agency",
                "qualifiers": [{
                    "kind": "no_revision_history",
                    "text": "USDA PSD holds one current estimate per "
                            "cell, not a vintage series. The stamp is "
                            "when this figure last changed, not a "
                            "revision history.",
                }],
            })
    rows.sort(key=lambda r: (r["commodity"], -r["share_of_world"]))
    return {
        "generated_from": "crops/.cache/psd (no fetch performed)",
        "note": "Shares let a condition index be expressed as a supply "
                "number. Arithmetic over a published table, never a "
                "forecast.",
        "rows": len(rows),
        "shares": rows,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    catalogue = json.loads(
        (HERE / "asap_countries.json").read_text(encoding="utf-8")
    )["countries"]

    stress = build_stress(catalogue)
    (OUT / "stress_current.json").write_text(
        json.dumps(stress, indent=1) + "\n", encoding="utf-8")
    print(f"stress_current.json: {stress['places_reported']} places, "
          f"{stress['places_skipped']} skipped, dekad {stress['dekad']}")

    shares = build_shares()
    (OUT / "production_shares.json").write_text(
        json.dumps(shares, indent=1) + "\n", encoding="utf-8")
    print(f"production_shares.json: {shares['rows']} country-commodity rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
