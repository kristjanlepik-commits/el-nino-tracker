"""Does the payload still make sense when the weather is not what it is today?

Kristjan's principle, 2026-08-08: "We should not hardcode heat logic to
anything, every element should be adjustable based on data. No matter what
the data does, the setup shows what is happening."

Product's acceptance test, which is what makes it checkable rather than
aspirational: feed the pipeline a synthetic dataset in which NOTHING is
abnormal, and one in which EVERYTHING is at a record. Both must produce a
coherent payload. Anything that only works for the summer of 2026 is
hardcoded.

This rewrites the CURRENT year in a copy of the series and re-runs the
emitter against it. It touches nothing real: the live payload is never the
output path.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "heat" / "data" / "city_series.json"
CUR = "2026"


def synth(mode):
    """Return a series with the current year rewritten to `mode`."""
    S = json.loads(SERIES.read_text())
    for c, v in S["cities"].items():
        prior = [d for y, d in v["years"].items()
                 if y != CUR and d["usable_to_cut"]]
        if not prior:
            continue
        cur = v["years"][CUR]
        n = sorted(d["nights_to_cut"] for d in prior)
        for pct in ("90", "95", "99"):
            dd = sorted(d["days_to_cut"][pct] for d in prior)
            if mode == "calm":
                cur["days_to_cut"][pct] = dd[len(dd) // 2]
            else:
                cur["days_to_cut"][pct] = max(dd) + 5
        cur["nights_to_cut"] = (n[len(n) // 2] if mode == "calm"
                                else max(n) + 5)
    return S


def run(mode):
    S = synth(mode)
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "series.json"
        op = Path(td) / "out.json"
        sp.write_text(json.dumps(S))
        env = {"HEAT_SERIES": str(sp)}
        r = subprocess.run(
            [sys.executable, str(ROOT / "heat/emit_city_nights.py"), str(op)],
            capture_output=True, text=True,
            env={**__import__("os").environ, **env})
        if r.returncode != 0:
            return None, r.stderr.strip()
        return json.loads(op.read_text()), ""


def main() -> int:
    bad = 0
    for mode, label in (("calm", "NOTHING abnormal"),
                        ("record", "EVERYTHING at a record")):
        p, err = run(mode)
        print(f"\n=== {label} ===")
        if p is None:
            print(f"  EMIT FAILED: {err}")
            bad += 1
            continue
        h, dh, g = p["headline"], p["day_headline"], p["geography"]
        print(f"  lead        : {h['lead']['claim']}")
        print(f"  night recs  : {h['records']} of {h['of_cities']}")
        print(f"  day recs    : {dh['records']} of {dh['of_cities']}")
        print(f"  may_say_worst: {dh['may_say_worst_on_record']}")
        print(f"  all elevated: {g['all_elevated_on_days']}")
        print(f"  lowest      : {g['lowest_day_percentile']}")
        print(f"  not_elevated: {h['lead']['not_elevated'][:5]}")
        print(f"  scale domain: {g['map']['scale_domain']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
