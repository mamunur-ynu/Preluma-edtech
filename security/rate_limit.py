"""Small in-process rate limiter for single-process demo deployments.

Production deployments with multiple workers must put equivalent limits at the
reverse proxy or a shared Redis-backed gateway. This helper still prevents one
browser session from accidentally flooding expensive AI providers locally.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque

from sqlalchemy import text

from config import get_setting, get_settings
from database.connection import session_scope


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


class DatabaseRateLimiter:
    """Atomic shared fixed-window limiter for SQLite/PostgreSQL workers.

    Uses one UPSERT/RETURNING statement, so concurrent workers cannot each
    grant their own quota. Raising happens after commit to retain denials.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(str(key or "anonymous").encode()).hexdigest()

    def check(self, key: str) -> None:
        now = int(time.time())
        with session_scope() as session:
            count = session.execute(
                text(
                    "INSERT INTO rate_limit_buckets (key_hash, window_start, count) "
                    "VALUES (:key_hash, :now, 1) "
                    "ON CONFLICT (key_hash) DO UPDATE SET "
                    "count = CASE WHEN rate_limit_buckets.window_start <= :cutoff "
                    "THEN 1 ELSE rate_limit_buckets.count + 1 END, "
                    "window_start = CASE WHEN rate_limit_buckets.window_start <= :cutoff "
                    "THEN :now ELSE rate_limit_buckets.window_start END "
                    "RETURNING count"
                ),
                {"key_hash": self._hash(key), "now": now, "cutoff": now - self.window_seconds},
            ).scalar_one()
            session.execute(
                text("DELETE FROM rate_limit_buckets WHERE window_start <= :expired"),
                {"expired": now - max(86400, self.window_seconds)},
            )
        if count > self.limit:
            raise RateLimitExceeded(
                f"Too many requests. Please wait up to {self.window_seconds} seconds and try again."
            )

    def count(self, key: str) -> int:
        cutoff = int(time.time()) - self.window_seconds
        with session_scope() as session:
            row = session.execute(
                text("SELECT count, window_start FROM rate_limit_buckets WHERE key_hash = :key_hash"),
                {"key_hash": self._hash(key)},
            ).one_or_none()
        return int(row.count) if row and row.window_start > cutoff else 0

    def clear(self, key: str) -> None:
        with session_scope() as session:
            session.execute(text("DELETE FROM rate_limit_buckets WHERE key_hash = :key_hash"),
                            {"key_hash": self._hash(key)})


def shared_limits_enabled() -> bool:
    """PostgreSQL defaults to shared counters; only local SQLite demos may opt out."""
    settings = get_settings()
    backend = get_setting("PRELUMA_RATE_LIMIT_BACKEND", "memory" if settings.is_sqlite else "database").lower()
    if backend not in {"memory", "database"}:
        raise ValueError("PRELUMA_RATE_LIMIT_BACKEND must be memory or database.")
    if backend == "memory" and not settings.is_sqlite:
        raise RuntimeError("PostgreSQL deployments require shared database rate limits.")
    return backend == "database"
