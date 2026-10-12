"""Small in-process rate limiter for single-process demo deployments.

Production deployments with multiple workers must put equivalent limits at the
reverse proxy or a shared Redis-backed gateway. This helper still prevents one
browser session from accidentally flooding expensive AI providers locally.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimitExceeded(RuntimeError):
    """Raised when a caller exceeds a configured sliding-window limit."""


class InProcessRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        safe_key = str(key or "anonymous")[:160]
        with self._lock:
            events = self._events[safe_key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                raise RateLimitExceeded(
                    f"Too many requests. Please wait up to {self.window_seconds} seconds and try again."
                )
            events.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
