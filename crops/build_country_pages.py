"""Write docs/crops/<country>/index.html for EVERY published place.

Thin adapter, same shape as crops/build_page.py and fires builders: it
reads the channel's validated JSON and hands each country to the
template. No science here and no layout here.

Does NOT fetch. crops/pull_asap_indicator.py must never be reachable
from a publish path.

WHY EVERY PLACE, changed 2026-08-17 on Kristjan's call. This used to
build only countries with a region at a record low, or pinned ones. That
rule made "is this newsworthy this week" also decide "should this page
exist", and those are different questions.

The consequence was 14 live pages nobody maintained. When a country
stopped qualifying the builder skipped it and last month's file stayed
on disk: India, China, Japan and Russia among them, ten of the fourteen
frozen on the 11 July dekad and still serving it on 17 August. Every one
of them was present in the payload with current data the whole time. And
they were kept out of search only by a `noindex` tag baked into those
stale files, from a template that no longer emits it (D-172), so the
exclusion was an artefact rather than a rule.

Building all 123 removes the category instead of managing it. There is
no qualifying set to remember, no unmaintained remainder, and a page
that exists is current by construction. A calm country renders the calm
case, which the template already did for the pinned European set.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from templates.crops_country import render, slugify, claim_shapes  # noqa: E402
from templates.crops_index import PINNED, PINNED_REGIONS  # noqa: E402

PINNED_PLACES = set(PINNED) | {c for c, _ in PINNED_REGIONS}

DATA = os.path.join(REPO, "crops", "data", "stress_current.json")
OUTDIR = os.path.join(REPO, "docs", "crops")


def main() -> None:
    with open(DATA) as fh:
        doc = json.load(fh)
    places = doc.get("places") or []
    if not places:
        raise SystemExit("stress_current.json has no places; refusing to build")

    # WHICH URLS EXISTED BEFORE THIS RUN.
    #
    # A refresh of existing pages and a change to the SET of pages are
    # different acts with different sign-offs (D-030, and the seam
    # product ratified 2026-08-18): a refresh runs silently, a change to
    # which pages exist needs design's eyes because it is their surface.
    #
    # The test is not "did I touch the template", which is a judgement
    # made by the person with the least incentive to say no, at the end
    # of a long session. I made exactly that call tonight and published
    # 123 pages, 66 of them new, on my own sign-off. The test is whether
    # the set of URLs changed, and this knows the answer.
    #
    # Announces rather than blocks. Blocking a build on a shared tree
    # would strand other chats, and the acknowledgement belongs at the
    # publish step where platform's guard sits, not here.
    before = {d for d in os.listdir(OUTDIR)
              if os.path.isdir(os.path.join(OUTDIR, d))} \
        if os.path.isdir(OUTDIR) else set()

    written, shapes, slugs = 0, {}, set()
    for p in places:
        # A page is built when the country has a region at a record low
        # OR when it is PINNED on the index. Pinned countries are shown
        # every week whether or not anything is happening in them, which
        # is the whole point of pinning, so by definition they need not
        # have a record low. Without this the index names seven European
        # countries that have nowhere to click, and the dead-link guard
        # correctly refuses to link them.
        #
        # PINNED is imported rather than duplicated: two lists that can
        # disagree about which countries are pinned is exactly the class
        # of defect this channel keeps finding.
        lows = [r for r in (p.get("regions") or []) if r.get("rank") == 1]
        # Fail loudly rather than drawing an empty chart. The series is
        # the reason this page exists; a region silently missing one
        # would render a blank block that looks like a design choice.
        missing = [r["region"] for r in lows if not r.get("series")]
        if missing:
            raise SystemExit(
                f"{p['place']}: no `series` on {', '.join(missing)}. "
                "Refusing to render a history chart with no history.")
        # The instrument legend and the absence glosses are DOC-level and
        # the template renders a place, so they ride along rather than
        # being re-typed in the template. Names and reasons then come from
        # CRO's payload, and a sixth instrument arrives named instead of as
        # a bare key.
        p = dict(p, dekad=doc.get("dekad", ""),
                 _instrument_legend=doc.get("instrument_legend") or {},
                 # D-182: the row order is DATA, not a renderer's choice.
                 _instrument_order=(doc.get("instrument_order") or {}).get("order") or [],
                 _absence_reasons=doc.get("absence_reasons") or {})
        slug = slugify(p["place"])
        slugs.add(slug)
        out = os.path.join(OUTDIR, slug)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w") as fh:
            fh.write(render(p))
        written += 1
        for s in claim_shapes(p):
            shapes[(s["statement"], s["driver_line"], s["qualifiers"])] = \
                f"{p['place']} / {s['example']}"

    print(f"wrote {written} country page(s) to docs/crops/")

    added = sorted(slugs - before)
    gone = sorted(d for d in before - slugs if d != "index.html")
    if added or gone:
        print()
        print("  THE SET OF URLS CHANGED. This is not a refresh.")
        if added:
            print(f"  +{len(added)} new page(s): "
                  f"{', '.join(added[:8])}"
                  + (f" ... and {len(added) - 8} more" if len(added) > 8
                     else ""))
        if gone:
            print(f"  -{len(gone)} page(s) no longer built, and their files "
                  f"are STILL ON DISK serving stale data: "
                  f"{', '.join(gone[:8])}"
                  + (f" ... and {len(gone) - 8} more" if len(gone) > 8
                     else ""))
        print("  docs/crops/ is design's surface (D-030). A refresh of "
              "existing pages is crops' to publish; a change to WHICH "
              "pages exist gets design's eyes first.")
    else:
        print("  URL set unchanged: this is a refresh, crops' to publish.")
    print(f"{len(shapes)} distinct claim shape(s) emitted:")
    for (st, drv, q), eg in sorted(shapes.items()):
        print(f"  - {st}\n      driver_line={drv} qualifiers={q}  e.g. {eg}")


if __name__ == "__main__":
    main()
