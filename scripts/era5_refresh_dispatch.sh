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
# STAY AWAKE FOR EXACTLY THIS RUN. On 2026-10-25 six network probes meant
# to be seconds apart ran from 09:08 to 11:52: the laptop slept between
# them, and a wall-clock fetch budget that spans a sleep times out however
# fast CDS actually was. caffeinate wrapping this script holds idle and
# system sleep for as long as this job runs and no longer. That is not the
# pid-scoped lock CLAUDE.md warns about: that rule is about OTHER jobs
# depending on a lock whose owner exits; this lock protects only its own
# process and is meant to end with it. It cannot survive a closed lid.
if [ -z "${TLS_CAFFEINATED:-}" ]; then
  exec /usr/bin/caffeinate -i -m -s /usr/bin/env TLS_CAFFEINATED=1 /bin/bash "$0" "$@"
fi
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

# Run the refresher. It writes each source that succeeded and exits
# non-zero if ANY failed, so a non-zero exit is not "nothing to keep".
out=$("$PY" scripts/refresh_era5_committed.py 2>&1); code=$?
[ $code -ne 0 ] && log "PULL INCOMPLETE (exit $code): $(echo "$out" | tail -3 | tr '\n' ' | ')"

# JUDGE EACH FILE ON ITS OWN. Until 2026-10-26 a non-zero exit discarded
# BOTH files: on 10-24 and 10-25 the wind series (era5_wwe) came back
# fine, the burst detector timed out, and the good wind file was thrown
# away with the bad one, so the 10-26 issue shipped without its wind row
# (tls-internal#48, D-343). Now each file is kept or reverted for its own
# reason, the survivors are committed, and the run still exits non-zero
# when anything failed so the failure stays visible.
#
# Per file:  unwritten   byte-identical to HEAD: that source did not land
#            refused     covers less than HEAD (issued went backwards, or
#                        for wwe the observation-day count shrank): the
#                        capped-200 rule from Heat, 2026-09-17
#            stale-only  only fetched_at moved: a pull ran, nothing new
#            commit      a real advance
verdicts=$("$PY" - $FILES <<'PYCHK'
import json, subprocess, sys
for f in sys.argv[1:]:
    head = subprocess.run(["git", "show", f"HEAD:{f}"], capture_output=True, text=True)
    try:
        new = json.load(open(f))
    except Exception:
        print(f, "refused", "unreadable-after-pull"); continue
    if head.returncode != 0:
        print(f, "commit", "new-file"); continue
    if head.stdout == open(f).read():
        print(f, "unwritten", "-"); continue
    old = json.loads(head.stdout)
    oi, ni = old.get("issued", ""), new.get("issued", "")
    od = (old.get("payload") or {}).get("observation_days")
    nd = (new.get("payload") or {}).get("observation_days")
    if ni < oi or (od is not None and nd is not None and nd < od):
        print(f, "refused", f"issued:{oi}->{ni},days:{od}->{nd}"); continue
    o2, n2 = dict(old), dict(new)
    o2.pop("fetched_at", None); n2.pop("fetched_at", None)
    print(f, "stale-only" if o2 == n2 else "commit", f"issued:{oi}->{ni},days:{od}->{nd}")
PYCHK
)
keep=""
while read -r f verdict detail; do
  [ -z "$f" ] && continue
  name=$(basename "$f" _last_good.json)
  case "$verdict" in
    commit)     keep="$keep $f"; log "  $name: ADVANCED ($detail)";;
    stale-only) $GIT checkout -- "$f"; log "  $name: no new day ($detail), not committed";;
    refused)    $GIT checkout -- "$f"; log "  $name: REFUSED, covers less than committed ($detail)";;
    unwritten)  log "  $name: not written by the refresher (failed, or force-live regressed)";;
  esac
done <<< "$verdicts"

if [ -z "$keep" ]; then
  log "NOTHING TO COMMIT"; exit $([ $code -ne 0 ] && echo 1 || echo 0)
fi

# Commit with the pathspec ON THE COMMIT (CLAUDE.md).
$GIT add $keep
summary=$(echo "$verdicts" | awk '$2=="commit"{n=split($1,a,"/"); sub("_last_good.json","",a[n]); printf "%s %s; ", a[n], $3}')
if ! $GIT commit $keep -q -m "era5: refresh $(date -u +%F): ${summary%; }"; then
  log "COMMIT FAILED  (tree state?) $($GIT status --short $keep | tr '\n' ' ')"
  exit 1
fi
sha=$($GIT rev-parse HEAD)

# Push. Origin may have moved during a 25-minute pull; the worker has
# nothing else in flight, so rebasing this one commit is safe here.
for attempt in 1 2 3; do
  if $GIT push -q origin HEAD:main 2>>"$LOG"; then
    log "PUSHED  $($GIT rev-parse --short HEAD) ${summary%; }"; exit $([ $code -ne 0 ] && echo 1 || echo 0)
    exit 0
  fi
  $GIT pull -q --rebase origin main 2>>"$LOG" || break
done
log "PUSH FAILED  commit $sha is in ~/tls-era5-worker only; run: cd ~/tls-era5-worker && git push origin HEAD:main"
exit 1
