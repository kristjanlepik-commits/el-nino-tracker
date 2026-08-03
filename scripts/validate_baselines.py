#!/usr/bin/env python3
"""Are the fire baseline files parseable before we commit them?

WHY THIS IS A FILE RATHER THAN THREE LINES IN THE WORKFLOW. It was
inline first, and the heredoc broke the YAML twice: a block scalar ends
at the first line indented less than the block, so an embedded script
with lines at column 0 silently truncates the workflow. That is a
particularly bad failure because the file still parses as SOMETHING and
the damage shows up as a missing step rather than an error.

WHAT IT GUARDS. The commit step that calls this runs under
`if: always()`, which means it fires precisely when the previous step
was killed mid-write by its timeout. A JSON file truncated by a kill
would otherwise be committed as fact, and these files are baselines:
every fire multiple on the site is computed against them. A corrupt
baseline does not look corrupt on a page, it looks like a bigger number.

Anything unparseable is reverted to its committed version, or deleted if
it has none, so the next run rebuilds it. Deliberately not fatal: one
bad file should cost that file, not the whole run's work.

Exit 0 always unless the repo itself is unreadable; the caller decides
what a reverted file means.
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    "fires/data/full_history/*.json",
    "fires/data/country_history.json",
]


def main() -> int:
    paths: list[Path] = []
    for pattern in TARGETS:
        paths.extend(Path(p) for p in glob.glob(str(ROOT / pattern)))

    bad = []
    for p in paths:
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bad.append(p)

    if not bad:
        print(f"validated {len(paths)} baseline file(s), all parseable.")
        return 0

    print(f"::error::{len(bad)} baseline file(s) unparseable, most likely a "
          f"write interrupted by a step timeout. Reverting so a corrupt "
          f"baseline is never committed.")
    for p in bad:
        rel = p.relative_to(ROOT)
        print(f"  {rel}")
        restored = subprocess.run(
            ["git", "checkout", "--", str(rel)],
            cwd=ROOT, capture_output=True).returncode == 0
        if not restored:
            p.unlink(missing_ok=True)
            print(f"    no committed version; deleted, next run rebuilds it")
        else:
            print(f"    reverted to the committed version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
