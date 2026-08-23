"""Decide whether a fires payload refresh may publish itself or needs a human.

D-212. Supersedes the D-200 byte-hash for fires' PAYLOAD only; the template
files (fires/build_page.py, fires/build_country_pages.py,
templates/country_page.py) stay on D-200's hash in signoff/fires.json,
trimmed to just those three, because "template change: always hold" is a
different rule from this one and needs no classification.

WHY THE BYTE HASH HAD TO GO FOR PAYLOAD. D-200 held fires on any byte
difference in fires/data/current_week.json, data/events.json and
fires/data/burnt_area.json, all three touched by the daily data job (30+
commits each since 1 August). Measured cost: approved 20 August at 3,175 ha
for Belgium; GWIS revised to 3,208 on the 21st, the hash moved, the channel
blocked, and the site kept serving 3,175 for two days with every automated
check green, corrected only when Fire published by hand. THE GATE PRODUCED
THE EXACT HARM IT EXISTS TO PREVENT: the correct number was in our data on
the 21st and the gate kept the wrong one live.

Same shape as heat/refresh_gate.py, same reason: a byte is not a claim. A
revised magnitude inside an unchanged claim (3,175 to 3,208, still above
Belgium's own record) should pass. A record appearing, a record withdrawn,
a country entering or leaving the qualifying set, or a country's weekly
rank crossing into or out of 1st should not.

WHY IT COMPARES PAYLOADS RATHER THAN RECOMPUTING. Same as heat: the
previously PUBLISHED payload is the only external reference for what a
reader last saw. Deriving "what changed" from the new data alone would be
comparing the artifact under test to itself.

THE TIMESTAMP FIX IS STRUCTURAL, NOT A SPECIAL CASE. Fire found the second
data-job run of most days rewrites burnt_area.json's top-level "fetched"
field and nothing else (2 changed lines against 400+ on a real-revision
run), which alone tripped the old byte hash. This gate never reads
"fetched" at all: it only ever looks at named claim fields inside
`countries`/`events`, so a field nobody asked about cannot block anything,
structurally, rather than by being remembered and excluded.

EXIT CODE IS THE PRODUCT. 0 means publish, 1 means a human looks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_CUR = ROOT / "data" / "events.json"
EVENTS_PUB = ROOT / "fires" / "data" / "published" / "events.json"
AREA_CUR = ROOT / "fires" / "data" / "burnt_area.json"
AREA_PUB = ROOT / "fires" / "data" / "published" / "burnt_area.json"
WEEK_CUR = ROOT / "fires" / "data" / "current_week.json"
WEEK_PUB = ROOT / "fires" / "data" / "published" / "current_week.json"
# The EU area envelope, added 2026-08-22 after Fire found it had NO
# sign-off coverage at all: templates/eu_area_chart.py opens this file
# itself at call time, so its path never appears in fires/build_page.py
# and was invisible to anyone assembling this list by reading the
# builder. See scripts/publish_all.py's SIGNOFF_INPUTS comment for the
# template half of the same fix.
EU_CUR = ROOT / "fires" / "data" / "eu_area.json"
EU_PUB = ROOT / "fires" / "data" / "published" / "eu_area.json"
# Per-country season history, added 2026-08-22 after Fire traced every
# file fires/build_page.py and fires/build_country_pages.py actually
# read (not just what appears in the builder's own source, which is how
# eu_area.json was missed too) and found this directory referenced
# nowhere in either gate. It is not incidental: it is where the
# "It has already passed <year>, the previous record season" /
# "The record season, <year>, reached N ha" sentence on every country
# page comes from (fires/build_country_pages.py:231-239), a DIFFERENT
# record claim from burnt_area.json's area_ha-vs-max_ha one above. Fire
# demonstrated the gap directly: quadrupling a historical year's series
# in a scratch clone flipped a country's page from "passed the record"
# to "the record still stands" and the old gate reported PUBLISH.
AREA_HIST_DIR = ROOT / "fires" / "data" / "area_history"
AREA_HIST_PUB_DIR = ROOT / "fires" / "data" / "published" / "area_history"


def _is_area_record(country: dict) -> bool | None:
    """Does the committed area_ha claim a record against max_ha. None when
    the fields aren't there (desert-fire countries read 0 ha everywhere,
    per fires/build_country_pages.py's own handling of that case)."""
    area, mx = country.get("area_ha"), country.get("max_ha")
    if area is None or mx is None:
        return None
    return area > mx


def _week_rank(entry: dict) -> int | None:
    """1 = this week is the highest on record for this country, matching
    the ordinal the template renders (ORD in fires/build_country_pages.py:
    1 highest, 2 second-heaviest, ...). Only the boundary at rank 1 is a
    claim this gate cares about; 2nd-to-3rd is ordinary movement, same as
    heat's day-rank drifting a place or two."""
    hist = entry.get("hist") or {}
    count = entry.get("count")
    if count is None or not hist:
        return None
    return 1 + sum(1 for v in hist.values() if v is not None and v > count)


def classify(prev: dict, cur: dict) -> tuple[list[str], list[str]]:
    """(block, report). See module docstring for the four triggers:
    qualifying-set change, an area record appearing/withdrawn, a weekly
    rank crossing into/out of 1st, and the "record" tag on an existing
    event appearing/withdrawn. Everything else is ordinary."""
    block, report = [], []

    # data/events.json: the qualifying set. ALWAYS editorial, same
    # reasoning as heat's added/removed cities (D-141): every claim about
    # "which countries are showing anomalous fire activity" inherits the
    # choice of which countries are in that set.
    pe = {e["region"]: e for e in (prev.get("events") or {}).get("events", [])}
    ce = {e["region"]: e for e in (cur.get("events") or {}).get("events", [])}
    added = sorted(set(ce) - set(pe))
    removed = sorted(set(pe) - set(ce))
    if added:
        block.append(f"events: region(s) entered the qualifying set: {added}")
    if removed:
        block.append(f"events: region(s) LEFT the qualifying set: {removed}")

    for region in sorted(set(pe) & set(ce)):
        p, c = pe[region], ce[region]
        p_rec = "record" in (p.get("qualifies_on") or [])
        c_rec = "record" in (c.get("qualifies_on") or [])
        if p_rec != c_rec:
            block.append(f"{region}: 'record' qualification {p_rec} -> {c_rec}")
        elif p.get("stat") != c.get("stat") or p.get("title") != c.get("title"):
            report.append(f"{region}: stat/title {p.get('stat')!r} -> {c.get('stat')!r}")

    # fires/data/burnt_area.json: the national-record area claim. This is
    # exactly the Belgium case: area_ha revising from 3,175 to 3,208 while
    # both readings sit above max_ha (2,180) is a magnitude change inside
    # an unchanged claim, and must pass. Crossing max_ha, either
    # direction, is the record appearing or being withdrawn.
    pc, cc = (prev.get("burnt_area") or {}).get("countries", {}), \
             (cur.get("burnt_area") or {}).get("countries", {})
    for iso in sorted(set(pc) & set(cc)):
        p, c = pc[iso], cc[iso]
        pr, cr = _is_area_record(p), _is_area_record(c)
        if pr != cr and pr is not None and cr is not None:
            block.append(
                f"{c.get('name', iso)}: area record status {pr} -> {cr} "
                f"({p.get('area_ha')} -> {c.get('area_ha')} ha against "
                f"max {c.get('max_ha')}). A revised magnitude on the same "
                f"side of the record line would have passed.")
        elif p.get("area_ha") != c.get("area_ha"):
            report.append(f"{c.get('name', iso)}: area_ha {p.get('area_ha')} "
                          f"-> {c.get('area_ha')}")

    # fires/data/current_week.json: the weekly ordinal claim a country
    # page opens on ("fourth-heaviest fire week..."). Only the rank-1
    # boundary is a claim; anything else is data doing what data does.
    pw = (prev.get("current_week") or {}).get("countries") or \
         (prev.get("current_week") or {})
    cw = (cur.get("current_week") or {}).get("countries") or \
         (cur.get("current_week") or {})
    for iso in sorted(set(pw) & set(cw)):
        p, c = pw[iso], cw[iso]
        # Fire, 2026-08-23: Saudi Arabia and Libya both read as gas
        # flaring, not a fire season (73.1% and 38.0% same-cell
        # recurrence against genuine fire weeks scoring near zero), and
        # build_events now excludes them from the qualifying set on that
        # basis. But this loop still saw Saudi Arabia cross into 1st
        # place and held the whole channel on a rank movement for a page
        # that publishes no claim, since an excluded country renders
        # nothing. A country's own current persistence verdict decides
        # whether its rank means anything; "was persistent last time and
        # excluded" is not a signal, the current flag is.
        if (c.get("persistence") or {}).get("verdict") == "persistent_source":
            continue
        pr, cr = _week_rank(p), _week_rank(c)
        if pr != cr and (pr == 1 or cr == 1):
            block.append(f"{c.get('name', iso)}: weekly rank {pr} -> {cr}, "
                        f"crossing the 1st-place boundary")
        elif pr != cr and pr is not None and cr is not None:
            report.append(f"{c.get('name', iso)}: weekly rank {pr} -> {cr}")

    # fires/data/eu_area.json: the EU season envelope's projection. This
    # is the densest claim surface on the page, per Fire's own read: the
    # headline sentence pivots on whether the median outcome breaks the
    # record ("could exceed" vs "on course to exceed"), which is exactly
    # what median_below_record encodes. record_inside_envelope is the
    # companion claim: whether the record sits inside the projected
    # range at all. Both are booleans computed by the analog method, not
    # magnitudes, so they belong in block rather than report.
    #
    # analogs_exceeding_record crossing ZERO is also a claim: "no analog
    # exceeds the record" flipping to "at least one does" changes whether
    # "could exceed the record" is true at all, independent of the median.
    # Movement between nonzero counts (5 of 20 to 6 of 20) is the
    # magnitude changing under an unchanged claim and is ordinary.
    # The claim fields live under "projection", not at the top level of
    # eu_area.json (area_ha and as_of_week are top-level; the analog
    # method's output is nested). Read from there, not from the file's
    # root, which is the bug this comment exists to prevent recurring.
    pe2 = (prev.get("eu_area") or {}).get("projection") or {}
    ce2 = (cur.get("eu_area") or {}).get("projection") or {}
    if pe2 and ce2:
        pm, cm = pe2.get("median_below_record"), ce2.get("median_below_record")
        if pm != cm:
            block.append(f"EU envelope: median_below_record {pm} -> {cm}. "
                        f"This is the pivot between 'could exceed the "
                        f"record' and 'on course to exceed it', the "
                        f"headline sentence on the page.")
        pi, ci = pe2.get("record_inside_envelope"), ce2.get("record_inside_envelope")
        if pi != ci:
            block.append(f"EU envelope: record_inside_envelope {pi} -> {ci}")
        pex, cex = pe2.get("analogs_exceeding_record"), ce2.get("analogs_exceeding_record")
        if pex is not None and cex is not None and (pex == 0) != (cex == 0):
            block.append(f"EU envelope: analogs_exceeding_record {pex} -> "
                        f"{cex}, crossing zero: whether any analog beats "
                        f"the record at all has changed.")
        elif pex != cex:
            report.append(f"EU envelope: analogs_exceeding_record {pex} -> {cex}")
        # area_ha (the observed total, not a projection field) lives at
        # the file's top level, so it is read from the un-nested dicts.
        pa, ca = (prev.get("eu_area") or {}).get("area_ha"), \
                 (cur.get("eu_area") or {}).get("area_ha")
        if pa != ca:
            report.append(f"EU envelope: area_ha {pa} -> {ca}")

    # fires/data/area_history/<ISO>.json: the season-record claim on
    # every country page, computed exactly as
    # fires/build_country_pages.py:231-239 does, "this year" being the
    # newest year key present rather than date.today().year, so this
    # stays deterministic and testable rather than depending on the
    # clock. Only whether the claim's TRUTH VALUE changes is a block; the
    # margin by which a season leads or trails is ordinary.
    hist_pairs = cur.get("area_history") or {}
    hist_prev = prev.get("area_history") or {}
    for iso in sorted(set(hist_prev) & set(hist_pairs)):
        pb = _beat_record(hist_prev[iso])
        cb = _beat_record(hist_pairs[iso])
        if pb != cb and pb is not None and cb is not None:
            block.append(
                f"{iso}: season-record claim {pb} -> {cb}. This is the "
                f"'has already passed <year>' / 'the record still stands' "
                f"sentence on the country page, computed from "
                f"fires/data/area_history/{iso}.json, a different file "
                f"from burnt_area.json's own record check above.")

    return block, report


def _beat_record(years: dict) -> bool | None:
    """True if the newest year's cumulative max beats every prior year's,
    mirroring fires/build_country_pages.py's beat_record computation.
    None when there's nothing to compare (a country with only one year
    of history, or malformed data)."""
    if not years or len(years) < 2:
        return None
    try:
        year = max(int(y) for y in years)
    except (TypeError, ValueError):
        return None
    prior = [y for y in years if int(y) != year]
    if not prior:
        return None
    rec_v = max(max(years[y].values()) for y in prior)
    cur_v = max(years[str(year)].values())
    return cur_v > rec_v


def _load(path: Path):
    return json.loads(path.read_text()) if path.exists() else {}


def _load_area_history(directory: Path) -> dict:
    """{ISO: {year: {week: value}}} for every area_history file present.
    Missing directory (no baseline yet) yields an empty dict, same
    "nothing to compare, not this run's problem" shape as _load."""
    out = {}
    if not directory.exists():
        return out
    for p in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(p.read_text())["years"]
        except (OSError, ValueError, KeyError):
            continue
        out[p.stem] = raw
    return out


def main() -> int:
    if not EVENTS_PUB.exists() or not AREA_PUB.exists():
        print("  HOLD: no previously published fires payload to compare "
              "against.", file=sys.stderr)
        return 1
    prev = {"events": _load(EVENTS_PUB), "burnt_area": _load(AREA_PUB),
            "current_week": _load(WEEK_PUB), "eu_area": _load(EU_PUB),
            "area_history": _load_area_history(AREA_HIST_PUB_DIR)}
    cur = {"events": _load(EVENTS_CUR), "burnt_area": _load(AREA_CUR),
           "current_week": _load(WEEK_CUR), "eu_area": _load(EU_CUR),
           "area_history": _load_area_history(AREA_HIST_DIR)}
    block, report = classify(prev, cur)
    for r in report:
        print(f"    changed: {r}")
    if not block:
        print(f"  PUBLISH: {len(report)} ordinary change(s), no record "
              f"appeared or was withdrawn, qualifying set unchanged, no "
              f"weekly rank crossed into or out of 1st.")
        return 0
    print(f"  HOLD: {len(block)} change(s) that need a person. "
          f"{len(report)} ordinary change(s) would have passed.",
          file=sys.stderr)
    for b in block:
        print(f"    - {b}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
