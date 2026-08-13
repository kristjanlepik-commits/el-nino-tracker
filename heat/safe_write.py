"""One safe way to write a source-cache series, because there were nine.

WHY. On 2026-08-13 build_uk.py wrote its output file before checking that the
MIDAS fetch had returned anything. The CEDA token had expired, the fetch came
back empty, and Nottingham's cache went from 69 years to 222 rows of 2026
alone. The crash arrived one line later, so the traceback described a
reporting bug while the record was already gone. These caches are gitignored,
so there is no revert: the only copy was the one being overwritten.

I first guarded that single call site. Crops pointed out that this is not a
heat problem and not a build_uk problem. Every fetcher here writes the same
way, so every fetcher has the same exposure, and the fix is the one their
puller already uses: write somewhere else, check, then rename.

WHAT THIS REFUSES, and why it is two rules rather than one.

    EMPTY          A series with no rows is always a fetch failure and never
                   a fact about a station. Stations do not stop having had a
                   history.
    SHRINKAGE      A series shorter than the one on disk means the new pull
                   saw less than the last one did. Archives grow. When one
                   appears to shrink, the pull is wrong far more often than
                   the archive is, so the burden of proof sits on the new
                   file rather than on the old one.

Shrinkage is the rule that would have caught Nottingham, and it is the one I
would not have written on my own, because the empty case is the one that had
just bitten me. 222 rows is not empty. It is 0.8% of 28,000 and it would have
sailed through a check for emptiness.

WHAT THIS CANNOT SEE, recorded so nobody mistakes it for coverage. It compares
the new file against the OLD FILE, so it catches a pull that got less than
last time. It is blind to a pull that succeeds and returns stale data, because
yesterday's complete file is neither empty nor shorter. Catching that needs an
absolute check against what the source says it has published, which is a
different guard that does not exist here yet. Crops built theirs only after
ratifying a staleness rule nobody had a field to measure; ours is the same
gap, currently unfilled.

    this guard   do my inputs agree with what I held before?
    the other    do my inputs agree with the world?

Neither substitutes for the other.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


class RefusedWrite(Exception):
    """Raised instead of destroying a good file."""


def write_series(path, rows, *, label=None, allow_shrink=False,
                 shrink_tolerance=0.0):
    """Write `rows` to `path` atomically, refusing an empty or shorter series.

    `shrink_tolerance` is the fraction of rows a series may legitimately lose,
    for the archives that revise downward. It defaults to zero: a caller that
    genuinely expects to lose rows says so at its own call site, where the
    reason can be written down, rather than here where it would apply to
    everything.

    The write goes to a sibling `.partial` and is renamed only after it lands.
    os.replace is atomic within a filesystem, so a kill mid-write leaves the
    previous file whole rather than a half-written one that parses.
    """
    path = Path(path)
    name = label or path.name
    if not rows:
        raise RefusedWrite(
            f"{name}: refusing to write an empty series. An empty result is a "
            f"fetch failure, not a station without a history. {path.name} is "
            f"unchanged.")

    if path.exists():
        try:
            old = len(json.loads(path.read_text()))
        except (ValueError, OSError):
            old = 0
        floor = old * (1 - shrink_tolerance)
        if old and len(rows) < floor and not allow_shrink:
            raise RefusedWrite(
                f"{name}: refusing to shrink {path.name} from {old} rows to "
                f"{len(rows)}. Archives grow; a pull that sees less than the "
                f"last one is usually the broken half. Nothing written. Pass "
                f"allow_shrink=True at the call site if the loss is real, and "
                f"say there why.")

    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(rows))
    os.replace(tmp, path)
    return len(rows)
