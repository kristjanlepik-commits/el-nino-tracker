"""Rolling 14-day CWWA accumulation rate, 2026 against the analogs.

Analysis chart, not a published figure. The analog chart shows the LEVEL of
wind forcing; this shows its SLOPE, which is what a fade looks like before
the level shows it. The two horizontal lines are the monitoring rule set
2026-09-13: below 4 per day is worth a mention, below 2 is the fade signal.
"""
import glob, json, sys
from datetime import date
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T

for _pat in ("*.ttf", "*.otf"):
    for _f in glob.glob(str(ROOT / "assets" / "fonts" / _pat)):
        try: font_manager.fontManager.addfont(_f)
        except Exception: pass
if T.MONO_FAMILY in {f.name for f in font_manager.fontManager.ttflist}:
    plt.rcParams["font.family"] = T.MONO_FAMILY

W = 14
w = json.load(open(ROOT / ".fetch_cache" / "era5_wwe_last_good.json"))["payload"]
series = {"2026": w["cwwa_series"], **w["cwwa_analogs"]}

def rolling_rate(pairs):
    pts = sorted(pairs)
    out = []
    for i in range(W, len(pts)):
        d = date.fromisoformat(pts[i][0])
        doy = (d - date(d.year, 3, 1)).days
        out.append((doy, (pts[i][1] - pts[i - W][1]) / W))
    return out

STYLE = {"1997": dict(color=T.INK_SOFT, ls=(0, (4, 3)), lw=1.5, label="1997"),
         "2015": dict(color=T.INK_SOFT, ls="-", lw=1.3, label="2015 (second year)"),
         "2023": dict(color=T.INK_FAINT, ls=(0, (1, 3)), lw=1.2, label="2023"),
         "2025": dict(color=T.INK_FAINT, ls=(0, (3, 1, 1, 1)), lw=1.0, label="2025 (La Nina)"),
         "2026": dict(color=T.NINO, ls="-", lw=2.6, label="2026 (current)")}

fig, ax = plt.subplots(figsize=(12.4, 5.6), facecolor=T.PAPER)
ax.set_facecolor(T.PAPER)
for s in ax.spines.values(): s.set_visible(False)
for side in ("bottom", "left"):
    ax.spines[side].set_visible(True); ax.spines[side].set_color(T.RULE)
ax.tick_params(colors=T.INK_FAINT, labelsize=8.5, length=3)
ax.grid(axis="y", color=T.RULE, lw=0.6, alpha=0.55); ax.set_axisbelow(True)

# the monitoring rule
ax.axhspan(-1, 2, color=T.WARM, alpha=0.06, zorder=0)
ax.axhline(4, color=T.INK_FAINT, lw=0.9, ls=(0, (2, 3)), zorder=1)
ax.axhline(2, color=T.WARM, lw=0.9, ls=(0, (2, 3)), zorder=1)
ax.text(17, 4.15, "watch line 4", color=T.INK_FAINT, fontsize=8, va="bottom")
ax.text(17, 2.15, "fade signal 2", color=T.WARM, fontsize=8, va="bottom")

for y in ("2025", "2023", "2015", "1997", "2026"):
    r = rolling_rate(series[y])
    if not r: continue
    ax.plot([a for a, _ in r], [b for _, b in r], zorder=3 if y != "2026" else 5, **STYLE[y])
    if y == "2026":
        ax.scatter([r[-1][0]], [r[-1][1]], s=46, color=T.NINO, zorder=6, edgecolors=T.PAPER, linewidths=0.8)
        ax.annotate(f"{r[-1][1]:+.1f}/day", (r[-1][0], r[-1][1]), xytext=(8, 6),
                    textcoords="offset points", color=T.NINO, fontsize=10, fontweight="bold")

# 1997 at the same date, for the eye
r97 = rolling_rate(series["1997"]); r26 = rolling_rate(series["2026"])
cur_doy = r26[-1][0]
v97 = next((b for a, b in r97 if a >= cur_doy), None)
if v97 is not None:
    ax.scatter([cur_doy], [v97], s=34, color=T.INK_SOFT, zorder=6, edgecolors=T.PAPER, linewidths=0.8)
    ax.annotate(f"1997 {v97:+.1f}", (cur_doy, v97), xytext=(8, -12), textcoords="offset points",
                color=T.INK_SOFT, fontsize=9)

ax.axvline(cur_doy, color=T.RULE, lw=0.8, ls=(0, (1, 2)), zorder=1)
months = [(0, "Mar"), (31, "Apr"), (61, "May"), (92, "Jun"), (122, "Jul"), (153, "Aug"),
          (184, "Sep"), (214, "Oct"), (245, "Nov"), (275, "Dec")]
ax.set_xticks([m for m, _ in months]); ax.set_xticklabels([l for _, l in months])
ax.set_xlim(W, 306); ax.set_ylim(-0.6, 14)
ax.set_ylabel("14-day CWWA rate  (m/s·days per day)", color=T.INK_FAINT, fontsize=9)
ax.legend(loc="upper left", frameon=False, fontsize=8.6, labelcolor=T.INK_SOFT)

fig.suptitle("How fast the wind forcing is arriving, 2026 against the analogs",
             color=T.INK, fontsize=15, fontweight="bold", x=0.055, ha="left", y=0.975)
fig.text(0.055, 0.915, "Rolling 14-day accumulation rate of the cumulative westerly wind anomaly. "
         "The level says what has been delivered; the slope says whether delivery is stalling.",
         color=T.INK_SOFT, fontsize=9.4, ha="left")
fig.text(0.055, 0.02, f"ERA5 850 hPa zonal wind, 5N-5S 130E-150W, positive anomalies vs 1991-2020 "
         f"integrated from 1 March. 2026 to {sorted(series['2026'])[-1][0]}. "
         f"Shaded band is the fade region.  The Long Swell",
         color=T.INK_FAINT, fontsize=7.8, ha="left")
fig.subplots_adjust(top=0.84, bottom=0.12, left=0.075, right=0.975)
out = Path(sys.argv[1] if len(sys.argv) > 1 else "cwwa_rate.png")
fig.savefig(out, dpi=170, facecolor=T.PAPER)
print(f"  wrote {out}")
