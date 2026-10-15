"""Barcelona, 3 October 2026: the first station piece on the floods channel.

Renders through templates/fast_reaction.py, like every flood piece, but is
not built by floods/build_piece.py: that builder takes an area-mean
fortnight against its own median, and this is one gauge's wettest day
against its own record. Different claim, different payload, same template.

Inputs, each read from where its owner put it:
  copy        copy/tortosa_draft.md on origin/main (editor)
  judgement   floods/data/spain_dana_2026-10_stations.json on origin/main
              (floods): the rank, the unbroken-run start, the record flags
  series      Fabra's wettest day of each year, annual_max_1day in the
              same payload (floods, 5cdcabc6). 2026 is a partial year and
              not in it, so its mark is the judged day itself.
  sea figure  floods/data/europe_ingredients_2026-10.json, sst_sept (floods)

The series is checked against the judgement before anything renders. If
the strip and the headline could disagree, the build refuses.

Run:  .venv/bin/python design/make_barcelona_piece.py --preview
      .venv/bin/python design/make_barcelona_piece.py          (publishes)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from floods.build_piece import _pretty, _staleness     # noqa: E402
from templates.fast_reaction import render             # noqa: E402

SID = "0200E"
DAY = "2026-10-03"
# The storm the page cites, not only Fabra's three days: the body quotes
# Tortosa on 1 October, so the closed-event line has to cover it (CPO).
WINDOW = {"start": "2026-10-01", "end": "2026-10-05"}
PATH = "/floods/barcelona-2026-10-03/"
PREVIEW = Path("/private/tmp/claude-505/-Users-admin-Documents-Claude-"
               "Projects-El-Nino-Tracker/963b8065-d8cb-408a-9195-"
               "33d00aeda096/scratchpad/barcelona_preview")


def _origin(path):
    """A file as origin/main has it. The shared tree lags origin."""
    return subprocess.run(["git", "show", "origin/main:" + path], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout


def copy():
    """Headline and paragraphs from the editor's draft, untouched."""
    sec, out = None, {"headline": [], "body": []}
    for line in _origin("copy/tortosa_draft.md").splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
            continue
        if sec in out:
            out[sec].append(line)
    paras = [" ".join(p.split()) for p in "\n".join(out["body"]).split("\n\n")]
    return " ".join(out["headline"]).strip(), [p for p in paras if p]


def station():
    st = json.loads(_origin("floods/data/spain_dana_2026-10_stations.json"))
    return next(s for s in st["stations"] if s["id"] == SID)


def series(st):
    """Wettest day of each year from the unbroken start, as floods emit it.

    Years below the completeness floor floods judged with are refused
    rather than dropped: a hole in the strip would read as a dry year.
    """
    since, ann = st["unbroken_since"], st["annual_max_1day"]
    best, thin = {}, []
    for y in range(since, 2026):
        row = ann.get(str(y))
        if row is None or row["days_reported_frac"] < 0.90:
            thin.append(y)
        else:
            best[y] = row["mm"]
    if thin:
        raise SystemExit("REFUSING TO RENDER: years below 90%% reported "
                         "inside the unbroken run: %s" % thin)
    best[2026] = st["1day"]["mm"]
    return best


def sea():
    """The one sea figure the copy quotes, checked before it is sourced."""
    d = json.loads(_origin("floods/data/europe_ingredients_2026-10.json"))
    for basin in ("Western Mediterranean", "Central Mediterranean"):
        row = next(v for k, v in d["sst_sept"].items() if k.startswith(basin))
        if row["rank"][0] != 1 or row["since"] != 1940:
            raise SystemExit("REFUSING TO RENDER: %s September SST is rank "
                             "%s since %s, not 1st since 1940"
                             % (basin, row["rank"], row["since"]))


def check(st, best):
    """The strip must say what the headline says, or nothing renders."""
    one = st["1day"]
    problems = []
    if not (one["record_unbroken"] and one["rank_unbroken"] == 1):
        problems.append("floods no longer judge 3 October a record in the "
                        "unbroken run")
    if one["start"] != DAY:
        problems.append("floods' wettest day is %s, not %s" % (one["start"], DAY))
    others = {y: v for y, v in best.items() if y != 2026}
    if others and max(others.values()) >= one["mm"]:
        problems.append("a year in the strip reaches %.1f mm" % one["mm"])
    missing = [y for y in range(st["unbroken_since"], 2026) if y not in best]
    if missing:
        problems.append("no data for %s" % missing)
    if problems:
        raise SystemExit("REFUSING TO RENDER, strip and judgement disagree:\n  "
                         + "\n  ".join(problems))


def piece(today):
    head, paras = copy()
    st = station()
    since = st["unbroken_since"]
    best = series(st)
    check(st, best)
    sea()
    one, three = st["1day"], st["3day"]
    return {
        "channel": "flood",
        # SAYS RAIN ON THE PAGE. The URL and the section say floods while
        # flood extent is not assessed; the eyebrow is the cheap place to
        # say what this record is of (CPO, from the persona read).
        "region": "Barcelona",
        "window": "rain record, 3 October 2026",
        "measured": "published " + _pretty(today),
        "staleness": _staleness(WINDOW, today),
        "path": PATH,
        "claim": head,
        "standfirst": paras[0],
        "body": paras[1:],
        "value": {
            "display": "%.1f mm" % one["mm"],
            "caption": "in one day at the Fabra station, 3 October",
        },
        "chart": {
            "label": "Wettest day of each year at Barcelona Fabra, %d to 2026"
                     % since,
            "series": [{"x": y, "y": v} for y, v in sorted(best.items())],
            "current_x": 2026,
            "unit": " mm",
            "decimals": 1,
            "header": "WETTEST DAY OF EACH YEAR · BARCELONA FABRA "
                      "· MM · ONE SLOT PER YEAR",
            "lo": 0,
            "noun": "year",
            "noun_plural": "years",
            "current_kicker": "3 OCT 2026",
            "diverging": False,
            "annotations": [],
        },
        "instruments": [
            {"name": "Rainfall, one day",
             "detail": "AEMET rain gauge, Barcelona Fabra",
             "value": "%.1f mm" % one["mm"],
             "rank": "highest since %d; %s since %d, with gaps"
                     % (since, _nth(one["rank_full"]), one["full_from"]),
             "state": "measured"},
            {"name": "Rainfall, three days",
             "detail": "AEMET rain gauge, Barcelona Fabra",
             "value": "%.1f mm" % three["mm"],
             "rank": "highest since %d; %s since %d, with gaps"
                     % (since, _nth(three["rank_full"]), three["full_from"]),
             "state": "measured"},
            {"name": "Flood extent",
             "detail": "satellite surface water",
             "value": "not assessed",
             "rank": "",
             "state": "not_assessed"},
        ],
        # Floods' ruling, 15 October: no established ENSO pathway for
        # European autumn rain (Science, 12 October), and the HANZE count
        # against ONI is r = -0.02.
        "attribution": "non_enso",
        "notes": {
            "what_this_is": (
                "Daily rainfall at one gauge, AEMET's Barcelona Fabra "
                "station, against its own record. The chart shows the "
                "wettest day of each year since %d, the first year of the "
                "station's unbroken record, meaning every year since has at "
                "least 90%% of its days reported. The result does not "
                "change at any threshold from 70%% to 100%%. The 2026 mark "
                "is %s itself." % (since, _pretty(DAY))),
            "what_this_is_not": (
                "Not a measurement of flooding, and not an area total: one "
                "gauge can catch a downpour its neighbours miss. Flood "
                "extent is not assessed for European regions: the satellite "
                "screen passed none of the six tested, because week-to-week "
                "visibility varies enough that a ranking would reflect "
                "cloud cover, not flooding."),
        },
        "source": [
            {"name": "AEMET (Agencia Estatal de Meteorología)",
             "detail": "daily climatological values, station 0200E",
             "as_of": _pretty(st_end())},
            {"name": "Copernicus ERA5",
             "detail": "monthly sea surface temperature, Septembers 1940 "
                       "to 2026 (2026 preliminary)",
             "as_of": "12 October 2026"},
        ],
    }


def st_end():
    """How far the gauge reading reaches: the end of floods' judged window."""
    st = json.loads(_origin("floods/data/spain_dana_2026-10_stations.json"))
    return st["window"][1]


def _nth(n):
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(
        n if n < 20 else n % 10, "th"))


def main():
    from datetime import date
    today = date.today().isoformat()
    p = piece(today)
    if "--preview" in sys.argv:
        out = PREVIEW / PATH.strip("/") / "index.html"
    else:
        out = ROOT / "docs" / PATH.strip("/") / "index.html"
        if out.exists():
            raise SystemExit("REFUSING TO REBUILD: %s exists (invariant 5)."
                             % out.relative_to(ROOT))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(p, root_prefix="../../"))
    print("wrote", out)


if __name__ == "__main__":
    main()
