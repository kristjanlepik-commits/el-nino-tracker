"""Stacked against mirrored, same data, so the choice is made by eye."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())["cities"]["Paris"]
SY = json.loads((R / "heat/data/city_series.json").read_text())["cities"]["Paris"]["years"]
TH = N["days"]["thresholds_c"]["95"]
DNOW, NNOW = N["days"]["days_2026"]["95"], N["nights_2026"]

days, nights = [], {}
for y, v in SY.items():
    if not v.get("usable_to_cut"):
        continue
    if v.get("days_to_cut"):
        days.append((int(y), v["days_to_cut"]["95"]))
    if v.get("nights_to_cut") is not None:
        nights[int(y)] = v["nights_to_cut"]
DAYS = sorted([(y, n) for y, n in days if y < 2026] + [(2026, DNOW)])
nights[2026] = NNOW
Y0 = DAYS[0][0]
D_MAX, N_MAX = max(n for _, n in DAYS), max(nights.values())
PREV_D = max(n for y, n in DAYS if y < 2026)
PREV_N = max(v for y, v in nights.items() if y < 2026)
W, PAD, K = 880, 40, 4.0          # PAD: the 2026 bar sat on the edge and clipped
BW = (W - PAD) / len(DAYS)


def ticks(y):
    return "".join(
        f'<text x="{i*BW+(BW if yr == 2026 else 0):.1f}" y="{y}" class="ax" '
        f'text-anchor="{"end" if yr == 2026 else "start"}">{yr}</text>'
        for i, (yr, _) in enumerate(DAYS) if yr in (1950, 1976, 2000, 2026))


def stacked(h=190):
    top = max(d + nights.get(y, 0) for y, d in DAYS)
    out = []
    for i, (y, d) in enumerate(DAYS):
        x, n = i * BW, nights.get(y, 0)
        c = "var(--accent)" if y == 2026 else "var(--ink)"
        if d:
            out.append(f'<rect x="{x:.1f}" y="{h-(d+n)/top*h:.1f}" width="{BW-1.2:.1f}" '
                       f'height="{d/top*h:.1f}" fill="{c}"/>')
        if n:
            out.append(f'<rect x="{x:.1f}" y="{h-n/top*h:.1f}" width="{BW-1.2:.1f}" '
                       f'height="{n/top*h:.1f}" fill="{c}" opacity="0.5"/>')
    return (f'<svg viewBox="0 0 {W} {h+18}" width="100%" style="height:{h+18}px" '
            f'preserveAspectRatio="none">{"".join(out)}{ticks(h+13)}</svg>')


def mirrored():
    """ONE px-per-unit above and below. The previous version sized each half
    to its own maximum, so 17 nights and 17 days drew at different heights
    while the caption claimed a shared scale."""
    up, dn = D_MAX * K, N_MAX * K
    out = []
    for i, (y, d) in enumerate(DAYS):
        x, n = i * BW, nights.get(y, 0)
        c = "var(--accent)" if y == 2026 else "var(--ink)"
        if d:
            out.append(f'<rect x="{x:.1f}" y="{up-d*K:.1f}" width="{BW-1.2:.1f}" '
                       f'height="{d*K:.1f}" fill="{c}"/>')
        if n:
            out.append(f'<rect x="{x:.1f}" y="{up+1.4:.1f}" width="{BW-1.2:.1f}" '
                       f'height="{n*K:.1f}" fill="{c}" opacity="0.55"/>')
    return (f'<svg viewBox="0 0 {W} {up+dn+22}" width="100%" '
            f'style="height:{up+dn+22}px" preserveAspectRatio="none">{"".join(out)}'
            f'<line x1="0" y1="{up:.1f}" x2="{W}" y2="{up:.1f}" stroke="var(--ink)" '
            f'stroke-width="1.4"/>{ticks(up+dn+18)}</svg>')


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
tallest bar 2026, {DNOW}&nbsp;+&nbsp;{NNOW}&nbsp;=&nbsp;{DNOW+NNOW}</p>
<p class="cap">Reads as one rising quantity, which is the appeal. But the height is
days plus nights and those can be the same 24 hours: a day above {TH}&nbsp;&deg;C
followed by a night above 20&nbsp;&deg;C is counted twice. The tallest bar says
{DNOW+NNOW} of something, and there is no something.</p>

<div class="lab">Mirrored</div>
{mirrored()}
<p class="key"><b>above</b> hot days &nbsp; <b>below</b> hot nights &nbsp;
one scale, {K:.0f}px per count on both halves</p>
<p class="cap">Nothing is summed, and the same count draws the same size above and
below. What this shows and the stack hides:
<strong style="font-weight:500;color:var(--ink)">the two measures pick out the same two
summers.</strong> 1976 stands alone in the old record on days and nights both, and 2026
beats it on both: {DNOW} days against {PREV_D}, {NNOW} nights against {PREV_N}. Two
instruments agreeing on which summers mattered is harder to dismiss than either
alone.</p>
</main></body></html>"""
out = R / "design/review/stack-vs-mirror.html"
out.write_text(html)
print(f"wrote {out} | days max {D_MAX} prev {PREV_D} | nights max {N_MAX} prev {PREV_N}")
