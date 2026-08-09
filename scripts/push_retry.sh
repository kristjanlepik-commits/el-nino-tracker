#!/usr/bin/env bash
# Push to main, tolerating a concurrent push from another job.
#
# WHY THIS EXISTS. Three workflows commit to main on their own
# schedules, and two of them can genuinely overlap. floods_capture
# starts at 02:00 UTC with a 150 minute timeout, so a slow capture is
# still running when fires starts at 04:00. They are deliberately NOT in
# the same concurrency group: floods does not publish, and putting it in
# the `publish` group would let a 2.5 hour capture block the fire pages
# from updating at all. So concurrency is correct as it stands, and the
# collision has to be handled at the push instead.
#
# Whoever pushed second used to fail on non-fast-forward, and the shape
# of that failure is the nasty part: the data pull SUCCEEDED and was
# committed locally, then the job went red at the last step and the work
# was thrown away with the runner. A perishable capture would be lost
# for good, since the source deletes after about seven days.
#
# The far more likely collision is not CI against CI, it is a laptop
# push landing while a scheduled job is mid-run. That happens most days.
#
# NEVER force-push here. docs/briefs/ is an immutable archive
# (invariant 5) and a force-push is the one operation that can silently
# rewrite it. On a genuine conflict this fails loudly and leaves the
# commit on the runner for a human to look at, which is the right
# outcome: a conflict between two publishing jobs is a fact worth
# knowing, not something to paper over with a retry.
set -euo pipefail

BRANCH="${1:-main}"
ATTEMPTS=5

for i in $(seq 1 "$ATTEMPTS"); do
  if git push origin "$BRANCH"; then
    [ "$i" -gt 1 ] && echo "Pushed on attempt $i after a concurrent update."
    exit 0
  fi

  if [ "$i" -eq "$ATTEMPTS" ]; then
    echo "::error::Push failed $ATTEMPTS times. The commit exists on the" \
         "runner but is not on origin, so this run's work is NOT saved." >&2
    exit 1
  fi

  echo "Push rejected, another job likely pushed first. Rebasing (attempt $i)."
  git fetch origin "$BRANCH"

  # --rebase, not merge: keeps main linear, and a data commit has no
  # reason to sit behind a merge bubble. Rebasing our own fresh commit
  # onto whatever landed is exactly the intended result.
  # --autostash because NINE CHATS SHARE ONE WORKING TREE. A plain rebase
  # refuses outright when anyone has uncommitted work, and on 2026-08-09
  # that was CRO mid-fix on crops/build_data.py while platform pushed an
  # unrelated file. Autostash sets their work aside and puts it back.
  #
  # AND THE ERROR BELOW USED TO LIE. It asserted "a real conflict, two
  # jobs wrote the same file" for ANY rebase failure, including the dirty
  # tree above, which shares no file with anything. It cost a wrong
  # diagnosis today: the message named a cause it had never checked, in
  # the script whose job is to explain why a push stopped.
  #
  # It now reports what git actually said, and claims a conflict only
  # after looking for one.
  rebase_out=$(git rebase --autostash "origin/$BRANCH" 2>&1) || {
    conflicted=$(git diff --name-only --diff-filter=U 2>/dev/null)
    git rebase --abort 2>/dev/null || true
    if [ -n "$conflicted" ]; then
      echo "::error::Rebase hit a REAL CONFLICT against origin/$BRANCH on:" >&2
      echo "$conflicted" | sed 's/^/  /' >&2
      echo "::error::Two jobs wrote the same file. Not resolving this" \
           "automatically: a wrong guess here can corrupt published data." >&2
    else
      echo "::error::Rebase failed against origin/$BRANCH, and NOT on a" \
           "content conflict. Git said:" >&2
      echo "$rebase_out" | sed 's/^/  /' >&2
    fi
    exit 1
  }

  # Backoff so two racing jobs do not retry in lockstep forever. The
  # stagger matters more than the delay: without $i they would collide
  # on every round.
  sleep $(( i * 5 ))
done
