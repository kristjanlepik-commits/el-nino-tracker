"""The Paris city page. One city, bars per year, the threshold drawn.

Product's reversal 2026-08-06: fifteen cities as a league table was the
wrong answer. The answer to "too thin" is depth, not breadth.

Two charts, because the payload supports two and they answer different
questions:

  nights per year      how OFTEN. Full-year bars with the to-date
                       portion solid inside, so the matched comparison
                       and the full history are the same mark and 2026
                       is visibly unfinished rather than captioned so.
  warmest night, C     how HOT. This is the chart the 20 C line belongs
                       on, because it is the only one whose y axis is a
                       temperature. On the counts chart the threshold is
                       the metric's definition and cannot be drawn.

Figures are MATCHED (to-date against to-date) wherever 2026 appears.
Product's brief quoted 0.4 / 2.5 / 3.6 against 17, which is three
full-year means against one partial season. 1945-74 is 0.41 on either
basis, so the fortyfold survives; the middle rungs do not.
"""
import json, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "heat/data/city_nights.json").read_text())
P = D["cities"]["Paris"]
FULL = {int(y): v for y, v in P["full_year_series"].items() if v is not None}
TD = {int(y): v for y, v in P["series_to_same_date"]["values"].items() if v is not None}
WARM = {int(y): v for y, v in P["warmest_night_c"].items() if v is not None}
CUT = P["series_to_same_date"]["cut_at"]
_MON = ["January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December"]
# cut_at arrives as "08-03". Rendering it raw gave "to 08 03 2026".
CUT_TXT = f"{int(CUT.split('-')[1])} {_MON[int(CUT.split('-')[0]) - 1]}"
NOW, YEAR = P["nights_2026"], 2026

if P["rank"]["requires_series"] and not TD:
    raise SystemExit("rank requires a series and none is present")


def mean(d, a, b):
    v = [x for y, x in d.items() if a <= y <= b]
    return st.mean(v) if v else None


M_OLD_TD, M_OLD_FULL = mean(TD, 1945, 1974), mean(FULL, 1945, 1974)
M_REF_TD, M_REF_FULL = mean(TD, 1991, 2020), mean(FULL, 1991, 2020)
W_OLD, W_REF = mean(WARM, 1945, 1974), mean(WARM, 1991, 2020)
FOLD = NOW / M_OLD_TD
DEC_50 = sum(v for y, v in FULL.items() if 1950 <= y < 1960)
DEC_60 = sum(v for y, v in FULL.items() if 1960 <= y < 1970)
if NOW <= DEC_50 + DEC_60:
    raise SystemExit(
        f"headline claims 2026 ({NOW}) beats the 1950s and 1960s combined "
        f"({DEC_50 + DEC_60}); it no longer does. Rewrite the headline.")

years = sorted(set(FULL) | {YEAR})
Y0, Y1 = min(years), YEAR
TOP = max(list(FULL.values()) + [NOW])


def bars(w=980, h=210):
    """Full-year bar in light ink, to-date portion solid inside it.

    One mark carrying both series. A reader sees the whole history at
    full-year scale AND the like-for-like comparison, and 2026 is a bar
    with no light portion because its season is not over. That is the
    incompleteness drawn rather than captioned.
    """
    bw = w / (Y1 - Y0 + 1)
    out = []
    for y in years:
        x = (y - Y0) * bw
        f = NOW if y == YEAR else FULL.get(y, 0)
        t = NOW if y == YEAR else TD.get(y, 0)
        if f:
            out.append(f'<rect x="{x:.1f}" y="{h - f/TOP*h:.1f}" width="{bw-1.1:.1f}" '
                       f'height="{f/TOP*h:.1f}" fill="var(--sunk-ink)"/>')
        if t:
            out.append(f'<rect x="{x:.1f}" y="{h - t/TOP*h:.1f}" width="{bw-1.1:.1f}" '
                       f'height="{t/TOP*h:.1f}" '
                       f'fill="{"var(--accent)" if y == YEAR else "var(--ink)"}"/>')
    ticks = "".join(
        f'<text x="{(y-Y0)*bw:.1f}" y="{h+13}" class="ax">{y}</text>'
        for y in (1930, 1950, 1970, 1990, 2010, 2026))
    grid = "".join(
        f'<line x1="0" y1="{h - v/TOP*h:.1f}" x2="{w}" y2="{h - v/TOP*h:.1f}" '
        f'stroke="var(--rule)" stroke-width="1"/>'
        f'<text x="{w-2}" y="{h - v/TOP*h - 3:.1f}" class="ax" text-anchor="end">{v}</text>'
        for v in (5, 10, 15))
    return (f'<svg viewBox="0 0 {w} {h+18}" width="100%" preserveAspectRatio="none" '
            f'style="height:{h+18}px">{grid}{"".join(out)}{ticks}</svg>')


def warm_chart(w=980, h=132):
    """Warmest night of each year, with the 20 C line drawn.

    The line is literal here: the y axis is degrees. Years below it are
    summers in which Paris never had a single tropical night at all.
    """
    ys = sorted(WARM)
    lo, hi = min(WARM.values()) - 0.5, max(WARM.values()) + 0.5
    px = lambda y: (y - ys[0]) / (Y1 - ys[0]) * w
    py = lambda v: h - (v - lo) / (hi - lo) * h
    pts = " ".join(f"{px(y):.1f},{py(WARM[y]):.1f}" for y in ys)
    below = "".join(
        f'<circle cx="{px(y):.1f}" cy="{py(WARM[y]):.1f}" r="1.7" fill="var(--ink-faint)"/>'
        for y in ys if WARM[y] < 20)
    return (f'<svg viewBox="0 0 {w} {h+16}" width="100%" preserveAspectRatio="none" '
            f'style="height:{h+16}px">'
            f'<line x1="0" y1="{py(20):.1f}" x2="{w}" y2="{py(20):.1f}" '
            f'stroke="var(--ink)" stroke-width="1.6" stroke-dasharray="5 3"/>'
            f'<text x="2" y="{py(20)-5:.1f}" class="ax" style="fill:var(--ink)">'
            f'20 &#176;C, the tropical-night line</text>'
            f'<polyline points="{pts}" fill="none" stroke="var(--soft)" stroke-width="1.2"/>'
            f'{below}</svg>')


strip = "".join(
    f'<div class="sr"><span class="sc">{n}</span>'
    f'<span class="sf">{v["nights_2026"]} nights · '
    f'{"record, +" + str(v["record_margin_nights"]) if v["record_margin_nights"] is not None else str(v["rank"]["value"]) + " of " + str(v["rank"]["of_years"])}'
    f'</span></div>'
    for n, v in sorted(D["cities"].items(),
                       key=lambda kv: (kv[1]["rank"]["value"],
                                       -(kv[1]["record_margin_nights"] or 0))))

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paris · Heat · The Long Swell</title><style>
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--sunk-ink:#D3D2CB;--ink:#1A1A18;
--soft:#3A3A36;--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--sunk-ink:#43423C;--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;
--rule:#3A3A36;--accent:#6E97E8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:1020px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;
font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}}
.facts{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--soft);margin:42px 0 12px}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:54px;line-height:1.04;
letter-spacing:-.02em;color:var(--ink);margin:0;max-width:17ch;text-wrap:balance}}
.ax{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}}
.figlab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;
text-transform:uppercase;color:var(--ink);margin:46px 0 10px;
border-bottom:2.4px solid var(--ink);padding-bottom:9px}}
.cap{{font-size:15.5px;line-height:1.6;max-width:74ch;margin:10px 0 0;color:var(--soft)}}
.ladder{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:30px 0 0;
border-top:2.4px solid var(--ink)}}
.lc{{padding:14px 16px 14px 0;border-right:1px solid var(--rule)}}
.lc:last-child{{border-right:0}}
.lv{{font-family:'IBM Plex Mono',monospace;font-size:34px;font-weight:500;
line-height:1;color:var(--ink)}}
.lk{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-faint);margin-top:7px;line-height:1.6}}
.sr{{display:grid;grid-template-columns:110px 1fr;gap:14px;padding:6px 0;
border-bottom:1px solid var(--rule);align-items:baseline}}
.sc{{font-size:15px;color:var(--ink)}}
.sf{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--soft)}}
.warn{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.7;
color:var(--soft);background:var(--sunk);padding:13px 15px;margin:40px 0 0}}
</style></head><body><main>
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">Paris · Montsouris · to {CUT_TXT} 2026</span></div>

<p class="facts">Nights that never fall below 20 &#176;C · one station ·
{Y0} to {YEAR}</p>
<h1>Paris has had more hot nights this year than in the whole of the 1950s and 1960s together.</h1>\n<p class="cap" style="font-size:17px;max-width:60ch">Seventeen so far, against {DEC_50} across the whole of the 1950s and {DEC_60} across the 1960s. The season is not over.</p>

<div class="ladder">
  <div class="lc"><div class="lv">{M_OLD_TD:.1f}</div><div class="lk">1945&ndash;74<br>average by {CUT_TXT}</div></div>
  <div class="lc"><div class="lv">{M_REF_TD:.1f}</div><div class="lk">1991&ndash;2020<br>average by {CUT_TXT}</div></div>
  <div class="lc"><div class="lv">{NOW}</div><div class="lk">2026<br>by {CUT_TXT}, season unfinished</div></div>
  <div class="lc"><div class="lv">{FOLD:.0f}&times;</div><div class="lk">2026 against<br>the 1945&ndash;74 average</div></div>
</div>
<p class="cap">Every figure above is counted to the same calendar day, so a
part-finished 2026 is not being set against complete years. On a whole-year
basis the 1991&ndash;2020 average was {M_REF_FULL:.1f} and 2026 is not yet
comparable, which is why the matched figure is the one shown.</p>

<div class="figlab">Nights above 20 &#176;C, every year since {Y0}</div>
{bars()}
<p class="cap">Solid is the count to {CUT_TXT}; the lighter block above it is
the rest of that year. 2026 has no lighter block because the season is not over,
so what the chart cannot yet know is drawn as absent rather than assumed.</p>

<div class="figlab">And the nights themselves got hotter</div>
{warm_chart()}
<p class="cap">The warmest single night of each year. Dots mark the years that never
crossed the line at all: through the 1950s that was most of them. The average
warmest night has moved from {W_OLD:.1f} &#176;C in 1945&ndash;74 to {W_REF:.1f} &#176;C
in 1991&ndash;2020.</p>

<div class="figlab">Is this only Paris</div>
{strip}
<p class="cap">{D['headline']['lead']['claim']} {D['headline']['records']} of
{D['headline']['of_cities']} have beaten their own record outright, against a typical
year of {D['headline']['baseline']['typical_year_records']}.
{D['headline']['may_not_say']}</p>

<div class="warn">MOCKUP. Every figure read from heat/data/city_nights.json.
Product's brief quoted 0.4 / 2.5 / 3.6 against 17, which mixes three whole-year
means with one part-season. The matched values are
{M_OLD_TD:.2f} / {M_REF_TD:.2f} / {mean(TD,2011,2025):.2f}. The fortyfold survives
because 1945-74 is {M_OLD_TD:.2f} on either basis.</div>
</main></body></html>"""
out = ROOT / "design/review/paris-heat.html"
out.write_text(html)
print(f"wrote {out} ({len(FULL)} years, 2026={NOW}, fold={FOLD:.1f}x)")
