#!/bin/bash
# Is every page a reader sees current? Runs hourly; records one REAL reading
# per day. The check itself is ~/bin/check_live_freshness.py, a copy of
# scripts/check_live_freshness.py (Admin.command warns if they drift).
# Lives outside ~/Documents because launchd cannot read there.
#
# HOURLY, NOT ONCE AT 10:10. From 30 September the Mac slept through the
# mornings; the single 10:10 run fired during a brief dark wake with no
# network and reported every page stale, five days running. Now it tries
# every hour and stops once it has a real reading for the day.
LOG="$HOME/.tls_freshness.log"
DONE="$HOME/.tls_freshness.done"
PY=/usr/bin/python3
stamp() { date '+%Y-%m-%d %H:%M'; }
today=$(date '+%Y-%m-%d')
[ "$(cat "$DONE" 2>/dev/null)" = "$today" ] && exit 0
[ -x "$PY" ] || { echo "$(stamp)  BROKEN  $PY missing, check cannot run" >> "$LOG"; exit 2; }
[ -f "$HOME/bin/check_live_freshness.py" ] || { echo "$(stamp)  BROKEN  check script missing" >> "$LOG"; exit 2; }
out=$("$PY" "$HOME/bin/check_live_freshness.py" --line 2>&1); rc=$?
if [ $rc -eq 3 ]; then
  # No network. Not a finding about the site; try again next hour, quietly.
  echo "$out" >> "$LOG"; exit 0
fi
echo "$out" >> "$LOG"
echo "$today" > "$DONE"
if [ $rc -ne 0 ]; then
  msg=$(echo "$out" | sed 's/^[0-9-]* [0-9:]*  //' | cut -c1-200 | tr '"' "'")
  /usr/bin/osascript -e "display notification \"$msg\" with title \"The Long Swell: a page is stale\"" 2>/dev/null
fi
exit $rc
