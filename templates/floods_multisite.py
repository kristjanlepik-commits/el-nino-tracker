#!/usr/bin/env python3
"""A flood piece with many sites, a hydrograph, and outside corroboration.

WHY THIS IS NOT build_piece. That builder takes a payload shaped as one
region with a `series` list, and renders one basin against its own record.
This payload is a different object: one finding, seven named places, a
daily hydrograph, an alert location on the far side of a continental
divide, and the first `event_corroboration: true` this channel has had.
Bolting the second shape onto the first would have made both harder to
read, so the two live apart and share the house furniture.

THE ORDER IS FLO'S AND IT IS AN ARGUMENT, not a layout:

  1. Rain across the Yungas on 17-18 August, every river at a 48-year
     high on the 19th.
  2. Seven towns Bolivian reporting named three days later. All seven.
  3. Caranavi: 16 mm of local rain, a river at 620 m3/s, because it sits
     downstream and collects from the catchments above it.
  4. Only then the warnings, 1,128 km away across the divide.

The alert comes LAST deliberately. "The warning pointed the wrong way" is
a claim about other people; "a river at a 48-year high under ordinary
rain" is a claim about the world. The editor's call and it is right.

TWO THINGS THIS PAGE MUST NEVER SAY, both of them FLO's instruction:
nobody has been counted, so nothing here may imply we know how many
people were affected; and the national figure of families affected covers
snowfall, rain and floods countrywide and has never been traced to this
event. Neither is in the payload, which is the best guard available.

DISCHARGE IS MODELLED AND SAYS SO EVERY TIME IT APPEARS. GloFAS is
LISFLOOD forced by reanalysis precipitation, not a gauge. `modelled` is a
separate flag rather than part of the instrument string, at my request and
for this reason: a page then cannot name the instrument without stating
that it is a model.
"""
import json
import sys
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_MON = ("January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December")


def _day(iso, year=False):
    y, m, d = (int(x) for x in iso.split("-"))
    return "%d %s%s" % (d, _MON[m - 1], " %d" % y if year else "")


def _window_words(w):
    a, b = w["start"], w["end"]
    ya, ma, da = (int(x) for x in a.split("-"))
    yb, mb, db = (int(x) for x in b.split("-"))
    if (ya, ma) == (yb, mb):
        return "%d to %d %s %d" % (da, db, _MON[ma - 1], yb)
    return "%s to %s %d" % (_day(a), _day(b), yb)


def _rain(place):
    """Per-site rainfall, whichever key it is under.

    FLO is renaming `rain_17_22_mm` to `rain_mm` with the window alongside,
    because a key that encodes a window is wrong the moment the window
    moves. Reading both means the rename does not need to land in the same
    commit as this page.

    I nearly reported these figures as missing: my first probe asked for
    `rain_mm`, got None on all seven, and seven consecutive Nones read as
    "these do not exist" rather than "I am asking the wrong question".
    A wrong key and an absent value look identical from here.
    """
    for k in ("rain_mm", "rain_17_22_mm"):
        if place.get(k) is not None:
            return place[k]
    return None


def _hydrograph_svg(hyd, rain_by_day):
    """Rain, then river, one day later. The mechanism, drawn.

    The whole causal claim is a lag: 62.8 mm across two days and a
    hundredfold discharge spike on the third. Drawn, a reader sees it
    before reading a word; described, they have to take it on trust.
    """
    days = hyd["days"]
    q = hyd["discharge_m3s"]
    if not days or not q:
        return ""
    W, H = 860, 250
    left, right, top, bot = 46, W - 14, 16, H - 34
    n = len(days)
    qmax = max(q) or 1.0
    rmax = max([v for v in rain_by_day.values() if v is not None] or [1]) or 1.0

    def X(i):
        return left + (right - left) * (i / max(1, n - 1))

    def Yq(v):
        return bot - (bot - top) * (v / qmax)

    # Rain as columns from the top, so the two series cannot be read as
    # one line: rain falls, the river answers.
    bars = []
    for i, d in enumerate(days):
        key = d[5:]
        v = rain_by_day.get(key)
        if not v:
            continue
        hgt = (bot - top) * 0.38 * (v / rmax)
        bars.append(
            '<rect x="%.1f" y="%.1f" width="7" height="%.1f" '
            'fill="var(--flood)" fill-opacity="0.30"/>'
            % (X(i) - 3.5, top, hgt))

    line = " ".join("%.1f,%.1f" % (X(i), Yq(v)) for i, v in enumerate(q))
    peak = hyd.get("peak_day")
    pi = days.index(peak) if peak in days else q.index(max(q))
    ticks = []
    for i, d in enumerate(days):
        if i % 4 == 0 or i == pi:
            ticks.append('<text x="%.1f" y="%d" text-anchor="middle" '
                         'font-size="9.5" fill="var(--ink-faint)">%s</text>'
                         % (X(i), H - 18, d[8:]))
    return (
        '<div class="fmfig"><svg viewBox="0 0 %d %d" role="img" '
        'aria-label="Daily rainfall as columns and modelled river '
        'discharge as a line, %s to %s. Discharge peaks one day after the '
        'heaviest rain.">'
        '%s'
        '<polyline points="%s" fill="none" stroke="var(--flood)" '
        'stroke-width="2.2"/>'
        '<circle cx="%.1f" cy="%.1f" r="4" fill="var(--flood)"/>'
        '<text x="%.1f" y="%.1f" font-size="11" text-anchor="middle" '
        'fill="var(--ink)">%s</text>'
        '%s'
        '</svg>'
        '<p class="fmcap"><b>Columns are rainfall. The line is modelled '
        'discharge.</b> The river answers the day after the rain: %s on '
        'the %s, a peak of %s m&sup3;/s on the %s, against a quiet level '
        'of %s.</p></div>'
        % (W, H, days[0], days[-1],
           "".join(bars), line,
           X(pi), Yq(q[pi]),
           X(pi), Yq(q[pi]) - 10, "%.0f" % q[pi],
           "".join(ticks),
           "%.1f mm" % max(rain_by_day.values() or [0]),
           _day("2026-" + max(rain_by_day, key=lambda k: rain_by_day[k] or 0))
           if rain_by_day else "",
           "{:,.0f}".format(hyd["peak_value"]), _day(peak),
           "%.1f" % hyd.get("quiet_level", 0)))


def _places_rows(places):
    out = []
    for p in sorted(places, key=lambda x: -x["discharge_m3s"]):
        r = _rain(p)
        out.append(
            '<tr><td class="fmn">%s</td>'
            '<td class="fmv">%s</td>'
            '<td class="fmv">%.1f&times;</td>'
            '<td class="fmv">%s of %s</td>'
            '<td class="fmv">%s</td></tr>'
            % (h(p["name"]), "{:,.0f}".format(p["discharge_m3s"]),
               p["x_median"], p["rank"], p["of"],
               ("%.0f mm" % r) if r is not None else "not measured"))
    return "\n".join(out)


CSS = """
.fmwrap{max-width:820px;margin:0 auto;padding:26px 24px 80px}
.fmkick{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  letter-spacing:.09em;text-transform:uppercase;color:var(--ink-faint);
  margin:6px 0 0}
.fmlede{font-family:var(--serif);font-size:31px;line-height:1.18;
  letter-spacing:-.012em;margin:14px 0 12px;max-width:26ch}
.fmstand{font-size:17px;line-height:1.62;color:var(--ink-soft);
  max-width:64ch;margin:0 0 8px}
/* Corroboration is a statement the page makes, not a hedge under it. */
.fmcorr{border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);
  padding:14px 0 15px;margin:22px 0 0;max-width:64ch}
.fmcorr b{font-family:var(--serif);font-size:18px;line-height:1.35;
  display:block;margin-bottom:6px}
.fmcorr span{font-size:14.5px;line-height:1.55;color:var(--ink-soft)}
.fmsec{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-faint);margin:36px 0 0;padding-bottom:8px;
  border-bottom:1px solid var(--ink)}
.fmfig{margin:16px 0 0}
.fmfig svg{width:100%;height:auto;display:block}
.fmcap{font-size:14px;line-height:1.55;color:var(--ink-soft);
  max-width:64ch;margin:8px 0 0}
.fmscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.fm{width:100%;min-width:520px;border-collapse:collapse;
  margin:14px 0 0;font-size:15px}
table.fm th{text-align:left;font-family:"__D__",ui-monospace,monospace;
  font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  font-weight:600;color:var(--ink-faint);padding:0 10px 8px 0;
  border-bottom:1px solid var(--rule)}
table.fm th.n,table.fm td.fmv{text-align:right;white-space:nowrap}
table.fm td{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule)}
.fmn{font-weight:500}
.fmv{font-family:"__D__",ui-monospace,monospace;font-size:14px;
  font-variant-numeric:tabular-nums}
.fmnote{font-size:14.5px;line-height:1.55;color:var(--ink-soft);
  max-width:64ch;margin:16px 0 0}
.fmpull{border-left:3px solid var(--flood);padding:2px 0 2px 14px;
  margin:18px 0 0;max-width:62ch;font-size:16px;line-height:1.55}
.fmlim{font-size:14px;line-height:1.55;color:var(--ink-faint);
  max-width:64ch;margin:10px 0 0}
@media(max-width:620px){.fmlede{font-size:25px}}
"""


def render(payload, root_prefix="../../"):
    sys.path.insert(0, str(ROOT))
    import tokens as T
    from templates.page_head import head_meta
    from run_brief import (site_masthead, SITE_MASTHEAD_CSS,
                           ANALYTICS_SNIPPET)
    from templates.subscribe_band import band as sub_band, css as sub_css

    win = _window_words(payload["window"])
    f = payload["finding"]
    rain, disc = f["rainfall"], f["discharge"]
    places = payload["named_places"]
    hyd = payload["hydrograph"]
    ec = payload["event_corroboration"]
    alert = payload["alert_location"]
    inst = payload["instruments"]

    n = len(places)
    all_first = all(p["rank"] == 1 for p in places)
    of = places[0]["of"] if places else 0
    _W = ("no", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
          "Eight", "Nine", "Ten")
    word = _W[n] if n < len(_W) else str(n)

    # DERIVED, NEVER TYPED. Every number in the lede and standfirst comes
    # from the payload, so the sentence cannot outlive the data.
    lede = ("Rain fell across the Yungas, and every river %s named "
            "reached its highest in %s years." % (
                "Bolivian reporting" if all_first else "we checked", of))
    stand = (
        "%s towns were named in Bolivian reporting three days after the "
        "water came. Checked against their own %s-year records, %s. The "
        "reporting chose the places; we did not. Rainfall is measured; "
        "river discharge is MODELLED, not observed."
        % (word, disc.get("baseline_years", of - 1),
           "all %s rank first" % word.lower() if all_first
           else "%d of %d rank first" % (sum(1 for p in places
                                             if p["rank"] == 1), n)))

    downstream = [p for p in places if "downstream" in (p.get("note") or "")]
    pull = ""
    if downstream:
        d0 = downstream[0]
        r = _rain(d0)
        pull = (
            '<p class="fmpull"><b>%s is the one to look at.</b> %s mm of '
            'rain fell there and its river ran at %s m&sup3;/s, %.1f times '
            'its own median, because it sits downstream and collects from '
            'the catchments above it. The water did not fall on %s.</p>'
            % (h(d0["name"]), ("%.0f" % r) if r is not None else "Little",
               "{:,.0f}".format(d0["discharge_m3s"]), d0["x_median"],
               h(d0["name"])))

    corr = (
        '<div class="fmcorr"><b>A flood was declared here, and we dated '
        'the peak before reading any of it.</b><span>%s We put the peak on '
        '%s from rainfall and a routing model. The municipal damage report '
        'is dated %s. %s</span></div>'
        % (h(ec.get("detail", "")), _day(hyd["peak_day"]),
           _day("2026-08-20"), h(ec.get("limits", ""))))

    sweep = payload.get("sweep") or {}
    sweep_note = ""
    if sweep.get("river_cells"):
        below = sweep.get("cells_below_median")
        sweep_note = (
            '<p class="fmnote"><b>Regionally there is nothing to see, and '
            'that is the point.</b> Across %s river cells in Peru, Bolivia '
            'and northern Chile over the same days, %s rank first against '
            'their own records and %s sit below their own median. A region '
            'is the wrong unit for a flood that happened in a valley.</p>'
            % ("{:,}".format(sweep["river_cells"]),
               "{:,}".format(sweep.get("cells_rank1", 0)),
               "{:,}".format(below) if below else "most"))

    alert_r = alert.get("rainfall") or {}
    alert_note = (
        '<p class="fmnote"><b>The international alert was %s km away, on '
        'the other side of the divide.</b> On the same days the %s took '
        '%.2f mm against a median of %.2f, which is %s of %s years: drier '
        'than usual rather than wetter. Nothing we measure supports a '
        'flood there in this window.</p>'
        % ("{:,}".format(alert.get("km_from_flood", 0)), h(alert["name"]),
           alert_r.get("value", 0), alert_r.get("median", 0),
           alert_r.get("rank", "?"), alert_r.get("of", "?")))

    body = """
%s
<p class="fmstand">%s</p>
%s
<p class="fmsec">Rain, then river</p>
%s
<p class="fmsec">Every place the reporting named</p>
<div class="fmscroll"><table class="fm">
<tr><th>Place</th><th class="n">Discharge</th><th class="n">Against its
own median</th><th class="n">Rank</th><th class="n">Rain, %s</th></tr>
%s
</table></div>
<p class="fmnote">Discharge is <b>%s</b>: %s</p>
%s
%s
<p class="fmsec">What this does not say</p>
<p class="fmlim">Nobody has been counted. We do not know how many people
were affected, how many homes, or how much land. This page measures
rainfall and models river discharge; neither counts anyone.</p>
<p class="fmlim">%s</p>
""" % (corr, h(stand), pull,
       _hydrograph_svg(hyd, payload.get("daily_rain_mm") or {}),
       h(win), _places_rows(places),
       h(inst["discharge"]["string"]),
       h(inst["discharge"].get("modelled_note", "")),
       sweep_note, alert_note,
       h(ec.get("limits", "")))

    css = (CSS.replace("__D__", T.FONT_DATA) + sub_css() + SITE_MASTHEAD_CSS)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
%s
<title>%s | The Long Swell</title>
<style>
%s
:root {{ {vars} }}
</style>
</head>
<body>
%s
<main class="fmwrap">
  <p class="fmkick">Floods &middot; %s &middot; published %s</p>
  <h1 class="fmlede">%s</h1>
  %s
  %s
</main>
</body>
</html>
""".replace("{vars}", T.css_variables()) % (
        ANALYTICS_SNIPPET,
        head_meta(title="%s | The Long Swell" % payload["label"],
                  description=lede,
                  path="/floods/%s/" % payload["piece_id"].replace("_", "-")),
        h(payload["label"]), css, site_masthead(root_prefix, active="flood"),
        h(win), _day(payload["generated"], year=True), h(lede), body, sub_band())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = Path(args[0]) if args else None
    if src is None or not src.exists():
        raise SystemExit("usage: floods_multisite.py <payload.json> "
                         "[--publish]")
    payload = json.loads(src.read_text())
    html = render(payload)
    slug = payload["piece_id"].replace("_", "-")

    if "--publish" not in sys.argv:
        out = (Path("/private/tmp/claude-505/-Users-admin-Documents-Claude-"
                    "Projects-El-Nino-Tracker/"
                    "963b8065-d8cb-408a-9195-33d00aeda096/scratchpad")
               / ("preview_%s.html" % slug))
        out.write_text(html)
        print("preview: %s\n  Not in docs/; --publish once FLO signs off."
              % out)
        return

    out = ROOT / "docs" / "floods" / slug / "index.html"
    if out.exists():
        raise SystemExit(
            "REFUSING TO REBUILD %s: it is published and says so on its "
            "face. Invariant 5." % out.relative_to(ROOT))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print("PUBLISHED %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
