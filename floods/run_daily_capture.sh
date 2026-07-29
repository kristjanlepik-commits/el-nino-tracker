#!/bin/bash
# Daily VIIRS capture wrapper, run unattended by launchd.
#
# Interim measure. Platform owns scheduled jobs and will replace this
# with a proper CI workflow once the D-033 gate is ratified. It exists
# because D-038's whole premise is that a missed day is unrecoverable:
# LANCE deletes after about seven days, so a gap in this job is a
# permanent hole in every future VIIRS baseline, not a retry.
#
# The job must therefore fail LOUDLY. The specific way it will fail
# quietly, if nothing is done, is credential expiry: the Earthdata
# token dies 2026-09-26, and LAADS and LANCE respond to an
# unauthenticated request by serving an HTML login page with HTTP 200
# rather than a 401. A naive job would keep "succeeding" while writing
# nothing.

set -uo pipefail

REPO="/Users/admin/Documents/Claude Projects/El Nino Tracker"
OUT="$HOME/tls-floods-capture/vcdwd_0p1deg"
LOG="$HOME/tls-floods-capture/daily.log"
STATUS="$HOME/tls-floods-capture/last_run.json"
PY="$REPO/.venv/bin/python"

mkdir -p "$OUT"
exec >> "$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') starting ==="

fail() {
  echo "FAILED: $1"
  printf '{"ok":false,"when":"%s","error":"%s"}\n' "$(date -u +%FT%TZ)" "$1" > "$STATUS"
  osascript -e "display notification \"$1\" with title \"TLS floods capture FAILED\"" 2>/dev/null
  exit 1
}

# Refuse to run concurrently with another instance. A global day takes
# about 90 minutes and the catch-up run on 2026-07-28 was still going
# close to the first scheduled 09:30 firing, so this is not theoretical.
# Two instances would race on the same .parts_<day> directory and could
# consolidate a day while the other was still writing tiles into it,
# producing a short day that is then never revisited, because
# capture_day skips any date that already has an npz.
#
# mkdir is the lock because it is atomic on every filesystem that
# matters and needs no flock, which macOS bash does not ship.
LOCK="$OUT/.capture.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  # A lock left behind by a killed run would block every future run
  # silently, which is precisely the failure this wrapper exists to
  # prevent, so the staleness check belongs here on the failure path
  # rather than after a successful acquire. A full pass over seven
  # days takes about ten hours; six hours of no progress means dead.
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +360 2>/dev/null)" ]; then
    echo "NOTE: stale lock older than 6h, taking it over"
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null || fail "could not take over stale lock $LOCK"
  else
    echo "SKIPPED: another capture is already running (lock held: $LOCK)"
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT


# Credential check before doing any work, because this is the failure
# mode that would otherwise be silent.
TOK=$(cat "$HOME/.earthdata_token" 2>/dev/null) || fail "no ~/.earthdata_token"
PROBE=$(curl -sS -L -o /dev/null -w '%{content_type}' -m 120 \
  -H "Authorization: Bearer $TOK" \
  "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/5200/VCDWD_L3_NRT.json") \
  || fail "LANCE unreachable"
case "$PROBE" in
  *html*) fail "auth rejected: served an HTML login page. Token expired or app approval lost." ;;
esac

BEFORE=$(ls "$OUT"/*.npz 2>/dev/null | wc -l | tr -d ' ')
"$PY" "$REPO/floods/capture_viirs_global.py" --out-dir "$OUT" --workers 6
RC=$?
AFTER=$(ls "$OUT"/*.npz 2>/dev/null | wc -l | tr -d ' ')

[ $RC -eq 0 ] || fail "capture exited $RC"

echo "days stored: $BEFORE -> $AFTER"
printf '{"ok":true,"when":"%s","days_before":%s,"days_after":%s}\n' \
  "$(date -u +%FT%TZ)" "$BEFORE" "$AFTER" > "$STATUS"

# Staleness, not consecutive no-ops.
#
# The first design counted no-ops and failed on two in a row. That only
# works if the job runs exactly once per new day. It does not: this
# fires several times daily, because a laptop sleeps and a single daily
# slot is missed silently (the 09:30 slot on 2026-07-29 never fired at
# all). With several firings a day, most runs legitimately capture
# nothing and a no-op counter would cry wolf every morning.
#
# What actually matters is not how many runs did nothing, it is how
# long since anything was captured. That is frequency-independent, and
# it is the staleness check the Fire chat asked platform for after a
# politely-declining step froze their pages for two days.
#
# 36 hours: a new day becomes eligible every 24, so 36 allows one
# missed day plus slack, and still leaves several days of the seven day
# LANCE window to react.
STAMP="$HOME/tls-floods-capture/.last_capture_epoch"
NOW=$(date +%s)
if [ "$AFTER" -gt "$BEFORE" ]; then
  echo "$NOW" > "$STAMP"
  echo "captured $((AFTER-BEFORE)) new day(s)"
else
  echo "no new day this run (correct when none has aged in yet)"
  LAST=$(cat "$STAMP" 2>/dev/null || echo "$NOW")
  [ -f "$STAMP" ] || echo "$NOW" > "$STAMP"
  AGE_H=$(( (NOW - LAST) / 3600 ))
  echo "hours since last capture: $AGE_H"
  if [ "$AGE_H" -ge 36 ]; then
    fail "nothing captured for ${AGE_H}h. LANCE deletes after ~7 days; this is losing data."
  fi
fi
echo "=== $(date '+%H:%M:%S') done ==="
