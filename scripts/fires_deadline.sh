#!/bin/bash
# Fires deadline check, self-contained. D-241: the page must be live by
# 10:00 Europe/Tallinn.
#
# WHY THIS LIVES IN ~/bin AND NOT IN THE REPO. The first version lived in
# ~/Documents and launchd could not start it at all: macOS TCC returns
# "Operation not permitted" to a launchd agent reading that folder, so it
# ran once, exited 126, and never fired again. It looked like it was
# working because a manual run and its own retry loop left three
# plausible timestamps in the log. Two chats confirmed a working safety
# net to each other without opening stderr.
#
# So this version touches NOTHING under ~/Documents. It uses system
# python3, curl and gh, needs no Full Disk Access, and needs nothing from
# Kristjan.
#
# WHY NOT IN GITHUB ACTIONS. The failure it exists to catch is GitHub's
# own scheduler dropping or stalling a run. A check inside that scheduler
# is silent on exactly the nights it is needed.
set -uo pipefail

LOG="$HOME/.fires_deadline.log"
PAGE="https://thelongswell.com/fires/"
BUDGET=2
stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }

# Fail LOUDLY if the check itself cannot run. The failure mode that hid
# for a day was silence being indistinguishable from success.
GH="/opt/homebrew/bin/gh"   # absolute: launchd's PATH is /usr/bin:/bin:/usr/sbin:/sbin only
for tool in curl python3 "$GH"; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "$(stamp)  BROKEN  $tool not found, check cannot run" >> "$LOG"; exit 2; }
done

age() {
  html=$(curl -s --max-time 25 "$PAGE") || return 2
  printf '%s' "$html" | python3 -c '
import sys, re, datetime
# TWO WINDOW SHAPES. A week inside one month renders "wk Aug 24-30";
# a week crossing a month renders "wk Aug 27-Sep 2". The first version
# matched only the former, so it returned NOWINDOW and exited without
# dispatching on 2026-09-02, the first cross-month window since it was
# written. A once-a-month blind spot that fails silently to the page
# and loudly only to a log nobody reads.
m = re.search(r"wk ([A-Z][a-z]{2}) (\d{1,2})-(?:([A-Z][a-z]{2}) )?(\d{1,2})",
              sys.stdin.read())
if not m: print("NOWINDOW"); raise SystemExit
MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
       "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
end_mon = MON[m.group(3) or m.group(1)]
today = datetime.date.today()
end = datetime.date(today.year, end_mon, int(m.group(4)))
# YEAR ROLLOVER, BOTH DIRECTIONS. The page never names a year, so the
# window is dated into the current one and corrected. A window ending
# in the future belongs to last year; one ending absurdly far in the
# past belongs to next. Without the second case, "wk Dec 29-Jan 4" read
# on 30 December resolves to January ELEVEN MONTHS AGO, reports an age
# of 360 days and dispatches a run against a page that is fine.
if (end - today).days > 60: end = end.replace(year=today.year - 1)
elif (today - end).days > 180: end = end.replace(year=today.year + 1)
print((today - end).days)
'
}

d=$(age)
if [ "$d" = "NOWINDOW" ] || [ -z "$d" ]; then
  echo "$(stamp)  BROKEN  could not read a window from the live page" >> "$LOG"; exit 2
fi

if [ "$d" -le "$BUDGET" ]; then
  echo "$(stamp)  OK      page current, window ${d}d old" >> "$LOG"; exit 0
fi

echo "$(stamp)  STALE   window ${d}d old, budget $BUDGET" >> "$LOG"
"$GH" workflow run "Fires data pull and publish" \
   --repo kristjanlepik-commits/el-nino-tracker >/dev/null 2>&1 \
  && echo "$(stamp)  DISPATCHED" >> "$LOG" \
  || { echo "$(stamp)  DISPATCH FAILED" >> "$LOG"; exit 1; }

# A dispatch is not a fix. Wait for the PAGE to move.
for _ in $(seq 1 20); do
  sleep 60
  n=$(age)
  if [ "$n" != "NOWINDOW" ] && [ -n "$n" ] && [ "$n" -le "$BUDGET" ]; then
    echo "$(stamp)  RECOVERED  window ${n}d old" >> "$LOG"; exit 0
  fi
done
echo "$(stamp)  STILL STALE after 20 min. Needs a person." >> "$LOG"
exit 1
