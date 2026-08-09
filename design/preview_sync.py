"""Refresh heat-preview/ without destroying anyone's hand edits.

heat-preview/ is a copy of the build output that Kristjan and the editor
chat read, and edit. It is untracked, so an overwrite is unrecoverable.
Editor's copy was rescued twice today from snapshots taken minutes before
a rebuild would have destroyed it.

The safeguard I improvised first did not work, and the reason is worth
stating because it is not obvious: I compared heat-preview/ against a
baseline that I also updated, so any difference could be my own rebuild
as easily as somebody's edit, and the check could never tell them apart.

This does it properly. The baseline is written at the same instant as the
copy and never touched otherwise, so a file differing from its baseline
means exactly one thing: a human changed it.

    .venv/bin/python design/preview_sync.py           refuse if edited
    .venv/bin/python design/preview_sync.py --force   overwrite anyway
"""
import filecmp
import hashlib
import re
import shutil
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
SRC = R / "docs/heat"
DST = Path.home() / "Documents/Claude Projects/El Nino Tracker/heat-preview"
BASE = DST / ".baseline"


def payload_stamp():
    return hashlib.sha256(
        (R / "heat/data/city_nights.json").read_bytes()).hexdigest()[:12]


def stale_pages():
    """Pages built from a payload other than the one on disk.

    Editor found two city pages a night stale and found them by accident,
    cross-checking heat's social figures against page copy they had reviewed
    before the cut advanced. Both numbers were right when written. A page
    carrying a stale count is indistinguishable from a correct one, so this
    is the check that makes it visible rather than lucky.
    """
    want = payload_stamp()
    out = []
    for f in sorted(SRC.glob("*.html")):
        m = re.search(r"<!-- payload ([0-9a-f]{12}) -->", f.read_text())
        if not m:
            out.append((f.name, "no stamp"))
        elif m.group(1) != want:
            out.append((f.name, f"built from {m.group(1)}, payload is {want}"))
    return out


def main(force=False):
    stale = stale_pages()
    if stale:
        print("REFUSING TO SYNC. These pages were not built from the payload "
              "now on disk, so they carry figures from an earlier cut:\n")
        for n, why in stale[:6]:
            print(f"    docs/heat/{n}  ({why})")
        if len(stale) > 6:
            print(f"    ... and {len(stale) - 6} more")
        print("\nRe-run design/make_heat_index.py and design/make_city_pages.py.")
        return 1

    if not SRC.is_dir():
        raise SystemExit(f"no build output at {SRC}")
    DST.mkdir(parents=True, exist_ok=True)
    BASE.mkdir(exist_ok=True)

    edited = [f.name for f in sorted(DST.glob("*.html"))
              if (BASE / f.name).exists()
              and not filecmp.cmp(f, BASE / f.name, shallow=False)]
    if edited and not force:
        print("REFUSING TO REFRESH. These have been edited by hand since the "
              "last sync, and copying over them would lose the changes with "
              "nothing to recover them from:\n")
        for n in edited:
            print(f"    heat-preview/{n}")
        print("\nPort the edits into the generator first, or re-run with "
              "--force to discard them.")
        return 1
    if edited:
        print(f"--force: discarding hand edits in {', '.join(edited)}")

    for f in sorted(SRC.glob("*.html")):
        shutil.copy(f, DST / f.name)
        # Written in the same breath as the copy. A baseline updated at any
        # other moment is the bug this file exists to fix.
        shutil.copy(f, BASE / f.name)
    print(f"refreshed {len(list(SRC.glob('*.html')))} pages, baseline updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--force" in sys.argv))
