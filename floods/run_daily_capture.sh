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

# A run that adds nothing is not automatically wrong: with --min-age-days
# there are days when no new date has aged in. It IS wrong if it repeats,
# so warn rather than fail, and let the pattern show in the log.
if [ "$AFTER" -eq "$BEFORE" ]; then
  echo "NOTE: no new day captured this run"
fi
echo "=== $(date '+%H:%M:%S') done ==="
