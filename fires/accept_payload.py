#!/usr/bin/env python3
"""Record that a person reviewed a held fires payload, and release it.

THE GAP THIS FILLS. D-212's gate holds when a claim moves, which is
right. It has no way to say "I looked, and it is correct". The promotion
of fires/data/published/* happens inside publish_all only AFTER a
successful publish, and a hold prevents the publish, so a held channel
stays held forever with no documented way out. Found 2026-08-23, when
the site served a week-old page and nothing in the repo said how to
clear it.

D-200's byte hash has approve_channel.py for exactly this. The payload
gate had no counterpart.

THIS SCRIPT REVIEWS NOTHING, the same as approve_channel.py, and for the
same reason. It records that a named human says the held changes are
correct, and promotes the payload the gate compares against. Running it
to clear an error you have not read turns the gate into decoration,
which is the failure D-212 exists to prevent one level up.

--by and --note are REQUIRED rather than optional. approve_channel.py
makes them optional and its first marker read "platform (bootstrap)"
for four days on a channel platform does not own. An acceptance with no
name is an acceptance nobody can question later.

Usage:
    python fires/accept_payload.py --by "Fire" --note "why these are right"
    python fires/accept_payload.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD = (("events.json", os.path.join(ROOT, "data", "events.json")),
           ("burnt_area.json", os.path.join(ROOT, "fires", "data", "burnt_area.json")),
           ("current_week.json", os.path.join(ROOT, "fires", "data", "current_week.json")),
           ("eu_area.json", os.path.join(ROOT, "fires", "data", "eu_area.json")))
PUB = os.path.join(ROOT, "fires", "data", "published")
HIST = os.path.join(ROOT, "fires", "data", "area_history")
LOG = os.path.join(ROOT, "fires", "data", "acceptance_log.json")


def gate() -> tuple[bool, list[str]]:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "fires",
                                                     "refresh_gate.py")],
                       capture_output=True, text=True, cwd=ROOT)
    held = r.returncode != 0
    reasons = [l.strip()[2:] for l in (r.stdout + r.stderr).splitlines()
               if l.strip().startswith("- ")]
    return held, reasons


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--by", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    held, reasons = gate()
    if not held:
        print("  gate is not holding; nothing to accept")
        return 0

    print(f"  gate is holding on {len(reasons)} change(s):")
    for r in reasons:
        print(f"    - {r}")

    if args.dry_run:
        print("\n  --dry-run, nothing promoted")
        return 0
    if not args.by or not args.note:
        print("\n  REFUSING: --by and --note are both required. An "
              "acceptance with no name and no reason is one nobody can "
              "question later, which is the whole point of recording it.",
              file=sys.stderr)
        return 2

    os.makedirs(PUB, exist_ok=True)
    moved = 0
    for name, cur in PAYLOAD:
        if not os.path.exists(cur):
            continue
        dest = os.path.join(PUB, name)
        data = open(cur, "rb").read()
        if not os.path.exists(dest) or open(dest, "rb").read() != data:
            open(dest, "wb").write(data)
            moved += 1
    hist_pub = os.path.join(PUB, "area_history")
    if os.path.isdir(HIST):
        os.makedirs(hist_pub, exist_ok=True)
        for f in os.listdir(HIST):
            if not f.endswith(".json"):
                continue
            src, dst = os.path.join(HIST, f), os.path.join(hist_pub, f)
            data = open(src, "rb").read()
            if not os.path.exists(dst) or open(dst, "rb").read() != data:
                open(dst, "wb").write(data)
                moved += 1

    log = json.load(open(LOG)) if os.path.exists(LOG) else []
    log.append({
        "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "accepted_by": args.by,
        "note": args.note,
        "held_on": reasons,
        "files_promoted": moved,
    })
    json.dump(log, open(LOG, "w"), indent=1)
    print(f"\n  accepted by {args.by}: promoted {moved} file(s), "
          f"logged to {os.path.relpath(LOG, ROOT)}")
    held_after, _ = gate()
    print("  gate now:", "STILL HOLDING (unexpected)" if held_after
          else "clear, fires publishes on the next run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
