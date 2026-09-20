#!/bin/bash
# ERA5 comes off the runner (D-300): this pulls ERA5 on the laptop, which
# has the climatology cache the runner cannot build inside its budget,
# and commits the two compact results the runner reads instead.
#
# Runs from launchd (scripts/com.thelongswell.era5-refresh.plist) on
# Saturday and Sunday mornings. Two slots because launchd does not retry
# and the Monday brief is the deadline: a Saturday failure gets a second
# chance on Sunday, and a Sunday success after a Saturday success is a
# harmless no-op (nothing to commit). Science's fetchers hold a ten-day
# staleness bound, so if BOTH slots fail for two weekends the panel goes
# blank and the snapshot names this file. That is the failure we want.
#
# EVERY OUTCOME IS LOGGED WITH ITS REASON. The fires dispatcher's first
# version sent gh's stderr to /dev/null and the one morning it failed
# left a log that said only FAILED (0fbf483d). Not repeating that.
#
# A REFRESH IS ACCEPTED ONLY IF IT COVERS AT LEAST WHAT IS COMMITTED.
# Heat measured on 2026-09-17 that OGIMET caps a response at ~5,800
# bulletins and returns HTTP 200 with the partial body; a capped
# response is indistinguishable from a complete one by anything except
# comparison with what you already hold. So: issued must not go
# backwards, and the WWE observation-day count must not shrink. A
# refresh that fails that test is refused, both extents logged, and the
# committed file stands.
set -u
REPO="/Users/admin/Documents/Claude Projects/El Nino Tracker"
PY="$REPO/.venv/bin/python"
GIT=/usr/bin/git
LOG="$HOME/.era5_refresh.log"
FILES="data/era5/era5_wwe_last_good.json data/era5/era5_burst_last_good.json"
stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { echo "$(stamp)  $*" >> "$LOG"; }

cd "$REPO" || { log "BROKEN  repo not at $REPO"; exit 2; }
[ -x "$PY" ] || { log "BROKEN  no python at $PY"; exit 2; }

# Wait for a network, up to five minutes: launchd fires on wake and the
# laptop can be seconds from having one (same lesson as fires_dispatch).
for attempt in 1 2 3 4 5 6; do
  /usr/bin/curl -s --max-time 15 -o /dev/null https://cds.climate.copernicus.eu/ && break
  log "attempt $attempt: no route to CDS yet"
  sleep $((attempt * 15))
done

# What is committed, before the pull touches the working files.
before=$($GIT show HEAD:data/era5/era5_wwe_last_good.json 2>/dev/null | "$PY" -c '
import json,sys
try: d=json.load(sys.stdin); print(d.get("issued",""), (d.get("payload") or {}).get("observation_days",0))
except Exception: print("", 0)')
set -- $before; issued_before=${1:-}; days_before=${2:-0}

out=$("$PY" scripts/refresh_era5_committed.py 2>&1); code=$?
if [ $code -ne 0 ]; then
  log "PULL FAILED (exit $code): $(echo "$out" | tail -3 | tr '\n' ' | ')"
  $GIT checkout -- $FILES 2>/dev/null
  exit 1
fi

after=$("$PY" -c '
import json; d=json.load(open("data/era5/era5_wwe_last_good.json"))
print(d.get("issued",""), (d.get("payload") or {}).get("observation_days",0))')
set -- $after; issued_after=${1:-}; days_after=${2:-0}

if [ -n "$issued_before" ] && { [ "$issued_after" \< "$issued_before" ] || [ "$days_after" -lt "$days_before" ]; }; then
  log "REFUSED  new result covers less than committed: issued $issued_before -> $issued_after, observation_days $days_before -> $days_after. Committed file stands."
  $GIT checkout -- $FILES
  exit 1
fi

if $GIT diff --quiet -- $FILES; then
  log "NO CHANGE  issued $issued_after, observation_days $days_after; nothing to commit"
  exit 0
fi

# Commit with the pathspec ON THE COMMIT (CLAUDE.md): nine chats share
# this tree and the index holds whatever they have staged.
$GIT add $FILES
if ! $GIT commit $FILES -q -m "era5: refresh $(date -u +%F), issued $issued_after, $days_after observation days"; then
  log "COMMIT FAILED  (tree state?) $(git status --short $FILES | tr '\n' ' ')"
  exit 1
fi
sha=$($GIT rev-parse HEAD)

# Push. If the shared tree is behind origin, do NOT rebase it (other
# chats' in-flight work): cherry-pick this one commit onto origin/main
# in a throwaway worktree and push from there.
if $GIT push -q origin HEAD:main 2>>"$LOG"; then
  log "PUSHED  $sha issued $issued_after, observation_days $days_before -> $days_after"
  exit 0
fi
WT=$(mktemp -d /tmp/era5-push.XXXXXX)
if $GIT fetch -q origin && $GIT worktree add -q --detach "$WT" origin/main \
   && (cd "$WT" && $GIT cherry-pick -q "$sha" && $GIT push -q origin HEAD:main); then
  log "PUSHED via worktree  $sha issued $issued_after, observation_days $days_before -> $days_after (shared tree was behind origin)"
  $GIT worktree remove --force "$WT"; exit 0
fi
$GIT worktree remove --force "$WT" 2>/dev/null
log "PUSH FAILED  commit $sha is local only; run: git push origin HEAD:main"
exit 1
