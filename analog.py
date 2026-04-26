"""
Analog tracker: plot ONI trajectories for three reference El Niño events
from a common calendar start (March 1 of develop year), with the current
2026 trajectory overlaid. Optional second panel for CWWA.

Plotted using the central month of each 3-month season for x-axis position.
Visual gut check, not a quantitative forecast.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt

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


DEVELOP_YEARS = (1997, 2015, 2023, 2025, 2026)
DECAY_YEARS = (1998, 2016, 2024)


def _event_for(year: int, season: str) -> int | None:
    if year in DEVELOP_YEARS:
        return year
    if year in DECAY_YEARS:
        return year - 1
    return None


def load_trajectories(live_oni_by_year: dict | None = None,
                      override_year: int | None = None):
    """Return dict: develop_year -> list of (months_since_mar1, oni).

    `live_oni_by_year` is dict[int year -> dict[season -> oni]] from CPC's
    oni.ascii.txt, used to override / extend the CSV rows for the current
    calendar year. Historical years stay frozen in the CSV. If
    `override_year` is given, only that year is overridden / extended.
    """
    rows = []
    with open(CSV_PATH) as f:
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    import io
    for row in csv.DictReader(io.StringIO("".join(lines))):
        rows.append(row)

    series: dict[int, list[tuple[int, float]]] = {}
    for r in rows:
        y = int(r["develop_year"])
        if override_year is not None and y == override_year and live_oni_by_year:
            # Skip CSV rows for the override year; we'll use live data instead.
            continue
        season = r["season"]
        event = _event_for(y, season)
        if event is None:
            continue
        m = months_since_march1(record_year=y, develop_year=event, season=season)
        series.setdefault(event, []).append((m, float(r["oni"])))

    if live_oni_by_year and override_year is not None:
        for season, oni in live_oni_by_year.get(override_year, {}).items():
            event = _event_for(override_year, season)
            if event is None:
                continue
            try:
                m = months_since_march1(record_year=override_year,
                                        develop_year=event, season=season)
            except KeyError:
                continue
            series.setdefault(event, []).append((m, float(oni)))

    for event in series:
        series[event] = sorted(set(series[event]))
    return series


STYLE = {
    1997: {"color": "#c92020", "label_oni": "1997-98 (super, peak 2.4)",
           "label_cwwa": "1997 develop year", "lw": 2.0},
    2015: {"color": "#7d2bb0", "label_oni": "2015-16 (super, peak 2.8)",
           "label_cwwa": "2015 develop year", "lw": 2.0},
    2023: {"color": "#1f6fa6", "label_oni": "2023-24 (recent super, peak 2.1)",
           "label_cwwa": "2023 develop year", "lw": 2.0},
    2025: {"color": "#6b8e8a", "label_oni": "2025-26 (La Niña, peak -0.5)",
           "label_cwwa": "2025 develop year (La Niña)",
           "lw": 1.5, "linestyle": "--"},
    2026: {"color": "#000000", "label_oni": "2026-27 (current)",
           "label_cwwa": "2026 develop year (current)", "lw": 2.5,
           "marker": "o", "ms": 6},
}


def _months_from_mar1_for_dateiso(date_iso: str, develop_year: int) -> float:
    """Fractional months elapsed since March 1 of develop_year."""
    d = date.fromisoformat(date_iso)
    days = (d - date(develop_year, 3, 1)).days
    return days / 30.44   # average days per month


def _plot_oni(ax, series):
    for event in [1997, 2015, 2023, 2025, 2026]:
        if event not in series:
            continue
        xs = [pt[0] for pt in series[event]]
        ys = [pt[1] for pt in series[event]]
        s = STYLE[event]
        kwargs = {"color": s["color"], "label": s["label_oni"], "linewidth": s["lw"]}
        if "marker" in s:
            kwargs["marker"] = s["marker"]
            kwargs["markersize"] = s["ms"]
        if "linestyle" in s:
            kwargs["linestyle"] = s["linestyle"]
        ax.plot(xs, ys, **kwargs)


def _plot_seas5_forecast(ax, per_lead, current_develop_year: int):
    """Overlay ECMWF SEAS5 ensemble median trajectory as a dashed forecast line.

    SEAS5 outputs monthly mean Niño 3.4 anomaly, which is a close-but-not-identical
    cousin of the 3-month-running-mean ONI used for the analog series. Treated as
    visually comparable; the caption flags the distinction.
    """
    if not per_lead:
        return
    xs, ys = [], []
    for entry in per_lead:
        cal = entry.get("calendar")
        med = entry.get("median")
        if cal is None or med is None:
            continue
        year, month = (int(x) for x in cal.split("-"))
        offset = (year - current_develop_year) * 12 + (month - 3)
        xs.append(offset)
        ys.append(med)
    if not xs:
        return

    ax.plot(xs, ys, color="#000000", linestyle="--", linewidth=1.6,
            marker="D", markersize=5,
            label=f"{current_develop_year}-{(current_develop_year + 1) % 100:02d} "
                  "SEAS5 forecast (median)")

    peak_idx = ys.index(max(ys))
    ax.annotate(
        f"+{ys[peak_idx]:.1f}°C ({per_lead[peak_idx]['calendar']})",
        xy=(xs[peak_idx], ys[peak_idx]),
        xytext=(10, 6), textcoords="offset points",
        fontsize=8.5, color="#222",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="#aaa", alpha=0.9),
    )

    for y, lbl in [(1.0, "moderate"), (1.5, "strong"), (2.0, "super"), (2.5, "1997/2015")]:
        ax.axhline(y, color="grey", linestyle="--", alpha=0.4, linewidth=0.8)
        ax.text(13, y + 0.04, lbl, fontsize=8, color="grey")

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlim(-3, 14)
    ax.set_ylim(-1.0, 3.2)
    ax.set_ylabel("Niño 3.4 ONI (traditional, °C)")
    ax.set_title(
        "Analog tracker: 2026-27 vs reference events\n"
        "Top: ONI 3-month running mean (ERSST.v5, 1991-2020 climo). "
        "Bottom: cumulative westerly wind anomaly (ERA5, 5N-5S, 130E-150W)."
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)


def _plot_cwwa(ax, current_series, analogs, current_develop_year):
    """Plot CWWA curves keyed by months-since-March-1.

    `current_series` is a list of (date_iso, value) for the current develop year.
    `analogs` is dict[year_int -> list[(date_iso, value)]] for reference years.
    """
    plotted_anything = False
    for yr, ser in (analogs or {}).items():
        if yr not in STYLE:
            continue
        xs = [_months_from_mar1_for_dateiso(d, yr) for d, _ in ser]
        ys = [v for _, v in ser]
        s = STYLE[yr]
        kwargs = {"color": s["color"], "label": s["label_cwwa"], "linewidth": s["lw"]}
        if "linestyle" in s:
            kwargs["linestyle"] = s["linestyle"]
        ax.plot(xs, ys, **kwargs)
        plotted_anything = True

    if current_series:
        xs = [_months_from_mar1_for_dateiso(d, current_develop_year)
              for d, _ in current_series]
        ys = [v for _, v in current_series]
        s = STYLE[2026]
        ax.plot(xs, ys, color=s["color"], label=s["label_cwwa"],
                linewidth=s["lw"], marker=s["marker"], markersize=s["ms"],
                markevery=max(1, len(xs) // 8))
        plotted_anything = True

    ax.set_xlim(-3, 14)
    if not plotted_anything:
        ax.text(0.5, 0.5, "CWWA data not available", transform=ax.transAxes,
                ha="center", va="center", fontsize=10, color="grey")
        return

    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Months since March 1 of develop year")
    ax.set_ylabel("CWWA (m/s · days)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)


def plot(out_path: str, cwwa_data: dict | None = None,
         seas5_per_lead: list | None = None,
         current_develop_year: int = 2026, today_offset: float | None = None,
         live_oni_by_year: dict | None = None):
    """Render the two-panel analog chart. If `cwwa_data` is supplied (with keys
    `cwwa_series` and `cwwa_analogs`), the bottom panel shows CWWA trajectories;
    otherwise it stays empty with a placeholder message. If `seas5_per_lead` is
    supplied, overlay the SEAS5 ensemble median as a dashed forecast on the ONI
    panel. If `live_oni_by_year` is supplied (CPC oni.ascii format,
    dict[year -> dict[season -> oni]]), the current develop-year ONI rows on
    the top panel are refreshed from that live data; historical rows stay
    sourced from the CSV."""
    series = load_trajectories(live_oni_by_year=live_oni_by_year,
                               override_year=current_develop_year)
    fig, (ax_oni, ax_cwwa) = plt.subplots(2, 1, figsize=(10, 9), sharex=True,
                                          gridspec_kw={"height_ratios": [3, 2]})
    _plot_oni(ax_oni, series)
    if seas5_per_lead:
        _plot_seas5_forecast(ax_oni, seas5_per_lead, current_develop_year)
    _plot_cwwa(ax_cwwa, (cwwa_data or {}).get("cwwa_series"),
               (cwwa_data or {}).get("cwwa_analogs"), current_develop_year)

    if today_offset is not None:
        for ax in (ax_oni, ax_cwwa):
            ax.axvline(today_offset, color="black", linestyle=":", alpha=0.5,
                       linewidth=0.8)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    plot(str(Path(__file__).parent / "briefs" / "2026-04-25" / "analog.png"))
