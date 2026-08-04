#!/usr/bin/env python3
"""Is a credential close enough to expiry to be worth shouting about?

WHY THIS EXISTS, and it is the compounding case QA's escalation map put
at the top. EARTHDATA_TOKEN expires 2026-09-26, silently. It is the
credential for the VIIRS flood capture. That capture has no alerting,
and ITS DATA CANNOT BE REFETCHED: LANCE deletes after about a week, so a
missed run is a permanent hole rather than a retry.

Token dies quietly, capture fails, and the failure lands in the one
place where failure cannot be undone.

Product's framing, which is right: a check that fires BEFORE the date is
worth more than an alert on the job that uses it, because by the time
that job fails the hole already exists.

WHY IT READS THE TOKEN RATHER THAN A DATE IN A CONSTANT. Earthdata
tokens are JWTs and carry their own `exp` claim, so the expiry is read
from the artifact. A hard-coded date would be exactly the class of
defect found four times this week: a fact written into code that was
right when written and silently wrong after its source moved. Rotate the
token and this check follows it with no edit.

WHERE IT RUNS, and the ordering is deliberate. In the floods workflow,
AFTER the capture step. Failing before the capture would prevent the
very run whose data cannot be recovered, which would be the guard
causing the harm it exists to prevent. So: capture first, then go red.

No network. Decodes the payload; does not verify the signature, which is
the server's job and not what is being asked here.

Exit 0 when the token is comfortably alive, 1 when it is inside the
warning window or already dead.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_TOKEN = Path.home() / ".earthdata_token"
# Three weeks. Long enough that a renewal needing Kristjan's credentials
# can wait for a convenient moment, short enough that it does not sit red
# for months and become furniture.
DEFAULT_WARN_DAYS = 21


def jwt_expiry(token: str) -> date | None:
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return datetime.fromtimestamp(claims["exp"], timezone.utc).date()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token-file", default=str(DEFAULT_TOKEN))
    ap.add_argument("--warn-days", type=int, default=DEFAULT_WARN_DAYS)
    ap.add_argument("--label", default="EARTHDATA_TOKEN")
    args = ap.parse_args()

    path = Path(args.token_file)
    if not path.exists():
        print(f"::warning::{args.label}: no token at {path}, nothing to check.")
        return 0

    expiry = jwt_expiry(path.read_text())
    if expiry is None:
        print(f"::warning::{args.label}: could not read an expiry from the "
              f"token. It may not be a JWT. Not treating that as a failure, "
              f"since an unreadable expiry is not evidence of a dead token.")
        return 0

    left = (expiry - date.today()).days
    if left > args.warn_days:
        print(f"{args.label} expires {expiry} ({left} days). Fine.")
        return 0

    if left < 0:
        print(f"::error::{args.label} EXPIRED on {expiry}, {-left} days ago. "
              f"The VIIRS flood capture cannot authenticate, and LANCE "
              f"deletes after about a week, so every day from here is a "
              f"permanent hole rather than a delayed fetch. Renewal needs "
              f"Kristjan's credentials.")
    else:
        print(f"::error::{args.label} expires {expiry}, in {left} days. "
              f"Renew before then. This is deliberately loud early: the "
              f"capture it authenticates cannot be re-run after the fact, "
              f"so an alert on the failing job would arrive after the data "
              f"was already lost. Renewal needs Kristjan's credentials.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
