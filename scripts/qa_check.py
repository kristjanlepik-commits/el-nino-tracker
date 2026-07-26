#!/usr/bin/env python3
"""Pre-publish QA gate for The Long Swell.

Run before any push that publishes to docs/. Stdlib only, so it works
with bare python3 in CI and with .venv/bin/python locally.

Checks:
  1. Em-dash guard: no U+2014 outside the documented allowlist
     (CLAUDE.md invariant 6).
  2. Immutability: files under docs/briefs/ and snapshots/ that exist
     at the base ref are never modified or deleted (invariants 4, 5).
  3. Internal links: every relative href/src in docs/ HTML resolves to
     a file that exists.
  4. Structure: front page, methodology page, CNAME, and per-brief
     index.html + analog.png all present.
  5. snapshots/*.json parse as JSON.

Usage:
  scripts/qa_check.py                  local run, base = origin/main
  scripts/qa_check.py --base SHA       CI run, explicit base
  scripts/qa_check.py --no-frozen-check
  scripts/qa_check.py --allow-frozen-edits   emergency --force fixes only

Exit 0 when clean, 1 when any violation is printed.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EMDASH = "\u2014"
# Built from the escape so this file never contains the literal char.

# Documented legitimate em-dash carriers; must not grow (invariant 6).
EMDASH_ALLOWLIST = {
    "LICENSE",
    "docs/briefs/2026-05-18/index.html",
    "docs/briefs/2026-05-25/index.html",
    "fetchers/iri.py",
}

TEXT_SUFFIXES = {
    ".py", ".md", ".html", ".htm", ".yml", ".yaml", ".txt", ".css",
    ".js", ".svg", ".json", ".csv", ".toml", ".cfg", ".ini", "",
}

FROZEN_PREFIXES = ("docs/briefs/", "snapshots/")

CANONICAL_DOMAIN = "thelongswell.com"

LINK_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "data:", "//", "#", "javascript:")

# Broken links shipped inside frozen archives (invariant 5). The nav
# 'briefs/' link in these issues resolves nowhere; generator fixed from
# 2026-07-13 on. Fixing the frozen files needs a Kristjan-ratified
# surgical --force edit; until then these are suppressed, not endorsed.
KNOWN_FROZEN_DEFECTS = {
    (f"docs/briefs/{day}/index.html", "briefs/")
    for day in (
        "2026-04-25", "2026-05-04", "2026-05-11", "2026-05-18",
        "2026-05-25", "2026-06-01", "2026-06-08", "2026-06-15",
        "2026-06-22", "2026-06-29", "2026-07-06",
    )
}


def git(*args):
    out = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    return out.returncode, out.stdout


def repo_files():
    """Tracked plus untracked-but-not-ignored files, as repo-relative paths."""
    code, out = git("ls-files", "-co", "--exclude-standard", "-z")
    if code != 0:
        return []
    return [p for p in out.split("\0") if p]


def check_emdash(violations):
    for rel in repo_files():
        path = ROOT / rel
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = [i + 1 for i, line in enumerate(text.splitlines()) if EMDASH in line]
        if not hits:
            continue
        if rel in EMDASH_ALLOWLIST:
            continue
        violations.append(
            f"em-dash: {rel} lines {', '.join(map(str, hits[:10]))}"
            + (" ..." if len(hits) > 10 else "")
        )


def check_frozen(violations, base):
    code, _ = git("cat-file", "-e", base)
    if code != 0:
        violations.append(f"frozen-check: base ref '{base}' not found; "
                          "run with --base or --no-frozen-check")
        return
    # Diff base against the working tree; statuses M and D on files that
    # exist at base. Newly added briefs and snapshots show as A and pass.
    _, out = git("diff", "--name-status", "--diff-filter=MD", base, "--",
                 *[p.rstrip("/") for p in FROZEN_PREFIXES])
    for line in out.splitlines():
        status, _, rel = line.partition("\t")
        violations.append(f"immutable surface modified ({status}): {rel}")


def check_links(violations):
    docs = ROOT / "docs"
    for html in sorted(docs.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="ignore")
        for url in LINK_RE.findall(text):
            if url.startswith(SKIP_SCHEMES):
                continue
            target = url.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if target.startswith("/"):
                violations.append(
                    f"root-absolute link in {html.relative_to(ROOT)}: {url} "
                    "(breaks on the github.io project path; use relative)")
                continue
            rel_html = str(html.relative_to(ROOT))
            if (rel_html, url) in KNOWN_FROZEN_DEFECTS:
                continue
            resolved = (html.parent / target).resolve()
            if resolved.is_dir():
                # Pages serves no directory listings; a dir link 404s
                # without an index.html inside.
                if not (resolved / "index.html").is_file():
                    violations.append(
                        f"dead link in {rel_html}: {url} "
                        "(directory without index.html)")
            elif not resolved.exists():
                violations.append(f"dead link in {rel_html}: {url}")


def check_structure(violations):
    docs = ROOT / "docs"
    for required in ("index.html", "methodology.html", "CNAME"):
        if not (docs / required).is_file():
            violations.append(f"structure: docs/{required} missing")
    cname = docs / "CNAME"
    if cname.is_file():
        content = cname.read_text(encoding="utf-8").strip()
        if content != CANONICAL_DOMAIN:
            violations.append(
                f"structure: docs/CNAME is '{content}', "
                f"expected '{CANONICAL_DOMAIN}'")
    briefs = docs / "briefs"
    if briefs.is_dir():
        for day in sorted(p for p in briefs.iterdir() if p.is_dir()):
            for required in ("index.html", "analog.png"):
                if not (day / required).is_file():
                    violations.append(
                        f"structure: {day.relative_to(ROOT)}/{required} missing")


def check_snapshots(violations):
    snaps = ROOT / "snapshots"
    if not snaps.is_dir():
        return
    for path in sorted(snaps.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            violations.append(f"snapshot unparseable: {path.name}: {exc}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main",
                    help="ref to compare frozen surfaces against")
    ap.add_argument("--no-frozen-check", action="store_true")
    ap.add_argument("--allow-frozen-edits", action="store_true",
                    help="skip immutability check for emergency --force fixes")
    args = ap.parse_args()

    violations = []
    check_emdash(violations)
    if not (args.no_frozen_check or args.allow_frozen_edits):
        check_frozen(violations, args.base)
    check_links(violations)
    check_structure(violations)
    check_snapshots(violations)

    if violations:
        print(f"QA FAILED: {len(violations)} violation(s)\n")
        for v in violations:
            print(f"  {v}")
        return 1
    print("QA clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
