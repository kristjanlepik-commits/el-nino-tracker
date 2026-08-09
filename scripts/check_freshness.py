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
from datetime import date, datetime, timedelta, timezone
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



def _newest_collected(doc) -> "date | None":
    """Newest timestamp in an append-only collector file.

    Not a dict: this layer reads JSONL, so the loader hands it a list.
    """
    if not isinstance(doc, list) or not doc:
        return None
    best = None
    for s in doc:
        # THE KEY IS NOT FIXED EITHER, which is the second half of the
        # same mistake. Last time this read one VALUE format and Tallinn
        # wrote the other; this time it read one KEY NAME and London
        # writes "dt" ISO strings where Tallinn writes "ts" epoch ints.
        # A guard that hardcodes its subject's field name fails open the
        # moment a second subject arrives, and reports "no readable
        # as-of date" against a file full of good timestamps.
        v = None
        if isinstance(s, dict):
            for k in ("ts", "dt", "time", "observed_at"):
                if s.get(k) is not None:
                    v = s[k]
                    break
        d = None
        # Epoch seconds OR an ISO string. The collector writes epoch
        # ints; I assumed ISO and the layer reported "no readable as-of
        # date" against a file full of perfectly good timestamps, which
        # is a guard failing open on the one dataset that cannot be
        # refetched. Accept both rather than couple this to one writer.
        if isinstance(v, (int, float)):
            try:
                d = datetime.fromtimestamp(v, tz=timezone.utc).date()
            except (OverflowError, OSError, ValueError):
                d = None
        elif isinstance(v, str):
            try:
                d = datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            except ValueError:
                d = None
        if d is None:
            continue
        best = max(best, d) if best else d
    return best


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
    # Tallinn is BUILD-FORWARD: no archive reaches 2026 on a
    # commercially clear source, so a missed hour is permanently absent
    # rather than fetchable later. That makes silence the dangerous
    # state here more than anywhere else on the site.
    #
    # The collector commits nothing when there is no new sample, which is
    # correct: an empty commit every hour would be noise. But it means a
    # permanently BROKEN fetch looks exactly like a quiet one, and the
    # consecutive-no-op trap that cost Fire six days would cost this
    # channel record it cannot get back.
    #
    # 1 day, not hours, because this file's own alerting cadence is the
    # daily 06:30 UTC qa run; a tighter number could not be acted on any
    # sooner. A healthy hourly collector is never more than an hour
    # stale, so a full day means roughly 24 consecutive failures.
    #
    # active_months: the collector is bound to May-September in the cron,
    # because Tallinn's tropical-night count is measured from 1 May and a
    # February sample cannot move it. Without this key the layer would
    # report STALE every single day from October to April, and a guard
    # that cries wolf for seven months of the year is one nobody reads in
    # the five months it works. Off-season silence is correct here, which
    # is the opposite of every other layer in this file.
    {"path": "heat/data/collected/Tallinn.jsonl", "as_of": _newest_collected,
     "max_age": 1, "owner": "HEAT", "active_months": (5, 6, 7, 8, 9),
     "what": "the Tallinn forward collector, whose missed hours are "
             "permanent"},
    # LONDON HAS A HARDER CLOCK THAN TALLINN, and it is the retention
    # rather than the cadence. Met Office DataHub keeps 48 hours, measured
    # off the response because the documentation is a JavaScript shell.
    # Tallinn's feed is current-observation-only, so a missed run costs
    # one reading; here a missed run costs nothing at all until 48 hours
    # pass, and then it costs EVERYTHING since the last success.
    #
    # So 1 day is not a warning threshold, it is the last point at which
    # acting still saves the data. At the 6-hourly cadence a full day of
    # silence is four consecutive failures with roughly one day of margin
    # left, which is the latest a daily 06:30 check could still be acted
    # on before loss becomes permanent.
    #
    # NOT season-bound, unlike Tallinn. Tallinn's exemption is sound
    # because a February sample cannot move a tropical-night count, and
    # missing one costs one reading anyway. Here an off-season outage
    # costs every hour in the window, and four commits a day is too cheap
    # to trade against that.
    {"path": "heat/data/collected/London.jsonl", "as_of": _newest_collected,
     "max_age": 1, "owner": "HEAT",
     "what": "the London forward collector, whose source retains 48 hours"},
    {"path": "docs/pacific-sst.json", "as_of": _from_key("observation_date"),
     "max_age": 14, "owner": "DESIGN", "what": "front page Pacific SST field, "
                                               "refreshed by hand"},
]



# TRUNCATION IS INVISIBLE TO A DATE, which is Heat's Barcelona defect in
# this file. Their coverage gate passed a city at "100% coverage" while
# it held 35 years of an 86-year record, because the gate computed its
# denominator from the data it was checking. A truncated series scores
# perfectly against itself.
#
# The same hole is here: _newest_country_as_of takes the MAX over
# whatever countries are present. A burnt-area payload truncated to five
# countries would still report a current date and pass, because the
# newest date among five is as recent as the newest among ninety-four.
#
# THE RULE, worth holding for every guard: a check that derives its
# reference from the thing under test cannot detect truncation. It can
# only detect internal inconsistency, which is exactly the property a
# cleanly truncated artifact still has.
#
# So the reference is EXTERNAL: the canonical roster in
# country_history.json, which is what decides how many countries there
# should be. 0.9 rather than 1.0 because a country legitimately drops out
# when it has no qualifying data, and the fires roster moved 45 -> 48 ->
# 94 inside a week. Ten percent absorbs that; Heat's Barcelona was 26%.
ROSTER = ROOT / "fires" / "data" / "country_history.json"
MIN_ROSTER_FRACTION = 0.9


def _roster_size() -> int:
    try:
        return len(json.loads(ROSTER.read_text()).get("countries") or [])
    except (OSError, ValueError):
        return 0


def check_truncation(problems: list) -> None:
    expected = _roster_size()
    if expected < 10:
        return
    for rel in ("fires/data/burnt_area.json", "fires/data/current_week.json"):
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            n = len(json.loads(path.read_text()).get("countries") or {})
        except (OSError, ValueError):
            continue
        if n < expected * MIN_ROSTER_FRACTION:
            problems.append(
                f"{rel} holds {n} countries against a roster of {expected} "
                f"({n / expected:.0%}). The dates in it may look perfectly "
                f"current, because the newest date among a few countries is "
                f"as recent as the newest among all of them. A check that "
                f"takes its denominator from the data under test cannot see "
                f"truncation; this one takes it from the roster.")


def _expected_run_date(today: date, months) -> date:
    """The last date a seasonally-bound collector was expected to run.

    In season this is today, so the layer behaves normally. Out of season
    it is the final day of the most recent active month, and age is
    measured against THAT rather than against today.

    The second half is the part that matters. The obvious implementation
    is to skip the layer entirely when out of season, and it has a hole:
    a collector that dies in July, alarms for ten weeks, and is ignored
    goes GREEN on 1 October and stays green until May. The failure would
    be laundered into a clean bill of health by the exemption written to
    make the guard quieter. Anchoring to the season end instead means a
    mid-season death stays visible all winter, which is the whole winter
    somebody has to notice it before the next season starts on top of it.
    """
    if today.month in months:
        return today
    d = today.replace(day=1) - timedelta(days=1)
    while d.month not in months:
        d = d.replace(day=1) - timedelta(days=1)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", help="pretend today is this date (testing)")
    args = ap.parse_args()
    today = date.fromisoformat(args.as_of) if args.as_of else date.today()

    problems, rows = [], []
    check_truncation(problems)
    for layer in LAYERS:
        p = ROOT / layer["path"]
        if not p.exists():
            rows.append((layer["path"], "absent", "-", layer["owner"]))
            continue
        try:
            raw = p.read_text()
            doc = ([json.loads(l) for l in raw.splitlines() if l.strip()]
                   if p.suffix == ".jsonl" else json.loads(raw))
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
        months = layer.get("active_months")
        reference = _expected_run_date(today, months) if months else today
        age = (reference - as_of).days
        note = "" if reference == today else " off-season"
        rows.append((layer["path"], as_of.isoformat(), f"{age}d{note}",
                     layer["owner"]))
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
