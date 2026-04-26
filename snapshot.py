"""
Snapshot and diff inputs across weekly issues.

Each issue's `sources.py` state is serialized to snapshots/YYYY-MM-DD.json
when run_brief.py runs. The next issue's run loads the most recent prior
snapshot and computes deltas, which feed into the editorial layer's
"what changed week-over-week" subsection.

Why JSON snapshots rather than just diffing sources.py via git: snapshots
are decoupled from your editing history. You can re-run the pipeline
against any prior issue's inputs without checking out an old commit, and
you can rewrite sources.py freely without losing comparability.

Methodology version is included in every snapshot. If the version changes
between two snapshots, diffs are still shown but flagged as
"non-comparable: methodology version bumped".
"""

import json
from datetime import date
from pathlib import Path

import sources as S

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


# ---- JSON serialization helpers ------------------------------------

def _to_jsonable(obj):
    """Recursively convert dates and tuples to JSON-friendly types."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


def current_snapshot(fetched: dict) -> dict:
    """Capture the current state of inputs as a flat dict.

    `fetched` is the live (or seed-fallback) dict produced by
    fetch_all.fetch_all() with `_freshness` already popped off. It owns
    the per-source fields; sources.py only owns methodology constants
    and target-season identifiers.

    The snapshot key shape is preserved as `cpc_strength`, `iri`, `bom`,
    `ecmwf`, `physical_state` so the existing diff() keeps working. We
    map fetched["ecmwf_seas5"] onto the legacy "ecmwf" key.
    """
    offset_block = fetched.get("roni_to_oni_offset", {})
    offset_value = offset_block.get("value", S.RONI_TO_ONI_OFFSET)
    return _to_jsonable({
        "brief_date": S.BRIEF_DATE,
        "methodology_version": S.METHODOLOGY_VERSION,
        "roni_to_oni_offset": offset_value,
        "roni_to_oni_offset_block": offset_block,
        "target_season": S.TARGET_SEASON,
        "nearest_cpc_season": S.NEAREST_CPC_SEASON,
        "cpc_strength": fetched["cpc_strength"],
        "iri": fetched["iri"],
        "ecmwf": fetched["ecmwf_seas5"],
        "bom": fetched["bom"],
        "physical_state": fetched["physical_state"],
    })


def save_snapshot(snap: dict) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{snap['brief_date']}.json"
    out.write_text(json.dumps(snap, indent=2, sort_keys=True))
    return out


def load_prior_snapshot(before: date):
    """Most recent snapshot strictly before `before`, or None."""
    if not SNAPSHOT_DIR.exists():
        return None
    candidates = []
    for p in SNAPSHOT_DIR.glob("*.json"):
        try:
            d = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if d < before:
            candidates.append((d, p))
    if not candidates:
        return None
    candidates.sort()
    latest = candidates[-1][1]
    return json.loads(latest.read_text())


# ---- Diff logic ----------------------------------------------------

def _safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def diff(prev: dict, curr: dict) -> dict:
    """
    Produce a structured diff focused on the things that matter for the
    editorial layer. Per source: did the issuance date change, and if so,
    what numerical fields shifted.
    """
    out = {
        "is_first_issue": prev is None,
        "methodology_changed": False,
        "offset_changed": False,
        "source_changes": [],   # list of dicts, one per source
        "physical_state_deltas": {},
    }
    if prev is None:
        return out

    if _safe_get(prev, "methodology_version") != _safe_get(curr, "methodology_version"):
        out["methodology_changed"] = True
        out["methodology_prev"] = prev.get("methodology_version")
        out["methodology_curr"] = curr.get("methodology_version")

    if _safe_get(prev, "roni_to_oni_offset") != _safe_get(curr, "roni_to_oni_offset"):
        out["offset_changed"] = True
        out["offset_prev"] = prev.get("roni_to_oni_offset")
        out["offset_curr"] = curr.get("roni_to_oni_offset")

    # Per-source issuance + summary
    for src in ["cpc_strength", "iri", "ecmwf", "bom"]:
        prev_issued = _safe_get(prev, src, "issued")
        curr_issued = _safe_get(curr, src, "issued")
        new_release = (prev_issued != curr_issued)
        entry = {
            "source": src,
            "prev_issued": prev_issued,
            "curr_issued": curr_issued,
            "new_release": new_release,
            "changes": [],
        }
        if new_release:
            # For CPC, surface the NDJ peak season delta in concrete numbers
            if src == "cpc_strength":
                p_table = _safe_get(prev, "cpc_strength", "table", "NDJ 2026-27", default={})
                c_table = _safe_get(curr, "cpc_strength", "table", "NDJ 2026-27", default={})
                for bin_label in c_table:
                    pv = p_table.get(bin_label, 0)
                    cv = c_table.get(bin_label, 0)
                    if pv != cv:
                        entry["changes"].append(
                            f"NDJ {bin_label}: {pv}% -> {cv}% (Delta {cv - pv:+d})"
                        )
            elif src == "iri":
                p_djf = _safe_get(prev, "iri", "three_cat", "DJF 2026-27")
                c_djf = _safe_get(curr, "iri", "three_cat", "DJF 2026-27")
                if p_djf and c_djf and p_djf != c_djf:
                    entry["changes"].append(
                        f"DJF (LN, N, EN): {tuple(p_djf)} -> {tuple(c_djf)}"
                    )
        out["source_changes"].append(entry)

    # Physical state numerical deltas
    p_phys = _safe_get(prev, "physical_state", default={})
    c_phys = _safe_get(curr, "physical_state", default={})
    for key in ["nino34_weekly_traditional", "nino34_weekly_roni",
                "heat_content_0_300m_estimate", "wwe_count_since_mar1_estimate"]:
        pv = p_phys.get(key)
        cv = c_phys.get(key)
        if pv is None or cv is None:
            continue
        if pv != cv:
            out["physical_state_deltas"][key] = {"prev": pv, "curr": cv,
                                                 "delta": round(cv - pv, 2)}
    return out


# ---- Markdown rendering of the diff -------------------------------

def render_diff_markdown(d: dict) -> str:
    """Render the diff section as markdown, ready to embed in the brief."""
    if d["is_first_issue"]:
        return ("This is the first issue under V1. No prior snapshot to "
                "diff against; future briefs will surface week-over-week "
                "deltas mechanically.")

    lines = []
    if d["methodology_changed"]:
        lines.append(
            f"**Methodology version bumped: {d['methodology_prev']} -> "
            f"{d['methodology_curr']}.** Headline buckets are not strictly "
            "comparable to last issue. See methodology change log."
        )
        lines.append("")
    if d["offset_changed"]:
        lines.append(
            f"**RONI->trad ONI offset changed: +{d['offset_prev']}°C -> "
            f"+{d['offset_curr']}°C.** This shifts headline buckets even "
            "without underlying probability changes; flag in editorial."
        )
        lines.append("")

    new_releases = [s for s in d["source_changes"] if s["new_release"]]
    no_change = [s for s in d["source_changes"] if not s["new_release"]]

    if new_releases:
        lines.append("**New agency releases since last issue:**")
        lines.append("")
        for s in new_releases:
            lines.append(f"- **{s['source']}**: prior issued {s['prev_issued']}, "
                         f"now issued {s['curr_issued']}.")
            for c in s["changes"]:
                lines.append(f"    - {c}")
        lines.append("")

    if no_change:
        unchanged_list = ", ".join(s["source"] for s in no_change)
        lines.append(f"**Unchanged since last issue:** {unchanged_list}.")
        lines.append("")

    if d["physical_state_deltas"]:
        lines.append("**Physical state deltas:**")
        lines.append("")
        for k, v in d["physical_state_deltas"].items():
            lines.append(f"- {k}: {v['prev']} -> {v['curr']} "
                         f"(delta {v['delta']:+})")
        lines.append("")
    else:
        lines.append("**Physical state:** no numerical changes from last "
                     "issue. (Either truly unchanged or weekly update has "
                     "not been ingested.)")
        lines.append("")

    return "\n".join(lines).strip()


if __name__ == "__main__":
    import fetch_all as F
    fetched = F.fetch_all()
    fetched.pop("_freshness", None)
    snap = current_snapshot(fetched)
    prev = load_prior_snapshot(before=date.fromisoformat(snap["brief_date"]))
    d = diff(prev, snap)
    print(render_diff_markdown(d))
