"""The youth test page: one map, one country template (D-349, D-350).

ONE MEASURE, NOTHING BLENDED. The index failed its pre-registered outside
check and was dropped (D-349), so the map colours by a single question: the
share of young people dissatisfied with how democracy works in their country.
No score, tier or type anywhere, and the classes carry numbers only: a
hot-looking map would bring the dropped index back by the look alone, so the
ramp is the cool side of the house palette, not red.

WHOLE NUMBERS, FROM THE DATA. The source rounds each wave to a point. TLS Youth
emits whole-number display fields from the raw shares (rounding their
one-decimal values would round twice), so this reads those and only falls back
to rounding on the working shape, before they land. Gaps are never printed:
rounding makes three printed figures disagree in 22 of 84 rows, so a gap is
shown by the dots and `gap_read` in words, and the interval stays on hover.

Words are editor's, in copy/youth.md. Data is TLS Youth's, in youth/data/. A
block with no data draws a dashed "not yet measured", never a gap.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "design"))

import copydeck                                                # noqa: E402
import tokens as T                                             # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS, SITE_NAME,  # noqa: E402
                       h, site_masthead)
from templates.page_head import head_meta                      # noqa: E402

# Five classes, 15 points wide (TLS Youth: their intervals run about +/-5 and
# reach +/-8 for Malta and Cyprus, so narrower classes imply differences the
# data cannot support). Cool and sequential, on purpose; see the docstring.
CLASS_EDGES = (15, 30, 45, 60)
CLASS_LABELS = ("under 15", "15-30", "30-45", "45-60", "60 and over")
CLASS_FILL = ("#D9E4E6", "#A9C1C8", "#6F98A4", "#417785", "#0A4A57")
# Too small to find or tap at map scale: a marker as well as the shape.
SMALL_STATES = {"MT", "LU"}
# Lambert azimuthal equal-area on 52N 10E, the standard frame for Europe.
LAT0, LON0 = math.radians(52.0), math.radians(10.0)
# Measured from the 28 countries' outlines (-1684 to 2172 km east, -1781 to
# 2099 km north) plus a margin; overseas territories fall outside it.
FRAME = (-1740.0, 2230.0, 2150.0, -1830.0)  # x0, x1, y0(top), y1(bottom), km
GEO_NAMES = {"Czechia": ("Czechia", "Czech Republic"),
             "United Kingdom": ("United Kingdom",)}


def _laea(lon, lat):
    la, lo = math.radians(lat), math.radians(lon)
    k = 6371.0 * math.sqrt(2.0 / (1 + math.sin(LAT0) * math.sin(la)
                                  + math.cos(LAT0) * math.cos(la)
                                  * math.cos(lo - LON0)))
    return (k * math.cos(la) * math.sin(lo - LON0),
            k * (math.cos(LAT0) * math.sin(la)
                 - math.sin(LAT0) * math.cos(la) * math.cos(lo - LON0)))


def _class(v):
    return sum(1 for e in CLASS_EDGES if v >= e)


def _whole(rec, key):
    """The whole-number display field if TLS Youth emits one, else the
    working shape rounded half up. Never used for classing or sorting."""
    for k in (key.replace("_pct", "_display"), key + "_display"):
        if rec.get(k) is not None:
            return int(rec[k])
    v = rec.get(key)
    return None if v is None else int(v + 0.5)


def _rings(geom):
    c = geom["coordinates"]
    return c if geom["type"] == "Polygon" else [r for p in c for r in p]


def _svg_paths(geom, W, H):
    x0, x1, y0, y1 = FRAME
    sx, sy = W / (x1 - x0), H / (y1 - y0)
    out, hit = [], False
    for ring in _rings(geom):
        pts = []
        for lon, lat in ring:
            x, y = _laea(lon, lat)
            px, py = (x - x0) * sx, (y - y0) * sy
            hit = hit or (-40 <= px <= W + 40 and -40 <= py <= H + 40)
            pts.append("%.1f %.1f" % (px, py))
        out.append("M" + "L".join(pts) + "Z")
    return "".join(out), hit


def _centre(geom, W, H):
    x0, x1, y0, y1 = FRAME
    big = max(_rings(geom), key=len)
    xs, ys = zip(*(_laea(*p) for p in big))
    return ((sum(xs) / len(xs) - x0) * W / (x1 - x0),
            (sum(ys) / len(ys) - y0) * H / (y1 - y0))


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:var(--serif);font-size:17.5px;line-height:1.62}
.yw{max-width:820px;margin:0 auto;padding:30px 24px 90px}
h1{font-weight:400;font-size:36px;line-height:1.14;letter-spacing:-.016em;
 margin:10px 0 14px;max-width:24ch;text-wrap:pretty}
.ylede{max-width:62ch;margin:0 0 22px;color:var(--ink-soft);text-wrap:pretty}
.ylede strong{color:var(--ink);font-weight:500}
.ymono{font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--ink-faint)}
.ymap{display:block;width:100%;height:auto;margin:6px 0 0}
.ymap a{outline:none}
.ymap .c{stroke:var(--paper);stroke-width:.8}
.ymap a:hover .c,.ymap a:focus .c{stroke:var(--ink);stroke-width:1.6}
.ymap .video{stroke:var(--ink);stroke-width:1;stroke-dasharray:3 2}
.ymap .o{fill:none;stroke:var(--rule);stroke-width:.6}
.ywho{max-width:62ch;margin:16px 0 0;font-size:17.5px}
.yread{font-family:var(--mono);font-size:12.5px;min-height:1.7em;color:var(--ink);margin:8px 0 0}
.ylg{display:flex;flex-wrap:wrap;gap:6px 14px;font-family:var(--mono);font-size:11px;
 color:var(--ink-faint);margin:10px 0 0;align-items:center}
.ylg i{display:inline-block;width:18px;height:10px;margin-right:5px;vertical-align:-1px}
.ylg .dv{background:none;border:1px dashed var(--ink)}
.ysec{margin-top:44px;border-top:3px solid var(--ink);padding-top:12px}
.ysec h2{font-weight:500;font-size:20px;margin:0 0 12px}
.yrow{display:grid;grid-template-columns:minmax(0,11em) 3.2em minmax(0,1fr);gap:4px 12px;
 align-items:center;padding:7px 0;border-bottom:1px solid var(--rule);font-size:15px}
.yrow a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}
.yrow a:hover{border-bottom-color:var(--ink)}
.yrow .n{font-family:var(--mono);font-size:14px;text-align:right}
.ystrip{position:relative;margin:0 6px}
.ystrip i{position:absolute;top:50%;display:block}
.ystrip .yl{left:-6px;right:-6px;height:1px;background:var(--rule)}
.ystrip .yt{width:2px;height:12px;margin:-6px 0 0 -1px;background:var(--ink-faint)}
.ystrip .yo{width:9px;height:9px;margin:-4.5px 0 0 -4.5px;border-radius:50%;
 background:var(--paper);border:1.4px solid var(--ink)}
.ystrip .yy{width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;background:var(--ink)}
.yrow .r{grid-column:3;padding-left:6px;font-family:var(--mono);font-size:11px;color:var(--ink-faint)}
.yq{padding:12px 0;border-bottom:1px solid var(--rule)}
.yq p{margin:0 0 6px;font-size:15px;color:var(--ink-soft);max-width:62ch}
.yq .r{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint)}
.ybar{display:grid;grid-template-columns:8.5em minmax(0,1fr) 3em;gap:4px 10px;align-items:center;
 font-size:14.5px;padding:3px 0}
.ybar .t{background:var(--paper-sunk);height:12px;position:relative}
.ybar .f{position:absolute;left:0;top:0;bottom:0;background:var(--ink)}
.ybar .n{font-family:var(--mono);font-size:13px;text-align:right}
.ydash{border:1px dashed var(--rule);padding:14px;font-family:var(--mono);font-size:12px;color:var(--ink-faint)}
.ylist{margin:0;padding:0 0 0 1.1em;font-size:15px;color:var(--ink-soft);max-width:62ch}
.ylist li{margin:0 0 6px}
.ygrey{border-left:3px solid var(--ink-faint);padding:6px 0 6px 14px;margin:0 0 20px;font-size:15px;color:var(--ink-soft)}
.yback{font-family:var(--mono);font-size:11px}
.yback a{color:var(--ink-faint)}
@media (max-width:560px){h1{font-size:28px}
 .yrow{grid-template-columns:minmax(0,1fr) 3.2em}.ystrip{grid-column:1/-1}.yrow .r{grid-column:1/-1}}
"""


def _page(title, description, path, root_prefix, body, script=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_meta(title=title, description=description, path=path)}
<title>{h(title)}</title>
<style>{T.font_faces_css(root_prefix + "fonts/")}
:root {{ color-scheme: light dark; {T.css_variables()} }}
@media (prefers-color-scheme: dark) {{ :root {{ {T.css_variables(dark=True)} }} }}
{SITE_MASTHEAD_CSS}
{CSS}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix)}
<main class="yw">
{body}
</main>
{script}
</body>
</html>
"""


def _strip(young, older, eu, height=18, label=False):
    """Young (filled), older (hollow), EU (tick), on 0 to 100. Positioned
    elements, not a stretched SVG: dots stay round at every width."""
    def at(v):
        return f"left:{max(0, min(100, v)):.1f}%"
    p = ['<i class="yl"></i>']
    if eu is not None:
        p.append(f'<i class="yt" style="{at(eu)}"></i>')
    if older is not None:
        p.append(f'<i class="yo" style="{at(older)}"></i>')
    if young is not None:
        p.append(f'<i class="yy" style="{at(young)}"></i>')
    return (f'<div class="ystrip" style="height:{height}px" aria-hidden="true">'
            f'{"".join(p)}</div>')


def _key(young_label, older_label):
    return (f'<div class="ylg"><span>&#9679; {h(young_label)}</span>'
            f'<span>&#9675; {h(older_label)}</span>'
            f'<span>| EU average</span></div>')


def render_map(doc, geo, root_prefix="../"):
    M = doc["measure"]
    eu = M["comparator"]["young_pct"]
    # EU27 rows only, for the range and the counts: the UK is on the map but
    # is not one of the 27 the sentences name.
    eu_rows = [c for c in doc["countries"].values() if c.get("in_eu27_average")]
    lo_c = min(eu_rows, key=lambda c: c["map_value_pct"])
    hi_c = max(eu_rows, key=lambda c: c["map_value_pct"])
    lede = _slot("map_lede", eu_avg=int(eu + 0.5),
                 min_pct=_whole(lo_c, "map_value_pct"), min_name=lo_c["name"],
                 max_pct=_whole(hi_c, "map_value_pct"), max_name=hi_c["name"])
    young_hi = sorted(c["name"] for c in eu_rows if c.get("gap_read") == "young higher")
    n_older = sum(1 for c in eu_rows if c.get("gap_read") == "older higher")
    who = (_slot("older_some", n_young_higher=len(young_hi),
                 young_higher_names=", ".join(young_hi), n_older_higher=n_older)
           if young_hi else _slot("older_none", n_older_higher=n_older))
    title = _plain_slot("map_title")
    W, H = 800, 802  # the frame's own aspect, so nothing is stretched
    by_name = {f["properties"]["name"]: f for f in geo["features"]}
    C = doc["countries"]
    want = {}
    for iso, c in C.items():
        for nm in GEO_NAMES.get(c["name"], (c["name"],)):
            if nm in by_name:
                want[iso] = by_name[nm]
                break
    missing = sorted(set(C) - set(want))
    if missing:
        raise SystemExit(f"no outline for {missing} in fires/data/countries.geo.json")
    used = {id(f) for f in want.values()}
    ctx, shapes, dots = [], [], []
    for f in geo["features"]:
        if id(f) in used:
            continue
        d, hit = _svg_paths(f["geometry"], W, H)
        if hit:
            ctx.append(f'<path class="o" d="{d}"/>')
    for iso, c in sorted(C.items(), key=lambda kv: kv[1]["name"]):
        v = c["map_value_pct"]
        fill = CLASS_FILL[_class(v)]
        d, _ = _svg_paths(want[iso]["geometry"], W, H)
        lo, hi = c.get("map_interval90") or (None, None)
        lab = f'{c["name"]}: {_whole(c, "map_value_pct")}%'
        read = (f'{c["name"]} {_whole(c, "map_value_pct")}%'
                + (f' &middot; 90% interval {int(lo+.5)} to {int(hi+.5)}' if lo is not None else "")
                + (f' &middot; people 55 and over {_whole(c, "older_pct")}%' if c.get("older_pct") is not None else ""))
        vid = " video" if c.get("interview_mode_mark") else ""
        marker = ""
        if iso in SMALL_STATES:
            x, y = _centre(want[iso]["geometry"], W, H)
            marker = f'<circle class="c{vid}" cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{fill}"/>'
        shapes.append(
            f'<a href="{iso.lower()}/" data-r="{read}" aria-label="{h(lab)}">'
            f'<title>{h(lab)}</title><path class="c{vid}" fill="{fill}" d="{d}"/>{marker}</a>')
    svg = (f'<svg class="ymap" viewBox="0 0 {W} {H}" role="group" '
           f'aria-label="Map of Europe, each country shaded by the share of young people dissatisfied with democracy">'
           + "".join(ctx) + "".join(shapes) + dots_join(dots) + '</svg>')
    legend = "".join(f'<span><i style="background:{CLASS_FILL[k]}"></i>{CLASS_LABELS[k]}</span>'
                     for k in range(5))
    rows = []
    for iso, c in sorted(C.items(), key=lambda kv: -kv[1]["map_value_pct"]):
        mark = " &dagger;" if c.get("interview_mode_mark") else ""
        out = "" if c.get("in_eu27_average", True) else " *"
        lo, hi = c.get("map_interval90") or (None, None)
        tip = f'90% interval {int(lo+.5)} to {int(hi+.5)}' if lo is not None else ""
        rows.append(
            f'<div class="yrow" title="{h(tip)}"><span><a href="{iso.lower()}/">{h(c["name"])}</a>{mark}{out}</span>'
            f'<span class="n">{_whole(c, "map_value_pct")}%</span>'
            + _strip(c["map_value_pct"], c.get("older_pct"), eu)
            + f'<span class="r">{h(_gap_words(c.get("gap_read")))}</span></div>')
    limits = "".join(f"<li>{h(x)}</li>" for x in M.get("limits", []))
    body = (
        f'<h1>{h(title)}</h1><p class="ylede">{lede}</p>'
        + svg + '<p class="yread" id="yread" aria-live="polite"></p>'
        f'<div class="ylg">{legend}<span><i class="dv"></i>{h(_plain_slot("video_legend"))}</span>'
        f'<span>% of people {h(M["young"])}</span></div>'
        f'<p class="ywho">{who}</p>'
        f'<div class="ysec"><h2>{h(_plain_slot("every_country_heading"))}</h2>'
        + _key(M["young"], M["older"]) + "".join(rows)
        + (f'<p class="ymono" style="margin-top:12px">* Not in the EU average. &dagger; {h(_plain_slot("video_note"))}</p>')
        + '</div>'
        f'<div class="ysec"><h2>{h(_plain_slot("limits_heading"))}</h2><ul class="ylist">{limits}</ul>'
        f'<p class="ymono" style="margin-top:12px">{h(M["wording"])}. {h(M["source"])}</p></div>')
    script = """<script>(function(){var r=document.getElementById('yread');
if(!r)return;document.querySelectorAll('.ymap a').forEach(function(a){
function s(){r.innerHTML=a.getAttribute('data-r')}
a.addEventListener('mouseenter',s);a.addEventListener('focus',s);});})();</script>"""
    return _page(title, _strip_tags(lede), "/youth/", root_prefix, body, script)


def dots_join(dots):
    return "".join(dots)


def _strip_tags(s):
    import re
    return " ".join(re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ").split())


def _plain_slot(name):
    return " ".join(copydeck.load("youth")[name].split())


def _slot(name, **values):
    """One slot with figures, through copydeck's checks (a placeholder with
    no value, or a value no slot uses, refuses the build)."""
    others = [k for k in copydeck.load("youth") if k != name]
    return copydeck.render("youth", values, wanted=[name],
                           placed_elsewhere=others)[name]


# gap_read is TLS Youth's enum; what a reader sees is the editor's.
_GAP_SLOT = {"older higher": "gap_older_higher",
             "young higher": "gap_young_higher",
             "no clear difference": "gap_no_clear"}


def _gap_words(read):
    """Refuses an unknown value: printing the raw enum is how "older higher"
    reached the page in the first place."""
    if not read:
        return ""
    if read not in _GAP_SLOT:
        raise SystemExit(f"gap_read {read!r} has no words in copy/youth.md")
    return _plain_slot(_GAP_SLOT[read])


def _dashed(text=None):
    return f'<div class="ydash">{h(text or _plain_slot("not_measured"))}</div>'


def _sec(slot, inner):
    return f'<div class="ysec"><h2>{h(_plain_slot(slot))}</h2>{inner}</div>'


def _bar(label, pct):
    n = int(pct + 0.5) if pct is not None else None
    fill = f'<span class="f" style="width:{pct:.1f}%"></span>' if pct is not None else ""
    return (f'<div class="ybar"><span>{h(label)}</span><span class="t">{fill}</span>'
            f'<span class="n">{"" if n is None else str(n) + "%"}</span></div>')


def render_country(c, entry, doc, root_prefix="../../", show_grey=False):
    iso, name = c["iso"], c["name"]
    M = doc["measure"]
    date = M["newest_fieldwork_ends"]
    grey = entry.get("level") == "grey" and not show_grey
    head = (f'<p class="yback"><a href="../">&larr; All countries</a></p><h1>{h(name)}</h1>'
            f'<p class="ymono">Survey data to {h(date)}. People {h(c["young"])} against people {h(c["older"])}.</p>')
    if c.get("headline"):
        head += f'<p class="ylede">{h(c["headline"])}</p>'
    if grey:
        body = head + (f'<div class="ygrey">{h(_plain_slot("not_checked"))} '
                       f'{h(entry.get("grey_reason") or "")}</div>')
        return _page(f"{name}: young people and democracy | {SITE_NAME}",
                     f"{name}: young people's dissatisfaction with democracy, survey data to {date}.",
                     f"/youth/{iso.lower()}/", root_prefix, body)

    # Block 2. Dots and gap_read in words; never a printed gap.
    b2 = c.get("block2_discontent") or {}
    rows = []
    for k in ("democracy", "distrust", "direction"):
        r = b2.get(k)
        if not r:
            continue
        cmp_ = (r.get("comparator") or {}).get("young_pct")
        lo, hi = r.get("young_interval90") or (None, None)
        tip = f'90% interval {int(lo+.5)} to {int(hi+.5)}' if lo is not None else ""
        cmp_w = _whole(r.get("comparator") or {}, "young_pct")
        rows.append(
            f'<div class="yq" title="{h(tip)}"><p>{h(r["wording"])}</p>'
            + _strip(r.get("young_pct"), r.get("older_pct"), cmp_, height=30)
            + f'<div class="r">Young {_whole(r, "young_pct")}% &middot; older {_whole(r, "older_pct")}%'
            + (f' &middot; young Europeans {cmp_w}%' if cmp_w is not None else "")
            + f' &middot; {h(_gap_words(r.get("gap_read")))}</div></div>')
    block2 = _key(c["young"], c["older"]) + "".join(rows) if rows else _dashed()

    # Block 3.
    b3 = c.get("block3_life_against_country") or {}
    yb, ob = b3.get("young") or {}, b3.get("older") or {}
    block3 = ""
    if yb:
        block3 = ('<p class="ymono">Say things are going in the wrong direction</p>'
                  + _bar("My life, young", yb.get("my_life_wrong_pct"))
                  + _bar("My country, young", yb.get("my_country_wrong_pct"))
                  + _bar("My life, older", ob.get("my_life_wrong_pct"))
                  + _bar("My country, older", ob.get("my_country_wrong_pct")))
    ls = b3.get("life_satisfaction")
    if ls:
        block3 += f'<p class="ymono" style="margin-top:10px">{h(ls.get("sentence") or "")}</p>'
    block3 = block3 or _dashed()

    # Block 6. Flash 585 Q7a: a petition counts, so it is never called protest.
    b6 = c.get("block6_action_to_change_society") or {}
    now = c.get("block6_now") or c.get("now_marker")
    block6 = (f'<p>{h(now.get("text"))}</p>' if isinstance(now, dict) and now.get("text")
              else _dashed(_plain_slot("not_checked")))
    if b6.get("young_pct") is not None:
        cm = b6.get("comparator") or {}
        block6 += (f'<div class="yq" style="margin-top:12px"><p>{h(b6.get("wording") or "")}</p>'
                   + _bar(name, b6.get("young_pct"))
                   + _bar(cm.get("label") or "EU", cm.get("young_pct"))
                   + f'<div class="r">Ages {h(b6.get("ages") or "")} &middot; {h(b6.get("fieldwork") or "")} &middot; {h(b6.get("source") or "")}</div></div>')

    def generic(key):
        b = c.get(key)
        if not b:
            return _dashed()
        items = b.get("rows") if isinstance(b, dict) else None
        if not items:
            return f'<p class="ymono">{h(json.dumps(b, ensure_ascii=False))[:400]}</p>'
        out = ""
        for it in items:
            out += _bar(it.get("label", ""), it.get("value_pct"))
        return out

    # Block 8.
    src = f'<p class="ymono">{h(c.get("source") or "")}</p>'
    if c.get("interview_mode_mark"):
        src += f'<p class="ymono">&dagger; {h(_plain_slot("video_note"))}</p>'
    limits = "".join(f"<li>{h(x)}</li>" for x in M.get("limits", []))
    help_ = c.get("helpline")
    block8 = (src + f'<ul class="ylist" style="margin-top:10px">{limits}</ul>'
              + (f'<p style="margin-top:10px">{h(help_.get("text") if isinstance(help_, dict) else help_)}</p>'
                 if help_ else '<div style="margin-top:10px">' + _dashed("National helpline: " + _plain_slot("not_measured").lower()) + '</div>'))

    body = (head
            + _sec("block2_name", block2) + _sec("block3_name", block3)
            + _sec("block4_name", generic("block4_issues"))
            + _sec("block5_name", generic("block5_starting_out"))
            + _sec("block6_name", block6)
            + _sec("block7_name", generic("block7_contrast"))
            + _sec("block8_name", block8))
    return _page(f"{name}: young people and democracy | {SITE_NAME}",
                 f"{name}: young people's dissatisfaction with democracy, survey data to {date}.",
                 f"/youth/{iso.lower()}/", root_prefix, body)
