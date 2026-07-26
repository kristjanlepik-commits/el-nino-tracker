"""
Citable chart template: the one shareable image every event piece
produces (T10). The chart is the distribution channel, so everything a
reader needs must survive a screenshot out of context: the claim, the
number, the comparison, the attribution status, the named sources with
their issue dates, and the house mark.

Design-chat surface (The Long Swell token set; see tokens.py and
research/handover_design.md). Subsection chats call render() with
their event data; the template owns layout, type, and color. Keep the
furniture fixed: the trust elements are not optional.

Usage:
    import citable
    citable.render(
        "out.png",
        title="Spain's fire week is the highest on the 15-year record",
        number="8.1x", number_label="the 2012-25 same-week mean",
        bars=[("2012", 1.0), ..., ("2026", 8.1)], highlight="2026",
        baseline=1.0, baseline_label="same-week mean",
        attribution="non_enso",
        sources="NASA FIRMS SNPP, 2012-2026 · issued 2026-07-25",
    )

The bar comparison is the v1 body (current vs the baseline years, the
fires use case). Other bodies can be added when a second concrete
shape exists; the furniture stays identical.
"""

from __future__ import annotations

import glob
import math
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Arc, Rectangle

import tokens as T

ROOT = Path(__file__).parent

for _pat in ("spectral/*.ttf", "ibm-plex-mono/*.ttf"):
    for _f in glob.glob(str(ROOT / "assets" / "fonts" / _pat)):
        try:
            font_manager.fontManager.addfont(_f)
        except Exception:
            pass
_available = {f.name for f in font_manager.fontManager.ttflist}
SERIF = T.FONT_PROSE if T.FONT_PROSE in _available else "DejaVu Serif"
MONO = T.FONT_DATA if T.FONT_DATA in _available else "DejaVu Sans Mono"

# Attribution tag vocabulary: fixed three states (T9), matching the
# site component in run_brief.py. Never invent a fourth.
ATTR = {
    "enso": ("ENSO-LOADED WINDOW", T.TAG_LOADED_BG, T.TAG_LOADED_FG),
    "non_enso": ("NOT ENSO-LINKED", T.TAG_NOTLINK_BG, T.TAG_NOTLINK_FG),
    "pending": ("ATTRIBUTION PENDING", T.TAG_PENDING_BG, T.TAG_PENDING_FG),
}

# Canonical host lives in tokens so the two distributed image
# surfaces cannot drift apart again.
SITE_URL_DISPLAY = T.SITE_HOST_DISPLAY


def _mark(fig, x, y, s, W, H):
    """Propagation mark, on-paper colorway, lower-left anchored."""
    ax = fig.add_axes([x, y, s * (H / W), s])
    ax.set_xlim(0, 26)
    ax.set_ylim(26, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((1, 10), 6, 6, facecolor=T.WARM, edgecolor="none"))
    for chord_x, half, r, col in [(10, 9.8, 13.5, T.INK),
                                  (15, 7.4, 10.0, T.INK_SOFT),
                                  (20, 4.9, 6.4, T.INK_FAINT)]:
        cx = chord_x - math.sqrt(r * r - half * half)
        ang = math.degrees(math.asin(half / r))
        ax.add_patch(Arc((cx, 13), 2 * r, 2 * r, angle=0,
                         theta1=-ang, theta2=ang, edgecolor=col, lw=1.6))


def render(out_path, *, title: str, number: str, number_label: str,
           bars: list[tuple[str, float]], highlight: str,
           sources: str, attribution: str = "pending",
           baseline: float | None = None, baseline_label: str = "",
           unit_note: str = "", subtitle: str = "",
           channel: str = "fire") -> Path:
    """Render the citable chart. 1200x675 PNG (social/press ratio).

    bars: (label, value) pairs in display order; the bar whose label
    equals `highlight` carries the warm anomaly color, all others
    recede. baseline draws a labeled reference line (e.g. the
    same-week mean the multiple is computed against). sources is the
    named-sources line with issue dates; it prints on the image, as
    does the attribution tag. No element here is decorative.
    """
    # channel picks the single hue this chart is allowed to use, so the
    # image carries its publication's identity (D-016 #4).
    hue = T.CHANNEL.get(channel, T.FIRE)
    W, H = 12, 6.75
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(T.PAPER)
    ML, MR = 0.055, 0.945

    # Header: house wordmark + attribution tag (top right)
    _mark(fig, ML - 0.004, 0.918, 0.031, W, H)
    fig.text(ML + 0.034, 0.9475, "The Long Swell", fontsize=15,
             color=T.INK, family=SERIF, fontweight="medium", va="top")
    # Attribution tag: a filled surface, mono uppercase, prominence
    # descending with claim strength (D-016).
    label_txt, tag_bg, tag_fg = ATTR.get(attribution, ATTR["pending"])
    fig.text(MR - 0.008, 0.9405, label_txt, fontsize=9.5, color=tag_fg,
             family=MONO, fontweight="medium", ha="right", va="center",
             bbox=dict(facecolor=tag_bg, edgecolor="none",
                       boxstyle="square,pad=0.55"))

    # Claim (serif) left, the number (mono, in the channel hue) right.
    # The two live in separate columns and the claim is hard-wrapped to
    # its own, because an unwrapped long title used to run straight
    # through the number and still render, which is the worst kind of
    # failure: silent. Reported by the Fire chat, which bisected the
    # collision at 63 characters.
    TITLE_WRAP = 52          # characters per line at 21px in this column
    if "\n" in title:
        title_lines = title.split("\n")
    else:
        title_lines = textwrap.wrap(title, TITLE_WRAP) or [title]
    fig.text(ML, 0.884, "\n".join(title_lines), fontsize=21, color=T.INK,
             family=SERIF, fontweight="semibold", va="top",
             linespacing=1.28)
    # Body drops when the claim needs a third line, so a long headline
    # costs vertical space rather than legibility.
    body_top = 0.20 if len(title_lines) <= 2 else 0.17
    if subtitle:
        sub_y = 0.884 - 0.052 * len(title_lines) - 0.02
        fig.text(ML, sub_y, subtitle, fontsize=12.5, color=T.INK_SOFT,
                 family=SERIF, va="top")
    fig.text(MR, 0.884, number, fontsize=44, color=hue, family=MONO,
             fontweight="medium", ha="right", va="top")
    fig.text(MR, 0.796, number_label, fontsize=10.5, color=T.INK_SOFT,
             family=MONO, ha="right", va="top")

    # Bar body
    ax = fig.add_axes([ML, body_top, MR - ML, 0.54])
    ax.set_facecolor(T.PAPER)
    labels = [b[0] for b in bars]
    values = [b[1] for b in bars]
    colors = [hue if lb == highlight else T.RULE for lb in labels]
    xs = range(len(bars))
    ax.bar(xs, values, color=colors, width=0.62, zorder=3)
    if baseline is not None:
        ax.axhline(baseline, color=T.INK_SOFT, lw=1.1, ls="--", zorder=4)
        ax.text(-0.45, baseline, f" {baseline_label}", fontsize=9.5,
                color=T.INK_SOFT, family=MONO, va="bottom")
    for i, (lb, v) in enumerate(bars):
        if lb == highlight:
            ax.text(i, v, f"{v:g}", fontsize=12, color=hue,
                    family=MONO, fontweight="semibold",
                    ha="center", va="bottom")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=9.5, family=MONO, color=T.INK_SOFT)
    ax.tick_params(axis="y", labelsize=9.5, colors=T.INK_SOFT, length=0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(T.INK)
    ax.grid(True, axis="y", color=T.RULE, lw=0.7, zorder=0)
    for tick in ax.get_yticklabels():
        tick.set_family(MONO)
    if unit_note:
        ax.set_ylabel(unit_note, fontsize=10, family=MONO,
                      color=T.INK_SOFT)

    # Footer: named sources + house URL. This line is the citation.
    fig.add_artist(plt.Line2D([ML, MR], [0.115, 0.115], color=T.INK,
                              lw=1.4, transform=fig.transFigure))
    fig.text(ML, 0.095, f"Sources: {sources}", fontsize=10,
             color=T.INK_SOFT, family=MONO, va="top")
    fig.text(MR, 0.095, SITE_URL_DISPLAY, fontsize=10, color=T.INK_SOFT,
             family=MONO, ha="right", va="top")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=100, facecolor=T.PAPER)
    plt.close(fig)
    print(f"citable: {out_path}")
    return out_path


if __name__ == "__main__":
    # Demo with the published fires-spotlight numbers (2026-07-25).
    render(
        ROOT / "briefs" / "citable-demo.png",
        title="Spain, France, and the UK each set their highest\nfire week in the 15-year satellite record",
        number="8.1x",
        number_label="Spain vs its 2012-25 same-week mean",
        bars=[("Spain", 8.1), ("France", 7.6), ("United Kingdom", 3.3)],
        highlight="Spain",
        baseline=1.0, baseline_label="same-week mean 2012-25",
        attribution="non_enso",
        sources="NASA FIRMS SNPP active fires, wk Jul 19-25 · retrieved 2026-07-25",
        unit_note="multiple of same-week mean",
    )
