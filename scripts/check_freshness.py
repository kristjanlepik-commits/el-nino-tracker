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
from datetime import date, datetime
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


def _latest_event_date(doc: dict) -> date | None:
    ds = [e.get("date") for e in doc.get("events", []) if isinstance(e.get("date"), str)]
    try:
        return max(date.fromisoformat(d) for d in ds) if ds else None
    except ValueError:
        return None


# Budgets are set from each layer's CADENCE, not picked. A daily job
# that ran successfully leaves its data one day old, because it captures
# through yesterday; the age therefore oscillates between 1 and 2 across
# the day. So 2 is the tightest budget that does not cry wolf in the
# hours before a run, and it means a freeze is caught once two
# consecutive daily runs have been missed, roughly 48 hours in, not on
# day one. A budget of 1 would be caught faster and would also fail
# every night before 04:00 UTC, which is how a check gets ignored.
#
# A hand-refreshed layer gets a fortnight, because nothing schedules it
# and the honest question there is "has anyone touched this recently".
LAYERS = [
    {"path": "data/events.json", "as_of": _latest_event_date, "max_age": 2,
     "owner": "FIRE", "what": "fire detections, the layer that froze"},
    {"path": "fires/data/current_week.json", "as_of": _from_window, "max_age": 2,
     "owner": "FIRE", "what": "detections working set"},
    {"path": "fires/data/burnt_area.json", "as_of": _from_key("fetched"), "max_age": 2,
     "owner": "FIRE", "what": "burnt area hectares"},
    {"path": "fires/data/country_history.json", "as_of": _from_window, "max_age": 2,
     "owner": "FIRE", "what": "same-week baseline; if this is stale the "
                              "detections job refuses every run"},
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
