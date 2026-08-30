#!/bin/bash
# Fires deadline check: is the published page live by 10:00 Estonia?
#
# D-241 makes 10:00 Europe/Tallinn a hard daily deadline. This is the
# only thing that both CHECKS it and can DO something about it.
#
# WHY IT RUNS HERE AND NOT IN GITHUB ACTIONS. The failure this exists to
# catch is GitHub's scheduler dropping or stalling a run. A check living
# inside that same scheduler goes silent on exactly the nights it is
# needed and reads as a clean day. So it runs from launchd on Kristjan's
# Mac, which is the only origin available that is independent of GitHub
# and costs nothing.
#
# WHY NO NEW CREDENTIAL. `gh` is already authenticated on this machine.
# The objection to a laptop origin was that recovery always needs a new
# token on a third-party service; that is true of a hosted service and
# false here.
#
# THE LIMIT, STATED SO NOBODY MISTAKES THIS FOR FULL COVERAGE: it only
# runs when the Mac is awake and online. A day spent travelling with the
# lid shut has no safety net. It is a real gap, priced at zero.
set -uo pipefail

REPO="/Users/admin/Documents/Claude Projects/El Nino Tracker"
PY="$REPO/.venv/bin/python"
LOG="$REPO/.fires_deadline.log"
cd "$REPO" || exit 1

stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }

if "$PY" scripts/heartbeat_fires.py >/dev/null 2>&1; then
  echo "$(stamp)  OK   page current at the deadline" >> "$LOG"
  exit 0
fi

# Stale. Say what we saw, then try to fix it rather than only reporting.
echo "$(stamp)  STALE $("$PY" scripts/heartbeat_fires.py 2>&1 | head -1)" >> "$LOG"

if gh workflow run "Fires data pull and publish" >/dev/null 2>&1; then
  echo "$(stamp)  DISPATCHED a run" >> "$LOG"
else
  echo "$(stamp)  DISPATCH FAILED, gh could not reach GitHub" >> "$LOG"
  exit 1
fi

# A dispatch is not a fix. Wait for the page itself to move, and report
# on the property rather than on the mechanism: the whole failure class
# this week was reporting that a run went green while the page had not
# moved.
for _ in $(seq 1 20); do
  sleep 60
  if "$PY" scripts/heartbeat_fires.py >/dev/null 2>&1; then
    echo "$(stamp)  RECOVERED page is current" >> "$LOG"
    exit 0
  fi
done

echo "$(stamp)  STILL STALE after 20 min. Needs a person." >> "$LOG"
exit 1
