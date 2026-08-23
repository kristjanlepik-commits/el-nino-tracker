#!/usr/bin/env python3
"""Record a channel's sign-off (D-200): scripts/approve_channel.py <channel>

Run this AFTER the owning chat has reviewed a preview build, never before.
It writes signoff/<channel>.json with the current hash of that channel's
template and payload files (scripts/publish_all.py's SIGNOFF_INPUTS), and
from that point publish_all will rebuild the channel until either file set
changes again.

THIS SCRIPT DOES NOT REVIEW ANYTHING. It has no way to know whether the
pages are right; it only records that a human says they are. Running it
without having looked is how the gate becomes decorative, which is the
exact failure D-200 was written to close one level up.

WHY A SEPARATE SCRIPT, not a flag on publish_all.py. D-200's own design:
"the channel signs off on a preview build, and the act of approving writes
the hash." Folding that into the publish path would make approval and
publishing the same act again, which is the mistake this whole mechanism
exists to undo.

--by and --note are REQUIRED. Fire's fires/accept_payload.py made this
the rule and named the reason: this script's own first marker read
"platform (bootstrap)" for four days on a channel platform does not own,
because both flags defaulted to empty. An approval with no name and no
reason is one nobody can question later, which is the whole point of
recording it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from publish_all import SIGNOFF_INPUTS, SIGNOFF_DIR, channel_signoff_hash  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("channel", choices=sorted(SIGNOFF_INPUTS))
    ap.add_argument("--by", default="", help="REQUIRED: who is approving, for the record")
    ap.add_argument("--note", default="", help="REQUIRED: why these changes are correct")
    args = ap.parse_args()

    if not args.by or not args.note:
        print("  REFUSING: --by and --note are both required. An approval "
              "with no name and no reason is one nobody can question "
              "later, which is the whole point of recording it.",
              file=sys.stderr)
        return 2

    current = channel_signoff_hash(args.channel)
    marker = SIGNOFF_DIR / f"{args.channel}.json"
    SIGNOFF_DIR.mkdir(exist_ok=True)
    marker.write_text(json.dumps({
        "channel": args.channel,
        "approved_hash": current,
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "approved_by": args.by,
        "note": args.note,
        "inputs": sorted(SIGNOFF_INPUTS[args.channel]),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"  {args.channel} approved: {current[:12]}... "
          f"({len(SIGNOFF_INPUTS[args.channel])} input file(s))")
    print(f"  wrote {marker.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
