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


# Emphasis hierarchy (public-side styling): 2026 is the hero line; the analog
# years are reference-weight traces that recede so the reader's eye lands on
# 2026 first. `alpha` + `zorder` carry the weighting; line width reinforces it.
# This is the single biggest clarity lever the reference forecast charts use:
# one line you look at, the rest as faint context.
STYLE = {
    1997: {"color": "#c92020", "label_oni": "1997-98 (super, peak 2.4)",
           "label_cwwa": "1997 develop year", "lw": 1.6, "alpha": 0.55,
           "zorder": 2},
    2015: {"color": "#7d2bb0", "label_oni": "2015-16 (super, peak 2.8)",
           "label_cwwa": "2015 develop year", "lw": 1.6, "alpha": 0.55,
           "zorder": 2},
    2023: {"color": "#1f6fa6", "label_oni": "2023-24 (recent super, peak 2.1)",
           "label_cwwa": "2023 develop year", "lw": 1.6, "alpha": 0.55,
           "zorder": 2},
    2025: {"color": "#6b8e8a", "label_oni": "2025-26 (La Niña, peak -0.5)",
           "label_cwwa": "2025 develop year (La Niña)",
           "lw": 1.3, "linestyle": "--", "alpha": 0.45, "zorder": 1},
    2026: {"color": "#000000", "label_oni": "2026-27 (current)",
           "label_cwwa": "2026 develop year (current)", "lw": 2.8,
           "marker": "o", "ms": 6, "alpha": 1.0, "zorder": 5},
}

# ONI panel y-range. Top raised to 3.9 (from 3.2) so the CFSv2 longer-
# horizon extension peak is visible above the +2.5 record line; this
# matches the public chat's signed-off mock.
Y_TOP_ONI = 4.5   # raised 2026-07-06: July SEAS5 p95 reaches 4.28; a 3.9
                  # ceiling clipped the fan, the exact "adjust the y-axis"
                  # failure the CFSv2 chart tweets mocked NOAA for.
Y_BOT_ONI = -1.5

# Calendar x-axis. The internal coordinate stays months-since-March-1 of
# the develop year (so all existing trajectory math is untouched); these
# ticks just relabel it to calendar months, killing the mental arithmetic.
# Offsets: -3=Dec'25, 0=Mar'26, 3=Jun'26, 6=Sep'26, 9=Dec'26, 12=Mar'27.
_CALENDAR_XTICKS = [-3, 0, 3, 6, 9, 12]
_CALENDAR_XLABELS = ["Dec '25", "Mar '26", "Jun '26", "Sep '26",
                     "Dec '26", "Mar '27"]


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
        if "alpha" in s:
            kwargs["alpha"] = s["alpha"]
        if "zorder" in s:
            kwargs["zorder"] = s["zorder"]
        ax.plot(xs, ys, **kwargs)

    # ENSO category background bands. Above the +0.5 ONI threshold is El
    # Niño territory, below -0.5 is La Niña; the band between is neutral.
    # The red field deepens with intensity via stacked semi-transparent
    # overlays (each threshold adds another layer), giving "deeper in the
    # red = stronger" at a glance. Drawn first (low zorder) so trajectory
    # lines and gridlines sit on top. The +0.5 / -0.5 / intensity-step
    # thresholds are the standard ONI definition (methodology-side); the
    # tint colors and alphas are the public chat's design (ported from
    # their signed-off mock).
    ax.axhspan(0.5, Y_TOP_ONI, color="#d94327", alpha=0.05, zorder=0)
    ax.axhspan(1.5, Y_TOP_ONI, color="#d94327", alpha=0.05, zorder=0)
    ax.axhspan(2.0, Y_TOP_ONI, color="#d94327", alpha=0.06, zorder=0)
    ax.axhspan(Y_BOT_ONI, -0.5, color="#1f6fa6", alpha=0.08, zorder=0)
    ax.text(11.7, Y_TOP_ONI - 0.25, "EL NIÑO", ha="right", va="top",
            fontsize=10, color="#a8321c", fontweight="bold", alpha=0.6)
    ax.text(11.7, Y_BOT_ONI + 0.12, "LA NIÑA", ha="right", va="bottom",
            fontsize=10, color="#1f6fa6", fontweight="bold", alpha=0.6)

    # DJF 2026-27 peak-season target band (x ~ Dec/Jan/Feb).
    ax.axvspan(9, 11, color="#1f4068", alpha=0.05, zorder=0)
    ax.text(10, Y_BOT_ONI + 0.30, "DJF 2026-27\npeak target", ha="center",
            va="bottom", fontsize=8, color="#1f4068", alpha=0.75)

    # Static styling for the ONI panel. Always runs, independent of whether
    # SEAS5 data is overlaid (when SEAS5 is missing in CI, the panel must
    # still have a title, legend, threshold lines, and axis labels).
    for y, lbl in [(1.0, "moderate"), (1.5, "strong"), (2.0, "super"),
                   (2.5, "1997/2015 record")]:
        ax.axhline(y, color="grey", linestyle="--", alpha=0.4, linewidth=0.8)
        ax.text(-2.9, y + 0.05, lbl, fontsize=8, color="grey")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlim(-3, 12)
    ax.set_ylim(Y_BOT_ONI, Y_TOP_ONI)
    ax.set_ylabel("Niño 3.4 ONI (traditional, °C)")
    ax.set_title(
        "Analog tracker: 2026-27 vs reference events\n"
        "Top: ONI 3-month running mean (ERSST.v5, 1991-2020 climo). "
        "Bottom: cumulative westerly wind anomaly (ERA5, 5N-5S, 130E-150W)."
    )
    ax.grid(True, axis="y", alpha=0.18)
    ax.legend(loc="lower right", fontsize=9)


def _plot_seas5_forecast(ax, per_lead, current_develop_year: int):
    """Overlay ECMWF SEAS5 ensemble forecast as a fan: 5-95 and 25-75 bands plus
    median line. SEAS5 outputs monthly mean Niño 3.4 anomaly, which is a close-
    but-not-identical cousin of the 3-month-running-mean ONI on the analog
    series; the caption flags the distinction. Showing only the median would
    hide the spread that's the whole point of running a 51-member ensemble."""
    if not per_lead:
        return
    xs, med, p5, p25, p75, p95 = [], [], [], [], [], []
    for entry in per_lead:
        cal = entry.get("calendar")
        m = entry.get("median")
        if cal is None or m is None:
            continue
        year, month = (int(x) for x in cal.split("-"))
        offset = (year - current_develop_year) * 12 + (month - 3)
        xs.append(offset)
        med.append(m)
        p5.append(entry.get("p5", m))
        p25.append(entry.get("p25", m))
        p75.append(entry.get("p75", m))
        p95.append(entry.get("p95", m))
    if not xs:
        return

    label_year = f"{current_develop_year}-{(current_develop_year + 1) % 100:02d}"

    # Near-term fan: SEAS5's real 5-95 (outer, faint) and 25-75 (inner) bands.
    ax.fill_between(xs, p5, p95, color="#000000", alpha=0.10, linewidth=0,
                    zorder=3)
    ax.fill_between(xs, p25, p75, color="#000000", alpha=0.18, linewidth=0,
                    zorder=3)
    # Near-term median: dashed with diamond markers. The dashed style and
    # markers cue the higher-confidence, multi-member near-term piece; the
    # CFSv2 extension (drawn separately) continues this same black median
    # dotted and marker-less. One merged legend entry covers both segments.
    ax.plot(xs, med, color="#000000", linestyle="--", linewidth=1.8,
            marker="D", markersize=5, zorder=4,
            label=f"{label_year} forecast median + range "
                  f"(SEAS5 dashed; NMME-pool extension dotted)")

    # Refresh the legend so the forecast entry is picked up; the static
    # legend was already drawn by _plot_oni for the analog lines.
    ax.legend(loc="lower right", fontsize=9)
    # Return the SEAS5 endpoint so the CFSv2 extension connects continuously
    # from exactly where the SEAS5 fan ends (median + inner-band edges).
    return {"offset": xs[-1], "median": med[-1],
            "p25": p25[-1], "p75": p75[-1]}


def _plot_cfsv2_extension(ax, trajectory, current_develop_year: int,
                          seas5_end: dict | None):
    """Continue the single merged forecast fan past SEAS5's horizon, drawn
    as one continuous line: the SEAS5 near-term median (dashed, diamonds)
    hands off at its last lead to an extension segment that is DOTTED and
    marker-less. The dotted style cues "longer-horizon projection, softer."
    There is no separate legend entry and no distinct tint; this is one
    merged multi-model forecast, not a competing line.

    SEAS5's operational CDS product stops at 6 forecast months, so months
    past its horizon come from the NMME suite. As of methodology v1.9 the
    `trajectory` passed in is the equal-model-weight POOLED NMME per-month
    member pool (median + p25/p75 computed as weighted percentiles across
    all models' members, each model weighted equally). Pre-v1.9 caches fall
    back to CFSv2's own trajectory; the shape is identical either way.

    Band: single grey band from the trajectory's p25-p75, anchored to the
    SEAS5 inner-band edge at the hand-off. With the pooled trajectory this
    is a true mixture interquartile, wider than any single model's spread
    when the models disagree, which is exactly the uncertainty the
    extension should show.
    """
    if not trajectory or not seas5_end:
        return
    end_off = seas5_end["offset"]
    # CFSv2 months strictly beyond the SEAS5 horizon (Dec onward).
    ext = []
    for entry in trajectory:
        cal = entry.get("calendar")
        med = entry.get("median")
        if cal is None or med is None:
            continue
        year, month = (int(x) for x in cal.split("-"))
        offset = (year - current_develop_year) * 12 + (month - 3)
        if offset > end_off:
            ext.append((offset, med, entry.get("p25", med), entry.get("p75", med)))
    if not ext:
        return
    ext.sort(key=lambda p: p[0])
    # Prepend the SEAS5 endpoint so the dotted median and the band connect
    # continuously at November (no visual break, no double-counting Nov).
    xs = [end_off] + [p[0] for p in ext]
    ys = [seas5_end["median"]] + [p[1] for p in ext]
    lo = [seas5_end["p25"]] + [p[2] for p in ext]
    hi = [seas5_end["p75"]] + [p[3] for p in ext]
    # Single grey extension band (same black tint as the near-term fan), and
    # the dotted black median continuing the merged line. No separate label.
    ax.fill_between(xs, lo, hi, color="#000000", alpha=0.10, linewidth=0,
                    zorder=3)
    ax.plot(xs, ys, color="#000000", linestyle=":", linewidth=1.8, zorder=4)


def _plot_obs_to_forecast_connector(ax, obs_series, per_lead,
                                    current_develop_year: int):
    """Dotted line bridging the last observed 2026 ONI point to the first
    SEAS5 forecast lead. Observed ONI (CPC seasons) typically runs a couple
    of months behind the calendar, and the SEAS5 fan starts at its first
    lead month, leaving a visual gap. This connector spans it so the
    observed-to-forecast handoff reads as one continuous trajectory."""
    if not obs_series or not per_lead:
        return
    obs_end = obs_series[-1]   # (offset, value)
    first = per_lead[0]
    cal = first.get("calendar")
    med = first.get("median")
    if cal is None or med is None:
        return
    year, month = (int(x) for x in cal.split("-"))
    fan_start_offset = (year - current_develop_year) * 12 + (month - 3)
    # Only draw if there is an actual gap to bridge (fan starts after obs).
    if fan_start_offset <= obs_end[0]:
        return
    # Dotted, matching the DJF/CFSv2 extension tail, so dotted reads
    # consistently across the figure as "softer / bridged / projected."
    ax.plot([obs_end[0], fan_start_offset], [obs_end[1], med],
            color="black", linestyle=":", linewidth=1.4, alpha=0.7, zorder=4)


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
        if "alpha" in s:
            kwargs["alpha"] = s["alpha"]
        if "zorder" in s:
            kwargs["zorder"] = s["zorder"]
        ax.plot(xs, ys, **kwargs)
        plotted_anything = True

    if current_series:
        xs = [_months_from_mar1_for_dateiso(d, current_develop_year)
              for d, _ in current_series]
        ys = [v for _, v in current_series]
        s = STYLE[2026]
        ax.plot(xs, ys, color=s["color"], label=s["label_cwwa"],
                linewidth=s["lw"], marker=s["marker"], markersize=s["ms"],
                markevery=max(1, len(xs) // 8),
                alpha=s.get("alpha", 1.0), zorder=s.get("zorder", 5))
        plotted_anything = True

    ax.set_xlim(-3, 12)
    if not plotted_anything:
        ax.text(0.5, 0.5, "CWWA data not available", transform=ax.transAxes,
                ha="center", va="center", fontsize=10, color="grey")
        return

    ax.axhline(0, color="black", linewidth=0.6)
    # X-axis is relabeled to calendar months at the plot() level (shared
    # axis). No "months since March 1" label needed; the calendar ticks
    # are self-explanatory.
    ax.set_ylabel("CWWA (m/s · days)")
    ax.grid(True, axis="y", alpha=0.18)
    ax.legend(loc="upper left", fontsize=9)


def plot(out_path: str, cwwa_data: dict | None = None,
         seas5_per_lead: list | None = None,
         current_develop_year: int = 2026, today_offset: float | None = None,
         live_oni_by_year: dict | None = None,
         cfsv2_median: list | None = None):
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
    seas5_end = None
    if seas5_per_lead:
        seas5_end = _plot_seas5_forecast(ax_oni, seas5_per_lead,
                                         current_develop_year)
    if cfsv2_median:
        _plot_cfsv2_extension(ax_oni, cfsv2_median, current_develop_year,
                              seas5_end)

    # Dotted connector bridging the gap between where the 2026 observed ONI
    # line ends and where the SEAS5 forecast fan begins. The observed series
    # runs through the latest CPC ONI season; the fan starts at the first
    # SEAS5 lead month. Without this, the eye reads a break between the two.
    _plot_obs_to_forecast_connector(ax_oni, series.get(current_develop_year),
                                    seas5_per_lead, current_develop_year)

    _plot_cwwa(ax_cwwa, (cwwa_data or {}).get("cwwa_series"),
               (cwwa_data or {}).get("cwwa_analogs"), current_develop_year)

    if today_offset is not None:
        for ax in (ax_oni, ax_cwwa):
            ax.axvline(today_offset, color="black", linestyle=":", alpha=0.5,
                       linewidth=0.8)

    # Calendar x-axis: relabel the shared months-since-March-1 axis with
    # calendar months so the reader does not have to do the arithmetic.
    # Internal coordinates are unchanged; this is tick cosmetics only.
    ax_cwwa.set_xlim(-3, 12)
    ax_cwwa.set_xticks(_CALENDAR_XTICKS)
    ax_cwwa.set_xticklabels(_CALENDAR_XLABELS)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    plot(str(Path(__file__).parent / "briefs" / "2026-04-25" / "analog.png"))
