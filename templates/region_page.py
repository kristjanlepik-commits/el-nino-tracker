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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
        mean = e.get("mean")
        if not mean:
            out.append({"name": n, "state": "blind"})
            continue
        out.append({"name": n, "state": "measured",
                    "mult": e["count"] / mean, "count": e["count"]})
    return out


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
    if kind == "crops":
        b = _band(row["rank"], row["of"])
        return ('<td class="n b%d">%s of %s</td>' % (b, row["rank"], row["of"]))
    b = _fire_band(row["mult"])
    return '<td class="n b%d">%.2f&times;</td>' % (b, row["mult"])


def render(root_prefix="../"):
    import sys
    sys.path.insert(0, str(ROOT))
    import tokens as T
    from templates.page_head import head_meta
    from run_brief import site_masthead, SITE_MASTHEAD_CSS
    from templates.subscribe_band import band as sub_band, css as sub_css

    names = [n for _, n in LATAM]
    crops = {r["name"]: r for r in _crops_rows(names)}
    fires = {r["name"]: r for r in _fires_rows(LATAM)}

    # THE LEDE IS DERIVED, NEVER TYPED (D-124). Product said eight
    # contiguous countries; it is seven, and Belize would have made eight
    # but is not in the crops roster at all, so it could not have been
    # counted either way.
    corridor = ["Guatemala", "El Salvador", "Honduras", "Nicaragua",
                "Costa Rica", "Panama", "Colombia"]
    worst = [n for n in corridor
             if crops[n]["state"] == "measured" and crops[n]["rank"] <= 4]
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
        "week: %s all sit below half their normal for this week of the "
        "year. Both are findings. Neither is visible on a channel page, "
        "which shows only what qualified, or on a country page, which "
        "shows one place."
        % (worst[0], worst[-1],
           ", ".join(worst[:-1]) + " and " + worst[-1],
           ", ".join(quiet[:-1]) + " and " + quiet[-1]))

    from templates.region_map import block as map_block, CSS as MAP_CSS
    body = """
<p class="rgsec">Four instruments, one region, one week</p>
__MAPS__
<p class="rgsec" style="margin-top:40px">Every country we measure, and every one we do not</p>
<div class="rgscroll"><table class="rg">
<tr><th>Country</th><th class="n">Crops, against its own 26 years</th>
<th class="n">Fires, against its own normal week</th>
<th class="n">Heat</th></tr>
%s
</table></div>
<div class="rgkey"><span>CROPS: rank 1 is the worst year on that country's
own record</span><span>FIRES: 1.0&times; is its own normal week</span></div>
<p class="rgnote"><b>Heat is not measured anywhere in Latin America.</b>
All 45 cities on that channel are European. This row is empty because the
instrument does not reach here, not because the nights are ordinary.</p>
<p class="rgnote"><b>Fires reaches 12 of these 24 countries.</b> Every
country in the Central America corridor above is outside it, so the
countries with the worst crop stress on this page are exactly the ones the
fire instrument cannot see. That is a limit of our coverage and not a
finding about Central America.</p>
<p class="rgnote"><b>Crops places 20 of 24.</b> Belize, the Dominican Republic and
Jamaica are in ASAP's roster but report fewer than three crop units each,
and our sub-national method needs three, so they cannot be ranked here at
all. Suriname is measured and has a rank, but only four of a possible 28
regional readings carry cropland, which is too thin to place on this
scale.</p>
<p class="rgnote">One flood finding exists for this region, the Lima coast
over 6 to 19 August, and it reads 0.48&times; its median rainfall: drier
than usual rather than wetter. It is not in this table because floods
publishes by catchment rather than by country.</p>
""" % "\n".join(rows)
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
     crops to dekad 1 August &middot; fires week to 25 August</p>
  <h1 class="rglede">%s</h1>
  <p class="rgstand">%s</p>
  %s
  %s
</main>
</body>
</html>
""".replace("{vars}", T.css_variables()) % (
        head_meta(title="Latin America | The Long Swell",
                  description=lede, path="/latin-america/"),
        T.font_faces_css(root_prefix + "fonts/") + css,
        site_masthead(root_prefix), lede, stand, body, sub_band())
