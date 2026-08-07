"""Stacked against mirrored, same data, so the choice is made by eye.

Kristjan asked to see the stacked version. Built rather than argued.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())["cities"]["Paris"]
SY = json.loads((R / "heat/data/city_series.json").read_text())["cities"]["Paris"]["years"]
TH = N["days"]["thresholds_c"]["95"]
DNOW, NNOW = N["days"]["days_2026"]["95"], N["nights_2026"]

def ser(key, sub=None):
    out = []
    for y, v in SY.items():
        if not v.get("usable_to_cut"):
            continue
        raw = v.get(key)
        val = raw.get(sub) if (sub and isinstance(raw, dict)) else raw
        if val is not None:
            out.append((int(y), val))
    return sorted(out)

DAYS = [(y, n) for y, n in ser("days_to_cut", "95") if y < 2026] + [(2026, DNOW)]
NIGHTS = dict([(y, n) for y, n in ser("nights_to_cut") if y < 2026] + [(2026, NNOW)])
Y0 = DAYS[0][0]
TOP_M = max(max(n for _, n in DAYS), max(NIGHTS.values()))
TOP_S = max(d + NIGHTS.get(y, 0) for y, d in DAYS)


def ticks(bw, y):
    return "".join(f'<text x="{i*bw:.1f}" y="{y}" class="ax">{yr}</text>'
                   for i, (yr, _) in enumerate(DAYS) if yr in (1950, 1976, 2000, 2026))


def stacked(w=880, h=200):
    bw = w / len(DAYS)
    out = []
    for i, (y, d) in enumerate(DAYS):
        x, n = i * bw, NIGHTS.get(y, 0)
        c = "var(--accent)" if y == 2026 else "var(--ink)"
        if d:
            out.append(f'<rect x="{x:.1f}" y="{h-(d+n)/TOP_S*h:.1f}" width="{bw-1.2:.1f}" '
                       f'height="{d/TOP_S*h:.1f}" fill="{c}"/>')
        if n:
            out.append(f'<rect x="{x:.1f}" y="{h-n/TOP_S*h:.1f}" width="{bw-1.2:.1f}" '
                       f'height="{n/TOP_S*h:.1f}" fill="{c}" opacity="0.5"/>')
    return (f'<svg viewBox="0 0 {w} {h+18}" width="100%" style="height:{h+18}px" '
            f'preserveAspectRatio="none">{"".join(out)}{ticks(bw, h+13)}</svg>')


def mirrored(w=880, up=112, dn=88):
    bw = w / len(DAYS)
    out = []
    for i, (y, d) in enumerate(DAYS):
        x, n = i * bw, NIGHTS.get(y, 0)
        c = "var(--accent)" if y == 2026 else "var(--ink)"
        if d:
            out.append(f'<rect x="{x:.1f}" y="{up-d/TOP_M*up:.1f}" width="{bw-1.2:.1f}" '
                       f'height="{d/TOP_M*up:.1f}" fill="{c}"/>')
        if n:
            out.append(f'<rect x="{x:.1f}" y="{up+1:.1f}" width="{bw-1.2:.1f}" '
                       f'height="{n/TOP_M*dn:.1f}" fill="{c}" opacity="0.55"/>')
    return (f'<svg viewBox="0 0 {w} {up+dn+20}" width="100%" '
            f'style="height:{up+dn+20}px" preserveAspectRatio="none">{"".join(out)}'
            f'<line x1="0" y1="{up}" x2="{w}" y2="{up}" stroke="var(--ink)" '
            f'stroke-width="1.4"/>{ticks(bw, up+dn+15)}</svg>')


tallest = max(DAYS, key=lambda t: t[1] + NIGHTS.get(t[0], 0))
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stacked or mirrored &middot; The Long Swell</title><style>
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:960px;margin:0 auto;padding:26px 24px 80px}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:34px;line-height:1.12;
color:var(--ink);margin:0 0 8px}}
.sub{{max-width:66ch;margin:0 0 10px}}
.lab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:2.4px solid var(--ink);
padding-bottom:9px;margin:44px 0 18px}}
.ax{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}}
.cap{{font-size:15.5px;line-height:1.6;max-width:74ch;margin:12px 0 0}}
.key{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--ink-faint);
margin:8px 0 0}}
.key b{{color:var(--ink);font-weight:500}}
</style></head><body><main>
<h1>Stacked or mirrored</h1>
<p class="sub">Paris, every summer since {Y0}. Same two numbers both times:
days above {TH}&nbsp;&deg;C and nights above 20&nbsp;&deg;C, counted to the same date
each year.</p>

<div class="lab">Stacked</div>
{stacked()}
<p class="key"><b>solid</b> hot days &nbsp; <b>faded</b> hot nights &nbsp;
tallest bar {tallest[0]}, {tallest[1]}&nbsp;+&nbsp;{NIGHTS.get(tallest[0],0)}&nbsp;=&nbsp;{tallest[1]+NIGHTS.get(tallest[0],0)}</p>
<p class="cap">Reads as one rising quantity, which is the appeal. The bar height is
days plus nights, and those can be the same 24 hours: a day above {TH}&nbsp;&deg;C
followed by a night above 20&nbsp;&deg;C counts twice. So the tallest bar says
{tallest[1]+NIGHTS.get(tallest[0],0)} of something, and there is no something.</p>

<div class="lab">Mirrored</div>
{mirrored()}
<p class="key"><b>above</b> hot days &nbsp; <b>below</b> hot nights &nbsp;
one shared scale</p>
<p class="cap">Nothing is summed. The extra thing it shows: the nights half stays
empty for decades while the days half is already busy, so the two measures diverge in
TIME as well as size. That is invisible when they are stacked into one height.</p>
</main></body></html>"""
out = R / "design/review/stack-vs-mirror.html"
out.write_text(html)
print(f"wrote {out} | tallest stacked bar {tallest[0]}: "
      f"{tallest[1]}+{NIGHTS.get(tallest[0],0)}={tallest[1]+NIGHTS.get(tallest[0],0)}")
