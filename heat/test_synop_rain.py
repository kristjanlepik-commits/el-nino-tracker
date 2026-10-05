"""Hand-decoded cases for the SYNOP rain reader (D-321).

synop.py's own header says it must not grow without a test suite, because
every new group is another chance to return a plausible wrong number. This
is that suite for rain. Each case was decoded by hand against WMO-No. 306
code tables 1819 (iR), 3590 (RRR) and 4019 (tR), and every one is a trap
that a regex or a naive scan falls into.

    .venv/bin/python heat/test_synop_rain.py
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synop  # noqa: E402
import station_rain as SR  # noqa: E402

FAIL = []


def check(name, got, want):
    if got != want:
        FAIL.append(f"{name}: got {got!r}, want {want!r}")


def reps(msg):
    return synop.rain_reports(msg)


# Real Zagreb Gric bulletin: 000 in section 1 beside 7R24 = 0000.
check("zero 000 read as zero",
      reps("AAXX 01061 14236 12/75 42302 10092 20072 30080 40274 56/// "
           "60002 82071 333 20090 31005 70000=="),
      ([(12, 0.0, False, "s1"), (24, 0.0, False, "r24")], False, []))

# Real Budapest bulletin: 990 is TRACE, 7R24 9999 is trace.
check("trace codes",
      reps("AAXX 01061 12843 11672 73301 10163 20125 30001 40166 58001 "
           "69902 72598 81988 333 20141 55078 79999 81940="),
      ([(12, 0.0, True, "s1"), (24, 0.0, True, "r24")], False, []))

check("tenths 991-999", reps("AAXX 01061 12843 11672 73301 69952 333 70005=")[0],
      [(12, 0.5, False, "s1"), (24, 0.5, False, "r24")])

check("989 is open-ended", reps("AAXX 01061 12843 11672 73301 69894=")[2],
      ["s1_989_or_more"])

# THE CLOUD TRAP: N=6 oktas makes Nddff read 6ddff. It is not rain.
check("Nddff with six oktas is not rain",
      reps("AAXX 01001 12843 45970 60801 10121 20072 30043 40212 90030="),
      ([], False, []))

# Wind of 99 units adds 00fff after Nddff; it is skipped positionally.
check("00fff skipped",
      reps("AAXX 01061 12843 11672 73399 00120 10163 60122=")[0],
      [(12, 12.0, False, "s1")])

# iR 3 is NONE FELL, iR 4 is NOT OBSERVED. Only the first is a zero.
check("iR 3 is a zero", reps("AAXX 01001 12843 35970 60801 10121="),
      ([], True, []))
check("iR 4 is not a zero", reps("AAXX 01001 12843 45970 60801 10121="),
      ([], False, []))

# iR 1 says section 1 only: a section-3 group is ignored and flagged.
check("group iR does not license",
      reps("AAXX 01061 12843 11672 73301 60122 333 60051=")[2],
      ["s3_present_but_iR_1"])

# Section 3 is ascending-ordered: 1 and 2 groups before 6 are temperatures.
check("section 3 rain after extremes",
      reps("AAXX 01001 12843 25/70 /0701 10121 333 10250 20141 60005 90710=")[0],
      [(1, 0.0, False, "s3")])

# THE RADIATION TRAP: after 55SSS, a 6xxxx may be radiation. Not read.
check("radiation ambiguity",
      reps("AAXX 01061 12843 21672 73301 10163 333 20141 55078 20123 60104 79999="),
      ([(24, 0.0, True, "r24")], False, ["s3_ambiguous_radiation"]))

# Tenths in 7R24: 0121 is 12.1 mm.
check("r24 tenths", reps("AAXX 02061 12843 11681 10203 60122 333 70121=")[0],
      [(12, 12.0, False, "s1"), (24, 12.1, False, "r24")])

check("NIL is absent", reps("AAXX 05181 14236 NIL="), ([], False, ["nil"]))


# ---- assembly: a day exists only where periods tile 24 h exactly.

def bull(day, hour, body):
    d = dt.date.fromisoformat(day)
    return (f"14236,{d.year},{d.month:02d},{d.day:02d},{hour:02d},00,"
            f"AAXX {d.day:02d}{hour:02d}1 14236 {body}=")


lines = [
    bull("2023-01-01", 18, "12/75 42302 60052"),     # 06-18: 5 mm
    bull("2023-01-02", 6, "12/75 42302 60032 333 70081"),  # 18-06: 3, r24 8.1
]
days, diag = SR.daily(lines, 6)
check("12+12 agrees with r24, r24 kept", days.get("2023-01-02"),
      (8.1, False, 1))

lines = [
    bull("2023-01-01", 18, "12/75 42302 60052"),
    bull("2023-01-02", 6, "12/75 42302 60032 333 70161"),  # r24 16.1 vs 8
]
days, diag = SR.daily(lines, 6)
check("disagreeing tilings refused", ("2023-01-02" in days,
      diag["conflict_days"]), (False, ["2023-01-02"]))

# One 12 h half missing: no tiling, NO DAY. Not 3 mm, not zero.
days, _ = SR.daily([bull("2023-01-02", 6, "12/75 42302 60032")], 6)
check("half a day is no day", days.get("2023-01-02"), None)

# iR 3 at an hour where the station reports 12 h becomes a 12 h zero.
lines = [bull("2023-01-0%d" % d, h, "12/75 42302 60012")
         for d in (1, 2, 3) for h in (6, 18)]
lines += [bull("2023-01-04", 18, "32/75 42302 10092"),
          bull("2023-01-05", 6, "12/75 42302 60022")]
days, diag = SR.daily(lines, 6)
check("iR 3 placed as zero", (days.get("2023-01-05"),
      diag["iR3_zeros_placed"]), ((2.0, False, 2), 1))

# iR 4 at the same hour is not placed: the day does not exist.
lines[-2] = bull("2023-01-04", 18, "42/75 42302 10092")
days, diag = SR.daily(lines, 6)
check("iR 4 not placed", days.get("2023-01-05"), None)


if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  " + f)
    sys.exit(1)
print("synop rain: all cases pass")
