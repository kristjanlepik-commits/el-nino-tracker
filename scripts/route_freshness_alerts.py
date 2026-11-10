#!/usr/bin/env python3
"""Turn check_live_freshness.py's findings into alert issues, one per page.

Business's request, 2026-11-10. The live check caught Heat's 54 pages
standing still for five weeks, and the missing 2026-11-09 issue at 03:43 the
next morning, and reached nobody: a Mac notification and a line on the admin
page. Assigned issues (scripts/open_alert_issue.sh) are the one channel that
reaches Kristjan (D-358).

  STALE, NO DATE, or UNREACHABLE for one page   one issue, "Stale page: <page>"
  ok                                            closes that page's open issue
  exit 3 (nothing could be fetched at all)      NO finding: the network, not
                                                the site, so nothing opens

LIVE_ALERTS must be "on" to open or close anything. Otherwise it only prints
what it would do. It ships off for a week of logging (Business's condition:
an alarm that cries wolf once stops being read), because the date budgets
for floods, crops and the ocean field are unconfirmed and floods' reframed
page may read as NO DATE. A person turns it on, in a commit, after that week.
Stdlib only. Never fails the job.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = os.environ.get("LIVE_ALERTS", "off") == "on"
REPO = os.environ.get("GITHUB_REPOSITORY", "kristjanlepik-commits/el-nino-tracker")
RUN = os.environ.get("RUN_URL", "")


def title(page):
    return f"Stale page: {page}"


def open_titles():
    out = subprocess.run(["gh", "issue", "list", "-R", REPO, "--state", "open",
                          "--limit", "100", "--json", "number,title"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("could not list issues:", out.stderr.strip()[:200])
        return None
    return {i["title"]: i["number"] for i in json.loads(out.stdout or "[]")}


def main():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_live_freshness.py"),
                        "--json"], capture_output=True, text=True)
    if r.returncode == 3:
        print("CANNOT CHECK: no page could be fetched (the network, not the site). No finding.")
        return 0
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        print("check_live_freshness.py gave no JSON:", (r.stdout + r.stderr).strip()[:300])
        return 0
    existing = open_titles() if LIVE else {}
    if existing is None:
        return 0
    mode = "" if LIVE else "[dry run, LIVE_ALERTS off] "
    for row in rows:
        t = title(row["page"])
        if row["state"] == "ok":
            if t in (existing or {}):
                print(f"{mode}close #{existing[t]}: {row['page']} current, claims {row['claims']}")
                if LIVE:
                    subprocess.run(["gh", "issue", "close", str(existing[t]), "-R", REPO, "-c",
                                    f"Current again on the live site: {row['page']} claims "
                                    f"{row['claims']}, within its {row['budget_days']}-day budget. "
                                    f"Closed by route_freshness_alerts.py."], capture_output=True)
            else:
                print(f"{mode}ok: {row['page']} claims {row['claims']}")
            continue
        body = (f"{row['page']} on the live site: {row['state']}. {row['detail']}. "
                f"Claims {row['claims']}, budget {row['budget_days']} days, owner "
                f"{row['owner']}. Checked by scripts/check_live_freshness.py against the "
                f"page a reader sees. {RUN}").strip()
        print(f"{mode}ALERT: {t} ({row['state']}: {row['detail']})")
        if LIVE:
            subprocess.run(["bash", str(ROOT / "scripts" / "open_alert_issue.sh"), t, body])
    return 0


if __name__ == "__main__":
    sys.exit(main())
