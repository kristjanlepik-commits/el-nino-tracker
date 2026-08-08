# Proposals for other chats

Files here are changes to surfaces this chat does not own. They live here
rather than in place, because the ownership map says to send a proposal
rather than merge it for someone.

## heat_collect.yml, for platform

Hourly collector for build-forward cities, currently Tallinn.

**Why it is not a normal workflow request.** It gathers the only data in the
channel that cannot be re-fetched. Tallinn has no licensed archive covering
the current summer, so an hour not running is an hour permanently missing.
Merging it late does not delay a feature, it shortens a series forever.

Three things in it that are deliberate rather than boilerplate:

- **hourly**, because a daily minimum from one sample a day is a reading
- **`git pull --rebase` before push**, because an hourly job will race a
  human push and a rejected push loses that hour
- **no commit when unchanged**, so a failed fetch is a quiet no-op
