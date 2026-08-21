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
    """Quote a payload string that is displayed as prose.

    This used to capitalise and terminate the fragment, because
    not_assessed_summary was written lowercase and unterminated. FLO has
    made the field sentence-shaped and asked me to drop the handling, and
    they are right: editing at the boundary was the correct instinct in
    the wrong place, since a field displayed as prose should BE prose.

    So nothing is rewritten. A regression is reported rather than patched,
    because silently fixing someone else's field is how two surfaces drift
    while both look fine.
    """
    t = (text or "").strip()
    if not t:
        return ""
    if not (t[0].isupper() and t.endswith((".", "!", "?"))):
        print("  NOTE: not_assessed_summary is not sentence-shaped (%r). "
              "Rendering it verbatim; FLO owns the wording." % t[:60])
    return t + " "


def _pretty(iso):
    y, m, d = iso.split("-")
    return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)


def _window_words(w):
    a, b = w["start"], w["end"]
    if a[:7] == b[:7]:
        return "%d to %d %s %s" % (int(a[8:10]), int(b[8:10]),
                                   MONTHS[int(b[5:7]) - 1], b[:4])
    return "%s to %s" % (_pretty(a), _pretty(b))


def _days_between(a, b):
    from datetime import date
    ya, ma, da = (int(x) for x in a.split("-"))
    yb, mb, db = (int(x) for x in b.split("-"))
    return (date(yb, mb, db) - date(ya, ma, da)).days


def _staleness(window, today):
    """How old the event is, in the page's own words, or "" if current.

    Silent below a week: a piece published within days of its window is
    what the format is for and does not need to apologise for itself.
    """
    end_age = _days_between(window["end"], today)
    if end_age < 7:
        return ""
    start_age = _days_between(window["start"], today)
    return ("This event has closed. The rain fell between %d and %d days "
            "ago, over %s, and this page has not been updated since. It is "
            "a record of what happened, not a report of what is happening."
            % (end_age, start_age, _window_words(window)))


def _instrument_rows(payload, rain, basis, extent):
    """Every instrument the piece could have used, assessed or not."""
    cov = payload.get("instrument_coverage") or {}
    rows = [{
        "name": "Rainfall",
        "detail": rain["instrument"],
        "value": "%.1f mm" % rain["value"],
        "rank": "%s of %s" % (basis["rank"], basis["of"]),
        "state": "measured",
    }]
    # THE INSTRUMENT'S OWN REACH IS PART OF THE ROW. FLO emits
    # data_through and window_truncated; a window that closed before the
    # data ran out is complete, and one that did not is a page whose
    # event may still be going. Rendering the flag rather than the note,
    # because a page that does not know its instrument stopped short
    # implies the event stopped there too.
    if cov.get("window_truncated"):
        rows[0]["caveat"] = (
            "The instrument holds data only to %s, %s day%s short of this "
            "window. The event may have continued past what is measured "
            "here."
            % (_pretty(cov.get("data_through", "?")),
               cov.get("days_behind_run_date", "?"),
               "" if cov.get("days_behind_run_date") == 1 else "s"))
    if extent:
        rows.append({
            "name": "Flood extent",
            "detail": extent.get("instrument", ""),
            "value": "not assessed",
            "rank": "",
            "state": "not_assessed",
            "caveat": (extent.get("not_assessed_reason") or [""])[0],
        })
    return rows


def piece_from(payload: dict, today: str) -> dict:
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
        # PUBLISHED, NOT MEASURED, and the difference is not pedantry.
        # `as_of` moved when the payload was re-emitted with no new
        # measurement in it, so it dates the FILE rather than the reading,
        # and "measured 21 August" was false about rain that stopped on the
        # 14th. The window already carries when it was measured. What a
        # reader additionally needs, per D-190 and D-191, is when we said
        # it, and that is unambiguous. Asked FLO to define as_of.
        "measured": "published " + _pretty(today),
        # A CLOSED EVENT SAYS IT IS CLOSED. FLO's call and it is right: this
        # window ended on 14 August and the page would be read on the 21st,
        # so a piece framed as current would be wrong about its own subject.
        # Fast reaction is a FORMAT, not a claim about recency, and nothing
        # else on the page would have told a reader which it was.
        #
        # The age is computed from the payload and today, never typed. FLO
        # said "three weeks", which is the age of the window's START; its
        # END is a week old. Both are true and they are different sentences,
        # so the page states the span rather than picking a number.
        "staleness": _staleness(payload["window"], today),
        # THE URL IS THE EVENT, SO IT COMES FROM THE WINDOW, NOT as_of.
        # Built from as_of first, which moved from 18 to 21 August when
        # FLO re-emitted the payload to ADD A FIELD, changing no
        # measurement. That would have given the same event a new URL on
        # every re-emission, orphaning whatever had been shared. A piece
        # is identified by the event it describes; the window closing is
        # the one date about it that cannot move.
        "path": "/floods/%s-%s/" % (payload["region_id"],
                                    payload["window"]["end"]),
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
            # FLO SPLIT as_of INTO TWO FIELDS after I reported it was dating
        # the file while the page read it as dating the reading. The source
        # line now carries the one a citation needs: how far the
        # measurement reaches. `generated` is when the file was written and
        # belongs nowhere on the page.
        "as_of": _pretty(payload["measured_to"]),
        },
        # DECISION 2A, Kristjan's call. Flood extent is a ROW in the
        # instrument table at the same weight as the measurement, not a
        # sentence under "what this is not". A reader who skims sees that a
        # second instrument exists and was not assessed; in prose below the
        # fold they have already formed a view. Absent-read-as-zero is this
        # project's recurring defect and a row is the version a skimmer
        # cannot miss.
        "instruments": _instrument_rows(payload, rain, basis, extent),
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


def _today():
    """Today, from the environment. Passed in rather than read inside
    piece_from so a test can pin it, and so the staleness sentence is never
    computed from a clock a caller cannot see."""
    from datetime import date
    return date.today().isoformat()


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None or not src.exists():
        raise SystemExit("usage: build_piece.py <floods/data/payload_*.json>")
    payload = json.loads(src.read_text())
    piece = piece_from(payload, today=_today())
    out = ROOT / "docs" / piece["path"].strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(piece, root_prefix="../../"))
    print("wrote %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
