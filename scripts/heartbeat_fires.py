#!/usr/bin/env python3
"""Does the LIVE fires page say a current week, checked from outside CI.

    .venv/bin/python scripts/heartbeat_fires.py [--max-age-days N]

WHY THIS EXISTS AND WHY EVERYTHING ELSE IN THIS REPO CANNOT DO ITS JOB.
2026-08-28: GitHub silently dropped all three of fires.yml's scheduled
slots overnight, the second such night in three (the first cost
ea1c76df's third cron slot, which did not help, because three slots on
one scheduler share one failure mode). The gate split, per-country
isolation and hold-vs-crash separation built this week all assume a run
STARTS and then reports on itself. None of them can see a run that never
started: a missing run and a quiet night are identical from inside CI,
so absence produces no signal there at all.

THIS SCRIPT MUST NEVER RUN ON A GITHUB ACTIONS SCHEDULE. That would put
it behind the exact scheduler it exists to catch failing, and it would
go silent on precisely the nights that matter, which is a more dangerous
failure than not having it, because a check that CAN fail silently reads
as coverage that is not there. It is a standalone script for a reason:
Business's ask (2026-08-28) was for a second trigger origin outside
GitHub's scheduler entirely, e.g. Kristjan's own machine (Admin.command)
or the mycelium spine dispatching this via the GitHub API. That decision
is joint with the Fire chat and is not made here; this file is the
payload whichever origin is chosen would run.

SAME SHAPE AS scripts/check_live_matches_committed.py (A16), ONE STEP
SIMPLER: that compares live against committed and needs a reference.
This only needs a live fetch and a calendar, because the question is not
"does live match committed", it is "is live current at all", and a repo
comparison cannot answer that when the repo itself may not have moved
either.

DOES NOT DISTINGUISH A DROPPED SCHEDULE FROM A LEGITIMATE HOLD, on
purpose. Both leave the live page equally stale, and a human needs to
know either way. Once alerted, fires_gate.yml's own run history (a
separate, already-loud signal under its own name) is where to look next
to tell the two apart; that is not this script's job.

Exit 0 when the live page is within budget, 1 when it is not (or cannot
be read at all, which is its own kind of "not current").
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import date, timedelta

URL = "https://thelongswell.com/fires/"
# Abbreviated, matching the live page's own format exactly ("wk Aug
# 21-27"), not the full month name. Tested against a real fetch, not
# assumed: the first version used full names and silently matched
# nothing, an empty result that read as "cannot verify" rather than
# crashing, which is the correct failure shape but was caught by running
# it, not by writing it carefully enough the first time.
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
     "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "tls-fires-heartbeat"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception as exc:
        return 0, str(exc)


def claimed_end_date(html: str, today: date) -> date | None:
    """The window's own end date, from "wk Aug 20-26" or similar, read
    off the live index page rather than any file. The end day is what
    matters; the start day only disambiguates which month the range
    opened in when it spans a boundary and is not otherwise used.

    Year is inferred: fires' window always trails today, so a parsed
    date more than 60 days in the future is last year's, catching the
    one real ambiguity (a check run in early January against a window
    that closed in December).
    """
    m = re.search(r"wk\s+([A-Za-z]+)\s+\d+-(\d+)", html)
    if not m:
        return None
    month_name, end_day = m.group(1), int(m.group(2))
    month = MONTHS.get(month_name)
    if month is None:
        return None
    try:
        candidate = date(today.year, month, end_day)
    except ValueError:
        return None
    if (candidate - today).days > 60:
        candidate = date(today.year - 1, month, end_day)
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-age-days", type=int, default=2,
                    help="how many days behind today the window may "
                         "trail before this shouts. Fire's arithmetic, "
                         "2026-08-28, corrected the original default of "
                         "4: the trailing window always ends YESTERDAY "
                         "on a healthy page, so age 1 is the normal "
                         "reading every day, not age 0. Age 2 means one "
                         "publish was missed; age 3 means two. D-236 is "
                         "zero failure days, so the alarm has to fire on "
                         "the FIRST miss it can safely distinguish from "
                         "noise, which is the second consecutive one, "
                         "age 2, not somewhere past D-237's 24-hour hold "
                         "allowance. The original 4 gave real problems "
                         "days of silence past that target trying not to "
                         "cry wolf on a hold that D-237 already covers.")
    ap.add_argument("--as-of", help="pretend today is this date (testing)")
    args = ap.parse_args()
    today = date.fromisoformat(args.as_of) if args.as_of else date.today()

    status, body = fetch(URL)
    if status != 200:
        print(f"  CANNOT VERIFY: {URL} returned {status or 'a fetch error'} "
              f"({body[:120]}). A page that cannot be read is not "
              f"confirmed current, and that is a failure in its own "
              f"right, not a reason to pass silently.")
        return 1

    end = claimed_end_date(body, today)
    if end is None:
        print(f"  CANNOT VERIFY: no 'wk <Month> D-D' window found on "
              f"{URL}. The page's own shape changed or this pattern is "
              f"stale; either way, not confirmed current.")
        return 1

    age = (today - end).days
    # >= , not >. Fire's arithmetic is stated as "a budget of 2 fires on
    # the second consecutive miss, age 2": the budget IS the age that
    # trips it, not the age one below the trip point. A plain `>` here
    # would have silently moved the real threshold to 3 while the
    # --help text and every comment still said 2, the exact shape of bug
    # this whole file exists to catch elsewhere.
    if age >= args.max_age_days:
        print(f"  STALE: live fires page's window ends {end.isoformat()}, "
              f"{age} day(s) behind today ({today.isoformat()}), budget "
              f"{args.max_age_days}. Checked live, not from the repo: "
              f"whatever CI believes happened, the page a reader sees "
              f"has not moved.")
        return 1

    print(f"  live fires page current: window ends {end.isoformat()}, "
          f"{age} day(s) old, within budget {args.max_age_days}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
