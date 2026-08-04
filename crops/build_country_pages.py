"""Write docs/crops/<country>/index.html for every country with a record low.

Thin adapter, same shape as crops/build_page.py and fires builders: it
reads the channel's validated JSON and hands each country to the
template. No science here and no layout here.

Does NOT fetch. crops/pull_asap_indicator.py must never be reachable
from a publish path.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from templates.crops_country import render, slugify, claim_shapes  # noqa: E402

DATA = os.path.join(REPO, "crops", "data", "stress_current.json")
OUTDIR = os.path.join(REPO, "docs", "crops")


def main() -> None:
    with open(DATA) as fh:
        doc = json.load(fh)
    places = doc.get("places") or []
    if not places:
        raise SystemExit("stress_current.json has no places; refusing to build")

    written, shapes = 0, {}
    for p in places:
        lows = [r for r in (p.get("regions") or []) if r.get("rank") == 1]
        if not lows:
            continue
        # Fail loudly rather than drawing an empty chart. The series is
        # the reason this page exists; a region silently missing one
        # would render a blank block that looks like a design choice.
        missing = [r["region"] for r in lows if not r.get("series")]
        if missing:
            raise SystemExit(
                f"{p['place']}: no `series` on {', '.join(missing)}. "
                "Refusing to render a history chart with no history.")
        p = dict(p, dekad=doc.get("dekad", ""))
        out = os.path.join(OUTDIR, slugify(p["place"]))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w") as fh:
            fh.write(render(p))
        written += 1
        for s in claim_shapes(p):
            shapes[(s["statement"], s["driver_line"], s["qualifiers"])] = \
                f"{p['place']} / {s['example']}"

    print(f"wrote {written} country page(s) to docs/crops/")
    print(f"{len(shapes)} distinct claim shape(s) emitted:")
    for (st, drv, q), eg in sorted(shapes.items()):
        print(f"  - {st}\n      driver_line={drv} qualifiers={q}  e.g. {eg}")


if __name__ == "__main__":
    main()
