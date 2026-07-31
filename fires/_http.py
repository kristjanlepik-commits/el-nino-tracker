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
import urllib.error
import urllib.request

import pandas as pd


class OverLimit(Exception):
    """FIRMS refused because the key is over its rate limit.

    Distinct from every other failure BECAUSE IT MUST NOT BE RETRIED.
    The Fire chat asked for this and the reasoning is theirs: retrying an
    over-limit request is the one case where a retry makes the situation
    strictly worse. Each attempt spends more of the budget it is waiting
    on, so a saturated key pins itself. Measured on 2026-07-29, the key
    sat at exactly 5000/5000 while the builder logged nothing but FAILED,
    having completed two countries in nine minutes.

    Every caller currently treats all exceptions alike, so an over-limit
    response costs three more requests plus 18 seconds of backoff before
    the caller gives up. Catch this separately and WAIT instead: the
    limit is 5,000 transactions per rolling 10 minutes, so the budget
    refills on a clock rather than on anything the caller does.
    """

# 25s, and the number is set by the RETRY BUDGET rather than by what a
# single request needs. A healthy FIRMS response is single-digit seconds,
# so 25 is already generous for one call.
#
# The first version used 60, which was defensible per-request and wrong
# in aggregate. Callers retry three times with 6s and 12s backoff, so a
# country whose window genuinely has no data costs 3 x 60 + 18, about
# three minutes, and fetch_window_baseline walks 45 countries. On
# 2026-07-30 three countries failed that way and the step ran past its
# budget on retries alone, having previously taken 5 minutes.
#
# At 25s the same dead country costs about 93 seconds. That is the real
# constraint: not how long one request may take, but how much a handful
# of failures may add to a step that has 45 of them to get through.
DEFAULT_TIMEOUT = 25


def read_csv(url: str, timeout: int = DEFAULT_TIMEOUT) -> pd.DataFrame:
    """`pd.read_csv(url)` that cannot hang forever.

    Reads the body under an explicit timeout, then hands pandas an
    in-memory buffer so pandas never owns the socket.

    Raises OverLimit on HTTP 400, which is what FIRMS returns when the
    key is over its rate limit. Callers should wait for quota rather than
    retry; see the OverLimit docstring.

    CAVEAT ON THE BOUND, raised by the Fire chat and worth stating rather
    than leaving implicit: urlopen's timeout applies to each socket
    operation, not to the transfer as a whole. A server trickling bytes
    can therefore exceed `timeout` in total. Not defended against here,
    because the observed failure is a stalled connection rather than a
    slow drip, and a total-transfer bound needs a reader loop that is not
    worth its complexity until we see the problem.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        # 400 is FIRMS for over-limit. It is not a malformed request:
        # the same URL succeeds once the window refills.
        if exc.code == 400:
            raise OverLimit(
                f"FIRMS returned HTTP 400 (over rate limit). Do not retry; "
                f"wait for the rolling 10 minute window to refill. url={url}"
            ) from exc
        raise
    return pd.read_csv(io.StringIO(body.decode("utf-8", errors="replace")))
