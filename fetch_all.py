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
from fetchers import cpc_strength, oisst_weekly, heat_content, iri, bom, ecmwf_seas5, era5_wwe

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
        "ecmwf_seas5":   safe_fetch("ecmwf_seas5", ecmwf_seas5.fetch),
        "era5_wwe":      safe_fetch("era5_wwe", era5_wwe.fetch),
    }

    out = dict(seeded)  # start from seed

    if results["cpc_strength"].ok and not results["cpc_strength"].used_fallback:
        out["cpc_strength"].update({
            "issued": results["cpc_strength"].issued,
            "table": results["cpc_strength"].payload.get("table", out["cpc_strength"]["table"]),
            "used_fallback": False,
            "fallback_note": None,
            "fetched_at": results["cpc_strength"].fetched_at,
        })

    if results["iri"].ok and not results["iri"].used_fallback:
        out["iri"].update({
            "issued": results["iri"].issued,
            "three_cat": results["iri"].payload.get("three_cat", out["iri"]["three_cat"]),
            "used_fallback": False,
            "fallback_note": None,
            "fetched_at": results["iri"].fetched_at,
        })

    if results["bom"].ok and not results["bom"].used_fallback:
        out["bom"].update({
            "issued": results["bom"].issued,
            "alert_status": results["bom"].payload.get("alert_status", out["bom"]["alert_status"]),
            "summary": results["bom"].payload.get("summary", out["bom"]["summary"]),
            "used_fallback": False,
            "fallback_note": None,
            "fetched_at": results["bom"].fetched_at,
        })

    if results["ecmwf_seas5"].ok and not results["ecmwf_seas5"].used_fallback:
        p = results["ecmwf_seas5"].payload
        out["ecmwf_seas5"].update({
            "issued": results["ecmwf_seas5"].issued,
            "summary": p.get("summary", out["ecmwf_seas5"].get("summary")),
            "members_above": p.get("members_above", {}),
            "member_count": p.get("member_count"),
            "median_anomaly": p.get("median_anomaly"),
            "max_lead_calendar": p.get("max_lead_calendar"),
            "max_lead_month": p.get("max_lead_month"),
            "per_lead": p.get("per_lead", []),
            "used_fallback": False,
            "fallback_note": None,
            "fetched_at": results["ecmwf_seas5"].fetched_at,
        })

    # Physical state is assembled from three weekly fetchers. The OISST
    # fetcher also drives the dynamic RONI-to-traditional-ONI offset.
    phys = out["physical_state"]
    if results["oisst_weekly"].ok and not results["oisst_weekly"].used_fallback:
        p = results["oisst_weekly"].payload
        phys["nino34_weekly_traditional"] = p.get(
            "weekly_traditional", phys["nino34_weekly_traditional"])
        if p.get("weekly_relative") is not None:
            phys["nino34_weekly_roni"] = p.get("weekly_relative")
        phys["issued"] = results["oisst_weekly"].issued or phys["issued"]
        phys["used_fallback"] = False
        phys["fallback_note"] = None
        if p.get("roni_to_oni_offset") is not None:
            out["roni_to_oni_offset"] = {
                "value": p["roni_to_oni_offset"],
                "issued": results["oisst_weekly"].issued,
                "used_fallback": False,
                "fallback_note": None,
                "fetched_at": results["oisst_weekly"].fetched_at,
                "weekly_traditional": p.get("weekly_traditional"),
                "weekly_relative": p.get("weekly_relative"),
            }
    if results["heat_content"].ok and not results["heat_content"].used_fallback:
        phys["heat_content_0_300m_estimate"] = results["heat_content"].payload.get(
            "anomaly_c", phys["heat_content_0_300m_estimate"])
    if results["era5_wwe"].ok and not results["era5_wwe"].used_fallback:
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
