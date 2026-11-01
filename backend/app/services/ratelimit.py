"""In-process sliding-window rate limiting for the public surfaces.

One process, one window. That is enough to stop a runaway client (or a
spoofed identity loop) from burning model credits during a demo. It is
explicitly *not* a distributed limiter: with several workers each process
keeps its own counts. The honest ceiling is documented in the README.

``RATE_LIMIT_PER_MINUTE=0`` disables limiting (used by the test suite).
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request


class SlidingWindow:
    """Allow at most ``limit`` events per ``window_seconds`` per key."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        current = now if now is not None else time.monotonic()
        cutoff = current - self.window
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(current)
            # A spoofed-header flood must not grow this map forever.
            if len(self._hits) > 10_000:
                self._hits.clear()
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _configured_limit() -> int:
    try:
        return max(0, int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")))
    except ValueError:
        return 60


limiter = SlidingWindow(_configured_limit())


def client_key(request: Request) -> str:
    """Prefer the identity the request claims, fall back to the caller IP."""
    phone = (request.headers.get("X-Phone-Number") or "").strip()
    if phone:
        return f"phone:{phone}"
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    host = request.client.host if request.client else "unknown"
    return f"ip:{forwarded or host}"


async def rate_limit(request: Request) -> None:
    if not limiter.allow(client_key(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many captures in a minute. Wait a moment and try again.",
        )
