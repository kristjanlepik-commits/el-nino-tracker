"""Two fast-reaction mockups for Kristjan, built to surface decisions.

His ask, via product: to be involved early on UX rather than reacting to a
shipped page. So where a choice is open this shows BOTH options side by
side rather than quietly picking one, and says which way I lean and why.

PROVENANCE DIFFERS BETWEEN THE TWO AND THE PAGE SAYS SO LOUDLY.

Piece 1 is ours: every number comes from
floods/data/payload_catalonia_pyrenees_2026-08-18.json, validated, verdict
measured, no guards fired.

Piece 2 is NOT ours. The Lima figures come from the station's own
bulletins and GHCN, via heat. Nothing in this repo contains station 84628,
Jorge Chavez or Lima: our 45 heat cities are all European, and Lima is 0
of 30 on both WMO baselines so our percentile instrument cannot be built
there at all. Product misrepresented these to Kristjan once today as a
finding in the repo and he caught it. A mockup that does not carry its own
provenance becomes believed within a week, so this one carries it in the
piece rather than in a footnote.

THE CHARTS ARE HONEST ABOUT WHAT WE HOLD. Neither piece has a full annual
series in hand. The flood payload has value, median and rank but no
per-year accumulations, and the Lima figures are a top-five list rather
than a record. So the flood chart is drawn as the frame it will be, marked
empty, and the Lima chart draws exactly the six points that exist and says
so. Drawing plausible bars would make the mockup the most convincing
untrue thing on the site.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAY = json.loads((ROOT / "floods/data/payload_catalonia_pyrenees_2026-08-18.json").read_text())
RAIN = next(s for s in PAY["series"] if s["id"] == "rainfall")
EXT = next(s for s in PAY["series"] if s["id"] == "flood_extent")
B = RAIN["basis"]

# THE PAYLOAD'S OWN SENTENCE, NOT MY PARAPHRASE OF IT. This box read
# "not assessed, no baseline exists for this region", which product
# caught: "no baseline exists" invites a reader to think we CHOSE not to
# look. The payload's second clause is the load-bearing half and says we
# do not know, which is the true and more uncomfortable statement and the
# one that stops absence reading as reassurance.
#
# The built row was already quoting the payload in full; only this mockup
# was short, so the two disagreed about what the row says. Reading the
# emitted string rather than restating it is the same rule that stopped
# the crops caveat drifting by a rounding rule.
EXT_REASON = (EXT.get("not_assessed_reason") or [""])[0]

# LIMA IS OURS NOW. heat/data/lima_nights.json, emitted in 553fa955, so
# these are read from the file rather than typed from a message. When this
# mockup was first built the figures were external and it said so; heat has
# since built the artifact.
_LIMA = json.loads((ROOT / "heat/data/lima_nights.json").read_text())
_REC = sorted(_LIMA["august_record"], key=lambda r: -(r["warmest_night_c"] or 0))

# THE FIRST VERSION OF THIS CHART ASSERTED SOMETHING FALSE. Product wrote,
# and I drew, "that list of years IS the El Nino list, in order". Heat
# checked it against our own ONI and it is not: August 1983 was NEUTRAL,
# ONI -0.24, sitting in the decay of the 1982-83 event. A calendar-year
# label files that El Nino under 1982 and calls 1983 la_nina, which would
# have put a La Nina year among the five warmest on a chart arguing warm
# August nights are El Nino nights.
#
# So each August is labelled by the ocean AT THAT AUGUST, and the true
# claim is FOUR of the five, not five. Weaker, and it survives contact
# with our own year-status file, which the stronger one did not.
LIMA_TOP = [(str(r["year"]), r["warmest_night_c"], r["enso"] == "el_nino")
            for r in _REC[:5]]
_CW = _LIMA["current_winter"]
LIMA_NOW = (str(_CW["year"]), _CW["warmest_night_c"])
LIMA_N, LIMA_OF = _CW["nights_at_or_above_20"], _CW["nights_measured"]
LIMA_MONTHS = _CW["by_month"]

CSS = """
:root{--paper:#f1efec;--ink:#1a1a1a;--ink2:#3a3a38;--ink3:#6b6a66;
 --rule:#d9d5cd;--flood:#2b6b7a;--heat:#b4531f;--warn:#8a5a00}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:30px 22px 70px;
 font:15px/1.55 Georgia,'Times New Roman',serif}
.wrap{max-width:1080px;margin:0 auto}
.mono{font:11px/1.5 ui-monospace,'SF Mono',Menlo,monospace;letter-spacing:.04em;
 text-transform:uppercase;color:var(--ink3)}
h1{font-size:27px;letter-spacing:-.01em;margin:6px 0 10px}
h2{font-size:20px;margin:0 0 6px;letter-spacing:-.01em}
.intro{color:var(--ink2);max-width:72ch;font-size:14.5px}
.piece{background:#fbfaf8;border:1px solid var(--rule);padding:26px 26px 22px;
 margin:26px 0}
.claim{font-size:29px;line-height:1.16;letter-spacing:-.012em;margin:6px 0 10px}
.stand{color:var(--ink2);max-width:66ch;margin:0 0 18px}
.hero{font:600 40px/1 ui-monospace,Menlo,monospace;letter-spacing:-.02em}
.herocap{font:11px/1.5 ui-monospace,Menlo,monospace;color:var(--ink3);
 margin-top:5px}
.opt{border:1px dashed #bdb7ab;background:#f6f4f0;padding:14px 15px;margin:12px 0}
.opt .mono{color:var(--warn)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.lean{font-size:13px;color:var(--ink3);margin:8px 0 0;font-style:italic}
.prov{border-left:4px solid var(--warn);background:#fbf6ea;padding:13px 15px;
 margin:0 0 18px;font-size:13.5px;color:#4a3c1a}
.prov b{display:block;font:11px/1.6 ui-monospace,Menlo,monospace;
 letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}
table{border-collapse:collapse;font-size:13.5px;margin:4px 0 0}
td{padding:3px 14px 3px 0;vertical-align:baseline}
td.n{font-family:ui-monospace,Menlo,monospace}
.tag{display:inline-block;font:10px/1 ui-monospace,Menlo,monospace;
 letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--rule);
 padding:5px 7px;color:var(--ink3);background:var(--paper)}
.empty{border:1px dashed #c3bdb1;background:repeating-linear-gradient(-45deg,
 #f4f2ee 0 6px,#eeebe5 6px 12px);height:150px;display:flex;align-items:center;
 justify-content:center;text-align:center;padding:16px}
.note{font-size:13px;color:var(--ink3);max-width:70ch}
hr.r{border:0;border-top:1px solid var(--rule);margin:18px 0}
"""


def bars(rows, current, hue, marked_label):
    """Rows are (label, value, marked). Drawn to scale, no axis tricks."""
    top = max(v for _, v, _ in rows + [(current[0], current[1], False)])
    # HEADROOM FOR THE VALUE LABEL. Each bar prints its value 6px above
    # itself, so on the tallest bar that lands at y = -6 and the number is
    # clipped off the top of the viewBox. The label on the one bar the
    # chart exists to show was the one that vanished.
    w, h, gap, pad = 74, 150, 16, 20
    out, x = [], 0
    allrows = rows + [(current[0], current[1], "now")]
    for lab, v, mark in allrows:
        bh = h * (v / top)
        fill = hue if mark == "now" else ("#7d9aa3" if mark else "#c6c1b7")
        out.append('<g><rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s"/>'
                   '<text x="%d" y="%.1f" text-anchor="middle" font-size="12" '
                   'font-family="ui-monospace,Menlo,monospace" fill="%s">%.1f</text>'
                   '<text x="%d" y="%d" text-anchor="middle" font-size="11" '
                   'font-family="ui-monospace,Menlo,monospace" fill="#6b6a66">%s</text>'
                   '%s</g>'
                   % (x, pad + h - bh, w, bh, fill,
                      x + w // 2, pad + h - bh - 6, "#1a1a1a", v,
                      x + w // 2, pad + h + 15, lab,
                      ('<text x="%d" y="%d" text-anchor="middle" font-size="10" '
                       'font-family="ui-monospace,Menlo,monospace" fill="#b4531f">%s</text>'
                       % (x + w // 2, pad + h + 29, marked_label)) if mark is True else ""))
        x += w + gap
    return ('<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx;height:auto">'
            '%s</svg>' % (x, pad + h + 36, x, "".join(out)))


def opt(letter, title, body, lean=""):
    return ('<div class="opt"><p class="mono">Option %s &middot; %s</p>%s%s</div>'
            % (letter, title, body,
               '<p class="lean">%s</p>' % lean if lean else ""))


def flood_piece():
    win = "1 to 14 August 2026"
    q1 = (
        '<h3 class="mono" style="color:#1a1a1a;font-size:12px">Decision 1 &middot; '
        'how the page says it measures rainfall, not flooding</h3>'
        '<p class="note">A reader arrives at a flood page with flooding in '
        'mind and will supply the word we did not. Harder than the crops '
        'instrument problem, because the channel name and the reader\'s '
        'expectation both point the wrong way.</p>'
        '<div class="grid2">'
        + opt("A", "in the claim itself",
              '<p class="claim" style="font-size:22px">69.4 mm of RAIN fell on '
              'the Eastern Pyrenees in a fortnight, the most in 27 years.</p>'
              '<p class="note">The word is load-bearing and unmissable. '
              'Costs the sentence some grace.</p>')
        + opt("B", "claim clean, instrument line directly under it",
              '<p class="claim" style="font-size:22px">The Eastern Pyrenees had '
              'their wettest fortnight in 27 years.</p>'
              '<span class="tag">Measures rainfall &middot; not flood extent</span>'
              '<p class="note" style="margin-top:8px">Reads better and puts the '
              'qualifier one line below the claim rather than inside it.</p>')
        + '</div>'
        '<p class="lean">I lean A. D-051 says a qualifier travels with its '
        'datum, and on this page the qualifier IS the finding\'s boundary. B '
        'is one scroll from being screenshotted without the tag.</p>')

    q2 = (
        '<h3 class="mono" style="color:#1a1a1a;font-size:12px">Decision 2 &middot; '
        'flood extent is not assessed, and that is a finding</h3>'
        '<p class="note">D-193: the screen passed 0 of 6 European regions, not '
        'because Europe cannot be seen but because week-to-week visibility '
        'varies enough that a ranking would rank the weather over the sensor.</p>'
        '<div class="grid2">'
        + opt("A", "a second instrument row, deliberately empty",
              '<table><tr><td>Rainfall</td><td class="n">69.4 mm</td>'
              '<td class="n">1st of 27</td></tr>'
              '<tr><td style="color:#6b6a66">Flood extent</td>'
              '<td colspan="2" style="color:#6b6a66">not assessed</td></tr>'
              '<tr><td colspan="3" style="color:#6b6a66;font-size:12.5px;'
              'padding-top:0">' + EXT_REASON + '</td></tr></table>'
              '<p class="note" style="margin-top:8px">The gap is drawn at the '
              'same weight as the measurement, so absence cannot read as zero.</p>')
        + opt("B", "prose only, under “what this is not”",
              '<p class="note">We have not measured flooding here; this page '
              'reports rainfall only. Flood extent is not assessed for European '
              'regions because satellite visibility varies week to week.</p>'
              '<p class="note" style="margin-top:8px">Honest, and it sits below '
              'the fold where the reader has already formed a view.</p>')
        + '</div>'
        '<p class="lean">I lean A, strongly. This project\'s recurring defect '
        'is absent read as zero, and a row that exists and says "not assessed" '
        'is the only version a skimming reader cannot miss.</p>')

    q3 = (
        '<h3 class="mono" style="color:#1a1a1a;font-size:12px">Decision 3 &middot; '
        'two dates, neither of them small print</h3>'
        '<div class="grid2">'
        + opt("A", "both in the eyebrow, equal weight",
              '<p class="mono" style="color:#1a1a1a">Eastern Pyrenees &middot; '
              '1 to 14 August 2026 &middot; measured 18 August</p>'
              '<p class="note" style="margin-top:8px">One line, both facts, no '
              'hierarchy asserted between them. This is what I built.</p>')
        + opt("B", "window in the eyebrow, made-on beside the number",
              '<p class="mono" style="color:#1a1a1a">Eastern Pyrenees &middot; '
              '1 to 14 August 2026</p>'
              '<div class="hero" style="font-size:30px;color:var(--flood)">3.17&times;</div>'
              '<p class="herocap">the median for this fortnight &middot; '
              'measured 18 August, published 21 August</p>'
              '<p class="note" style="margin-top:8px">Separates when it happened '
              'from when we said it, which is the distinction that will matter '
              'once pieces are days old.</p>')
        + '</div>'
        '<p class="lean">Genuinely unsure. A is cleaner; B is the one that '
        'still works when someone reads this in October.</p>')

    return (
        '<div class="piece">'
        '<p class="mono">Mockup 1 &middot; flood &middot; every number below is ours</p>'
        '<p class="mono" style="color:#1a1a1a">Eastern Pyrenees and upper Segre '
        '&middot; %s &middot; measured 18 August 2026</p>'
        '<p class="claim">%.1f mm of rain fell on the Eastern Pyrenees and upper '
        'Segre in %s, the most in %s years of the same fortnight.</p>'
        '<p class="stand">Against a median of %.1f mm for the same fortnight, '
        '%.2f times the median and the highest of the %s years compared. '
        'This measures rainfall, not flooding.</p>'
        '<div class="hero" style="color:var(--flood)">%.2f&times;</div>'
        '<p class="herocap">the median for this fortnight, %.1f mm</p>'
        '<hr class="r">'
        '<p class="mono">The chart, and what is missing from it</p>'
        '<div class="empty"><p class="note" style="margin:0">'
        '<b>Rainfall over 1 to 14 August, by year, 27 bars.</b><br>'
        'Not drawn: the payload carries the value, the median and the rank but '
        'not the 27 yearly accumulations. FLO holds them. Plausible bars here '
        'would make this the most convincing untrue thing on the site.</p></div>'
        '<hr class="r">%s<hr class="r">%s<hr class="r">%s'
        '<hr class="r">'
        '<p class="mono">Carried through from the payload, unchanged</p>'
        '<p class="note">%d of %d days compared. %s absent from the source and '
        'excluded from EVERY year, not just this one, so the comparison stays '
        'like for like. Peak day %.1f mm, %.0f%% of the fortnight against a '
        '%.0f%% median, so this is an accumulation rather than one cloudburst. '
        'Instrument: %s. Attribution: not ENSO-linked.</p>'
        '<p class="lean">The excluded day is the kind of honesty that reads as '
        'a caveat and should read as rigour. Open question for you: does it '
        'belong here, or one line under the chart where it explains a gap the '
        'reader can see?</p>'
        '</div>'
        % (win, RAIN["value"], win, B["of"], B["median"], B["x_median"],
           B["of"], B["x_median"], B["median"], q1, q2, q3,
           RAIN["window_days_compared"], RAIN["window_days_nominal"],
           " and ".join(RAIN["days_excluded"]), RAIN["peak_day_mm"],
           100 * RAIN["event_character"]["top_day_share"],
           100 * RAIN["event_character"]["baseline_median_top_day_share"],
           RAIN["instrument"]))


def _full_record_option():
    """The whole GHCN record, now that heat has emitted it.

    OFFERED, NOT SUBSTITUTED. Kristjan has already ruled on the chart, and
    this is a new capability rather than a re-run of a settled question:
    when the six-bar version was drawn, the full record did not exist in
    the repo and the mockup said heat would have to build it. They have.

    It is the more honest picture and it makes the marking argument better
    rather than worse: on six bars a reader sees four marks and takes our
    word for the pattern; on the whole record they can see every El Nino
    August and judge it. It also shows the years the top-five view hides,
    including the El Nino Augusts that were NOT warm.
    """
    rows = sorted(_REC, key=lambda r: r["year"])
    top = max(r["warmest_night_c"] for r in rows + [
        {"warmest_night_c": LIMA_NOW[1]}])
    w, gap, h, pad = 15, 4, 130, 18
    out, x = [], 0
    for r in rows + [{"year": int(LIMA_NOW[0]), "warmest_night_c": LIMA_NOW[1],
                      "enso": "current"}]:
        v = r["warmest_night_c"]
        bh = h * (v / top)
        cur = r.get("enso") == "current"
        fill = ("#b4531f" if cur else
                "#7d9aa3" if r.get("enso") == "el_nino" else "#cfcabf")
        out.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s">'
                   '<title>%s: %.1f C, %s</title></rect>'
                   % (x, pad + h - bh, w, bh, fill, r["year"], v,
                      r.get("enso", "")))
        if cur or r["year"] in (1997, 1983):
            out.append('<text x="%d" y="%d" text-anchor="middle" font-size="9" '
                       'font-family="ui-monospace,Menlo,monospace" '
                       'fill="#6b6a66">%s</text>'
                       % (x + w // 2, pad + h + 12, r["year"]))
        x += w + gap
    n_nino = sum(1 for r in rows if r.get("enso") == "el_nino")
    return (
        '<div class="opt"><p class="mono">Option &middot; the whole record, '
        'now that it exists</p>'
        '<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx;height:auto">'
        '%s</svg>'
        '<p class="note" style="margin-top:8px">All %d measured Augusts in '
        'GHCN, El Nino Augusts marked, 2026 at the right. It makes the '
        'marking argument better rather than worse: on six bars a reader '
        'takes our word for the pattern, and here they can see it, including '
        'the %d El Nino Augusts that were not warm.</p>'
        '<p class="lean">Offered, not substituted. You have ruled on the '
        'chart; this only became possible when heat emitted the record.</p>'
        '</div>' % (x, pad + h + 18, x, "".join(out), len(rows), n_nino))


def lima_piece():
    chart = bars(LIMA_TOP, LIMA_NOW, "#b4531f", "El Nino")
    return (
        '<div class="piece">'
        '<p class="mono">Mockup 2 &middot; heat &middot; Lima</p>'
        '<div class="prov"><b>Corrected since you last saw this</b>This piece originally said the five warmest August nights ARE the El Nino list, in order. That was false and heat caught it against our own ONI: August 1983 was NEUTRAL, ONI &minus;0.24, sitting in the decay of the 1982-83 event. The true claim is FOUR of the five. Weaker, and it survives contact with our own year-status file, which the stronger one did not. The figures are also ours now: heat emitted heat/data/lima_nights.json and this reads from it rather than from a message.</div>'
        '<p class="mono" style="color:#1a1a1a">Lima &middot; winter 2026 '
        '&middot; GHCN record, current winter from station bulletins</p>'
        '<p class="claim">Lima has had 75 of its last 77 winter nights at or '
        'above 20&nbsp;&deg;C.</p>'
        '<p class="stand">June 29 of 29, July 30 of 30, August 16 of 18. The '
        'warmest, 21.7&nbsp;&deg;C on 14 August, is above anything in the '
        'station&rsquo;s August record.</p>'
        '<hr class="r">'
        '<p class="mono">The chart, and it is the whole piece</p>'
        '<p class="note" style="margin-bottom:10px">The five warmest August '
        'nights in Lima&rsquo;s GHCN record, and 2026. <b>Four of the five '
        'fell in an El Nino August</b>, marked below; 1983 did not, and is '
        'not marked. Each August is labelled by the ocean AT THAT AUGUST, '
        'not by its calendar year. No European page of ours can show this.</p>'
        + chart +
        '<p class="note" style="margin-top:12px">Six points, not a series: '
        'the top five and this year. Drawn as six discrete bars so it cannot '
        'be read as a complete history. <b>Heat has since emitted the full '
        'record</b>, so the option below is now possible and was not when '
        'this was first drawn.</p>'
        + _full_record_option() +
        '<hr class="r">'
        '<h3 class="mono" style="color:#1a1a1a;font-size:12px">Decision 4 '
        '&middot; count versus peak, and it is our distinction</h3>'
        '<div class="grid2">'
        + opt("A", "lead with the count",
              '<p class="claim" style="font-size:22px">75 of Lima&rsquo;s last '
              '77 winter nights stayed at or above 20&nbsp;&deg;C.</p>'
              '<p class="note">The viral framing is one record night. Ours is '
              'persistence, which is the same argument that made Lugano work.</p>')
        + opt("B", "lead with the record night, count as support",
              '<p class="claim" style="font-size:22px">Lima&rsquo;s warmest '
              'August night on record, above 1997.</p>'
              '<p class="note">Sharper, more shareable, and it is the framing '
              'everyone else will already have used.</p>')
        + '</div>'
        '<p class="lean">I lean A and it is not close. B is a race we lose on '
        'speed and win on nothing; A is a claim only a baseline can make, and '
        'the chart underneath it does the shareable work anyway.</p>'
        '<hr class="r">'
        '<h3 class="mono" style="color:#1a1a1a;font-size:12px">Decision 5 '
        '&middot; SETTLED: mark the years, claim nothing further</h3>'
        '<p class="note">Kristjan\'s call. The chart marks which Augusts were '
        'El Nino and the prose does not argue from it. The reader connects; '
        'we do not. That posture is the reason the correction above cost us '
        'a word and not a page: nothing in the copy had been built on five '
        'of five, because the copy never made the claim.</p>'
        '<p class="lean">Worth noting what nearly happened. The stronger '
        'claim was the one everybody wanted, including me, and it was wrong '
        'in the one direction that would have embarrassed the thesis it was '
        'meant to support: a La Nina year among the five warmest, on a chart '
        'arguing warm nights are El Nino nights.</p>'
        '</div>')


def main():
    out = ROOT / "design/mockups/fast_reaction_options.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        '<!doctype html><meta charset="utf-8">'
        '<title>Fast-reaction mockups, two pieces</title>'
        '<style>%s</style><div class="wrap">'
        '<p class="mono">Design &middot; mockups for reaction, not for publishing</p>'
        '<h1>Two fast-reaction pieces, and the decisions inside them</h1>'
        '<p class="intro">Built on real numbers so the shapes are honest. '
        'Where a choice is open this shows both options and says which way I '
        'lean, rather than picking quietly. <b>Piece 1 is entirely our own '
        'validated data. Piece 2 is not ours at all</b> and carries that on '
        'its face. Neither chart invents a data point: where we do not hold a '
        'series, the space says so.</p>'
        '%s%s</div>' % (CSS, flood_piece(), lima_piece()))
    print("wrote %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
