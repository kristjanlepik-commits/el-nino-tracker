#!/usr/bin/env python3
"""Announce a fires publish hold where a person will see it.

WHY THIS EXISTS. On 2026-08-23 the overnight pull worked perfectly and
the site served a week-old page anyway. refresh_gate held for seven real
editorial changes, exactly as D-212 intends, and printed them into a CI
log that reports success. Nothing told anyone. CLAUDE.md already says of
the sign-off gate: "It will not find you; you have to look." That is a
description of a defect, not a design.

A hold is CORRECT behaviour. The defect is that a correct hold is
indistinguishable from a healthy run, which is the same shape as the
D-200 gate blocking fires for two days, and as a missing crop mask
silently dropping a field from 82 countries. The channel keeps
rediscovering that safe and silent are different things.

WHAT IT DOES. Runs the gate, and keeps exactly one GitHub issue in sync
with it:

    held  and no open issue   ->  open one, with the reasons
    held  and an open issue   ->  update it if the reasons changed
    clear and an open issue   ->  close it, because the hold is resolved

An issue rather than a log line because it survives a run, a context and
a chat, and because `gh issue list` is somewhere a person already looks.
Idempotent on purpose: a daily job that re-opens or re-comments every
morning teaches people to ignore it, which is how a notification becomes
noise and then becomes nothing.

Usage:
    python fires/notify_hold.py            # act
    python fires/notify_hold.py --dry-run  # print what it would do
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "kristjanlepik-commits/tls-internal"
MARKER = "<!-- fires-publish-hold -->"
TITLE = "fires: publish held by the refresh gate, pages are stale until reviewed"


def gate() -> tuple[bool, str]:
    """(held, output). Exit 1 means held; 0 means clear."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, "fires",
                                                     "refresh_gate.py")],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode != 0, (r.stdout or "") + (r.stderr or "")


def find_issue() -> dict | None:
    r = subprocess.run(
        ["gh", "issue", "list", "-R", REPO, "--state", "open",
         "--search", TITLE, "--json", "number,body", "--limit", "20"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return None
    for item in json.loads(r.stdout or "[]"):
        if MARKER in (item.get("body") or ""):
            return item
    return None


def body_for(output: str) -> str:
    reasons = [l.strip() for l in output.splitlines()
               if l.strip().startswith("- ")]
    head = next((l.strip() for l in output.splitlines()
                 if "HOLD:" in l), "held")
    return (f"{MARKER}\n"
            f"`fires/refresh_gate.py` is holding the publish, so "
            f"`publish_all.py` is not rebuilding the fires pages and the "
            f"live site keeps serving the last approved week.\n\n"
            f"**{head}**\n\n"
            + "\n".join(reasons) + "\n\n"
            f"This is the gate working. It holds only when a CLAIM moves: "
            f"a record appearing or being withdrawn, a country entering or "
            f"leaving the qualifying set, a weekly rank crossing first "
            f"place. Someone from the Fire chat has to look at the changes "
            f"above and decide, and the pages stay stale until they do.\n\n"
            f"This issue closes itself once the gate clears.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    held, output = gate()
    issue = find_issue()

    if held:
        body = body_for(output)
        if issue and (issue.get("body") or "").strip() == body.strip():
            print("  held; issue already open and current, nothing to do")
            return 0
        if args.dry_run:
            print(f"  would {'update' if issue else 'open'} an issue:\n{body}")
            return 0
        if issue:
            subprocess.run(["gh", "issue", "edit", str(issue["number"]),
                            "-R", REPO, "--body", body], check=True)
            print(f"  held; updated issue #{issue['number']}")
        else:
            r = subprocess.run(["gh", "issue", "create", "-R", REPO,
                                "--title", TITLE, "--body", body],
                               capture_output=True, text=True, check=True)
            print(f"  held; opened {r.stdout.strip()}")
        return 0

    if issue:
        if args.dry_run:
            print(f"  would close issue #{issue['number']}")
            return 0
        subprocess.run(["gh", "issue", "close", str(issue["number"]),
                        "-R", REPO, "--comment",
                        "Gate cleared, fires pages rebuild normally again."],
                       check=True)
        print(f"  clear; closed issue #{issue['number']}")
    else:
        print("  clear; nothing held")
    return 0


if __name__ == "__main__":
    sys.exit(main())
