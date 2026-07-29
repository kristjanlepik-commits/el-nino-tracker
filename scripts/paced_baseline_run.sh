#!/usr/bin/env bash
# Drive fires/build_full_baselines.py to completion without ever
# starving the scheduled jobs of FIRMS quota.
#
# THE PROBLEM. One country-year is about 73 chunked requests, so the 39
# countries still outstanding are roughly 15,000 requests against a cap
# of 5,000 per rolling 10 minutes. An unpaced run therefore saturates
# the key within minutes, and what happens next is the expensive part:
# every chunk retries three times before the year is abandoned, so a
# saturated key generates MORE traffic than a healthy one and holds
# itself pinned. Measured 2026-07-29, the key sat at exactly 5000/5000
# while the builder logged nothing but FAILED.
#
# WHY THAT MATTERS BEYOND THIS JOB. The 04:00 UTC fires workflow calls
# fetch_window_baseline.py, which needs the same key. A local baseline
# build that pins the quota overnight makes the scheduled run fail and
# the public fire page go stale, which is precisely the failure that
# froze the detections layer for two days in July. This job is not time
# critical; the daily page is. So this job yields.
#
# WHY A WRAPPER RATHER THAN A FIX INSIDE THE BUILDER. That script is the
# Fire chat's, and its science is not in question: it already refuses to
# store a year under 300 days, so a rate-limited failure leaves the year
# absent and retried rather than silently full of holes. Pacing is an
# orchestration concern, which is platform's. Wrapping keeps the seam.
#
# HOW IT CONVERGES. The builder skips any country-year already on disk,
# so running it repeatedly is cheap and strictly additive. Each pass
# fills in whatever the quota allows; we then wait for the window to
# drain and go again. A single pass could never converge on its own,
# because it makes exactly one attempt per country and exits.
set -uo pipefail

cd "$(dirname "$0")/.."

DEADLINE_UTC="${DEADLINE_UTC:-03:00}"   # stop before the 04:00 UTC fires run
START_BELOW="${START_BELOW:-1000}"      # only begin a pass on a drained key
LOG="${LOG:-/tmp/baselines_paced.log}"
KEY_FILE="$HOME/.firms_map_key"

say() { echo "[$(date -u +'%H:%M:%S')Z] $*" | tee -a "$LOG"; }

deadline=$(python3 - "$DEADLINE_UTC" <<'PY'
import sys
from datetime import datetime, timezone, timedelta
h, m = (int(x) for x in sys.argv[1].split(":"))
now = datetime.now(timezone.utc)
stop = now.replace(hour=h, minute=m, second=0, microsecond=0)
if stop <= now:
    stop += timedelta(days=1)
print(int(stop.timestamp()))
PY
)

# Portable bounded run. macOS ships no `timeout` and no `gtimeout`
# unless coreutils is installed, and calling a missing command returns
# 127 instantly, which a loop reads as "that pass finished". Doing this
# by hand is uglier than `timeout` and always present, which is the
# trade that matters for an unattended overnight job.
run_bounded() {
  local budget="$1"; shift
  "$@" >> "$LOG" 2>&1 &
  local pid=$! waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$budget" ]; then
      say "pass budget of ${budget}s reached, stopping the builder."
      kill -TERM "$pid" 2>/dev/null
      sleep 10
      kill -KILL "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep 5
    waited=$((waited + 5))
  done
  wait "$pid" 2>/dev/null
  return $?
}

# Push what this pass built, immediately.
#
# WHY, and C2 found this the hard way on 2026-07-29. The builder skips
# country-years already ON DISK, which means built-but-unpushed work is
# invisible to the other machine and simply gets rebuilt there, spending
# the shared FIRMS quota twice for data we already hold. C2's count read
# 326 against pushed main while C1's tree read 298: 28 country-years
# that would have been paid for a second time.
#
# The window for that is not small. This job runs unattended for hours
# and can hard-stop at 03:00 UTC with nobody awake to push it, so
# "remember to push afterwards" is not a mechanism. Pushing per pass
# also means a crash costs one pass, not a night.
#
# Data only: `git add` is scoped to the baseline directory so a running
# job can never sweep up an editor's half-finished work from the shared
# tree. Files are validated as parseable first, because the builder
# writes them non-atomically and a truncated JSON committed as fact is
# worse than a missing one.
publish_progress() {
  local n
  n=$(.venv/bin/python - <<'PY'
import json, glob
bad = 0
for f in glob.glob("fires/data/full_history/*.json"):
    try:
        d = json.load(open(f))
        assert isinstance(d, dict) and all(isinstance(v, dict) for v in d.values())
    except Exception:
        bad += 1
print(bad)
PY
)
  if [ "$n" != "0" ]; then
    say "NOT pushing: $n baseline file(s) unparseable, likely a write in "
    say "flight. Next pass will retry."
    return 0
  fi

  git add fires/data/full_history/ 2>/dev/null || return 0
  if git diff --cached --quiet -- fires/data/full_history/; then
    return 0
  fi
  git commit -q -m "fires: baseline pass, $(remaining) country-years outstanding" \
    -- fires/data/full_history/ || return 0
  if bash scripts/push_retry.sh main >/dev/null 2>&1; then
    say "pushed this pass. Other machines will now skip this work."
  else
    say "WARNING: commit made but push failed. Work is safe locally; the "
    say "other machine may rebuild it until this lands."
  fi
}

quota() {
  curl -s --max-time 30 \
    "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=$(cat "$KEY_FILE")" \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin)["current_transactions"])
except Exception: print(-1)'
}

remaining() {
  # Same seed list and same 14 year span the builder itself uses
  # (YEARS = 2012..2025, the SNPP science-quality archive).
  python3 -c "
import json,os
need=0
for iso in json.load(open('fires/data/country_history.json'))['countries']:
    p=f'fires/data/full_history/{iso}.json'
    have=len(json.load(open(p))) if os.path.exists(p) else 0
    need+= max(0, 14-have)
print(need)" 2>/dev/null || echo "?"
}

say "paced baseline run starting. Hard stop $(date -u -r "$deadline" +'%Y-%m-%d %H:%M')Z."

# Refuse to start if progress cannot be measured. The stall guard below
# compares this number across passes, so an unreadable count would make
# every pass look identical and abort a perfectly good run after two
# rounds. Better to fail here, in front of a person, than at 02:00.
start_missing=$(remaining)
case "$start_missing" in
  ''|*[!0-9]*)
    say "ABORTING: cannot count outstanding country-years (got" \
        "'$start_missing'). Expected to run from the repo root with" \
        "fires/data/country_history.json readable."
    exit 1 ;;
esac
say "country-years still missing: $start_missing"

pass=0
stalled=0
while [ "$(date -u +%s)" -lt "$deadline" ]; do
  q=$(quota)
  if [ "$q" = "-1" ]; then
    say "quota endpoint unreadable. Waiting 5 min rather than guessing."
    sleep 300; continue
  fi
  if [ "$q" -gt "$START_BELOW" ]; then
    say "key at $q/5000, above the $START_BELOW start threshold. Waiting 3 min."
    sleep 180; continue
  fi

  pass=$((pass + 1))
  say "pass $pass: key drained to $q/5000, running a build pass."

  # Bound each pass so a pathological country cannot eat the whole
  # window, and so the deadline is always honoured.
  budget=$(( deadline - $(date -u +%s) ))
  [ "$budget" -gt 3600 ] && budget=3600

  before=$(remaining)
  run_bounded "$budget" .venv/bin/python fires/build_full_baselines.py
  rc=$?

  left=$(remaining)
  say "pass $pass finished (rc=$rc). Country-years still missing: $left"
  publish_progress
  if [ "$left" = "0" ]; then
    say "COMPLETE: every country has 14 years."
    exit 0
  fi

  # A pass that changed nothing is the failure mode this loop is most
  # likely to hide, and it already bit once: the first version called
  # `timeout`, which macOS does not ship, so every pass returned 127
  # instantly and the loop cheerfully reported 22 successful-looking
  # rounds over 90 minutes with the counter frozen at 324. Everything
  # LOOKED healthy, the log advanced and the quota drained, because
  # nothing was running at all.
  #
  # So: two consecutive passes with no progress is not patience, it is a
  # broken command. Stop and say so rather than burn the night.
  if [ "$left" = "$before" ]; then
    stalled=$((stalled + 1))
    say "WARNING: pass $pass made no progress ($before -> $left), rc=$rc."
    if [ "$stalled" -ge 2 ]; then
      say "ABORTING: two consecutive passes did nothing. This is a broken" \
          "run, not a slow one. rc=$rc. Check the tail of $LOG."
      exit 1
    fi
  else
    stalled=0
  fi
  # Let the rolling window clear before the next pass, otherwise the
  # first chunks of it fail and burn their retries for nothing.
  sleep 240
done

say "deadline reached, stopping so the 04:00 UTC fires run has quota."
say "country-years still missing: $(remaining). Safe to resume later."
