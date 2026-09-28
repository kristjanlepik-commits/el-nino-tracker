#!/bin/bash
# Daily: is every page a reader sees current? Logs one line; if anything is
# stale, raises a macOS notification. The check itself is
# ~/bin/check_live_freshness.py, a copy of scripts/check_live_freshness.py
# (Admin.command warns if they drift). Lives outside ~/Documents because
# launchd cannot read there.
LOG="$HOME/.tls_freshness.log"
PY=/usr/bin/python3
stamp() { date '+%Y-%m-%d %H:%M'; }
[ -x "$PY" ] || { echo "$(stamp)  BROKEN  $PY missing, check cannot run" >> "$LOG"; exit 2; }
[ -f "$HOME/bin/check_live_freshness.py" ] || { echo "$(stamp)  BROKEN  check script missing" >> "$LOG"; exit 2; }
out=$("$PY" "$HOME/bin/check_live_freshness.py" --line 2>&1); rc=$?
echo "$out" >> "$LOG"
if [ $rc -ne 0 ]; then
  msg=$(echo "$out" | sed 's/^[0-9-]* [0-9:]*  //' | cut -c1-200 | tr '"' "'")
  /usr/bin/osascript -e "display notification \"$msg\" with title \"The Long Swell: a page is stale\"" 2>/dev/null
fi
exit $rc
