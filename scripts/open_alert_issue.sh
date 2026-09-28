#!/bin/bash
# Open an issue assigned to Kristjan, once, so a failure reaches his inbox.
#
#   scripts/open_alert_issue.sh "<title>" "<body>"
#
# WHY AN ISSUE. On 2026-09-21 the weekly brief crashed, check_weekly_issue
# named the missing issue the next morning, qa.yml went red on six
# scheduled runs in a row, and nobody knew for five days: a red workflow
# emails nobody here. The repo has no SMTP secrets, so the brief's own
# mail step has never sent anything either. An issue opened by
# github-actions[bot] and ASSIGNED to Kristjan is the channel that needs
# no setup and no password: GitHub emails an assignee by default, and a
# bot's action is not the owner's own activity, so it is not suppressed.
#
# ONE ISSUE PER TITLE while it is open. A daily check re-firing adds a
# comment rather than a new issue, so a missed week is one thread in the
# inbox, not one per morning.
#
# Needs GH_TOKEN (the workflow's GITHUB_TOKEN with issues: write).
set -u
title="$1"; body="$2"
repo="${GITHUB_REPOSITORY:-kristjanlepik-commits/el-nino-tracker}"
existing=$(gh issue list -R "$repo" --state open --search "\"$title\" in:title" \
           --json number,title --jq ".[] | select(.title == \"$title\") | .number" | head -1)
if [ -n "$existing" ]; then
  gh issue comment "$existing" -R "$repo" --body "Still true at $(date -u '+%F %H:%MZ'). $body"
  echo "commented on #$existing"
else
  gh issue create -R "$repo" --title "$title" --body "$body" \
     --assignee kristjanlepik-commits
fi
