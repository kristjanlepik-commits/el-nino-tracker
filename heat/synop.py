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
