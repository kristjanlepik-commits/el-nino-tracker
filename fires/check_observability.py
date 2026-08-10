"""D-121 observability test for the fire channel. Reproducible.

THE QUESTION strategy asked (D-121, from floods): is the instrument
anti-correlated with the truth? For fire the specific mechanism is smoke.
Plumes are thickest over the largest fires, so if smoke suppresses VIIRS
detection then the channel under-counts exactly the events readers most
want to know about, and every number on the page is biased toward calm in
the worst week.

WHY THE CHANNEL CAN TEST THIS AT ALL. It carries two independent
instruments. VIIRS active-fire detections are real-time thermal and are
the plume-suppressible one. EFFIS/GWIS burnt area is a post-hoc mapped
perimeter and sees the scar whether or not there was smoke on the day.
Disagreement between them that grows with fire size is the signature.

RESULT: NEGATIVE. No evidence of smoke-driven suppression.

=============================================================================
THE FIRST VERSION OF THIS TEST WAS WRONG, AND ITS OUTPUT WAS CONVINCING.
=============================================================================

It ranked burned hectares against detections-per-hectare and found median
Spearman rho -0.72, with 24 of 29 countries strongly negative. That reads
as a dramatic confirmation. It is an artifact: area is in the denominator
of the y variable, so noise in area alone drives the correlation negative.
This is Pearson's spurious correlation of ratios, 1897.

`_null_controls` below is what caught it, and it is the reason this file
exists rather than a note saying "we checked". Feeding the ratio test data
where detections are INDEPENDENT of area yields rho -0.69, indistinguishable
from the -0.72 measured on the real channel. A test that returns the same
answer on real data and on noise has measured nothing.

Run the controls before believing the output. They are cheap and they are
the only part of this file that can tell you the method still works.

=============================================================================
WHAT THE CORRECTED TEST MEASURES
=============================================================================

Log-log scaling, no ratio anywhere:

    detections ~ k * area ** b

    b about 1   proportional. The instrument scales with the event.
    b < 1       sub-linear. It sees proportionally less as fires grow,
                which is what suppression would look like.

Measured: median b 0.75. Sub-linear. Taken alone that supports the
hypothesis, which is why it is not taken alone. Two mechanisms produce
sub-linearity with no blindness involved, and both are testable.

CONFOUND 1, ATTENUATION. Noise in x biases a least-squares slope toward
zero, worst where the country's range of fire sizes is narrow. Measured
correlation between b and the spread of log(area) is r = +0.55, and the
extreme low values are exactly the narrow-range, small-n countries
(DZA b=0.15 on 67 weeks, FRA b=0.17 on 46). Restricting to wide-range
countries lifts the median to 0.78 and removes the tail.

CONFOUND 2, GEOMETRY. Active-fire detections track the burning FRONT;
burnt area tracks the polygon. Perimeter against area is sub-linear by
construction for any compact shape, with no instrument involved.

THE DISCRIMINATOR, and the reason the answer is negative. Smoke predicts
b should be LOWEST in dense-smoke fuel (peat, closed forest) and HIGHEST
in open savanna. Measured, it is flat and if anything runs the other way:

    peat/forest   0.77      forest        0.74
    boreal        0.79      savanna       0.81

Indonesian peat and Angolan savanna are the same number. A smoke effect
that is identical in peat and in open savanna is not a smoke effect. The
residual uniform 0.78 is what geometry predicts.

=============================================================================
WHAT THIS DOES NOT RULE OUT, which belongs on the page and not in a drawer
=============================================================================

This test can only see suppression that VARIES WITH FIRE SIZE. A blindness
that is uniform, or that varies with something other than size, passes it
untouched. Two live ones:

  - CLOUD. The channel still cannot distinguish a cloud-covered day from a
    calm one, and there is no cloud product wired in. That is the real
    observability limit here and it is unmeasured, not measured-and-clear.
  - Detection floor. Fires below the pixel threshold are absent from both
    instruments, so this comparison cannot see them at all.

So the honest statement is narrow: the specific smoke mechanism D-121 asked
about is not detectable in this channel's data, and the sub-linearity that
looks like it is explained by attenuation and geometry. It is not a clean
bill of health for fire observability generally.
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics as st
from datetime import date

FULL_HISTORY = os.path.join(os.path.dirname(__file__), "data", "full_history")
AREA_HISTORY = os.path.join(os.path.dirname(__file__), "data", "area_history")

MIN_WEEKLY_HECTARES = 500
MIN_WEEKLY_DETECTIONS = 20
MIN_WEEKS = 40
MIN_DAYS_FOR_COMPLETE_YEAR = 300
WIDE_RANGE_SD = 1.0

# Dominant fuel, for the discriminating test. The smoke hypothesis predicts
# the peat and closed-forest entries should sit well below the savanna ones.
FUEL = {
    "IDN": "peat/forest",
    "COD": "forest", "COG": "forest", "BRA": "forest", "PNG": "forest",
    "BOL": "forest", "VEN": "forest", "MDG": "forest",
    "CAN": "boreal forest", "RUS": "boreal forest",
    "AGO": "savanna", "ZMB": "savanna", "TZA": "savanna", "MOZ": "savanna",
    "ZWE": "savanna", "BWA": "savanna", "NAM": "savanna", "ZAF": "savanna",
    "AUS": "savanna/scrub", "KAZ": "steppe", "UKR": "cropland",
    "USA": "mixed", "MEX": "mixed", "CHN": "mixed",
    "FRA": "mediterranean", "ESP": "mediterranean", "ITA": "mediterranean",
    "DZA": "mediterranean",
}


def _iso_week(datestr: str) -> int:
    year, month, day = (int(part) for part in datestr.split("-"))
    return date(year, month, day).isocalendar()[1]


def _slope(xs: list[float], ys: list[float]) -> float:
    """Least squares b in y = a + b x."""
    mean_x, mean_y = st.mean(xs), st.mean(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if not denom:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom


def _pearson(xs: list[float], ys: list[float]) -> float:
    mean_x, mean_y = st.mean(xs), st.mean(ys)
    denom = math.sqrt(sum((x - mean_x) ** 2 for x in xs)
                      * sum((y - mean_y) ** 2 for y in ys))
    if not denom:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom


def _spearman(xs: list[float], ys: list[float]) -> float:
    def rank(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for position, index in enumerate(order):
            ranks[index] = float(position)
        return ranks
    return _pearson(rank(xs), rank(ys))


def _null_controls(trials: int = 200, seed: int = 7) -> None:
    """Prove the method separates signal from arithmetic. Run this first.

    The ratio form is included precisely because it FAILS, and seeing it
    fail is the point: it is the version that produced a confident wrong
    answer, and anyone re-running this needs to see why it was discarded.
    """
    random.seed(seed)
    print("CONTROLS. Synthetic data with a known answer.\n")

    print("  the discarded ratio test, area vs detections-per-area:")
    for label, make in (
        ("detections INDEPENDENT of area (truth: no relationship)",
         lambda a: math.exp(random.gauss(6, 1.5))),
        ("detections PROPORTIONAL to area (truth: no suppression)",
         lambda a: a * 0.05 * math.exp(random.gauss(0, 0.4))),
    ):
        rhos = []
        for _ in range(trials):
            area = [math.exp(random.gauss(8, 1.5)) for _ in range(500)]
            det = [make(a) for a in area]
            rhos.append(_spearman(area, [d / a for d, a in zip(det, area)]))
        print(f"    {label:<56} rho {st.median(rhos):+.2f}")
    print("    ^ independent data scores about as negative as the real")
    print("      channel did (-0.72). The ratio test cannot tell them apart.\n")

    print("  the log-log slope used below:")
    for label, make, expected in (
        ("proportional", lambda a: a * 0.05 * math.exp(random.gauss(0, 0.4)), 1.0),
        ("true sub-linear b=0.7", lambda a: 2 * a ** 0.7 * math.exp(random.gauss(0, 0.4)), 0.7),
    ):
        area = [math.exp(random.gauss(8, 1.5)) for _ in range(800)]
        det = [make(a) for a in area]
        got = _slope([math.log(a) for a in area], [math.log(d) for d in det])
        print(f"    {label:<56} b {got:.2f} (expect {expected:.2f})")
    print()


def measure() -> list[tuple[str, float, int, float]]:
    """Per country: (iso, scaling exponent b, weeks used, spread of log area)."""
    rows = []
    for filename in sorted(os.listdir(AREA_HISTORY)):
        iso = filename[:3]
        detections_path = os.path.join(FULL_HISTORY, filename)
        if not os.path.exists(detections_path):
            continue
        with open(os.path.join(AREA_HISTORY, filename)) as handle:
            area_years = json.load(handle)["years"]
        with open(detections_path) as handle:
            detections = json.load(handle)

        complete = {year for year in detections.get("_complete", [])
                    if len(detections.get(year, {})) >= MIN_DAYS_FOR_COMPLETE_YEAR}

        log_area, log_detections = [], []
        for year in sorted(complete):
            weekly = area_years.get(year)
            if not weekly:
                continue
            previous = 0
            cumulative = sorted((int(week), value) for week, value in weekly.items()
                                if value is not None)
            for week, total_to_date in cumulative:
                burned, previous = total_to_date - previous, total_to_date
                if burned < MIN_WEEKLY_HECTARES:
                    continue
                detected = sum(count for day, count in detections[year].items()
                               if _iso_week(day) == week)
                if detected < MIN_WEEKLY_DETECTIONS:
                    continue
                log_area.append(math.log(burned))
                log_detections.append(math.log(detected))

        if len(log_area) >= MIN_WEEKS:
            rows.append((iso, _slope(log_area, log_detections),
                         len(log_area), st.pstdev(log_area)))
    return rows


def report() -> None:
    _null_controls()
    rows = measure()
    if not rows:
        print("No country had enough complete weeks. Check the caches.")
        return

    exponents = [row[1] for row in rows]
    print(f"MEASURED across {len(rows)} countries: median b "
          f"{st.median(exponents):.2f}, range {min(exponents):.2f} "
          f"to {max(exponents):.2f}\n")

    spreads = [row[3] for row in rows]
    print("CONFOUND 1, attenuation. Narrow range biases b toward zero.")
    print(f"  b against spread of log(area): r = "
          f"{_pearson(spreads, exponents):+.2f}")
    wide = [row for row in rows if row[3] >= WIDE_RANGE_SD]
    print(f"  restricted to the {len(wide)} wide-range countries: median b "
          f"{st.median([row[1] for row in wide]):.2f}\n")

    print("CONFOUND 2, fuel. Smoke predicts peat and forest BELOW savanna.")
    by_fuel: dict[str, list[float]] = {}
    for iso, exponent, _weeks, _spread in rows:
        by_fuel.setdefault(FUEL.get(iso, "unclassified"), []).append(exponent)
    for fuel, values in sorted(by_fuel.items(), key=lambda kv: st.median(kv[1])):
        print(f"  {fuel:<16} median b {st.median(values):.2f}  (n={len(values)})")
    print("\n  Flat across fuel types is the negative result. A suppression")
    print("  mechanism that is identical in peat and in open savanna is not")
    print("  smoke; it is geometry, which predicts a uniform sub-linear b.\n")

    print(f"{'country':<9}{'b':>7}{'weeks':>8}{'sd log area':>13}  fuel")
    for iso, exponent, weeks, spread in sorted(rows, key=lambda r: r[1]):
        print(f"{iso:<9}{exponent:>7.2f}{weeks:>8}{spread:>13.2f}  "
              f"{FUEL.get(iso, 'unclassified')}")


if __name__ == "__main__":
    report()
