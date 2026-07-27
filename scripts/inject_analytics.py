#!/usr/bin/env python3
"""Add the analytics snippet to already-published rolling pages.

Why this exists: the snippet lives in run_brief.py, so it only reaches
a page when that page is next built. The launch happens before the next
weekly run, which would leave the launch spike, the one traffic event
that cannot be reconstructed later, entirely unmeasured.

Scope, deliberately narrow:

  * It edits only ROLLING surfaces, pages that every weekly run
    rewrites anyway (the front page, the methodology overview, the
    archive listing). Nothing here is a published claim; the edit adds
    a script tag and changes no number, sentence, or link.
  * It REFUSES to touch a dated archive under docs/briefs/YYYY-MM-DD/.
    Those are immutable (CLAUDE.md invariant 5) and no analytics need
    justifies rewriting them. Frozen archives therefore stay untagged;
    measuring them would need edge analytics instead.

It is idempotent: a page that already carries the snippet is skipped,
so re-running after a weekly build is safe and does nothing.

Usage:
  scripts/inject_analytics.py            report what would change
  scripts/inject_analytics.py --write    apply
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_brief import ANALYTICS_SNIPPET, ANALYTICS_SITE_ID  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Rolling pages only. Add to this list, never a dated archive path.
TARGETS = [
    DOCS / "index.html",
    DOCS / "methodology.html",
    DOCS / "briefs" / "index.html",
]

ARCHIVE_RE = re.compile(r"docs/briefs/\d{4}-\d{2}-\d{2}/")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="apply the edit")
    args = ap.parse_args()

    changed, skipped, missing = [], [], []

    for path in TARGETS:
        rel = path.relative_to(ROOT).as_posix()
        if ARCHIVE_RE.search(rel):
            print(f"REFUSED (immutable archive): {rel}")
            return 1
        if not path.is_file():
            missing.append(rel)
            continue
        html = path.read_text(encoding="utf-8")
        if ANALYTICS_SITE_ID in html:
            skipped.append(rel)
            continue
        if "</head>" not in html:
            print(f"REFUSED (no </head> to anchor to): {rel}")
            return 1
        # Insert immediately before the first </head>, touching nothing else.
        new_html = html.replace("</head>", f"{ANALYTICS_SNIPPET}\n</head>", 1)
        if args.write:
            path.write_text(new_html, encoding="utf-8")
        changed.append(rel)

    verb = "tagged" if args.write else "would tag"
    for rel in changed:
        print(f"{verb}: {rel}")
    for rel in skipped:
        print(f"already tagged, skipped: {rel}")
    for rel in missing:
        print(f"not present, skipped: {rel}")

    if not args.write and changed:
        print("\nDry run. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
