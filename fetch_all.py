"""
Orchestrate all fetchers. Returns a dict in the same shape sources.py
exposes, so run_brief.py works whether inputs are hand-curated or
auto-fetched.

Behavior:
  - Each fetcher runs through safe_fetch (catches exceptions, returns
    last-good cache on failure).
  - For unimplemented fetchers (return ok=False with no cache), we
    seed from sources.py so the pipeline never breaks.
  - The brief surfaces "stale" status per source in the editorial layer
    so the analyst knows what's auto-fetched vs fallback.
"""

from __future__ import annotations
from datetime import date
from typing import Any

from fetchers._common import safe_fetch, FetchResult, now_iso
from fetchers import (
    cpc_strength, oisst_weekly, heat_content, iri, bom,
    ecmwf_seas5, era5_wwe, era5_burst, oni_history, nmme,
)

import sources as S   # used as seed/fallback


def _seed_from_sources() -> dict:
    """Returns the same shape as the live fetched dict, using sources.py."""
    return {
        "roni_to_oni_offset": {
            "value": S.RONI_TO_ONI_OFFSET,
            "issued": S.PHYSICAL_STATE["issued"].isoformat(),
            "used_fallback": True,
            "fallback_note": "seeded from sources.RONI_TO_ONI_OFFSET",
            "fetched_at": now_iso(),
            "weekly_traditional": None,
            "weekly_relative": None,
        },
        "cpc_strength": {
            "ok": True, "issued": S.CPC_STRENGTH["issued"].isoformat(),
            "table": S.CPC_STRENGTH["table"],
            "fetched_at": now_iso(), "used_fallback": True,
            "fallback_note": "seeded from sources.py (no fetcher result)",
        },
        "iri": {
            "ok": True, "issued": S.IRI["issued"].isoformat(),
            "three_cat": S.IRI["three_cat"],
            "fetched_at": now_iso(), "used_fallback": True,
            "fallback_note": "seeded from sources.py",
        },
        "ecmwf_seas5": {
            "ok": True, "issued": S.ECMWF["issued"].isoformat(),
            "summary": S.ECMWF["summary"],
            "approx_p_above_2.5_oct": S.ECMWF["approx_p_above_2.5_oct"],
            "fetched_at": now_iso(), "used_fallback": True,
            "fallback_note": "seeded from sources.py (qualitative only)",
        },
        "bom": {
            "ok": True, "issued": S.BOM["issued"].isoformat(),
            "alert_status": S.BOM["alert_status"],
            "summary": S.BOM["summary"],
            "fetched_at": now_iso(), "used_fallback": True,
            "fallback_note": "seeded from sources.py",
        },
        "physical_state": {
            "ok": True, "issued": S.PHYSICAL_STATE["issued"].isoformat(),
            "nino34_weekly_traditional": S.PHYSICAL_STATE["nino34_weekly_traditional"],
            "nino34_weekly_roni": S.PHYSICAL_STATE["nino34_weekly_roni"],
            "heat_content_0_300m_estimate": S.PHYSICAL_STATE["heat_content_0_300m_estimate"],
            "wwe_count_since_mar1_estimate": S.PHYSICAL_STATE["wwe_count_since_mar1_estimate"],
            "heat_content_qualitative": S.PHYSICAL_STATE["heat_content_qualitative"],
            "wwe_qualitative": S.PHYSICAL_STATE["wwe_qualitative"],
            "fetched_at": now_iso(), "used_fallback": True,
            "fallback_note": "seeded from sources.py",
        },
    }


def fetch_all() -> dict:
    """
    Run all fetchers, merge with seed fallback. Returns a sources-shaped
    dict plus per-source freshness metadata for the editorial layer.
    """
    seeded = _seed_from_sources()

    # Each fetcher result either fills/overwrites a seeded slot or leaves it.
    results = {
        "cpc_strength":  safe_fetch("cpc_strength", cpc_strength.fetch),
        "oisst_weekly":  safe_fetch("oisst_weekly", oisst_weekly.fetch),
        "heat_content":  safe_fetch("heat_content", heat_content.fetch),
        "iri":           safe_fetch("iri", iri.fetch),
        "bom":           safe_fetch("bom", bom.fetch),
        # CDS-backed fetchers get a 25-minute budget each. CDS queue waits
        # during busy periods can otherwise hang the workflow indefinitely;
        # on timeout, safe_fetch falls back to the last-good cache so the
        # brief still renders and commits.
        # 40-min budget: CDS queue waits run 20-60 min on busy days, so the
        # earlier 25-min budget timed out too often. A timeout is now
        # harmless (the merge above reuses the cached per_lead seamlessly),
        # but the larger budget reduces how often we fall back to a stale
        # SEAS5 run.
        "ecmwf_seas5":   safe_fetch("ecmwf_seas5", ecmwf_seas5.fetch,
                                    timeout_seconds=40 * 60),
        "era5_wwe":      safe_fetch("era5_wwe", era5_wwe.fetch,
                                    timeout_seconds=25 * 60),
        "era5_burst":    safe_fetch("era5_burst", era5_burst.fetch,
                                    timeout_seconds=30 * 60),
        "oni_history":   safe_fetch("oni_history", oni_history.fetch),
        # NMME multi-model consensus. Cold cache pulls ~200MB across 5
        # models over the CPC FTP; warm cache (same monthly init) is
        # seconds. 15-minute budget covers a cold pull with margin.
        "nmme":          safe_fetch("nmme", nmme.fetch,
                                    timeout_seconds=15 * 60),
    }

    out = dict(seeded)  # start from seed

    # All merges below use the fetched payload whenever ok, including a
    # last-good cache fallback: the cache is a full prior live payload and
    # is strictly better than the sources.py seed. _fallback_note() reports
    # which path ran so the freshness panel stays accurate.
    def _fallback_note(r):
        return (None if not r.used_fallback else
                f"live fetch failed; using last-good cache (issued {r.issued})")

    if results["cpc_strength"].ok:
        r = results["cpc_strength"]
        out["cpc_strength"].update({
            "issued": r.issued,
            "table": r.payload.get("table", out["cpc_strength"]["table"]),
            "used_fallback": r.used_fallback,
            "fallback_note": _fallback_note(r),
            "fetched_at": r.fetched_at,
        })

    if results["iri"].ok:
        r = results["iri"]
        out["iri"].update({
            "issued": r.issued,
            "three_cat": r.payload.get("three_cat", out["iri"]["three_cat"]),
            "used_fallback": r.used_fallback,
            "fallback_note": _fallback_note(r),
            "fetched_at": r.fetched_at,
        })

    if results["bom"].ok:
        r = results["bom"]
        out["bom"].update({
            "issued": r.issued,
            "alert_status": r.payload.get("alert_status", out["bom"]["alert_status"]),
            "summary": r.payload.get("summary", out["bom"]["summary"]),
            "used_fallback": r.used_fallback,
            "fallback_note": _fallback_note(r),
            "fetched_at": r.fetched_at,
        })

    # Use the fetched payload whenever the fetcher returned ok, INCLUDING a
    # last-good cache fallback (used_fallback=True). The cache holds a full
    # prior live payload (per_lead, member counts), which is strictly better
    # than the sources.py seed (qualitative only, no per_lead). The previous
    # `not used_fallback` guard discarded the cache on a timeout and left the
    # seed in place, which dropped per_lead and broke both the analog
    # forecast fan and the consensus headline's SEAS5 member counts.
    if results["ecmwf_seas5"].ok:
        r = results["ecmwf_seas5"]
        p = r.payload
        out["ecmwf_seas5"].update({
            "issued": r.issued,
            "summary": p.get("summary", out["ecmwf_seas5"].get("summary")),
            "members_above": p.get("members_above", {}),
            "member_count": p.get("member_count"),
            "median_anomaly": p.get("median_anomaly"),
            "max_lead_calendar": p.get("max_lead_calendar"),
            "max_lead_month": p.get("max_lead_month"),
            "per_lead": p.get("per_lead", []),
            "used_fallback": r.used_fallback,
            "fallback_note": (None if not r.used_fallback else
                              f"live fetch failed; using last-good cache "
                              f"(issued {r.issued})"),
            "fetched_at": r.fetched_at,
        })

    # Physical state is assembled from three weekly fetchers. The OISST
    # fetcher also drives the dynamic RONI-to-traditional-ONI offset.
    phys = out["physical_state"]
    if results["oisst_weekly"].ok:
        r = results["oisst_weekly"]
        p = r.payload
        phys["nino34_weekly_traditional"] = p.get(
            "weekly_traditional", phys["nino34_weekly_traditional"])
        if p.get("weekly_relative") is not None:
            phys["nino34_weekly_roni"] = p.get("weekly_relative")
        phys["issued"] = r.issued or phys["issued"]
        phys["used_fallback"] = r.used_fallback
        phys["fallback_note"] = (None if not r.used_fallback else
                                 f"live fetch failed; using last-good cache "
                                 f"(issued {r.issued})")
        if p.get("roni_to_oni_offset") is not None:
            out["roni_to_oni_offset"] = {
                "value": p["roni_to_oni_offset"],
                "issued": r.issued,
                "used_fallback": r.used_fallback,
                "fallback_note": (None if not r.used_fallback else
                                  "live fetch failed; using last-good cache"),
                "fetched_at": r.fetched_at,
                "weekly_traditional": p.get("weekly_traditional"),
                "weekly_relative": p.get("weekly_relative"),
            }
    if results["heat_content"].ok:
        phys["heat_content_0_300m_estimate"] = results["heat_content"].payload.get(
            "anomaly_c", phys["heat_content_0_300m_estimate"])
    if results["era5_wwe"].ok:
        wp = results["era5_wwe"].payload
        # CWWA replaces the legacy event-count metric (methodology v1.2).
        if wp.get("cwwa_ms_days") is not None:
            phys["cwwa_ms_days"] = wp["cwwa_ms_days"]
            phys["cwwa_series"] = wp.get("cwwa_series", [])
            phys["cwwa_analogs"] = wp.get("cwwa_analogs", {})
            phys["cwwa_domain"] = wp.get("domain")
        elif wp.get("wwe_count_since_mar1") is not None:
            # Legacy payload from old caches.
            phys["wwe_count_since_mar1_estimate"] = wp["wwe_count_since_mar1"]

    # Spatial-peak WWB detection (methodology v1.6, complement to CWWA).
    if results["era5_burst"].ok:
        bp = results["era5_burst"].payload
        phys["wwb_events_since_mar1"] = bp.get("events_since_mar1")
        phys["wwb_events_detail"] = bp.get("events_detail", [])
        phys["wwb_analogs"] = bp.get("analogs", {})
        phys["wwb_domain"] = bp.get("domain")

    # ONI history is consumed only by analog.py to keep current-year ONI
    # rows up to date with CPC's latest publication.
    if results["oni_history"].ok:
        r = results["oni_history"]
        out["oni_history"] = {
            "ok": True,
            "issued": r.issued,
            "by_year": r.payload.get("by_year", {}),
            "latest_year": r.payload.get("latest_year"),
            "latest_season": r.payload.get("latest_season"),
            "used_fallback": r.used_fallback,
            "fallback_note": _fallback_note(r),
            "fetched_at": r.fetched_at,
        }
    else:
        out["oni_history"] = {
            "ok": False, "used_fallback": True,
            "by_year": {}, "issued": None,
            "latest_year": None, "latest_season": None,
            "fallback_note": "oni_history fetch failed; chart uses CSV defaults",
            "fetched_at": now_iso(),
        }

    # NMME multi-model consensus: feeds both the section-2b panel and the
    # v1.8 consensus headline. Use the payload on a cache fallback too (the
    # cache holds the full prior payload, cfsv2_trajectory included), so a
    # timeout keeps the consensus and the chart's CFSv2 extension alive.
    if results["nmme"].ok:
        r = results["nmme"]
        np_ = r.payload
        out["nmme"] = {
            "ok": True,
            "issued": r.issued,
            "init": np_.get("init"),
            "models": np_.get("models", {}),
            "cfsv2_trajectory": np_.get("cfsv2_trajectory"),
            "ensemble_mean_peak": np_.get("ensemble_mean_peak"),
            "ensemble_frac_above": np_.get("ensemble_frac_above", {}),
            "thresholds_degC": np_.get("thresholds_degC", []),
            "peak_window": np_.get("peak_window"),
            "nino34_region": np_.get("nino34_region"),
            "n_models_ok": np_.get("n_models_ok"),
            "n_models_attempted": np_.get("n_models_attempted"),
            "used_fallback": r.used_fallback,
            "fallback_note": (None if not r.used_fallback else
                              f"live fetch failed; using last-good cache "
                              f"(issued {r.issued})"),
            "fetched_at": r.fetched_at,
        }
    else:
        out["nmme"] = {
            "ok": False, "used_fallback": True,
            "models": {}, "issued": None,
            "ensemble_mean_peak": None, "ensemble_frac_above": {},
            "fallback_note": "nmme fetch failed or unavailable; "
                             "model-consensus panel omitted this issue",
            "fetched_at": now_iso(),
        }

    # Per-source freshness summary for the brief
    out["_freshness"] = {
        name: {
            "ok": r.ok, "used_fallback": r.used_fallback,
            "error": r.error, "issued": r.issued, "fetched_at": r.fetched_at,
        }
        for name, r in results.items()
    }
    return out


if __name__ == "__main__":
    import json
    data = fetch_all()
    print(json.dumps(data["_freshness"], indent=2, default=str))
