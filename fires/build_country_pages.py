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
CITED = os.path.join(REPO, "fires", "data", "cited_figures.json")
OUTDIR = os.path.join(REPO, "docs", "fires")

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


def build_piece(ev, det, area_cur, area_years, window, elsewhere, year,
                iso=None):
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
    # A CITED FIGURE FROM A NAMED AUTHORITY, WHERE ONE EXISTS.
    #
    # Not an estimate of ours. T10 is cite-never-author, and citing
    # somebody else's published number is a different act from producing
    # one. This channel tried to produce a Belgian hectares estimate and
    # binned it: the country's own fit came out with a NEGATIVE slope on 16
    # paired weeks, and borrowing a Mediterranean fit would have been worse
    # than the stale number it replaced while looking more authoritative.
    #
    # THE QUANTITY FIELD IS THE POINT. The Liege figure is "superficie
    # concernee", area AFFECTED, which is normally the perimeter. EFFIS maps
    # area BURNT, which is smaller. They are different measurements, so a
    # later EFFIS figure below the cited one is not a correction and must
    # never be rendered as one. Emitting `quantity` and `quantity_note`
    # rather than a bare number is what stops that comparison being made by
    # a renderer or a reader.
    #
    # Why it is here at all: the page currently shows 299 ha as of 12 August
    # beside news of a 3,000 ha fire. A number that is correct and
    # unexplained is worse than no number, because the panel invites exactly
    # the comparison it cannot survive. Showing both, each with its own date
    # and quantity, makes the lag legible instead of looking like an error.
    piece["cited"] = None
    if os.path.exists(CITED):
        try:
            with open(CITED) as handle:
                piece["cited"] = (json.load(handle).get("figures", {})
                              .get(iso) if iso else None)
        except (OSError, ValueError):
            piece["cited"] = None

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
                            elsewhere, year, iso)
        out = os.path.join(OUTDIR, slugify(ev["region"]))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w") as fh:
            fh.write(render(piece))
        written += 1
    print(f"wrote {written} country page(s) to docs/fires/")
    print(stamp_unregenerated({slugify(e["region"]) for e in events},
                              pretty_window(window)))


STAMP_ID = "lastassessed"


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
    stamped = []
    for slug in sorted(os.listdir(OUTDIR)):
        d = os.path.join(OUTDIR, slug)
        page = os.path.join(d, "index.html")
        if slug in live_slugs or not os.path.isfile(page):
            continue
        html = open(page).read()
        # TWO DIFFERENT WEEKS, and the first wording conflated them. The
        # country WAS checked this week; what is old is the figures,
        # which date from the last week it qualified. "Last assessed for
        # the week of X ... the figures below are from that assessment"
        # said both were X and only one is.
        note = (f'<p id="{STAMP_ID}" class="stalestamp">Checked for the '
                f'week of {window_label}: this country did not clear the '
                f'anomaly gate, so no new assessment was published. The '
                f'figures below are from the last week it did, and are '
                f'not current.</p>')
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
    return (f"stamped {len(stamped)} unregenerated page(s) as last assessed"
            if stamped else "no unregenerated pages to stamp")


if __name__ == "__main__":
    main()
