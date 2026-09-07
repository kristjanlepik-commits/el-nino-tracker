#!/usr/bin/env python3
"""Did every assembled city get accounted for by the builder that owns it?

    python scripts/check_heat_accounted.py [--builders a,b,c]

Exit 0 when every assembled city has a resolved status and every expected
builder wrote one. Exit 1 otherwise, naming what was not accounted for.

WHY SILENCE IS THE SIGNAL. On 2026-09-07 three separate bugs each froze a
set of cities and all three reported success. Rome sat at 2026-08-14 for
three and a half weeks while build_bridge completed cleanly every run,
reading a cached file. Nothing was short-and-broken in a way any check
could see; it was short-and-nobody-said-anything, and every mechanism
that looked at it reported on itself rather than on whether the date
moved.

TWO EARLIER VERSIONS OF THIS CHECK FAILED, and the way they failed is
why this one asks the builders instead of the data.

    "is any city short"        Aberdeen and Tallinn are permanently short
                               for reasons that never resolve, so the
                               predicate is permanently true and collapses
                               to "nothing moved". Fires every quiet week.

    "did a shortfall GROW"     Out of season the frontier pins to the
                               season end, so a stalled city's shortfall
                               is CONSTANT. Measured against the real
                               incident: Rome 17 days short on 1 Sep and
                               17 days short on 7 Sep, zero growth across
                               the entire freeze. Silent on the one case
                               we have, and silent for eight months a
                               year, which is the false-assurance shape
                               rather than the never-fires one.

Both were attempts to derive "was there work to do" from the payload. The
payload does not contain that. Only the builder knows whether it fetched,
held, refused or quietly read a cache, so this asks the builder.

`unchanged` IS NOT ACCOUNTED FOR, which is the property that catches
Rome. A builder that runs cleanly and produces the same series has not
explained anything, it has described the freeze. heat/builder_status.py
draws that line: advanced, held, refused and failed account for a city;
unchanged, attempted, and no row at all do not.

A MISSING STATUS FILE IS ITSELF THE FAULT, and this is the hole that
status rows alone cannot cover. A builder that dies before opening its
status writes nothing, so its cities appear in no file and a check that
only reads the rows it finds cannot see the cities nobody wrote about.
That is not hypothetical: build_uk and build_london died on
ModuleNotFoundError this morning, before any status existed. So the
expected builder list is checked, not discovered.

WHY THE BUILDER LIST LIVES HERE RATHER THAN BEING DISCOVERED. It is the
same four names heat_refresh.yml's builder step already runs, in a file
that already owns that list and has to keep it in step. Discovering it
from whatever files happen to exist is precisely the failure above.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "heat"))

# The builders heat_refresh.yml's "Refresh the assembled cities" step runs.
# Keep in step with that loop; they are the same list and a drift between
# them is a builder whose silence nobody notices.
BUILDERS = ("build_uk", "build_london", "build_bridge", "build_argentina")

STATUS_DIR = ROOT / "heat" / "data" / "status"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--builders", default=",".join(BUILDERS))
    ap.add_argument("--status-dir", default=str(STATUS_DIR))
    args = ap.parse_args()

    expected = [b for b in args.builders.split(",") if b]
    sdir = Path(args.status_dir)

    # Both readers take the directory now. Heat changed the interface
    # rather than let me keep the workaround: the first version of this
    # rebound their module global to test it, and a function that makes
    # its caller do that is a defect in the interface rather than in the
    # caller. builders_seen exists for the same reason, so this does not
    # glob their directory and make their layout my assumption.
    import builder_status as BS  # noqa: E402

    seen = set(BS.builders_seen(status_dir=sdir))
    missing_files = [b for b in expected if b not in seen]

    # The assembled set is the union of what the builders that DID write
    # say they own. A builder with no file contributes no cities, which is
    # exactly why its absence is reported separately above rather than
    # being silently absorbed into an empty set.
    owned: set[str] = set()
    for b in expected:
        f = sdir / f"{b}.json"
        if not f.exists():
            continue
        try:
            owned |= set(json.loads(f.read_text()).get("cities", {}))
        except ValueError:
            missing_files.append(f"{b} (unreadable)")

    stranded = BS.unexplained(sorted(owned), status_dir=sdir) if owned else []

    if not missing_files and not stranded:
        print(f"  all {len(owned)} assembled cities accounted for by "
              f"{len(expected)} builders. Nothing unexplained.")
        return 0

    if missing_files:
        print(f"::error::{len(missing_files)} builder(s) wrote no status at "
              f"all: {', '.join(missing_files)}. A builder that dies before "
              f"opening its status leaves its cities in no file, so they "
              f"cannot be reported as unexplained by name. This is that "
              f"case: check whether the builder failed to import or crashed "
              f"before starting.")
    if stranded:
        print(f"::error::{len(stranded)} city/cities were not accounted for: "
              f"{', '.join(stranded)}. Their builder neither advanced them "
              f"nor said why. A city whose data did not move and whose "
              f"builder reported nothing is the freeze this check exists "
              f"for: build_bridge completed cleanly for three and a half "
              f"weeks while Rome sat at 2026-08-14.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
