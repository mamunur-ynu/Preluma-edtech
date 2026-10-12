"""
database/connection.py — engine and session management.

SQLite (a single file under ``data/``) is the zero-configuration default, which keeps
local development and Streamlit Cloud demos simple.  Set ``DATABASE_URL`` to a PostgreSQL
URL (for example Supabase's connection string) for production; no other code changes.

Usage::

    with session_scope() as session:
        repo = UserRepository(session)
        ...                      # commit on success, rollback on exception
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import get_settings
from database.models import Base

logger = logging.getLogger("preluma.database")

_lock = threading.Lock()
_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False, "timeout": 30}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # one shared in-memory DB (tests)
        else:
            from pathlib import Path

            db_path = url.replace("sqlite:///", "", 1)
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, future=True, **kwargs)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record) -> None:  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            if "memory" not in url and url != "sqlite://":
                cur.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
            cur.close()

        return engine
    return create_engine(url, future=True, pool_pre_ping=True)


def configure_database(url: str | None = None, *, create_tables: bool = True) -> Engine:
    """(Re)initialise the global engine.  Tests call this with ``"sqlite://"``."""
    global _engine, _factory
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = _build_engine(url or get_settings().database_url)
        _factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        if create_tables:
            Base.metadata.create_all(_engine)
        return _engine


def get_engine() -> Engine:
    """Return the global engine, creating it (and the tables) on first use."""
    if _engine is None:
        configure_database()
    if _engine is None:  # defensive: configure_database must initialise it
        raise RuntimeError("Database engine initialisation failed.")
    return _engine


def init_db() -> None:
    """Create any missing tables.  Idempotent; cheap enough to call at start-up."""
    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit if the block succeeds, roll back otherwise."""
    get_engine()
    if _factory is None:  # defensive: get_engine must initialise it
        raise RuntimeError("Database session factory initialisation failed.")
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
