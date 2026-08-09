"""The chart that travels with a Note. One component, any city, either metric.

WHAT MAKES THIS DIFFERENT FROM A PAGE CHART. A page chart has a page
around it: a lead that scopes the claim, a definitions row, a source
footer. This one goes on social with none of that. It is the whole
artefact, so anything the page would have said elsewhere has to be ON THE
IMAGE. Editor's rule and it is the right one; the all-hands version is
"charts travel alone, emit the fields that let them".

Concretely, everything below is drawn rather than left to a caption:

    the basis        the y-axis says what is counted and against what
    the window       counted to the same calendar day in every year
    the floor        the season is unfinished, so the count is a floor
    the station      one thermometer, named, with its source
    the disclosure   station moves inside the plotted period

THE GATE IS ENFORCED HERE, NOT ASSUMED. 19 of 36 cities are night-gated:
their 1991-2020 tropical-night baseline is near zero, so a record is
arithmetic rather than evidence, and heat's payload says in capitals that
such a page may not quote a night ratio, multiple or record. A chart whose
entire content is "17 against a previous best of 7" is a record claim in
visual form, whichever words sit near it. This module refuses to draw one.

Refusing in code rather than in a note, because the first Note was specced
against Frankfurt nights, then Paris nights before that, and both cities
are gated. Two chats read the payload and neither of us saw the flag.

    .venv/bin/python design/make_note_chart.py Paris days
    .venv/bin/python design/make_note_chart.py Madrid nights
"""
import json
import textwrap
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

R = Path(__file__).resolve().parent.parent
N = json.loads((R / "heat/data/city_nights.json").read_text())
OUT = R / "docs/notes/charts"

PAPER, INK, INK_SOFT, INK_FAINT = "#F1F0EC", "#1A1A18", "#3A3A36", "#6E6E67"
RULE, QUIET, NOW = "#CFCEC7", "#D8D7D1", "#8E240A"
MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]


def _day(mmdd):
    m, d = mmdd.split("-")[-2:]
    return f"{int(d)} {MON[int(m) - 1]}"


def series(city, metric):
    """Values, the 2026 figure, and everything the image has to carry."""
    v = N["cities"][city]

    if metric == "nights":
        # See the module docstring. This is heat's rule, quoted from the
        # payload so the refusal cannot drift from what the data says.
        if v.get("nights_metric_gated"):
            raise SystemExit(
                f"REFUSING: {city}'s tropical-night metric is gated.\n\n"
                f"  {v['nights_metric_gated_note']}\n\n"
                f"A chart of this series IS a record claim: its content is "
                f"{v['nights_2026']} against a previous best. "
                f"{len([c for c, x in N['cities'].items() if x.get('nights_metric_gated')])} "
                f"of {len(N['cities'])} cities are gated, all of them north of "
                f"the Mediterranean. Pick an ungated city, or chart days.")
        s, now = v["series_to_same_date"], v["nights_2026"]
        axis = "NIGHTS THAT NEVER FELL BELOW 20 °C"
        sub = "the ETCCDI tropical-night index, one thermometer"
    else:
        d = v["days"]
        s, now = d["series_to_same_date"], d["days_2026"]["95"]
        axis = f"DAYS AT OR ABOVE {d['thresholds_c']['95']} °C"
        sub = ("about one summer day in twenty at this station, "
               "1971 to 2000")

    vals = {int(y): x for y, x in s["values"].items() if int(y) != 2026}
    return v, s, vals, now, axis, sub


def draw(city, metric):
    v, s, vals, now, axis, sub = series(city, metric)
    years = sorted(vals)
    cut = _day(s["cut_at"])

    # The floor is read, never typed. While any city in the set is short of
    # the latest cut, a count can only rise, so the figure is a lower bound
    # and the chart says so rather than implying a settled number.
    floor = "at least " if N.get("coverage", {}).get("counts_are_floors") else ""

    fig, ax = plt.subplots(figsize=(10.8, 7.2), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    ax.bar(years, [vals[y] for y in years], width=0.86, color=QUIET,
           linewidth=0)
    ax.bar([2026], [now], width=0.86, color=NOW, linewidth=0)

    prev = max(vals.values())
    ax.axhline(prev, color=INK_FAINT, lw=0.9, ls=(0, (4, 3)), zorder=3)
    ax.text(years[0], prev, f" previous best, {prev}", va="bottom", ha="left",
            fontsize=10.5, color=INK_FAINT)
    ax.annotate(f"{floor}{now}".strip(), (2026, now), xytext=(0, 7),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=15, color=NOW, weight="bold")

    ax.set_xlim(years[0] - 1.5, 2027.5)
    ax.set_ylim(0, max(now, prev) * 1.20)
    ax.yaxis.set_major_locator(MaxNLocator(4, integer=True))
    ax.tick_params(labelsize=11, colors=INK_FAINT, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.grid(axis="y", color=RULE, lw=0.6, alpha=0.55)
    ax.set_axisbelow(True)

    # THE BASIS GOES IN THE AXIS, not in a subtitle. Editor's call and it
    # is better than what I proposed: a subtitle is a sentence a crop can
    # remove, and the axis label cannot be cropped off without taking the
    # numbers it labels with it.
    ax.set_ylabel(f"{axis}\n{sub}", fontsize=11.5, color=INK_SOFT,
                  labelpad=14, linespacing=1.7)

    # SELF-CONTAINED, because the title is the line that gets quoted and
    # the one a crop keeps. The first version read "Paris has had at least
    # 31 of them this summer", whose antecedent was the y-axis label,
    # rotated ninety degrees on the far side of the plot. It parsed only
    # for someone reading the whole image in order, which is not how a
    # chart on a timeline is read.
    #
    # Wrapped for the same reason as the footer, and it needed it: the
    # self-contained version was longer than the one it replaced and ran
    # off the right edge at "The previous best was". Twice in one figure,
    # so the rule is that no text on this image is trusted to fit.

    noun = "hot nights" if metric == "nights" else "hot days"
    ax.set_title("\n".join(textwrap.wrap(
        f"{city} has had {floor}{now} {noun} this summer. "
        f"The previous best was {prev}.", 54)),
        fontsize=19, color=INK, loc="left", pad=16, weight="medium",
        linespacing=1.35)

    # Everything a page would have carried elsewhere, on the image.
    foot = [f"Every summer counted to {cut}, so the years compare.",
            f"{v['record_scope']['text'].capitalize()}.",
            # Some services publish the station name in caps (ORLY,
            # VALENCIA) and others mixed (Wien Hohe Warte). Title-cased only
            # when it is entirely upper, so a name that carries meaningful
            # case keeps it.
            f"{v['station'].title() if v['station'].isupper() else v['station']}, "
            f"{v['source']['who']}."]
    if v.get("station_disclosure"):
        # Shown because Kristjan ruled the state is shown per city rather
        # than hedged across the set. It is a disclosure, not a warning:
        # the rise here sits inside the range set by stations that never
        # moved, so it is placed as plain text and never in red.
        foot.append(v["station_disclosure"])
    if floor:
        foot.append("The season is unfinished, so 2026 can only rise.")
    # WRAPPED, not trusted to fit. The first render ran the source line off
    # the right edge mid-word, which on a chart that travels alone deletes
    # the attribution rather than making it look cramped.

    fig.text(0.006, 0.012, "\n".join(textwrap.wrap(" ".join(foot), 118)),
             fontsize=10, color=INK_FAINT, ha="left", va="bottom",
             linespacing=1.5)

    fig.tight_layout(rect=(0, 0.085, 1, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{city.lower()}-{metric}.png"
    fig.savefig(p, facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {p} | {city} {metric}: {floor}{now} against a previous best "
          f"of {prev}, {len(years)} prior years from {years[0]}, cut {cut}")
    return p


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("days", "nights"):
        raise SystemExit("usage: make_note_chart.py <City> days|nights")
    draw(sys.argv[1], sys.argv[2])
