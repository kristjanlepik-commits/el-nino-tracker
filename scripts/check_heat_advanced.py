#!/usr/bin/env python3
"""Did this heat refresh move ANY city, when a city could have moved?

    python scripts/check_heat_advanced.py [--payload PATH] [--base REF]

Exit 0 when at least one city advanced, or when none could have. Exit 1
when work was available and nothing was done.

WHY THIS EXISTS, AND WHY IT IS NOT heat/refresh_gate.py's frontier check.
Those answer two different questions and conflating them is what would
make one of them useless:

    frontier(cur)   PER CITY: is this city short of the last day it could
                    have reached? Advisory on purpose. A short city is
                    correctly labelled by counted_to and publishing it is
                    honest; Tallinn's source has stopped and Aberdeen's
                    bulletins were refused by a guard doing its job, and
                    neither is a fault to fix. Blocking on those would
                    stop weeks of publishes on cities that are fine.

    this check      PER RUN: did the run accomplish anything at all?
                    Zero movement is not staleness. It is a job that
                    fetched, built, committed and published while every
                    single city stayed exactly where it was.

The second has no coverage anywhere else. On 2026-09-07 the assembled
cities' builders were wired into heat_refresh.yml, and the step's own
guard fails only when every builder throws. Once a refused write became
a HOLD rather than a failure, which was the correct fix, four builders
each holding every one of their cities became a case with no exception,
no failure, no movement, and eighteen cities frozen at their committed
dates behind a green run. That is the exact shape of the three bugs
found that morning, arriving through the fix for them.

THE PRECEDENT IS scripts/check_window_advanced.py, written for fires
after the identical event: "Every step exited zero, the bot committed,
the page rebuilt, and nothing said the window had not advanced." It
lives in scripts/ rather than the channel's own directory at the Fire
chat's request, on the grounds that a check a channel writes about its
own output inherits that channel's blind spots. Same reasoning here.

"WHEN A CITY COULD HAVE MOVED" IS THE WHOLE PRECISION. A weekly job
re-run twice in one afternoon legitimately moves nothing the second
time, and a guard that fires on that gets muted within a fortnight. So
this asks two questions and needs both: did anything advance, and was
there anything to advance toward. Nothing moved AND nothing could have
is a quiet week. Nothing moved WHILE something could have is the
failure.

THE FRONTIER IS IMPORTED, NOT REIMPLEMENTED. heat/refresh_gate.frontier
owns "today minus the source's own publication lag, or the season end,
whichever is earlier", and a second copy of that arithmetic here is a
thing that drifts until the two disagree and nobody can say which is
right. This calls it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "heat"))

PAYLOAD = "heat/data/city_nights.json"


def _counted(payload: dict) -> dict[str, str]:
    """{city: counted_to} for every city that states one."""
    out = {}
    for city, v in (payload.get("cities") or {}).items():
        if isinstance(v, dict) and v.get("counted_to"):
            out[city] = v["counted_to"]
    return out


def _committed(ref: str, rel: str):
    """The payload as of `ref`, or None when it is not there.

    None is a real answer rather than an error: the first run after this
    file is added, or a fresh branch, has no base to compare against and
    that is not a fault.
    """
    r = subprocess.run(["git", "show", f"{ref}:{rel}"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def _base_age_hours(ref: str, rel: str):
    """Hours since the compared-against payload was committed, or None."""
    r = subprocess.run(["git", "log", "-1", "--format=%cI", ref, "--", rel],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        when = datetime.fromisoformat(r.stdout.strip())
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - when.astimezone(timezone.utc)
            ).total_seconds() / 3600


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", default=PAYLOAD)
    ap.add_argument("--base", default="HEAD",
                    help="git ref holding the payload to compare against")
    ap.add_argument("--min-base-age-hours", type=float, default=20.0,
                    help="below this, a run that advanced nothing is treated "
                         "as a re-run rather than a stalled refresh")
    args = ap.parse_args()

    cur_path = ROOT / args.payload
    if not cur_path.exists():
        print(f"  no payload at {args.payload}; nothing to check.")
        return 0
    cur = json.loads(cur_path.read_text())

    prev = _committed(args.base, args.payload)
    if prev is None:
        print(f"  no committed payload at {args.base}:{args.payload} to "
              f"compare against. Not a fault; nothing to say.")
        return 0

    now, was = _counted(cur), _counted(prev)
    advanced = sorted(c for c, d in now.items() if d > was.get(c, ""))

    # Work available is measured on the PREVIOUS payload on purpose: the
    # question is whether this run had something to do when it started,
    # not whether anything is short now. A run that correctly advanced
    # every city it could still leaves cities short whose sources have
    # stopped, and judging on the current payload would call that a
    # failure forever.
    from refresh_gate import frontier  # noqa: E402
    available = frontier(prev)

    if advanced:
        print(f"  {len(advanced)} city/cities advanced: "
              f"{', '.join(advanced[:6])}"
              f"{' ...' if len(advanced) > 6 else ''}")
        return 0

    if not available:
        print("  no city advanced, and none could have: every city was "
              "already at the last day its source and season allow. A "
              "quiet week, not a failure.")
        return 0

    # THE FALSE POSITIVE THIS EXISTS TO KILL, found by running the check
    # rather than by writing it carefully. Some cities are short for
    # reasons that will never resolve by running again: Tallinn's source
    # has stopped, Aberdeen's bulletins are refused by a guard doing its
    # job. Their shortfall is FIXED rather than growing, because once a
    # season closes the frontier stops advancing, so "work was available"
    # reads true forever on those two alone. A same-afternoon re-run
    # therefore trips this while being entirely correct, and a check that
    # cries wolf on a re-run is a check somebody mutes.
    #
    # So the base's own age is the tiebreak. If the payload we are
    # comparing against was committed in the last few hours, nothing
    # advancing is the expected result rather than a defect: no source
    # has published since. Measured from the commit rather than from the
    # payload, which carries no timestamp of its own.
    age_h = _base_age_hours(args.base, args.payload)
    if age_h is not None and age_h < args.min_base_age_hours:
        print(f"  no city advanced, and {len(available)} could have, but the "
              f"payload being compared against is only {age_h:.1f}h old "
              f"(threshold {args.min_base_age_hours}h). Nothing has "
              f"published since it was written, so this is a re-run rather "
              f"than a stalled refresh. Not failing.")
        return 0

    names = ", ".join(f"{c} ({n}d short)" for c, _, _, n in available[:6])
    print(f"::error::NO city advanced, but {len(available)} could have: "
          f"{names}{' ...' if len(available) > 6 else ''}. The run fetched, "
          f"built and published while every city stayed exactly where it "
          f"was. Every step can exit zero and every page can rebuild with "
          f"the dates unchanged, which is why this asks the only question "
          f"that catches it. Check whether the assembled-city builders "
          f"held every city, and read the holds they printed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
