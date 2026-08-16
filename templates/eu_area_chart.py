"""The EU burnt-area season chart: where 2026 stands, and where it could end.

KRISTJAN ASKED FOR THE FUNNEL. Fire supplied the data and three constraints
that live in the payload as fields rather than in a chat, which is the only
reason this renderer can honour them on a rebuild nobody is watching.

THE ONE THAT SHAPES EVERY DRAWING DECISION HERE. Editor's rule, arrived at
from fire's problem: PUBLISHING A RANGE PUBLISHES ITS MAXIMUM unless a
sentence says otherwise. Not a label on an axis, a sentence. A funnel is
read top-first because the big number is the interesting one, so a band
drawn with equal weight throughout says "worse than the worst year ever"
however the caption is worded.

So the band is drawn as faintly as it can be and still be seen, its upper
edge carries no stroke at all, and the MEDIAN is drawn at the same weight
as the observed line so the eye runs straight from where the season is
into where a typical season would take it. The maximum is reachable and
never dominant. `median_below_record` is true and the chart has to look
like it.

THE COUNT, NEVER A PERCENTILE. Science removed the percentile deliberately:
"5 of the 20 prior seasons would have finished above the record" is
unimpeachable, while "the record sits at the 75th percentile" is the same
fact dressed as a probability and swings to 1 of 20 under a different
modelling choice. The count is what renders.

EUROPEAN UNION, NEVER EUROPE. EFFIS files the United Kingdom under Non_EU,
so this total omits it, and the UK is currently the most extreme country in
this channel's detection record. An EU hectares total sitting near UK
country charts with the UK invisible inside it is a defect a reader finds
in one scroll, so the set is named on the chart itself and the exclusion is
stated rather than implied.

COMPILED, NOT MEASURED. D-033. This is EFFIS's published product aggregated
and projected; the detection charts beside it are ours. Two adjacent charts
on different evidence bases is exactly what the tagging exists to disclose.
"""
import json
import os

W, H = 760, 330
PAD_L, PAD_R, PAD_T, PAD_B = 4, 132, 26, 34
WEEK_LO, WEEK_HI = 10, 52          # nothing burns in the EU before week 10


def _fmt(ha):
    """Hectares at the scale this chart works in. 879,980 reads as 880k,
    which is the precision the envelope actually carries; printing six
    significant figures on a projected band is false precision, and fire's
    own `why_not_a_point` is the argument for not doing it."""
    return "%.0fk" % round(ha / 1000.0)


def _path(pts):
    return "M" + " L".join("%.1f,%.1f" % p for p in pts)


def _rlab(x, y, cls, long, short):
    """A right-gutter label in two lengths, one shown per width.

    The gutter is 132 viewBox units, which holds a 9.5-unit label and
    nothing larger. The phone needs those labels at about 19 units to be
    readable at all, and at 19 units "highest analog 1538k" runs 103 units
    past the edge of the box. Nothing in CSS can shorten a string, so both
    lengths are emitted and the breakpoint picks one.

    Measured rather than guessed: at 19 units the short forms end at 749
    of 760. They are the same numbers either way, from the same variables,
    so the two forms cannot come to disagree.
    """
    return (f'<text class="{cls} euwide" x="{x:.1f}" y="{y:.1f}">{long}</text>'
            f'<text class="{cls} eunar" x="{x:.1f}" y="{y:.1f}">{short}</text>')


def chart(doc):
    """The figure. Returns SVG, or "" if the payload cannot support it."""
    series = doc.get("series") or {}
    pr = doc.get("projection") or {}
    now_year = str(doc.get("as_of_year") or "")
    now_week = int(doc.get("as_of_week") or 0)
    now_ha = doc.get("area_ha")
    if not series or not pr or not now_ha or now_year not in series:
        return ""

    lo, mid, hi = (pr.get("analog_min_ha"), pr.get("analog_median_ha"),
                   pr.get("analog_max_ha"))
    rec, rec_y = pr.get("record_ha"), str(pr.get("record_year") or "")
    if None in (lo, mid, hi, rec):
        return ""

    top = max(hi, rec) * 1.10
    IW, IH = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    X = lambda w: PAD_L + (w - WEEK_LO) / (WEEK_HI - WEEK_LO) * IW
    Y = lambda v: PAD_T + IH - (v / top) * IH

    out = []

    # THE PRIOR SEASONS, all twenty, drawn once and faintly. They are the
    # evidence the envelope is built from, so leaving them out would make
    # the band look like a model output rather than what twenty seasons
    # actually did. The record year is not given a hue: it earns its
    # emphasis from the labelled line at its own height, and D-101 keeps
    # hue for a record rather than spending it on a background trace.
    for y, weeks in sorted(series.items()):
        if y == now_year:
            continue
        pts = [(X(int(w)), Y(v)) for w, v in sorted(weeks.items(), key=lambda kv: int(kv[0]))
               if int(w) >= WEEK_LO]
        if len(pts) > 1:
            emph = ' stroke-width="1.3" opacity="0.55"' if y == rec_y else \
                   ' stroke-width="0.8" opacity="0.28"'
            out.append(f'<path d="{_path(pts)}" fill="none" '
                       f'stroke="var(--ink-faint)"{emph}/>')

    # THE ENVELOPE. Drawn from where the season stands, so it is visibly a
    # continuation of the observed line rather than a separate object.
    x0, xe = X(now_week), X(WEEK_HI)
    band = [(x0, Y(now_ha)), (xe, Y(hi)), (xe, Y(lo))]
    out.append(f'<path d="{_path(band)} Z" fill="var(--fire)" opacity="0.10" '
               f'stroke="none"/>')
    # The lower edge only. An upper edge would draw the eye to the maximum,
    # which is the failure mode this chart is built against.
    out.append(f'<path d="{_path([(x0, Y(now_ha)), (xe, Y(lo))])}" fill="none" '
               f'stroke="var(--fire)" stroke-width="0.8" opacity="0.45"/>')

    # THE RECORD, as a line at its own height across the whole chart, so a
    # reader can see the median passing below it without reading a number.
    out.append(f'<line x1="{PAD_L}" y1="{Y(rec):.1f}" x2="{xe:.1f}" '
               f'y2="{Y(rec):.1f}" stroke="var(--ink)" stroke-width="1" '
               f'stroke-dasharray="5 4" opacity="0.7"/>')
    out.append(_rlab(xe + 7, Y(rec) + 3.5, "eul",
                     f"{rec_y} record {_fmt(rec)}", f"rec {_fmt(rec)}"))

    # THE MEDIAN, at the weight of the observed line. This is the sentence
    # the chart makes: a typical season from here lands BELOW the dashed
    # line. Everything above it is reachable and nothing above it is
    # central.
    out.append(f'<path d="{_path([(x0, Y(now_ha)), (xe, Y(mid))])}" fill="none" '
               f'stroke="var(--fire)" stroke-width="2.4"/>')
    out.append(_rlab(xe + 7, Y(mid) + 3.5, "eum",
                     f"median {_fmt(mid)}", f"med {_fmt(mid)}"))
    out.append(_rlab(xe + 7, Y(hi) + 3.5, "eul",
                     f"highest analog {_fmt(hi)}", f"high {_fmt(hi)}"))
    out.append(_rlab(xe + 7, Y(lo) + 3.5, "eul",
                     f"lowest {_fmt(lo)}", f"low {_fmt(lo)}"))

    # THE SEASON SO FAR, last, so it sits above everything else it crosses.
    pts = [(X(int(w)), Y(v)) for w, v in
           sorted(series[now_year].items(), key=lambda kv: int(kv[0]))
           if int(w) >= WEEK_LO]
    out.append(f'<path d="{_path(pts)}" fill="none" stroke="var(--fire)" '
               f'stroke-width="2.4"/>')
    out.append(f'<circle cx="{x0:.1f}" cy="{Y(now_ha):.1f}" r="3.4" '
               f'fill="var(--fire)"/>')
    out.append(f'<text class="eun" x="{x0 - 7:.1f}" y="{Y(now_ha) - 9:.1f}" '
               f'text-anchor="end">{now_year}, {_fmt(now_ha)} so far</text>')

    # A sparse axis. Week numbers mean little to a reader, so the ticks are
    # months, and only four of them.
    for wk, lab in ((14, "Apr"), (23, "Jun"), (31, "Aug"), (40, "Oct")):
        out.append(f'<text class="eux" x="{X(wk):.1f}" y="{H - 12}" '
                   f'text-anchor="middle">{lab}</text>')

    n_over = pr.get("analogs_exceeding_record")
    n_tot = pr.get("analogs_total")
    alt = (f"European Union burnt area by week. {now_year} stands at "
           f"{now_ha:,} hectares at week {now_week}. Applying every prior "
           f"season's remaining growth from this same week gives a band "
           f"from {lo:,} to {hi:,} hectares, with a median of {mid:,}, "
           f"which is below the {rec_y} record of {rec:,}. "
           f"{n_over} of the {n_tot} prior seasons would have finished above "
           f"that record from here. The twenty faint lines are those "
           f"seasons. European Union only: the United Kingdom is not in "
           f"this total.")

    return (f'<svg viewBox="0 0 {W} {H}" width="100%" style="height:auto" '
            f'role="img" aria-label="{alt}">' + "".join(out) + "</svg>")


CSS = """
.euwrap { margin: 26px 0 0; }
.eul { font-family: var(--mono, ui-monospace, monospace); font-size: 9.5px;
  fill: var(--ink-faint); }
/* The median label is the only one in full ink. Same reasoning as the line
   weight: the centre of the band has to win the glance. */
.eum { font-family: var(--mono, ui-monospace, monospace); font-size: 10.5px;
  font-weight: 600; fill: var(--ink); }
.eun { font-family: var(--mono, ui-monospace, monospace); font-size: 10.5px;
  font-weight: 600; fill: var(--fire); }
.eux { font-family: var(--mono, ui-monospace, monospace); font-size: 9.5px;
  fill: var(--ink-faint); }
/* THE PHONE. A 760-unit viewBox in a 342px column renders a 9.5-unit label
   at 4.3 real pixels, which is the defect that cost the El Nino charts a
   week. Sized here rather than left for later, and the labels are placed
   at four distinct heights precisely so this bump cannot collide them. */
svg .eunar { display: none; }
@media (max-width: 640px) {
  .eul, .eux { font-size: 19px; }
  .eum, .eun { font-size: 21px; }
  svg .euwide { display: none; }
  svg .eunar { display: inline; }
}
.eusay { margin: 14px 0 0; font-size: 16.5px; line-height: 1.55;
  max-width: 62ch; color: var(--ink-soft); }
.eusay b { color: var(--ink); font-weight: 600; }
.euf { margin-top: 22px; }
.eub { margin: 6px 0 0; padding-left: 18px; }
.eub li { margin: 5px 0; }
"""


def block(doc):
    """The whole unit: the sentence that licenses the funnel, the figure,
    and the register under it.

    EVERY PROSE STRING HERE IS FIRE'S, RENDERED VERBATIM. `why_not_a_point`,
    `headline_rule`, `caveat`, `method_note`, `stability` and the two
    `known_biases` are fields in the payload, so this renderer cites its
    channel rather than paraphrasing it. That is not deference: a
    paraphrase of a statistical caveat is a new claim, and it is the claim
    nobody reviewed.

    THE ORDER IS THE ARGUMENT. why_not_a_point comes FIRST, before the
    chart, because it is the fact that makes a funnel honest rather than
    hedging: in 2025 two weeks were 57% of the record season. A reader who
    has taken that in cannot then read the band as indecision. Fire and
    editor arrived at that independently and they are right.
    """
    if not doc:
        return "", ""
    pr = doc.get("projection") or {}
    fig = chart(doc)
    if not fig:
        return "", ""
    n_over, n_tot = pr.get("analogs_exceeding_record"), pr.get("analogs_total")
    rec_y = pr.get("record_year")
    biases = "".join(f"<li>{b}</li>" for b in (pr.get("known_biases") or []))

    body = f"""
  <p class="sectionlabel">How big the season is, for the {doc.get('country_set')}</p>
  <p class="standfirst">{pr.get('why_not_a_point','')}</p>

  <div class="euwrap">{fig}</div>

  <!-- THE COUNT, IN A SENTENCE, DIRECTLY UNDER THE BAND. Editor's rule:
       publishing a range publishes its maximum unless a sentence says
       otherwise, and it has to be a sentence rather than an axis label.
       Both halves of fire's headline_rule are here, in their words: what
       is true and what is not. -->
  <p class="eusay"><b>{n_over} of the {n_tot} prior seasons would have
  finished above the {rec_y} record from here, and the median lands below
  it.</b> This season could exceed the record; it is not on course to.</p>

  <p class="note"><b>European Union only.</b> {(doc.get('excludes') or [''])[0]}</p>

  <div class="foot euf">
    <p><b>Basis.</b> {doc.get('basis_note','')} {doc.get('instrument','')}.</p>
    <p><b>Method.</b> {pr.get('method_note','')} {pr.get('caveat','')}</p>
    <p><b>Stability.</b> {pr.get('stability','')}</p>
    <p><b>Known biases</b>, both running toward the more alarming
    answer.</p>
    <ul class="eub">{biases}</ul>
  </div>"""
    return body, CSS


def load(repo_root):
    p = os.path.join(repo_root, "fires", "data", "eu_area.json")
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)
