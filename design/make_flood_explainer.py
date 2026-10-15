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
         "pump-1", "pump-2", "pump-3", "pump-4", "pump-5", "pump-wk-1", "pump-wk-2",
         "ground", "weekend"]
# "not" (what this is not) was cut by Kristjan on 16 October: "this is
# pointless". The editor's copy file may still carry the section; unused.


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


# The forecast act (ECMWF, FLO 3903bf41): same rule, its own captions.
PUMP_WK_AT = [("2026-10-18T12:00Z", "18 October"), ("2026-10-19T12:00Z", "19 October")]


def check_pump_dates(w):
    bad = [("pump-%d" % i, d) for i, (_, d) in enumerate(PUMP_AT, 1)
           if not w["pump-%d" % i].startswith(d)]
    bad += [("pump-wk-%d" % i, d) for i, (_, d) in enumerate(PUMP_WK_AT, 1)
            if not w["pump-wk-%d" % i].startswith(("[WORDS", d))]
    return ["%s does not start with %r" % (k, d) for k, d in bad]


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
    stamp = ("AEMET's rain and thunderstorm warnings%s, drawn at the level AEMET set. "
             "Issued up to %s UTC. Source: AEMET OpenData (Meteoalerta)."
             % (win_txt, sent))
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
    # SHADED BY RANK, not percent (VD): the percent says how much, the rank
    # says how unusual for the date, which is the claim. Top third of the
    # record is filled, darker the higher it ranks; anything mid-record
    # (Malaga 15th, Ibiza 16th of 36) is drawn plain, as within range.
    for name, a in ground["areas"].items():
        s_, n_, w_, e_ = a["box_s_n_w_e"]
        pct, (r, n) = a["pct_vs_normal"], a["wettest_rank"]
        top = r <= n / 3
        op = 0.85 - 0.6 * (r - 1) / (n / 3 - 1) if top else 0
        boxes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" class="%s" '
                     'style="fill-opacity:%.2f"><title>%s: topsoil %+.0f%% vs normal, %s wettest of %d</title></rect>'
                     % (X(w_), Y(n_), X(e_) - X(w_), Y(s_) - Y(n_), "w8-wet" if top else "w8-mid",
                        max(op, 0.2) if top else 0, h(name), pct, _nth(r), n))
    # Past floods by YEAR on the map itself (no numbered list): points within
    # about 30 km share one label, so Valencia 2000 and Paiporta 2024 read
    # as one place hit twice rather than two labels on top of each other.
    groups = []
    for e in ev:
        lp = e["label_point"]
        g = next((g for g in groups
                  if math.hypot(g["lat"] - lp["lat"], (g["lon"] - lp["lon"]) * 0.78) < 0.3), None)
        if g is None:
            g = {"lat": lp["lat"], "lon": lp["lon"], "ev": []}
            groups.append(g)
        g["ev"].append(e)
    dots = []
    for k, g in enumerate(groups):
        x, y = X(g["lon"]), Y(g["lat"])
        years = " \u00b7 ".join(sorted({e["start"][:4] for e in g["ev"]}))
        tip = "; ".join("%s %s, %s" % (MON[int(e["start"][5:7]) - 1], e["start"][:4], e["name"]) for e in g["ev"])
        left = g["lon"] < -0.3          # inland of the coast: label to the left
        dots.append('<g class="w8-pt" style="--k:%d"><title>%s</title>'
                    '<circle cx="%.1f" cy="%.1f" r="5" class="w8-dot"/>'
                    '<text x="%.1f" y="%.1f" class="w8-n" text-anchor="%s">%s</text></g>'
                    % (k, h(tip), x, y, x + (-9 if left else 9), y + 4, "end" if left else "start", years))
    aem_svg, aemet_txt, n_zones = aemet_layer(X, Y, (lo0, lo1, la0, la1)) if aemet else ("", "", 0)
    svg = f"""<svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Map of Spain's Mediterranean coast and the Balearics: damaging floods since 1982, topsoil wetter than normal after the first storm, and AEMET's warnings for 17 to 20 October.">
<rect width="{W:.0f}" height="{H:.0f}" class="w8-sea"/>
<defs><clipPath id="w8-landclip">{"".join(land).replace(' class="w8-land"', '')}</clipPath></defs>
{"".join(land)}
<g class="L L-aemet">{aem_svg}</g>
<g class="L L-wet" clip-path="url(#w8-landclip)">{"".join(boxes)}</g>
{places(X, Y)}
<g class="L L-floods">{"".join(dots)}</g>
</svg>"""
    layers = [
        ("Floods since 1982", "Damaging floods on this coast, by year. A selection, not a ranking; markers place each at a named town, not its extent. HANZE v2.1 to 2020 (Paprotny et al. 2024); 2024 from named news sources."),
        ("Wet ground, now", "Topsoil after the first storm, filled where it is among the wettest third of 36 years for the date, darker the higher it ranks; outlined areas are within the usual range. ERA5, top 7 cm, 8 to 10 October."),
        ("AEMET's warnings", aemet_txt),
    ]
    steps = "".join('<div class="step"><p class="wk-cap"><b>%s</b>%s</p></div>' % (h(t), h(d)) for t, d in layers)
    return f"""<section class="scrolly" id="wk">
  <div class="stage wk-stage"><div class="wk-where">{locator((lo0, lo1, la0, la1))}</div><div class="wk-map">{svg}</div></div>
  <div class="steps">{steps}</div>
</section>"""


# THE STRUCTURE IS THE ARGUMENT, so it is set big (Kristjan, 16 Oct: "bring
# out the key words"). One word per chapter, numbered, the old phrase kept
# as a subtitle. Structural labels, design's; the prose stays the editor's.
# Subtitles are QUESTIONS (VD's proposal, Kristjan's yes): each chapter
# word names a part, the question says what that part answers.
CHAPTERS = {"bath": ("01", "Rain", "How much is 159 millimetres?"),
            "heat": ("02", "Heat", "How hot did the summer get?"),
            "sea": ("03", "Sea", "Where did the water come from?"),
            "air": ("04", "Air", "How much water can air hold?"),
            "pump": ("05", "Pump", "What lifted it and set it off?"),
            "ground": ("06", "Ground", "Why didn't the ground take it?"),
            "weekend": ("07", "Weekend", "What does this weekend look like?")}


def places(X, Y):
    """Where this is, said on the map itself (Kristjan: make it clear it
    is Spain). Country and sea in large spaced type, four cities small.
    Drawn beneath the data layers so no label hides a marker."""
    big = [("SPAIN", -3.4, 39.6, "w8-country"), ("MEDITERRANEAN SEA", 1.7, 37.9, "w8-sea-l"),
           ("BALEARIC ISLANDS", 2.9, 40.25, "w8-isl"), ("ALGERIA", 2.4, 36.25, "w8-isl")]
    cities = [("Barcelona", 2.17, 41.39), ("Valencia", -0.38, 39.47), ("Alicante", -0.49, 38.35),
              ("Málaga", -4.42, 36.72)]
    out = ['<text x="%.1f" y="%.1f" class="%s" text-anchor="middle">%s</text>' % (X(lo), Y(la), c, h(t))
           for t, lo, la, c in big]
    # City names go on the opposite side to the flood labels, which sit
    # left of points west of 0.3W and right of the rest.
    for name, lo, la in cities:
        right = lo < -0.3
        out.append('<circle cx="%.1f" cy="%.1f" r="2.4" class="w8-city"/>'
                   '<text x="%.1f" y="%.1f" class="w8-city-t" text-anchor="%s">%s</text>'
                   % (X(lo), Y(la), X(lo) + (7 if right else -7), Y(la) + (14 if right else 4),
                      "start" if right else "end", h(name)))
    return '<g class="w8-places">%s</g>' % "".join(out)


# For scale only, as the editor's bath-2 caption says: a full bath holds
# around 150 litres. Illustrative, and labelled so next to the icon.
BATH_L = 150


def tub_svg():
    """A bathtub that fills in step with the counter (Kristjan: it was not
    clear that 159 mm is a bathtub of water). Full at BATH_L litres."""
    return ('<svg class="tub" viewBox="0 0 120 64" aria-hidden="true">'
            '<defs><clipPath id="tub-in"><path d="M12 22 H108 V34 Q108 52 88 52 H32 Q12 52 12 34 Z"/></clipPath></defs>'
            '<rect id="tub-water" x="0" y="20" width="120" height="44" clip-path="url(#tub-in)" class="tub-water"/>'
            '<path d="M6 22 H114 M12 22 V34 Q12 52 32 52 H88 Q108 52 108 34 V22" class="tub-line"/>'
            '<path d="M30 52 L26 60 M90 52 L94 60" class="tub-line"/>'
            '<path d="M100 22 V8 Q100 4 104 4 H110" class="tub-line"/></svg>')


def locator(box=None):
    """A small map of Iberia with Barcelona marked, for the bathtub stage.

    Kristjan, 16 Oct: hard to tell the cube is Barcelona. Coastline from
    the 50m file the heat map uses; no data, just where."""
    import math
    lo0, lo1, la0, la1 = -10.0, 4.5, 35.8, 44.0
    k = 12.0
    kx = k * math.cos(math.radians(40))
    W, H = (lo1 - lo0) * kx, (la1 - la0) * k
    X = lambda lo: (lo - lo0) * kx
    Y = lambda la: (la1 - la) * k
    rings = json.loads((ROOT / "design/data/europe_coast.json").read_text())["rings"]
    polys = []
    for r in rings:
        if len(r) < 3 or max(x for x, _ in r) < lo0 or min(x for x, _ in r) > lo1 \
           or max(y for _, y in r) < la0 or min(y for _, y in r) > la1:
            continue
        polys.append('<polygon points="%s"/>' % " ".join("%.1f,%.1f" % (X(x), Y(y)) for x, y in r))
    bx, by = X(2.17), Y(41.39)
    if box:
        b0, b1, b2, b3 = box
        return ('<svg class="loc" viewBox="0 0 %.0f %.0f" aria-hidden="true"><g class="loc-land">%s</g>'
                '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" class="loc-box"/>'
                '<text x="%.1f" y="%.1f" class="loc-t" text-anchor="middle">SPAIN</text></svg>'
                % (W, H, "".join(polys), X(b0), Y(b3), X(b1) - X(b0), Y(b2) - Y(b3), X(-7.6), Y(41.9)))
    return ('<svg class="loc" viewBox="0 0 %.0f %.0f" aria-hidden="true"><g class="loc-land">%s</g>'
            '<circle cx="%.1f" cy="%.1f" r="4.5" class="loc-dot"/>'
            '<text x="%.1f" y="%.1f" class="loc-t" text-anchor="end">BARCELONA</text></svg>'
            % (W, H, "".join(polys), bx, by, bx - 10, by - 8))


def heat_figure(flat):
    """May to September 2026 as a crossfade, or the September map alone.

    Kristjan, 16 Oct: "make that a moving heat as well, May - Sept". Each
    frame is that month against its own 1991-2020 mean (ERA5 monthly,
    design/fetch_heat_months.py), same box and scale as the September map.
    The markup shows September, so no-JS and reduced motion get the frame
    the copy describes; the loop holds there longest.
    """
    hm = flat.get("heat_months")
    alt = ("Map of Europe, 2026 temperature against 1991 to 2020, %s: much warmer "
           "than normal over France, Iberia, the western and central Mediterranean.")
    if not hm:
        return ('<img src="assets/%s" alt="%s" width="%d" height="%d">'
                % (flat["heat"]["img"], alt % "September", *flat["heat"]["size"]))
    # September's still only: the morph draws every month from the grids,
    # and five eager 300 KB PNGs were most of the page weight (VD).
    f = hm[-1]
    imgs = ('<img src="assets/%s" alt="%s" data-month="%s" class="hm on" width="%d" height="%d">'
            % (f["img"], h(alt % f["month"]), f["month"], f["size"][0], f["size"][1]))
    ticks = "".join('<span%s>%s</span>' % (' class="on"' if i == len(hm) - 1 else "", f["month"][:3])
                    for i, f in enumerate(hm))
    return ('<div class="heatmove" id="heatmove"><div class="hm-stack">%s'
            '<div class="hm-month" id="hm-month">%s 2026</div></div>'
            '<div class="hm-ticks">%s</div></div>' % (imgs, hm[-1]["month"], ticks))


def heat_caption(flat):
    if flat.get("heat_months"):
        return ("Each month of 2026 against the same month in 1991 to 2020: sea surface "
                "temperature over the sea, air temperature at 2 m over land. ERA5 monthly "
                "means, 2026 preliminary.")
    return flat["heat"]["what"] + "."


def cycle_svg():
    """The close: everything is connected (Kristjan, 16 Oct).

    Replaces "Heat + Sea + Air + Pump + Ground = Flood": an equation adds
    things up and, CPO noted, claims a cause and a flood the page never
    measured. A loop says what the page explains. The water's own path:
    sea to air, lifted by the pump, onto the ground, back to the sea by the
    rivers; heat at the centre warming both sea and air. One verb per link,
    textbook relations, nothing about this storm's cause.
    """
    import math
    cx, cy, R = 450, 300, 215
    nodes = {"Sea": 215, "Air": 145, "Pump": 35, "Ground": 325}   # degrees, 0 = right
    pos = {k: (cx + R * math.cos(math.radians(a)), cy - R * math.sin(math.radians(a)))
           for k, a in nodes.items()}
    pos["Heat"] = (cx, cy)
    links = [("Sea", "Air", "feeds", 1), ("Air", "Pump", "lifted", 1), ("Pump", "Ground", "falls on", 1),
             ("Ground", "Sea", "drains back", 1), ("Heat", "Sea", "", 0), ("Heat", "Air", "", 0)]
    # Each word has its own clearance, so a line stops short of it rather
    # than running into the letters ("Ground" is twice as wide as "Air").
    trim = {"Sea": 56, "Air": 50, "Pump": 74, "Ground": 96, "Heat": 70}
    paths, flows, verbs = [], [], []
    for i, (a, b, verb, ring) in enumerate(links):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        ta, tb = trim[a] * (0.75 if ring and abs(dy) > abs(dx) else 1), trim[b] * (0.75 if ring and abs(dy) > abs(dx) else 1)
        x1t, y1t = x1 + dx / L * ta, y1 + dy / L * ta - (6 if ring else 0)
        x2t, y2t = x2 - dx / L * tb, y2 - dy / L * tb - (6 if ring else 0)
        if ring:   # arc along the circle, bulging outward
            mx, my = (x1t + x2t) / 2, (y1t + y2t) / 2
            ox, oy = mx - cx, my - cy
            ol = math.hypot(ox, oy) or 1
            bend = 58
            qx, qy = mx + ox / ol * bend, my + oy / ol * bend
            d = "M%.1f %.1f Q%.1f %.1f %.1f %.1f" % (x1t, y1t, qx, qy, x2t, y2t)
            vx, vy = mx + ox / ol * (bend * 0.5 + 40), my + oy / ol * (bend * 0.5 + 40) + 4
            anchor = "end" if ox < -40 else "start" if ox > 40 else "middle"
        else:
            d = "M%.1f %.1f L%.1f %.1f" % (x1t, y1t, x2t, y2t)
        pid = "cy-p%d" % i
        cls = "cy-ring" if ring else "cy-heat"
        paths.append('<path id="%s" d="%s" class="cy-link %s" style="--i:%d" pathLength="1" marker-end="url(#cy-arr-%s)"/>'
                     % (pid, d, cls, i, "r" if ring else "h"))
        if verb:
            verbs.append('<text x="%.1f" y="%.1f" class="cy-verb" style="--i:%d" text-anchor="%s">%s</text>'
                         % (vx, vy, i, anchor, h(verb)))
        n = 3 if ring else 2
        for k in range(n):
            flows.append('<circle r="%s" class="cy-dot %s"><animateMotion dur="%.1fs" begin="%.2fs" '
                         'repeatCount="indefinite"><mpath href="#%s"/></animateMotion></circle>'
                         % ("4.5" if ring else "3.5", cls, 3.2 if ring else 2.6, k * (3.2 if ring else 2.6) / n, pid))
    verbs.append('<text x="%d" y="%d" class="cy-verb" style="--i:5" text-anchor="middle">warms the sea and the air</text>'
                 % (cx, cy + 48))
    defs = ('<defs>'
            '<marker id="cy-arr-r" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0 0 L10 5 L0 10 z" class="cy-arrow-r"/></marker>'
            '<marker id="cy-arr-h" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M0 0 L10 5 L0 10 z" class="cy-arrow-h"/></marker></defs>')
    words = "".join('<text x="%.1f" y="%.1f" class="cy-w%s" style="--i:%d" text-anchor="middle">%s</text>'
                    % (x, y + 16, " cy-centre" if k == "Heat" else "", i, k)
                    for i, (k, (x, y)) in enumerate(pos.items()))
    return ('<figure class="cycle" id="cycle"><svg viewBox="0 0 900 600" role="img" '
            'aria-label="A loop: the sea feeds the air, the air is lifted by the pump, the rain falls on the ground, '
            'the ground drains back to the sea; heat at the centre warms the sea and the air.">'
            '%s<g class="cy-links">%s</g><g class="cy-flows">%s</g>%s%s</svg></figure>'
            % (defs, "".join(paths), "".join(flows), "".join(verbs), words))


def chapter(key):
    n, word, sub = CHAPTERS[key]
    return ('<div class="chap"><span class="chap-n">%s</span><h2 class="chap-w">%s</h2>'
            '<p class="chap-s">%s</p></div>' % (n, h(word), h(sub)))


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
    pump_steps = "".join('<div class="step" data-at="%s" data-act="obs"><p>%s</p></div>'
                         % (at, prose(w["pump-%d" % i])) for i, (at, _) in enumerate(PUMP_AT, 1))
    wk = pump.get("weekend")
    if wk:
        run = wk["run"][:16].replace("T", " ")
        pump_steps += ('<div class="step wk-intro" data-act="wk"><p class="wk-cut">This weekend'
                       '<span>The same layers, in ECMWF\'s forecast. Run %s UTC. Not a forecast of ours.</span></p></div>'
                       % h(run))
        pump_steps += "".join('<div class="step" data-at="%s" data-act="wk"><p>%s</p></div>'
                              % (at, prose(w["pump-wk-%d" % i])) for i, (at, _) in enumerate(PUMP_WK_AT, 1))
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
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --cold: #7FB4C2; }} }}
:root[data-theme="dark"] {{ --cold: #7FB4C2; }}
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
header.top {{ padding-top: 9vh; padding-bottom: 4vh; }}
h1 {{ font-weight: 500; font-size: clamp(34px, 5vw, 52px); line-height: 1.06; letter-spacing: -.015em;
  margin: 0 0 18px; text-wrap: balance; }}
.stand {{ font-size: 20px; color: var(--ink-soft); }}
h2 {{ font-weight: 500; font-size: 28px; line-height: 1.15; margin: 0 0 14px; }}
section.flat {{ padding: 12vh 0 6vh; }}
.ph {{ background: #fff3c4; color: #5a4a00; font-family: var(--mono); font-size: 13px; padding: 2px 6px; }}
figure {{ margin: 26px 0 0; }}
figure img {{ display: block; width: 100%; height: auto; }}
figcaption, .src {{ font-family: var(--mono); font-size: 10.5px; letter-spacing: .06em; color: var(--ink-soft);
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
  color: var(--ink-soft); padding-bottom: 8px; }}
.gt th, .gt td {{ padding: 7px 10px 7px 0; border-top: 1px solid var(--rule); text-align: left; font-weight: 400; }}
.gt thead th {{ font-family: var(--mono); font-size: 10px; letter-spacing: .1em; color: var(--ink-soft);
  text-transform: uppercase; border-top: 0; }}
.gt .num {{ font-family: var(--mono); text-align: right; white-space: nowrap; }}
.gt .bar {{ display: block; height: 8px; width: var(--w); background: var(--c); min-width: 2px; }}
.gt td:last-child {{ width: 32%; }}
figure img {{ max-height: 82vh; width: auto; max-width: 100%; margin: 0 auto; }}
{FIG_CSS}
.chap {{ margin: 0 0 22px; }}
.heatmove {{ max-width: 760px; margin: 0 auto; }}
.hm-stack {{ position: relative; }}
.hm-stack img {{ display: block; width: 100%; height: auto; max-height: none; }}
.hm-stack img.hm {{ position: absolute; inset: 0; opacity: 0; transition: opacity .9s ease; }}
.hm-stack img.hm.on {{ position: relative; opacity: 1; }}
.hm-stack.anim img.hm {{ opacity: 0; }}
.hm-stack.anim img.hm.fade {{ opacity: 1; }}
.hm-month {{ position: absolute; left: 0; top: 0; font-family: var(--mono); font-weight: 500;
  font-size: clamp(20px, 3.4vw, 32px); letter-spacing: -.01em; color: var(--ink); background: var(--paper);
  padding: 6px 12px 6px 0; }}
.hm-ticks {{ display: flex; gap: 6px; margin-top: 10px; }}
.hm-ticks span {{ flex: 1; font-family: var(--mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ink-faint); padding-top: 9px; background: linear-gradient(var(--ink), var(--ink)) 0 0 / 100% 3px no-repeat,
  linear-gradient(var(--rule), var(--rule)) 0 0 / 100% 3px no-repeat; }}
.hm-stack.morph img.hm {{ display: none; }}
.hm-canvas {{ display: block; width: 100%; }}
.hm-lines {{ position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }}
.hm-ticks span.on {{ color: var(--ink); border-top-color: var(--ink); }}
.eqsec {{ padding: 12vh 0 10vh; }}
.cycle {{ margin: 0 auto; max-width: 960px; }}
.cycle svg {{ display: block; width: 100%; height: auto; overflow: visible; }}
.cy-w {{ font-family: var(--serif); font-weight: 500; font-size: 52px; letter-spacing: -.03em; fill: var(--ink); }}
.cy-w.cy-centre {{ fill: #C05B3D; font-size: 46px; }}
.cy-link {{ fill: none; stroke-width: 2; stroke-dasharray: 1 1; stroke-dashoffset: 0; }}
.cy-ring {{ stroke: var(--flood); }}
.cy-heat {{ stroke: #C05B3D; stroke-width: 1.5; }}
.cy-dot.cy-ring {{ fill: var(--flood); }}
.cy-arrow-r {{ fill: var(--flood); }} .cy-arrow-h {{ fill: #C05B3D; }}
.cy-dot.cy-heat {{ fill: #C05B3D; }}
.cy-verb {{ font-family: var(--mono); font-size: 13px; letter-spacing: .12em; text-transform: uppercase; fill: var(--ink-faint); }}
.cycle .cy-w, .cycle .cy-verb {{ transition: opacity .7s ease calc(var(--i) * .25s); }}
.cycle .cy-link {{ transition: stroke-dashoffset 1.1s ease calc(var(--i) * .3s + .3s); }}
.cycle .cy-flows {{ transition: opacity .8s ease 2.4s; }}
.cycle.pre .cy-w, .cycle.pre .cy-verb {{ opacity: 0; }}
.cycle.pre .cy-link {{ stroke-dashoffset: 1; }}
.cycle .cy-links {{ transition: opacity .4s ease .3s; }}
.cycle.pre .cy-links {{ opacity: 0; }}   /* arrowheads would otherwise show before their lines */
.cycle.pre .cy-flows {{ opacity: 0; }}
@media (prefers-reduced-motion: reduce) {{ .cy-flows {{ display: none; }} }}
.tubrow {{ display: flex; align-items: center; gap: 14px; margin-top: 16px; }}
.tub {{ width: 132px; height: auto; flex: none; }}
.tub-line {{ fill: none; stroke: var(--ink); stroke-width: 2.4; stroke-linecap: round; }}
.tub-water {{ fill: var(--flood); }}
.tubrow b {{ display: block; font-family: var(--serif); font-weight: 500; font-size: 24px; color: var(--ink); line-height: 1.1; }}
.tubrow span {{ display: block; font-family: var(--mono); font-size: 11px; letter-spacing: .08em; color: var(--ink-soft);
  margin-top: 4px; max-width: 30ch; }}
@media (max-width: 899px) {{ .tub {{ width: 64px; }} .tubrow b {{ font-size: 18px; }} .tubrow span {{ font-size: 10px; }} }}
.hud .place {{ font-family: var(--mono); font-size: 12px; font-weight: 500; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink); margin-bottom: 10px; }}
.where {{ position: absolute; right: 4vw; bottom: 6vh; width: min(220px, 30vw); z-index: 2; pointer-events: none; }}
.loc {{ display: block; width: 100%; height: auto; }}
.loc-land polygon {{ fill: var(--land); stroke: var(--ink-faint); stroke-width: .8; }}
.loc-dot {{ fill: var(--ink); }}
.loc-ring {{ fill: none; stroke: var(--flood); stroke-width: 1.5; }}
.loc-t {{ font-family: var(--mono); font-size: 13px; font-weight: 500; letter-spacing: .12em; fill: var(--ink); }}
@media (max-width: 899px) {{
  .where {{ bottom: auto; top: 5vh; right: 16px; width: 92px; }}
  #bath .hud {{ left: 16px; right: 120px; top: 5vh; text-align: left; }}
  #bath .hud .num {{ font-size: 46px; }}
  .hud .place {{ font-size: 10px; }} .pl-long {{ display: none; }}
  .tag3 {{ top: auto; bottom: 2vh; right: 16px; }}
  #pump .step p, #bath .step p {{ margin-top: 0; }}
}}
.chap-wrap {{ padding-top: 14vh; padding-bottom: 2vh; }}
.chap-n {{ display: block; font-family: var(--mono); font-size: 13px; font-weight: 500; letter-spacing: .2em;
  color: var(--ink); margin-bottom: 4px; }}
.chap-w {{ font-family: var(--serif); font-weight: 500; font-size: clamp(54px, 10.5vw, 124px); line-height: .9;
  letter-spacing: -.035em; margin: 0; color: var(--ink); }}
.chap-s {{ font-family: var(--serif); font-size: clamp(20px, 2.4vw, 26px); font-style: italic; letter-spacing: 0;
  color: var(--ink-soft); margin: 10px 0 0; }}
.chap.pre {{ opacity: 0; transform: translateY(28px); }}
.chap {{ transition: opacity .9s ease, transform .9s cubic-bezier(.2,.7,.2,1); }}
.seawrap {{ max-width: 1100px; margin: 22px auto 0; padding: 0 24px; }}
.seawrap canvas {{ display: block; width: 100%; height: clamp(300px, 42vw, 460px); }}
.ground3 {{ position: relative; height: min(78vh, 720px); max-width: 1200px; margin: 18px auto 0; }}
.ground3 canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.g3-lab {{ position: absolute; top: 4%; margin: 0; font-family: var(--mono); font-size: 11px;
  letter-spacing: .14em; text-transform: uppercase; color: var(--ink-soft); }}
.g3-lab span {{ display: block; font-family: var(--serif); font-size: 17px; letter-spacing: 0;
  text-transform: none; color: var(--ink); margin-top: 3px; }}
.g3-dry, .g3-wet {{ transform: translate(0, -100%); top: auto; }}
.g3-river {{ position: absolute; margin: 0; transform: translate(-50%, -100%); font-family: var(--mono);
  font-size: 11px; font-weight: 500; letter-spacing: .14em; text-transform: uppercase; color: var(--ink); }}
.g3-foot {{ position: absolute; left: 24px; right: 24px; bottom: 2%; display: flex; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin: 0; font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ink-soft); }}
#wk {{ height: 360vh; }}
.wk-stage {{ display: flex; align-items: center; justify-content: flex-end; }}
.wk-map {{ height: 92vh; width: min(62vw, 92vh * 0.92); margin-right: 3vw; }}
.wk-map svg {{ display: block; width: 100%; height: 100%; }}
#wk .step p.wk-cap {{ font-size: 15px; color: var(--ink-soft); line-height: 1.5; max-width: 330px; }}
#wk .step p.wk-cap b {{ display: block; font-family: var(--serif); font-weight: 500; font-size: clamp(28px, 3.4vw, 44px);
  line-height: 1.05; letter-spacing: -.02em; color: var(--ink); margin-bottom: 10px; }}
#wk .L {{ transition: opacity .8s ease; }}
#wk[data-step="0"] .L-wet, #wk[data-step="0"] .L-aemet, #wk[data-step="1"] .L-aemet {{ opacity: 0; }}
#wk[data-step="-1"] .L {{ opacity: 0; }}
.w8-pt {{ transition: opacity .5s ease calc(var(--k) * .09s), transform .5s cubic-bezier(.2,.9,.3,1.4) calc(var(--k) * .09s);
  transform-box: fill-box; transform-origin: center; }}
#wk[data-step="-1"] .w8-pt {{ opacity: 0; transform: translateY(-14px); }}
@media (max-width: 899px) {{ .wk-stage {{ justify-content: center; }} .wk-map {{ width: 94vw; height: 70vh; margin: 0; }} }}
.w8-sea {{ fill: var(--paper); }}
.w8-land {{ fill: var(--land); stroke: var(--ink-faint); stroke-width: .6; }}
.w8-wet {{ fill: var(--flood); stroke: var(--flood); stroke-width: .8; }}
.w8-aemet {{ stroke-width: .6; fill-opacity: .55; }}
.w8-amarillo {{ fill: #F2C94C; stroke: #B8901A; }}
.w8-naranja {{ fill: #E8893A; stroke: #A85A16; }}
.w8-rojo {{ fill: #C8322B; stroke: #7E1A15; }}
.w8-key .sw.aem {{ background: #F2C94C; opacity: .8; }}
.w8-country {{ font-family: var(--mono); font-size: 30px; font-weight: 500; letter-spacing: .5em; fill: var(--ink-soft); }}
.w8-sea-l {{ font-family: var(--serif); font-style: italic; font-size: 17px; letter-spacing: .12em; fill: var(--ink-soft); }}
.w8-isl {{ font-family: var(--mono); font-size: 11px; letter-spacing: .2em; fill: var(--ink-soft); }}
.w8-city {{ fill: var(--ink-soft); }}
.w8-city-t {{ font-family: var(--serif); font-size: 15px; fill: var(--ink); paint-order: stroke;
  stroke: var(--paper); stroke-width: 3px; }}
.wk-where {{ position: absolute; left: 6vw; bottom: 6vh; width: 170px; z-index: 2; }}
.loc-box {{ fill: none; stroke: var(--ink); stroke-width: 2; }}
@media (max-width: 899px) {{ .wk-where {{ left: auto; right: 16px; top: 4vh; bottom: auto; width: 96px; }} }}
.w8-mid {{ fill: none; stroke: var(--ink-faint); stroke-width: .8; }}
.w8-dry {{ fill: var(--paper); fill-opacity: .85 !important; stroke: var(--ink-faint); stroke-width: .8; stroke-dasharray: 3 2; }}
.w8-dot {{ fill: var(--ink); stroke: var(--paper); stroke-width: 1.5; }}
.w8-n {{ font-family: var(--mono); font-size: 13px; font-weight: 500; fill: var(--ink);
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
#pump {{ height: 860vh; }}
#pump .wk-only {{ display: none; }}
#pump.forecast .wk-only {{ display: block; }}
#pump.forecast .obs-only {{ display: none; }}
#pump.forecast .stage {{ box-shadow: inset 0 0 0 3px var(--ink); }}
.wk-unc {{ margin-top: 6px; max-width: 34ch; text-transform: none !important; letter-spacing: .02em !important;
  font-size: 12px !important; color: var(--ink-soft) !important; }}
#pump .step p.wk-cut {{ border-left: 0; padding: 0; max-width: 520px; font-family: var(--serif); font-weight: 500;
  font-size: clamp(44px, 7vw, 88px); line-height: 1; letter-spacing: -.03em; background: var(--paper); }}
#pump .step p.wk-cut span {{ display: block; font-family: var(--mono); font-weight: 400; font-size: 13px; letter-spacing: .08em;
  margin-top: 14px; color: var(--ink-soft); }}
.stage {{ position: sticky; top: 0; height: 100vh; overflow: hidden; }}
.stage canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.steps {{ position: absolute; top: 0; left: 0; right: 0; pointer-events: none; }}
.step {{ height: 105vh; display: flex; align-items: center; }}
#pump .step {{ height: 100vh; }}
#pump .step p, #bath .step p {{ margin-top: 22vh; }}
.when, .legend, .foot3 {{ z-index: 2; }}
.step p {{ max-width: 340px; margin: 0 0 0 6vw; padding: 4px 0 4px 16px; border-left: 3px solid var(--ink); font-size: 18px; }}
.hud {{ position: absolute; left: 6vw; top: 10vh; pointer-events: none; z-index: 2; }}
.hud .num {{ font-family: var(--mono); font-weight: 500; font-size: clamp(44px, 8vw, 84px); letter-spacing: -.03em;
  font-variant-numeric: tabular-nums; line-height: 1; }}
.hud .unit {{ font-family: var(--mono); font-size: 12px; letter-spacing: .16em; color: var(--ink-soft);
  margin-top: 10px; text-transform: uppercase; }}
.tag3 {{ position: absolute; top: 18px; right: 18px; font-family: var(--mono); font-size: 10px;
  letter-spacing: .14em; color: var(--ink-soft); text-transform: uppercase; }}
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
.lab.wind {{ font-weight: 500; font-size: 15px; background: var(--ink); color: var(--paper); padding: 5px 9px; }}
.foot3 {{ position: absolute; right: 4vw; top: 21vh; text-align: right; max-width: 30vw; font-family: var(--mono); font-size: 10px;
  letter-spacing: .12em; color: var(--ink-soft); text-transform: uppercase; }}
@media (max-width: 899px) {{
  .hud {{ left: 0; right: 0; top: 6vh; text-align: center; }}
  .step {{ align-items: flex-end; padding-bottom: 8vh; }}
  .step p {{ margin: 0 16px; max-width: none; }}
  .legend {{ top: auto; bottom: 14vh; right: 16px; }}
  .when {{ left: 16px; top: 5vh; }} .foot3 {{ left: 16px; right: auto; top: auto; bottom: 3vh; text-align: left; max-width: none; }}
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

<div class="col chap-wrap">{chapter("bath")}</div>
<section class="scrolly" id="bath" data-mm="{bath["mm"]}">
  <div class="stage">
    <canvas id="bath-gl" role="img" aria-label="A one-metre-square tray with 20 centimetre walls filling, to scale, to 159.1 millimetres of rain."></canvas>
    <div class="tag3">Drawn to scale &middot; 1 m square, 20 cm walls</div>
    <div class="where">{locator()}</div>
    <div class="hud"><div class="place">Barcelona<span class="pl-long"> &middot; Fabra observatory</span> &middot; 3 October 2026</div><div class="num" id="bath-num">{bath["mm"]:.1f} mm</div>
      <div class="unit" id="bath-unit">{bath["mm"]:.0f} litres on one square metre</div>
      <div class="tubrow" data-bath-l="{BATH_L}">{tub_svg()}<div><b id="bath-tubs">&asymp; one full bathtub</b><span>on every square metre &middot; a bath holds about {BATH_L} litres, for scale</span></div></div></div>
  </div>
  <div class="steps">{bath_steps}</div>
</section>

<section class="flat">
  <div class="col">{chapter("heat")}<p>{prose(w["heat"])}</p></div>
  <div class="wide"><figure>
    {heat_figure(flat)}
    <div class="key"><span>Colder</span><span class="rampbar"></span><span>Warmer</span><span>&middot; scale &plusmn;{flat["heat"]["full_c"]:g} &deg;C, saturates beyond</span></div>
    <figcaption>{h(heat_caption(flat))}</figcaption>
  </figure></div>
</section>

<section class="flat">
  <div class="col">{chapter("sea")}<p>{prose(w["sea"])}</p>
  </div>
  <div class="seawrap" id="sea" data-t-normal="{wm["c"] - wm["anom"]:.1f}" data-t2026="{wm["c"]:.1f}"
       data-e-normal="{ev["normal"]:.2f}" data-e2026="{ev["y2026"]:.2f}" data-e-pct="{ev["pct"]:+.0f}">
    <canvas id="sea-cv" aria-label="Two sea surfaces side by side. A normal September at {wm["c"] - wm["anom"]:.1f} degrees, and September 2026 at {wm["c"]:.1f} degrees, with water vapour rising from both at the measured evaporation rate."></canvas>
  </div>
  <div class="col">
    <p class="src">Temperatures measured: western Mediterranean (Alboran, Balearic, Gulf of Lion), September mean, ERA5; 2026 is the warmest September in a record going back to {wm["since"]} ({wm["rank"][0]} of {wm["rank"][1]}). The motion is illustrative: the warmer sea is drawn with a heat shimmer and slightly denser vapour, not to a measured rate.</p>
  </div>
</section>

<section class="flat">
  <div class="col">{chapter("air")}<p>{prose(w["vapour"])}</p>
    <div id="vap-strip" class="hero-strip">{strip(vp["by_year_pct"], "%", "Water vapour in the air, every September since 1940, % vs 1991-2020", "September")}</div>
    <p class="src">Global total column water vapour, area-weighted, ERA5. {h(vp["physics"][0].upper() + vp["physics"][1:])}.</p>
  </div>
</section>

<div class="col chap-wrap">{chapter("pump")}</div>
<section class="scrolly" id="pump">
  <div class="stage">
    <canvas id="pump-gl" role="img" aria-label="Map of the western Mediterranean, 27 September to 3 October 2026: a cold air pool over the Atlantic five kilometres up weakens, and the wind off Barcelona turns south-easterly, onshore from a record-warm sea."></canvas>
    <div class="when"><b id="pump-when">27 Sep, 00:00 UTC</b><span class="obs-only">ERA5 &middot; measured &middot; 2026 preliminary</span><span class="wk-only">ECMWF forecast &middot; run {h(pump["weekend"]["run"][:16].replace("T", " ")) if pump.get("weekend") else ""} UTC</span>
      <span class="wk-only wk-unc">AEMET on where the low will sit: &ldquo;elevada incertidumbre&rdquo;, high uncertainty.</span></div>
    <div class="legend">
      <div><span class="obs-only">Sea, September vs normal</span><span class="wk-only">Sea, 8 to 12 October vs normal</span> <i class="ramp"></i></div>
      <div>Cold air, 5 km up <i class="coldsw"></i></div>
      <div id="pump-lgwind" style="opacity:0">Wind, 1.5 km up <i class="windsw"></i></div>
    </div>
    <div class="lab" id="pump-lbcn">Barcelona</div>
    <div class="lab cold" id="pump-lbcold"></div>
    <div class="lab wind" id="pump-lbwind" style="opacity:0"></div>
    <div class="lab wind" id="pump-lbwind2" style="opacity:0"></div>
    <div class="foot3"><span class="obs-only">Heights exaggerated &middot; every layer is a measured field</span><span class="wk-only">Heights exaggerated &middot; cold air and wind are ECMWF's model forecast, not measurements</span></div>
  </div>
  <div class="steps">{pump_steps}</div>
</section>

<section class="flat">
  <div class="col">{chapter("ground")}<p>{prose(w["ground"])}</p>
  </div>
  <div class="ground3" id="ground">
    <canvas id="ground-gl" role="img" aria-label="Illustration: two hillsides under the same rain. Dry ground soaks it in; already wet ground fills and the rest runs off, so its river rises far higher."></canvas>
    <p class="g3-lab g3-dry">Dry ground<span>soaks the rain in</span></p>
    <p class="g3-lab g3-wet">Already wet<span>fills, and the rest runs off</span></p>
    <p class="g3-river">River</p><p class="g3-river">River</p>
    <p class="g3-foot"><span id="ground-clock">Hour 0 of 24</span><span>Same rain on both &middot; illustrative &middot; not to scale</span></p>
  </div>
  <div class="col">

  </div>
</section>

<section class="flat">
  <div class="col">{chapter("weekend")}<p>{prose(w["weekend"])}</p>
  </div>
</section>
{weekend_map(flat["ground"])}
<section class="flat" style="padding-top:2vh">
  <div class="col"><p class="src">Not a forecast of ours, and no combined score: each layer is shown as its source published it.</p></div>
</section>

<section class="flat eqsec">
  <div class="wide">{cycle_svg()}</div>
</section>

<section class="flat">
  <div class="col">
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
<script>
// Chapter words rise into place once, as they arrive. Without JS or with
// reduced motion they are simply there.
(function () {{
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var cs = document.querySelectorAll(".chap");
  cs.forEach(function (c) {{ c.classList.add("pre"); }});
  var io = new IntersectionObserver(function (es) {{
    es.forEach(function (e) {{ if (e.isIntersecting) {{ e.target.classList.remove("pre"); io.unobserve(e.target); }} }});
  }}, {{ threshold: 0.4 }});
  cs.forEach(function (c) {{ io.observe(c); }});
}})();
</script>
<script>
// The heat, May to September, as a continuous morph (Kristjan: "more
// fluid"). The page interpolates the monthly ERA5 anomaly grids pixel by
// pixel and recolours them on the site's ramp, under a fixed coastline
// overlay, so the heat flows rather than cutting between stills. The month
// label names the nearest month; the bar fills continuously. The <img>
// stack stays as the no-JS and reduced-motion figure (September).
(function () {{
  var box = document.getElementById("heatmove");
  if (!box || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  fetch("assets/heat_morph.json").then(function (r) {{ return r.json(); }}).then(function (M) {{
    var stack = box.querySelector(".hm-stack"), label = document.getElementById("hm-month");
    var ticks = box.querySelectorAll(".hm-ticks span");
    var rows = M.months[0].grid.length, cols = M.months[0].grid[0].length, n = M.months.length;
    var flat = M.months.map(function (m) {{ var a = new Float32Array(rows * cols), k = 0;
      m.grid.forEach(function (r) {{ r.forEach(function (v) {{ a[k++] = v === null ? NaN : v; }}); }}); return a; }});
    var ramp = M.ramp.map(function (h) {{ return [1, 3, 5].map(function (i) {{ return parseInt(h.substr(i, 2), 16); }}); }});
    function col(v) {{ var x = (Math.max(-1, Math.min(1, v / M.full_c)) + 1) * 4, i = Math.min(7, Math.floor(x)), f = x - i;
      return [0, 1, 2].map(function (c) {{ return ramp[i][c] * (1 - f) + ramp[i + 1][c] * f; }}); }}
    var lh = getComputedStyle(document.documentElement).getPropertyValue("--land").trim() || "#D9D8D0";
    var LAND = [1, 3, 5].map(function (i) {{ return parseInt(lh.substr(i, 2), 16); }});
    var src = document.createElement("canvas"); src.width = cols; src.height = rows;
    var sx = src.getContext("2d"), img = sx.createImageData(cols, rows);
    var cv = document.createElement("canvas"); cv.className = "hm-canvas";
    var lines = new Image(); lines.src = "assets/" + M.lines; lines.className = "hm-lines";
    stack.classList.add("morph");
    stack.insertBefore(cv, stack.firstChild); stack.insertBefore(lines, label);
    var ctx = cv.getContext("2d");
    function size() {{ var w = stack.clientWidth, h = w * M.size[1] / M.size[0], d = Math.min(devicePixelRatio || 1, 2);
      cv.width = Math.round(w * d); cv.height = Math.round(h * d); cv.style.height = h + "px"; }}
    addEventListener("resize", size); size();
    function draw(f) {{
      var k = Math.min(n - 2, Math.floor(f)), t = f - k, A = flat[k], B = flat[k + 1], d = img.data;
      for (var j = 0; j < A.length; j++) {{
        var v = A[j] + (B[j] - A[j]) * t, c = isNaN(v) ? LAND : col(v);
        d[j * 4] = c[0]; d[j * 4 + 1] = c[1]; d[j * 4 + 2] = c[2]; d[j * 4 + 3] = 255;
      }}
      sx.putImageData(img, 0, 0);
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
      ctx.drawImage(src, 0, 0, cv.width, cv.height);
      label.textContent = M.months[Math.round(f)].month + " 2026";
      ticks.forEach(function (tk, i) {{ var fill = Math.max(0, Math.min(1, f - i + 1));
        tk.style.backgroundSize = (fill * 100) + "% 3px, 100% 3px"; tk.classList.toggle("on", fill >= 1); }});
    }}
    var RUN = 9000, HOLD = 3500, t0 = null, on = false;
    function loop(ts) {{
      if (!on) return;
      if (t0 === null) t0 = ts;
      var e = (ts - t0) % (RUN + HOLD), f = Math.min(1, e / RUN) * (n - 1);
      draw(f); requestAnimationFrame(loop);
    }}
    // ?heat=F draws one moment (0 = May, 4 = September), for screenshots.
    var still = parseFloat(new URLSearchParams(location.search).get("heat"));
    draw(still >= 0 ? Math.min(n - 1, still) : n - 1);
    if (still >= 0) return;
    new IntersectionObserver(function (es) {{
      var was = on; on = es[0].isIntersecting;
      if (on && !was) {{ t0 = null; requestAnimationFrame(loop); }}
    }}, {{ threshold: 0.3 }}).observe(box);
  }});
}})();
// The closing loop draws itself link by link, then the water keeps
// flowing round it. Without JS or with reduced motion it is simply drawn.
(function () {{
  var c = document.getElementById("cycle");
  if (!c || !("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  c.classList.add("pre");
  var io = new IntersectionObserver(function (es) {{
    if (es[0].isIntersecting) {{ c.classList.remove("pre"); io.disconnect(); }}
  }}, {{ threshold: 0.45 }});
  io.observe(c);
}})();
</script>
<script>
// Weekend: the map's layers arrive with the captions, floods, then wet
// ground, then AEMET's warnings. Without JS every layer simply shows.
(function () {{
  var wk = document.getElementById("wk");
  if (!wk || !("IntersectionObserver" in window)) return;
  var steps = wk.querySelectorAll(".step");
  wk.dataset.step = "-1";
  var io = new IntersectionObserver(function (es) {{
    es.forEach(function (e) {{ if (e.isIntersecting) wk.dataset.step = String([].indexOf.call(steps, e.target)); }});
  }}, {{ rootMargin: "-45% 0px -45% 0px" }});
  steps.forEach(function (st) {{ io.observe(st); }});
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
