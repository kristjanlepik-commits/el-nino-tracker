# ECON: economic damages

Channel spec. ECON owns the cross-channel damage ledger as a data
product: what a climate event cost, according to whom, as of when, and
how that figure has moved. Commissioned by D-032, 2026-07-28.

Under D-030 ECON behaves like a channel: it owns sourcing and method,
emits validated JSON, and signs off on its rendered page before
publish. It does not render and does not publish. Unlike Fire, Floods
and Crops it is a **curation product, not a fetch product**, so it is
never a fast-reaction channel and its data job is human-triggered.

## The two rules that cannot bend

1. **TLS never authors a figure.** Every number belongs to a named
   estimator, with their issue date and their own units. Confirmed as a
   standing line in D-039. This is T5's authorship line.
2. **Never sum across categories.** Insured, direct economic, total
   economic, output loss, humanitarian appeal, mortality and monetised
   mortality measure different things. Separate rows, always. The
   validator enforces the enum.

## Files

    data/estimators.json    Estimator registry. Category definitions,
                            revision cadences, licence notes and
                            provenance, keyed by estimator so a
                            restatement updates one place and two rows
                            can never disagree about what the same
                            estimator meant.
    data/latency_map.json   After an event, when will a credible damage
                            figure exist and who will publish it.
                            Assembled from estimators' own published
                            schedules. States no event's cost.
    validate.py             Guards. Run before emitting anything.

Run the guards:

    .venv/bin/python econ/validate.py

Warnings do not fail the run; they mark entries that are not yet fit to
publish. Errors mean the data does not go to design.

## Evidence basis (D-033)

ECON is the type case for **Compiled**: named sources side by side, no
new number created by us. Where layers are joined into a view no single
source states, the item is **Combined** and carries the label visually
and textually. The `settles` field in the latency map is derived and is
flagged `derived: true` for exactly this reason; the validator fails if
it is not.

## Background

    research/handover_econ.md              the birth brief
    research/econ_source_report.md         phase 1: licensing, what
                                           each estimator measures,
                                           revision cadences, machine
                                           accessibility, the minimum
                                           viable ledger
    research/econ_rapid_response_spec.md   fast damage context from
                                           live channel data
    research/econ_disclosure_policy_draft.md   sponsor conflict, drafted
                                           and deferred per D-039
    research/econ_notes/                   working notes with full
                                           quotes and source URLs

## What ECON needs from the hazard channels

Requested from Fire, Floods and Crops on 2026-07-28. Detail in
`research/econ_rapid_response_spec.md` section 5:

    event_id, geography, measure + units, analog_comparison,
    baseline_tier, event_status (ongoing | ended), optional footprint

`event_status` is the one that is cheap now and expensive to backfill.
A loss estimate revised while an event is still running is a different
object from one revised after it ends, and no published loss record
separates those.
