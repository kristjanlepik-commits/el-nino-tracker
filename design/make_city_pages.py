"""All 21 heat city pages from one template.

Every page is a landing page: Kristjan's framing is that these get linked
in promotion and a reader arrives caring about their own city. So the
URL and the claim have to stand alone.

THE BRANCHES, enumerated from the payload rather than discovered on city
four. Eight cities need no special case; the other thirteen need one of:

  night-gated (7)      Hamburg, Cologne, Munich, Bilbao, Frankfurt,
                       Berlin, Paris. Under two hot nights a year, so no
                       ratio, multiple or record may be quoted on nights.
                       Read from the payload flag, never inferred.
  no day multiple (3)  Lyon, Murcia, Palma. Station opened after 1961 so
                       the baseline is part-length and drawn from the
                       warmer end. The field is ABSENT rather than
                       flagged, so it cannot be rendered by accident.
  peak IS a record (7) Barcelona, Berlin, Bilbao, Frankfurt, Marseille,
                       Munich, Vienna. For these the hottest day of 2026
                       IS the hottest on record, so the Paris sentence
                       "its hottest day was still not a record" is FALSE
                       and must not be templated.

A COUNT AND A PEAK ARE DIFFERENT CLAIMS AND NEITHER BORROWS THE OTHER'S
RANK. Paris is 1st of 77 on the count of hot days and 2nd on its hottest
single day. Both true; "the hottest Paris has ever been" is false.

Every figure is counted TO THE SAME CALENDAR DAY each year, so a
part-finished 2026 is never set against complete seasons. The payload's
b6190 is a WHOLE-YEAR mean and is deliberately unused: pairing it with a
part-season count understates the change and misdescribes the basis.
"""
import json, math, statistics as st
from pathlib import Path

R = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(R))
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       site_masthead)
N = json.loads((R / "heat/data/city_nights.json").read_text())
S = json.loads((R / "heat/data/city_series.json").read_text())["cities"]
C = N["cities"]
NO_MULT = set(N["cities_without_day_multiple"])
MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]
slug = lambda n: n.lower().replace(" ", "-")


def series(yrs, key, sub=None):
    out = []
    for y, x in sorted(yrs.items(), key=lambda kv: int(kv[0])):
        if not x.get("usable_to_cut"):
            continue
        raw = x.get(key)
        v = raw.get(sub) if (sub and isinstance(raw, dict)) else raw
        if v is not None:
            out.append((int(y), v))
    return out


def bars(data, top, w=880, h=104, accent_last=True):
    if not data:
        return ""
    bw = w / len(data)
    out = []
    for i, (y, v) in enumerate(data):
        if not v:
            continue
        cur = accent_last and y == 2026
        out.append(f'<rect x="{i*bw:.1f}" y="{h-v/top*h:.1f}" width="{bw-1.2:.1f}" '
                   f'height="{v/top*h:.1f}" '
                   f'fill="{"var(--accent)" if cur else "var(--ink)"}"/>')
    ticks = "".join(
        f'<text x="{i*bw:.1f}" y="{h+13}" class="ax" '
        f'text-anchor="{"end" if y == 2026 else "start"}">{y}</text>'
        for i, (y, _) in enumerate(data)
        if y in (data[0][0], 1976, 2000, 2026))
    return (f'<svg viewBox="0 0 {w} {h+18}" width="100%" style="height:{h+18}px" '
            f'preserveAspectRatio="none">{"".join(out)}{ticks}</svg>')


def line(data, w=880, h=104, mark_year=None, ring_year=None):
    lo = min(v for _, v in data) - .5
    hi = max(v for _, v in data) + .5
    px = lambda y: (y - data[0][0]) / (data[-1][0] - data[0][0]) * w
    py = lambda v: h - (v - lo) / (hi - lo) * h
    pts = " ".join(f"{px(y):.1f},{py(v):.1f}" for y, v in data)
    extra = ""
    d = dict(data)
    if ring_year and ring_year in d:
        extra += (f'<circle cx="{px(ring_year):.1f}" cy="{py(d[ring_year]):.1f}" '
                  f'r="3.4" fill="none" stroke="var(--ink)" stroke-width="1.6"/>')
    if mark_year and mark_year in d:
        extra += (f'<circle cx="{px(mark_year):.1f}" cy="{py(d[mark_year]):.1f}" '
                  f'r="3.6" fill="var(--accent)"/>')
    return (f'<svg viewBox="0 0 {w} {h+6}" width="100%" style="height:{h+6}px" '
            f'preserveAspectRatio="none"><polyline points="{pts}" fill="none" '
            f'stroke="var(--soft)" stroke-width="1.2"/>{extra}</svg>')


def units(k, accent=False):
    cls = "u ua" if accent else "u"
    return "".join(f'<span class="{cls}"></span>' for _ in range(int(round(k))))


CSS = """
:root{--paper:#F1F0EC;--sunk:#E7E6DF;--ink:#1A1A18;--soft:#3A3A36;
--ink-faint:#6E6E67;--rule:#CFCEC7;--accent:#173F9E}
@media(prefers-color-scheme:dark){:root{--paper:#1A1A18;--sunk:#252521;
--ink:#EDECE6;--soft:#B4B3AB;--ink-faint:#86857D;--rule:#3A3A36;--accent:#6E97E8}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--soft);
font-family:Spectral,Georgia,serif;font-size:17px;line-height:1.55}
main{max-width:940px;margin:0 auto;padding:0 24px 90px}
.mast{display:flex;align-items:baseline;gap:13px;padding:20px 0 11px;
border-bottom:3px solid var(--ink)}
.house{font-size:21px;font-weight:500;color:var(--ink)}
.prod{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink)}
.when{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint)}
h1{font-family:Spectral,serif;font-weight:400;font-size:50px;line-height:1.05;
letter-spacing:-.02em;color:var(--ink);margin:40px 0 16px;max-width:19ch;text-wrap:balance}
.stand{font-size:17.5px;line-height:1.62;max-width:62ch;margin:0}
.rows{display:flex;flex-direction:column;gap:22px;margin:34px 0 0}
.urow{display:grid;grid-template-columns:196px 1fr 54px;gap:20px;align-items:center}
.uk{font-family:'IBM Plex Mono',monospace;font-size:11px;line-height:1.55;
color:var(--ink-faint);text-align:right}
.ug{display:flex;flex-wrap:wrap;gap:4px}
.u{width:19px;height:19px;background:var(--ink);display:block}
.ua{background:var(--accent)}
.un{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:500;
color:var(--ink);text-align:right}
.seclab{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.22em;
text-transform:uppercase;color:var(--ink);border-bottom:3px solid var(--ink);
padding-bottom:10px;margin:52px 0 14px}
.cap{font-size:15.5px;line-height:1.6;max-width:72ch;margin:12px 0 0}
.ax{font-family:'IBM Plex Mono',monospace;font-size:9px;fill:var(--ink-faint)}
.grid{display:grid;grid-template-columns:136px minmax(0,1fr);gap:20px;align-items:end;
margin-top:16px}
.gk{font-family:'IBM Plex Mono',monospace;font-size:10.5px;line-height:1.5;
letter-spacing:.06em;text-transform:uppercase;color:var(--ink);padding-bottom:8px}
.gk em{display:block;font-style:normal;color:var(--ink-faint);letter-spacing:.03em}
.src{font-family:'IBM Plex Mono',monospace;font-size:12px;line-height:1.9;
color:var(--soft);display:grid;grid-template-columns:1fr auto;column-gap:30px;
margin-top:48px}
.src span{border-top:1px solid var(--rule);padding-top:9px}
.src span:nth-child(-n+2){border-top:2.4px solid #8E8E88}
.back{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-faint);text-decoration:none;
border-bottom:1px solid var(--rule)}
"""

built, notes = [], []
for name, v in sorted(C.items()):
    yrs = S[name]["years"]
    D = series(yrs, "days_to_cut", "95")
    NI = series(yrs, "nights_to_cut")
    WD = series(yrs, "warmest_day_to_cut_c")
    th = v["days"]["thresholds_c"]["95"]
    now = v["days"]["days_2026"]["95"]
    base = st.mean([x for y, x in D if 1961 <= y <= 1990])
    nbase = st.mean([x for y, x in NI if 1961 <= y <= 1990]) if NI else 0
    gated = bool(v.get("nights_metric_gated"))
    peak = dict(WD).get(2026)
    prank = 1 + sum(1 for y, x in WD if x >= peak and y != 2026)
    pprev = max(x for y, x in WD if y != 2026)
    pprev_y = max(y for y, x in WD if x == pprev and y != 2026)
    cut = S[name]["cut_at"]
    cut_txt = f"{int(cut.split('-')[1])} {MON[int(cut.split('-')[0]) - 1]}"
    dr = v["days"]["rank"]

    # The headline must name its period: base is a TO-DATE mean and reading
    # it as a season total overstates the change.
    head = (f"{name} used to get {base:.0f} hot day{'s' if round(base)!=1 else ''} "
            f"by this point in the summer. This year: {now}.")

    # THE PEAK CARRIES ITS OWN RANK. Seven cities have peak == record, so
    # the sentence branches rather than being templated.
    if prank == 1:
        peak_cap = (f"The hottest day of {name}'s year, to the same date. "
                    f"<strong>2026 is the hottest on this record too</strong>, at "
                    f"{peak}&nbsp;&deg;C. Both the count and the peak are records "
                    f"here, which is not true everywhere: a count and a peak are "
                    f"separate claims and each carries its own rank.")
    else:
        ordn = {2: "2nd", 3: "3rd"}.get(prank, f"{prank}th")
        peak_cap = (f"The hottest day of {name}'s year, to the same date. "
                    f"<strong>2026 is the {ordn} hottest, not the hottest</strong>, "
                    f"at {peak}&nbsp;&deg;C against {pprev}&nbsp;&deg;C in {pprev_y}, "
                    f"the open ring. More hot days than any year on record and its "
                    f"hottest day still short of one: a count and a peak are "
                    f"different claims, and neither borrows the other's rank.")

    if gated:
        night_block = (
            f'<div class="seclab">And the nights</div>'
            f'{bars(NI, max(x for _, x in NI) or 1)}'
            f'<p class="cap">{v["nights_2026"]} nights so far that never dropped below '
            f'20&nbsp;&deg;C. <strong>No multiple is quoted here.</strong> {name} '
            f'averages about {nbase:.1f} a year, and dividing by a base that thin '
            f'produces a large number and no evidence, so the count is published and '
            f'the ratio is withheld. '
            f'{sum(1 for c in C.values() if c.get("nights_metric_gated"))} of the '
            f'{len(C)} cities are gated this way.</p>')
    else:
        nrank = v["rank"]
        night_block = (
            f'<div class="seclab">And the nights</div>'
            f'{bars(NI, max(x for _, x in NI) or 1)}'
            f'<p class="cap">{v["nights_2026"]} nights so far at or above '
            f'20&nbsp;&deg;C, against {nbase:.1f} in a typical 1961-1990 summer by '
            f'this date. That is {nrank["value"]} of {nrank["of_years"]} on this '
            f'station\'s record.</p>')

    mult_note = ("" if name not in NO_MULT else
                 f'<p class="cap"><strong>No multiple is published for '
                 f'{name}\'s days.</strong> The station opened after 1961, so its '
                 f'1961-1990 baseline is part-length and drawn from the warmer end of '
                 f'the period. The count and the rank stand; the ratio is not emitted '
                 f'at all rather than emitted with a warning.</p>')

    top = max(max(x for _, x in D), 1)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} &middot; Heat &middot; The Long Swell</title>
<meta name="description" content="{head}">
{ANALYTICS_SNIPPET}
<style>{SITE_MASTHEAD_CSS}{CSS}</style></head><body><main>
{site_masthead("../", active="heat")}
<div class="mast"><span class="house">The Long Swell</span>
<span class="prod">Heat</span>
<span class="when">{name} &middot; {S[name]['station']} &middot; to {cut_txt} 2026</span></div>

<h1>{head}</h1>
<p class="stand">A hot day here means one at or above {th}&nbsp;&deg;C, which is this
station's own 95th percentile for July and August between 1971 and 2000. The bar for
what counts as hot has not moved; the number of days clearing it has.
Both figures below are counted to {cut_txt}, in 2026 and in every earlier year, so a
part-finished summer is never set against complete ones.</p>

<div class="rows">
  <div class="urow"><span class="uk">By this date in a typical<br>summer of 1961-1990</span>
    <span class="ug">{units(base)}</span><span class="un">{base:.1f}</span></div>
  <div class="urow"><span class="uk">By this date<br>this summer</span>
    <span class="ug">{units(now, True)}</span><span class="un">{now}</span></div>
</div>

<div class="seclab">Every summer on this thermometer</div>
<div class="grid"><span class="gk">Hot days<em>above {th} &deg;C</em></span>
<span>{bars(D, top)}</span></div>
<p class="cap">2026 is {"the most on record" if dr["value"] == 1 else
f'{dr["value"]}th of {dr["of_years"]}'} for hot days.</p>
{mult_note}

{night_block}

<div class="seclab">And the hottest day of each summer</div>
{line(WD, mark_year=2026, ring_year=None if prank == 1 else pprev_y)}
<p class="cap">{peak_cap}</p>

<div class="src">
<span>{S[name]['source']}, {S[name]['station']}, daily minimum and maximum</span>
<span style="text-align:right">to {v['counted_to']}</span>
<span>Hot days, this station's own 95th percentile of July-August maxima, 1971 to 2000</span>
<span style="text-align:right">{th} &deg;C</span>
<span>Hot nights, ETCCDI index TR, at or above 20.0 &deg;C</span>
<span style="text-align:right">not chosen by us</span>
</div>
<p style="margin-top:26px"><a class="back" href="index.html">All 21 cities</a></p>
</main></body></html>"""
    out = R / f"docs/heat/{slug(name)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    built.append(name)
    if gated:
        notes.append(f"{name}: night-gated")
    if name in NO_MULT:
        notes.append(f"{name}: no day multiple")
    if prank == 1:
        notes.append(f"{name}: peak is also a record")

print(f"built {len(built)} city pages")
for n in notes:
    print("  ", n)
