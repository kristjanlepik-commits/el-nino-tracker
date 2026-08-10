"""Wait for FIRMS quota, as a command the workflow can call.

WHY THIS EXISTS. The workflow did this in inline bash, and on 2026-08-10
that step failed the whole daily run. The FIRMS mapkey_status endpoint
was unreadable for about twenty minutes, the loop logged "Quota endpoint
unreadable; waiting rather than guessing" fifteen times, and the step hit
its budget. The site sat a day stale and nobody knew until Kristjan
asked.

THE DEFECT WAS NOT THE OUTAGE. The loop ran 20 attempts at 60s, which is
exactly its 20 minute step budget, so it could never reach its own
"Proceeding anyway" fallback: the step timeout always fired first. A
guard written to degrade gracefully was structurally unable to.

WHY THIS IS A COMMAND RATHER THAN A TIMEOUT TUNE. The gate is belt over
braces. `build_events` already handles quota exhaustion in process:
`_http.OverLimit` is raised on HTTP 400 and `_quota.wait_for_quota`
suspends the caller rather than burning retries, which is the mechanism
that actually protects the run. Verified against three cases, all of
which PROCEED rather than fail: unreadable endpoint, free quota,
saturated quota.

So the pre-check is an optimisation that saves runner minutes, and an
optimisation must never be able to fail the thing it optimises. This
exits 0 in every case, including when it gives up waiting.

EXIT CODES
    0  always. The caller proceeds regardless; build_events is the
       component that knows what to do about quota, and it does.

    Writing a non-zero here would recreate the defect: a transient
    upstream blip on an ADVISORY endpoint taking down a publish whose
    data source was healthy the whole time.
"""
from __future__ import annotations

import argparse
import sys
import time

from fires import _quota


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=600,
                    help="seconds to wait before proceeding anyway. "
                         "Deliberately below the caller's step timeout so "
                         "this can always reach its own fallback.")
    ap.add_argument("--resume-below", type=int, default=_quota.RESUME_BELOW,
                    help="transactions below which it is safe to start")
    args = ap.parse_args()

    started = time.time()
    used = _quota.current_transactions()

    if used is None:
        # UNREADABLE IS NOT EVIDENCE OF ANYTHING. It is not evidence the
        # quota is full, so blocking is wrong; and not evidence it is
        # free, so charging ahead unthrottled would be wrong too. Proceed
        # and let the in-process guard handle what it finds, which is the
        # only component that can actually observe the truth.
        print("::warning::FIRMS quota endpoint unreadable. Proceeding: "
              "build_events handles over-limit in process, and an "
              "advisory endpoint must not fail a publish whose data "
              "source may be healthy.")
        return 0

    if used < args.resume_below:
        print(f"Quota at {used}/5000, below {args.resume_below}. Proceeding.")
        return 0

    print(f"Quota at {used}/5000. Waiting up to {args.budget}s.", flush=True)
    _quota.MAX_WAIT_SECONDS = args.budget
    _quota.wait_for_quota("ci")

    used = _quota.current_transactions()
    waited = int(time.time() - started)
    if used is not None and used < args.resume_below:
        print(f"Quota at {used}/5000 after {waited}s. Proceeding.")
    else:
        # Still high, and we proceed anyway ON PURPOSE. The alternative
        # is failing a run that the in-process guard would have completed
        # slowly, which is strictly worse than completing slowly.
        print(f"::warning::Quota still {used}/5000 after {waited}s. "
              f"Proceeding; build_events will pace itself and may take "
              f"longer than usual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
