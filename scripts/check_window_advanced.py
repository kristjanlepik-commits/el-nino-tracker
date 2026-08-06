#!/usr/bin/env python3
"""Did the fires baseline window actually advance today?

THE DEFECT THIS EXISTS FOR, and it has now happened three times. On
2026-08-05 the fires publish reported complete success while the window
did not move: the site served 07-29..08-04 for a second day with the
data for 08-05 already available. Every step exited zero, the bot
committed, the page rebuilt, and nothing said the window had not
advanced. The same shape froze detections from 27 to 29 July, and again
on the morning of 08-06.

Each time the FAILURE was "the baseline did not advance" and every check
we had asked a different question: did the step exit zero, did the page
render, does docs match its generator, is the data's date inside budget.
All of those can be satisfied by a run that achieved nothing.

WHY IT LIVES HERE RATHER THAN IN fires/. The Fire chat asked for it on
their own surface to be moved to platform's, on the grounds that their
code is what keeps being wrong and a check a channel writes about its
own output inherits that channel's blind spots. That reasoning is right
and it generalises: the floods capture-gap check had the same problem,
reading the manifest it was supposed to be auditing.

WHY IT RUNS AT THE END OF THE JOB, not before the publish. A stale
window is not a reason to withhold the rest: burnt area moves on its own
clock and may have advanced, and the page is better published than
frozen. So the publish happens, then this goes red. Same ordering as the
token-expiry check, and the same reasoning: a guard must not cause the
harm it exists to detect.

Run:  python3 scripts/check_window_advanced.py [--as-of YYYY-MM-DD]
Exit 0 when the window is current, 1 when it has not advanced.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "fires" / "data" / "country_history.json"


def expected_window(today: date) -> str:
    """The trailing COMPLETE seven days, which ends yesterday.

    Matches fires/fetch_window_baseline.py's own definition. If that
    definition ever changes this check must change with it, which is a
    real coupling and better than the alternative of guessing.
    """
    end = today - timedelta(days=1)
    start = end - timedelta(days=6)
    return f"{start:%m-%d}..{end:%m-%d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", help="pretend today is this date (testing)")
    args = ap.parse_args()
    today = date.fromisoformat(args.as_of) if args.as_of else date.today()

    if not BASELINE.exists():
        print(f"::error::{BASELINE.relative_to(ROOT)} is missing entirely. "
              f"The baseline is the thing detections compare against, so "
              f"nothing downstream can be trusted.")
        return 1

    try:
        actual = json.loads(BASELINE.read_text()).get("window")
    except (OSError, ValueError) as exc:
        print(f"::error::{BASELINE.relative_to(ROOT)} is unreadable ({exc}).")
        return 1

    want = expected_window(today)
    if actual == want:
        print(f"baseline window is current: {actual}")
        return 0

    # Say how far behind, because one day late and five days late are
    # different problems and the number is the first thing anyone asks.
    behind = ""
    m = re.match(r"\d{2}-\d{2}\.\.(\d{2})-(\d{2})", actual or "")
    if m:
        try:
            got_end = date(today.year, int(m.group(1)), int(m.group(2)))
            if got_end > today:
                got_end = got_end.replace(year=got_end.year - 1)
            behind = f", {(today - timedelta(days=1) - got_end).days} day(s) behind"
        except ValueError:
            pass

    print(f"::error::The fires baseline window did NOT advance{behind}. "
          f"country_history.json holds '{actual}', expected '{want}'. "
          f"Every step in this run may have exited zero and the page may "
          f"have rebuilt, but detections cannot move while the baseline is "
          f"stale, so the site is serving a window it already served. This "
          f"is the failure that presented as a healthy run on 2026-07-27, "
          f"2026-08-05 and 2026-08-06. Check the baseline refresh step "
          f"first: a defective-day gap can drop coverage below its own "
          f"floor and make it refuse to write.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
