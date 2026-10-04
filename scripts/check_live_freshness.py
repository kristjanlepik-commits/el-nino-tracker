#!/usr/bin/env python3
"""Is every page a reader sees current? One question, asked of the LIVE site.

    python3 scripts/check_live_freshness.py          table, exit 1 if anything is stale
    python3 scripts/check_live_freshness.py --line   one line, for a log

WHY THIS EXISTS. In September a reader could have found, on the same day:
the El Nino issue a week old because the Monday job crashed; heat measured
to 13 September because its refresh had published nothing new for three
weeks while reporting success; floods showing 15 to 28 August; the landing
page's ocean field stopped at 13 September. Kristjan found them himself,
after a week away.

A check for the missing El Nino issue DID exist and went red every day from
22 September. It reached nobody, and it lives in a workflow that is red 17
days in 22 anyway, so red had stopped meaning anything.

So this check deliberately does ONE thing, and is green on every normal
day. Red here means a reader is looking at something old. Nothing else.

THE RULES IT FOLLOWS, each learned the hard way this summer:
  - Ask the LIVE page, never the repo or a run's exit code. Heat's refresh
    was green every Monday while publishing nothing.
  - Read each page's OWN date label. "Latest date anywhere on the page"
    would read a footer as fresh.
  - A page whose date cannot be found is a FAILURE, not a pass. Silence
    must never look like health.
  - Standard library only, so it runs under launchd with no venv and
    nothing under ~/Documents.

BUDGETS are days since the date the page claims. They are provisional:
each channel's owner should confirm the promise its page makes. They are
set so that every failure of September 2026 would have gone red within a
day or two of starting.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.request

SITE = "https://thelongswell.com/"
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MON3 = {k[:3]: v for k, v in MONTHS.items()}


def _page(path: str) -> str:
    req = urllib.request.Request(SITE + path, headers={"User-Agent": "tls-freshness"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _iso(t, pattern):
    ds = [dt.date.fromisoformat(d) for d in re.findall(pattern, t)]
    return max(ds) if ds else None


def _fires(t):
    # "wk Aug 24-30" or, across a month, "wk Aug 27-Sep 2"
    m = re.search(r"wk ([A-Z][a-z]{2}) (\d{1,2})-(?:([A-Z][a-z]{2}) )?(\d{1,2})", t)
    return _roll(dt.date(TODAY.year, MON3[m.group(3) or m.group(1)], int(m.group(4)))) if m else None


def _floods(t):
    ends = [dt.date(int(y), MONTHS[mo], int(d)) for d, mo, y in
            re.findall(r"\d{1,2} to (\d{1,2}) ([A-Z][a-z]+) (20\d\d)", t) if mo in MONTHS]
    return max(ends) if ends else None


def _crops(t):
    m = re.search(r"ten days to (\d{1,2}) ([A-Z][a-z]+)", t)
    return _roll(dt.date(TODAY.year, MONTHS[m.group(2)], int(m.group(1)))) if m and m.group(2) in MONTHS else None


def _roll(d):
    # Pages that print no year: a date in the future belongs to last year.
    return d.replace(year=d.year - 1) if (d - TODAY).days > 60 else d


# name, path, how to read the page's own date, budget in days, owner
CHANNELS = [
    ("El Nino issue", "", lambda t: _iso(t, r"issue (20\d\d-\d\d-\d\d)"), 7, "science"),
    ("Ocean field", "", lambda t: _iso(t, r"observed \d+ days to (20\d\d-\d\d-\d\d)"), 8, "science"),
    ("Fires", "fires/", _fires, 2, "fire"),
    ("Heat", "heat/", lambda t: _iso(t, r"measured to (20\d\d-\d\d-\d\d)"), 11, "heat"),  # heat set 11: weekly worst case ~9, scheduler ~8h late
    ("Floods", "floods/", _floods, 21, "floods"),
    ("Crops", "crops/", _crops, 25, "crops"),
]

TODAY = dt.date.today()


def main() -> int:
    rows, bad = [], []
    for name, path, read, budget, owner in CHANNELS:
        try:
            claimed = read(_page(path))
        except Exception as e:  # unreachable is a failure, not a skip
            rows.append((name, "UNREACHABLE", "-", budget, owner, type(e).__name__))
            bad.append(name); continue
        if claimed is None:
            rows.append((name, "NO DATE", "-", budget, owner, "page states no date we can read"))
            bad.append(name); continue
        age = (TODAY - claimed).days
        state = "STALE" if age > budget else "ok"
        if state == "STALE":
            bad.append(name)
        rows.append((name, state, claimed.isoformat(), budget, owner, "%d days old" % age))

    # UNREACHABLE IS NOT STALE. From 30 September the Mac slept through the
    # mornings and every run reported every page "stale" because it could
    # not fetch any of them. An alarm that says everything is wrong every
    # day is the same as no alarm. If nothing could be fetched, say that,
    # and exit 3 so the caller does not raise a stale-page notification.
    unreachable = [r for r in rows if r[1] == "UNREACHABLE"]
    if len(unreachable) == len(rows):
        if "--line" in sys.argv:
            print("%s  CANNOT CHECK: site unreachable from this machine "
                  "(no network, or the Mac asleep)" % dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
        else:
            print("  CANNOT CHECK: no page could be fetched. This is the "
                  "network, not the site.")
        return 3
    if "--line" in sys.argv:
        print("%s  %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
              "ALL CURRENT" if not bad else "STALE: " + ", ".join(
                  "%s (%s)" % (r[0], r[5]) for r in rows if r[0] in bad)))
    else:
        print("  %-14s %-12s %-11s %-7s %-8s %s" % ("page", "state", "claims", "budget", "owner", ""))
        for r in rows:
            print("  %-14s %-12s %-11s %-7s %-8s %s" % (r[0], r[1], r[2], "%dd" % r[3], r[4], r[5]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
