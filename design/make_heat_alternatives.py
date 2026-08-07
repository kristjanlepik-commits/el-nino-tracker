"""Three genuinely different ways to answer "how hot has it been", one city.

For reader testing, not for converging internally. Three rejected layouts
have shown our judgement about legibility is not reliable, so this stops
arguing and puts alternatives in front of people.

Paris, on DAYS above its own 95th percentile. Days rather than nights
because the night metric is gated out in Paris and Bilbao, so anything
built on nights breaks in the two cities most worth promoting.

Product proposed a season calendar as option 2. It is NOT BUILDABLE FROM
THE CURRENT PAYLOAD, which carries annual counts only: no committed heat
file has a daily series. But the upstream data IS daily, since counting
days above a threshold is a per-day operation, so this is an ASK on heat
to emit what they already compute rather than an impossibility. Worth
making, because density in a season is a different question from height
over years and a reader may well find it the more obvious one.

Substituted a unit chart here, which answers the same "count rather than
height" question from data we have today.

Every figure matched to-date against to-date. counts_per_year.b6190 is a
FULL-YEAR mean (2.6) and 2026 is a part-season (30); pairing them would
have understated the change at 12x where the matched pair gives 17x.
"""
import json, statistics as st
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())["cities"]["Paris"]
SY = json.loads((R / "heat/data/city_series.json").read_text())["cities"]["Paris"]["years"]
D, TH = N["days"], N["days"]["thresholds_c"]["95"]
NOW, RANK = D["days_2026"]["95"], D["rank"]

series = sorted((int(y), v["days_to_cut"]["95"]) for y, v in SY.items()
                if v.get("usable_to_cut") and v.get("days_to_cut"))
series = [(y, n) for y, n in series if y < 2026] + [(2026, NOW)]
BASE = st.mean([n for y, n in series if 1961 <= y <= 1990])
PREV = max(n for y, n in series if y < 2026)
PREV_Y = max(y for y, n in series if y < 2026 and n == PREV)
Y0, TOP = series[0][0], max(n for _, n in series)


def opt_a(w=940, h=200):
    """Count over time. The Vienna construction: the change is the shape."""
    bw = w / len(series)
    bars = "".join(
        f'<rect x="{i*bw:.1f}" y="{h - n/TOP*h:.1f}" width="{bw-1.4:.1f}" '
        f'height="{max(n/TOP*h,0.8):.1f}" fill="{"var(--accent)" if y==2026 else "var(--ink)"}"/>'
        for i, (y, n) in enumerate(series))
    base_y = h - BASE / TOP * h
    ticks = "".join(f'<text x="{(y-Y0)/len(series)*w*0+i*bw:.1f}" y="{h+13}" class="ax">{y}</text>'
                    for i, (y, n) in enumerate(series) if y in (1950, 1976, 2000, 2026))
    return (f'<svg viewBox="0 0 {w} {h+18}" width="100%" style="height:{h+18}px" '
            f'preserveAspectRatio="none">'
            f'<line x1="0" y1="{base_y:.1f}" x2="{w}" y2="{base_y:.1f}" '
            f'stroke="var(--ink-faint)" stroke-width="1" stroke-dasharray="4 3"/>'
            f'{bars}{ticks}</svg>')


def opt_b():
    """Then against now, as units. One square is one day. No axis at all,
    nothing to read, and the comparison is a count rather than a height."""
    def blk(k, label):
        sq = "".join('<span class="u"></span>' for _ in range(k))
        return (f'<div class="ub"><div class="uk">{label}</div>'
                f'<div class="ug">{sq}</div><div class="un">{k}</div></div>')
    return ('<div class="units">' + blk(round(BASE), "A typical summer, 1961-1990")
            + blk(NOW, "This summer, so far") + '</div>')


def opt_c(w=940, h=112):
    """Every year as one mark on a single axis. The reader sees the tail
    directly rather than inferring it from a trend."""
    px = lambda n: 26 + n / TOP * (w - 52)
    def dot(i, y, n):
        fill = "var(--accent)" if y == 2026 else "var(--ink)"
        op = "" if y == 2026 else ' opacity="0.32"'
        return (f'<circle cx="{px(n):.1f}" cy="{h/2 + ((i*13)%5-2)*4:.1f}" '
                f'r="3.1" fill="{fill}"{op}/>')
    dots = "".join(dot(i, y, n) for i, (y, n) in enumerate(series))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="height:{h}px" '
            f'preserveAspectRatio="none">'
            f'<line x1="26" y1="{h-16}" x2="{w-26}" y2="{h-16}" stroke="var(--rule)"/>'
            f'{dots}'
            f'<text x="{px(0):.1f}" y="{h-3}" class="ax">0 days</text>'
            f'<text x="{px(PREV):.1f}" y="{h-3}" class="ax" text-anchor="middle">{PREV}</text>'
            f'<text x="{px(NOW):.1f}" y="{h-3}" class="ax" text-anchor="end">{NOW}</text>'
            f'</svg>')


html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heat: three ways to show it &middot; The Long Swell</title><style>
:root{{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}}
@media(prefers-color-scheme:dark){{:root{{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}}
main{{max-width:1000px;margin:0 auto;padding:0 24px 90px}}
.mast{{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}}
.house{{font-size:21px;font-weight:500;color:var(--ink)}}
.prod{{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}}
.when{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}}
h1{{font-family:Spectral,serif;font-weight:400;font-size:44px;line-height:1.08;
letter-spacing:-.018em;color:var(--ink);margin:38px 0 12px;max-width:22ch}}
.stand{{font-size:17.5px;line-height:1.6;max-width:66ch;margin:0}}
.opt{{margin:54px 0 0;padding-top:16px;border-top:3px solid var(--ink)}}
.ol{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);margin-bottom:6px}}
.oq{{font-size:23px;line-height:1.3;color:var(--ink);max-width:40ch;margin:0 0 4px}}
.oh{{font-size:15px;line-height:1.55;color:var(--ink-faint);max-width:62ch;margin:0 0 22px}}
.ax{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}}
.cap{{font-size:15px;line-height:1.55;color:var(--soft);max-width:70ch;margin:14px 0 0}}
.units{{display:flex;flex-direction:column;gap:26px}}
.ub{{display:grid;grid-template-columns:210px 1fr 46px;gap:20px;align-items:center}}
.uk{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-faint);line-height:1.5}}
.ug{{display:flex;flex-wrap:wrap;gap:4px}}
.u{{width:17px;height:17px;background:var(--ink);display:block}}
.ub:last-child .u{{background:var(--accent)}}
.un{{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:500;
color:var(--ink);text-align:right}}
.warn{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.7;
color:var(--soft);background:var(--sunk);padding:13px 15px;margin:48px 0 0}}
</style></head><body><main>
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span><span class="when">Three alternatives &middot; for reader testing</span></div>

<h1>How hot has the European summer been?</h1>
<p class="stand">Same city, same number, three ways of showing it. Paris, days at or
above {TH}&nbsp;&deg;C, which is its own 95th percentile of July-August maxima.
{NOW} so far this year against {BASE:.1f} in a typical year of 1961-1990, and a
previous record of {PREV} in {PREV_Y}. Rank {RANK['value']} of {RANK['of_years']}.
<strong style="color:var(--ink);font-weight:500">Pick the one a reader gets fastest,
not the one we find most complete.</strong></p>

<div class="opt"><div class="ol">Option A &middot; count over time</div>
<p class="oq">Every summer since {Y0}, and this one.</p>
<p class="oh">The Vienna construction. The change IS the shape, so no sentence is
needed. Dashed line is the 1961-1990 average.</p>
{opt_a()}
<p class="cap">Strongest at showing that this is a trend rather than one odd year.
Weakest on a phone, where 77 bars is a smear.</p></div>

<div class="opt"><div class="ol">Option B &middot; then against now</div>
<p class="oq">One square is one day above {TH}&nbsp;&deg;C.</p>
<p class="oh">No axis, no scale, nothing to read. The comparison is a count you can
see at a glance and check by counting.</p>
{opt_b()}
<p class="cap">Strongest on a phone and for a reader who does not read charts. Loses
the history entirely: it cannot show that 1976 came close.</p></div>

<div class="opt"><div class="ol">Option C &middot; where this year sits</div>
<p class="oq">Every year on one axis. This one is the mark on the right.</p>
<p class="oh">The reader sees the tail directly rather than inferring it. Answers
"is this unusual" rather than "is this rising".</p>
{opt_c()}
<p class="cap">Strongest at showing how far outside normal this is, and it is the
only one that makes the gap to {PREV_Y} visible as distance. Weakest at showing when
the change happened.</p></div>

<div class="warn">FOR TESTING. Paris, days above its own 95th percentile, matched
to-date against to-date. The payload's b6190 of {D['counts_per_year']['95']['b6190']}
is a FULL-YEAR mean and is deliberately not used here: pairing it with a part-season
2026 would give 12x where the matched pair gives {NOW/BASE:.0f}x.
Product's season-calendar option is not buildable from TODAY'S payload, which has
annual counts only. The upstream data is daily, so it is an ask on heat rather than
an impossibility, and worth making: density within a season is a different question
from height across years.</div>
</main></body></html>"""
out = R / "design/review/heat-alternatives.html"
out.write_text(html)
print(f"wrote {out} | Paris {NOW} vs {BASE:.1f} base, prev {PREV} ({PREV_Y}), "
      f"{len(series)} years, {NOW/BASE:.0f}x matched")
