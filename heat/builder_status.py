"""Per-city status from the assembled-city builders, so silence is a signal.

WHY THIS EXISTS. On 2026-09-07 Rome sat frozen at 2026-08-14 for three and a
half weeks while every run reported success: build_bridge read a cached
bulletin file, wrote the same series, and exited 0. Nothing anywhere could
tell that city apart from one that was legitimately finished.

TWO CHECKS WERE BUILT AGAINST THE PAYLOAD AND NEITHER COULD WORK, which is
what this file is the answer to. Both tried to derive "was there work to do"
from the data:

    is the city short          permanently true for Aberdeen and Tallinn,
                               whose sources have genuinely stopped
    did its shortfall grow     out of season the frontier pins to the season
                               end, so a stalled city's shortfall is CONSTANT.
                               Zero growth across the whole Rome incident.

The second is the instructive one: the property used to exclude the permanent
cases is the same property that hides the real ones. **The payload does not
contain the answer. Only the builder knows whether it did any work**, so the
builder has to say.

THE PREDICATE THIS ENABLES is "short, and no builder accounted for it".
Short-and-explained is Tuesday; short-and-unexplained is the fault. It never
asks what the calendar allows, so it is season-independent, and it catches
Rome, which is the only test that matters because Rome is the one incident we
actually have.

TWO PROPERTIES REQUESTED BY PLATFORM, both earned earlier the same day:

    written EVERY run, including when every city is fine. An absent status
    file and a healthy one must not be the same thing. That is the
    withdrawals file defect, fixed this morning, arriving on a new surface.

    a city with NO entry is the fault, not a city with a bad entry. A builder
    that died before writing anything is exactly the Rome case, and a check
    that only reads the entries it finds cannot see the city nobody wrote
    about.

SO IT IS OPENED AT START, NOT WRITTEN AT THE END. Every city a builder intends
to handle is recorded as `attempted` before any work happens, and each is
overwritten as it resolves. A builder that crashes half way leaves `attempted`
rows, which are not an accounted-for outcome and therefore read as the fault
they are. Writing only at the end would mean a crash produced no rows at all
and the run looked like it had nothing to say.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "heat" / "data" / "status"

# The outcomes that ACCOUNT FOR a city. Anything else, including `attempted`,
# including `unchanged`, and including no row at all, is unexplained.
#
# `unchanged` IS DELIBERATELY NOT HERE, and it is the whole Rome case. A
# builder that ran cleanly and produced the same series it already had has
# not accounted for a city being short; it has described exactly the freeze.
# Rome's builder succeeded every run for three and a half weeks while reading
# a cached file, and an "it ran fine" outcome counted as an explanation is
# how that stayed invisible. A city that is short AND unchanged is the fault.
# A city that is not short and unchanged is a finished season, and the
# consumer only asks about short ones.
ACCOUNTED = ("advanced", "held", "refused", "failed")

# What a builder may RECORD, which is a wider set than what ACCOUNTS FOR a
# city. Conflating the two made the validator refuse `unchanged`, the one
# outcome this whole file exists to make visible. Recordable is about honesty;
# accounted-for is about whether a short city has an explanation.
VALID = ACCOUNTED + ("unchanged", "attempted")


def _path(builder):
    return DIR / f"{builder}.json"


def open_status(builder, cities):
    """Record every city this builder intends to handle, before it starts."""
    DIR.mkdir(parents=True, exist_ok=True)
    _path(builder).write_text(json.dumps({
        "builder": builder,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cities": {c: {"status": "attempted", "reason": None} for c in cities},
    }, indent=1) + "\n")


def set_status(builder, city, status, reason=None):
    """Resolve one city. Unknown statuses are refused rather than recorded,
    because a typo would otherwise read as an accounted-for outcome."""
    if status not in VALID:
        raise ValueError(f"{status!r} is not one of {VALID}")
    p = _path(builder)
    doc = json.loads(p.read_text())
    doc["cities"][city] = {"status": status, "reason": reason}
    p.write_text(json.dumps(doc, indent=1) + "\n")


def unexplained(payload_cities, status_dir=None):
    """Cities the builders did not account for this run, for a consumer.

    A city with no row anywhere, or a row that never resolved, is unexplained.
    Cities no builder owns are not this file's business and are excluded by
    the caller passing only the assembled set.

    TAKES A DIRECTORY, because resolving DIR internally made this untestable
    from outside. Platform's check passed a scratch --status-dir, which moved
    only ITS reads while this function went on reading the real one, so a
    healthy fixture reported twelve healthy cities as unexplained. The test
    failed for a reason unrelated to the code under test, and the workaround
    was to reach in and rebind the module global. A function that forces its
    caller to monkeypatch a global to test it is a sharp edge I left.
    """
    d = Path(status_dir) if status_dir else DIR
    seen = {}
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        doc = json.loads(f.read_text())
        for c, v in doc.get("cities", {}).items():
            seen[c] = v.get("status")
    return sorted(c for c in payload_cities
                  if seen.get(c) not in ACCOUNTED)


def builders_seen(status_dir=None):
    """Which builders wrote a status file this run.

    A CONSUMER CANNOT GET THIS FROM unexplained() AND MUST NOT GLOB THIS
    DIRECTORY ITSELF. A builder that dies before open_status leaves its cities
    in no file at all, so a check reading only the rows it finds cannot see
    the city nobody wrote about; that is build_uk and build_london on
    2026-09-07, both dead on a missing import in under a second. The consumer
    compares this against the builder list it already runs, which is the only
    place that list honestly lives. Exposed here so the directory layout stays
    this module's business rather than becoming a second caller's assumption.
    """
    d = Path(status_dir) if status_dir else DIR
    return sorted(f.stem for f in d.glob("*.json")) if d.exists() else []
