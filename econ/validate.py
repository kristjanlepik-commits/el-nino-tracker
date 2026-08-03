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
import re
import sys

DATA = pathlib.Path(__file__).parent / "data"

# The categories that must never be summed together. Started at seven
# (source report, section 3) and grew to nine on 2026-07-29. Adding
# any two of these produces a number that measures nothing.
CATEGORIES = {
    "insured_loss",
    "economic_direct",
    "economic_total",
    "output_loss",
    # response_cost was added 2026-07-29, discovered by building the Spain
    # payload: a firefighting bill is not insured loss, not damage to an
    # asset, not foregone output and not an appeal. It is money spent
    # responding. The original seven could not hold it, and on that event
    # it is the largest figure anyone has published.
    "response_cost",
    "humanitarian_appeal",
    # funding_granted likewise: an EUSF award is money disbursed, which is
    # neither a loss nor a request. Kept apart from both.
    "funding_granted",
    "mortality",
    "mortality_valued",
}

# Categories that are NOT losses. Money moving toward a disaster, rather
# than value destroyed by it. Rendering these beside loss figures without
# the distinction is the single easiest way to inflate an event.
NON_LOSS_CATEGORIES = {"humanitarian_appeal", "funding_granted", "response_cost"}

EVIDENCE_BASIS = {"measured", "compiled", "combined"}
AUTHORSHIP = {"agency", "tls_built"}
BASIS = {"published_schedule", "observed_practice", "conditional"}
ABSENCE_REASONS = {"below_threshold", "outside_coverage", "not_yet_valid",
                   "upstream_not_selected"}

# Estimators that publish no methodology. A figure from one of these
# may never appear alone: the reader has no way to check what is
# inside it, so it only makes sense beside something documented.
UNDOCUMENTED = {"accuweather"}

# How a death toll was arrived at. Excess deaths are a modelled
# statistical estimate, not counted bodies, and the two are not
# interchangeable at any reading level: a reader hearing "100,300
# deaths" pictures a body count. Editor's rule, 2026-07-29, and the
# same preserve-the-kind principle as the insured tense.
DEATH_TOLL_KINDS = {"counted", "excess_estimated", "modelled"}

# Any key starting with an underscore is pipeline guidance: renderers
# never print it. The rule cannot reach INSIDE a string, so a field
# doing two jobs at once is invisible to it. Design hit exactly that on
# the Spain payload, where a scope field held reader copy and a renderer
# directive in one sentence pair, and "Must never render as a Spain
# figure" printed at the reader. This pattern catches the shape.
DIRECTIVE_LANGUAGE = re.compile(
    r"\b(must never|must not|never render|do not render|should not|"
    r"do not publish|never publish|not publishable|never be compared)\b",
    re.IGNORECASE)


# Internal references that mean nothing to a reader. A decision number
# or thesis number in reader copy is a leak even though it is not an
# instruction, so neither the underscore rule nor the directive pattern
# catches it. Found on 2026-07-29 in design's built latency map, which
# printed "T4's worked example of the fast-reaction thesis" and a note
# about an earlier version of the entry being wrong. Both came from an
# unprefixed ECON field.
INTERNAL_REFS = re.compile(
    r"(\bD-\d{3}\b|\bT\d{1,2}\b|\bthe [a-z-]+ thesis\b|"
    r"\ban earlier version\b|\bwas corrected on\b|\bTLS\b)")


def check_reader_fields(name, doc):
    """Reader-facing fields must not contain instructions to the renderer.

    A field holding both is the defect: no prefix rule can split a
    string, so the split has to happen in the payload.
    """
    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            key = path.rsplit(".", 1)[-1].split("[")[0]
            if key.startswith("_"):
                return
            hit = DIRECTIVE_LANGUAGE.search(node)
            if hit:
                err(f"{name}{path}: reader-facing field contains a renderer "
                    f"directive ({hit.group(0)!r}). Split it: reader copy stays, "
                    f"the instruction moves to an underscore-prefixed key")
            ref = INTERNAL_REFS.search(node)
            if ref:
                err(f"{name}{path}: reader-facing field contains an internal "
                    f"reference ({ref.group(0)!r}) that means nothing to a "
                    f"reader. Move it to an underscore-prefixed key")
    walk(doc)

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


# Human-readable heading for each enum value, as it appears in the
# methodology page's category table.
CATEGORY_LABELS = {
    "insured_loss": "Insured loss",
    "economic_direct": "Direct economic",
    "economic_total": "Total economic",
    "output_loss": "Output loss",
    "response_cost": "Response cost",
    "humanitarian_appeal": "Humanitarian appeal",
    "funding_granted": "Funding granted",
    "mortality": "Mortality",
    "mortality_valued": "Monetised mortality",
}

NUMBER_WORDS = {7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven"}


def check_methodology_matches_enum():
    """The methodology page describes the categories; validate.py enforces
    them. They drifted apart once, on 2026-07-29, when a string replace
    failed silently and left the page claiming seven while the enum held
    nine. The page's own change log was correct and the page was not,
    which is the exact defect this channel exists to catch elsewhere."""
    page = pathlib.Path(__file__).parent / "methodology.md"
    if not page.exists():
        err("methodology.md: missing")
        return
    text = page.read_text()

    for cat, label in CATEGORY_LABELS.items():
        if f"| {label} |" not in text:
            err(f"methodology.md: category {cat!r} is in the enum but its row "
                f"({label!r}) is not in the page's table")

    for cat in CATEGORY_LABELS:
        if cat not in CATEGORIES:
            err(f"CATEGORY_LABELS has {cat!r}, which is not in CATEGORIES")
    for cat in CATEGORIES:
        if cat not in CATEGORY_LABELS:
            err(f"CATEGORIES has {cat!r} with no label for the methodology page")

    # The page's headline promise and its derived-figure section have to
    # agree. They contradicted each other for one commit on 2026-08-03,
    # when D-070 permitted a TLS-computed figure and the top of the page
    # still said we produce none.
    if "tls_built" in AUTHORSHIP:
        if "## The one number that is ours" not in text:
            err("methodology.md: a TLS-built figure is permitted but the page has "
                "no section explaining it")
        if "We do not produce loss estimates" in text:
            err("methodology.md: the page still claims we produce no estimates, "
                "which contradicts the derived-figure section")

    word = NUMBER_WORDS.get(len(CATEGORIES))
    if word and f"The {word} categories" not in text:
        err(f"methodology.md: enum holds {len(CATEGORIES)} categories, so the "
            f"page should say 'The {word} categories'")


def check_estimators(doc):
    if doc.get("authorship") not in AUTHORSHIP:
        err("estimators: authorship missing or not in the D-021 enum")
    if doc.get("evidence_basis") not in EVIDENCE_BASIS:
        err("estimators: evidence_basis missing or not in the D-033 enum")

    for eid, e in doc.get("estimators", {}).items():
        where = f"estimators.{eid}"

        for field in ("full_name", "organisation_type", "citation_string",
                      "categories_published", "revision_cadence"):
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
        if prov.get("_verification_note"):
            warn(f"{where}: carries a verification note, not publishable as-is")

        if not (e.get("licence_note") or e.get("_licence_note")):
            err(f"{where}: missing licence_note")

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

    # A monetised-mortality figure is a PRICE PUT ON a death toll, not
    # an independent finding about the same event. Indonesia 2015 is
    # the case: the ~100,300 excess deaths (Koplitz et al. 2016) are
    # the same mortality Kiely et al. monetise as USD 7.3 bn. Rendered
    # side by side without the link they read as two sources agreeing,
    # which is the opposite of the truth. Caught by the aftereffects
    # chat, 2026-07-28.
    if cat == "mortality_valued" and not fig.get("monetises"):
        err(f"{where}: mortality_valued requires a 'monetises' field naming the "
            f"death-toll source it prices, or it will read as independent corroboration")

    # A monetised death toll rests on a value-of-a-statistical-life
    # figure that varies enormously by method and by country. The price
    # is somebody's choice and the payload has to name whose.
    if cat == "mortality_valued" and not fig.get("vsl_note"):
        err(f"{where}: mortality_valued requires a 'vsl_note' naming the "
            f"value-of-statistical-life basis; the price is a choice, not a fact")

    if cat == "mortality" and fig.get("death_toll_kind") not in DEATH_TOLL_KINDS:
        err(f"{where}: mortality requires death_toll_kind in {sorted(DEATH_TOLL_KINDS)}; "
            f"excess deaths are modelled estimates and must never render as counted bodies")

    # Editor's carve-out to the never-sum rule: a source's own total may
    # include monetised mortality, and we may quote it, but only when the
    # source did the including and named its VSL. Otherwise the largest
    # and most method-dependent number on the page silently inflates a
    # total.
    if fig.get("includes_mortality_valuation") and not fig.get("vsl_note"):
        err(f"{where}: a total including monetised mortality must name the "
            f"source's VSL basis, or it is a silent inflation")


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

            # Same double-count trap at the group level: a death toll
            # and a monetised death toll in one view must be linked.
            cats = [f.get("category") for f in figs]
            if "mortality" in cats and "mortality_valued" in cats:
                linked = any(f.get("monetises") for f in figs
                             if f.get("category") == "mortality_valued")
                if not linked:
                    err(f"{where}: shows mortality and mortality_valued together "
                        f"without a link; they are one fact, not two")

        # A missing figure must never render as a small figure. The
        # three absences read identically on a page and mean opposite
        # things: below a published threshold (weak evidence it was
        # small), outside anyone's coverage (says nothing at all), and
        # present but not yet valid (a crops reading before its
        # earliest publishable dekad can be confidently wrong).
        absence = entry.get("absence_meaning")
        if not absence:
            err(f"{where}: missing absence_meaning; silence must be explained")
        elif absence.get("reason") not in ABSENCE_REASONS:
            err(f"{where}: absence_meaning.reason {absence.get('reason')!r} not in enum")
        elif not absence.get("note"):
            err(f"{where}: absence_meaning needs a note, not just a reason")

        status = entry.get("verification_status")
        if status in ("blocked", "partial"):
            warn(f"{where}: verification_status={status}, not publishable yet")


def check_derived(where, d, layers):
    """A TLS-computed central figure, permitted by D-070.

    Every rule here is one of D-070's safeguards. The last one is the
    strictest and is ECON's own: our number may not rest on an input we
    have not verified, because a tls_built figure standing on an
    unchecked source is the worst combination available.
    """
    if d.get("status") == "blocked":
        warn(f"{where}: derived figure blocked, {d.get('_blocked_reason', 'no reason given')}")
        return
    if d.get("status") != "published":
        err(f"{where}: derived figure needs status blocked or published")
        return

    if d.get("authorship") != "tls_built":
        err(f"{where}: a derived figure must carry authorship tls_built (D-021)")
    if d.get("evidence_basis") != "combined":
        err(f"{where}: a derived figure is Combined under D-033")
    if not d.get("method"):
        err(f"{where}: a derived figure must state its method at the point of use")
    if not (d.get("range_low") is not None and d.get("range_high") is not None):
        err(f"{where}: a derived figure is never shown without its range (D-070)")

    inputs = d.get("inputs") or []
    if len(inputs) < 1:
        err(f"{where}: a derived figure must name its inputs")
    for i, inp in enumerate(inputs):
        if not inp.get("verified"):
            err(f"{where}.inputs[{i}]: input {inp.get('label')!r} is not verified; "
                f"a TLS-computed figure may not rest on an unverified source")
        if not inp.get("estimator_note") and not inp.get("estimator_id"):
            err(f"{where}.inputs[{i}]: input must name its estimator")

    # D-070's same-basis test: the constraint that makes the whole thing
    # defensible. Averaging or scaling across categories reproduces the
    # Indonesia error with a decimal point.
    cats = {inp.get("category") for inp in inputs if inp.get("category")}
    if len(cats) > 1:
        err(f"{where}: inputs span categories {sorted(cats)}; a derived figure may "
            f"only combine inputs in the same category on the same basis (D-070)")

    # Never the only number on the page.
    money = [l for l in layers if l.get("kind") in {"money", "analog", "reference"}]
    if len(money) < 2:
        err(f"{where}: a derived figure is never the only number on a page")


def check_event(name, doc, estimators):
    """Per-event payloads. The Spain case is the first."""
    where = f"events/{name}"

    for field in ("econ_event_id", "label", "geography", "attribution_tag",
                  "evidence_basis", "authorship", "layers"):
        if not doc.get(field):
            err(f"{where}: missing {field}")

    if doc.get("evidence_basis") not in EVIDENCE_BASIS:
        err(f"{where}: evidence_basis not in the D-033 enum")
    if doc.get("authorship") not in AUTHORSHIP:
        err(f"{where}: authorship not in the D-021 enum")

    # The never-sum rule, enforced structurally rather than trusted. A
    # payload carrying a total invites a renderer to show it, and the
    # sum of these categories measures nothing.
    flat = json.dumps(doc).lower()
    for banned in ('"total":', '"sum":', '"grand_total":', '"total_cost":'):
        if banned in flat:
            err(f"{where}: contains a {banned} field; layers are different "
                f"categories and their sum measures nothing")

    money_kinds = {"money", "analog", "reference"}
    non_loss_seen, loss_seen = [], []

    for i, layer in enumerate(doc.get("layers", [])):
        lw = f"{where}.layers[{i}]"
        kind = layer.get("kind")
        if not kind:
            err(f"{lw}: missing kind")
        if not layer.get("label"):
            err(f"{lw}: missing label")

        if kind in money_kinds:
            check_figure(lw, layer, estimators)
            cat = layer.get("category")
            if not cat:
                err(f"{lw}: money layer needs a category")
            elif cat in NON_LOSS_CATEGORIES:
                non_loss_seen.append(cat)
            else:
                loss_seen.append(cat)
        else:
            # Physical quantities need units, not currency.
            if "value" in layer and not layer.get("units"):
                err(f"{lw}: non-money layer needs units")

        # A figure whose scope is wider than the event must say so, or a
        # reader takes it as the event's own. The evacuation figure here
        # covers Spain AND France.
        if layer.get("value") and layer.get("kind") == "impact" and not layer.get("scope"):
            warn(f"{lw}: impact layer without an explicit scope")

    # Naming what nobody counted is what stops a reader treating the
    # visible layers as the cost of the event.
    if not doc.get("uncounted"):
        err(f"{where}: missing 'uncounted'; a payload that does not say what "
            f"is uncounted reads as complete")

    if not doc.get("absence_meaning"):
        err(f"{where}: missing absence_meaning")
    elif doc["absence_meaning"].get("reason") not in ABSENCE_REASONS:
        err(f"{where}: absence_meaning.reason not in enum")

    if non_loss_seen and loss_seen:
        # Legitimate, and the reason the Spain headline works, but only
        # when the payload is explicit that these are different kinds.
        if not doc.get("_no_total"):
            err(f"{where}: mixes loss and non-loss categories "
                f"({sorted(set(loss_seen))} with {sorted(set(non_loss_seen))}) "
                f"without a _no_total declaration")

    d = doc.get("derived_figure")
    if d:
        check_derived(f"{where}.derived_figure", d, doc.get("layers", []))

    hc = doc.get("headline_candidate")
    if hc:
        if hc.get("evidence_basis") == "combined" and not hc.get("_guardrail"):
            err(f"{where}: combined headline candidate needs a guardrail")
        if hc.get("_status", "").startswith("candidate"):
            warn(f"{where}: headline_candidate is not approved copy")


def main():
    raw_est = (DATA / "estimators.json")
    raw_lat = (DATA / "latency_map.json")
    for p in (raw_est, raw_lat):
        if p.exists():
            check_no_em_dash(p.name, p.read_text())

    estimators_doc = load("estimators.json")
    latency_doc = load("latency_map.json")

    check_methodology_matches_enum()

    if estimators_doc:
        check_estimators(estimators_doc)
        check_reader_fields("estimators", estimators_doc)
    if latency_doc:
        check_reader_fields("latency_map", latency_doc)
    if latency_doc and estimators_doc:
        check_latency(latency_doc, estimators_doc.get("estimators", {}))

    events_dir = DATA / "events"
    if events_dir.exists() and estimators_doc:
        for ev in sorted(events_dir.glob("*.json")):
            check_no_em_dash(f"events/{ev.name}", ev.read_text())
            try:
                ev_doc = json.loads(ev.read_text())
                check_event(ev.stem, ev_doc, estimators_doc.get("estimators", {}))
                check_reader_fields(f"events/{ev.stem}", ev_doc)
            except json.JSONDecodeError as exc:
                err(f"events/{ev.name}: invalid JSON, {exc}")

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
