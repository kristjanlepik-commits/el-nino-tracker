"""Wait for the FIRMS key to drain, instead of retrying into a wall.

The caller side of platform's `_http.OverLimit`. Three modules fetch
from FIRMS and all three treated every failure identically, so an
over-limit response cost three more requests plus backoff. That is the
one case where retrying makes the situation actively worse: the key is
over its limit precisely because too many requests arrived, and the
retry is more requests.

Measured on 2026-07-29: the key sat pinned at 5000/5000 while the
builder logged nothing but FAILED, having completed two countries in
nine minutes. A saturated key generates more traffic than a healthy one
and holds itself there.

So an OverLimit does not consume a retry. It suspends the caller until
the quota is actually available, checked against the status endpoint
rather than guessed at with a fixed sleep, because the window is a
rolling ten minutes and a fixed sleep is either wasteful or useless
depending on where in the window it lands.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

KEY_PATH = os.path.expanduser("~/.firms_map_key")
STATUS = ("https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/"
          "?MAP_KEY={key}")

# Resume below this, not at zero. The window is rolling, so it drains
# continuously and waiting for empty wastes most of a window. 1000 of
# 5000 leaves room for one caller's burst without immediately
# re-saturating, and matches the threshold platform's pacing wrapper
# settled on independently.
RESUME_BELOW = 1000
POLL_SECONDS = 30
MAX_WAIT_SECONDS = 900


def current_transactions(key: str | None = None) -> int | None:
    """Transactions used in the rolling window, or None if unreadable.

    None means "cannot tell", and callers treat that as a reason to wait
    a fixed interval rather than to charge ahead: an unreadable status
    endpoint is not evidence of available quota.
    """
    try:
        if key is None:
            key = open(KEY_PATH).read().strip()
        with urllib.request.urlopen(STATUS.format(key=key), timeout=15) as r:
            return int(json.loads(r.read().decode())["current_transactions"])
    except Exception:
        return None


def wait_for_quota(label: str = "") -> None:
    """Block until the key has room, or until MAX_WAIT_SECONDS."""
    waited = 0
    while waited < MAX_WAIT_SECONDS:
        used = current_transactions()
        if used is not None and used < RESUME_BELOW:
            if waited:
                print(f"  quota available ({used}/5000) after {waited}s"
                      f"{' ' + label if label else ''}", file=sys.stderr,
                      flush=True)
            return
        shown = "unreadable" if used is None else f"{used}/5000"
        print(f"  over limit ({shown}), waiting {POLL_SECONDS}s"
              f"{' ' + label if label else ''}", file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    # Give up waiting rather than hang a CI step forever. The caller's
    # own retry then runs, and if it fails the country is dropped for
    # this window, which is the existing and correct behaviour.
    print(f"  still over limit after {MAX_WAIT_SECONDS}s, proceeding"
          f"{' ' + label if label else ''}", file=sys.stderr, flush=True)
