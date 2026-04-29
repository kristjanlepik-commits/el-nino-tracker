"""
Shared helpers for fetcher modules.

Every fetcher returns a dict with at minimum:
  - issued: ISO date string (when the source agency issued the data)
  - fetched_at: ISO datetime string (when we ran the fetch)
  - ok: bool (True if fetch + parse succeeded)
  - error: str or None
plus source-specific payload fields.

Failed fetches do NOT raise. The orchestrator falls back to the last
good snapshot's value for that source and flags the brief as
partially stale. This keeps the pipeline running on Mondays when one
agency's site is down or has changed format.
"""

from __future__ import annotations
import json
import os
import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import requests


class FetcherTimeout(Exception):
    """Raised when a fetcher exceeds its per-source time budget."""


@contextmanager
def _alarm(seconds: int):
    """SIGALRM-based wall-clock timeout (POSIX, main thread only).

    cdsapi's CDS queue-wait can stretch into hours; we want to bound that so
    a slow Copernicus day doesn't kill the whole Monday workflow run. The
    alarm interrupts blocking syscalls (sockets, sleeps) and propagates as
    FetcherTimeout, which safe_fetch catches and treats like any other
    fetch failure (cache fallback).
    """
    if seconds is None or seconds <= 0:
        yield
        return

    def _handler(signum, frame):
        raise FetcherTimeout(f"fetcher exceeded {seconds}s budget")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(int(seconds))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

CACHE_DIR = Path(__file__).parent.parent / ".fetch_cache"
CACHE_DIR.mkdir(exist_ok=True)


@dataclass
class FetchResult:
    source: str
    ok: bool
    issued: Optional[str] = None     # ISO date stamped by agency
    fetched_at: str = ""              # ISO datetime when we ran it
    payload: dict = field(default_factory=dict)
    error: Optional[str] = None
    used_fallback: bool = False       # True if we returned a cached value

    def to_jsonable(self) -> dict:
        return asdict(self)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def http_get(url: str, *, timeout: int = 30, retries: int = 2,
             user_agent: str = "el-nino-tracker/1.5 (internal)") -> requests.Response:
    """GET with simple exponential backoff. Raises on final failure."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout,
                             headers={"User-Agent": user_agent})
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise last_err  # type: ignore[misc]


def cache_path(source: str) -> Path:
    return CACHE_DIR / f"{source}_last_good.json"


def write_cache(source: str, result: FetchResult) -> None:
    """Persist a successful fetch as the last-good fallback."""
    if result.ok:
        cache_path(source).write_text(json.dumps(result.to_jsonable(), indent=2))


def read_cache(source: str) -> Optional[FetchResult]:
    p = cache_path(source)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return FetchResult(**d)
    except Exception:
        return None


def safe_fetch(source: str, fn: Callable[[], FetchResult],
               timeout_seconds: Optional[int] = None) -> FetchResult:
    """
    Run a fetcher. On exception OR ok=False OR timeout, return last-good
    cache with used_fallback=True. The orchestrator decides what to do.

    `timeout_seconds`, if set, bounds the fetch wall-clock via SIGALRM. Use
    it for fetchers that hit external queues (CDS for SEAS5/ERA5) where a
    slow day could otherwise hang the entire workflow until the runner-level
    timeout-minutes limit kills it.
    """
    try:
        with _alarm(timeout_seconds):
            result = fn()
        if result.ok:
            write_cache(source, result)
            return result
        # Parser ran but result not ok; fall back
        cached = read_cache(source)
        if cached:
            cached.used_fallback = True
            cached.error = result.error or "parser returned ok=False"
            return cached
        return result   # no cache, return the failure as-is
    except Exception as e:
        cached = read_cache(source)
        if cached:
            cached.used_fallback = True
            cached.error = f"{type(e).__name__}: {e}"
            return cached
        return FetchResult(source=source, ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
