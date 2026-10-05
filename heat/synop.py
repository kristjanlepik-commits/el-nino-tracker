"""Decode SYNOP FM-12 far enough to read the 12-hour temperature extremes.

WHY A PARSER AND NOT A REGEX. The first attempt matched `1sTTT` and `2sTTT`
anywhere in section 333. Section 333 is full of five-digit groups and several
of them start with 1 or 2, so the pattern also matched things like `20000`
from an unrelated group. It returned plausible temperatures on some messages
and -95 C on others, and the only reason the error surfaced was that taking a
minimum amplified the spurious matches. Plausible-looking wrong numbers are
the failure this whole channel exists to avoid.

WHAT MAKES A CORRECT PARSE POSSIBLE. Section 333 groups appear in ASCENDING
order of leading digit: 0, then 1, then 2, and so on. So a group starting
with 1 is the maximum ONLY while nothing with a higher leading digit has been
seen yet. Tracking that order is the whole difference between this and the
regex.

  1sTTT   maximum temperature over the period
  2sTTT   minimum temperature over the period
          s = 0 positive, 1 negative; TTT in tenths of a degree

WHAT THIS DELIBERATELY DOES NOT DO. It reads two groups. It is not a general
SYNOP decoder and should not be extended into one without a test suite, since
every additional group is another chance to return a plausible wrong number.
"""
from __future__ import annotations

MISSING = {"/", "//", "///", "////", "/////"}


def _temp(group):
    """1sTTT or 2sTTT -> degrees C, or None if the group is not a temperature."""
    if len(group) != 5 or not group[1:].isdigit():
        return None
    sign = group[1]
    if sign not in ("0", "1"):
        return None
    v = int(group[2:]) / 10.0
    return -v if sign == "1" else v


def section_333(msg):
    """Return the groups of section 333, or [] if absent.

    333 can be followed by 444, 555 or the end. Anything after a later
    section marker belongs to that section and must not be read here.
    """
    parts = msg.replace("=", " ").split()
    if "333" not in parts:
        return []
    out = []
    for g in parts[parts.index("333") + 1:]:
        if g in ("444", "555"):
            break
        out.append(g)
    return out


def extremes(msg):
    """(tmax, tmin) over the report's period, either possibly None.

    Groups are read in ascending-leading-digit order. Once a group with a
    leading digit above 2 appears, no later group can be a temperature, which
    is what stops `20000` in the 5- or 6-group range being read as -0.0 C.
    """
    tmax = tmin = None
    seen = 0
    for g in section_333(msg):
        if len(g) != 5 or g[0] in MISSING or not g[0].isdigit():
            continue
        lead = int(g[0])
        if lead < seen:
            # Out of order: this is a repeated group from a later class, not
            # a temperature. Stop rather than guess.
            break
        seen = lead
        if lead == 1 and tmax is None:
            tmax = _temp(g)
        elif lead == 2 and tmin is None:
            tmin = _temp(g)
        elif lead > 2:
            break
    return tmax, tmin


def parse_ogimet(text):
    """OGIMET getsynop CSV -> list of (date, hourUTC, tmax, tmin)."""
    out = []
    for line in text.splitlines():
        p = line.strip().split(",")
        if len(p) < 7 or not p[1].isdigit():
            continue
        date = f"{p[1]}-{int(p[2]):02d}-{int(p[3]):02d}"
        hour = f"{int(p[4]):02d}"
        tmax, tmin = extremes(",".join(p[6:]))
        out.append((date, hour, tmax, tmin))
    return out


# RAIN. Siblings of extremes(), never an extension of it (D-321): the heat
# count reads extremes() and must not change because rain was added beside it.
#
# THE ONE RULE ALL OF THIS SERVES: a period with no rain and a period nobody
# measured are different facts, and SYNOP says which. The iR digit opens
# section 1 and decides it:
#
#   iR 0  rain groups in sections 1 and 3      iR 3  omitted, NONE FELL (zero)
#   iR 1  rain group in section 1 only         iR 4  omitted, NOT OBSERVED
#   iR 2  rain group in section 3 only         /     indicator missing
#
# Reading iR 4 as zero is absence-as-zero at the parser, the fault this
# channel spent August finding at the rendering layer.
#
#   6RRRt   section 1 and section 3. RRR is code table 3590: 001-988 mm,
#           989 is 989 mm OR MORE, 990 trace, 991-999 tenths 0.1-0.9.
#           000 is read as zero: by the letter of 3590 it is unused, but
#           stations send it, and Zagreb Gric's 60002 at 06Z sits beside
#           7R24 = 0000 in the same bulletin, so it means none fell.
#           t is code table 4019, the period ending at the observation:
#           1=6h 2=12h 3=18h 4=24h 5=1h 6=2h 7=3h 8=9h 9=15h. 0 and /
#           mean "the regional period", which this does not guess at.
#   7RRRR   section 3 only: the 24 h total in TENTHS, 9999 trace.
#
# THE RADIATION TRAP. In section 3 a 55SSS (or 553SS) sunshine group may be
# followed by radiation groups j5FFFF with j5 from 0 to 6, so a 6xxxx after
# it can be net short-wave radiation rather than rain. Where that cannot be
# told apart, the section-3 group is reported AMBIGUOUS and not read.

RAIN_HOURS = {"1": 6, "2": 12, "3": 18, "4": 24, "5": 1, "6": 2, "7": 3,
              "8": 9, "9": 15}


def _rrr(code):
    """Code table 3590 -> (mm, trace, open_ended), or None if not reported."""
    if len(code) != 3 or not code.isdigit():
        return None
    v = int(code)
    if v == 990:
        return 0.0, True, False
    if v >= 991:
        return (v - 990) / 10.0, False, False
    return float(v), False, v == 989


def _six(group):
    """6RRRt -> {mm, trace, open_ended, hours} or None when RRR is missing."""
    r = _rrr(group[1:4])
    if r is None:
        return None
    mm, trace, open_ended = r
    return {"mm": mm, "trace": trace, "open_ended": open_ended,
            "hours": RAIN_HOURS.get(group[4])}


def _sections(msg):
    """(section-1 groups after iRiXhVV, iR digit, section-3 groups).

    Positional, because the first two groups of section 1 are not in
    leading-digit order: iRiXhVV, then Nddff, where N is cloud cover in
    oktas, so a sky six-eighths covered reads as 6ddff and would be taken for
    rain by anything that scanned for a leading 6.
    """
    parts = msg.replace("=", " ").split()
    if len(parts) < 5 or parts[0] != "AAXX" or "NIL" in parts[:4]:
        return None, None, []
    iRx, nddff = parts[3], parts[4]
    rest = parts[5:]
    if nddff[3:5] == "99" and rest and rest[0].startswith("00"):
        rest = rest[1:]                          # 00fff, wind of 99 units
    s1 = []
    for g in rest:
        if g in ("333", "444", "555") or g.startswith("222"):
            break
        s1.append(g)
    iR = iRx[0] if iRx else "/"
    return s1, iR, section_333(msg)


def rain(msg):
    """Everything one bulletin says about precipitation, nothing inferred.

    Returns None for a message that is not a land SYNOP, else a dict:
      iR       "0".."4" or "/"
      s1, s3   6RRRt decoded, or None if the group is absent
      r24      {mm, trace} from section 3's 7RRRR, or None
      flags    list of strings, e.g. "s3_ambiguous_radiation"
    Interpreting iR (what may be read as zero) is rain_reports()'s job, so
    this layer stays a faithful transcription a reviewer can check by eye.
    """
    s1g, iR, s3g = _sections(msg)
    if s1g is None:
        return None
    out = {"iR": iR, "s1": None, "s3": None, "r24": None, "flags": []}

    seen = 0
    for g in s1g:
        if len(g) != 5 or not g[0].isdigit():
            continue
        lead = int(g[0])
        if lead < seen:
            break
        seen = lead
        if lead == 6:
            out["s1"] = _six(g)
        elif lead > 6:
            break

    seen, after55, radiation = 0, False, False
    sixes = []
    for g in s3g:
        if len(g) != 5 or not g[0].isdigit():
            continue
        lead = int(g[0])
        if after55 and lead <= 6:
            # Inside or just after a radiation block: order restarts here.
            if lead < 5:
                radiation = True
                continue
            if lead == 6:
                sixes.append(g)
                continue
        if lead < seen:
            break
        seen = lead
        if g.startswith("55"):
            after55 = True
        elif lead == 6:
            sixes.append(g)
        elif lead == 7:
            if g[1:].isdigit():
                v = int(g[1:])
                out["r24"] = ({"mm": 0.0, "trace": True} if v == 9999
                              else {"mm": v / 10.0, "trace": False})
        elif lead > 7:
            break
    if sixes:
        if after55 and (radiation or len(sixes) > 1):
            out["flags"].append("s3_ambiguous_radiation")
        else:
            out["s3"] = _six(sixes[0])
    return out


def rain_reports(msg):
    """The precipitation FACTS a bulletin asserts, as a list of
    (hours, mm, trace, source). Only what iR licenses is returned:

      a group that iR says should not be there is ignored and flagged,
      iR 3 yields ("zero", None) for the caller to place, because "none fell"
      arrives without a period and the period is a property of the station
      and hour, which only that station's other bulletins can tell,
      iR 4 and / yield nothing: not observed is not zero.

    Returns (reports, zero_unplaced, flags).
    """
    r = rain(msg)
    if r is None:
        # NIL is a bulletin the station did not send: absent, not dry.
        return [], False, ["nil" if "NIL" in msg else "not_synop"]
    flags = list(r["flags"])
    reps = []
    iR = r["iR"]
    allowed = {"0": ("s1", "s3"), "1": ("s1",), "2": ("s3",)}.get(iR, ())
    for sec in ("s1", "s3"):
        g = r[sec]
        if g is None:
            continue
        if sec not in allowed:
            flags.append(f"{sec}_present_but_iR_{iR}")
            continue
        if g["hours"] is None:
            flags.append(f"{sec}_regional_period")
            continue
        if g["open_ended"]:
            flags.append(f"{sec}_989_or_more")
        reps.append((g["hours"], g["mm"], g["trace"], sec))
    if r["r24"] is not None:
        reps.append((24, r["r24"]["mm"], r["r24"]["trace"], "r24"))
    return reps, iR == "3", flags


def parse_ogimet_rain(text):
    """OGIMET getsynop CSV -> list of (date, hour, minute, reports, zero, flags).

    The minute is kept, unlike parse_ogimet(): some stations send automatic
    bulletins every ten minutes, and only the main hours carry periods a
    daily total can be built from.
    """
    out = []
    for line in text.splitlines():
        p = line.strip().split(",")
        if len(p) < 7 or not p[1].isdigit():
            continue
        date = f"{p[1]}-{int(p[2]):02d}-{int(p[3]):02d}"
        reps, zero, flags = rain_reports(",".join(p[6:]))
        out.append((date, int(p[4]), int(p[5]), reps, zero, flags))
    return out
