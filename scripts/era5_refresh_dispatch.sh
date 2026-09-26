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
# THE WORKER CLONE, NOT THE SHARED TREE, and the reason is macOS rather
# than taste. The first scheduled run (2026-09-26) died on
#   PermissionError: Operation not permitted: .../El Nino Tracker/.venv/pyvenv.cfg
# because TCC blocks a LaunchAgent from reading ~/Documents until Full
# Disk Access is granted, which needs Kristjan's password. The home
# folder itself is not protected (this script, in ~/bin, ran fine), so
# the job runs from its own clone at ~/tls-era5-worker with its own venv
# and its own copy of the ~50 MB climatology cache (.fetch_cache/era5_*,
# gitignored, seeded once by hand from the shared tree).
#
# Two properties fall out, and both are improvements rather than side
# effects. The job never touches the shared tree, so it cannot collide
# with nine chats' in-flight work there, and it starts from a clean
# `git pull` of origin every run instead of whatever state the shared
# tree is in. The cost: the worker's climatology is a copy. If Science
# rebuilds the climatology, reseed with
#   cp -p "<shared tree>/.fetch_cache/"era5_* ~/tls-era5-worker/.fetch_cache/
REPO="$HOME/tls-era5-worker"
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

# Start every run from origin/main. The worker holds no work of its own
# between runs, so a hard reset here cannot cost anybody anything, which
# is exactly what would not be true of the shared tree.
if ! { $GIT fetch -q origin && $GIT reset -q --hard origin/main; }; then
  log "SYNC FAILED  could not reset the worker to origin/main"; exit 1
fi

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

# NOTHING BUT fetched_at MOVED IS NO CHANGE. A live pull always writes a
# new fetched_at, so on a weekend with no new ERA5 day (and Sunday after
# a good Saturday is exactly that) a byte comparison commits every time.
# Freshness is judged on `issued`, not fetched_at, so that commit extends
# nothing and is noise in a history people read. Measured on the first
# end-to-end run, 2026-09-26: b1de0ff2 changed two fetched_at lines and
# nothing else.
if $GIT diff --quiet -- $FILES; then
  # Byte-identical, fetched_at included: nothing was written at all, so a
  # live pull did NOT happen. Worth saying differently from the case
  # below, because it is the signature of the force-live path regressing.
  log "NO CHANGE, NOTHING WRITTEN  files byte-identical to committed, fetched_at included: the live pull did not run (force-live regressed?)"
  exit 0
fi
substantive=$("$PY" - $FILES <<'PYCHK'
import json, subprocess, sys
changed = []
for f in sys.argv[1:]:
    try:
        old = json.loads(subprocess.run(["git", "show", f"HEAD:{f}"],
                         capture_output=True, text=True, check=True).stdout)
    except Exception:
        changed.append(f); continue
    new = json.load(open(f))
    old.pop("fetched_at", None); new.pop("fetched_at", None)
    if old != new:
        changed.append(f)
print(" ".join(changed))
PYCHK
)
if [ -z "$substantive" ]; then
  $GIT checkout -- $FILES
  log "NO CHANGE  issued $issued_after, observation_days $days_after: fetched_at moved, so a live pull ran, and nothing else did; not committed"
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

# Push. Origin may have moved during a 25-minute pull; the worker has
# nothing else in flight, so rebasing this one commit is safe here.
for attempt in 1 2 3; do
  if $GIT push -q origin HEAD:main 2>>"$LOG"; then
    log "PUSHED  $($GIT rev-parse --short HEAD) issued $issued_after, observation_days $days_before -> $days_after"
    exit 0
  fi
  $GIT pull -q --rebase origin main 2>>"$LOG" || break
done
log "PUSH FAILED  commit $sha is in ~/tls-era5-worker only; run: cd ~/tls-era5-worker && git push origin HEAD:main"
exit 1
