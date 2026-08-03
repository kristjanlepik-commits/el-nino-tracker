"""Record-breakers against the number an even spread would give.

The load-bearing device for any page that counts record lows across many
units, and the reason it has to exist is arithmetic rather than taste.

With N units each holding a K-year record, an ordinary period produces
about N/K new records IF every year is equally likely to hold a unit's
record. For the crops dekad that is 2,122 / 26 = 81.6 against an
observed 81.

**That "if" is doing real work and this component used to hide it.**
Records hoard. Europe's record lows sit in 2001, 2003 and 2006, so
recent European years produce roughly a quarter of what uniform
predicts, a hoarding factor of 4. Applying the uniform figure to Europe
turned an unremarkable zero into an apparent finding, and that
substitution produced four wrong conclusions across three chats in one
day.

So: an empirical expectation is used when the channel supplies one, and
the uniform fallback is LABELLED as uniform, "if records fell evenly",
never as "chance produces". The global 81.6 has not been checked against
an empirical expectation either, so it carries the weaker label too
until it is.

## The consequence that does not go away

**The finer the units, the more record-breakers a normal period
contains.** The same dekad expects about 4.7 records at country level
and 81.6 at admin level, purely because there are more units. So a
sub-national map with no chance baseline on it will look alarming every
single week, for reasons that have nothing to do with the weather, and
it will be wrong every time.

That makes the chance baseline a property of the page rather than a
caveat on it. Hence this component, and hence it draws BOTH scales:
seeing the expectation move from 4.7 to 81.6 as the units get finer is
the thing that teaches the reader why the big number is not news.

## The device is the envelope again

Same answer as the crops volatility null. A count with no reference
reads as a magnitude; a count inside a drawn expectation reads as a
result. The expected range is Poisson, since these are counts of rare
independent events: lambda = N/K, sd = sqrt(lambda), and the band is
two standard deviations either side. 81 against an expected 81.6 with a
band of roughly 64 to 100 is visibly ordinary, and no sentence does
that as quickly.

The band is drawn before the observation, deliberately. The reader
should see what normal looks like before they see where this week sits.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import h                                       # noqa: E402


def scales_block(scales, note="") -> str:
    """One row per granularity: expected range drawn, observed marked.

    scales  [{label, units, years, observed, expected?}]

    `expected` is the EMPIRICAL expectation when the channel can supply
    one. Without it this falls back to the uniform N/K and says so, in
    those words, because the two are not interchangeable and today they
    differed by a factor of four.
    """
    rows = []
    for s in scales:
        # N/K assumes every year is equally likely to hold a unit's
        # record low. Records HOARD: Europe's record lows sit in 2001,
        # 2003 and 2006, so recent European years produce about a
        # quarter of what uniform predicts. Where the channel supplies
        # an empirical expectation, use it; where it does not, use the
        # uniform one and label it as uniform rather than as chance.
        uniform = s["units"] / s["years"]
        lam = s.get("expected") or uniform
        empirical = s.get("expected") is not None
        sd = math.sqrt(lam)
        rows.append(dict(s, lam=lam, uniform=uniform, empirical=empirical,
                         lo=max(0.0, lam - 2 * sd), hi=lam + 2 * sd))
    hi_all = max(max(r["hi"], r["observed"]) for r in rows) * 1.18

    W, ROW_H, PAD_L, PAD_R, PAD_T = 680, 74, 210, 20, 30
    H = PAD_T + ROW_H * len(rows) + 22

    def X(v):
        return PAD_L + v / hi_all * (W - PAD_L - PAD_R)

    out = []
    for i, r in enumerate(rows):
        y = PAD_T + ROW_H * i + 26
        out.append(f'<text class="cb-lab" x="0" y="{y - 8:.1f}">'
                   f'{h(r["label"])}</text>')
        out.append(f'<text class="cb-sub" x="0" y="{y + 8:.1f}">'
                   f'{r["units"]:,} units, {r["years"]}-year record</text>')

        # The expected range first: what normal looks like, before the
        # reader sees where this week sits.
        x1, x2 = X(r["lo"]), X(r["hi"])
        out.append(f'<rect x="{x1:.1f}" y="{y - 14:.1f}" '
                   f'width="{x2 - x1:.1f}" height="28" '
                   f'fill="var(--paper-sunk)"/>')
        xe = X(r["lam"])
        out.append(f'<line x1="{xe:.1f}" y1="{y - 16:.1f}" x2="{xe:.1f}" '
                   f'y2="{y + 16:.1f}" stroke="var(--ink-soft)" '
                   f'stroke-width="1" stroke-dasharray="4 3"/>')
        lead = ("chance produces" if r["empirical"]
                else "if records fell evenly")
        out.append(f'<text class="cb-exp" x="{xe:.1f}" y="{y - 21:.1f}" '
                   f'text-anchor="middle">{lead} {r["lam"]:.0f}</text>')

        ox = X(r["observed"])
        inside = r["lo"] <= r["observed"] <= r["hi"]
        # Ink when the observation sits inside the range chance explains.
        # A count that is ordinary must not be coloured as though it were
        # not, which is the calibration rule applied to a count.
        fill = "var(--ink)" if inside else "var(--crop)"
        out.append(f'<circle cx="{ox:.1f}" cy="{y:.1f}" r="6.4" '
                   f'fill="{fill}"/>')
        out.append(f'<text class="cb-obs" x="{ox:.1f}" y="{y + 27:.1f}" '
                   f'text-anchor="middle" fill="{fill}">'
                   f'{r["observed"]:,} observed</text>')

    out.append(f'<text class="cb-ax" x="{PAD_L}" y="{H - 6}">'
               f'places at their worst on record, this dekad</text>')
    note_html = f'<p class="cb-note">{h(note)}</p>' if note else ""
    return (f'<svg class="cb" viewBox="0 0 {W} {H}" role="img" '
            # The accessible name has to say what the visible label says.
            # This asserted "chance produces" while the label on screen
            # carefully said "if records fell evenly", so a screen reader
            # user was given the claim the page had just been corrected
            # to avoid. Same lesson as measuring contrast rather than
            # font size: the property I checked was not the one carrying
            # the meaning.
            f'aria-label="Places at record lows against the number an even '
            f'spread of records would give, at two levels of granularity">'
            + "".join(out) + f'</svg>{note_html}')


CHANCE_CSS = f"""
.cb {{ width: 100%; height: auto; display: block; margin-top: 22px; }}
.cb text {{ font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  paint-order: stroke; stroke: var(--paper); stroke-width: 2.5;
  stroke-linejoin: round; }}
.cb-lab {{ font-size: 13px; fill: var(--ink); font-weight: 600; }}
.cb-sub {{ font-size: 10.5px; fill: var(--ink-faint); }}
.cb-exp {{ font-size: 10.5px; fill: var(--ink-soft); }}
.cb-obs {{ font-size: 12px; font-weight: 600; }}
.cb-ax {{ font-size: 10px; fill: var(--ink-faint); }}
.cb-note {{ font-size: 13px; color: var(--ink-soft); margin: 12px 0 0;
  max-width: 64ch; }}
"""
