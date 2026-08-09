"""Does the heat index still work when the weather changes?

Kristjan's specification, 2026-08-08, made checkable rather than aspirational:

    We should not hardcode heat logic to anything, every element should be
    adjustable based on data. Some part of the world will have normal, some
    will have extremes. We show where the extremes are and how hard. No
    matter what the data does, the setup shows what is happening.

Product's test for it, which is the version this file implements: render the
index against a payload where NO city is abnormal, and against the mirror
where every city is at a record. Both ends have to produce a coherent page.

WHY IT IS A SCRIPT AND NOT A NOTE. The failure this catches is a page tuned
to one August. A scale, a count or a sentence that is only true of this
summer's distribution reads as verified today and goes false in silence, and
nothing else we run would notice: the payload stays valid, the guards stay
green, and the page simply starts describing a summer that has ended.

It renders into a temporary directory and never writes to docs/.

    .venv/bin/python design/check_heat_extremes.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
VENV = R / ".venv/bin/python"
PY = str(VENV if VENV.exists() else sys.executable)

# Everything make_heat_index.py imports or reads, directly or through
# run_brief. Copied rather than symlinked so a mutation cannot reach the
# real payload.
# What to copy into the scratch tree. Derived from git rather than listed,
# because the list version was a hand-maintained allowlist and it failed the
# first time an input arrived that nobody remembered to add: copy/ landed,
# the generator started requiring it, and this test reported the index as
# broken at both extremes when the only thing missing was a file it had
# declined to copy. A test that has to be told about each new input will
# eventually be wrong about the build rather than the thing under test.
COPY = sorted({p.split("/")[0] for p in subprocess.run(
    ["git", "ls-files"], cwd=R, capture_output=True, text=True,
    check=True).stdout.split()})


def calm(nights, series):
    """Nobody is having an unusual summer. Both files move together: setting
    a rank without lowering the count leaves 2026 drawing a full bar while
    claiming to be 40th, which is not a calm payload, it is an inconsistent
    one. The list guard catches that, correctly, and it is not what we are
    testing here."""
    for c in nights["cities"].values():
        c["days"]["rank"].update(value=40, of_years=76, percentile=48.0)
        c["days"]["days_2026"]["95"] = 2
    nights["day_headline"].update(records=0, record_cities=[],
                                  of_cities=len(nights["cities"]))
    nights["headline"]["lead"].update(at_day_record=0,
                                      of_cities=len(nights["cities"]))
    for c in series["cities"].values():
        y = c["years"].get("2026")
        if y and y.get("days_to_cut"):
            y["days_to_cut"]["95"] = 2


def blazing(nights, series):
    """Every city at its own record."""
    for c in nights["cities"].values():
        c["days"]["rank"].update(value=1, percentile=100.0)
    nights["day_headline"].update(records=len(nights["cities"]),
                                  of_cities=len(nights["cities"]))


def run(tag, mutate):
    tmp = Path(tempfile.mkdtemp(prefix="heat-extremes-"))
    try:
        for p in COPY:
            src = R / p
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, tmp / p, symlinks=True)
            else:
                shutil.copy(src, tmp / p)
        fn, fs = tmp / "heat/data/city_nights.json", tmp / "heat/data/city_series.json"
        nights, series = json.loads(fn.read_text()), json.loads(fs.read_text())
        mutate(nights, series)
        fn.write_text(json.dumps(nights))
        fs.write_text(json.dumps(series))
        r = subprocess.run([PY, "design/make_heat_index.py"], cwd=tmp,
                           capture_output=True, text=True)
        if r.returncode != 0:
            last = (r.stderr or r.stdout).strip().splitlines()[-1]
            print(f"  FAIL  {tag}\n        {last[:180]}")
            return False
        html = (tmp / "docs/heat/index.html").read_text()
        svg = re.search(r'<svg viewBox="0 0 \d+ \d+".*?</svg>', html, re.S).group(0)
        fills = {k: len(re.findall(rf'fill="var\(--{k}\)"', svg))
                 for k in ("f3", "f2", "f0")}
        # THE POINT OF THE TEST. All three states stay drawn and labelled at
        # both ends, so a reader can always see that the scale has an end
        # nobody reached. A legend that hid its empty rungs would look
        # tidier here and would be the page telling them less.
        rungs = len(re.findall(r'class="ks"', html))
        marks = len(re.findall(r"<circle", svg))
        ok = rungs == 3 and marks == sum(fills.values()) and marks > 0
        print(f"  {'PASS' if ok else 'FAIL'}  {tag}: {marks} marks, "
              f"fills {fills}, {rungs} legend rungs drawn")
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print("heat index, rendered against both ends of the weather")
    results = [run("no city abnormal", calm),
               run("every city at a record", blazing)]
    if not all(results):
        raise SystemExit("the index does not hold at both ends")
    print("both ends hold.")
