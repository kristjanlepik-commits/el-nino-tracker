"""ONI against seasonal ACE, both basins, satellite era.

Analysis chart, not a published figure. If this becomes a page, design
owns the final rendering per D-030; this exists so the asymmetry is
visible while we decide.

The point of the chart is that the two basins slope in OPPOSITE
directions against the same x axis, so both panels share it.
"""
import glob, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statistics as st
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T

for _pat in ("*.ttf", "*.otf"):
    for _f in glob.glob(str(ROOT / "assets" / "fonts" / _pat)):
        try:
            font_manager.fontManager.addfont(_f)
        except Exception:
            pass
if T.MONO_FAMILY in {f.name for f in font_manager.fontManager.ttflist}:
    plt.rcParams["font.family"] = T.MONO_FAMILY

SAT = 1966
d = json.load(open(ROOT / "data" / "hurricanes.json"))

COL = {"El Nino": T.WARM, "Neutral": T.INK_FAINT, "La Nina": T.COLD}
def cls(o):
    return "El Nino" if o >= 0.5 else ("La Nina" if o <= -0.5 else "Neutral")

fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.9), sharex=True,
                         facecolor=T.PAPER)
panels = [("atlantic", "ATLANTIC", axes[0]),
          ("east_pacific", "EAST PACIFIC", axes[1])]

for basin, label, ax in panels:
    rows = [r for r in d["basins"][basin]["seasons"]
            if r["year"] >= SAT and r["oni_aso"] is not None]
    g = {}
    for r in rows:
        g.setdefault(cls(r["oni_aso"]), []).append(r)

    ax.set_facecolor(T.PAPER)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(T.RULE)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(T.RULE)
    ax.tick_params(colors=T.INK_FAINT, labelsize=8.5, length=3)
    ax.grid(axis="y", color=T.RULE, lw=0.6, alpha=0.55)
    ax.set_axisbelow(True)

    # the +-0.5 El Nino / La Nina thresholds
    for x in (-0.5, 0.5):
        ax.axvline(x, color=T.RULE, lw=0.9, ls=(0, (2, 3)), zorder=1)

    for state in ("Neutral", "La Nina", "El Nino"):
        v = g.get(state, [])
        ax.scatter([r["oni_aso"] for r in v], [r["ace"] for r in v],
                   s=46, c=COL[state], alpha=0.82, zorder=3,
                   edgecolors=T.PAPER, linewidths=0.8, label=None)

    # group mean, drawn as a bar across that state's ONI range
    for state, x0, x1 in (("La Nina", -2.3, -0.5), ("Neutral", -0.5, 0.5),
                          ("El Nino", 0.5, 2.7)):
        v = g.get(state, [])
        if not v:
            continue
        m = st.mean(r["ace"] for r in v)
        ax.plot([x0, x1], [m, m], color=COL[state], lw=2.6, alpha=0.95, zorder=4)
        ax.text(x1 - 0.05, m, f" {m:.0f}", color=COL[state], fontsize=9.5,
                fontweight="bold", va="bottom", ha="right", zorder=5)

    en = [r["ace"] for r in g["El Nino"]]
    ln = [r["ace"] for r in g["La Nina"]]
    _, p = stats.mannwhitneyu(en, ln, alternative="two-sided")
    ratio = st.mean(en) / st.mean(ln)
    rho, prho = stats.spearmanr([r["oni_aso"] for r in rows],
                                [r["ace"] for r in rows])

    ax.set_title(label, color=T.INK, fontsize=12, fontweight="bold",
                 loc="left", pad=13)
    ax.text(0, 1.015, f"El Nino mean is {ratio:.2f}x the La Nina mean"
                      f"    p = {p:.3f}    Spearman {rho:+.2f}",
            transform=ax.transAxes, color=T.INK_SOFT, fontsize=8.8, va="bottom")

axes[0].set_ylabel("Seasonal ACE  (10$^4$ kt$^2$)", color=T.INK_FAINT, fontsize=9)

# shared band labels along the bottom
for ax in axes:
    ax.set_xlim(-2.4, 2.8)
for ax in axes:
    for state, x in (("La Nina", -1.45), ("Neutral", 0.0), ("El Nino", 1.65)):
        ax.text(x, 0.022, state.upper(), transform=ax.get_xaxis_transform(),
                color=COL[state], fontsize=8.0, fontweight="bold", ha="center",
                alpha=0.85, zorder=2)
fig.text(0.525, 0.105, "ONI, Aug-Sep-Oct", color=T.INK_FAINT, fontsize=9.2,
         ha="center")

fig.suptitle("El Nino suppresses Atlantic hurricanes and feeds east Pacific ones",
             color=T.INK, fontsize=15.5, fontweight="bold", x=0.055, ha="left",
             y=0.975)
fig.text(0.055, 0.925,
         "Every season 1966-2025, one dot each. Bars are the mean for each ENSO state. "
         "Same x axis, opposite slopes.",
         color=T.INK_SOFT, fontsize=9.6, ha="left")
fig.text(0.055, 0.018,
         "Accumulated Cyclone Energy from NOAA HURDAT2 (2026-02-27 release), summed over "
         "6-hourly observations at or above 34 kt while tropical.\n"
         "Satellite era only: earlier seasons undercount storms that stayed at sea. "
         "Basin activity, not landfall.\n"
         "Note the y axes differ: the east Pacific runs higher in absolute ACE. Compare the slope within each panel, not the heights across them.   The Long Swell",
         color=T.INK_FAINT, fontsize=7.8, ha="left", va="bottom")

fig.subplots_adjust(top=0.845, bottom=0.185, left=0.075, right=0.975, wspace=0.16)
out = Path(sys.argv[1] if len(sys.argv) > 1 else "hurricane_enso.png")
fig.savefig(out, dpi=170, facecolor=T.PAPER)
print(f"  wrote {out}")
