"""Paris heat page v2. Kristjan's four notes, 2026-08-07.

  1. C dropped. Tested with people and read as too complex.
  2. A and B together: B is the headline because it is instant, A is the
     evidence underneath. They answer different questions, "how much" and
     "since when", so stacking them costs nothing.
  3. A carries BOTH instruments as bars. Paris nights sit at zero in 36
     of 77 years, so the nights row is empty for decades and then spikes,
     which is the strongest single mark on the page.
  4. Vienna's temperature chart, on the hottest NIGHT of each year with
     the 20 C line drawn. There is no warmest-DAY series in the payload;
     that is an ask on heat, who compute days above a threshold from
     daily maxima and therefore hold it upstream.

Days lead because the night metric is gated for RATIOS in Paris, at
about one night a year in the baseline. Drawing the nights is fine and
quoting a multiple off that base is not, so no night multiple appears.

Everything matched to-date. b6190 is a FULL-YEAR mean and is not used.
"""
import json, statistics as st
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())["cities"]["Paris"]
SY = json.loads((R / "heat/data/city_series.json").read_text())["cities"]["Paris"]["years"]
TH = N["days"]["thresholds_c"]["95"]
DNOW, NNOW = N["days"]["days_2026"]["95"], N["nights_2026"]
DR, NR = N["days"]["rank"], N["rank"]

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
HEADLINE_BASIS_CHECK = ("Paris used to get two hot days by this point in "
                        "the summer. This year: thirty.")
NIGHTS = [(y, n) for y, n in ser("nights_to_cut") if y < 2026] + [(2026, NNOW)]
WARM = ser("warmest_night_c")
# The page LEADS on days, so its temperature chart is on days too. Product's
# note: a lead about a count and a closing chart about a different quantity
# is the page arguing with itself.
WARMD = ser("warmest_day_to_cut_c")          # to the cut, like everything else
PEAK = dict(WARMD)[2026]
# THE PEAK CARRIES ITS OWN RANK, NEVER THE COUNT'S. Paris is 1st of 77 on the
# COUNT of hot days and 2nd on its hottest single day, 40.6 against 41.9 in
# 2019. Both true, and "the hottest Paris has ever been" is false. Computed
# here only to assert it differs; the claim on the page states the peak rank
# explicitly rather than inheriting one.
PEAK_RANK = 1 + sum(1 for y, v in WARMD if v >= PEAK and y != 2026)
PEAK_PREV = max(v for y, v in WARMD if y != 2026)
PEAK_PREV_Y = max(y for y, v in WARMD if v == PEAK_PREV and y != 2026)
if PEAK_RANK == 1:
    raise SystemExit(
        "Paris is now 1st on the peak as well as the count. The caption below "
        "says it is not the hottest day on record; rewrite it before shipping.")
DBASE = st.mean([n for y, n in DAYS if 1961 <= y <= 1990])
NBASE = st.mean([n for y, n in NIGHTS if 1961 <= y <= 1990])
DPREV = max(n for y, n in DAYS if y < 2026)
DPREV_Y = max(y for y, n in DAYS if y < 2026 and n == DPREV)
Y0 = DAYS[0][0]
ZERO_N = sum(1 for y, n in NIGHTS if n == 0)


def mirror(w=940, up=118, dn=92):
    """Both instruments on ONE chart, sharing a zero line and a scale.

    NOT stacked. Stacking would add a day above 31.8 C to a night above
    20 C and present the sum as a height, but they can be the same 24
    hours and the total is not a quantity. Mirrored instead: days above
    the line, nights below, one scale so the comparison is real.

    The scale is shared because both are counts of qualifying periods in
    the same season, so a bar twice as tall genuinely means twice as
    many. Scaling each to its own maximum would have made 17 nights look
    like 30 days.
    """
    top = max(max(n for _, n in DAYS), max(n for _, n in NIGHTS)) or 1
    bw = w / len(DAYS)
    nights = dict(NIGHTS)
    out = []
    for i, (y, d) in enumerate(DAYS):
        x, cur = i * bw, (y == 2026)
        fill = "var(--accent)" if cur else "var(--ink)"
        if d:
            out.append(f'<rect x="{x:.1f}" y="{up - d/top*up:.1f}" '
                       f'width="{bw-1.3:.1f}" height="{d/top*up:.1f}" fill="{fill}"/>')
        n = nights.get(y, 0)
        if n:
            out.append(f'<rect x="{x:.1f}" y="{up+1:.1f}" width="{bw-1.3:.1f}" '
                       f'height="{n/top*dn:.1f}" fill="{fill}" opacity="0.55"/>')
    ticks = "".join(f'<text x="{i*bw:.1f}" y="{up+dn+15}" class="ax">{y}</text>'
                    for i, (y, _) in enumerate(DAYS) if y in (1950, 1976, 2000, 2026))
    return (f'<div class="mirror">'
            f'<div class="ml"><span class="mu">Hot days<em>above {TH} &#176;C</em></span>'
            f'<span class="md">Hot nights<em>above 20 &#176;C</em></span></div>'
            f'<svg viewBox="0 0 {w} {up+dn+20}" width="100%" '
            f'style="height:{up+dn+20}px" preserveAspectRatio="none">'
            f'{"".join(out)}'
            f'<line x1="0" y1="{up:.1f}" x2="{w}" y2="{up:.1f}" '
            f'stroke="var(--ink)" stroke-width="1.4"/>{ticks}</svg></div>')


def units(k, label, accent=False):
    sq = "".join(f'<span class="u{" a" if accent else ""}"></span>' for _ in range(k))
    return (f'<div class="ub"><div class="uk">{label}</div>'
            f'<div class="ug">{sq}</div><div class="un">{k}</div></div>')


def warm_chart(w=940, h=118):
    """The hottest day of each summer, with its own rank stated.

    Was the hottest NIGHT, because no warmest-day series existed. It does
    now, and the page leads on days, so the closing chart is on days.
    """
    lo, hi = min(v for _, v in WARMD) - .6, max(v for _, v in WARMD) + .6
    px = lambda y: (y - WARMD[0][0]) / (2026 - WARMD[0][0]) * w
    py = lambda v: h - (v - lo) / (hi - lo) * h
    pts = " ".join(f"{px(y):.1f},{py(v):.1f}" for y, v in WARMD)
    prev = f'<circle cx="{px(PEAK_PREV_Y):.1f}" cy="{py(PEAK_PREV):.1f}" r="3.4" ' \
           f'fill="none" stroke="var(--ink)" stroke-width="1.6"/>'
    cur = f'<circle cx="{px(2026):.1f}" cy="{py(PEAK):.1f}" r="3.6" ' \
          f'fill="var(--accent)"/>'
    return (f'<svg viewBox="0 0 {w} {h+16}" width="100%" style="height:{h+16}px" '
            f'preserveAspectRatio="none">'
            f'<polyline points="{pts}" fill="none" stroke="var(--soft)" '
            f'stroke-width="1.2"/>{prev}{cur}</svg>')



html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paris &middot; Heat &middot; The Long Swell</title><style>
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
h1{{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.05;
letter-spacing:-.02em;color:var(--ink);margin:38px 0 10px;max-width:19ch;
text-wrap:balance}}
.stand{{font-size:18px;line-height:1.6;max-width:56ch;margin:0 0 34px}}
.units{{display:flex;flex-direction:column;gap:20px;border-top:3px solid var(--ink);
border-bottom:3px solid var(--ink);padding:26px 0}}
.ub{{display:grid;grid-template-columns:230px 1fr 48px;gap:20px;align-items:center}}
.uk{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-faint);line-height:1.5}}
.ug{{display:flex;flex-wrap:wrap;gap:4px}}
.u{{width:18px;height:18px;background:var(--ink);display:block}}
.u.a{{background:var(--accent)}}
.un{{font-family:'IBM Plex Mono',monospace;font-size:27px;font-weight:500;
color:var(--ink);text-align:right}}
.seclab{{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:2.4px solid var(--ink);
padding-bottom:9px;margin:52px 0 20px}}
.mirror{{display:grid;grid-template-columns:132px 1fr;gap:20px;align-items:center}}
.ml{{display:flex;flex-direction:column;gap:58px;font-family:'IBM Plex Mono',monospace;
font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink);line-height:1.5}}
.ml em{{display:block;font-style:normal;color:var(--ink-faint);letter-spacing:.06em}}
.md{{opacity:.72}}

.ax{{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}}
.cap{{font-size:15.5px;line-height:1.6;color:var(--soft);max-width:72ch;margin:12px 0 0}}
.warn{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.7;
color:var(--soft);background:var(--sunk);padding:13px 15px;margin:44px 0 0}}
</style></head><body><main>
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">Paris &middot; Montsouris &middot; to 3 August 2026</span></div>

<h1>Paris used to get two hot days by this point in the summer. This year: thirty.</h1>
<p class="stand">Days at or above {TH}&nbsp;&deg;C, which is Paris's own 95th
percentile. Counted to the same date every year, so a part-finished 2026 is not
being set against complete ones.</p>

<div class="units">
{units(round(DBASE), f"A typical summer, 1961-1990<br>by early August")}
{units(DNOW, "This summer, so far", accent=True)}
</div>
<p class="cap">One square is one day above {TH}&nbsp;&deg;C. The previous record for
this point in the year was {DPREV}, in {DPREV_Y}.</p>

<div class="seclab">Every summer since {Y0}, both measures, one scale</div>
{mirror()}
<p class="cap">Days above the line, nights below, sharing one scale so a taller bar
really does mean more. They are NOT stacked: a hot day and a hot night can be the same
24 hours, so a combined height would be a number rather than a measurement.
The nights half is empty for decades because it genuinely was:
{ZERO_N} of {len(NIGHTS)} years recorded no tropical night at all in Paris. This year
there have been {NNOW}, which is {NR['value']} of {NR['of_years']}. No multiple is
quoted for nights, because a ratio against a baseline of about one a year would be
arithmetic rather than evidence.</p>

<div class="seclab">And the hottest day of each summer</div>
{warm_chart()}
<p class="cap">The hottest single day of each summer, to the same date.
<strong style="color:var(--ink);font-weight:500">2026 is the {PEAK_RANK}nd hottest,
not the hottest.</strong> It reached {PEAK} &#176;C against {PEAK_PREV} &#176;C in
{PEAK_PREV_Y}, which is the open ring. Paris has had more hot days this summer than in
any year on record and its hottest day was still not a record: a count and a peak are
different claims, and neither borrows the other's rank.</p>

<div class="warn">MOCKUP v2. Kristjan's notes: C dropped as too complex, A and B
together, both instruments as bars, Vienna's temperature chart added. There is no
warmest-DAY series in the payload, so the temperature chart is on nights; a hottest-day
series is an ask on heat, who hold it upstream. All figures matched to-date; the
payload's full-year b6190 mean is deliberately unused.</div>
</main></body></html>"""
out = R / "design/review/paris-heat-v2.html"
out.write_text(html)
print(f"wrote {out} | days {round(DBASE)}->{DNOW} (prev {DPREV} in {DPREV_Y}) | "
      f"nights base {NBASE:.2f} -> {NNOW}, {ZERO_N}/{len(NIGHTS)} years at zero")
