#!/usr/bin/env python3
"""A rough motion test: does animating the overtaking carry the argument?

CPO'S BRIEF NAMED THE ANALOG CHART AND DESCRIBED THIS ONE. Their words
were "the analog chart, 2026 climbing past 1997's October peak three
months early". Measured before building: on ONI, which is what analog.py
draws, 2026 is at 1.39 against 1997's 2.37. It has not overtaken
anything and will not for months. The overtaking they describe is in
ocean heat content: +3.20 in August against 1997's +2.56 October peak.

Their REASONING picked the right object, "the only thing we publish
where the overtaking IS the claim", and their own test for rejecting a
chart, "animating a rank adds motion without information", is exactly
what animating the ONI line would have been: a line climbing toward
something it does not reach. So this builds the chart their argument
selects rather than the one their sentence named.

THE TWO CONSTRAINTS ARE THEIRS AND BOTH ARE STRUCTURAL:

  1. The analogs are complete before 2026 moves. A comparative claim
     needs the comparison on screen first, so frame 0 is already a
     finished chart and the motion is one line arriving into it.
  2. The final frame stands alone as a still. An animation on X is
     watched once and then screenshotted, so it rests on a frame that
     carries the legend, the annotation and the crossing. Held for a
     third of the run time.

WHAT THIS IS NOT. Rough matplotlib, no design treatment, and it should
be judged on whether motion adds information rather than on how it
looks. If the answer is yes, VD sets the treatment and it becomes a
design problem then.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
       "Oct", "Nov", "Dec", "Jan", "Feb"]


def dev(ser, y0):
    """A development year: January through February of the next, 14 months.

    Same slice as run_brief.chart_heat. A calendar year cuts 1997 off at
    December and hides its turn, which is half of what makes the curve
    worth drawing.
    """
    out = []
    for i in range(14):
        y, m = (y0, i + 1) if i < 12 else (y0 + 1, i - 11)
        v = ser.get(f"{y}-{m:02d}")
        if v is None:
            break
        out.append((i, v))
    return out


def build(out_path="design/heat_overtaking.gif", fps=4):
    # 4fps, ~250ms a month. The first render ran at 12 and the whole thing
    # was over in 1.8 seconds with 0.56s of actual motion, which would have
    # had Kristjan judging the frame rate rather than the idea. Rough is
    # the brief; illegible is a different answer to a different question.
    #
    # Pillow merges identical consecutive frames and SUMS their durations,
    # so the opening beat and the hold survive as one long frame each
    # rather than being silently dropped. Worth knowing before trusting a
    # frame count: 22 frames in, 8 in the file, and the timing is right.
    snap = sorted((ROOT / "snapshots").glob("*.json"))[-1]
    ser = json.loads(snap.read_text())["physical_state"]["heat_content_series"]

    cur = dev(ser, 2026)
    peers = {1997: dev(ser, 1997), 2015: dev(ser, 2015), 2023: dev(ser, 2023)}
    peak97 = max(v for _, v in peers[1997])
    peak97_i = max(peers[1997], key=lambda p: p[1])[0]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.patch.set_facecolor(T.PAPER)
    ax.set_facecolor(T.PAPER)

    # The months 2026 has not reached, shaded and named. chart_heat's rule
    # and it matters more in motion: a line that stops because the DATA
    # stops looks exactly like a line that stops because the VALUE fell,
    # and it would mislead in the alarming direction.
    ax.axvspan(len(cur) - 1, 13, color=T.PAPER_SUNK, alpha=.75, zorder=0)
    ax.text((len(cur) - 1 + 13) / 2, -0.42, "2026 has not reached these months",
            ha="center", fontsize=8, color=T.INK_FAINT, zorder=1)

    # CONSTRAINT 1: the analogs are complete in frame 0.
    for y, style in ((1997, "--"), (2015, "-"), (2023, ":")):
        pts = peers[y]
        ax.plot([i for i, _ in pts], [v for _, v in pts], style,
                color=T.INK_SOFT if y == 1997 else T.INK_FAINT,
                lw=1.5 if y == 1997 else 1.1, zorder=2,
                label=f"{y}-{str(y + 1)[2:]}"
                      f"{' (second year)' if y == 2015 else ''}"
                      f"  peak {max(v for _, v in pts):+.2f}")
    ax.plot([peak97_i], [peak97], "o", ms=6, color=T.INK_SOFT, zorder=3)
    ax.annotate(f"1997 peaks here, {MON[peak97_i]}", (peak97_i, peak97),
                textcoords="offset points", xytext=(6, -14),
                fontsize=8.5, color=T.INK_SOFT)
    ax.axhline(peak97, color=T.INK_SOFT, lw=.8, ls=(0, (2, 3)), zorder=1)

    line, = ax.plot([], [], "-", color=T.NINO, lw=2.6, zorder=4,
                    label="2026-27 (current)")
    head, = ax.plot([], [], "o", ms=7, mfc=T.PAPER, mec=T.NINO, mew=2, zorder=5)
    # PLACED, NOT OFFSET, after two failed attempts at hanging it off the
    # crossing point. Above-right is where the curve climbs; below-left is
    # where it crosses the dotted rule and the Jun-Jul segment. The crossing
    # has no clear space around it in either direction, because the thing
    # that makes it a crossing is that two lines are there.
    #
    # x 2.6 to 6.5 above y 3.05 is empty in every frame: 2026 does not
    # exceed 2.99 before August and the analogs never come near it. The
    # dotted rule and "1997 peaks here" already carry the geometry, so this
    # only has to name what happened.
    cross = ax.text(2.6, 3.16, "", fontsize=9.5, color=T.NINO,
                    fontweight="bold", zorder=6)

    ax.set_xlim(-.4, 13.4)
    ax.set_ylim(-.6, 3.45)
    ax.set_xticks(range(14))
    ax.set_xticklabels(MON, fontsize=8.5, color=T.INK_FAINT)
    ax.set_ylabel("Ocean heat content, 0-300 m, °C anomaly", fontsize=9,
                  color=T.INK_SOFT)
    ax.tick_params(axis="y", labelsize=8.5, colors=T.INK_FAINT)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(T.RULE)
    ax.grid(axis="y", color=T.RULE, lw=.6, alpha=.6, zorder=0)
    ax.set_title("2026 passes 1997's peak three months earlier in its season",
                 fontsize=12.5, color=T.INK, loc="left", pad=12)
    leg = ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    for t in leg.get_texts():
        t.set_color(T.INK_SOFT)
    fig.tight_layout()

    # CONSTRAINT 2: the run rests on a frame that stands alone. A third of
    # the frames are the finished chart, so a screenshot taken at any point
    # after the motion ends is the still we would have drawn by hand.
    grow = list(range(1, len(cur) + 1))
    hold = [len(cur)] * max(8, len(grow) // 2)
    frames = [1] * 6 + grow + hold          # a beat on the comparison first

    def draw(k):
        pts = cur[:k]
        line.set_data([i for i, _ in pts], [v for _, v in pts])
        if pts:
            head.set_data([pts[-1][0]], [pts[-1][1]])
        over = [p for p in pts if p[1] > peak97]
        if over:
            i, _ = over[0]
            # SHORT ON PURPOSE. The full sentence ran to x 9 and the
            # August marker sits at (7, 3.20), so the words ran through
            # the head of the very line they describe. The title already
            # says "three months earlier in its season"; repeating it here
            # buys a collision and no information.
            cross.set_text(f"passes 1997's peak in {MON[i]}")
        else:
            cross.set_text("")
        return line, head, cross

    anim = FuncAnimation(fig, draw, frames=frames, interval=1000 / fps,
                         blit=False)
    out = ROOT / out_path
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out, cur, peak97, peak97_i


if __name__ == "__main__":
    out, cur, peak97, peak97_i = build()
    over = [p for p in cur if p[1] > peak97]
    print("wrote %s (%.0f KB)" % (out, out.stat().st_size / 1024))
    print("  2026 months observed : %d (to %s)" % (len(cur), MON[cur[-1][0]]))
    print("  2026 latest          : %+.2f" % cur[-1][1])
    print("  1997 peak            : %+.2f in %s" % (peak97, MON[peak97_i]))
    if over:
        print("  crosses 1997's peak  : %s, %d months earlier in the season"
              % (MON[over[0][0]], peak97_i - over[0][0]))
    else:
        print("  NEVER CROSSES: the animation has no overtaking to show.")
