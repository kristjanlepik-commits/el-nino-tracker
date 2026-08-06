#!/usr/bin/env bash
# Em-dash guard, invariant 6. EXITS NON-ZERO on a violation.
#
# The inline form used in Heat's commits for two days was broken:
#   (grep ... && echo "EM-DASH" || echo "clean") && git commit
# The group's exit status is the echo's, which is always 0, so it REPORTED a
# violation and committed anyway. It found a real em-dash and did not stop it.
# A guard that cannot fail the command it guards is a comment.
#
# Allowlist per CLAUDE.md invariant 6: LICENSE, the two frozen May archives,
# and the regex character classes in fetchers/iri.py that parse upstream
# em-dashes.
#
# The two archives are listed BY DATE rather than as docs/briefs/*, so a NEW
# brief cannot inherit the exemption. Invariant 6 says the known hits must not
# grow; a wildcard would let them.
set -uo pipefail
DASH=$(printf '\xe2\x80\x94')
hits=$(git ls-files -z | xargs -0 grep -l "$DASH" 2>/dev/null \
       | grep -v '^LICENSE$' \
       | grep -v '^docs/briefs/2026-05-18/' \
       | grep -v '^docs/briefs/2026-05-25/' \
       | grep -v '^fetchers/iri.py$' || true)
if [ -n "$hits" ]; then
  echo "em-dash found outside the allowlist:" >&2
  echo "$hits" | sed 's/^/  /' >&2
  exit 1
fi
echo "em-dash check: clean"
