#!/bin/bash
# Monday-morning dispatch of the weekly brief, so it goes live at about
# 10:00-11:00 Tallinn instead of whenever GitHub's scheduler gets round
# to it. Science's proposal, 2026-09-28; same pattern as fires (D-297)
# and ERA5 (D-300), and inside D-305: it touches only gh, curl and its
# own log, nothing under ~/Documents.
#
# WHY NOT THE CRON. weekly_brief.yml's cron was "0 13 * * 1", 16:00
# Tallinn at best, chosen for a CPC post time of ~12:00 UTC that was
# never measured. CPC posted wksst9120.for at 07:00:12 UTC on 09-28.
# GitHub then created the scheduled run 5.0 to 6.3 hours late on every
# Monday from 08-31 to 09-21 (queued 0 min each time, so it is the
# scheduler, not our concurrency group). The cron stays as a backstop
# at :17; this is now the primary trigger.
#
# WAIT FOR THE DATA, NOT THE CLOCK, with a clock fallback. Poll CPC's
# Last-Modified every 10 minutes and dispatch once it is TODAY (UTC).
# At 10:00 UTC dispatch regardless, so a late CPC costs a brief built on
# last week's SST, which the brief already labels by issued date, and
# not a missing Monday. A run launchd starts late (laptop asleep at
# 10:05) that wakes after the deadline dispatches immediately.
#
# Kept from the other dispatchers: every outcome logged with its
# reason, dispatch retried across a waking laptop's network gap, and
# the run READ BACK after dispatch, because `gh workflow run` can exit
# 0 without a run appearing.
set -u
GH=/opt/homebrew/bin/gh
REPO="kristjanlepik-commits/el-nino-tracker"
WF="weekly_brief.yml"
CPC="https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
DEADLINE_UTC_HOUR=10
LOG="$HOME/.brief_dispatch.log"
stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { echo "$(stamp)  $*" >> "$LOG"; }

for tool in /usr/bin/curl "$GH"; do
  [ -x "$tool" ] || { log "BROKEN  $tool not found, cannot dispatch"; exit 2; }
done

today_utc=$(date -u +%F)
# Monday of this week, local date (the issue is dated by its Monday).
monday=$(date -v-"$(( ($(date +%u) + 6) % 7 ))"d +%F)

# Already published? Ask origin, not the site: the CDN lies in both
# directions (CLAUDE.md), and the file on main is the authority.
if "$GH" api "repos/$REPO/contents/docs/briefs/$monday/index.html" >/dev/null 2>&1; then
  log "ALREADY PUBLISHED  docs/briefs/$monday exists on main; nothing to do"
  exit 0
fi

reason=""
while :; do
  lm=$(/usr/bin/curl -sI --max-time 25 "$CPC" | tr -d '\r' | awk -F': ' 'tolower($1)=="last-modified"{print $2}')
  lm_day=""
  [ -n "$lm" ] && lm_day=$(date -u -j -f "%a, %d %b %Y %H:%M:%S GMT" "$lm" +%F 2>/dev/null)
  if [ "$lm_day" = "$today_utc" ]; then
    reason="CPC posted ($lm)"; break
  fi
  if [ "$(date -u +%H)" -ge "$DEADLINE_UTC_HOUR" ]; then
    reason="deadline ${DEADLINE_UTC_HOUR}:00 UTC reached, CPC not yet posted today (Last-Modified: ${lm:-unreadable}); the brief will label SST by its issued date"
    break
  fi
  sleep 600
done

before=$("$GH" run list --workflow="$WF" --repo "$REPO" --limit 1 \
         --json databaseId --jq '.[0].databaseId' 2>/dev/null)

dispatched=0
for attempt in 1 2 3 4 5 6; do
  if err=$("$GH" workflow run "$WF" --repo "$REPO" --ref main 2>&1 >/dev/null); then
    dispatched=1; break
  fi
  log "attempt $attempt failed: ${err:-no stderr}"
  sleep $((attempt * 15))
done
if [ "$dispatched" -ne 1 ]; then
  log "DISPATCH FAILED after 6 attempts ($reason). The :17 cron is the backstop."
  exit 1
fi

# READ BACK WHAT YOU WROTE.
for _ in 1 2 3 4 5 6; do
  sleep 10
  after=$("$GH" run list --workflow="$WF" --repo "$REPO" --limit 1 \
          --json databaseId --jq '.[0].databaseId' 2>/dev/null)
  if [ -n "$after" ] && [ "$after" != "$before" ]; then
    log "DISPATCHED  run $after for issue $monday: $reason"
    exit 0
  fi
done
log "NO RUN APPEARED after dispatch returned 0 ($reason). The :17 cron is the backstop."
exit 1
