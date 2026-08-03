"""The July 2026 fire card: two numbers, both true, neither one the story.

MANUAL, like design/make_pacific_sst.py. Not wired into any publish
path. It reads committed regional data and writes one PNG.

## Why two numbers rather than one

The Fire chat's call and it is right: either figure alone is half the
story and misleads in opposite directions. "The world burned half its
normal July" reads as reassurance. "The EU had its third-worst July"
reads as alarm. Both are true of the same month, and the contrast IS
the finding, so they sit side by side at the same size.

## The calibration rule, with its first real test

D-043 says the system must be able to show "within historical range" as
legibly as it shows "extreme", and until now that has been asserted on
data that was never actually quiet. Here the world is at 0.5x, the
lowest in the satellite record, and it has to read as a finding rather
than as an absence.

So the same threshold rule as everywhere else: the channel hue is spent
only above a place's own baseline. The EU at 1.7x takes fire; the world
at 0.5x takes ink. A record LOW rendered in alarm red would be the
calibration failure in reverse, and rendering it in a "good" colour
would be a judgement the data does not carry.

## The four things this must not say

All four are the Fire chat's and all four are load-bearing.

1. Not "lowest ever". The record starts in 2012, so it is the lowest in
   the satellite record and 15 years is the whole of it.
2. Not detections. This is burnt area in hectares from GWIS and EFFIS, a
   different instrument from the country pages with different lag and
   revision behaviour. A reader who has seen "Greece 11.3x" on a country
   page will assume one metric unless told, so the card names the
   instrument on its face.
3. Not an attribution. Nothing here says why, and no ENSO framing: zero
   of the fire channel's countries are tagged ENSO-linked, so an El Nino
   frame would be actively false.
4. Not final. July area revises upward as perimeters are mapped, so the
   record-low margin can narrow. The card says so.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T  # noqa: E402

DATA = ROOT / "fires" / "data" / "area_regions.json"
OUT = ROOT / "design" / "review" / "fires-july-2026-card.png"
# Point sizes below are relative to the figure's INCHES, not its pixels,
# so the inch size is the layout and the save DPI is only resolution.
# 12 x 6.3 at 2x gives a 2400x1260 file for a 1200x630 card.
W, H, DPI, SCALE = 1200, 630, 100, 2


def july(series: dict):
    w = {int(k): v for k, v in series.items()}
    return w[30] - w[26] if 30 in w and 26 in w else None


def stats(region: dict):
    ys = {int(y): july(s) for y, s in region["years"].items()}
    ys = {y: v for y, v in ys.items() if v is not None}
    prior = {y: v for y, v in ys.items() if y < 2026}
    cur = ys[2026]
    mean = sum(prior.values()) / len(prior)
    rank = 1 + sum(1 for v in prior.values() if v > cur)
    return cur, mean, cur / mean, rank, len(ys)


def main() -> None:
    regions = json.loads(DATA.read_text())["regions"]
    world = stats(regions["gwis:WORLD"])
    eu = stats(regions["gwis:EU"])

    # Vendored per family in its own directory, as card.py loads them.
    # A flat *.ttf glob here silently matches nothing and every family
    # falls back, which looks like a font choice rather than a bug.
    for pat in ("spectral/*.ttf", "ibm-plex-mono/*.ttf"):
        for f in (ROOT / "assets" / "fonts").glob(pat):
            try:
                font_manager.fontManager.addfont(str(f))
            except Exception:
                pass

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(T.PAPER)
    prose = {"family": T.FONT_PROSE, "color": T.INK}

    fig.text(0.055, 0.90, " ".join("THE LONG SWELL"), fontsize=10.5,
             color=T.INK_FAINT, family=T.FONT_DATA)
    fig.text(0.945, 0.90, " ".join("FIRES"), fontsize=10.5,
             color=T.FIRE, family=T.FONT_DATA, ha="right")
    fig.text(0.055, 0.795, "July 2026, burnt area", fontsize=31,
             **prose)

    # Two panels, equal size, because the contrast is the finding and
    # either number alone misleads in the opposite direction.
    for x, (cur, mean, mult, rank, n), name, sub in (
            (0.055, world, "World", "lowest of the 15 Julys on record"),
            (0.545, eu, "European Union", "third highest of 15, and 0.6% "
                                          "below 2017")):
        # Threshold, not a ramp: hue only above the region's own normal.
        # A record LOW in alarm red would be the calibration failure
        # running backwards.
        hue = T.FIRE if mult >= 1.0 else T.INK
        fig.text(x, 0.60, " ".join(name.upper()), fontsize=11,
                 color=T.INK_FAINT, family=T.FONT_DATA)
        fig.text(x, 0.43, f"{mult:.1f}×", fontsize=76, color=hue,
                 family=T.FONT_DATA, weight="bold")
        fig.text(x, 0.335, f"{cur:,.0f} ha, against {mean:,.0f} normally",
                 fontsize=13.5, color=T.INK_SOFT, family=T.FONT_DATA)
        fig.text(x, 0.265, sub, fontsize=15, color=T.INK, family=T.FONT_PROSE)

    fig.lines.append(plt.Line2D([0.50, 0.50], [0.20, 0.63],
                                transform=fig.transFigure,
                                color=T.RULE, linewidth=1))
    fig.lines.append(plt.Line2D([0.055, 0.945], [0.70, 0.70],
                                transform=fig.transFigure,
                                color=T.INK, linewidth=2.2))

    # Instrument named on the face of the card, because a reader who has
    # seen a detection multiple on a country page will otherwise assume
    # one metric. And the revision direction, because this figure moves.
    # va="top" so the block grows downward from a known line, rather than
    # up from a baseline into the panels above it.
    fig.text(0.055, 0.175,
             "Burnt area mapped by Copernicus GWIS and EFFIS, weeks 27 to 30. "
             "Not the same instrument as\nthe detection counts on our country "
             "pages, and never converted into them. July area revises upward "
             "as\nperimeters are mapped, so the low can narrow. Satellite "
             "record begins 2012.",
             fontsize=10, color=T.INK_FAINT, family=T.FONT_DATA,
             linespacing=1.75, va="top")
    fig.text(0.945, 0.055, "thelongswell.com", fontsize=10.5,
             color=T.INK_FAINT, family=T.FONT_DATA, ha="right")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=T.PAPER, dpi=DPI * SCALE)
    print(f"world {world[2]:.2f}x rank {world[3]}/{world[4]}   "
          f"EU {eu[2]:.2f}x rank {eu[3]}/{eu[4]}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
