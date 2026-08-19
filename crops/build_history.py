"""Emit regions_at_record for the last N dekads as COMMITTED data.

WHY THIS EXISTS. Product asked for it and the reason is provenance
rather than convenience. Socials built a four-dekad UK series showing
temperature at a record on 1 July and released by 21 July, with the
canopy reaching its record three weeks behind and staying there. That is
the best thing produced about this channel, and it derived from
`crops/.cache/`, which is gitignored. So it existed on one laptop and in
no commit: nobody else could reproduce it and clearing the cache would
have destroyed it. Same shape as the London MIDAS baseline that turned
out to live in a release rather than the repo.

`stress_current.json` carries exactly one dekad by design. This carries
the counts back through the season so the series is reusable by country
pages and the weekly Note instead of living in a scratch script.

WHAT IT IS NOT. Not a second copy of the payload. Only the per-instrument
"N of M regions at their own record" counts, which is 3 KB gzipped per
dekad, so a full year to date is well under 100 KB in its own file and
touches the stress_current budget not at all.

Socials' validation harness should survive as the CHECK on this rather
than as the source: it recomputes a published dekad and asserts equality
against all of that country's region ranks, failing rather than
disagreeing quietly. That is the right relationship. This file becomes
the thing under test.

Does NOT fetch. Reads only crops/.cache/, same as build_data.py.
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from crops.build_data import (  # noqa: E402
    BASE_FIRST, BASE_LAST, CACHE, INSTRUMENTS, MIN_UNITS, load, rank_of,
)

OUT = os.path.join(HERE, "data", "regions_at_record_history.json")
# 36 is one full year of dekads, and doys do not wrap, so this always
# reaches doy 1 whatever the anchor. The window is therefore the WHOLE
# CALENDAR YEAR TO DATE rather than a number somebody picked, which is
# the point: trap 21 is that a chosen window can manufacture the
# sequence it appears to reveal, and the fix is to stop choosing.
DEKADS_BACK = 36


def main() -> None:
    cat = json.load(open(os.path.join(HERE, "asap_countries.json")))["countries"]
    cur = json.load(open(os.path.join(HERE, "data", "stress_current.json")))
    cur_dekad = cur["dekad"]
    # Anchor on the published dekad rather than on today, so the newest
    # column in here is always the column stress_current.json describes.
    # Anchoring on the clock would let the two disagree the moment a
    # refresh lands, and a history whose head is not the published dekad
    # is the mixed-vintage defect one file along.
    anchor = pd.Timestamp(cur_dekad)
    anchor_doy = (anchor.month - 1) * 3 + ((anchor.day - 1) // 10) + 1
    anchor_year = anchor.year

    doys = [anchor_doy - k for k in range(DEKADS_BACK)]
    doys = [d for d in doys if d >= 1]

    labels = {s: lab for s, lab, _u, _w in INSTRUMENTS}
    loaded = {}
    for slug, _lab, _u, _w in INSTRUMENTS:
        loaded[slug] = {}

    out = {
        "_what": "regions_at_record, per instrument, per dekad. `at_record` "
                 "is how many of a country's crop regions are at their own "
                 "worst on record for that point in the season; `of` is how "
                 "many reported that instrument, which is why it varies.",
        "_basis": f"each region against its own {BASE_FIRST}-{BASE_LAST} "
                  f"record at the SAME dekad-of-year",
        "_head_is": cur_dekad,
        "_head_matches": "the dekad in stress_current.json, by construction. "
                         "Anchored on the published dekad rather than on the "
                         "clock so the two cannot drift apart.",
        "_authorship": "tls_built",
        "_evidence_basis": "measured",
        # A WINDOW CAN MANUFACTURE THE SEQUENCE IT APPEARS TO REVEAL.
        #
        # Socials built a four-dekad UK card headlined "the four
        # instruments peak weeks apart", opening "temperature stands at a
        # record on 1 July". Against a longer series temperature was at
        # all four regions on 21 May and again on 21 June. Inside their
        # four dekads it only declines, so the tail of a fall was
        # presented as a starting peak, and the spread was "weeks" rather
        # than the two months it is.
        #
        # Worse for any causal reading: temperature has TWO spikes with
        # 0 of 4 between them. There is no single peak for anything to be
        # sequenced against, which removes the thing a propagation story
        # hangs on rather than declining to explain it.
        #
        # SO THIS FILE STOPPED CHOOSING. It was twelve dekads, which was
        # a pick, and it opened on a quiet column for the UK by luck. It
        # is now every dekad of the calendar year to the published one,
        # so no within-year peak can fall outside it. The remaining edge
        # is the year boundary, which is stated rather than hidden.
        "_window": {
            "dekads": DEKADS_BACK,
            "ends_at": cur_dekad,
            "is_derived_not_picked": "every dekad of this calendar year "
                                     "up to the published one. Not a "
                                     "window somebody chose, so a "
                                     "within-year peak cannot fall "
                                     "outside it. It was 12 dekads and "
                                     "that WAS a choice.",
            "still_bounded_at_the_left": "the year boundary. A season "
                                         "that began in the previous "
                                         "calendar year is cut, so for "
                                         "southern-hemisphere crops the "
                                         "first column can still be "
                                         "mid-story. Check it.",
            "before_inferring_order": "check the FIRST column. If an "
                                      "instrument is already elevated "
                                      "there, its peak may precede this "
                                      "file and any 'X moved before Y' "
                                      "read from these columns is "
                                      "unsupported.",
            "not": "evidence of sequence or of cause. `driver` in "
                   "stress_current.json is unidentified for most places, "
                   "including the UK and each of its four regions.",
        },
        "dekads": {},
        "places": {},
    }

    # date label for each doy, in the anchor year
    def label_for(doy: int) -> str:
        month = (doy - 1) // 3 + 1
        day = ((doy - 1) % 3) * 10 + 1
        return f"{anchor_year:04d}-{month:02d}-{day:02d}"

    for doy in sorted(doys):
        out["dekads"][label_for(doy)] = doy

    for cid, name in cat.items():
        base = load("zfparc", cid)
        if base is None or base.empty:
            continue
        if base.region_id.nunique() < MIN_UNITS:
            continue
        per_dekad = {}
        others = {s: load(s, cid) for s, _l, _u, _w in INSTRUMENTS
                  if s != "zfparc"}
        for doy in sorted(doys):
            row = {}
            # Every instrument including the spine, and worse_is comes
            # from INSTRUMENTS rather than being assumed. Temperature is
            # worse-when-high and the rest are worse-when-low; hardcoding
            # a direction here is how 8,417 region statements once got
            # inverted on one instrument.
            frames = []
            for slug, _lab, _u, worse_is in INSTRUMENTS:
                d = base if slug == "zfparc" else others.get(slug)
                frames.append((slug, d, worse_is))
            for slug, d, worse_is in frames:
                if d is None or d.empty:
                    continue
                sub = d[d.doy == doy]
                if sub.empty:
                    continue
                at, of = 0, 0
                for reg, grp in sub.groupby("region_name"):
                    ser = grp.groupby("year").value.mean()
                    hist = ser[(ser.index >= BASE_FIRST)
                               & (ser.index <= BASE_LAST)]
                    if anchor_year not in ser.index or len(hist) < 20:
                        continue
                    of += 1
                    if rank_of(float(ser[anchor_year]), hist, worse_is) == 1:
                        at += 1
                if of:
                    row[slug] = {"label": labels.get(slug, slug),
                                 "at_record": at, "of": of}
            if row:
                per_dekad[label_for(doy)] = row
        # COVERAGE, so a renderer can tell "most of the country" from
        # "most of what reported".
        #
        # `of` is per instrument PER DEKAD, not a property of the
        # country, because the crop-growing class stops reporting a
        # region once its cycle closes. So Oman reads 1 of 1 in late
        # season where it normally covers 7, and Mongolia 1 of 1 in
        # January against a usual 18.
        #
        # A fraction computed on a collapsed denominator is a statement
        # about coverage wearing the clothes of a statement about
        # extent, and design's five-band grid would paint those cells
        # the DARKEST shade. 23 of the 33 cells that would have entered
        # the top band on n=1 are this, not small countries.
        #
        # `of_max` is that instrument's fullest coverage for this place
        # across the window, so `of / of_max` says how much of the
        # country was even being measured.
        for slug in {k for row in per_dekad.values() for k in row}:
            of_max = max(r[slug]["of"] for r in per_dekad.values()
                         if slug in r)
            for r in per_dekad.values():
                if slug in r:
                    r[slug]["of_max"] = of_max
        if per_dekad:
            out["places"][name] = per_dekad

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
    n_d = len(out["dekads"])
    print(f"regions_at_record_history.json: {len(out['places'])} places, "
          f"{n_d} dekads, head {cur_dekad}")


if __name__ == "__main__":
    main()
