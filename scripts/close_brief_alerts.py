#!/usr/bin/env python3
"""Close weekly-brief alerts whose issue is now live, judged on the live site.

Business's rule (D-356): an open alert always means a live problem. Before
this, #5 and #6 stayed open for weeks after a later run had published, so
when #8 opened it looked like the third false alarm and sat for 25 hours
on a real outage.

Closed only on what a reader sees, never on a run going green:
  - the issue's Monday archive, /briefs/<monday>/, returns 200, AND
  - /elnino/, where readers land, links that issue or a later one, AND
  - for a section-render alert, the front page names that issue or later.

Alert titles carry the date the RUN failed (a Tuesday re-run, say), so each
is mapped back to the Monday on or before it. Needs GH_TOKEN with
issues: write. Prints what it did; never fails the job.
"""
import datetime as dt
import json
import os
import re
import subprocess
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "kristjanlepik-commits/el-nino-tracker")
SITE = "https://thelongswell.com"
PATTERNS = (
    ("run", re.compile(r"^Weekly brief run failed: (\d{4}-\d{2}-\d{2})$")),
    ("missing", re.compile(r"^Weekly brief missing: week of (\d{4}-\d{2}-\d{2})$")),
    ("section", re.compile(r"^Weekly brief section failed to render: (\d{4}-\d{2}-\d{2})$")),
)


def fetch(path):
    try:
        with urllib.request.urlopen(SITE + path, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as exc:
        return getattr(exc, "code", 0), ""


def latest_issue_linked(html):
    dates = re.findall(r"briefs/(\d{4}-\d{2}-\d{2})", html)
    return max(dates) if dates else ""


def main():
    out = subprocess.run(["gh", "issue", "list", "-R", REPO, "--state", "open",
                          "--limit", "100", "--json", "number,title"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("could not list issues:", out.stderr.strip()[:200])
        return
    _, elnino = fetch("/elnino/")
    linked = latest_issue_linked(elnino)
    _, front = fetch("/")
    for issue in json.loads(out.stdout or "[]"):
        for kind, pat in PATTERNS:
            m = pat.match(issue["title"])
            if not m:
                continue
            d = dt.date.fromisoformat(m.group(1))
            monday = (d - dt.timedelta(days=d.weekday())).isoformat()
            code, _ = fetch(f"/briefs/{monday}/")
            live = code == 200 and linked >= monday
            if kind == "section":
                live = live and (latest_issue_linked(front) >= monday
                                 or monday in front)
            if not live:
                print(f"#{issue['number']} stays open: {monday} archive {code}, "
                      f"/elnino/ links {linked or 'nothing'}")
                continue
            msg = (f"Resolved on the live site: the {monday} issue is live "
                   f"(archive 200, /elnino/ links {linked}). Closed by "
                   f"close_brief_alerts.py, which judges the page a reader "
                   f"sees, not a run going green.")
            subprocess.run(["gh", "issue", "close", str(issue["number"]), "-R",
                            REPO, "-c", msg], capture_output=True)
            print(f"#{issue['number']} closed: {monday} is live")


if __name__ == "__main__":
    main()
