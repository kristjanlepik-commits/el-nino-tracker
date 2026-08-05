"""Severity: five instruments read together, against a country's own record.

MOCKUP ONLY. Not wired into any build path. This is the first COMBINED
number crops would publish under D-033, so it goes to Kristjan for
sign-off rather than to CRO, and it does not ship until he has seen it.

## The rank leads and the value does not rank anything

I proposed drawing both orderings, labelled by their question, the way
the index draws depth and breadth. CRO corrected it and the correction
is the whole design.

The value is NOT a severity ordering across countries. Its year-to-year
spread is set almost entirely by how far a country's instruments move
together: r = 0.97 across 123 places. Where they co-move, an extreme
average is the ordinary shape of a bad year; where they do not, the same
number is unprecedented. PNG's instruments are nearly independent
(spread 0.151) and Chad's move together (0.261), which is exactly why
Sudan sits above PNG on value while PNG is worst on record and Sudan is
third.

So a two-column table with Sudan atop one and PNG atop the other would
read as two weightings of one question, and only one of them is
severity. The rank leads. The value is the Y AXIS OF THE HISTORY CHART,
which is the one place it is legitimate, because there it compares a
country only against itself.

## Ties are a quarter of the page

The measure lands on multiples of 1/125, so 29 of 123 places tie with a
prior year and three of those are at rank 1. A reader looking at two
identical bars will ask which is higher, so the tie has to be drawn as
a tie rather than left to look like a rendering accident.

## The sequence is a sentence, never a line

Eight dekads of movement is the most forecast-shaped object this
channel can produce. A line with its right edge at today is an
invitation to extend it, and no caption prevents that because the eye
finishes the line before the caption is read. Dropping the chart costs
a reader nothing; the sentence carries the same fact in the past tense.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import h                                       # noqa: E402

NOW = "2026"


def _history(sev: dict) -> str:
    """26 years at this dekad, value on Y, this year and any tie marked."""
    ser = {str(k): v for k, v in (sev.get("series") or {}).items()}
    if not ser:
        return ""
    years = sorted(ser)
    hi = max(max(ser.values()), 1.0)
    tied = {str(y) for y in (sev.get("tied_with") or [])}
    W, H, PAD_T, PAD_B, PAD_L, PAD_R = 660, 150, 20, 30, 8, 8
    slot = (W - PAD_L - PAD_R) / len(years)
    bw = min(slot * 0.62, 16.0)

    def Y(v):
        return PAD_T + (1 - v / hi) * (H - PAD_T - PAD_B)

    base = H - PAD_B
    out = [f'<line x1="{PAD_L}" y1="{base}" x2="{W - PAD_R}" y2="{base}" '
           f'stroke="var(--rule)" stroke-width="1"/>']
    for i, y in enumerate(years):
        v = ser[y]
        cx = PAD_L + slot * (i + 0.5)
        top = Y(v)
        now, tie = (y == NOW), (y in tied)
        hue = ("var(--crop)" if now else
               "var(--ink)" if tie else "var(--ink-faint)")
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{top:.1f}" '
                   f'width="{bw:.1f}" height="{base - top:.1f}" '
                   f'fill="{hue}"/>')
        if now or tie:
            # A tie is DRAWN as a tie. 29 of 123 places tie with a prior
            # year, so two bars of identical height are common and
            # correct, and a reader will ask which is higher. The rule
            # across both tops answers it before they ask.
            out.append(f'<text class="sv-y" x="{cx:.1f}" y="{top - 5:.1f}" '
                       f'text-anchor="middle">{h(y)}</text>')
    if tied:
        xs = [PAD_L + slot * (i + 0.5) for i, y in enumerate(years)
              if y == NOW or y in tied]
        v = ser.get(NOW)
        if v is not None and len(xs) > 1:
            out.append(f'<line x1="{min(xs) - bw:.1f}" y1="{Y(v):.1f}" '
                       f'x2="{max(xs) + bw:.1f}" y2="{Y(v):.1f}" '
                       f'stroke="var(--ink)" stroke-width="1" '
                       f'stroke-dasharray="3 3"/>')
    for i, y in enumerate(years):
        if y in (years[0], years[-1]):
            cx = PAD_L + slot * (i + 0.5)
            out.append(f'<text class="sv-x" x="{cx:.1f}" y="{H - 8}" '
                       f'text-anchor="{"start" if y == years[0] else "end"}">'
                       f'{h(y)}</text>')
    return (f'<svg class="sv" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="This country in every year of the record for the '
            f'same point in the season, five instruments read together">'
            + "".join(out) + '</svg>')


def severity_block(place: str, sev: dict) -> str:
    if not sev or not sev.get("available", True):
        why = h(sev.get("absent_because", "")) if sev else ""
        return f'<div class="svb"><p class="svabs">{why}</p></div>'
    rank, of = sev.get("rank"), sev.get("of")
    # THE RANK IS THE HEADLINE, in words, because it is the only figure
    # here that is comparable between places. The value never appears as
    # a number a reader could rank countries by; it exists as the height
    # of the bars, where it compares a country to itself alone.
    ordinal = ("worst on record" if rank == 1 else f"{_ord(rank)} worst")
    joint = " (joint)" if sev.get("tied_with") else ""
    quals = "".join(
        f'<li>{h(q.get("text", ""))}</li>' for q in (sev.get("qualifiers") or []))
    return f"""
      <div class="svb">
        <p class="svlab">Five instruments read together
          <span class="svtag">our combination, not an observation</span></p>
        <p class="svbig">{h(ordinal)}{joint}
          <span class="svof">of {of} years at this point in the season</span></p>
        <p class="svst">{h(sev.get("statement", ""))}</p>
        {_history(sev)}
        <ul class="svq">{quals}</ul>
      </div>"""


def _ord(n):
    if n is None:
        return ""
    if 10 <= n % 100 <= 20:
        s = "th"
    else:
        s = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{s}"


SEVERITY_CSS = f"""
.svb {{ margin-top:8px; }}
.svlab {{ margin:0; font-size:11px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-faint);
  font-family:"{T.FONT_DATA}",monospace; }}
/* The Combined register is bound to the number, not adjacent to it.
   Everything else on these pages is one series against its own history,
   so a reader has no reason to expect the register to change, and a
   footnote is separable by a layout decision in exactly the way
   `statement` exists to prevent. */
.svtag {{ display:inline-block; margin-left:8px; padding:1px 6px;
  background:var(--paper-sunk); color:var(--ink-soft);
  letter-spacing:.04em; text-transform:none; }}
.svbig {{ margin:6px 0 0; font-size:29px; font-weight:600;
  line-height:1.1; color:var(--crop); }}
.svof {{ display:block; font-size:14px; font-weight:400;
  color:var(--ink-soft); margin-top:4px; }}
.svst {{ margin:8px 0 0; font-size:13px; color:var(--ink-soft);
  max-width:64ch; font-family:"{T.FONT_DATA}",monospace; }}
.sv {{ width:100%; height:auto; display:block; margin:14px 0 2px; }}
.sv text {{ font-family:"{T.FONT_DATA}",monospace; }}
.sv-x {{ font-size:10px; fill:var(--ink-faint); }}
.sv-y {{ font-size:10.5px; fill:var(--ink); }}
.svq {{ margin:12px 0 0; padding-left:18px; font-size:12.5px;
  color:var(--ink-faint); max-width:66ch; }}
.svq li {{ margin-bottom:4px; }}
.svabs {{ margin:0; font-size:13.5px; color:var(--ink-faint); }}
"""
