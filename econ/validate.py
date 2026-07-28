"""Validate ECON's emitted JSON before it reaches design.

Run: .venv/bin/python econ/validate.py

Every check here exists because breaking it would put a wrong or
misleading money figure on the site. The rules come from
research/handover_econ.md, research/econ_source_report.md and D-039.

Exit 0 clean, 1 on any error. Warnings do not fail the run but are
printed, because an incomplete entry is fine as long as nobody
publishes it by accident.
"""

import json
import pathlib
import sys

DATA = pathlib.Path(__file__).parent / "data"

# The seven categories that must never be summed together. From the
# source report, section 3. Adding any two of these produces a number
# that measures nothing.
CATEGORIES = {
    "insured_loss",
    "economic_direct",
    "economic_total",
    "output_loss",
    "humanitarian_appeal",
    "mortality",
    "mortality_valued",
}

EVIDENCE_BASIS = {"measured", "compiled", "combined"}
AUTHORSHIP = {"agency", "tls_built"}
BASIS = {"published_schedule", "observed_practice", "conditional"}

# Estimators that publish no methodology. A figure from one of these
# may never appear alone: the reader has no way to check what is
# inside it, so it only makes sense beside something documented.
UNDOCUMENTED = {"accuweather"}

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(name):
    path = DATA / name
    if not path.exists():
        err(f"{name}: missing")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        err(f"{name}: invalid JSON, {exc}")
        return None


def check_no_em_dash(name, raw):
    # Written as an escape so this file is not itself an em-dash hit.
    # CLAUDE.md invariant 6 says the allowlist must not grow.
    if "\u2014" in raw:
        err(f"{name}: contains an em-dash (CLAUDE.md invariant 6)")


def check_estimators(doc):
    if doc.get("authorship") not in AUTHORSHIP:
        err("estimators: authorship missing or not in the D-021 enum")
    if doc.get("evidence_basis") not in EVIDENCE_BASIS:
        err("estimators: evidence_basis missing or not in the D-033 enum")

    for eid, e in doc.get("estimators", {}).items():
        where = f"estimators.{eid}"

        for field in ("full_name", "organisation_type", "citation_string",
                      "licence_note", "categories_published", "revision_cadence"):
            if not e.get(field):
                err(f"{where}: missing {field}")

        for cat in e.get("categories_published", []):
            if cat not in CATEGORIES:
                err(f"{where}: unknown category {cat!r}")

        prov = e.get("provenance")
        if not prov:
            err(f"{where}: missing provenance")
            continue
        # fetched_at distinct from issued is the whole vintage mechanic.
        if not prov.get("fetched_at"):
            err(f"{where}: provenance.fetched_at is required")
        if not prov.get("source_url"):
            err(f"{where}: provenance.source_url is required")
        if "fallback" not in prov:
            err(f"{where}: provenance.fallback flag is required")
        if prov.get("verification_note"):
            warn(f"{where}: carries a verification note, not publishable as-is")

        if eid in UNDOCUMENTED and not e.get("caution"):
            err(f"{where}: undocumented estimator must carry a caution field")


def check_figure(where, fig, estimators):
    """A figure is a value that will be rendered as money. Every one of
    these checks maps to a way a reader could be misled."""
    has_value = any(k in fig for k in ("value", "value_low", "value_high"))
    if not has_value:
        err(f"{where}: no value")
        return

    # T11 units rule, and the reason it is a hard field: our own
    # handover carried GBP 1.15 bn as "roughly GBP 1.5B" because the
    # coverage headlined the USD conversion.
    if not fig.get("currency"):
        err(f"{where}: currency is required and is never inferred")
    if not fig.get("scale"):
        err(f"{where}: scale is required (million / billion)")
    if not fig.get("issued"):
        err(f"{where}: issued date is required")

    cat = fig.get("category")
    if cat is not None and cat not in CATEGORIES:
        err(f"{where}: unknown category {cat!r}")

    eid = fig.get("estimator_id")
    if eid is None:
        if not fig.get("estimator_note"):
            err(f"{where}: estimator_id is null and no estimator_note explains who said it")
    elif eid not in estimators:
        err(f"{where}: estimator_id {eid!r} not in the registry")


def check_latency(doc, estimators):
    if doc.get("evidence_basis") not in EVIDENCE_BASIS:
        err("latency_map: evidence_basis missing or not in the D-033 enum")

    for entry in doc.get("entries", []):
        where = f"latency_map.{entry.get('entry_id', '?')}"

        if not entry.get("label"):
            err(f"{where}: missing label")

        for step in entry.get("sequence", []):
            eid = step.get("estimator_id")
            if eid is not None and eid not in estimators:
                err(f"{where}: sequence references unknown estimator {eid!r}")
            if eid is None and not step.get("note"):
                err(f"{where}: unprofiled estimator in sequence needs a note")
            if step.get("basis") not in BASIS:
                err(f"{where}: sequence step basis {step.get('basis')!r} not in enum")
            cat = step.get("category")
            if cat not in CATEGORIES:
                err(f"{where}: sequence step category {cat!r} not in enum")

        # 'settles' is our inference from the schedules, not anyone's
        # published claim. D-033 requires that to be visible.
        settles = entry.get("settles")
        if settles is not None and settles.get("derived") is not True:
            err(f"{where}: settles is derived and must be flagged derived:true (D-033 Combined)")

        example = entry.get("worked_example")
        if example:
            figs = example.get("figures", [])
            for i, fig in enumerate(figs):
                check_figure(f"{where}.worked_example[{i}]", fig, estimators)

            cited = {f.get("estimator_id") for f in figs}
            if cited & UNDOCUMENTED:
                documented = cited - UNDOCUMENTED - {None}
                if not documented:
                    err(f"{where}: cites an undocumented estimator with no documented "
                        f"estimator alongside it")

        status = entry.get("verification_status")
        if status in ("blocked", "partial"):
            warn(f"{where}: verification_status={status}, not publishable yet")


def main():
    raw_est = (DATA / "estimators.json")
    raw_lat = (DATA / "latency_map.json")
    for p in (raw_est, raw_lat):
        if p.exists():
            check_no_em_dash(p.name, p.read_text())

    estimators_doc = load("estimators.json")
    latency_doc = load("latency_map.json")

    if estimators_doc:
        check_estimators(estimators_doc)
    if latency_doc and estimators_doc:
        check_latency(latency_doc, estimators_doc.get("estimators", {}))

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). Not fit to emit.")
        return 1
    print(f"\nOK. {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
