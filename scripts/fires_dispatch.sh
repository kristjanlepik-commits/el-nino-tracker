#!/bin/bash
# Dispatch the fires pull every morning at 07:15 Europe/Tallinn.
#
# WHY THIS EXISTS. GitHub's scheduler has been firing this workflow about
# 4.5 hours after its cron slot for eleven days. The earliest slot,
# 03:10 UTC, therefore lands around 07:40 UTC, which is 10:40 Tallinn and
# past Kristjan's 10:00 deadline. No cron time fixes that: moving slots
# earlier moves them into the previous day.
#
# For seven consecutive mornings an agent dispatched this workflow BY
# HAND. That is what kept the page current, and nobody decided it; it
# just became the routine. This is that chore, made explicit.
#
# UNCONDITIONAL, ON PURPOSE. It does not check whether a run is needed.
# Detection logic is the part that breaks, and the workflow is safe to
# run twice. It logs the page age it saw so we can later measure whether
# this job was load bearing, without gating on that measurement.
#
# WHY 07:15 TALLINN (04:15 UTC). build_events.py refuses to run before
# 03:00 UTC, because FIRMS processing lags an overpass by up to three
# hours and the previous UTC day is not closed until then. 04:15 UTC is
# 75 minutes clear of that floor and 2h45m before the deadline, which
# leaves room for the run plus the 10:00 check to catch a failure.
#
# THE 10:00 JOB STAYS. This one makes the page current; that one asks
# whether it worked. Neither replaces the other.
set -uo pipefail

LOG="$HOME/.fires_dispatch.log"
GH="/opt/homebrew/bin/gh"   # launchd's PATH is /usr/bin:/bin:/usr/sbin:/sbin
REPO="kristjanlepik-commits/el-nino-tracker"
WF="Fires data pull and publish"
stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }

# Fail LOUDLY if the job cannot run. A silent failure here is
# indistinguishable from a morning that went fine.
for tool in curl "$GH"; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$(stamp)  BROKEN  $tool not found, cannot dispatch" >> "$LOG"; exit 2; }
done

# Observed, not acted on. Same parser as the deadline check, including
# the cross-month window shape "wk Aug 27-Sep 2".
age=$(curl -s --max-time 25 https://thelongswell.com/fires/ | python3 -c '
import sys, re, datetime
m = re.search(r"wk ([A-Z][a-z]{2}) (\d{1,2})-(?:([A-Z][a-z]{2}) )?(\d{1,2})", sys.stdin.read())
if not m: print("?"); raise SystemExit
MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
       "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
today = datetime.date.today()
end = datetime.date(today.year, MON[m.group(3) or m.group(1)], int(m.group(4)))
if (end - today).days > 60: end = end.replace(year=today.year - 1)
elif (today - end).days > 180: end = end.replace(year=today.year + 1)
print((today - end).days)
' 2>/dev/null) || age="?"

before=$("$GH" run list --workflow=fires.yml --repo "$REPO" --limit 1 \
         --json databaseId --jq '.[0].databaseId' 2>/dev/null)

if ! "$GH" workflow run "$WF" --repo "$REPO" >/dev/null 2>&1; then
  echo "$(stamp)  DISPATCH FAILED  page age ${age}d" >> "$LOG"; exit 1
fi

# READ BACK WHAT YOU WROTE. `gh workflow run` can exit 0 without a run
# appearing. An exit code from a call that did nothing is
# indistinguishable from one that worked, unless you go and look.
for _ in 1 2 3 4 5 6; do
  sleep 10
  after=$("$GH" run list --workflow=fires.yml --repo "$REPO" --limit 1 \
          --json databaseId --jq '.[0].databaseId' 2>/dev/null)
  if [ -n "$after" ] && [ "$after" != "$before" ]; then
    echo "$(stamp)  DISPATCHED  run $after, page was ${age}d old" >> "$LOG"
    exit 0
  fi
done
echo "$(stamp)  NO RUN APPEARED after dispatch returned 0, page ${age}d old" >> "$LOG"
exit 1
