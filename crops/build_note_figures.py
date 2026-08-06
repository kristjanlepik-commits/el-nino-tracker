"""Emit the figures the first Note needs, as a small readable file.

WHY THIS EXISTS. Editor went looking for the piece's central number and
could not find it. Everything they had came through chat messages, and
today the Greece figure went through four people's hands and came out
four different numbers.

The numbers WERE in `stress_current.json`. The file is 4.7 MB over 123
places, England is nested two levels down as a region, and the country
is named `U.K. of Great Britain and Northern Ireland`, so:

    searching "United Kingdom"  finds nothing
    searching "England"         finds nothing at place level
    searching "UK"              FINDS UKRAINE

That last one is the dangerous one. It does not fail, it returns a
plausible wrong country. "Present in the payload" and "findable by the
person who needs it" are different properties, and only the first was
ever true here.

Every figure carries `source`, a path into stress_current.json, so
editor's review is a lookup rather than a judgement of plausibility. A
number recalled wrongly looks exactly like a number looked up
correctly.

DERIVED, NEVER TYPED. Re-run it and the figures move with the payload;
nothing here can go stale while looking authoritative.

    .venv/bin/python crops/build_note_figures.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "stress_current.json"
OUT = HERE / "data" / "note_figures.json"

UK = "U.K. of Great Britain and Northern Ireland"


def place(doc, name):
    for i, p in enumerate(doc["places"]):
        if p["place"] == name:
            return i, p
    raise SystemExit(f"{name!r} not in the payload")


def region(doc, country, reg):
    ci, p = place(doc, country)
    for ri, r in enumerate(p["regions"]):
        if r["region"] == reg:
            return ci, ri, r
    raise SystemExit(f"{reg!r} not under {country!r}")


def main() -> int:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    ci, uk = place(doc, UK)
    ei, ri, eng = region(doc, UK, "England")
    fi, fr = place(doc, "France")

    def rate_of(obj, path):
        r = obj["rate"]
        return {
            "change": r["value"],
            "rank": r["rank"], "of": r["of"],
            "start_value": r["start_value"],
            "start_rank": r["start_rank"], "start_of": r["start_of"],
            "statement": r["statement"],
            "holds_after_start_control": r["_start_control"]["holds"],
            "gap_to_next_year": r["_start_control"]["gap_to_next_year"],
            "source": path,
        }

    figs = {
        "_what": "Figures for the first Note. Derived from "
                 "crops/data/stress_current.json, never typed. Re-run "
                 "crops/build_note_figures.py to refresh.",
        "_dekad": doc["dekad"],
        "_observation_window": "the ten days ending 20 July 2026",
        "_uk_naming": "the UK is named "
                      f"{UK!r} in the payload, and England is a REGION "
                      "under it, not a place. Searching 'UK' returns "
                      "Ukraine.",
        "_attribution": "Not ENSO-linked. Channel call, not inherited: "
                        "no established pathway ties northern European "
                        "summer vegetation to ENSO, and no European pair "
                        "qualified as ENSO-linked in the channel's own "
                        "correlation work.",
        "_no_forecast": "Every figure here describes what has already "
                        "been measured. The rate predicts poorly (a "
                        "record rate at an ordinary level is followed by "
                        "a bad level 2.9% of the time against 1.3% "
                        "otherwise), so nothing here licenses a sentence "
                        "about what comes next.",

        "england": {
            "rate": rate_of(eng, f"places[{ci}].regions[{ri}].rate"),
            "level_now": {
                "value": eng["value"], "rank": eng["rank"], "of": eng["of"],
                "statement": eng["statement"],
                "source": f"places[{ci}].regions[{ri}]",
            },
            "level_2025_same_dekad": {
                "value": eng["series"].get("2025"),
                "means": "where 2025 ENDED at this dekad, against 2026's "
                         f"{eng['value']}. The piece turns on this: 2025 "
                         "fell almost as fast and finished far worse.",
                "source": f"places[{ci}].regions[{ri}].series['2025']",
            },
        },

        "france": {
            "rate": rate_of(fr, f"places[{fi}].rate"),
            "crop_outcome_level_now": {
                "instrument": "Vegetation, cumulative",
                "rank": 20, "of": 26,
                "statement": fr["magnitude"]["statement"],
                "means": "BETTER than average. 19 of the 26 years were "
                         "worse at this date.",
                "source": f"places[{fi}].magnitude",
            },
            "instruments_at_a_record_by_LEVEL": [
                {"name": i["name"], "rank": i["rank"], "of": i["of"],
                 "worse_is": i["worse_is"], "value": i["value"],
                 "source": f"places[{fi}].instruments"}
                for i in fr["instruments"]
                if i.get("available") and i["rank"] == 1
            ],
            "_the_distinction_editor_asked_about": (
                "These are two DIFFERENT quantities and they do not agree "
                "the way they appear to. The four record ranks are LEVELS "
                "at this dekad, on current vegetation, water "
                "satisfaction, rainfall and temperature. The rate is a "
                "CHANGE, over four dekads, on the season-cumulative crop "
                "indicator. That cumulative indicator is at rank 20 of "
                "26, better than average. So: the weather is at a record, "
                "the cumulative crop signal is falling faster than in any "
                "year on record, and the crop outcome itself has not "
                "responded yet. State them separately."
            ),
        },

        "also_hold_after_the_control": [
            {"place": p["place"], "change": p["rate"]["value"],
             "rank": p["rate"]["rank"],
             "level": p["magnitude"]["statement"],
             "source": f"places[{i}].rate"}
            for i, p in enumerate(doc["places"])
            if p["place"] in ("Hungary", "Slovakia")
        ],
    }

    OUT.write_text(json.dumps(figs, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(HERE.parent)} "
          f"({OUT.stat().st_size / 1024:.0f} KB)")
    print(f"  England rate  : {figs['england']['rate']['statement']}")
    print(f"  England level : {figs['england']['level_now']['statement']}")
    print(f"  England 2025  : {figs['england']['level_2025_same_dekad']['value']}")
    print(f"  France rate   : {figs['france']['rate']['statement']}")
    print(f"  France crop   : {figs['france']['crop_outcome_level_now']['statement']}")
    print(f"  France records by LEVEL: "
          f"{[i['name'] for i in figs['france']['instruments_at_a_record_by_LEVEL']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
