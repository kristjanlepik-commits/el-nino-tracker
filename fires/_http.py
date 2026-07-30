"""Bounded CSV fetch for the FIRMS API.

WHY THIS EXISTS. All three FIRMS callers used `pd.read_csv(url)`
directly. Pandas reads a URL through urllib with NO default timeout, so
an unanswered request blocks forever.

The part that made it expensive: every caller already had a three-try
retry loop with backoff, and none of them helped. A hang does not raise,
so the retry was never reached. The call sat there looking like work.

On 2026-07-30 that took down the whole daily fires publish. The
same-week baseline refresh hung with no output for 58 minutes, the
job-level 60 minute timeout then cancelled every step after it, and the
public fire page did not refresh at all. The same step had finished in
about 5 minutes the day before, so the failure is intermittent.

So the fix is not really "add a timeout", it is "make the failure
visible to the retry that was already written". With a bounded read a
stalled request raises, the existing backoff engages, and a slow FIRMS
response costs seconds instead of a morning.

Ownership note: `fires/` is the Fire chat's. This module was added by
platform on 2026-07-30 at Kristjan's explicit instruction ("fix it"),
because detections had not advanced for two days and the fix is
reliability rather than science. Tracked as tls-internal issue #6.
"""

from __future__ import annotations

import io
import urllib.request

import pandas as pd

# 60s is well beyond a healthy FIRMS response, which is single-digit
# seconds, and well short of the 10 minute step budget in the workflow.
# The point is not to be tight, it is to be finite: with three tries and
# 6s and 12s backoff, a fully dead endpoint costs about 3 minutes and
# then raises, rather than consuming the entire job.
DEFAULT_TIMEOUT = 60


def read_csv(url: str, timeout: int = DEFAULT_TIMEOUT) -> pd.DataFrame:
    """`pd.read_csv(url)` that cannot hang forever.

    Reads the body under an explicit timeout, then hands pandas an
    in-memory buffer so pandas never owns the socket.
    """
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        body = resp.read()
    return pd.read_csv(io.StringIO(body.decode("utf-8", errors="replace")))
