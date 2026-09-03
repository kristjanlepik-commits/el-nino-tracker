"""Build docs/fires/<slug>/ for every country in data/events.json.

Under D-030 the front end is the design chat's, so the layout lives in
templates/country_page.py and this file is the adapter: it reads the
Fire chat's validated JSON, shapes one piece dict per country, and
renders. It contains no layout and no CSS, and the template contains no
knowledge of FIRMS, EFFIS, GWIS or baseline gates. That boundary is the
point: the Fire chat can change its science freely as long as the JSON
shape holds.

Country set comes from data/events.json and is NOT a fixed list. It was
14 yesterday and 12 today, and the Fire chat is about to change the gate
that selects it (it currently ranks on the weekly detection multiple
alone, which leaves Algeria eleventh while leading on year-to-date area
at 14.2x, and Italy with no page at all despite 3.3x for the year).
Directories from a previous, larger set linger under docs/fires/ and are
left alone rather than deleted: this builder owns what it writes, not
what it finds.

Reads, all committed:

    data/events.json                which countries have a page
    fires/data/current_week.json    detections, dailies, same-week history
    fires/data/burnt_area.json      hectares to date, per-country source
    fires/data/area_history/<ISO>   weekly cumulative area, every season
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from templates.country_page import render  # noqa: E402

EVENTS = os.path.join(REPO, "data", "events.json")
DETAIL = os.path.join(REPO, "fires", "data", "current_week.json")
AREA = os.path.join(REPO, "fires", "data", "burnt_area.json")
AREA_HIST = os.path.join(REPO, "fires", "data", "area_history")
OUTDIR = os.path.join(REPO, "docs", "fires")
# The set of things that ARE countries, for the stamper. Same file the
# channel takes its country geometry from, so "is this a country page"
# and "is this a country" cannot answer differently.
GEO = os.path.join(REPO, "fires", "data", "countries.geo.json")

ORD = {1: "highest", 2: "second-heaviest", 3: "third-heaviest",
       4: "fourth-heaviest", 5: "fifth-heaviest"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def pretty_window(window: str) -> str:
    """"07-21..07-27" into "21 to 27 July"."""
    m = re.match(r"(\d{2})-(\d{2})\.\.(\d{2})-(\d{2})", window or "")
    if not m:
        return window or ""
    m1, d1, m2, d2 = (int(x) for x in m.groups())
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    if m1 == m2:
        return f"{d1} to {d2} {months[m2 - 1]}"
    return f"{d1} {months[m1 - 1]} to {d2} {months[m2 - 1]}"


def pretty_day(iso: str) -> str:
    """"2026-07-24" into "24 July", so prose reads as prose."""
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    try:
        _, m, d = iso.split("-")
        return f"{int(d)} {months[int(m) - 1]}"
    except (ValueError, IndexError):
        return iso


def build_piece(ev, det, area_cur, area_years, window, elsewhere, year):
    name = ev["region"]
    hist = {int(k): v for k, v in det["hist"].items()}
    now, mean = det["count"], det["mean"]
    rank = 1 + sum(1 for v in hist.values() if v > now)
    daily = det.get("daily") or {}
    peak_day, peak_val = (max(daily.items(), key=lambda kv: kv[1])
                          if daily else ("", 0))
    normal = mean / 7.0
    cleared = sum(1 for v in daily.values() if v > normal)

    # The claim leads with whichever timescale is more extreme, and always
    # names which clock it is on.
    #
    # Leading on a fixed timescale buries the story on half the set: at
    # 1.9x on the week against 14.2x on the year, Algeria's own page
    # would open on its least remarkable number, while Botswana at 5.9x
    # against 0.4x would open on a record year it is not having. Naming
    # the timescale is what stops the other one being read as a summary
    # of both, which is the failure the never-adjacent rule exists to
    # prevent one paragraph earlier.
    #
    # It argues from this country's own baselines only. No ENSO framing:
    # most of the live set carries no attribution tag at all, and the
    # house context does not travel into a channel page as an assumption.
    week_mult = now / mean if mean else 0.0
    # "SINCE 2012" ASSERTS A SPAN THIS BASELINE DOES NOT HAVE.
    #
    # min(hist) is derived rather than hardcoded, which is why this
    # survived the round of fixes that caught the index title and
    # stat_label: it looked like the correct pattern. It is not. The
    # earliest year present is 2012 and the baseline holds THIRTEEN
    # years, because 2022 has no SNPP science archive over most windows
    # and is excluded on purpose. "Since 2012" reads as fourteen
    # continuous years, and wherever the missing year would have
    # outranked this week the claim is wrong rather than imprecise.
    #
    # Counting the weeks we actually compared cannot say something
    # untrue, and it stays correct when the hole moves, which it does:
    # the excluded year is 2021 in some windows and 2022 in others,
    # because the exclusion follows the defective DATES rather than a
    # fixed year.
    compared = len(hist) + 1
    week_claim = (f"{name} had its {ORD.get(rank, str(rank) + 'th-heaviest')} "
                  f"fire week for this point in the year, of "
                  f"{compared} compared")
    claim = week_claim

    # The channel's own flags decide what kind of claim is available.
    # Before these were consumed, DR Congo at 1.0x and z = -0.08 rendered
    # exactly like Spain at 14.1x: the largest fire system on Earth
    # behaving completely normally, presented as news. A page that says
    # "seventh-heaviest week" about a country sitting on its own mean is
    # true and still misleading, which is the failure the flags exist to
    # prevent.
    anomalous = bool(ev.get("anomalous"))
    volume_context = bool(ev.get("volume_context"))
    unstable = bool(ev.get("multiple_unstable"))
    z = ev.get("z")

    if volume_context and not anomalous:
        # Large, above normal, NOT abnormal. D-043 requirement 2 in its
        # first live case: this has to read as legibly as "extreme" does.
        near_normal = z is not None and abs(z) < 1.0
        claim = ((f"{name} is burning at close to its normal rate for this "
                  f"point in the year")
                 if near_normal else
                 (f"{name} is burning above its normal rate, and within "
                  f"its historical range"))

    if area_cur and area_years and not (volume_context and not anomalous):
        year_mult = area_cur.get("multiple") or 0.0
        prev = [y for y in area_years if y != year]
        rec = max(prev, key=lambda y: max(area_years[y].values())) if prev else None
        rec_v = max(area_years[rec].values()) if rec else 0
        beat_record = bool(rec and max(area_years[year].values()) > rec_v)
        # A broken all-time record outranks any ratio. Comparing the two
        # multiples alone put France on its week at 10.2x against 8.9x,
        # which is true but weaker than the fact it displaced: a season
        # that has already passed every completed year on record is a
        # different kind of statement from a large multiple, and no
        # ratio is more extreme than it. Below that, the two multiples
        # decide.
        if beat_record:
            claim = (f"{name} has already burned more this year than in "
                     f"any full year on record")
        elif year_mult > week_mult and not unstable:
            claim = (f"{name} has burned {year_mult:.1f} times its normal "
                     f"area for this point in the year")

    piece = {
        "region": name,
        "year": year,
        "window_pretty": pretty_window(window),
        "claim": claim,
        "standfirst": (
            "Two questions, side by side. How bad was this week, measured "
            "against every week like it. How bad is the year, measured "
            "against every season on record. Different instruments, "
            "different units, and one of them is not finished."),
        "attribution": ev.get("attribution"),   # D-076: null, not "pending"
        # Orthogonal, and a country carries more than one: Spain is
        # anomalous AND pinned, Canada is pinned AND volume_context and
        # explicitly not anomalous. Collapsing them into one class is
        # what the split exists to prevent.
        "anomalous": anomalous,
        "volume_context": volume_context,
        "multiple_unstable": unstable,
        "z": z,
        # Says which of the three states this is, in words, at the same
        # weight in every case. An unstable multiple says so where the
        # multiple is printed, so a pinned country's thin number cannot
        # look sturdy just because a reader asked for that country.
        "verdict": (
            ("Above normal, and within this country's historical range"
             if volume_context and not anomalous else
             "Cleared the anomaly gate for this week")
            + (". The multiple rests on a thin baseline, so the rank is "
               "the sturdier reading" if unstable else "")
            + (f". Standardised anomaly z = {z:+.1f}" if z is not None else "")),
        "detections": {
            "count": now,
            "mean": mean,
            "hist": hist,
            "daily": daily,
            "multiple": now / mean if mean else 0.0,
            "baseline_span": f"{min(hist)} to {max(hist)}",
            "instrument": "NASA FIRMS SNPP VIIRS, daily, 375 m",
            "daily_note": (
                f"{cleared} of {len(daily)} days cleared one seventh of a "
                f"normal week. The peak, {peak_val:,} on "
                f"{pretty_day(peak_day)}, is {peak_val / normal:.0f} times "
                f"that line."
                if daily and normal else "Day by day through the window."),
        },
        "elsewhere": elsewhere,
        "what_this_is": (
            "Two measurements of the same fire season at two time scales. "
            "The multiple is a rate: how much fire activity satellites "
            "detected this week against what this week normally looks "
            "like. The hectare figure is a stock: how much land has been "
            "mapped as burnt since January. A country can have an "
            "unremarkable week and still be having a record year, and the "
            "reverse is also true."),
        "what_this_is_not": (
            "Not one number at two zoom levels. The two figures come from "
            "different instruments with different latencies, and they are "
            "not convertible into each other. Not an attribution: fire "
            "seasons are driven by heat, drought, wind and land use, and "
            "the tag on this page states what is and is not established "
            "for this event. Not a forecast of where the season ends."),
    }

    if area_cur and area_years:
        # DROP THE LEADING ALL-ZERO YEARS BEFORE ANYTHING READS THIS.
        #
        # EFFIS reports a year it did not cover as zero, so a country
        # whose record starts late carries flat zero seasons at the
        # front. min() over them made the caption claim a span the data
        # does not have: Algeria's page said "every season since 2006"
        # when its coverage begins in 2009, and drew three phantom
        # fire-free seasons a reader has no way to identify as absent.
        #
        # This is the same absence-as-zero defect socials found in
        # avg_ha on 2026-08-30, which I fixed inside _clean_avg and did
        # not carry to the chart. For a MEAN the zeros deflate the
        # baseline and inflate the multiple. For a RECORD they do not
        # move the number at all, since a maximum ignores zeros, but
        # they make the SPAN wrong, and the span is the whole strength
        # of "the biggest season since 2006". 35 of 97 countries carry
        # such a run; Slovakia's is fourteen years long, leaving six.
        #
        # Interior zeros are kept: a quiet year after coverage began is
        # a real measurement and belongs on the chart.
        _ordered = sorted(area_years)
        _lead = 0
        for _y in _ordered:
            if area_years[_y] and max(area_years[_y].values()) == 0:
                _lead += 1
            else:
                break
        if _lead and _lead < len(_ordered):
            area_years = {y: v for y, v in area_years.items()
                          if y >= _ordered[_lead]}
        first_year = min(area_years)
        prev = [y for y in area_years if y != year]
        rec = max(prev, key=lambda y: max(area_years[y].values())) if prev else None
        rec_v = max(area_years[rec].values()) if rec else 0
        cur_v = max(area_years[year].values())
        beat = (f"It has already passed {rec}, the previous record season, "
                f"at {rec_v:,.0f} ha." if rec and cur_v > rec_v else
                f"The record season, {rec}, reached {rec_v:,.0f} ha."
                if rec else "")
        weeks_in = max(area_years[year])
        piece["area"] = {
            "area_ha": area_cur["area_ha"],
            "multiple": area_cur.get("multiple") or 0.0,
            "week": area_cur.get("week"),
            "as_of": area_cur.get("as_of"),
            "source": area_cur.get("source", ""),
            "instrument": f'{area_cur.get("source", "")} mapped perimeters, weekly',
            "years": area_years,
            "first_year": first_year,
            "cumulative_note": (
                f"Only this year carries hue; every grey line is one earlier "
                f"season accumulating from January. {beat}"),
            "weekly_note": (
                f"Week by week rather than cumulative, so a single heavy "
                f"week is visible as one. The cell runs to week 52: "
                f"{52 - weeks_in} weeks of this season have not happened "
                f"yet."),
        }
        # Instruments, plural, both named, each with its own baseline. The
        # source is read per country: 33 of 45 resolve to GWIS and 12 to
        # EFFIS, so a literal would name a European instrument for
        # Canadian fires.
        piece["rail_instruments"] = (
            f'NASA FIRMS SNPP VIIRS<br>thermal anomaly counts, daily, 375 m'
            f'<br><br>{area_cur.get("source", "")} burnt area<br>'
            f'mapped perimeters, weekly. Area lands in the week it is '
            f'mapped, which need not be the week it burned.')
        piece["rail_baseline"] = (
            f'Weekly multiple: same-week mean, {min(hist)} to {max(hist)}.'
            f'<br>Cumulative: complete seasons, {first_year} to {year - 1}.')
        piece["rail_revision"] = (
            'Mapped area for recent weeks rises as perimeters are '
            'completed, and a week&rsquo;s area may be mapped after the '
            'week it burned. Published figures are not edited in place; '
            'corrections run forward.')
    else:
        piece["area"] = None
        piece["rail_instruments"] = (
            'NASA FIRMS SNPP VIIRS<br>thermal anomaly counts, daily, 375 m')
        piece["rail_baseline"] = (
            f'Weekly multiple: same-week mean, {min(hist)} to {max(hist)}.')
        piece["rail_revision"] = (
            'Detection counts are whole UTC days and are not revised. '
            'Published figures are not edited in place.')

    # D-076, 2026-08-04: an unassessed country gets NO attribution rail.
    #
    # "pending" was the default fallback, so it rendered on nearly every
    # page and told the reader only that we had not looked. That is a
    # work state, not a finding, and it is not the reader's problem. The
    # two ENSO strings are unchanged, and the field is kept null rather
    # than removed so a real string can occupy it later.
    tag = piece["attribution"]
    piece["rail_attribution"] = {
        "enso": ('ENSO-loaded window<br>This event falls in a window and '
                 'region where an ENSO teleconnection is established. '
                 'That is a loading, not a cause.'),
        "non_enso": ('not ENSO-linked<br>No established teleconnection '
                     'between ENSO and fire weather in this region. The '
                     'swell raised this; the wave did not.'),
    }.get(tag, "")
    return piece


def main() -> None:
    events = json.load(open(EVENTS))["events"]
    detail = json.load(open(DETAIL))
    window = detail.get("window", "")
    dets = detail.get("countries") or detail
    try:
        areas = json.load(open(AREA))["countries"]
    except (OSError, ValueError, KeyError):
        areas = {}
    name2iso = {v.get("name"): k for k, v in dets.items()}
    year = date.today().year

    written = 0
    for ev in events:
        iso = name2iso.get(ev["region"])
        det = dets.get(iso) if iso else None
        if not det or not det.get("hist"):
            print(f"  skip {ev['region']}: no detection detail")
            continue
        area_cur = areas.get(iso)
        # A country can have fire detections and no mapped burnt area at
        # all: Saudi Arabia and Libya both read 0 ha for 2026 across a
        # 21-year EFFIS/GWIS record, because desert fire leaves no
        # mappable perimeter. The row exists, so `areas.get(iso)` is
        # truthy, and every value in it is zero.
        #
        # Passing that through renders an area cell whose series maxes at
        # zero. Treat "no area anywhere" as no area section, which the
        # template already handles, rather than an area section full of
        # zeros. This is an adapter decision about which data exists, not
        # a layout one.
        if area_cur and not (area_cur.get("area_ha") or 0):
            area_cur = None
        area_years = None
        hist_path = os.path.join(AREA_HIST, f"{iso}.json")
        if area_cur and os.path.exists(hist_path):
            try:
                raw = json.load(open(hist_path))["years"]
                area_years = {int(y): {int(w): v for w, v in wk.items()}
                              for y, wk in raw.items()}
                if year not in area_years:
                    area_years = None
            except (OSError, ValueError, KeyError):
                area_years = None
        # events.json hrefs are root-relative because the landing page
        # consumes them from the site root. This page already sits at
        # /fires/<slug>/, so the prefix has to become a sibling hop or
        # the link resolves to /fires/<slug>/fires/<other>/.
        elsewhere = []
        for o in events:
            if o["region"] == ev["region"]:
                continue
            href = o.get("href", "")
            if href.startswith("fires/"):
                href = "../" + href[len("fires/"):]
            elsewhere.append(dict(o, href=href))
            if len(elsewhere) == 3:
                break
        piece = build_piece(ev, det, area_cur, area_years, window,
                            elsewhere, year)
        out = os.path.join(OUTDIR, slugify(ev["region"]))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w") as fh:
            fh.write(render(piece))
        written += 1
    print(f"wrote {written} country page(s) to docs/fires/")
    # REFUSE RATHER THAN NO-OP, and refuse BEFORE stamping.
    #
    # QA's finding: this exited 0 whatever happened, so a build that
    # produced nothing was indistinguishable downstream from a week where
    # no country qualified. That nearly cost the whole channel. Platform's
    # dropped-page redirect identified dropped countries by an unchanged
    # index.html mtime, so one exit-0-with-no-output would have classified
    # every fires country page as dropped and redirected the lot in a
    # single publish, silently. The redirect is withdrawn (D-197 reversed
    # by D-198), but the hole it exposed is real and outlives it.
    #
    # THE FLOOR IS THE PINNED SET, NOT AN ARBITRARY FRACTION. build_events
    # guarantees GBR, USA, CAN, FRA and ESP appear every week whatever the
    # gate does, because readers come to check their own country. So a
    # missing pinned country is proof that something upstream failed, and
    # it cannot be a quiet week. A percentage drop would have to be tuned
    # against a set that legitimately ran 22 to 28 in the last seven days;
    # this needs no tuning and cannot false-positive on a calm week.
    #
    # It also protects the stamp, which is the half QA cared about most.
    # The stamp asserts "checked for the week of X" on pages nothing else
    # updates. If the builder ever no-ops, that date stops advancing while
    # the page keeps claiming it, and a reader in September reads an August
    # date as the latest check. A build that dies must not leave a freshness
    # claim standing, which is the lesson heat wrote up on 2026-08-17 after
    # an aborted build left a gate printing PUBLISH.
    from fires.build_events import PINNED
    pinned_names = {dets[i]["name"] for i in PINNED if i in dets}
    missing = sorted(pinned_names - {e["region"] for e in events})
    if not written or missing:
        raise SystemExit(
            f"REFUSING to finish: wrote {written} country page(s)"
            + (f" and these pinned countries are absent from events.json: "
               f"{', '.join(missing)}" if missing else "")
            + ". The pinned set is guaranteed by the gate, so this is an "
              "upstream failure rather than a quiet week. Nothing has been "
              "stamped, so no page will claim a freshness it does not have.")

    print(stamp_unregenerated({slugify(e["region"]) for e in events},
                              pretty_window(window)))
    print(emit_archive({slugify(e["region"]) for e in events}, window,
                       window_end=max((e.get("date") for e in events
                                       if e.get("date")), default=None)))


STAMP_ID = "lastassessed"



ARCHIVE_OUT = os.path.join(REPO, "fires", "data", "country_archive.json")


def emit_archive(live_slugs, window, window_end=None) -> str:
    """Every country page that exists, with whether it is current.

    WHY THIS IS EMITTED RATHER THAN DERIVED. 31 of 49 fire country pages
    are reachable only by knowing the URL, and four of them are stories
    we published: Belgium's national record, Serbia's record week,
    Bosnia and Macedonia. Nothing links them, every link on the site
    resolves, and so nothing is broken enough to notice. Design hit the
    same shape on floods an hour later, from the other end.

    Design asked for this rather than parse 49 rendered pages for a date
    that this builder already knows, which is the mistake we made once
    on the region page: a consumer deriving a number from HTML that the
    producer could simply have stated.

    THE QUALIFIER TRAVELS WITH THE ROW, not only on the page. Design's
    point and it is the same rule as a multiple carrying its count: a
    list of 49 rows reads as 49 current assessments unless each row says
    otherwise. So `current` is on every entry, and `last_assessed` is
    the window a row's FIGURES come from, which for a dropped country is
    not this week.
    """
    # Real names from the roster, keyed by the same slugify the pages
    # were written with, so the join cannot drift from the filenames.
    names = {}
    try:
        for v in json.load(open(os.path.join(
                REPO, "fires", "data", "current_week.json")))["countries"].values():
            names[slugify(v["name"])] = v["name"]
    except (OSError, ValueError, KeyError):
        pass
    # A PAGE CAN OUTLIVE ITS ROSTER ENTRY, so the roster alone cannot name
    # every page. Ethiopia has a published page and appears in no roster
    # file, which is how it ended up claiming a check that never happened.
    # The geo file names all 180 countries and is what the pages were
    # built from, so it is the right fallback rather than title-casing a
    # slug, which design refused to do and was right to.
    try:
        for f in json.load(open(os.path.join(
                REPO, "fires", "data", "countries.geo.json")))["features"]:
            n = (f.get("properties") or {}).get("name")
            if n:
                names.setdefault(slugify(n), n)
    except (OSError, ValueError, KeyError):
        pass
    roster_slugs = tracked_slug_set()
    prev_seen = {}
    if os.path.exists(ARCHIVE_OUT):
        try:
            for r in json.load(open(ARCHIVE_OUT)).get("countries", []):
                if r.get("last_assessed"):
                    prev_seen[r["slug"]] = r["last_assessed"]
        except (OSError, ValueError):
            pass
    rows = []
    if os.path.isdir(OUTDIR):
        for slug in sorted(os.listdir(OUTDIR)):
            page = os.path.join(OUTDIR, slug, "index.html")
            if not os.path.isfile(page):
                continue
            # A DIRECTORY UNDER docs/fires/ IS NOT NECESSARILY A COUNTRY.
            # Design's archive index lives at docs/fires/countries/, so
            # this listed the archive as a country in the archive: name
            # null, tracked false, no date. The same mistake as the
            # stamper reading a directory listing as a roster, which is
            # what put a false "checked this week" line on Ethiopia.
            # A country is one we have a NAME for; anything else here is
            # a page that happens to live nearby.
            if slug not in names:
                continue
            current = slug in live_slugs
            # CARRIED FORWARD, NOT PARSED BACK. My first version read the
            # date out of the rendered page and got None for all 31
            # archived rows, because the stamp records when a country was
            # CHECKED and never when its figures date from. The page does
            # not carry the fact, so deriving it from the page could only
            # ever fail, and it failed silently into a field rather than
            # loudly.
            #
            # Design asked for this emitted rather than derived from HTML
            # for exactly this reason. So the window a country last
            # qualified in is remembered here, and a country that drops
            # out keeps the value it had.
            # ONE FIELD, ONE FORMAT. The first version put the window
            # "08-23..08-29" on current rows and an ISO date on seeded
            # ones, so a consumer had to handle two shapes in one field.
            # Design is rendering this; mixed formats are how a table
            # ends up with two kinds of row that mean the same thing.
            last = (window_end if current else prev_seen.get(slug))
            # NAME, because a slug is not a name. Design was right to
            # refuse rather than title-case: 48 of 49 slugs invert
            # cleanly, WHICH IS EXACTLY WHAT MAKES THAT JOIN LOOK SAFE,
            # and "republic-of-serbia" and "democratic-republic-of-the
            # -congo" are not spellings we use anywhere else.
            rows.append({"slug": slug, "name": names.get(slug),
                         "href": f"fires/{slug}/",
                         "current": current,
                         # ROSTER MEMBERSHIP, not "do we have a name".
                         # I conflated the two by adding a geo fallback to
                         # `names` for Ethiopia, which flipped its tracked
                         # flag to true, asserting the opposite of the
                         # fact that caused this bug. Two dictionaries,
                         # two questions.
                         "tracked": slug in roster_slugs,
                         "last_assessed": last,
                         "claims_current": current})
    doc = {"_readme": [
        "Every fire country page that exists, current or not.",
        "Built so design can render an archive without parsing rendered",
        "HTML for a date this builder already knows.",
        "`current` false means the country did not clear the anomaly",
        "gate this week. It was CHECKED; that is a result, not a gap.",
        "`last_assessed` is the window the row's FIGURES come from,",
        "which for a dropped country is not this week.",
    ], "window": window, "countries": rows}
    with open(ARCHIVE_OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    live = sum(1 for r in rows if r["current"])
    return (f"wrote country_archive.json: {len(rows)} page(s), {live} "
            f"current, {len(rows) - live} archived")

def tracked_slug_set() -> set:
    """Slugs of countries actually in the roster this run.

    Membership of the ROSTER, not presence of a directory. A page can
    outlive the country's baseline, and Ethiopia's did.
    """
    try:
        names = [v["name"] for v in json.load(
            open(os.path.join(REPO, "fires", "data",
                              "current_week.json")))["countries"].values()]
    except (OSError, ValueError, KeyError):
        return set()
    return {slugify(n) for n in names}


def stamp_unregenerated(live_slugs, window_label) -> str:
    """Date the pages that stopped qualifying, rather than leaving them.

    Product's ruling, Fire's instinct and mine. A 404 is worse than a
    dated page: the URL may be linked and removing it destroys the
    record instead of qualifying it. But a bare date says when we last
    looked and not what we found, so the stamp says both.

    "Not flagged since" is the honest half. These countries were checked
    and did not clear the anomaly gate; that is a result, and it is the
    same calibration move as Canada's row qualifier on the index. A
    country shown so it can be checked should read as ordinary rather
    than as abandoned.

    An unregenerated page cannot stamp itself, which is why this runs
    over the directory rather than inside the builder. Idempotent: the
    stamp is replaced, never stacked.
    """
    import re
    if not os.path.isdir(OUTDIR):
        return "no docs/fires/ yet"
    tracked_slugs = tracked_slug_set()

    # A DIRECTORY LISTING IS NOT A ROSTER, and this loop was treating it
    # as one. OUTDIR is docs/fires/, so every subdirectory holding an
    # index.html looked like a country page, and docs/fires/countries/
    # is the ARCHIVE INDEX. It got stamped "This country is no longer in
    # the tracked set, so it was NOT checked for the week of..." on a
    # page that is not a country.
    #
    # Design found it. It is the same shape as the Ethiopia fix and I
    # only half-applied that one: I stopped the archive LISTING itself
    # as a country and left the STAMPER walking the filesystem, so the
    # next run would have put the stamp straight back.
    #
    # The test is now membership of the set of real country names, from
    # the same geo file the channel takes its countries from. Anything
    # else is SKIPPED AND ANNOUNCED rather than silently passed over,
    # because a genuine new country page that fails to match belongs in
    # a log, not in a silence.
    country_slugs = {slugify(f["properties"]["name"])
                     for f in json.load(open(GEO))["features"]}
    skipped = []
    stamped = []
    for slug in sorted(os.listdir(OUTDIR)):
        d = os.path.join(OUTDIR, slug)
        page = os.path.join(d, "index.html")
        if slug in live_slugs or not os.path.isfile(page):
            continue
        if slug not in country_slugs:
            skipped.append(slug)
            continue
        html = open(page).read()
        # TWO DIFFERENT WEEKS, and the first wording conflated them. The
        # country WAS checked this week; what is old is the figures,
        # which date from the last week it qualified. "Last assessed for
        # the week of X ... the figures below are from that assessment"
        # said both were X and only one is.
        # A PAGE MUST NOT CLAIM A CHECK THAT DID NOT HAPPEN.
        #
        # This function walks the DIRECTORY, so it stamped every page it
        # found, including countries no longer in the roster at all.
        # Ethiopia's page said "Checked for the week of 23 to 29 August"
        # for a week in which Ethiopia was in no roster file: not
        # tracked_countries, not country_history, not current_week. It
        # was not checked. Design found it on the live site.
        #
        # "Did not clear the gate" and "we no longer measure here" are
        # different facts and only one of them was being said. The first
        # is a result; the second is a gap in our coverage, which
        # fires/roster.py already refuses to let anyone read as a
        # finding.
        if slug in tracked_slugs:
            note = (f'<p id="{STAMP_ID}" class="stalestamp">Checked for '
                    f'the week of {window_label}: this country did not '
                    f'clear the anomaly gate, so no new assessment was '
                    f'published. The figures below are from the last '
                    f'week it did, and are not current.</p>')
        else:
            note = (f'<p id="{STAMP_ID}" class="stalestamp">This country '
                    f'is no longer in the tracked set, so it was NOT '
                    f'checked for the week of {window_label}. The figures '
                    f'below are from the last week it was assessed. Its '
                    f'absence from our current pages is a limit of our '
                    f'coverage and not a finding about this country.</p>')
        # Consume the trailing newline with the old stamp. Without it
        # every publish left a blank line behind and added a fresh one,
        # so the file grew by a line a week forever and every run showed
        # 15 pages "changed" with a whitespace-only diff. Idempotent has
        # to mean byte-identical or it is not a useful property.
        html = re.sub(rf'\n?<p id="{STAMP_ID}".*?</p>\n?', "\n", html,
                      flags=re.S)
        # D-076 reaches these pages too. They are not regenerated, so the
        # deprecated chip survives in their markup, and 15 live pages
        # were still showing "attribution pending". It is a work state
        # rather than a finding, so removing it is not editing a
        # published result: it is deleting a label that never said
        # anything. The figures on the page are untouched.
        html = re.sub(r'<span class="tag tag-pending">[^<]*</span>', "", html)
        html = re.sub(r'<div class="tagrow">\s*</div>', "", html)
        if "<main>" in html:
            html = html.replace("<main>", "<main>\n" + note, 1)
        elif "</header>" in html:
            html = html.replace("</header>", "</header>\n" + note, 1)
        else:
            continue
        if ".stalestamp" not in html:
            html = html.replace("</style>", (
                "\n.stalestamp { margin: 0 0 18px; padding: 10px 14px;"
                " background: var(--paper-sunk); color: var(--ink-soft);"
                " font-size: 13.5px; max-width: 64ch; }\n</style>"), 1)
        open(page, "w").write(html)
        stamped.append(slug)
    if skipped:
        print(f"  stamper skipped {len(skipped)} page(s) under docs/fires/ "
              f"that are not countries: {', '.join(skipped)}",
              file=sys.stderr)
    return (f"stamped {len(stamped)} unregenerated page(s) as last assessed"
            if stamped else "no unregenerated pages to stamp")


if __name__ == "__main__":
    main()
