"""Refresh data/oni_full_history.csv from the ONI fetcher.

CLAUDE.md says to refresh this file from fetchers/oni_history.py and never
by hand, and then no refresher existed, so it silently fell a season behind.
The editor caught it: JJA 2026 at +1.80 was in the fetch cache and not in
the production file, while a brief citing it was on its way to a reader.

This file is read by analog.py for a PUBLISHED chart, and by heat's
emit_lima.py and emit_city_nights.py. It is not ours alone.

THE GUARD. A refresh must be an APPEND. If CPC has revised an existing
value, that is a different event: it changes published history, it can
move another desk's output, and it needs a person rather than a script.
So this refuses on any changed value and prints what moved.
"""
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "oni_full_history.csv"
sys.path.insert(0, str(ROOT))
from fetchers import oni_history

ORD = ['DJF','JFM','FMA','MAM','AMJ','MJJ','JJA','JAS','ASO','SON','OND','NDJ']


def main():
    res = oni_history.fetch()
    if not res.ok:
        sys.exit(f"REFUSING: fetch failed: {res.error}")
    live = res.payload["by_year"]

    head, rows = [], []
    for line in CSV.read_text().splitlines():
        (head if line.startswith("#") else rows).append(line)
    header = rows[0]
    existing = {(int(r["year"]), r["season"].upper()): (float(r["oni"]), i)
                for i, r in enumerate(csv.DictReader(rows))}

    changed, added = [], []
    for y, seasons in live.items():
        for s, v in seasons.items():
            k = (int(y), s.upper())
            if k in existing:
                if abs(existing[k][0] - float(v)) > 1e-9:
                    changed.append((k, existing[k][0], float(v)))
            else:
                added.append((k, float(v)))

    if changed:
        print("REFUSING TO WRITE: CPC has revised values already published here.")
        for k, a, b in changed:
            print(f"  {k[0]} {k[1]}: {a} -> {b}")
        print("A revision to published history is not a refresh. It can move "
              "analog.py's chart and heat's pages. Raise it with a person.")
        sys.exit(1)

    if not added:
        print("  already current, nothing to add")
        return

    new = sorted(added, key=lambda t: (t[0][0], ORD.index(t[0][1])))
    out = head + [header] + rows[1:] + [f"{y},{s},{v}" for (y, s), v in new]
    CSV.write_text("\n".join(out) + "\n")
    print(f"  appended {len(new)} row(s), issued {res.issued}:")
    for (y, s), v in new:
        print(f"    {y},{s},{v}")


if __name__ == "__main__":
    main()
