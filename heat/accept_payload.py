#!/usr/bin/env python3
"""Record that a person reviewed heat's held payload, and release it.

THE DEADLOCK THIS ENDS. publish_all promotes heat/data/published/ only
after a successful publish, and a hold prevents the publish, so a held
channel stays held with no documented way out. That is fine while
publishing only happens in band. It stops being fine the moment pages
move by another route, which happened on 2026-09-07: Kristjan directed
the heat page fixed immediately, design pushed 54 pages directly while
the gate held, and the reference could not follow. Pages moved, the
reference could not, and the gate went on holding a claim that had
already been corrected and shipped.

I CLEARED IT BY HAND THAT DAY, with a commit of 4,288 insertions and
4,062 deletions. It worked and it is the wrong mechanism: nothing in it
distinguishes "I read the held claims and they are correct" from "I made
the red light go away", and a diff at that volume is not reviewable by
anybody. That is D-200's problem arriving at the reference file.

THIS SCRIPT REVIEWS NOTHING. Same as fires/accept_payload.py and
approve_channel.py, and for the same reason: it records that a named
person says the held changes are correct. Running it on changes you have
not read turns the gate into decoration, which is the failure it exists
to prevent one level up.

IT APPROVES CLAIMS, NOT BYTES, and that is the one thing it does that
fires' version does not. Platform's framing, from the audit-approval
question: asking a person "is this payload correct" is unanswerable at
2.5 MB, and asking "does this change what we tell a reader" is small and
answerable. So it prints what the gate is holding on, names each
withdrawn record with its reason, and records those claims in the log
alongside the name. The log then says WHAT was approved rather than only
that something was.

--by and --note are REQUIRED. fires learned that from approve_channel.py,
whose first marker read "platform (bootstrap)" for four days on a channel
platform does not own. An acceptance with no name is one nobody can
question later.

Usage:
    python heat/accept_payload.py --dry-run
    python heat/accept_payload.py --by "Heat" --note "why these are right"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

CURRENT = ROOT / "heat" / "data" / "city_nights.json"
PUBLISHED = ROOT / "heat" / "data" / "published" / "city_nights.json"
LOG = ROOT / "heat" / "data" / "acceptance_log.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--by", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CURRENT.exists():
        print("  no current payload; run emit_city_nights.py first",
              file=sys.stderr)
        return 2
    if not PUBLISHED.exists():
        print("  no published reference to compare against; nothing to "
              "accept, and the gate will refuse for that reason instead",
              file=sys.stderr)
        return 2

    from refresh_gate import classify  # noqa: E402
    prev = json.loads(PUBLISHED.read_text())
    cur = json.loads(CURRENT.read_text())
    block, report, withdrawn = classify(prev, cur)

    if not block:
        print(f"  the gate is not holding. {len(report)} ordinary change(s) "
              f"would pass on their own, so there is nothing for a person to "
              f"accept and publish_all will promote the reference itself.")
        return 0

    # THE CLAIMS, WHICH IS WHAT IS ACTUALLY BEING APPROVED.
    print(f"  the gate is holding on {len(block)} claim(s):\n")
    for b in block:
        print(f"    - {b}\n")
    if withdrawn:
        print(f"  {len(withdrawn)} record withdrawal(s) in this payload:")
        for w in withdrawn:
            print(f"    {w['city']:12s} {w['reason']:18s} "
                  f"needs_correction={w['needs_correction']}")
        print()
    print(f"  and {len(report)} ordinary change(s) that would have passed "
          f"unaccompanied.\n")

    if args.dry_run:
        print("  --dry-run, nothing promoted")
        return 0
    if not args.by or not args.note:
        print("  REFUSING: --by and --note are both required. An acceptance "
              "with no name and no reason is one nobody can question later, "
              "which is the whole point of recording it.", file=sys.stderr)
        return 2

    PUBLISHED.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED.write_bytes(CURRENT.read_bytes())

    log = json.loads(LOG.read_text()) if LOG.exists() else []
    log.append({
        "accepted_at": datetime.now(timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "accepted_by": args.by,
        "note": args.note,
        # The claims, verbatim, so the record says what was approved rather
        # than that something was. A log naming only a person and a time
        # cannot be audited against the thing it released.
        "claims_accepted": block,
        "withdrawals": withdrawn,
        "ordinary_changes": len(report),
    })
    LOG.write_text(json.dumps(log, indent=1) + "\n")
    # PLAIN str(), NOT relative_to(). relative_to raises when the path is
    # not under ROOT, which happened the first time this was tested with LOG
    # pointed at a temp directory: the promotion and the log write had both
    # SUCCEEDED and the script then died on the sentence announcing it, so
    # the exit code reported failure on completed work. A cosmetic print must
    # not be able to fail after the side effects have landed.
    try:
        where = LOG.relative_to(ROOT)
    except ValueError:
        where = LOG
    print(f"  promoted the reference and logged the acceptance to {where}. "
          f"The gate now compares against what is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
