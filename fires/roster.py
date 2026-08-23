#!/usr/bin/env python3
"""Is this country in the fire roster, and under what name?

WHY THIS EXISTS. Three documents in one afternoon on 2026-08-23 pointed
confidently at regions the instrument could not measure, and each was
caught only because somebody happened to ask. Aftereffects found East
Africa OND unbaselined after five weeks at the top of their conviction
ranking; heat found their easternmost mainland station is Vilnius, so
Siberia was absent rather than thin. Their own summary: checking was
nobody's step in all three.

Two of those are a coverage question, which is a check rather than a
habit. This is the check.

NAME MATCHING IS THE HARD PART AND IT IS NOT A DETAIL. The roster holds
"Republic of Serbia", "Macedonia", "United Republic of Tanzania" and
"Democratic Republic of the Congo". A lookup for "Serbia", "North
Macedonia", "Tanzania" or "DR Congo" finds nothing and reads as ABSENT,
which is the same false negative in the opposite direction. I hit this
myself the same day: my own Serbia lookup returned nothing and I briefly
reported that Serbia did not qualify, when it was second in the list.

So an absence reported by this tool means "not under any name I know",
and a name I do not know is a gap in the alias table rather than proof.
That distinction is printed, not implied.

Usage:
    python fires/roster.py Somalia Ethiopia Kenya Sudan "South Sudan"
    python fires/roster.py --list
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEK = os.path.join(ROOT, "fires", "data", "current_week.json")

# Alias -> the roster's own spelling. Lowercased on both sides.
ALIASES = {
    "serbia": "republic of serbia",
    "north macedonia": "macedonia",
    "tanzania": "united republic of tanzania",
    "dr congo": "democratic republic of the congo",
    "drc": "democratic republic of the congo",
    "congo-kinshasa": "democratic republic of the congo",
    "congo": "republic of the congo",
    "congo-brazzaville": "republic of the congo",
    "usa": "united states of america",
    "us": "united states of america",
    "united states": "united states of america",
    "uk": "united kingdom",
    "britain": "united kingdom",
    "great britain": "united kingdom",
    "bosnia": "bosnia and herzegovina",
    "czechia": "czech republic",
    "burma": "myanmar",
    "east timor": "timor-leste",
    "ivory coast": "cote d'ivoire",
    "cape verde": "cabo verde",
    "swaziland": "eswatini",
    "turkey": "turkiye",
}


def roster() -> dict[str, str]:
    """lowercased name -> iso, for every country with a baseline."""
    doc = json.load(open(WEEK))["countries"]
    return {v["name"].lower(): k for k, v in doc.items()}


def resolve(name: str) -> tuple[str | None, str | None]:
    """(iso, canonical_name) or (None, None) if not found under any alias."""
    r = roster()
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key in r:
        iso = r[key]
        return iso, next(n for n in r if r[n] == iso)
    return None, None


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        r = roster()
        print(f"{len(r)} countries have a fire baseline:")
        for n in sorted(r):
            print(f"  {r[n]}  {n}")
        return 0

    absent = []
    for name in args:
        iso, canon = resolve(name)
        if iso:
            print(f"  IN     {name:28} -> {iso} {canon}")
        else:
            print(f"  ABSENT {name:28} -> no baseline")
            absent.append(name)

    if absent:
        print(f"\n  {len(absent)} absent: {', '.join(absent)}")
        print("  A country with no baseline cannot be reported at all, and "
              "building one is roughly 35 minutes of unattended pulling.")
        print("  NOTE: absent means 'not under any name this tool knows'. "
              "If a name looks wrong rather than missing, it is an alias "
              "gap in fires/roster.py, not proof of absence.")
        return 1
    print(f"\n  all {len(args)} present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
