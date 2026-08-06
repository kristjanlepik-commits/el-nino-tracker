#!/usr/bin/env python3
"""Is every published data layer as fresh as the page implies?

Requested by the Fire chat, 2026-07-28, after the detections layer on
the live fire pages froze on 27 July and stayed frozen for two days
while hectares kept updating daily. The pages looked alive. Nobody
noticed, including platform, and Kristjan found it by asking.

WHY THE EXISTING GUARDS COULD NOT SEE IT. qa_check.py and
publish_all.py answer "is this page well-formed": it exists, it has the
masthead and one analytics tag, its numbers match the frozen record,
nothing immutable moved. All of that was true, correctly, of a page
whose headline numbers were two days stale. Nothing answered "is this
page's data as fresh as it claims to be", so this file does.

WHY THIS ALSO SUBSUMES CONSECUTIVE-NO-OP ALERTING. The Fire chat asked
separately for an alert after N runs of exit 3 in a row, on the
reasoning that a step returning "nothing to do" six days in seven is
not idle, it is broken. That is right, but counting no-ops measures the
symptom and needs state across runs. Data age measures the thing itself
and needs no state: if a layer stops advancing, it goes stale here
whether the cause was a polite refusal, a silent skip, a crash, or a
source that quietly stopped publishing. One check, no bookkeeping.

Run:  python scripts/check_freshness.py [--as-of YYYY-MM-DD]
Exit 0 when every layer is inside its budget, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _from_window(doc: dict) -> date | None:
    """'07-21..07-27' carries no year. Assume the current one, and if
    that lands in the future, it belongs to last year."""
    m = re.search(r"(\d{2})-(\d{2})\.\.(\d{2})-(\d{2})", doc.get("window", ""))
    if not m:
        return None
    today = date.today()
    end = date(today.year, int(m.group(3)), int(m.group(4)))
    return end.replace(year=today.year - 1) if end > today else end


def _from_key(key: str):
    def get(doc: dict) -> date | None:
        v = doc.get(key)
        if not isinstance(v, str):
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return get


def _newest_country_as_of(doc: dict) -> date | None:
    """Leading edge of a per-country layer, from the SOURCE's own as_of.

    Not the top-level `fetched`. That records when we last ran, so a
    fetcher polling a dead source keeps it current forever while the data
    rots underneath: measuring our own activity and calling it freshness,
    which is the mistake this whole file exists to catch. Newest rather
    than oldest because countries legitimately publish at different lags;
    the question here is whether the layer as a whole has stopped
    advancing, and per-country lag is already guarded at fetch time by
    MAX_LAG_DAYS in fires/fetch_burnt_area.py.
    """
    ds = [c.get("as_of") for c in (doc.get("countries") or {}).values()
          if isinstance(c, dict) and isinstance(c.get("as_of"), str)]
    try:
        return max(date.fromisoformat(d) for d in ds) if ds else None
    except ValueError:
        return None


def _crops_publication(doc: dict) -> date | None:
    """When ASAP last PUBLISHED, which is the only clock the rule names.

    MY FIRST VERSION OF THIS LAYER WAS WRONG and CRO's own file is what
    showed it. I pointed it at `dekad` in the stress payload and it
    reported 26 days stale. But `dekad` is the LABEL of the observation
    window, and its start at that, so three different ages of one file
    were measurable on 2026-08-06:

        from the dekad label, 11 July      26 days
        from the window close, 20 July     17 days
        from publication                   the actual rule

    And the decisive fact: `newest_published` in this log is 2026-07-11,
    which is exactly what we hold. **We are not behind the source at
    all.** The layer was flagging a live channel as stale for holding the
    newest thing that exists, which is a false positive of the worst kind
    because it is loud, wrong, and points at the wrong owner.

    Same error I have spent the week finding in other people's work: the
    quantity measured sat one step away from the quantity that mattered.

    Returns None when the age is not yet computable. `first_seen` on a
    backfilled entry is the first probe rather than the publication, so
    no age may be derived from it, and reporting one anyway would be
    inventing precision. A layer that cannot state its age is reported as
    such rather than guessed at.
    """
    days = doc.get("days_since_newest_first_seen")
    if not isinstance(days, (int, float)):
        return None
    return date.today() - timedelta(days=int(days))


def _latest_event_date(doc: dict) -> date | None:
    ds = [e.get("date") for e in doc.get("events", []) if isinstance(e.get("date"), str)]
    try:
        return max(date.fromisoformat(d) for d in ds) if ds else None
    except ValueError:
        return None


# THE RULE, stated once here because every layer below is an instance of
# it and the next channel should arrive with an instance rather than a
# special case:
#
#     A BUDGET IS SET BY THE SOURCE'S PUBLISHING CADENCE, NEVER BY HOW
#     OFTEN WE POLL IT.
#
# Polling frequency measures our own activity. A fetcher hitting a dead
# source on schedule looks perfectly healthy by that measure, which is
# precisely the bug this file shipped with and had to be corrected for.
# The source's cadence is the only thing that says whether the DATA has
# stopped moving.
#
# Two corollaries, both learned expensively:
#
#   - Do NOT count consecutive no-ops. A source publishing every 10 days
#     produces nine days of legitimate silence, and a counter reads that
#     as nine failures. Fire lost six days to that shape. CRO's crops
#     threshold, no new dekad for more than 20 days, is this rule applied
#     to a 10 day cadence: two full publication cycles.
#   - A check that cannot fail is worse than no check, so do not add a
#     layer before the data exists. A permanently green row reads as
#     coverage and provides none.
#
# Budgets are set from each layer's CADENCE, not picked. A daily job
# that ran successfully leaves its data one day old, because it captures
# through yesterday; the age therefore oscillates between 1 and 2 across
# the day. So 2 is the tightest budget that does not cry wolf in the
# hours before a run, and it means a freeze is caught once two
# consecutive daily runs have been missed, roughly 48 hours in, not on
# day one. A budget of 1 would be caught faster and would also fail
# every night before the fires job runs (03:10 UTC, with a 05:30 UTC
# backstop), which is how a check gets ignored.
#
# A hand-refreshed layer gets a fortnight, because nothing schedules it
# and the honest question there is "has anyone touched this recently".
LAYERS = [
    {"path": "data/events.json", "as_of": _latest_event_date, "max_age": 2,
     "owner": "FIRE", "what": "fire detections, the layer that froze"},
    {"path": "fires/data/current_week.json", "as_of": _from_window, "max_age": 2,
     "owner": "FIRE", "what": "detections working set"},
    # 14, not 2. EFFIS and GWIS publish weekly with roughly six days of
    # lag, so a daily budget would cry wolf on the source's own cadence.
    # Matches MAX_LAG_DAYS in fires/fetch_burnt_area.py: weekly plus lag
    # plus slack. The Fire chat's figure, and the general rule it comes
    # from is that a budget is set by the SOURCE's publishing cadence,
    # never by how often we happen to poll it.
    {"path": "fires/data/burnt_area.json", "as_of": _newest_country_as_of,
     "max_age": 14, "owner": "FIRE", "what": "burnt area hectares"},
    {"path": "fires/data/country_history.json", "as_of": _from_window, "max_age": 2,
     "owner": "FIRE", "what": "same-week baseline; if this is stale the "
                              "detections job refuses every run"},
    # 20, being two full ASAP publication cycles, which is CRO's figure
    # and the rule above applied to a 10 day cadence. NOT a
    # consecutive-no-op counter: ASAP's cadence means nine days of
    # legitimate silence, and Fire lost six days to exactly that shape.
    #
    # Added 2026-08-06, later than it should have been. I told CRO I would
    # add this when crops emitted its first data file, on the correct
    # reasoning that a check which cannot fail is worse than none. Crops
    # then went live and I did not come back to it, so a published channel
    # ran with no staleness check at all. The promise was right and the
    # follow-through was mine to do.
    # pending_until: probing only began 2026-08-06, so no publication
    # INTERVAL has been observed yet and the age is legitimately
    # unknowable rather than missing. That is a real state and reporting
    # it as a failure would be crying wolf on day one.
    #
    # But it self-expires, deliberately. ASAP publishes every 10 days, so
    # by two full cycles past the first probe there must be a computable
    # interval; if there is not, either the source has stopped or the
    # probe has, and both are exactly what this file exists to catch. An
    # exemption with no end date is how a guard quietly stops guarding.
    {"path": "crops/data/publication_log.json", "as_of": _crops_publication,
     "max_age": 20, "owner": "CRO", "pending_until": date(2026, 8, 26),
     "what": "the crops publication clock, behind /crops/"},
    {"path": "docs/pacific-sst.json", "as_of": _from_key("observation_date"),
     "max_age": 14, "owner": "DESIGN", "what": "front page Pacific SST field, "
                                               "refreshed by hand"},
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", help="pretend today is this date (testing)")
    args = ap.parse_args()
    today = date.fromisoformat(args.as_of) if args.as_of else date.today()

    problems, rows = [], []
    for layer in LAYERS:
        p = ROOT / layer["path"]
        if not p.exists():
            rows.append((layer["path"], "absent", "-", layer["owner"]))
            continue
        try:
            doc = json.loads(p.read_text())
        except (OSError, ValueError) as exc:
            problems.append(f"{layer['path']} is unreadable ({exc}). "
                            f"Owner: {layer['owner']}.")
            continue
        as_of = layer["as_of"](doc)
        pending = layer.get("pending_until")
        if as_of is None and pending and today <= pending:
            rows.append((layer["path"], "pending", "-", layer["owner"]))
            continue
        if as_of is None:
            problems.append(
                f"{layer['path']} has no readable as-of date. A layer that "
                f"cannot state its own age cannot be checked, and an "
                f"unchecked layer is how the last one froze for two days. "
                f"Owner: {layer['owner']}.")
            continue
        age = (today - as_of).days
        rows.append((layer["path"], as_of.isoformat(), f"{age}d", layer["owner"]))
        if age > layer["max_age"]:
            problems.append(
                f"{layer['path']} is {age} days old, budget {layer['max_age']}. "
                f"This is {layer['what']}. The pages built from it are still "
                f"well-formed, which is exactly why nothing else catches this. "
                f"Owner: {layer['owner']}.")

    w = max(len(r[0]) for r in rows) if rows else 20
    for path, as_of, age, owner in rows:
        print(f"  {path:<{w}}  {as_of:>10}  {age:>4}  {owner}")

    if problems:
        print(f"\nSTALE: {len(problems)} layer(s) past budget\n")
        for p in problems:
            print(f"  {p}\n")
        return 1
    print("\nall layers fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
