"""
Analog tracker: plot ONI trajectories for three reference El Niño events
from a common calendar start (March 1 of develop year), with the current
2026 trajectory overlaid.

Plotted using the central month of each 3-month season for x-axis position.
Visual gut check, not a quantitative forecast.
"""

import csv
import os
import matplotlib.pyplot as plt
from pathlib import Path

# Map season codes to month-from-March-1 (using the central month).
# DJF center = January (so previous year). JFM = February, FMA = March,
# MAM = April, ..., NDJ = December.
SEASON_TO_MONTH_OFFSET = {
    "DJF": -2,   # central month Jan = 2 months before March of develop year? No.
    # Recompute cleanly: the trajectory we plot starts March 1 of develop year.
    # Central month of MAM is April -> month_offset = 1
    # JJA -> Jul = 4
    # SON -> Oct = 7
    # NDJ -> Dec = 9
    # We also want to show DJF and beyond as the next year (months 10, 11, 12...).
}

# Cleaner mapping: define which (year_offset, central_month) each season
# corresponds to relative to develop year (year_offset=0 means develop year).
SEASON_DEF = {
    # "DJF" centered on Jan = year_offset 0, month 1 (this is develop year DJF: Jan)
    # But "DJF 2015" in the table means Dec 2014, Jan 2015, Feb 2015 - so it's
    # "DJF of the develop year" with central month = January of develop year.
    "DJF": (0, 1),
    "JFM": (0, 2),
    "FMA": (0, 3),
    "MAM": (0, 4),
    "AMJ": (0, 5),
    "MJJ": (0, 6),
    "JJA": (0, 7),
    "JAS": (0, 8),
    "ASO": (0, 9),
    "SON": (0, 10),
    "OND": (0, 11),
    "NDJ": (0, 12),
}

CSV_PATH = Path(__file__).parent / "data" / "oni_historical.csv"


def months_since_march1(record_year: int, develop_year: int, season: str) -> int:
    """
    Months elapsed since March 1 of develop year.
    record_year: the year in the CSV row (could be develop_year or develop_year+1)
    """
    yo, mo = SEASON_DEF[season]
    # If row's year equals develop_year, we're in year 0; otherwise year 1
    if record_year == develop_year:
        absolute_month = mo            # month 1..12 of develop year
    else:
        absolute_month = mo + 12       # month 13..24 of post-develop year
    return absolute_month - 3          # March 1 = 0


def load_trajectories():
    """Return dict: develop_year -> list of (months_since_mar1, oni)."""
    out = {}
    # The CSV stores develop_year for each row. Recover the actual year
    # from develop_year (rows in develop year and post-develop year).
    # We treat the develop_year column as a label indicating which event the
    # row belongs to; the actual record year is develop_year for in-year
    # seasons (DJF=Jan-Feb of develop_year, ..., NDJ=Nov-Jan); but rows
    # labeled (develop_year+1) are explicit in the CSV. So we infer from
    # the CSV row label `develop_year` directly.
    rows = []
    with open(CSV_PATH) as f:
        # Skip leading comment lines (start with '#')
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    import io
    for row in csv.DictReader(io.StringIO("".join(lines))):
        rows.append(row)

    # We need to know which "event" each row belongs to. Group by event.
    # Convention in the CSV: rows labeled 1997 belong to 1997-98 event,
    # rows labeled 1998 belong to 1997-98 event, etc.
    event_for_row = {}
    for r in rows:
        y = int(r["develop_year"])
        # Define event = first year of the develop-pair
        if y in (1997, 2015, 2023, 2025, 2026):
            event_for_row[(y, r["season"])] = y
        elif y in (1998, 2016, 2024):
            event_for_row[(y, r["season"])] = y - 1
        # 2025 has no decay-year rows; trajectory ends at NDJ (month 9).
        # 2026 has no follow-up rows yet, fine.

    series = {}
    for r in rows:
        y = int(r["develop_year"])
        season = r["season"]
        oni = float(r["oni"])
        event = event_for_row.get((y, season))
        if event is None:
            continue
        m = months_since_march1(record_year=y, develop_year=event, season=season)
        series.setdefault(event, []).append((m, oni))

    for event in series:
        series[event].sort()
    return series


def plot(out_path: str):
    series = load_trajectories()
    fig, ax = plt.subplots(figsize=(10, 6))

    style = {
        1997: {"color": "#c92020", "label": "1997-98 (super, peak 2.4)", "lw": 2.0},
        2015: {"color": "#7d2bb0", "label": "2015-16 (super, peak 2.8)", "lw": 2.0},
        2023: {"color": "#1f6fa6", "label": "2023-24 (recent super, peak 2.1)", "lw": 2.0},
        2025: {"color": "#6b8e8a", "label": "2025-26 (La Niña, peak -0.5)",
               "lw": 1.5, "linestyle": "--"},
        2026: {"color": "#000000", "label": "2026-27 (current)", "lw": 2.5,
               "marker": "o", "ms": 6},
    }

    for event in [1997, 2015, 2023, 2025, 2026]:
        if event not in series:
            continue
        xs = [pt[0] for pt in series[event]]
        ys = [pt[1] for pt in series[event]]
        s = style[event]
        kwargs = {"color": s["color"], "label": s["label"], "linewidth": s["lw"]}
        if "marker" in s:
            kwargs["marker"] = s["marker"]
            kwargs["markersize"] = s["ms"]
        if "linestyle" in s:
            kwargs["linestyle"] = s["linestyle"]
        ax.plot(xs, ys, **kwargs)

    # Bucket reference lines
    for y, lbl in [(1.0, "moderate"), (1.5, "strong"), (2.0, "super"), (2.5, "1997/2015")]:
        ax.axhline(y, color="grey", linestyle="--", alpha=0.4, linewidth=0.8)
        ax.text(20, y + 0.04, lbl, fontsize=8, color="grey")

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlim(-3, 14)
    ax.set_ylim(-1.0, 3.2)
    ax.set_xlabel("Months since March 1 of develop year")
    ax.set_ylabel("Niño 3.4 ONI (traditional, °C)")
    ax.set_title(
        "Analog tracker: 2026-27 vs reference El Niño events\n"
        "ONI 3-month running mean, ERSST.v5, 1991-2020 climatology"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)

    # Mark current position (Apr 25, 2026 = roughly month 1.8 since Mar 1)
    ax.axvline(1.8, color="black", linestyle=":", alpha=0.5, linewidth=0.8)
    ax.annotate("today\n(Apr 25)", xy=(1.8, -0.85), fontsize=8, color="black",
                ha="center")

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    plot(str(Path(__file__).parent / "briefs" / "2026-04-25" / "analog.png"))
