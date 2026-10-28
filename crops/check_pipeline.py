"""Is the crops pipeline keeping up with its source?

A DIFFERENT QUESTION FROM STALENESS, and that is the point. D-092's
max_data_age_days asks whether the data is still relevant to a reader:
30 days from the dekad label, being 21 days of reader relevance plus the
9 from label to window close. It is the right number for relevance and
much too slow for detecting a broken pipeline.

Platform suggested a git-commit-date bound, as used for heat and fires.
Measured before adopting it, and it does not work here: crops/data/
stress_current.json was committed NINE times in the two weeks to
2026-08-26 and every one carried dekad 2026-08-01. A commit-date check
tracks how often I edit the payload, not whether the channel is
advancing, and would have read healthy through the entire outage.

THE SIGNAL THAT ACTUALLY FIRED ON DAY ONE was already sitting in two
committed files that nothing compared. From 25 August,
publication_log.json recorded 2026-08-11 as published while
stress_current.json held 2026-08-01. The scheduled job had failed five
days running, having pulled for about an hour and three quarters each
time and discarded a correct payload; the channel looked healthy because
it was inside its relevance bound the whole time.

So this compares what the SOURCE has published against what we HOLD.
It cannot be fooled by a slow source, because a slow source publishes
nothing newer and the check stays quiet. It cannot be fooled by an
active editor, because editing does not advance the dekad.

Exit codes follow the repo convention:
    0  up to date, or behind for fewer than GRACE_DAYS
    1  a newer dekad has been published and not taken for too long
"""
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "data" / "stress_current.json"
LOG = HERE / "data" / "publication_log.json"

# ASAP publishes every 10 days and our own measured lag from window close
# has run 3 to 9 days, so a new dekad normally reaches us well inside a
# week of appearing. Three days is comfortably outside the normal path
# and far tighter than the 20-day publication-stall rule, which is about
# the SOURCE stopping rather than us failing to collect.
GRACE_DAYS = 3


SIGNOFF = HERE.parent / "signoff" / "crops.json"

# A dekad is ten days. One full cycle of a held sign-off is ordinary: the
# payload lands and a person has not looked yet. Two is not.
SIGNOFF_GRACE_DAYS = 10


def rendered_lag():
    """(approved dekad, held dekad, days since approval) or None.

    THE SECOND HALF OF THIS CHECK, added 2026-10-28. Everything below it
    compares ASAP against the PAYLOAD. The payload was current for a
    month while the page was not: crops sat blocked on D-200 sign-off
    from 2026-09-20 to 2026-10-28, CI committed four dekads that never
    rendered, the live page served dekad 09-01 labelled "15 days ago"
    when it was 48, and this check printed "up to date" every morning.
    D-303's rule, applied to my own check: a freshness signal covers
    every consumer of the thing it measures, or it must not say
    "up to date".

    The marker records the commit it approved at, so the dekad a reader
    actually sees is readable from git rather than from the site.
    """
    if not SIGNOFF.exists():
        return None
    mark = json.loads(SIGNOFF.read_text())
    commit, at = mark.get("approved_commit"), mark.get("approved_at")
    if not commit or not at:
        return None
    import subprocess
    out = subprocess.run(
        ["git", "show", f"{commit}:crops/data/stress_current.json"],
        cwd=HERE.parent, capture_output=True, text=True)
    if out.returncode != 0:
        return None
    approved = json.loads(out.stdout)["dekad"]
    held = json.loads(PAYLOAD.read_text())["dekad"]
    days = (dt.date.today() - dt.datetime.fromisoformat(at).date()).days
    return approved, held, days


def main() -> int:
    lag = rendered_lag()
    if lag:
        approved, held, days = lag
        if approved < held and days > SIGNOFF_GRACE_DAYS:
            print(f"::error::crops pipeline: the payload holds {held} but "
                  f"readers see {approved}, because sign-off has not run "
                  f"for {days} day(s). This is a SIGN-OFF block, not a "
                  f"collection failure: the data is current and the page "
                  f"is not. Owner CROPS: review a preview build and run "
                  f"scripts/approve_channel.py crops.")
            return 1
    if not PAYLOAD.exists() or not LOG.exists():
        print("crops pipeline: payload or publication log missing, "
              "cannot check")
        return 0
    held = json.loads(PAYLOAD.read_text())["dekad"]
    log = json.loads(LOG.read_text())
    newest = log.get("newest_published")
    if not newest:
        print("crops pipeline: publication log records nothing published")
        return 0
    if newest <= held:
        print(f"crops pipeline: up to date, holding {held}, "
              f"newest published {newest}")
        return 0

    # How long has the newer dekad been sitting there unclaimed?
    entry = (log.get("dekads") or {}).get(newest) or {}
    first_seen = entry.get("first_seen")
    days = None
    if first_seen and not entry.get("backfilled"):
        seen = dt.datetime.fromisoformat(first_seen).date()
        days = (dt.date.today() - seen).days

    msg = (f"crops pipeline: ASAP has published {newest} and we hold "
           f"{held}")
    if days is not None:
        msg += f", first seen {days} day(s) ago"
    if days is not None and days > GRACE_DAYS:
        print(f"::error::{msg}. The source has moved and we have not. "
              f"This is a COLLECTION failure, not a stale source: check "
              f"the crops_refresh run log rather than waiting for "
              f"max_data_age_days, which measures reader relevance and "
              f"will not fire for weeks.")
        return 1
    print(f"{msg}. Inside the {GRACE_DAYS} day grace, not yet an error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
