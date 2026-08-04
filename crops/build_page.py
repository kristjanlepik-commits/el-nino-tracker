"""Render the Crops channel home page, docs/crops/index.html.

A thin adapter, exactly like fires/build_page.py: it reads the channel's
validated JSON and hands it to the template. All layout lives in
templates/crops_index.py, all science lives in crops/. This file holds
neither, and that is the point of it under D-030.

It does NOT fetch. The dekadal pull is crops/pull_asap_indicator.py and
it must never be called from here, for the same reason
fires/build_events.py is barred from scripts/publish_all.py: a publish
step that can reach the network can change the numbers on a page while
appearing only to re-render it.

Reads crops/data/stress_current.json, which build_data.py generates.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# templates/, tokens.py and run_brief.py all resolve from the repo root.
# Insert before importing, so `python crops/build_page.py` works from a
# plain checkout with no PYTHONPATH incantation.
sys.path.insert(0, REPO)

from templates.crops_index import render  # noqa: E402

DATA = os.path.join(REPO, "crops", "data", "stress_current.json")
OUT = os.path.join(REPO, "docs", "crops", "index.html")


def main():
    with open(DATA) as fh:
        doc = json.load(fh)

    # Fail loudly on an empty payload rather than publishing a page with
    # no places on it. An empty crops index is indistinguishable from a
    # quiet dekad to a reader, and the two mean opposite things.
    places = doc.get("places") or []
    if not places:
        raise SystemExit(
            "crops/data/stress_current.json has no places. Refusing to "
            "write an empty index: a page with nothing on it reads as a "
            "calm dekad rather than as a missing file.")

    html = render(doc, root_prefix="../")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(html)
    print(f"wrote {os.path.relpath(OUT, REPO)} "
          f"({len(places)} places, dekad {doc.get('dekad')})")


if __name__ == "__main__":
    main()
