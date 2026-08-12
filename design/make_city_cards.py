"""One share card per heat city. The finding, not an advert for the site.

WHY. Every page on the site returns the same og:image, the El Niño weekly
card, so a shared heat city page previews with an ENSO chart. Socials'
words: on-brand and off-subject, and the reader most affected is the one
who never clicks, which is most of them.

Their evidence for prioritising it is the clearest we have. Over two days,
one reply into a live thread took 4,957 views against 558 for five
standalone posts, and in both cases WHAT TRAVELLED WAS A CHART, not a
sentence. A per-page card puts that chart on every share by every reader
rather than on the ones where somebody has cropped a screenshot by hand.

TWO CONSTRAINTS, BOTH SOCIALS', AND BOTH MET STRUCTURALLY RATHER THAN BY
DISCIPLINE:

1. THE CUT DATE IS ON THE CARD. Heat figures move most days and were
   revised twice this week. A card baked once and never regenerated will
   eventually disagree with its own page, and unlike a page, a card sitting
   in someone's timeline cannot be corrected.

2. IT REGENERATES WITH THE PAGE. make_city_pages.py calls this in the same
   pass, from the same payload. A card cannot go stale relative to its page
   if it cannot be built without building the page. Socials' own example:
   London carried a stale provisional notice for eleven minutes because a
   field was updated in one place and not its neighbour, and a card on its
   own cadence is that failure with a longer fuse, because nobody looks at
   a preview image after it ships.

The payload hash goes into the PNG metadata as well, so a card built from a
different payload than its page is detectable rather than merely unlikely.

THE CARD CARRIES ITS OWN QUALIFIERS because it travels alone. Same rule as
the Note chart: "at least" where the counts are floors, the threshold's own
period per city rather than a constant, and the station. A card is the
whole artefact, so anything the page would have said elsewhere has to be on
the image.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import matplotlib.image as _mpimg        # noqa: E402  (kept for parity)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from design.make_note_chart import (      # noqa: E402
    N, PAPER, INK, INK_SOFT, INK_FAINT, QUIET, NOW, RULE,
    PAYLOAD_STAMP, series, _day)

OUT = ROOT / "docs" / "heat" / "cards"

# 1200x630 is the og:image aspect every platform crops to. Anything else is
# cropped for us, and the crop lands where the platform chooses.
W_IN, H_IN, DPI = 6.0, 3.15, 200


def _slug(city):
    return city.lower().replace(" ", "-")


def draw(city):
    """One city's card. Days only: nights are gated on most of the set."""
    v, s, vals, now, axis, sub = series(city, "days")
    d = v["days"]
    years = sorted(vals)
    if not years:
        return None

    floor = "at least " if (N.get("coverage") or {}).get(
        "counts_are_floors") else ""
    rank = d["rank"]
    ties = list(rank.get("tied_with") or [])

    # THE SAME TIE BRANCH AS THE PAGE. Rank counts prior years at or above,
    # so where the rank is exactly one more than the number of ties, nothing
    # exceeds this year and "2nd of 49" would say something false on an
    # image that travels without its page.
    if rank["value"] == 1:
        claim = "the most on record"
    elif ties and rank["value"] == 1 + len(ties):
        claim = "matching %s, the most on record" % ", ".join(
            str(y) for y in sorted(ties))
    else:
        claim = "%s of %d summers" % (_ord(rank["value"]), rank["of_years"])

    # THE THRESHOLD'S OWN PERIOD, read per city. make_note_chart's `sub`
    # hard-codes "1971 to 2000", which stopped being true for four cities
    # when D-151 moved them to a complete 1991-2020 normal. Same constant
    # I removed from the city pages this morning, still live in the file
    # this card reuses.
    lo, hi = (v.get("pctl_baseline") or [1971, 2000])
    basis = ("about one summer day in twenty at this station, %d to %d"
             % (lo, hi))

    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    fig.patch.set_facecolor(PAPER)

    fig.text(0.055, 0.895, "THE LONG SWELL  ·  HEAT", color=INK_FAINT,
             fontsize=6.4, family="IBM Plex Mono")
    fig.text(0.055, 0.775, city, color=INK, fontsize=21, family="Spectral")
    fig.text(0.055, 0.655,
             "%s%d days at or above %s °C this summer, %s"
             % (floor.capitalize() if False else floor, now,
                d["thresholds_c"]["95"], claim),
             color=INK_SOFT, fontsize=9.6, family="Spectral")

    ax = fig.add_axes([0.055, 0.185, 0.89, 0.40])
    ax.set_facecolor(PAPER)
    ax.bar(years, [vals[y] for y in years], width=0.86, color=QUIET,
           linewidth=0)
    # The current year takes the hue ONLY when it leads its own series,
    # which is the rule crops set and heat adopted: a record year drawn in
    # accent and an ordinary year drawn in accent teach a reader nothing.
    ax.bar([2026], [now], width=0.86,
           color=(NOW if rank["value"] == 1 or (
               ties and rank["value"] == 1 + len(ties)) else INK_SOFT),
           linewidth=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(axis="both", length=0, colors=INK_FAINT, labelsize=6.2)
    ax.set_xlim(min(years) - 1, 2027)
    ax.set_xticks([min(years), 2026])
    ax.set_yticks([])
    for lab in ax.get_xticklabels():
        lab.set_family("IBM Plex Mono")

    fig.text(0.055, 0.085, axis.title().upper(), color=INK_FAINT,
             fontsize=6.2, family="IBM Plex Mono")
    # THE CUT DATE, on the face. Socials' first constraint, and the reason
    # is that a card in a timeline cannot be corrected the way a page can.
    fig.text(0.945, 0.085,
             "%s  ·  TO %s" % (v.get("station", ""), _day(s["cut_at"]).upper()),
             color=INK_FAINT, fontsize=6.2, family="IBM Plex Mono",
             ha="right")
    fig.text(0.055, 0.022, basis, color=INK_FAINT, fontsize=5.8,
             family="IBM Plex Mono")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / ("%s.png" % _slug(city))
    fig.savefig(p, facecolor=PAPER,
                metadata={"Software": "tls-city-card payload=%s"
                          % PAYLOAD_STAMP})
    plt.close(fig)
    return p


def _ord(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def draw_all():
    """Every city with a days series. Returns {city: path}."""
    made = {}
    for city in sorted(N["cities"]):
        try:
            p = draw(city)
        except (KeyError, TypeError):
            p = None
        if p:
            made[city] = p
    return made


if __name__ == "__main__":
    m = draw_all()
    print("wrote %d city cards to %s" % (len(m), OUT.relative_to(ROOT)))
