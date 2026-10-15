"""Build "How a flood is made", the floods reader explainer (D-327, D-328).

Storyboard by FLO, order and visual direction by Kristjan. Scenes 1 and 5
are 3D (three.js, scroll by Motion); 2, 3 and 4 are flat maps and record
strips; 7 is the illustrative ground simulation beside measured topsoil
ranks; 8 is this weekend's map, added when AEMET's Friday update is out.

Inputs:
  assets      design/make_explainer_assets.py output (from FLO's payload)
  scene JS    design/explainer/scene_*.js
  words       copy/flood_explainer.md when it exists. Who writes them is
              Kristjan's call (a Note, D-093, or the editor). Until then
              every prose slot renders as a visible [WORDS] placeholder,
              and a publish build REFUSES while any remains.

Figure labels, legends and numbers are design's and come from the data.

Run:  .venv/bin/python design/make_flood_explainer.py --preview
      .venv/bin/python design/make_flood_explainer.py            (publish)
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                                # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,      # noqa: E402
                       SITE_NAME, h, site_masthead)
from templates.page_head import head_meta                         # noqa: E402
from templates.fast_reaction import _record_strip                 # noqa: E402
from templates.flood_explainer import (fig_ground, FIG_CSS,       # noqa: E402
                                       GROUND_JS)

SLUG = "floods/how-a-flood-is-made"
PATH = "/" + SLUG + "/"
PREVIEW = Path("/tmp/el_nino_preview") / SLUG
ASSETS = Path("/tmp/el_nino_preview/explainer3d/assets")

# Self-hosted, never a CDN on a published page (D-327; platform, 15 Oct).
# Relative paths only: qa_check rejects root-absolute src. The addons
# import a bare "three", which only the import map can resolve. The
# preview serves the same files, so what is checked is what ships.
VENDOR = {"three": "../../vendor/three-0.160.0/three.module.min.js",
          "three/addons/": "../../vendor/three-0.160.0/addons/"}
MOTION = "../../vendor/motion-11.11.13/motion.js"

# Prose slots, in page order. A slot is filled from copy/flood_explainer.md
# ("## slot-name" sections) or renders as a placeholder.
SLOTS = ["headline", "standfirst",
         "bath-1", "bath-2", "bath-3", "bath-4",
         "heat", "sea", "vapour",
         "pump-1", "pump-2", "pump-3", "pump-4", "pump-5",
         "ground", "weekend", "not"]


def words():
    f = ROOT / "copy/flood_explainer.md"
    got = {}
    if f.exists():
        sec = None
        for line in f.read_text().splitlines():
            if line.startswith("## "):
                sec = line[3:].strip()
                got[sec] = []
            elif sec:
                got[sec].append(line)
    out = {}
    for s in SLOTS:
        text = " ".join(" ".join(got.get(s, [])).split())
        out[s] = text or "[WORDS: %s]" % s
    return out


def prose(t):
    if t.startswith("[WORDS"):
        return '<span class="ph">%s</span>' % h(t)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h(t))


def data():
    a = json.loads((ASSETS / "flat.json").read_text())
    ing = json.loads(subprocess.run(
        ["git", "show", "origin/main:floods/data/europe_ingredients_2026-10.json"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)
    a["wm"] = next(v for k, v in ing["sst_sept"].items() if k.startswith("Western Mediterranean"))
    p = json.loads((ASSETS / "pump.json").read_text())
    b = json.loads(subprocess.run(
        ["git", "show", "origin/main:floods/data/explainer_2026-10.json"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)["bathtub"]
    return a, p, b


def strip(series, unit, header, noun, dp=1):
    chart = {"label": header, "series": [{"x": int(y), "y": v} for y, v in sorted(series.items())],
             "current_x": 2026, "unit": unit, "decimals": dp, "header": header.upper(),
             "noun": noun, "noun_plural": noun + "s", "current_kicker": "2026",
             "diverging": False, "annotations": []}
    return _record_strip(chart, "var(--flood)")


def ground_table(g):
    rows = sorted(g["areas"].items(), key=lambda kv: kv[1]["wettest_rank"][0])
    out = []
    for name, a in rows:
        pct = a["pct_vs_normal"]
        r, n = a["wettest_rank"]
        out.append('<tr><th scope="row">%s</th><td class="num">%+.0f%%</td>'
                   '<td class="num">%s</td><td><span class="bar" style="--w:%.0f%%;--c:%s"></span></td></tr>'
                   % (h(name), pct, "%d of %d" % (r, n),
                      min(100, abs(pct)), "var(--flood)" if pct > 0 else "var(--ink-faint)"))
    return ('<table class="gt"><caption>%s</caption><thead><tr><th></th>'
            '<th class="num">vs normal</th><th class="num">wettest rank</th><th></th></tr></thead>'
            '<tbody>%s</tbody></table>' % (h(g["what"]), "".join(out)))


# THE CLOCK FOLLOWS THE WORDS. Each pump caption names a date, and the 3D
# scene's clock is pinned to it: while caption k is centred, the scene shows
# PUMP_AT[k]. Run evenly with scroll instead, a caption saying "29
# September" sat over a scene showing the 28th. check_pump_dates() refuses
# a publish whose captions no longer start with these dates.
PUMP_AT = [("2026-09-27T12:00Z", "27 September"), ("2026-09-29T12:00Z", "29 September"),
           ("2026-09-30T12:00Z", "30 September"), ("2026-10-01T12:00Z", "1 October"),
           ("2026-10-03T12:00Z", "3 October")]


def check_pump_dates(w):
    bad = [(i, d) for i, (_, d) in enumerate(PUMP_AT, 1)
           if not w["pump-%d" % i].startswith(d)]
    return ["pump-%d does not start with %r" % (i, d) for i, d in bad]


MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
       "Nov", "Dec"]


def aemet_layer(X, Y, box):
    """AEMET's own warnings, drawn as AEMET issued them, never re-scored.

    Read from origin (FLO's fetch; a scheduled refresh commits at 06:30).
    Only warnings not yet expired at build time are drawn, one shape per
    warned area however many warnings it carries, coloured by AEMET's own
    level. Returns (svg, stamp sentence, n areas).
    """
    from datetime import datetime, timezone
    raw = json.loads(subprocess.run(
        ["git", "show", "origin/main:floods/data/aemet_warnings_latest.json"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)
    now = datetime.now(timezone.utc)
    lo0, lo1, la0, la1 = box
    rank = {"amarillo": 1, "naranja": 2, "rojo": 3}
    areas = {}
    for wn in raw["warnings"]:
        # FLO's flag (6c4653b5): only warnings inside the second storm's
        # window. Without it, Thursday's inland warnings (Burgos, Soria)
        # read as this weekend's risk.
        if not wn.get("in_dana2_window"):
            continue
        if datetime.fromisoformat(wn["expires"]) < now:
            continue
        for poly in wn["polygons_lonlat"]:
            if not any(lo0 <= x <= lo1 and la0 <= y <= la1 for x, y in poly):
                continue
            a = areas.setdefault(wn["area"], {"level": wn["level"], "polys": {}, "lines": set()})
            if rank.get(wn["level"], 0) > rank.get(a["level"], 0):
                a["level"] = wn["level"]
            # ONE SHAPE PER ZONE. Each warning for a zone carries the zone's
            # polygon, so a zone with four warnings arrived four times, and
            # four semi-transparent yellows stacked read as orange (CPO,
            # 16 Oct). AEMET's level is the one thing drawn exactly as issued.
            a["polys"][tuple(map(tuple, poly))] = poly
            a["lines"].add("%s, %s to %s" % (wn["threshold"].split(";", 1)[-1].replace(";", " "),
                                             wn["onset"][5:16].replace("T", " "),
                                             wn["expires"][5:16].replace("T", " ")))
    out = []
    for name, a in sorted(areas.items()):
        for poly in a["polys"].values():
            out.append('<polygon points="%s" class="w8-aemet w8-%s"><title>%s: %s</title></polygon>'
                       % (" ".join("%.1f,%.1f" % (X(x), Y(y)) for x, y in poly), a["level"],
                          h(name), h("; ".join(sorted(a["lines"])))))
    sent = max(wn["sent"] for wn in raw["warnings"])[:16].replace("T", " ")
    # FLO's dana2_window is a note to us ("warnings overlapping Sat 17 Oct
    # 00:00 to Wed 21 Oct 00:00 Madrid time..."), not reader text.
    win_txt = " for 17 to 20 October"
    stamp = ("AEMET's rain and thunderstorm warnings%s: %d zones drawn, at the level AEMET set. "
             "Issued up to %s UTC. Source: AEMET OpenData (Meteoalerta)."
             % (win_txt, len(areas), sent))
    return "".join(out), stamp, len(areas)


def weekend_map(ground, aemet=True):
    """Scene 8: where the ingredients overlap. Each layer names its source.

    Past floods are numbered markers with MONTH AND YEAR ONLY, and the map
    prints no death toll at all. That one rule covers all three of
    aftereffects' cautions (Valencia 2024's toll moved between vintages,
    Sant Llorenc's day is unsettled, Malaga November 2024 has no verified
    death and must never read as zero). The label points place markers;
    they are not flood extents, and the key says so.

    AEMET's warning areas are added when their Friday update is out; until
    then the slot says so rather than drawing nothing.
    """
    fl = json.loads((ROOT / "research/data/spain_med_floods_map.json").read_text())
    ev = sorted(fl["events"], key=lambda e: e["start"])
    lo0, lo1, la0, la1 = -5.6, 4.6, 35.9, 42.9
    py = 74.0
    import math
    px = py * math.cos(math.radians((la0 + la1) / 2))
    W, H = (lo1 - lo0) * px, (la1 - la0) * py
    X = lambda lo: (lo - lo0) * px
    Y = lambda la: (la1 - la) * py
    coast = json.loads((ROOT / "design/data/europe_coast.json").read_text())["rings"]
    land = []
    for r in coast:
        if len(r) < 3:
            continue
        if max(x for x, _ in r) < lo0 or min(x for x, _ in r) > lo1 or \
           max(y for _, y in r) < la0 or min(y for _, y in r) > la1:
            continue
        land.append('<polygon points="%s" class="w8-land"/>'
                    % " ".join("%.1f,%.1f" % (X(x), Y(y)) for x, y in r))
    boxes = []
    for name, a in ground["areas"].items():
        s_, n_, w_, e_ = a["box_s_n_w_e"]
        pct = a["pct_vs_normal"]
        op = max(0.0, min(1.0, pct / 60.0))
        # Drier than normal is an empty dashed box, never a pale fill under
        # a key that says "wetter" (Ibiza, -12%).
        boxes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" class="%s" '
                     'style="fill-opacity:%.2f"><title>%s: topsoil %+.0f%% vs normal, %s wettest of %d</title></rect>'
                     % (X(w_), Y(n_), X(e_) - X(w_), Y(s_) - Y(n_),
                        "w8-wet" if pct > 0 else "w8-dry", 0.12 + 0.6 * op if pct > 0 else 0,
                        h(name), pct, _nth(a["wettest_rank"][0]), a["wettest_rank"][1]))
    groups = {}
    for i, e in enumerate(ev, 1):
        lp = e["label_point"]
        groups.setdefault((lp["lat"], lp["lon"]), []).append(i)
    dots = []
    for (la, lo), ids in groups.items():
        x, y = X(lo), Y(la)
        dots.append('<circle cx="%.1f" cy="%.1f" r="4" class="w8-dot"/>'
                    '<text x="%.1f" y="%.1f" class="w8-n">%s</text>'
                    % (x, y, x + 6, y - 5, ",".join(map(str, ids))))
    items = "".join('<li><b>%d</b> %s %s &middot; %s</li>'
                    % (i, MON[int(e["start"][5:7]) - 1], e["start"][:4], h(e["name"]))
                    for i, e in enumerate(ev, 1))
    aem_svg, aemet_txt, _ = aemet_layer(X, Y, (lo0, lo1, la0, la1)) if aemet else ("", "", 0)
    return f"""<figure class="w8">
<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" role="img" aria-label="Map of Spain's Mediterranean coast and the Balearics: where topsoil is wetter than normal after the first storm, and where damaging floods have struck since 1982.">
<rect width="{W:.0f}" height="{H:.0f}" class="w8-sea"/>
<defs><clipPath id="w8-landclip">{"".join(land).replace(' class="w8-land"', '')}</clipPath></defs>
{"".join(land)}
{aem_svg}
<g clip-path="url(#w8-landclip)">{"".join(boxes)}</g>
{"".join(dots)}
</svg>
<div class="w8-key">
  <p><span class="sw wet"></span> Topsoil wetter than normal after the first storm, darker is wetter, by analysis area, land only. ERA5, top 7 cm, 8 to 10 October, against 1991 to 2020.</p>
  <p><span class="sw dry"></span> Drier than normal (Ibiza).</p>
  <p><span class="sw dot"></span> Damaging floods since 1982, numbered by date. Markers place each event at a named town; they are not flood extents. HANZE v2.1 to 2020 (Paprotny et al. 2024, CC BY 4.0); 2024 from named news sources. A selection, not a ranking.</p>
  <p><span class="sw aem"></span> {h(aemet_txt)}</p>
  <ol class="w8-list">{items}</ol>
</div>
</figure>"""


def _nth(n):
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def _v(name):
    """Content hash for a scene script's URL, so a changed module is never
    served from a cache that still holds the old one (the CDN keeps pages
    for ten minutes and browsers cache modules hard)."""
    import hashlib
    return hashlib.sha256((ROOT / "design/explainer" / name).read_bytes()).hexdigest()[:10]


def page(w, preview):
    flat, pump, bath = data()
    imports = VENDOR
    ev, vp, wm = flat["evap"], flat["vapour"], flat["wm"]
    bath_steps = "".join('<div class="step"><p>%s</p></div>' % prose(w["bath-%d" % i]) for i in range(1, 5))
    pump_steps = "".join('<div class="step" data-at="%s"><p>%s</p></div>'
                         % (at, prose(w["pump-%d" % i])) for i, (at, _) in enumerate(PUMP_AT, 1))
    ev_series = {y: v for y, v in ev["by_year"].items()}
    title = w["headline"] if not w["headline"].startswith("[WORDS") else "How a flood is made"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_meta(title=f"{title} | {SITE_NAME}", description=re.sub(r"[*]", "", w["standfirst"]), path=PATH)}
<script type="importmap">{json.dumps({"imports": imports})}</script>
<style>
{T.font_faces_css("../../fonts/")}
:root {{
{T.css_variables()}
--cold: {T.COLD};
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
{T.css_variables(dark=True)}
}} }}
:root[data-theme="dark"] {{
{T.css_variables(dark=True)}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: var(--serif);
  font-size: 18px; line-height: 1.6; }}
{SITE_MASTHEAD_CSS}
.col {{ max-width: 680px; margin: 0 auto; padding: 0 24px; }}
.wide {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}
.kick {{ font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-faint); margin: 0 0 10px; }}
header.top {{ padding: 9vh 0 4vh; }}
h1 {{ font-weight: 500; font-size: clamp(34px, 5vw, 52px); line-height: 1.06; letter-spacing: -.015em;
  margin: 0 0 18px; text-wrap: balance; }}
.stand {{ font-size: 20px; color: var(--ink-soft); }}
h2 {{ font-weight: 500; font-size: 28px; line-height: 1.15; margin: 0 0 14px; }}
section.flat {{ padding: 12vh 0 6vh; }}
.ph {{ background: #fff3c4; color: #5a4a00; font-family: var(--mono); font-size: 13px; padding: 2px 6px; }}
figure {{ margin: 26px 0 0; }}
figure img {{ display: block; width: 100%; height: auto; }}
figcaption, .src {{ font-family: var(--mono); font-size: 10.5px; letter-spacing: .06em; color: var(--ink-faint);
  margin-top: 8px; line-height: 1.5; }}
.key {{ display: flex; align-items: center; gap: 10px; font-family: var(--mono); font-size: 10.5px;
  letter-spacing: .1em; color: var(--ink-soft); text-transform: uppercase; margin-top: 10px; flex-wrap: wrap; }}
.key .rampbar {{ width: 160px; height: 9px; background: linear-gradient(90deg, {", ".join(T.ANOMALY)}); }}
.pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 26px 0 6px; }}
.pair div {{ border-top: 3px solid var(--ink); padding-top: 12px; }}
.pair b {{ display: block; font-family: var(--mono); font-weight: 500; font-size: clamp(32px, 5vw, 46px);
  letter-spacing: -.02em; line-height: 1; }}
.pair .y26 b {{ color: var(--flood); }}
.pair span {{ font-family: var(--mono); font-size: 11px; letter-spacing: .1em; color: var(--ink-faint);
  text-transform: uppercase; }}
.rs {{ display:block; width:100%; height:auto; margin-top: 18px; }}
.rs-cur {{ font-family: var(--mono); font-size:23px; font-weight:500; fill:var(--ink); }}
.rs-kick {{ font-family: var(--mono); font-size:9.5px; letter-spacing:1.9px; fill:var(--ink-soft); }}
.rs-lab {{ font-family: var(--mono); font-size:10.5px; letter-spacing:.6px; fill:var(--ink-soft); }}
.rs-said {{ font-family: var(--serif); font-size:17px; fill:var(--ink); }}
.rs-key {{ font-family: var(--mono); font-size:10px; letter-spacing:1.6px; fill:var(--ink-soft); }}
.gt {{ width: 100%; border-collapse: collapse; font-size: 15px; margin-top: 22px; }}
.gt caption {{ text-align: left; font-family: var(--mono); font-size: 10.5px; letter-spacing: .06em;
  color: var(--ink-faint); padding-bottom: 8px; }}
.gt th, .gt td {{ padding: 7px 10px 7px 0; border-top: 1px solid var(--rule); text-align: left; font-weight: 400; }}
.gt thead th {{ font-family: var(--mono); font-size: 10px; letter-spacing: .1em; color: var(--ink-faint);
  text-transform: uppercase; border-top: 0; }}
.gt .num {{ font-family: var(--mono); text-align: right; white-space: nowrap; }}
.gt .bar {{ display: block; height: 8px; width: var(--w); background: var(--c); min-width: 2px; }}
.gt td:last-child {{ width: 32%; }}
figure img {{ max-height: 82vh; width: auto; max-width: 100%; margin: 0 auto; }}
{FIG_CSS}
.seawrap {{ max-width: 1100px; margin: 22px auto 0; padding: 0 24px; }}
.seawrap canvas {{ display: block; width: 100%; height: clamp(300px, 42vw, 460px); border-radius: 3px; }}
.ground3 {{ position: relative; height: min(78vh, 720px); max-width: 1200px; margin: 18px auto 0; }}
.ground3 canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.g3-lab {{ position: absolute; top: 4%; margin: 0; font-family: var(--mono); font-size: 11px;
  letter-spacing: .14em; text-transform: uppercase; color: var(--ink-soft); }}
.g3-lab span {{ display: block; font-family: var(--serif); font-size: 17px; letter-spacing: 0;
  text-transform: none; color: var(--ink); margin-top: 3px; }}
.g3-dry {{ left: 12%; }} .g3-wet {{ left: 56%; }}
.g3-foot {{ position: absolute; left: 24px; right: 24px; bottom: 2%; display: flex; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin: 0; font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ink-faint); }}
.w8 svg {{ display: block; width: 100%; height: auto; border: 1px solid var(--rule); }}
.w8-sea {{ fill: var(--paper); }}
.w8-land {{ fill: var(--land); stroke: var(--ink-faint); stroke-width: .6; }}
.w8-wet {{ fill: var(--flood); stroke: var(--flood); stroke-width: .8; }}
.w8-aemet {{ stroke-width: .6; fill-opacity: .55; }}
.w8-amarillo {{ fill: #F2C94C; stroke: #B8901A; }}
.w8-naranja {{ fill: #E8893A; stroke: #A85A16; }}
.w8-rojo {{ fill: #C8322B; stroke: #7E1A15; }}
.w8-key .sw.aem {{ background: #F2C94C; opacity: .8; }}
.w8-dry {{ fill: var(--paper); fill-opacity: .85 !important; stroke: var(--ink-faint); stroke-width: .8; stroke-dasharray: 3 2; }}
.w8-dot {{ fill: var(--ink); stroke: var(--paper); stroke-width: 1.5; }}
.w8-n {{ font-family: var(--mono); font-size: 11px; font-weight: 500; fill: var(--ink);
  paint-order: stroke; stroke: var(--paper); stroke-width: 3px; }}
.w8-key {{ font-size: 14px; color: var(--ink-soft); margin-top: 12px; }}
.w8-key p {{ margin: 0 0 8px; }}
.w8-key .sw {{ display: inline-block; width: 14px; height: 10px; vertical-align: middle; margin-right: 6px; }}
.w8-key .sw.wet {{ background: var(--flood); opacity: .55; }}
.w8-key .sw.dry {{ border: 1px dashed var(--ink-faint); background: var(--paper); }}
.w8-key .sw.dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--ink); }}
.w8-pend {{ font-family: var(--mono); font-size: 11px; color: var(--ink-faint); }}
.w8-list {{ columns: 2; column-gap: 28px; padding-left: 0; list-style: none; font-size: 13.5px; margin: 10px 0 0; }}
.w8-list li {{ break-inside: avoid; margin-bottom: 4px; }}
.w8-list b {{ font-family: var(--mono); font-weight: 500; margin-right: 4px; }}
@media (max-width: 600px) {{ .w8-list {{ columns: 1; }} }}

/* the two 3D scenes: a sticky stage, captions scrolling past it */
.scrolly {{ position: relative; }}
#bath {{ height: 420vh; }}
#pump {{ height: 640vh; }}
.stage {{ position: sticky; top: 0; height: 100vh; overflow: hidden; }}
.stage canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.steps {{ position: absolute; top: 0; left: 0; right: 0; pointer-events: none; }}
.step {{ height: 105vh; display: flex; align-items: center; }}
#pump .step {{ height: 110vh; }}
#pump .step p, #bath .step p {{ margin-top: 22vh; }}
.when, .legend, .foot3 {{ z-index: 2; }}
.step p {{ max-width: 340px; margin: 0 0 0 6vw; background: color-mix(in srgb, var(--paper) 90%, transparent);
  padding: 14px 18px; border-left: 3px solid var(--ink); font-size: 18px; }}
.hud {{ position: absolute; left: 6vw; top: 10vh; pointer-events: none; z-index: 2; }}
.hud .num {{ font-family: var(--mono); font-weight: 500; font-size: clamp(44px, 8vw, 84px); letter-spacing: -.03em;
  font-variant-numeric: tabular-nums; line-height: 1; }}
.hud .unit {{ font-family: var(--mono); font-size: 12px; letter-spacing: .16em; color: var(--ink-faint);
  margin-top: 10px; text-transform: uppercase; }}
.tag3 {{ position: absolute; top: 18px; right: 18px; font-family: var(--mono); font-size: 10px;
  letter-spacing: .14em; color: var(--ink-faint); text-transform: uppercase; }}
.when {{ position: absolute; left: 6vw; top: 8vh; font-family: var(--mono); }}
.when b {{ display: block; font-weight: 500; font-size: clamp(26px, 4vw, 40px); letter-spacing: -.02em; }}
.when span {{ font-size: 11px; letter-spacing: .14em; color: var(--ink-faint); text-transform: uppercase; }}
.legend {{ position: absolute; right: 4vw; top: 8vh; font-family: var(--mono); font-size: 10px;
  letter-spacing: .12em; color: var(--ink-soft); text-transform: uppercase; display: grid; gap: 9px; justify-items: end; }}
.legend i {{ display: inline-block; vertical-align: middle; margin-left: 8px; }}
.legend .ramp {{ width: 90px; height: 8px; background: linear-gradient(90deg, {", ".join(T.ANOMALY[4:])}); }}
.legend .coldsw {{ width: 22px; height: 10px; background: var(--cold); opacity: .75; }}
.legend .windsw {{ width: 22px; height: 0; border-top: 1.5px solid var(--ink); }}
.lab {{ position: absolute; font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em;
  text-transform: uppercase; white-space: nowrap; pointer-events: none; transform: translate(-50%, -140%); }}
.lab.cold {{ color: var(--cold); font-weight: 500; }}
.lab.wind {{ font-weight: 500; font-size: 12px; background: var(--paper); padding: 3px 6px; }}
.foot3 {{ position: absolute; left: 6vw; bottom: 3vh; font-family: var(--mono); font-size: 10px;
  letter-spacing: .12em; color: var(--ink-faint); text-transform: uppercase; }}
@media (max-width: 899px) {{
  .hud {{ left: 0; right: 0; top: 6vh; text-align: center; }}
  .step {{ align-items: flex-end; padding-bottom: 8vh; }}
  .step p {{ margin: 0 16px; max-width: none; }}
  .legend {{ top: auto; bottom: 14vh; right: 16px; }}
  .when {{ left: 16px; top: 5vh; }} .foot3 {{ left: 16px; }}
  .pair {{ gap: 14px; }}
}}
</style>
</head>
<body>
{site_masthead("../../", active="flood")}
<main>
<header class="top col">
  <p class="kick">Floods &middot; explainer &middot; 16 October 2026</p>
  <h1>{prose(w["headline"])}</h1>
  <p class="stand">{prose(w["standfirst"])}</p>
</header>

<section class="scrolly" id="bath" data-mm="{bath["mm"]}">
  <div class="stage">
    <canvas id="bath-gl"></canvas>
    <div class="tag3">Drawn to scale &middot; 1 m cube</div>
    <div class="hud"><div class="num" id="bath-num">{bath["mm"]:.1f} mm</div>
      <div class="unit" id="bath-unit">{bath["mm"]:.0f} litres on one square metre</div></div>
  </div>
  <div class="steps">{bath_steps}</div>
</section>

<section class="flat">
  <div class="col"><p class="kick">The heat</p><p>{prose(w["heat"])}</p></div>
  <div class="wide"><figure>
    <img src="assets/{flat["heat"]["img"]}" alt="Map of Europe, September 2026 temperature against 1991 to 2020: much warmer than normal over France, Iberia, the western and central Mediterranean and North Africa." width="{flat["heat"]["size"][0]}" height="{flat["heat"]["size"][1]}">
    <div class="key"><span>Colder</span><span class="rampbar"></span><span>Warmer</span><span>&middot; scale &plusmn;{flat["heat"]["full_c"]:g} &deg;C, saturates beyond</span></div>
    <figcaption>{h(flat["heat"]["what"])}.</figcaption>
  </figure></div>
</section>

<section class="flat">
  <div class="col"><p class="kick">It starts from the sea</p><p>{prose(w["sea"])}</p>
  </div>
  <div class="seawrap" id="sea" data-t-normal="{wm["c"] - wm["anom"]:.1f}" data-t2026="{wm["c"]:.1f}"
       data-e-normal="{ev["normal"]:.2f}" data-e2026="{ev["y2026"]:.2f}" data-e-pct="{ev["pct"]:+.0f}">
    <canvas id="sea-cv" aria-label="Two sea surfaces side by side. A normal September at {wm["c"] - wm["anom"]:.1f} degrees, and September 2026 at {wm["c"]:.1f} degrees, with water vapour rising from both at the measured evaporation rate."></canvas>
  </div>
  <div class="col">
    <p class="src">Temperatures measured: western Mediterranean (Alboran, Balearic, Gulf of Lion), September mean, ERA5; 2026 is the warmest September in a record going back to {wm["since"]} ({wm["rank"][0]} of {wm["rank"][1]}). The motion is illustrative: the warmer sea is drawn more agitated, not to a measured rate.</p>
  </div>
</section>

<section class="flat">
  <div class="col"><p class="kick">Warm air holds more water</p><p>{prose(w["vapour"])}</p>
    <div id="vap-strip" class="hero-strip">{strip(vp["by_year_pct"], "%", "Water vapour in the air, every September since 1940, % vs 1991-2020", "September")}</div>
    <p class="src">Global total column water vapour, area-weighted, ERA5. {h(vp["physics"][0].upper() + vp["physics"][1:])}.</p>
  </div>
</section>

<section class="scrolly" id="pump">
  <div class="stage">
    <canvas id="pump-gl"></canvas>
    <div class="when"><b id="pump-when">27 Sep, 00:00 UTC</b><span>ERA5 &middot; 2026 preliminary</span></div>
    <div class="legend">
      <div>Sea, September vs normal <i class="ramp"></i></div>
      <div>Cold air, 5 km up <i class="coldsw"></i></div>
      <div id="pump-lgwind" style="opacity:0">Wind, 1.5 km up <i class="windsw"></i></div>
    </div>
    <div class="lab" id="pump-lbcn">Barcelona</div>
    <div class="lab cold" id="pump-lbcold"></div>
    <div class="lab wind" id="pump-lbwind" style="opacity:0"></div>
    <div class="foot3">Heights exaggerated &middot; every layer is a measured field</div>
  </div>
  <div class="steps">{pump_steps}</div>
</section>

<section class="flat">
  <div class="col"><p class="kick">The ground can't drink that fast</p><p>{prose(w["ground"])}</p>
  </div>
  <div class="ground3" id="ground">
    <canvas id="ground-gl"></canvas>
    <p class="g3-lab g3-dry">Dry ground<span>soaks the rain in</span></p>
    <p class="g3-lab g3-wet">Already wet<span>fills, and the rest runs off</span></p>
    <p class="g3-foot"><span id="ground-clock">Hour 0 of 24</span><span>Same rain on both &middot; illustrative &middot; not to scale</span></p>
  </div>
  <div class="col">
    {ground_table(flat["ground"])}
  </div>
</section>

<section class="flat">
  <div class="col"><p class="kick">This weekend</p><p>{prose(w["weekend"])}</p>
    {weekend_map(flat["ground"])}
    <p class="src">Not a forecast of ours, and no combined score: each layer is shown as its source published it.</p>
  </div>
</section>

<section class="flat">
  <div class="col"><p class="kick">What this is not</p><p>{prose(w["not"])}</p>
    <p class="src">Data: ERA5 (Copernicus Climate Change Service), 2026 preliminary; AEMET (Barcelona Fabra, station 0200E). Compiled by the floods desk.</p>
  </div>
</section>
</main>
<script src="{MOTION}"></script>
<script>
// THE VAPOUR STRIP BUILDS ITSELF, one September at a time, 1940 first, so
// the climb is something the reader watches happen rather than a shape
// they take in at a glance. The rule for 2026 arrives last. Reduced motion
// and no JavaScript get the finished strip, which is what the markup holds.
(function () {{
  // CSS transitions, not Motion: Motion's animate did not commit opacity on
  // SVG circles (measured 15 Oct), and a strip left invisible is worse than
  // one that does not animate.
  var el = document.getElementById("vap-strip");
  if (!el || !("IntersectionObserver" in window) ||
      matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var dots = el.querySelectorAll("circle"), late = el.querySelectorAll("line, rect, text");
  dots.forEach(function (d, i) {{ d.style.opacity = 0;
    d.style.transition = "opacity .35s ease " + (i * 0.035) + "s"; }});
  late.forEach(function (d) {{ d.style.opacity = 0;
    d.style.transition = "opacity .6s ease " + (dots.length * 0.035 + 0.2) + "s"; }});
  var io = new IntersectionObserver(function (es) {{
    if (!es[0].isIntersecting) return;
    dots.forEach(function (d) {{ d.style.opacity = 1; }});
    late.forEach(function (d) {{ d.style.opacity = 1; }});
    io.disconnect();
  }}, {{ threshold: 0.6 }});
  io.observe(el);
}})();
</script>
<script type="module" src="scene_bathtub.js?v={_v("scene_bathtub.js")}"></script>
<script type="module" src="scene_pump.js?v={_v("scene_pump.js")}"></script>
<script type="module" src="scene_ground.js?v={_v("scene_ground.js")}"></script>
<script type="module" src="scene_sea.js?v={_v("scene_sea.js")}"></script>
{ANALYTICS_SNIPPET}
</body>
</html>
"""


def main():
    preview = "--preview" in sys.argv
    w = words()
    holes = [k for k, v in w.items() if v.startswith("[WORDS")]
    drift = [] if holes else check_pump_dates(w)
    if drift:
        print("WARNING: captions and scene clock disagree:\n  " + "\n  ".join(drift))
        if not preview:
            raise SystemExit("REFUSING TO PUBLISH: update PUMP_AT to match the captions.")
    if holes and not preview:
        raise SystemExit("REFUSING TO PUBLISH: %d prose slots still empty: %s"
                         % (len(holes), ", ".join(holes)))
    out = PREVIEW if preview else ROOT / "docs" / SLUG
    (out / "assets").mkdir(parents=True, exist_ok=True)
    html = page(w, preview)
    (out / "index.html").write_text(html)
    for js in (ROOT / "design/explainer").glob("scene_*.js"):
        shutil.copy(js, out / js.name)
    for f in ASSETS.iterdir():
        shutil.copy(f, out / "assets" / f.name)
    if preview:
        shutil.copytree(ROOT / "docs/vendor", out.parent.parent / "vendor", dirs_exist_ok=True)
    print("wrote", out, "| empty prose slots:", len(holes))


if __name__ == "__main__":
    main()
