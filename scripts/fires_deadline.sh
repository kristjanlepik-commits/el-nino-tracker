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
m = re.search(r"wk ([A-Z][a-z]{2}) (\d{1,2})-(\d{1,2})", sys.stdin.read())
if not m: print("NOWINDOW"); raise SystemExit
mon = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
       "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}[m.group(1)]
today = datetime.date.today()
end = datetime.date(today.year, mon, int(m.group(3)))
if (end - today).days > 60: end = end.replace(year=today.year - 1)
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
