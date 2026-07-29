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

Requested 2026-07-28, revised the same day after Fire, Floods and Crops
all rejected the original `event_status` boolean. They were right:
none of them has event objects, they have continuous measured series,
and the field was shaped like ECON's mental model rather than their
data. Full history and reasoning in
`research/econ_rapid_response_spec.md` section 5.

Shared: `geography`, `measure + units`, `analog_comparison`,
`baseline_tier`, optional `footprint`.

Then each channel expresses two axes in its own domain terms, and ECON
derives the interpretation with the threshold published in ECON's
methodology, where a reader can check it:

    hazard trajectory       is the physical thing still developing
    measurement maturity    is the observation still catching up

    Fire      activity_status (active|quiet|dormant),
              area_revision_open, area_lag_days
    Floods    series[], peak and latest, days_above a named
              percentile, direction, observed_frac per day
    Crops     ASAP season state, estimate_state (provisional|settled)

Two consequences worth carrying:

- **Event identity comes from the estimator, not the channel.** A
  continuous series has no natural event, and declaring one is an
  editorial act neither the channels nor ECON should perform. PERILS
  says "Windstorm Goretti"; that is the event, because it is the unit
  the money attaches to. ECON joins to channel data on geography and
  date range.
- **Crops has no backward revision history.** The USDA PSD bulk file
  holds one current estimate per cell with no vintage series, so a
  crops revision history begins the day we start snapshotting and not
  before. Crops rows say "no prior vintages exist" rather than showing
  an empty history that reads like stability.

`baseline_tier` is per country-commodity pair for crops, not per
country. `attribution pending` is not a weak yes and is never
collapsed into an ENSO-attributed loss.
