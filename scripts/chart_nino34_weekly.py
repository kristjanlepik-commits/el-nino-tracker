"""Every year's weekly Nino 3.4 anomaly since 1982, 2026 on top.

CPC's weekly OISST v2.1 series (wksst9120.for), the file the brief already
quotes for "Nino 3.4 weekly", on its fixed 1991-2020 base. Built 2026-10-04
for the 10-05 Editor's note, after the week of 23 September (+3.1) passed
the series' previous high (+3.0, 18 Nov 2015).

The data is fetched from CPC, not from Climate Reanalyzer, whose daily file
refuses automated requests. A fixed base flatters recent years slightly as
the ocean warms; the chart says so and gives the RONI value beside it.

    .venv/bin/python scripts/chart_nino34_weekly.py docs/<name>.png
"""
import glob, re, sys
from datetime import datetime, date
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T
from fetchers._common import http_get
for pat in ("*.ttf", "*.otf"):
    for f in glob.glob(str(ROOT / "assets" / "fonts" / pat)):
        try: font_manager.fontManager.addfont(f)
        except Exception: pass
if T.MONO_FAMILY in {f.name for f in font_manager.fontManager.ttflist}:
    plt.rcParams["font.family"] = T.MONO_FAMILY

TEXT = http_get("https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for", timeout=60).text
series = {}
for line in TEXT.splitlines():
    m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)", line)
    if not m: continue
    nums = re.findall(r"-?\d+\.\d", m.group(2))
    if len(nums) < 8: continue
    d = datetime.strptime(m.group(1), "%d%b%Y").date()
    series.setdefault(d.year, []).append(((d - date(d.year, 1, 1)).days, float(nums[5])))

prev = max(((v, y, x) for y, pts in series.items() if 1982 <= y < 2026 for x, v in pts))
last_x, last_v = series[2026][-1]
last_d = date(2026, 1, 1).toordinal() + last_x

fig, ax = plt.subplots(figsize=(11, 6.4), facecolor=T.PAPER)
ax.set_facecolor(T.PAPER)
for s in ax.spines.values(): s.set_visible(False)
ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(T.RULE)
ax.tick_params(colors=T.INK_FAINT, labelsize=9, length=0)
ax.grid(axis="y", color=T.RULE, lw=0.6, alpha=0.6); ax.set_axisbelow(True)
ax.axhline(0, color=T.INK_SOFT, lw=0.8)

for y, pts in series.items():
    if 1982 <= y <= 2025 and y not in (1997, 2015, 2023):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=T.INK_FAINT, lw=0.7, alpha=0.35, zorder=1)

ANALOG = {1997: (0, (4, 3)), 2015: "-", 2023: (0, (1, 2.2))}
handles = []
for y, ls in ANALOG.items():
    pts = series[y]
    pv = max(p[1] for p in pts)
    h, = ax.plot([p[0] for p in pts], [p[1] for p in pts], color=T.INK_SOFT, lw=1.5, ls=ls, zorder=3,
                 label=f"{y}  (peak {pv:+.1f})")
    handles.append(h)
ax.legend(handles=handles, loc="upper left", ncol=3, frameon=False, fontsize=9,
          labelcolor=T.INK_SOFT, handlelength=2.6, columnspacing=1.8, borderaxespad=0.3)

pts = series[2026]
ax.plot([p[0] for p in pts], [p[1] for p in pts], color=T.NINO, lw=2.8, zorder=5)
ax.scatter([last_x], [last_v], s=46, color=T.NINO, zorder=6, edgecolors=T.PAPER, linewidths=0.9)
ax.annotate(f"2026  {last_v:+.1f}", (last_x, last_v), xytext=(8, -4), textcoords="offset points",
            color=T.NINO, fontsize=11, fontweight="bold", zorder=7)

ax.axhline(prev[0], color=T.INK_FAINT, lw=0.8, ls=(0, (2, 3)), zorder=2)
ax.text(4, prev[0] + 0.05, f"previous highest week, {prev[0]:+.1f} (Nov {prev[1]})",
        color=T.INK_FAINT, fontsize=8.5, va="bottom")

starts = [(date(2026, m, 1) - date(2026, 1, 1)).days for m in range(1, 13)]
ax.set_xticks(starts); ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_xlim(0, 365); ax.set_ylim(-2.9, 3.75)
ax.set_ylabel("°C above 1991-2020 average", color=T.INK_FAINT, fontsize=9)

fig.suptitle("Niño 3.4 is further above normal than in any week since 1981", color=T.INK, fontsize=16,
             fontweight="bold", x=0.06, ha="left", y=0.965)
fig.text(0.06, 0.895, "Weekly sea-surface temperature anomaly, central equatorial Pacific. Every year since 1982 in grey;\n"
         "the three strongest recent El Niños named. 2026 reached +3.1 in the week of 23 September, two months before the usual peak.",
         color=T.INK_SOFT, fontsize=9.5, ha="left", va="top", linespacing=1.4)
fig.text(0.06, 0.02, "NOAA OISST v2.1 weekly Niño 3.4 (5N-5S, 170W-120W), CPC, fixed 1991-2020 base for every year. A fixed base flatters "
         "recent years slightly as the ocean warms;\nagainst the tropical-mean ocean (RONI) the same week is +2.2. Values are rounded to 0.1 by CPC.  The Long Swell",
         color=T.INK_FAINT, fontsize=7.6, ha="left", linespacing=1.35)
fig.subplots_adjust(top=0.8, bottom=0.12, left=0.07, right=0.97)
out = Path(sys.argv[1] if len(sys.argv) > 1 else "nino34_weekly.png")
fig.savefig(out, dpi=170, facecolor=T.PAPER)
print("wrote", out, "| previous record", prev, "| 2026 last", date.fromordinal(last_d), last_v)
