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


def page(w, preview):
    flat, pump, bath = data()
    imports = VENDOR
    ev, vp = flat["evap"], flat["vapour"]
    bath_steps = "".join('<div class="step"><p>%s</p></div>' % prose(w["bath-%d" % i]) for i in range(1, 5))
    pump_steps = "".join('<div class="step"><p>%s</p></div>' % prose(w["pump-%d" % i]) for i in range(1, 6))
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

/* the two 3D scenes: a sticky stage, captions scrolling past it */
.scrolly {{ position: relative; }}
#bath {{ height: 420vh; }}
#pump {{ height: 640vh; }}
.stage {{ position: sticky; top: 0; height: 100vh; overflow: hidden; }}
.stage canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.steps {{ position: absolute; top: 0; left: 0; right: 0; pointer-events: none; }}
.step {{ height: 105vh; display: flex; align-items: center; }}
#pump .step {{ height: 110vh; }}
.step p {{ max-width: 340px; margin: 0 0 0 6vw; background: color-mix(in srgb, var(--paper) 90%, transparent);
  padding: 14px 18px; border-left: 3px solid var(--ink); font-size: 18px; }}
.hud {{ position: absolute; left: 6vw; top: 10vh; pointer-events: none; }}
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
    <img src="assets/{flat["heat"]["img"]}" alt="Map of Europe, September 2026 temperature against 1991 to 2020: much warmer than normal over France, Iberia, the western and central Mediterranean and North Africa." width="{flat["heat"]["size"][0]}" height="{flat["heat"]["size"][1]}" loading="lazy">
    <div class="key"><span>Colder</span><span class="rampbar"></span><span>Warmer</span><span>&middot; scale &plusmn;{flat["heat"]["full_c"]:g} &deg;C, saturates beyond</span></div>
    <figcaption>{h(flat["heat"]["what"])}.</figcaption>
  </figure></div>
</section>

<section class="flat">
  <div class="col"><p class="kick">It starts from the sea</p><p>{prose(w["sea"])}</p>
    <div class="pair"><div><b>{ev["normal"]:.2f}</b><span>mm a day, a normal September</span></div>
      <div class="y26"><b>{ev["y2026"]:.2f}</b><span>mm a day, September 2026 &middot; {ev["pct"]:+.1f}%</span></div></div>
    <p class="src">Evaporation, Mediterranean sea cells, ERA5. Normal = 1991 to 2020. 2026 ranks {ev["rank"][0]} of {ev["rank"][1]} Septembers since 1991.</p>
    {strip(ev_series, " mm", "Evaporation each September, Mediterranean, mm a day", "September", 2)}
  </div>
  <div class="wide"><figure>
    <img src="assets/{ev["img"]}" alt="Map of the Mediterranean: evaporation in September 2026 against normal. Higher across most of the central and eastern basin; lower than normal off eastern Spain." width="{ev["size"][0]}" height="{ev["size"][1]}" loading="lazy">
    <div class="key"><span>Less</span><span class="rampbar"></span><span>More</span><span>&middot; scale &plusmn;{ev["full_pct"]}%</span></div>
    <figcaption>Evaporation, September 2026 against 1991 to 2020, ERA5.</figcaption>
  </figure></div>
</section>

<section class="flat">
  <div class="col"><p class="kick">Warm air holds more water</p><p>{prose(w["vapour"])}</p>
    {strip(vp["by_year_pct"], "%", "Water vapour in the air, every September since 1940, % vs 1991-2020", "September")}
    <p class="src">Global total column water vapour, area-weighted, ERA5. {h(vp["physics"][0].upper() + vp["physics"][1:])}.</p>
  </div>
  <div class="wide"><figure>
    <img src="assets/{vp["img"]}" alt="World map of water vapour in September 2026 against normal: patchy, with large areas above normal." width="{vp["size"][0]}" height="{vp["size"][1]}" loading="lazy">
    <div class="key"><span>Drier</span><span class="rampbar"></span><span>Moister</span><span>&middot; scale &plusmn;{vp["full_pct"]}%</span></div>
    <figcaption>Total column water vapour, September 2026 against 1991 to 2020, ERA5.</figcaption>
  </figure></div>
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
    <div class="foot3">Heights exaggerated &middot; every layer is a measured field</div>
  </div>
  <div class="steps">{pump_steps}</div>
</section>

<section class="flat">
  <div class="col"><p class="kick">The ground can't drink that fast</p><p>{prose(w["ground"])}</p>
    {fig_ground("Topsoil after the first storm, against the same days in 1991 to 2020:", "ERA5, top 7 cm, 8 to 10 October")}
    {ground_table(flat["ground"])}
  </div>
</section>

<section class="flat">
  <div class="col"><p class="kick">This weekend</p><p>{prose(w["weekend"])}</p>
    <p class="src">Map added when AEMET's Friday update is out: AEMET's warning areas, ground wetness by area, past floods. Each layer labelled with its source. Not a forecast of ours, and no combined score.</p>
  </div>
</section>

<section class="flat">
  <div class="col"><p class="kick">What this is not</p><p>{prose(w["not"])}</p>
    <p class="src">Data: ERA5 (Copernicus Climate Change Service), 2026 preliminary; AEMET (Barcelona Fabra, station 0200E). Compiled by the floods desk.</p>
  </div>
</section>
</main>
{GROUND_JS}
<script src="{MOTION}"></script>
<script type="module" src="scene_bathtub.js"></script>
<script type="module" src="scene_pump.js"></script>
{ANALYTICS_SNIPPET}
</body>
</html>
"""


def main():
    preview = "--preview" in sys.argv
    w = words()
    holes = [k for k, v in w.items() if v.startswith("[WORDS")]
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
