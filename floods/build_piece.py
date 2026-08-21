"""Render one FLO finding through templates/fast_reaction.py.

FIRST USE OF THAT TEMPLATE. It was built as design's first deliverable
under D-030 condition 1, in D-029's format: one question, one baseline,
one citable chart, named sources, an attribution tag. It has existed since
then with no script referencing it and has never rendered a page.

WHY A FLOOD FINDING IS THE RIGHT FIRST OBJECT. A rainfall accumulation
against 27 years of the same calendar window is counts-shaped, zero-based
and positive-mean, which is the series shape templates/validate.py already
exercises with a fire week on every run.

NOT A CHANNEL. No index, no nav entry, no /floods/ landing page. One dated
piece per region, published when the finding exists. Product was explicit
and it is the right scope: the channel does not exist on the site and this
is not the commit that creates it.

FOUR THINGS EVERY PIECE MUST CARRY, three of them rules we already hold.

THE MEASUREMENT IS RAINFALL, NOT FLOODING. FLO's instrument says so in its
own docstring and nothing built on it may be labelled otherwise. It
matters more here than anywhere else we publish, because a reader arriving
at a page about a flood will supply the word we did not.

FLOOD EXTENT IS not_assessed FOR EUROPE AND THAT IS A FINDING. D-193: the
screen passed 0 of 6 European regions, not because Europe cannot be seen
but because week-to-week visibility varies so much that a ranking would
rank the weather over the sensor. Absence read as reassurance is the
failure this project keeps rediscovering, so the page says it.

THE WINDOW AND THE PUBLICATION DATE ARE BOTH VISIBLE. D-190 and D-191.
This is a measurement rather than a forecast, so it does not need the
genre treatment the hurricane card needs, but a finding about 1-14 August
published on 21 August is honest only if a reader sees both at a glance.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from templates.fast_reaction import render  # noqa: E402

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def _sentence(text):
    """Capitalise and terminate a fragment from the payload.

    FLO writes not_assessed_summary lowercase and unterminated,
    which is right for a field and wrong in prose: concatenated it
    read "flooding. we have not measured flooding here; this page
    reports rainfall only Flood extent is not assessed". Their
    string is quoted rather than rewritten; only its edges move.
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t + ("" if t.endswith((".", "!", "?")) else ".") + " "


def _pretty(iso):
    y, m, d = iso.split("-")
    return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)


def _window_words(w):
    a, b = w["start"], w["end"]
    if a[:7] == b[:7]:
        return "%d to %d %s %s" % (int(a[8:10]), int(b[8:10]),
                                   MONTHS[int(b[5:7]) - 1], b[:4])
    return "%s to %s" % (_pretty(a), _pretty(b))


def piece_from(payload: dict) -> dict:
    rain = next((s for s in payload["series"] if s["id"] == "rainfall"), None)
    if rain is None:
        raise SystemExit("no rainfall series in payload")

    basis = rain["basis"]
    find = rain.get("finding") or {}

    # THE CHART IS THE FORMAT, so a missing series is a refusal rather than
    # a smaller chart. D-029 specifies ONE CITABLE CHART, and the citable
    # part is what makes the number checkable by someone who did not
    # measure it. A two-bar this-year-against-median picture would satisfy
    # the template and not the format: it shows the ratio we already state
    # in words and hides the distribution the rank is drawn from.
    #
    # The payload has value, median and rank 1 of 27 but no per-year
    # accumulations. FLO holds them, since a rank of 27 cannot be computed
    # without them. Asked for them as `basis.series`.
    years = basis.get("series")
    if not years:
        raise SystemExit(
            "REFUSING TO BUILD: %s has no per-year series.\n"
            "  The payload states value %.1f, median %.1f and rank %s of %s,\n"
            "  which cannot be computed without the 27 yearly accumulations,\n"
            "  so FLO holds them and the payload does not carry them.\n"
            "  Needs series[rainfall].basis.series as {year: mm}.\n"
            "  Not substituting a two-bar chart: it would show the ratio the\n"
            "  page already states and hide the distribution the rank comes\n"
            "  from, which is the citable half."
            % (payload["region_id"], rain["value"], basis["median"],
               basis["rank"], basis["of"]))

    cur = str(max(int(y) for y in years))
    extent = next((s for s in payload["series"]
                   if s["id"] == "flood_extent"), None)

    # ATTRIBUTION MAPS, IT DOES NOT PASS THROUGH. FLO writes
    # "not_enso_linked"; the template's vocabulary is enso | non_enso |
    # pending, and an unrecognised value would silently render as pending,
    # which claims we have not decided when FLO has.
    tag = {"not_enso_linked": "non_enso", "enso_linked": "enso",
           "pending": "pending"}.get(payload.get("attribution"))
    if tag is None:
        raise SystemExit("unmapped attribution %r; the template takes "
                         "enso | non_enso | pending"
                         % payload.get("attribution"))

    window = _window_words(payload["window"])
    return {
        "channel": "flood",
        "region": payload["label"],
        "window": window,
        # BOTH DATES AT A GLANCE, D-190 and D-191. A finding about
        # 1-14 August read on 21 August is honest only if the reader
        # can see when it was made without hunting for the source
        # line. It is a measurement rather than a forecast, so it
        # needs the date but not the genre treatment the card needs.
        "measured": _pretty(payload["as_of"]),
        "path": "/floods/%s-%s/" % (payload["region_id"], payload["as_of"]),
        # NO .lower() ON THE LABEL. It read "the eastern pyrenees and
        # upper segre": a place name is not a common noun, and the
        # cheap way to make a sentence flow destroyed two of them.
        "claim": ("%.0f mm of rain fell on the %s in %s, the most in %s "
                  "years of the same fortnight."
                  % (rain["value"], payload["label"], window,
                     basis["of"])),
        "standfirst": (
            "%s recorded %.1f mm over %s, against a median of %.1f mm for the "
            "same fortnight since %s. That is %.2f times the median and the "
            "highest of the %s years compared. This measures RAINFALL, not "
            "flooding."
            % (payload["label"], rain["value"], window, basis["median"],
               min(years), basis["x_median"],
               basis["of"])),
        "value": {
            "display": "%.2f×" % basis["x_median"],
            "caption": "the median for this fortnight, %.1f mm"
                       % basis["median"],
        },
        "chart": {
            "label": "Rainfall over %s, by year" % window,
            "series": [{"x": y, "y": v} for y, v in sorted(years.items())],
            "current_x": cur,
            "baseline": {"value": basis["median"], "label": "median"},
            "unit": "mm",
            "diverging": False,
            "annotations": [],
        },
        "source": {
            "name": rain["instrument"],
            "detail": rain["measures"],
            "as_of": _pretty(payload["as_of"]),
        },
        "attribution": tag,
        "notes": {
            "what_this_is": (
                "Rainfall accumulated over %s and compared with the same "
                "calendar fortnight in each of the previous %s years, as an "
                "area mean over the region. %d of %d days are compared; %s "
                "%s excluded from EVERY year, not just this one, so the "
                "comparison stays like for like."
                % (window, basis["of"] - 1, rain["window_days_compared"],
                   rain["window_days_nominal"],
                   " and ".join(rain.get("days_excluded") or []) or "no days",
                   "was" if len(rain.get("days_excluded") or []) == 1
                   else "were")),
            "what_this_is_not": (
                "Not a measurement of flooding. %s%s"
                % (_sentence(extent.get("not_assessed_summary")) if extent else "",
                   "Flood extent is not assessed for European regions: the "
                   "screen passed none of the six tested, because "
                   "week-to-week satellite visibility varies enough that a "
                   "ranking would rank the weather over the sensor. That is "
                   "a limit we measured, not one we assumed.")),
        },
    }


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None or not src.exists():
        raise SystemExit("usage: build_piece.py <floods/data/payload_*.json>")
    payload = json.loads(src.read_text())
    piece = piece_from(payload)
    out = ROOT / "docs" / piece["path"].strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(piece, root_prefix="../../"))
    print("wrote %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
