#!/usr/bin/env python3
"""Derive a channel's real render inputs by running its builders.

PROPOSAL for platform (scripts/ is theirs). Lives here so it can be read
as code rather than pasted into a message. Move it wherever it belongs.

WHY THIS EXISTS. SIGNOFF_INPUTS and refresh_gate both read from a
hand-maintained list, and that list has now been wrong three times on one
channel: templates/eu_area_chart.py, fires/data/eu_area.json, and the 26
fires/data/area_history/<ISO>.json files that compute the previous-record
sentence on every country page. None of those were carelessness. Each was
one level of indirection away from anything a reader of the builder would
see, so the method produced the omission rather than the person.

TWO TRAPS, both of which this hits and a naive version misses.

1. IMPORTS DO NOT GO THROUGH open(). A trace that only wraps builtins.open
   sees every .json and no .py, so it misses every template, which is the
   half most likely to change a claim. sys.modules is walked separately.

2. A BUILDER THAT DOES NOT RUN LOOKS LIKE A BUILDER WITH NO INPUTS. If the
   run raises before it reads anything, the derived set is empty and that
   is indistinguishable from success. So the run's exit is checked and an
   implausibly small result is an error, not an answer.

Usage:
    python fires/derive_inputs.py fires/build_page.py fires/build_country_pages.py
    python fires/derive_inputs.py --compare fires <builders...>

--compare diffs the derived set against what scripts/publish_all.py
currently protects for that channel and exits 1 if anything real is
unprotected, so it can run in CI as a guard rather than a one-off audit.
"""
from __future__ import annotations

import builtins
import json
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Written, not read: an output is not an input. docs/ is the render target.
IGNORE_PREFIXES = (".git", ".venv", "docs/", ".fetch_cache", "__pycache__")
# Below this, assume the builders did not really run. See trap 2.
MIN_PLAUSIBLE = 5


def _rel(path: str) -> str | None:
    try:
        p = os.path.abspath(str(path))
    except (TypeError, ValueError):
        return None
    if not p.startswith(ROOT):
        return None
    rel = os.path.relpath(p, ROOT)
    if rel.startswith(IGNORE_PREFIXES):
        return None
    return rel


def derive(builders: list[str]) -> set[str]:
    opened: set[str] = set()
    real_open = builtins.open

    def tracking_open(file, mode="r", *a, **kw):
        if "w" not in str(mode) and "a" not in str(mode):
            rel = _rel(file)
            if rel:
                opened.add(rel)
        return real_open(file, mode, *a, **kw)

    builtins.open = tracking_open
    sys.path.insert(0, ROOT)
    try:
        for script in builders:
            sys.argv = [script]
            try:
                runpy.run_path(script, run_name="__main__")
            except SystemExit as exc:
                if exc.code not in (0, None):
                    raise SystemExit(
                        f"REFUSING: {script} exited {exc.code}. A builder that "
                        f"did not complete yields an input set that looks "
                        f"small rather than wrong.")
    finally:
        builtins.open = real_open

    # Imports bypass open(). See trap 1.
    for mod in list(sys.modules.values()):
        rel = _rel(getattr(mod, "__file__", "") or "")
        if rel and rel.endswith(".py"):
            opened.add(rel)

    if len(opened) < MIN_PLAUSIBLE:
        raise SystemExit(
            f"REFUSING: derived only {len(opened)} input(s). That is a "
            f"builder that did not read anything, not a channel with no "
            f"inputs.")
    return opened


def main() -> int:
    args = sys.argv[1:]
    channel = None
    if args and args[0] == "--compare":
        channel, args = args[1], args[2:]
    if not args:
        raise SystemExit(__doc__)

    derived = derive(args)

    if not channel:
        for f in sorted(derived):
            print(f)
        return 0

    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from publish_all import SIGNOFF_INPUTS  # noqa: E402
    protected = set(SIGNOFF_INPUTS.get(channel, ()))
    try:
        import importlib
        gate = importlib.import_module(f"{channel}.refresh_gate")
        for name in dir(gate):
            val = getattr(gate, name)
            if isinstance(val, (str, os.PathLike)):
                rel = _rel(val)
                if rel:
                    protected.add(rel)
    except Exception:
        pass

    # A protected DIRECTORY covers the files beneath it. refresh_gate
    # names fires/data/area_history as one Path and compares all 94 files
    # under it; comparing file-by-file against that would report a
    # working guard as a hole.
    dirs = {d for d in protected if not os.path.splitext(d)[1]}

    def covered(f: str) -> bool:
        return f in protected or any(
            f.startswith(d.rstrip("/") + "/") for d in dirs)

    unprotected = sorted(f for f in derived
                         if f.endswith((".json", ".py", ".csv", ".svg"))
                         and not covered(f))
    print(f"derived {len(derived)} input(s), {len(protected)} protected")
    if unprotected:
        print(f"\nUNPROTECTED ({len(unprotected)}):")
        for f in unprotected:
            print("   ", f)
        return 1
    print("nothing unprotected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
