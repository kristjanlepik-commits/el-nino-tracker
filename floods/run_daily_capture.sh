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

# Consecutive no-ops are counted, not just logged.
#
# The Fire chat lost two days on 2026-07-27 to exactly this shape: a
# step declined politely every run, every automated check passed
# because they verify structure rather than freshness, and nobody was
# counting the no-ops. A polite decline is invisible unless something
# keeps score.
#
# One new day ages past --min-age-days per calendar day, so a healthy
# daily run captures exactly one. A single no-op is tolerable (a run
# fired twice, or a day arrived late). Two in a row means no progress
# for two days, and with a seven day LANCE window and two days of
# min-age that leaves three days to react before data is lost.
NOOP_FILE="$HOME/tls-floods-capture/.consecutive_noops"
if [ "$AFTER" -eq "$BEFORE" ]; then
  N=$(( $(cat "$NOOP_FILE" 2>/dev/null || echo 0) + 1 ))
  echo "$N" > "$NOOP_FILE"
  echo "NOTE: no new day captured this run (consecutive: $N)"
  if [ "$N" -ge 2 ]; then
    fail "captured nothing $N runs in a row. LANCE deletes after ~7 days, so this is losing data now."
  fi
else
  echo 0 > "$NOOP_FILE"
fi
echo "=== $(date '+%H:%M:%S') done ==="
