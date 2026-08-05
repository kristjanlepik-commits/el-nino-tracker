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


def _rank_statement(rank: int, of: int, last: int,
                    worse_is: str = "low") -> str:
    """Value and basis in one string so they cannot be separated.
    Called at country and region level from one place, so the two
    cannot drift apart.

    worse_is is NOT optional in meaning even though it defaults. rank is
    rank-by-worseness, so for temperature rank 1 is the HOTTEST. This
    function previously hardcoded "lowest" and would have published
    Tunisia at +5.34 C as "lowest of 26 observations". The rank was
    right; the sentence built from it dropped the one field that sets
    its direction.
    """
    end = "lowest" if worse_is == "low" else "highest"
    if rank == 1:
        lead = end
    else:
        # 23th is the kind of thing a reader notices and a checker does
        # not, so the suffix is computed rather than assumed to be "th".
        suffix = ("th" if 11 <= rank % 100 <= 13
                  else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th"))
        lead = f"{rank}{suffix} {end}"
    return (f"{lead} of {of} observations for this point in the "
            f"season, {BASE_FIRST}-{last}")


def rank_of(current: float, history: pd.Series, worse_is: int) -> int:
    """1 = most stressed on record."""
    if worse_is > 0:
        return int((history < current).sum()) + 1
    return int((history > current).sum()) + 1


SEASON_STARTS = json.loads(
    (HERE / "season_starts.json").read_text(encoding="utf-8")
)["starts"] if (HERE / "season_starts.json").exists() else {}


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

        instruments, water_agree, loaded = [], {}, {}
        for slug, label, unit, worse_is in INSTRUMENTS:
            d = load(slug, cid)
            loaded[slug] = d
            if d is None:
                # An absent instrument is emitted, never omitted. A key
                # that is simply missing makes "not measured here" and
                # "nothing to report" look identical, and those are
                # opposite claims. D-051 applied to a gap.
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False,
                    "unavailable_because": "ASAP does not publish this "
                                           "indicator for this country",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            same = d[d.doy == doy].groupby("year").value.mean()
            hist = same[(same.index >= BASE_FIRST) & (same.index <= BASE_LAST)]
            cur = same.get(latest.year, np.nan)
            # Absences are stated here too. This used to `continue`,
            # which silently dropped soil moisture from every country
            # while the region rows below said explicitly that it had
            # not reported. Same fix as the region level, one level up,
            # and it was invisible until the layers were due to render.
            if same.empty:
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False, "absent": "undefined_at_this_dekad",
                    "absent_because": f"{label} is not defined for this "
                                      f"country at this point in the season.",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            if np.isnan(cur):
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False, "absent": "no_current_value",
                    "absent_because": f"{label} has not reported for this "
                                      f"dekad yet.",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
                continue
            if len(hist) < 20:
                instruments.append({
                    "name": label, "value": None, "unit": unit,
                    "available": False,
                    "absent": "too_few_comparable_years",
                    "absent_because": f"Fewer than 20 comparable years of "
                                      f"{label.lower()} at this dekad.",
                    "source": "JRC ASAP", "authorship": "agency",
                    "qualifiers": [],
                })
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
                # Five layers each showing a bare rank is the missing
                # basis multiplied by five. Bound here as it is on
                # magnitude and on region rows.
                "statement": _rank_statement(
                    rank_of(cur, hist, worse_is), len(hist) + 1,
                    latest.year, "low" if worse_is > 0 else "high"),
                "source": "JRC ASAP, GAUL1 indicator statistics, "
                          "crop mask, growing cycle",
                "authorship": "agency",
                "available": True,
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
            rk = rank_of(cur_r, hist_r, +1)
            of = len(hist_r) + 1
            regions.append({
                "region": reg,
                "value": round(cur_r, 3),
                "baseline_mean": round(float(hist_r.mean()), 3),
                "rank": rk,
                "of": of,
                # A region row used to declare rank and of but NOT its
                # basis, and the basis lived only on the country object.
                # The claim that reached copy and was wrong for 7 of
                # Chad's 8 regions was a REGION claim, so the writer had
                # no basis field in front of them to drop.
                "basis": f"same dekad, {BASE_FIRST}-{BASE_LAST}",
                # And the value and its basis bound into one computed
                # field, so dropping the basis is visibly dropping half
                # of a field rather than trimming a sentence. Computed,
                # never typed, per the ban on free text that stops
                # tracking its data.
                "statement": _rank_statement(rk, of, latest.year),
                # The region's own record, so a region page can show it
                # against itself the way the country block shows Chad.
                # Same shape as the country chance_baseline series.
                "series": {int(y): round(float(v), 3)
                           for y, v in s.items()
                           if BASE_FIRST <= y <= latest.year},
            })
        # Per-region driver. The country-level driver is evidence about
        # the country, and rendering it on a region page asserts
        # something about that region. Namibia is water-driven as a
        # country and Hardap is not: veg~rainfall is 0.15 there against
        # 0.30 required. That is the same fault as "driest" over Cairo,
        # a country property worn by a region, so the test is run per
        # region and the region carries its own answer.
        # Per-region summary for every instrument, absences included.
        # Series stay vegetation-only: stress_current.json is git-tracked
        # and rewritten wholesale each dekad, and JSON full of changed
        # floats deltas badly, so a second series is repo growth for
        # charts nothing renders yet.
        for slug, label, unit, worse_is in INSTRUMENTS:
            if slug == "zfparc":
                continue
            dd = loaded.get(slug)
            for entry in regions:
                inst = entry.setdefault("instruments", {})
                if dd is None:
                    inst[slug] = {
                        "available": False,
                        "absent": "not_published_for_country",
                        "absent_because": f"ASAP does not publish "
                                          f"{label.lower()} for this country.",
                    }
                    continue
                sub = dd[(dd.doy == doy) & (dd.region_name == entry["region"])]
                ser = sub.groupby("year").value.mean()
                if ser.empty:
                    # Never defined here at this point in the season, as
                    # opposed to defined-but-late. SPI is undefined in
                    # hyper-arid regions when the accumulation window
                    # holds no measurable rain: Luxor carries SPI only
                    # in winter dekads. Calling that "not reported yet"
                    # would read as temporary and it is seasonal.
                    inst[slug] = {
                        "available": False,
                        "absent": "undefined_at_this_dekad",
                        "absent_because": f"{label} is not defined for "
                                          f"this region at this point in "
                                          f"the season.",
                    }
                    continue
                h = ser[(ser.index >= BASE_FIRST) & (ser.index <= BASE_LAST)]
                if latest.year not in ser.index:
                    # Temporary by wording as well as by fact: this
                    # instrument publishes behind the others and will
                    # report. "Not measured here" would be permanent and
                    # false.
                    # Accurate reason. Soil moisture publishes one dekad
                    # behind the vegetation indicators, so it has full
                    # history here and no value for the dekad reported.
                    # "Too few years" would have been false.
                    inst[slug] = {
                        "available": False,
                        "absent": "no_current_value",
                        "absent_because": f"{label} has not reported for "
                                          f"this dekad yet.",
                    }
                    continue
                if len(h) < 20:
                    inst[slug] = {
                        "available": False,
                        "absent": "too_few_comparable_years",
                        "absent_because": f"Fewer than 20 comparable "
                                          f"years of {label.lower()} at "
                                          f"this dekad.",
                    }
                    continue
                v = float(ser[latest.year])
                # Keyed by slug and stripped of anything constant per
                # instrument. name, unit and worse_is live once in the
                # top-level legend rather than 2,122 times each: this
                # file is git-tracked and rewritten every dekad, so
                # repeated strings are repo growth, not just size.
                inst[slug] = {
                    "value": round(v, 3),
                    "baseline_mean": round(float(h.mean()), 3),
                    "rank": rank_of(v, h, worse_is), "of": len(h) + 1,
                    "available": True,
                }

        _wsi = loaded.get("wsi")
        _spi = loaded.get("spi3")
        if _wsi is not None and _spi is not None:
            zr = base.groupby(["region_name", "year"]).value.mean()
            wr = _wsi.groupby(["region_name", "year"]).value.mean()
            sr = _spi.groupby(["region_name", "year"]).value.mean()
            for entry in regions:
                nm = entry["region"]
                try:
                    j = pd.concat([zr[nm].rename("a"), wr[nm].rename("b"),
                                   sr[nm].rename("c")], axis=1).dropna()
                except KeyError:
                    entry["driver"] = "not identified"
                    continue
                j = j[(j.index >= 2002) & (j.index <= BASE_LAST)]
                ok = (len(j) >= 18
                      and j.a.corr(j.b) >= WATER_DRIVEN_MIN
                      and j.a.corr(j.c) >= WATER_DRIVEN_MIN)
                entry["driver"] = "water" if ok else "not identified"
        else:
            for entry in regions:
                entry["driver"] = "not identified"

        regions.sort(key=lambda r: r["rank"])

        # The empirical chance baseline, per place. Design needs this
        # as a drawn object rather than a sentence, and product's
        # adopted preference is to quote the TRAJECTORY where the series
        # allows it rather than a baseline. Both need the per-year
        # series, so it is emitted rather than left to be recomputed.
        #
        # Never units/26. The uniform assumption fails wherever a series
        # trends, and it fails in different directions in different
        # places: Europe 4.0x, globally 1.39x, Chad and neighbours 0.1
        # to 0.4x. It cannot be corrected, only counted.
        panel = (base[base.doy == doy]
                 .groupby(["region_id", "year"]).value.mean().unstack())
        panel = panel.dropna()
        worst_by_year = panel.idxmin(axis=1).value_counts()
        series = {int(y): int(worst_by_year.get(y, 0))
                  for y in range(BASE_FIRST, latest.year + 1)}
        recent = [v for y, v in series.items()
                  if 2014 <= y <= BASE_LAST]
        empirical = {
            "measures": "admin units at their worst on record for this "
                        "dekad, per year",
            "series": series,
            "recent_mean": round(float(np.mean(recent)), 2) if recent else None,
            "recent_min": int(min(recent)) if recent else None,
            "recent_max": int(max(recent)) if recent else None,
            "this_year": series.get(latest.year, 0),
            "_uniform_would_say": round(len(panel) / 26, 1),
            "_note": "uniform_would_say is shown only to be argued "
                     "with. Use recent_mean.",
        }
        # The bar product adopted 2026-07-29: a count is notable when it
        # clears the place's OWN recent maximum, not when it clears a
        # mean. Sharper than a mean because it needs no distributional
        # assumption, and it is what separated Chad and Sudan from
        # Rwanda, Eritrea, Mali and Burundi.
        empirical["clears_own_recent_max"] = bool(
            recent and empirical["this_year"] > max(recent))

        # Ordering key, for design, replacing a floor they wrote
        # themselves. Neither of their two suggestions survives the data:
        # a share excess ranks China's 0-to-1 above Turkiye's 2-to-4
        # because it rewards small denominators, and an absolute excess
        # has the many-units bias they identified.
        #
        # What works is a floor plus a share. The floor removes the
        # noise cases, which are all "went from 1 to 2" or "0 to 1", and
        # the share orders what survives without a size bias. A
        # materiality threshold is domain knowledge and belongs here
        # rather than in the renderer, per the platform contract.
        _mx = max(recent) if recent else 0
        empirical["excess_abs"] = empirical["this_year"] - _mx
        empirical["excess_share"] = round(
            (empirical["this_year"] - _mx) / len(panel), 4) if len(panel) else 0.0
        # Renamed. "notable" invited being read as a finding, and it
        # was: an h1 claimed six such countries were more than their own
        # history explains, when six is the 57th percentile of the last
        # 35 dekads. The field decides what to SHOW, never what is true.
        # Both keys emitted for one dekad so nothing breaks mid-switch.
        _sel = bool(empirical["clears_own_recent_max"]
                    and empirical["this_year"] >= 3)
        empirical["selected_for_display"] = _sel
        empirical["notable"] = _sel   # deprecated, remove after 2026-08-14
        empirical["_order_by"] = ("filter on selected_for_display, order by "
                                  "excess_share. Never order on "
                                  "clears_own_recent_max alone: it is a "
                                  "boolean over a small sample and puts "
                                  "1-against-0 beside 8-against-3. And "
                                  "the COUNT of selected places is not a "
                                  "finding: it sits at the 57th "
                                  "percentile of the last 35 dekads.")

        # Seasonality. The season window is derived from ASAP's static
        # phenology, and the static-ness is the point here. Section 6i
        # disqualified these windows for drift precisely because they
        # cannot change; a seasonality claim needs a climatology rather
        # than an observation, so the same property qualifies them. This
        # says WHEN a season opens, never what will happen in it.
        # The off-season flag lives in the warnings series, not the
        # indicator files, so the table is built once by
        # crops/season_starts.json rather than recomputed per place.
        # ALWAYS a list, never a bare int. Five countries here are
        # genuinely bimodal (Kenya's long and short rains, Somalia's Gu
        # and Der, Cote d'Ivoire, Egypt, Guyana), and emitting an int
        # for the rest made the field's type depend on the data. A
        # consumer testing `v in window` silently drops every bimodal
        # country; one testing `any(x in window for x in v)` keeps them.
        # That alone produced three different counts of the same thing
        # across two chats.
        _raw = SEASON_STARTS.get(name)
        season_starts = ([] if _raw is None
                         else _raw if isinstance(_raw, list) else [_raw])
        # And the scalar a renderer actually wants: the next opening
        # from the dekad being reported, wrapping through the year.
        next_open = None
        if season_starts:
            ahead = sorted(((x - doy) % 36, x) for x in season_starts)
            next_open = ahead[0][1]

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
                # Same binding as the region rows. basis alone is a
                # field a renderer can show the value without; statement
                # cannot be separated from what it describes, so a page
                # missing the basis is missing a field rather than being
                # subtly wrong.
                "statement": _rank_statement(head["rank"], head["of"], latest.year),
            },
            "driver": driver,
            "evidence_basis": "measured",
            # D-076: "attribution pending" comes off crops. It is a
            # work state, not a finding, and it rendered on every
            # untagged row, so it carried no information. Emitted only
            # when one of the two real ENSO strings applies, which for
            # crops is currently never.
            "attribution": None,
            "authorship": "tls_built",
            "publishable": True,
            "instruments": instruments,
            "regions": regions,
            "regions_worst_3": sum(1 for r in regions if r["rank"] <= 3),
            "chance_baseline": empirical,
            "season_opens_dekads": season_starts,
            "next_season_opens_dekad": next_open,
            "qualifiers": quals,
        })

    places.sort(key=lambda p: (p["magnitude"]["value"],
                               -p["magnitude"]["of"]))

    # Aggregate chance baseline over the REPORTED places only.
    #
    # This exists because a figure computed over a wider set than the
    # page shows is not like-for-like, and the error is invisible: the
    # current count is identical either way, because the 45 skipped
    # places contribute no record-worst units this dekad, while the
    # historical years they do contribute inflate the baseline. Design
    # caught it by failing to reproduce 60.1 from the payload and
    # refusing to print a verdict off a number they could not rebuild.
    #
    # Emitting it guarantees the comparison is over the same set as the
    # blocks it frames, and it cannot go stale the way a hard-coded
    # figure would.
    agg = {}
    for pl in places:
        for y, v in pl["chance_baseline"]["series"].items():
            agg[int(y)] = agg.get(int(y), 0) + v
    rec_years = [y for y in range(2014, BASE_LAST + 1)]
    rec_vals = [agg.get(y, 0) for y in rec_years]
    this_year = agg.get(max(agg), 0) if agg else 0
    aggregate = {
        "measures": "regions at their worst on record for this dekad, "
                    "summed across reported places, per year",
        "series": {int(y): int(v) for y, v in sorted(agg.items())},
        "this_year": this_year,
        "recent_mean": round(float(np.mean(rec_vals)), 1) if rec_vals else None,
        "recent_min": int(min(rec_vals)) if rec_vals else None,
        "recent_max": int(max(rec_vals)) if rec_vals else None,
        "recent_years_below_this": int(sum(1 for v in rec_vals
                                           if v < this_year)),
        "recent_years_counted": len(rec_vals),
        "_scope": "reported places only, never the full catalogue. A "
                  "baseline over a wider set than the page shows is not "
                  "like-for-like and the discrepancy is invisible in the "
                  "current year.",
    }
    return {
        "_generated_from": "crops/.cache (no fetch performed)",
        "instrument_legend": {
            slug: {"name": label, "unit": unit,
                   "worse_is": "low" if worse_is > 0 else "high"}
            for slug, label, unit, worse_is in INSTRUMENTS
        },
        "absence_reasons": {
            "no_current_value": "the instrument has history here but no "
                                "value for the dekad being reported, "
                                "usually because it publishes behind the "
                                "others",
            "undefined_at_this_dekad": "the instrument is never defined "
                                       "for this region at this point in "
                                       "the season, which is seasonal "
                                       "rather than late",
            "too_few_comparable_years": "fewer than 20 comparable years "
                                        "at this dekad",
            "not_published_for_country": "ASAP does not publish this "
                                         "indicator for this country",
        },
        "chance_baseline_aggregate": aggregate,
        "dekad": latest_dekad,
        "baseline": f"{BASE_FIRST}-{BASE_LAST}, same dekad of each year",
        # Two forms, because the footer has a length budget and a
        # renderer truncating the long one lands mid-sentence on
        # "The indicator is". Choosing where to cut a methods line is a
        # decision about what a reader must not lose, so it belongs
        # here rather than in a character count.
        "method_short": "FPAR cumulated z-score, ASAP crop mask, "
                        "growing cycle only",
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
        "_generated_from": "crops/.cache/psd (no fetch performed)",
        "_note": "Shares let a condition index be expressed as a supply "
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
