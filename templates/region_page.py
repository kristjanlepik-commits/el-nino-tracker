"""One region, every channel, including the channels that say nothing.

WHY A REGION AND NOT A COUNTRY. El Nino works by teleconnection and
teleconnections do not respect borders. Today seven contiguous countries
from Guatemala to Colombia are each in one of their four worst crop years
on their own 26-year record, simultaneously, and that fact is invisible on
every surface we publish: the channel index scatters them through a global
list sorted by severity, and a country page shows one place at a time.

AND IT IS THE ONLY SURFACE THAT CAN SHOW QUIET HONESTLY. A channel index
shows what qualified. A country page shows one country. A region page
shows every country in the region including the ones where nothing is
happening, and that context is what makes the loud ones mean anything:
Cuba at 11x reads differently beside a Southern Cone at a fifth of normal.

FOUR STATES, NOT TWO, and each is a different sentence:

  measured, and abnormal        the finding
  measured, and quiet           also a finding, drawn at the same weight
  not in the roster             we do not measure there
  the instrument does not apply a number here would describe nothing

The fourth is heat's and is not a variant of the third. A blind instrument
is transient; a station with 1.3 C of annual amplitude has no summer to
calibrate a heatwave threshold against, permanently. Different sentence.

READS THE ROSTER, NOT THE PAGE LIST. Fires publishes a country page only
where a country qualified, so five LatAm countries have pages and twelve
have readings. Rendering from the page list would have shown five loud
countries and called the other seven absent, which is the exact
absence-as-zero fault this page exists to fix. The readings are in
fires/data/current_week.json and were there the whole time; I told product
I could not see them because I looked in events.json, which is the
qualifying list.
"""
import json
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


_MON = ("January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December")


def _dateline():
    """Which windows this page is reporting, read from the payloads.

    THESE TWO DATES WERE TYPED, and by the time anyone looked they were
    both wrong: the page said "crops to dekad 1 August" against a payload
    at 2026-08-11, and "fires week to 25 August" against a window ending
    08-29. Nothing broke, no guard fired, and the page simply stated the
    wrong fortnight in the one line a reader uses to decide whether it is
    current. D-124 already covers this for the lede; the dateline is the
    same rule and was missed because it looked like furniture.
    """
    crops = json.loads((ROOT / "crops/data/stress_current.json").read_text())
    fires = json.loads((ROOT / "fires/data/current_week.json").read_text())

    y, m, d = (int(x) for x in crops["dekad"].split("-"))
    cro = "%d %s" % (d, _MON[m - 1])

    # fires carries "MM-DD..MM-DD" for the window it actually compared.
    end = fires["window"].split("..")[-1]
    fm, fd = (int(x) for x in end.split("-"))
    fir = "%d %s" % (fd, _MON[fm - 1])
    return "crops to dekad %s &middot; fires week to %s" % (cro, fir)


def _crops_rows(names):
    d = json.loads((ROOT / "crops/data/stress_current.json").read_text())
    by = {p["place"]: p for p in d["places"]}
    out = []
    for n in names:
        p = by.get(n)
        if not p:
            out.append({"name": n, "state": "no_roster"})
            continue
        sev = p.get("severity") or {}
        if not sev.get("available") or sev.get("rank") is None:
            out.append({"name": n, "state": "blind"})
            continue
        out.append({"name": n, "state": "measured",
                    "rank": sev["rank"], "of": sev["of"],
                    "slug": p.get("_slug") or n.lower().replace(" ", "-"),
                    "regions": (p.get("aggregate") or {}).get("regions_averaged")})
    return out


def _fires_rows(iso_names):
    d = json.loads((ROOT / "fires/data/current_week.json").read_text())
    cs = d["countries"]
    out = []
    for iso, n in iso_names:
        e = cs.get(iso)
        if not e:
            out.append({"name": n, "state": "no_roster"})
            continue
        # THE VERDICT COMES FROM FIRE, NOT FROM ARITHMETIC HERE. Their
        # fix, and the diagnosis is theirs and better than mine: the
        # payload used to ship a numerator and a denominator with the
        # gates kept somewhere else, computed only for the ~18 countries
        # that qualify as events. A regional table needs a figure for all
        # 97, so dividing count by mean was the only move available, and
        # that division is trivially correct and carries none of the
        # gating.
        #
        # A guard inside the code path that skips a country cannot protect
        # a consumer who never calls that path. 49 of 97 are not
        # publishable, so the obvious arithmetic was wrong on roughly
        # every other country.
        #
        # So this reads `reading` and never recomputes count/mean. Their
        # `means` string says so outright: "Do not compute count/mean
        # yourself; that is this field without its gates."
        rd = e.get("reading") or {}
        if not rd:
            out.append({"name": n, "state": "blind"})
            continue
        if not rd.get("publishable"):
            out.append({"name": n, "state": "withheld",
                        "why": rd.get("withheld_because"),
                        "count": rd.get("count") or e.get("count") or 0})
            continue
        out.append({"name": n, "state": "measured",
                    "mult": rd["multiple"], "count": rd["count"]})
    return out


def _noise_floor():
    """The floor fires publishes, read from fires' own method block.

    Kept only for the copy: the DECISION is fire's `publishable` field
    now, and this template no longer applies a threshold of its own.
    """
    try:
        m = json.loads((ROOT / "data/events.json").read_text())["method"]
        return int(m["noise_floor_detections"])
    except (OSError, KeyError, ValueError, TypeError):
        return 150


_NOISE_FLOOR = _noise_floor()


# LatAm, in the order a reader scans a map: north to south, Caribbean
# alongside. Fixed and editorial, never sorted by severity, for the same
# reason the crops instrument rows are fixed (D-182): a page that reorders
# itself to match its own data is the AUTHOR of the pattern it shows.
LATAM = [
    ("MEX", "Mexico"), ("BLZ", "Belize"), ("GTM", "Guatemala"),
    ("SLV", "El Salvador"), ("HND", "Honduras"), ("NIC", "Nicaragua"),
    ("CRI", "Costa Rica"), ("PAN", "Panama"),
    ("CUB", "Cuba"), ("HTI", "Haiti"), ("DOM", "Dominican Republic"),
    ("JAM", "Jamaica"),
    ("COL", "Colombia"), ("VEN", "Venezuela"), ("GUY", "Guyana"),
    ("SUR", "Suriname"), ("ECU", "Ecuador"), ("PER", "Peru"),
    ("BRA", "Brazil"), ("BOL", "Bolivia"), ("PRY", "Paraguay"),
    ("CHL", "Chile"), ("ARG", "Argentina"), ("URY", "Uruguay"),
]


def _band(rank, of):
    """Where a country sits in its own record. Bands, not a rank line.

    Four bands over 26 observations, because a reader cannot hold 26
    positions but can hold "worst few", "bad", "ordinary", "better than
    usual". Cuts at 4, 9 and 18 put roughly a sixth, a fifth and a third
    in the first three.
    """
    if rank is None:
        return None
    f = rank / of
    return 0 if rank <= 4 else (1 if f <= 0.34 else (2 if f <= 0.7 else 3))


def _fire_band(m):
    if m is None:
        return None
    return 0 if m >= 3 else (1 if m >= 1.5 else (2 if m >= 0.75 else 3))


CSS = """
.rgwrap{max-width:900px;margin:0 auto;padding:26px 24px 80px}
.rglede{font-family:var(--serif);font-size:30px;line-height:1.2;
  letter-spacing:-.012em;margin:16px 0 12px;max-width:24ch}
.rgstand{font-size:17px;line-height:1.6;color:var(--ink-soft);
  max-width:64ch;margin:0 0 30px}
.rgsec{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-faint);margin:34px 0 0;padding-bottom:8px;
  border-bottom:1px solid var(--ink)}
/* Every year in the record, drawn. The rank alone hides how far apart
   the years are, and the whole point here is that 2026 sits below a year
   we are calling the slowest on record. */
.amwrap{margin:16px 0 0;max-width:620px}
.amrow{display:grid;grid-template-columns:42px 1fr 56px;align-items:center;
  gap:0 10px;padding:2px 0}
.amy{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  color:var(--ink-faint);font-variant-numeric:tabular-nums}
.ambar{height:11px;border-radius:1px;background:var(--rule)}
/* D-043: the two named years are marked by ink, not by brightness, so a
   quiet year is as legible as a loud one. */
.am-o{background:var(--rule)}
.am-an{background:var(--ink-soft)}
.am-cur{background:var(--fire)}
.amv{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  color:var(--ink-soft);text-align:right;font-variant-numeric:tabular-nums}
.rgnote{font-size:14.5px;line-height:1.55;color:var(--ink-soft);
  max-width:66ch;margin:12px 0 0}
/* Wide content scrolls inside its own container; the page body
   must never scroll sideways. At 536px the four columns pushed
   the whole document to 691px. */
.rgscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.rg{width:100%;min-width:520px;border-collapse:collapse;margin:14px 0 0;font-size:15px}
table.rg th{text-align:left;font-family:"__D__",ui-monospace,monospace;
  font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  font-weight:600;color:var(--ink-faint);padding:0 10px 8px 0;
  border-bottom:1px solid var(--rule)}
table.rg th.n,table.rg td.n{text-align:right;white-space:nowrap}
table.rg td{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule);
  vertical-align:baseline}
td.cty{font-weight:500}
td.n{font-family:"__D__",ui-monospace,monospace;font-size:14px;
  font-variant-numeric:tabular-nums}
/* Four bands, ink only. A calm reading is drawn at the same weight as a
   loud one (D-043): nothing here recedes, so "quiet" is a value a reader
   can see rather than an empty cell they skip. */
.b0{color:var(--ink);font-weight:600}
.b1{color:var(--ink)}
.b2{color:var(--ink-soft)}
.b3{color:var(--ink-soft)}
.na{color:var(--ink-faint);font-style:italic;font-family:var(--serif);
  font-size:14px}
/* The count the multiple is computed from, next to the multiple. Muted
   and smaller: it qualifies the reading rather than competing with it. */
.sub{display:block;font-size:10.5px;color:var(--ink-faint);
  font-weight:400;letter-spacing:.02em;margin-top:1px}
.thsub{text-transform:none;letter-spacing:0;font-weight:400;
  font-size:9.5px;color:var(--ink-faint)}
.rgkey{display:flex;flex-wrap:wrap;gap:6px 18px;margin:12px 0 0;
  font-family:"__D__",ui-monospace,monospace;font-size:10.5px;
  color:var(--ink-faint)}
@media(max-width:620px){.rglede{font-size:24px}table.rg{font-size:14px}}
"""


def _cell(row, kind):
    """One reading, or the reason there is not one. Never an empty cell."""
    st = row["state"]
    if st == "no_roster":
        return '<td class="n na">not measured</td>'
    if st == "blind":
        return '<td class="n na">no reading</td>'
    if st == "withheld":
        why = row.get("why")
        if why == "persistent_source":
            return ('<td class="n na">measured, but this heat does not '
                    'behave like fire<span class="sub">%s detections, '
                    'flagged a persistent source</span></td>'
                    % _thousands(row["count"]))
        if why == "below_noise_floor":
            return ('<td class="n na">measured, but too thin to place'
                    '<span class="sub">%s detections, floor is %d</span>'
                    '</td>' % (_thousands(row["count"]), _NOISE_FLOOR))
        return ('<td class="n na">not published<span class="sub">%s</span>'
                '</td>' % h(str(why or "withheld by the fire channel")))
    if kind == "crops":
        b = _band(row["rank"], row["of"])
        return ('<td class="n b%d">%s of %s</td>' % (b, row["rank"], row["of"]))
    # COLOUR CODES THE MULTIPLE. Kristjan's call, 2026-08-30, asked
    # directly because the alternative was defensible: a country's position
    # against its own record is the more robust statistic when the baseline
    # is small.
    #
    # WHAT THE MULTIPLE RESTS ON TRAVELS WITH IT (D-051), which is the part
    # that is mine rather than his. Jamaica reads 5.43x on a baseline mean
    # of 12.9 detections and Cuba reads 10.88x on 68.4, and both draw the
    # heaviest weight on the page from the same rule. Printing the count
    # beside the multiple lets a reader see that one of those rests on 70
    # detections and the other on 744, without softening either or
    # second-guessing the colour rule.
    b = _fire_band(row["mult"])
    return ('<td class="n b%d">%.2f&times;<span class="sub">%s</span></td>'
            % (b, row["mult"], _thousands(row["count"])))


def _thousands(n):
    return "{:,}".format(int(n))


# Which published flood pieces sit inside this region. Matched on the
# payload's own region_id rather than on the label, because a label is
# prose and gets reworded.
_LATAM_FLOOD_IDS = ("lima_coast", "s_peru_altiplano", "n_chile_atacama",
                    "yungas_bolivia", "andes_amazon_peru")


def _flood_note(root_prefix):
    """The flood pieces covering this region, counted from what is published.

    THIS SAID "One flood finding exists for this region" AND NAMED LIMA.
    Two more published on 2026-08-30, both inside it, so the sentence was
    false within hours of the pieces going live and nothing on either page
    could have told anyone. Same failure as the three coverage notes above
    and the corridor list: a typed claim about a set that grows.
    """
    import sys
    sys.path.insert(0, str(ROOT))
    from templates.floods_index import _pieces
    try:
        pieces = [p for p in _pieces("2026-08-30")
                  if any(i in p["path"] for i in _LATAM_FLOOD_IDS)]
    except Exception:
        pieces = []
    if not pieces:
        return ""
    links = ", ".join(
        '<a href="%s%s">%s</a>' % (root_prefix.rstrip("/"), p["path"],
                                   p["region"])
        for p in pieces)
    _W = ("no", "One", "Two", "Three", "Four", "Five", "Six")
    n = len(pieces)
    return ('<p class="rgnote">%s flood %s cover%s this region: %s. They '
            'are not in this table because floods publishes by catchment '
            'rather than by country, and because each measures RAINFALL '
            'rather than flooding.</p>'
            % (_W[n] if n < len(_W) else n,
               "piece" if n == 1 else "pieces",
               "s" if n == 1 else "", links))


AREA_HISTORY = ROOT / "fires" / "data" / "area_history"


def _amazon_2015():
    """Where 2026 sits against 2015 on Brazil's burnt area, one instrument.

    THE WHOLE MODULE IS ONE INSTRUMENT ON PURPOSE. burnt_area.json says in
    its own header that hectares and detections measure different things
    and are never converted into each other, and aftereffects reached for
    a bare 0.40x from one and a 0.52x from the other in the same paragraph
    without naming either. Both were true. So this reads cumulative burnt
    area, per year, at the same Copernicus week number, and nothing here
    is a detection count.

    THE WEEK IS COPERNICUS'S OWN WEEK NUMBER, not a calendar date, and
    their file computes the cross-year comparison server-side. I asked
    rather than inferred it, because Brazil's fire year has a steep
    September and a week's misalignment moves the denominator more here
    than anywhere else we map.

    Every figure is derived. Nothing in this function is typed except the
    country and the shape of the sentence.
    """
    try:
        d = json.loads((AREA_HISTORY / "BRA.json").read_text())["years"]
    except (OSError, KeyError, ValueError):
        return ""
    cur = max((y for y in d), key=int)
    wk = max((int(w) for w in d[cur]), default=0)
    if not wk:
        return ""
    at = {y: d[y].get(str(wk)) for y in d if d[y].get(str(wk)) is not None}
    if cur not in at or len(at) < 5:
        return ""

    order = sorted(at, key=lambda y: -at[y])
    rank = order.index(cur) + 1
    complete = [y for y in d
                if y != cur and max(int(w) for w in d[y]) >= 52]
    share = {}
    for y in complete:
        tot = d[y][str(max(int(w) for w in d[y]))]
        if tot:
            share[y] = at[y] / tot * 100
    slow = sorted(share, key=lambda y: share[y])
    tot_rank = sorted(complete,
                      key=lambda y: -d[y][str(max(int(w) for w in d[y]))])

    an = slow[0]                       # the slowest start on record
    an_finish = tot_rank.index(an) + 1
    ratio = at[cur] / at[an] if at[an] else 0

    bars = []
    hi = max(at.values())
    for y in sorted(at, key=int):
        w = at[y] / hi * 100
        cls = ("am-cur" if y == cur else "am-an" if y == an else "am-o")
        bars.append(
            '<div class="amrow"><span class="amy">%s</span>'
            '<span class="ambar %s" style="width:%.1f%%"></span>'
            '<span class="amv">%.1fM</span></div>'
            % (y, cls, w, at[y] / 1e6))

    # TWO CLAIMS ON TWO SCALES, AND THE PAGE NAMED NEITHER. Fire caught
    # it. "Slowest start on record" is TRUE as a share of each year's own
    # eventual season (2015 is 1 of 14 at 22.8%) and FALSE in absolute
    # hectares, where four years started lower and 2015 is 5th of 14.
    # "2026 is slower still" can ONLY be absolute, because 2026's share
    # of its own final is unknowable while the season is running. Each
    # sentence was defensible; they could not both be true on one scale.
    abs_low = sorted(complete, key=lambda y: at[y])
    an_abs = abs_low.index(an) + 1

    return (
        '<p class="rgsec" style="margin-top:40px">Brazil against its own '
        'slowest year, at the same week</p>'
        '<p class="rgnote" style="margin-top:12px"><b>%s completed less of '
        'its season by this week than any year on record, %.1f%% of its '
        'eventual total, and still finished %s of %d. Measured in hectares '
        'burned so far, %s is lower than %s was at the same point.</b> '
        'Those are two different measures. On hectares alone %s ranks %s '
        'of %d at this week rather than first; its claim to the slowest '
        'start is about the SHARE of its own season completed, which '
        'cannot be computed for %s until %s ends.</p>'
        '<p class="rgnote">Cumulative burnt area by Copernicus week %d: '
        '%s has %.1f million hectares against %s&rsquo;s %.1f million, '
        '%.2f times it, and ranks %d of %d years including this one. The '
        'next slowest share after %s is %.1f%%.</p>'
        '<div class="amwrap">%s</div>'
        '<p class="rgnote">Burnt area, not detections. The two measure '
        'different things and are never converted into each other, so no '
        'figure here is a fire count. Where %s finishes is not forecast '
        'from this: a slow start is what %s also had.</p>'
        % (an, share[an], _nth_word(an_finish), len(complete),
           cur, an,
           an, _nth_word(an_abs), len(complete), cur, cur,
           wk, cur, at[cur] / 1e6, an, at[an] / 1e6, ratio, rank, len(at),
           an, share[slow[1]],
           "\n".join(bars), cur, an))


def _nth_word(n):
    return {1: "first", 2: "second", 3: "third", 4: "fourth"}.get(
        n, "%dth" % n)


def _fires_limit(names):
    """What the fires column counts, and what it cannot tell apart.

    Product's first instinct was to drop the column until a per-country
    qualifier existed. They withdrew it: LEAVING IT OUT IS ITSELF AN
    ABSENCE-AS-ZERO, and it deletes the quiet-continent reading that is
    half of why this page exists. What makes a column dishonest is
    silence, not the lack of a per-row field.

    BOTH SIDES OF THE CONTRAST ARE NAMED NOW. I first wrote "Cuba's
    detections fall on cropland far more often than chance, and Brazil's
    do not", cut the Brazil half as unsupportable, and was wrong to: I had
    looked in events.json, which is the QUALIFYING list, and concluded
    Brazil had no reading. Fire corrected it. current_week.json carries
    cropland for 86 of the 97 countries in the roster, qualifying or not,
    which is the same roster-versus-qualifying-list mistake I made once
    already on this page and then made again one field over.

    Both readings clear fire's own floor of 50 detections on cropland, so
    neither rests on noise: Cuba on 208, Brazil on 528.
    """
    try:
        cw = json.loads((ROOT / "fires/data/current_week.json").read_text())
        ev = json.loads((ROOT / "data/events.json").read_text())["events"]
    except (OSError, KeyError, ValueError):
        return ""
    floor = 50
    try:
        floor = int(json.loads((ROOT / "data/events.json").read_text())
                    ["method"]["cropland_min_detections_on_crop"])
    except (OSError, KeyError, ValueError, TypeError):
        pass

    here = []
    for e in (cw.get("countries") or {}).values():
        if e.get("name") not in names:
            continue
        cl = e.get("cropland") or {}
        if not cl.get("reading") or cl.get("ratio") is None:
            continue
        if (cl.get("detections_on_crop") or 0) < floor:
            continue
        here.append((e["name"], cl))
    if len(here) < 2:
        return ""

    rich = [x for x in here if x[1]["reading"] == "enriched"]
    poor = [x for x in here if x[1]["reading"] == "depleted"]
    if not rich or not poor:
        return ""
    hi = max(rich, key=lambda x: x[1]["ratio"])
    lo = min(poor, key=lambda x: x[1]["ratio"])

    means = ""
    for e in ev:
        m = (e.get("land_use") or {}).get("means")
        if m:
            means = m
            break

    return (
        '<p class="rgnote" style="border-top:2px solid var(--ink);'
        'padding-top:14px;margin-top:22px"><b>This column counts thermal '
        'detections against each country&rsquo;s own normal week. It does '
        'not distinguish agricultural burning from wildfire.</b> In this '
        'region that difference is large and measured: %s&rsquo;s '
        'detections fall on cropland %.1f times more often than chance, '
        'and %s&rsquo;s %.1f times LESS often. Same instrument, same week, '
        'opposite phenomena. %s</p>'
        % (h(hi[0]), hi[1]["ratio"], h(lo[0]), 1.0 / lo[1]["ratio"],
           h(means)))


def _coverage_notes(crops, fires, names, worst):
    """How far each instrument reaches, counted rather than remembered.

    ALL THREE OF THESE WERE TYPED AND ALL THREE WENT STALE THE SAME DAY.
    They said fires reached 12 of 24 and crops placed 20 of 24; the
    payloads say 15 and 24. Crops grew from 123 places to 165 when
    MIN_UNITS dropped to 1, which admitted Belize, the Dominican Republic
    and Jamaica, so the paragraph explaining why those three could not be
    ranked was describing a rule that no longer applied to them.

    Worse than the counts: the fires note claimed every country in the
    corridor was outside the fire instrument, and Colombia is in the
    corridor and measured. That one was wrong when written, not merely
    stale, and no number on the page contradicted it.
    """
    tot = len(names)
    fm = [n for n in names if fires[n]["state"] == "measured"]
    cm = [n for n in names if crops[n]["state"] == "measured"]
    out = ['<p class="rgnote"><b>Heat is not measured anywhere in Latin '
           'America.</b> All 45 cities on that channel are European. This '
           'row is empty because the instrument does not reach here, not '
           'because the nights are ordinary.</p>']

    blind = [n for n in worst if fires[n]["state"] != "measured"]
    fire_note = ("<b>Fires reaches %d of these %d countries.</b> "
                 % (len(fm), tot))
    if blind:
        fire_note += (
            "%d of the %d countries in the run above %s outside it, so "
            "some of the worst crop stress on this page sits where the "
            "fire instrument cannot see. That is a limit of our coverage "
            "and not a finding about those countries."
            % (len(blind), len(worst), "is" if len(blind) == 1 else "are"))
    else:
        fire_note += ("Every country in the run above is inside it, so the "
                      "two instruments can be read against each other "
                      "there.")
    out.append('<p class="rgnote">%s</p>' % fire_note)

    from templates.region_map import readings as _map_readings
    mr = _map_readings()
    thin = [n for n in names if (mr.get(n, {}).get("crops") or {}).get(
        "state") == "thin"]
    placed = len(cm) - len(thin)
    if thin:
        out.append(
            '<p class="rgnote"><b>Crops measures all %d and places %d.</b> '
            '%s %s a rank against %s own 26 years, but %s measured on too '
            'few regional readings to sit on the map&rsquo;s scale. '
            'Measured and placeable are different things, and the second '
            'is a limit of the drawing rather than of the data.</p>'
            % (len(cm), placed, ", ".join(thin),
               "has" if len(thin) == 1 else "have",
               "its" if len(thin) == 1 else "their",
               "is" if len(thin) == 1 else "are"))
    else:
        out.append('<p class="rgnote"><b>Crops places all %d.</b> Every '
                   'country in this table has a rank against its own 26 '
                   'years and sits on the map.</p>' % tot)
    return "\n".join(out)


def render(root_prefix="../"):
    import sys
    sys.path.insert(0, str(ROOT))
    import tokens as T
    from templates.page_head import head_meta
    from run_brief import (site_masthead, SITE_MASTHEAD_CSS,
                           ANALYTICS_SNIPPET)
    from templates.subscribe_band import band as sub_band, css as sub_css

    names = [n for _, n in LATAM]
    crops = {r["name"]: r for r in _crops_rows(names)}
    fires = {r["name"]: r for r in _fires_rows(LATAM)}

    # THE LEDE IS DERIVED, NEVER TYPED (D-124), AND SO IS THE SET IT
    # COUNTS. The count was already derived; the countries it counted over
    # were a hand-typed list, so the claim was only as current as that
    # list. It said seven while product said eight, and product was right:
    # Belize is measured at rank 3 of 26 as of the 2026-08-30 rebuild,
    # having been one of the 42 single-unit countries admitted when
    # MIN_UNITS dropped to 1. It was excluded here because it was absent
    # from the crops roster when this was written, and nothing re-examined
    # that when the roster grew by 42.
    #
    # ADJACENCY IS GEOGRAPHY AND THE FINDING IS DATA. So the isthmus chain
    # is stated once, north to south, and the claim is the LONGEST
    # UNBROKEN RUN within it. That also makes "without a gap" true by
    # construction rather than asserted by whoever typed the list: the
    # previous version could not have detected a gap in the middle.
    ISTHMUS = ["Mexico", "Belize", "Guatemala", "El Salvador", "Honduras",
               "Nicaragua", "Costa Rica", "Panama", "Colombia"]

    def _deep(n):
        r = crops.get(n) or {}
        return r.get("state") == "measured" and r.get("rank", 99) <= 4

    worst, run = [], []
    for n in ISTHMUS + [None]:
        if n is not None and _deep(n):
            run.append(n)
            continue
        if len(run) > len(worst):
            worst = run
        run = []
    quiet = [n for n in names
             if fires[n]["state"] == "measured" and fires[n]["mult"] < 0.5]

    rows = []
    for iso, n in LATAM:
        rows.append(
            "<tr><td class=\"cty\">%s</td>%s%s"
            "<td class=\"n na\">not measured</td></tr>"
            % (n, _cell(crops[n], "crops"), _cell(fires[n], "fires")))

    _W = ("no", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
          "Eight", "Nine", "Ten", "Eleven", "Twelve")
    lede = ("%s neighbouring countries are each having one of their four "
            "worst crop years in 26."
            % (_W[len(worst)] if len(worst) < len(_W) else len(worst)))
    stand = (
        "They run from %s to %s without a gap: %s. Each is "
        "measured only against its own record. At the same moment the "
        "southern half of the continent is having an unusually QUIET fire "
        "week: %s %s below half their normal for this week of the "
        "year. Both are findings. Neither is visible on a channel page, "
        "which shows only what qualified, or on a country page, which "
        "shows one place."
        % (worst[0], worst[-1],
           ", ".join(worst[:-1]) + " and " + worst[-1],
           (", ".join(quiet[:-1]) + " and " + quiet[-1]) if len(quiet) > 1
           else quiet[0],
           "all sit" if len(quiet) > 2 else
           ("both sit" if len(quiet) == 2 else "sits")))

    from templates.region_map import block as map_block, CSS as MAP_CSS
    body = """
<p class="rgsec">Four instruments, one region, one week</p>
__MAPS__
__AMAZON__
__FIRES_LIMIT__
<p class="rgsec" style="margin-top:40px">Every country we measure, and every one we do not</p>
<div class="rgscroll"><table class="rg">
<tr><th>Country</th><th class="n">Crops, against its own 26 years</th>
<th class="n">Fires, against its own normal week<br><span class="thsub">and the detections it is computed from</span></th>
<th class="n">Heat</th></tr>
%s
</table></div>
<div class="rgkey"><span>CROPS: rank 1 is the worst year on that country's
own record</span><span>FIRES: 1.0&times; is its own normal week</span></div>
__COVERAGE_NOTES__
__FLOOD_NOTE__
""" % "\n".join(rows)
    body = body.replace("__COVERAGE_NOTES__", _coverage_notes(crops, fires,
                                                              names, worst))
    body = body.replace("__FLOOD_NOTE__", _flood_note(root_prefix))
    body = body.replace("__FIRES_LIMIT__", _fires_limit(set(names)))
    body = body.replace("__AMAZON__", _amazon_2015())
    body = body.replace("__MAPS__", map_block(root_prefix))

    css = (CSS.replace("__D__", T.FONT_DATA)
           + MAP_CSS.replace("__D__", T.FONT_DATA) + sub_css()
           + SITE_MASTHEAD_CSS)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
%s
<title>Latin America | The Long Swell</title>
<style>
%s
:root {{ {vars} }}
</style>
</head>
<body>
%s
<main class="rgwrap">
  <p class="rgsec" style="border:0;margin-top:6px">Latin America &middot;
     %s</p>
  <h1 class="rglede">%s</h1>
  <p class="rgstand">%s</p>
  %s
  %s
</main>
</body>
</html>
""".replace("{vars}", T.css_variables()) % (
        ANALYTICS_SNIPPET,
        head_meta(title="Latin America | The Long Swell",
                  description=lede, path="/latin-america/"),
        T.font_faces_css(root_prefix + "fonts/") + css,
        site_masthead(root_prefix), _dateline(), lede, stand, body,
        sub_band())
