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


def _corroboration_line(corr):
    """What we know about whether the event happened, from outside.

    Silent when confirmed: a page about a flood that did flood needs no
    sentence saying so, and one there would read as doubt.
    """
    if corr.get("state") != "unknown":
        return ""
    return ("Whether this rainfall caused flooding has not been "
            "established. %s Our own instruments measure rainfall and flood "
            "extent, and neither can answer it."
            % corr.get("detail", "").strip())


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


# D-195: IMERG severely under-reads CONCENTRATED rainfall.
#
# NOT "THREE TO FIVE TIMES", which is what this said until FLO reversed
# their own same-day advice. That phrasing reads as a calibrated interval
# and it is not one: the over-150mm bin is n=3, and the three stations
# disagree by a factor of four. Turis 0.18, Utiel 0.44, Chelva 0.78. The
# bin mean is dominated by Turis, which is also the station that defined
# the event. So "five" is n=1 and "three" is the bottom of n=3.
#
# The SHAPE is not in doubt: monotonic across four bins at n=29, 4, 9 and
# 3, plus product's independent Bath measurement against Environment
# Agency gauges. Only the specific multiple was thin, so the text names
# the worst gauge and the case rather than implying a range.
# So a two-week accumulation reading ordinary is evidence about
# accumulation and evidence about nothing else, and on an event whose rain
# arrived in a few hours this instrument is largely blind.
# THE ONLY FIT THAT MEANS THE INSTRUMENT SAW IT. Matching a list of blind
# words was matching a vocabulary I had guessed at rather than the field
# FLO emits: they write "single-day dominated, intensity is under-read",
# which contains none of "mixed", "intense" or "convective", so the Atacama
# at 66% top-day share rendered as "no concentration". That is the inverse
# of the most important sentence on that page.
#
# So the default is inverted. A fit string this template does not recognise
# now reads as under-read rather than as clear, because on this channel an
# unknown reading must never come out as reassurance.
_FIT_WELL_MEASURED = "well measured"


def _intensity_row(rain):
    """Rainfall intensity, and whether this instrument could have seen it.

    THE THIRD ROW EXISTS BECAUSE OF WHAT A NORMAL READING WOULD OTHERWISE
    IMPLY. FLO's warning, and it is the right one: normal accumulation is
    not no flooding. A page reporting an ordinary fortnight with no further
    rows says, to any reader who is not a hydrologist, that nothing
    happened. That is absence-as-zero on the public surface, which is the
    one place we have not made this mistake yet.

    Same shape as the flood-extent row Kristjan ruled on: an instrument
    that could not answer the question is drawn, not omitted.
    """
    ec = rain.get("event_character") or {}
    fit = ec.get("instrument_fit") or ""
    share = ec.get("top_day_share")
    med = ec.get("baseline_median_top_day_share")
    if not fit:
        return None
    blind = _FIT_WELL_MEASURED not in fit
    detail = "GPM IMERG, 30-minute accumulation"
    if share is not None and med is not None:
        detail = ("one day carried %.0f%% of the fortnight, against a "
                  "%.0f%% median" % (100 * share, 100 * med))
    return {
        "name": "Rainfall intensity",
        "detail": detail,
        "value": "under-read" if blind else "no concentration",
        "rank": "",
        "state": "not_assessed" if blind else "measured",
        "caveat": (
            "This instrument measures accumulation over time and severely "
            "under-reads concentrated rainfall, by more than five times at "
            "the worst-hit gauge in the Valencia case. Rain that falls in a "
            "few hours can flood without moving a fortnight's total, so an "
            "ordinary total here is not evidence that nothing happened. Rain "
            "gauges answer that question; this does not."
            if blind else ""),
    }


def _rank_words(basis, find):
    """The rank, or a refusal to state one.

    ordinal_safe false means another year sits within 2% and the ordering
    is noise. Printing "16th of 27" there would publish a precision the
    measurement does not have, which is the same fault as a legend whose
    label the data denies.
    """
    # SEPARATION, NOT DENOMINATOR. The floor no longer reaches this: a
    # small median makes the multiple meaningless, not the ordering.
    # "about 1 of 27" is not a hedge, it still tells a reader we ranked it.
    if find.get("ordinal_safe"):
        return "%s of %s" % (basis["rank"], basis["of"])
    n = find.get("tied_with_n") or 0
    if n:
        return ("not ranked, %d other year%s within the tie margin"
                % (n, "" if n == 1 else "s"))
    return "not ranked"


_ORD_WORD = {1: "the most", 2: "the second most", 3: "the third most"}


def _nth(n):
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suf)


def _claim(payload, rain, basis, find, window):
    """The headline, from the RANK and from what each guard actually gates.

    TWO GUARDS, TWO DIFFERENT CLAIMS, and the template had them fused
    because the payload did. FLO separated them in a8e5bf18:

        ordinal_safe   may we say "4th of 27"?   a question of SEPARATION
        ratio_safe     may we say "3.6x"?        a question of DENOMINATOR

    So a reading can be perfectly rankable and still have a meaningless
    multiple. The Altiplano is exactly that: its median of 3.4 mm is under
    the floor, but the distribution runs 1.4 to 17.0 and its 12.3 sits 0.9
    clear of the next year. Publishable rank, unpublishable ratio.

    An earlier version of this function keyed both on baseline_below_floor
    and so threw away a good ordinal to protect against a bad ratio.
    """
    lab, val, med = payload["label"], rain["value"], basis["median"]
    state = find.get("claim")

    if state == "normal":
        return ("Rain over %s in %s was ordinary for the time of year: "
                "%.1f mm, %s the median for the same fortnight."
                % (lab, window, val,
                   "below" if basis["x_median"] < 1 else "just above"))

    if state == "low":
        return ("Rain over %s in %s was at the low end for the time of "
                "year: %.1f mm, against a median of %.1f mm for the same "
                "fortnight." % (lab, window, val, med))

    if find.get("ordinal_safe"):
        rank = basis["rank"]
        if rank in _ORD_WORD:
            return ("%.1f mm of rain fell over %s in %s, %s in %s years of "
                    "the same fortnight."
                    % (val, lab, window, _ORD_WORD[rank], basis["of"]))
        return ("%.1f mm of rain fell over %s in %s, the %s highest of %s "
                "years of the same fortnight."
                % (val, lab, window, _nth(rank), basis["of"]))

    return ("%.1f mm of rain fell over %s in %s, against a typical %.1f mm "
            "for the same fortnight. The closest years sit too near this "
            "total to place it among them."
            % (val, lab, window, med))


def _standfirst(payload, rain, basis, find, window, first_year):
    """Built from the guards rather than branched on one flag.

    WHERE ratio_safe IS FALSE THE MULTIPLE APPEARS NOWHERE, which is FLO's
    instruction and stricter than the previous version, which withheld the
    ordinal and then printed "That is 16.8 times the median" one clause
    later. Suppressing the ranking while keeping the number the ranking was
    unsafe because of is not a caveat, it is the same claim in another
    unit.
    """
    lab, val, med = payload["label"], rain["value"], basis["median"]
    state = find.get("claim")
    ordinal, ratio = find.get("ordinal_safe"), find.get("ratio_safe")

    out = ["%s recorded %.1f mm over %s, against a median of %.1f mm for "
           "the same fortnight since %s."
           % (lab, val, window, med, first_year)]

    if state in ("normal", "low"):
        out.append("That ranks it %s." % _rank_words(basis, find))
        out.append("This measures two-week RAINFALL ACCUMULATION, not "
                   "flooding, and an ordinary total is not evidence that "
                   "nothing happened.")
        return " ".join(out)

    if ratio and ordinal:
        out.append("That is %.2f times the median and the %s highest of the "
                   "%s years compared."
                   % (basis["x_median"], _nth(basis["rank"]), basis["of"]))
    elif ratio:
        out.append("That is %.2f times the median. The closest years sit "
                   "too near this total to rank it among them."
                   % basis["x_median"])
    elif ordinal:
        out.append("That is the %s highest of the %s years compared. No "
                   "multiple is given: the usual total here is small enough "
                   "that a ratio against it would measure noise rather than "
                   "how unusual the fortnight was."
                   % (_nth(basis["rank"]), basis["of"]))
    else:
        out.append("It is neither ranked nor expressed as a multiple: the "
                   "closest years sit too near this total to separate, and "
                   "the usual total is small enough that a ratio against it "
                   "would measure noise. The chart shows every year, which "
                   "is the honest comparison.")

    out.append("This measures RAINFALL, not flooding.")
    return " ".join(out)


def _instrument_rows(payload, rain, basis, extent, find):
    """Every instrument the piece could have used, assessed or not."""
    cov = payload.get("instrument_coverage") or {}
    rows = [{
        "name": "Rainfall",
        "detail": rain["instrument"],
        "value": "%.1f mm" % rain["value"],
        "rank": _rank_words(basis, find),
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
    intensity = _intensity_row(rain)
    if intensity:
        rows.append(intensity)
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


def _superseded_by(src_name):
    """Has another payload declared this one superseded?

    THE MARKER LIVES ON THE REPLACEMENT, NOT ON THE FILE IT REPLACES, so
    nothing stopped the withdrawn payload being built. FLO superseded the
    Andes payload on 2026-08-26 because its window was the RECESSION LIMB:
    every figure in it described the flood draining away, 7.15x where the
    truth was 37.5x, and a location 90 km from the event. Building it
    would have published a withdrawn finding that looks entirely healthy.

    So the check is a scan: if any payload in the directory names this one
    in `supersedes`, this one is not buildable.
    """
    for f in sorted(ROOT.glob("floods/data/payload_*.json")):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if d.get("supersedes") == src_name:
            return f.name, d.get("supersedes_reason") or ""
    return None


def piece_from(payload: dict, today: str) -> dict:
    rain = next((s for s in payload["series"] if s["id"] == "rainfall"), None)
    extent = next((s for s in payload["series"]
                   if s["id"] == "flood_extent"), None)
    if rain is None:
        raise SystemExit("no rainfall series in payload")

    # A PAYLOAD STILL WAITING FOR DATA HAS NO BASIS TO RENDER. Reaching
    # straight into rain["basis"] turned that into a bare KeyError, which
    # reads like a broken template rather than a payload that is honestly
    # not ready. FLO emits verdict "awaiting_data" for exactly this.
    if "basis" not in rain:
        raise SystemExit(
            "REFUSING TO BUILD: %s has no rainfall basis to render "
            "(verdict %r). Nothing is wrong with the payload; it is not "
            "finished. Build it when the rainfall series carries a basis."
            % (payload.get("region_id", "?"), rain.get("verdict")))

    basis = rain["basis"]
    find = rain.get("finding") or {}

    # A PAGE ON THE FLOODS CHANNEL IS ABOUT A FLOOD, AND NOTHING IN THE
    # PAYLOAD SAYS ONE HAPPENED.
    #
    # The Rhine is what surfaced it. Ordinary accumulation, rendered
    # honestly, three instrument rows, every caveat in place, and FLO then
    # read the Cologne gauge: 76 cm, BELOW mean low water, about a tenth of
    # mean flood level. The river did not flood. It rose from a record low
    # to a still-abnormally-low level. A Floods page about it would have
    # been wrong about its subject in a way no caveat rescues.
    #
    # THE RHINE WAS NOT A NEAR MISS, IT WAS THE GENERAL CASE. Checked every
    # payload afterwards: not one carries any field asserting that a flood
    # occurred. Every one measures RAINFALL and every one reports
    # flood_extent as not_assessed or cannot_say. That includes the
    # Pyrenees piece, which has been ready to publish all day and which I
    # have been describing as a clean validated European finding. It is a
    # clean validated RAINFALL finding. Whether anything flooded there is
    # something we have never established.
    #
    # The Rhine only got caught because FLO happened to hold a German
    # gauge. They hold no Italian or Polish one, so Po and Vistula cannot
    # be checked the same way and must not be assumed similar.
    #
    # So this refuses rather than warns. A warning is forgettable and the
    # failure it prevents is the channel's name asserting something the
    # channel has never measured.
    # READ `state`, NOT `occurred`. FLO encodes unknown as occurred null
    # with state "unknown", so testing `occurred is None` refused the
    # Pyrenees, which is exactly the case that is supposed to build. A
    # tri-state read through a boolean field is two of the three states.
    corr = payload.get("event_corroboration") or {}
    state = corr.get("state")
    if state not in ("true", "false", "unknown"):
        raise SystemExit(
            "REFUSING TO BUILD: %s carries no event_corroboration.\n"
            "  Nothing in this payload says a flood occurred. It measures\n"
            "  rainfall; flood_extent is %r. A page on a channel called\n"
            "  Floods asserts a flood by existing, and no caveat inside it\n"
            "  undoes the assertion its own URL makes.\n"
            "  Needs event_corroboration {occurred: true|false|unknown,\n"
            "  source, detail}. The Rhine reads occurred: false on the\n"
            "  Cologne gauge at 76 cm against a 725 cm mean flood level."
            % (payload["region_id"],
               (extent or {}).get("verdict", "absent")))
    if state == "false":
        raise SystemExit(
            "REFUSING TO BUILD: %s did not flood.\n  %s"
            % (payload["region_id"], corr.get("detail", "")))

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

    # ATTRIBUTION MAPS, IT DOES NOT PASS THROUGH. FLO writes
    # "not_enso_linked"; the template's vocabulary is enso | non_enso |
    # pending, and an unrecognised value would silently render as pending,
    # which claims we have not decided when FLO has.
    # The payload side is the three strings D-033 fixes. The map keyed on
    # "pending" instead of "attribution_pending" and so refused every
    # payload carrying the commonest of the three, 6 of the 11 on disk.
    # The error named the template's internal words rather than the ones a
    # payload can legally hold, which sent the reader looking in the wrong
    # file.
    ATTRIBUTION = {"enso_linked": "enso",
                   "not_enso_linked": "non_enso",
                   "attribution_pending": "pending"}
    tag = ATTRIBUTION.get(payload.get("attribution"))
    if tag is None:
        raise SystemExit("attribution %r is not one of the three strings "
                         "fixed by D-033: %s. A gap in that set is a "
                         "ratification question for Kristjan, not a value "
                         "a channel or a template fills in."
                         % (payload.get("attribution"),
                            ", ".join(sorted(ATTRIBUTION))))

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
        # SAID ON THE PAGE, NOT JUST CHECKED AT BUILD TIME. `unknown`
        # builds by design, so a page that passed the guard silently
        # would carry the same false assertion the guard exists to
        # stop, with an extra field behind it making everyone feel
        # better. It sits beside the staleness line, above the
        # standfirst, because it qualifies the URL rather than the
        # measurement.
        "corroboration": _corroboration_line(corr),
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
        "claim": _claim(payload, rain, basis, find, window),
        "standfirst": _standfirst(payload, rain, basis, find, window,
                                  min(years)),
        # THE BIG NUMBER IS THE MULTIPLE, EXCEPT WHERE THE MULTIPLE IS THE
        # ARTEFACT. On a near-zero baseline "16.80x" is the single most
        # misleading thing that could sit at the top of the page, so the
        # figure that leads is the one that was actually measured.
        "value": {
            "display": ("%.1f mm" % rain["value"]
                        if not find.get("ratio_safe")
                        else "%.2f×" % basis["x_median"]),
            "caption": (("against a typical %.1f mm for this fortnight"
                         if not find.get("ratio_safe")
                         else "the median for this fortnight, %.1f mm")
                        % basis["median"]),
        },
        "chart": {
            "label": "Rainfall over %s, by year" % window,
            "series": [{"x": y, "y": v} for y, v in sorted(years.items())],
            "current_x": cur,
            "baseline": {"value": basis["median"], "label": "median"},
            "unit": " mm",
            "decimals": 1,
            "header": "RAINFALL, %s \u00b7 MM \u00b7 ONE SLOT PER YEAR" % window.upper(),
            "lo": 0,
            "noun": "fortnight",
            "noun_plural": "fortnights",
            "current_kicker": cur,
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
        "instruments": _instrument_rows(payload, rain, basis, extent, find),
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

    sup = _superseded_by(src.name)
    if sup:
        raise SystemExit(
            "REFUSING TO BUILD: %s has been superseded by %s.\n%s\n"
            "A withdrawn payload builds into a page that looks entirely "
            "healthy, which is why this is a refusal rather than a "
            "warning." % (src.name, sup[0], sup[1][:400]))

    piece = piece_from(payload, today=_today())
    out = ROOT / "docs" / piece["path"].strip("/") / "index.html"

    force = "--force" in sys.argv
    if out.exists() and not force:
        raise SystemExit(
            "REFUSING TO REBUILD: %s already exists.\n"
            "This page was published on a date and says so. Rebuilding "
            "re-stamps it with today and re-words its headline in whatever "
            "the template says now, which is invariant 5 and is why "
            "run_brief exits early on the same condition.\n"
            "Use --force only to fix a published page in a genuine "
            "emergency, and expect the published date to move."
            % out.relative_to(ROOT))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(piece, root_prefix="../../"))
    print("wrote %s%s" % (out.relative_to(ROOT),
                          "  (FORCED over a published page)" if force else ""))


if __name__ == "__main__":
    main()
