"""City page brief for VD's canvas. Questions, not a solution."""
import json, html
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())
C, e = N["cities"], html.escape
MONO = "'IBM Plex Mono', monospace"
P = C["Paris"]
NO_MULT = N["cities_without_day_multiple"]
# Cities where the night metric breaks: a 1991-2020 to-date mean near zero
# makes a ratio arithmetic rather than evidence. Read from city_sd.json,
# which now carries the mean.
SD = json.loads((R / "heat/data/city_sd.json").read_text())["cities"]
gated = sorted(n for n, d in SD.items() if d["mean"] < 2)


def lab(t):
    return (f'<div style="font-family:{MONO};font-size:9.5px;letter-spacing:.22em;'
            f'text-transform:uppercase;color:#1A1A18;border-bottom:3px solid #1A1A18;'
            f'padding-bottom:10px;margin:46px 0 18px">{t}</div>')


def q(n, title, body):
    return (f'<div style="border-top:1px solid #C6C5C2;padding:18px 0;display:grid;'
            f'grid-template-columns:38px minmax(0,1fr);gap:20px;align-items:start">'
            f'<div style="font-family:{MONO};font-size:20px;color:#1A1A18">{n}</div>'
            f'<div><div style="font-size:19px;line-height:1.35;color:#1A1A18;'
            f'max-width:44ch;margin-bottom:8px">{title}</div>'
            f'<div style="font-size:16px;line-height:1.58;color:#3A3A36;'
            f'max-width:70ch">{body}</div></div></div>')


doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="./support.js"></script></head><body><x-dc><helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Spectral:wght@400;500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#F1F0EC}}</style></helmet>
<div style="max-width:1080px;margin:0 auto;padding:0 48px 90px;color:#3A3A36;
font-family:Spectral,serif">

<div style="padding:22px 0 12px;border-bottom:3px solid #1A1A18;display:flex;
align-items:baseline;gap:14px">
<span style="font-weight:500;font-size:22px;color:#1A1A18">The Long Swell</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.18em;
text-transform:uppercase;color:#1A1A18">Heat city page &middot; open questions</span>
<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:#6E6E67;margin-left:auto">From design</span></div>

<h1 style="font-weight:400;font-size:44px;line-height:1.08;letter-spacing:-.018em;
color:#1A1A18;margin:40px 0 14px;max-width:24ch">The city page is the promotion
surface, not a leaf</h1>
<p style="font-size:17.5px;line-height:1.62;max-width:66ch;margin:0">
Kristjan's framing: <em>"I could link the city pages in the promotions and people would
come to the site, because they care how their city is doing."</em> So each one is a
landing page. That changes the requirements: a URL that reads well, and a per-page
preview card, because these are the things that get shared. Worth building in rather
than retrofitting.</p>
<p style="font-size:17.5px;line-height:1.62;max-width:66ch;margin:14px 0 0">
The angle for the whole channel is a reader's question rather than our finding:
<strong style="font-weight:500;color:#1A1A18">how hot has the European summer
been?</strong> People have heard it seems hot and not how hot.</p>

{lab('What we have built, and why it is not the answer')}
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0 0 14px">
Design has a working Paris page. <strong style="font-weight:500;color:#1A1A18">It is one
candidate, not a proposal.</strong> Three heat layouts were rejected before it, all of
which led with the instrument rather than with what a reader wants to know, so our
judgement about legibility is the thing least worth trusting here.</p>
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0">
Its lead is a count comparison rather than a rank, which is the one thing that has
worked: <strong style="font-weight:500;color:#1A1A18">Paris used to get two hot days by
this point in the summer. This year: thirty.</strong> Two squares against thirty, in
about half a second, with nothing to read. Everything else on the page is apparatus
underneath it.</p>

{lab('Open questions, in the order they block things')}
{q(1, "Stacked or mirrored, and it needs readers rather than us.",
   "Nights and days on one chart. STACKED reads as one rising quantity and is more "
   "immediate, but the height is days plus nights and those can be the same 24 hours, "
   "so the tallest bar claims a total that is not a quantity. MIRRORED shares a zero "
   "line and one scale, sums nothing, and is the only version where you can see that "
   "1976 and 2026 are the two standout summers on BOTH measures. We have built both "
   "and cannot pick between them by looking.")}
{q(2, "Kristjan wants 2 to 3 alternatives to test with people, not a converged answer.",
   "Genuinely different approaches rather than three treatments of one idea. Ours so "
   "far: count over time, the Vienna construction; then-against-now as unit squares "
   "with no axis at all; and every year as one mark on a single axis so the tail is "
   "seen directly. A fourth we cannot build yet is a season calendar, which needs "
   "daily values that heat holds upstream but does not emit.")}
{q(3, "The page leads on DAYS and its closing temperature chart is on NIGHTS.",
   "The one structural weakness left. There is no warmest-DAY series in the payload, "
   "only warmest night, so the final chart is about a different thing from the lead. "
   "Heat has been asked for it. Worth knowing before you lay out the bottom of the "
   "page, because the strongest version has them matching.")}
{q(4, "The template must survive cities where an instrument is missing.",
   f"Days work in all 21 cities. Nights do NOT: the metric breaks where tropical "
   f"nights are rare, which gates out {' and '.join(gated)} at about one a year. And "
   f"{', '.join(NO_MULT)} publish a count with no multiple at all, because their "
   f"baseline is part-length. So a layout that needs both instruments breaks in two "
   f"cities, and one that needs a multiple in a fixed slot breaks in three. Optional "
   f"blocks rather than one fixed grid.")}
{q(5, "How does a reader see abnormality when there are two readings?",
   "Kristjan's question. One abnormal and one not is a weaker statement; both abnormal "
   "is stronger. Note what the data actually says: the two instruments AGREE almost "
   "everywhere. Seven of fifteen cities are at an outright record on both, seven have "
   "identical percentiles, and none is extreme on one and ordinary on the other. So "
   "the grammar has to make agreement visible and carry weight, while still showing "
   "Marseille, where the days run 7.8 percentile points ahead of the nights.")}
{q(6, "The word ORDINARY is banned from this page.",
   "Everywhere in the set is elevated. Seville sits at the 89th percentile, Hamburg at "
   "the 89th, Berlin at the 86th. None of those is ordinary; the EXTREME is "
   "concentrated in the middle latitudes. Any visual grammar that renders the quieter "
   "cities as a null state will assert something false.")}

{lab('Two things that are working and should survive a redesign')}
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0 0 12px">
<strong style="font-weight:500;color:#1A1A18">An absence stated as a finding.</strong>
The nights half of the Paris chart is empty for decades because it genuinely was:
36 of 77 years recorded no tropical night at all. That is the working shown rather
than a gap apologised for.</p>
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0">
<strong style="font-weight:500;color:#1A1A18">A refused number, explained.</strong>
No multiple is quoted for Paris nights, because a ratio against a baseline of about
one a year would be arithmetic rather than evidence. The gate is applied and stated in
language a reader understands.</p>

{lab('One thing we got wrong today, because it will bite you too')}
<p style="font-size:16.5px;line-height:1.6;max-width:70ch;margin:0">
Every figure on this page is counted TO THE SAME DATE each year, so a part-finished
2026 is never set against complete seasons. The headline briefly read "two hot days a
summer", which is a to-date figure phrased as a whole-season total, and it overstated
the change in the direction that flatters us. There is no full-year day series in the
payload, so we cannot even say by how much. It is now a build failure rather than a
habit. <strong style="font-weight:500;color:#1A1A18">If a sentence quotes a baseline,
it has to carry the basis.</strong></p>

</div></x-dc></body></html>"""
out = R / "design/review/citypage-brief.dc.html"
out.write_text(doc)
print(f"wrote {out} | gated on nights: {gated} | no multiple: {NO_MULT}")
