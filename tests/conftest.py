"""Shared pytest fixtures: every test gets a fresh in-memory database and a private data folder."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Fresh DB + data dir + AI wiring for each test (no network, no API keys, no shared state)."""
    monkeypatch.setenv("PRELUMA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("PRELUMA_PBKDF2_ITERATIONS", "1000")      # fast hashing in tests (production default: 600 000)
    for name in ("DEMO_USERS_JSON", "PRELUMA_ADMIN_USERS", "PRELUMA_TEACHER_INVITE_CODE", "TEACHER_INVITE_CODE",
                 "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY",
                 "TOGETHER_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        monkeypatch.delenv(name, raising=False)

    from auth import authentication
    from database.connection import configure_database
    from services import ai_service

    configure_database("sqlite://")
    authentication.reset_throttle()
    ai_service.set_router(None)
    ai_service.set_rag(None)
    ai_service.reset_rate_limits()
    try:
        import streamlit as st

        st.cache_resource.clear()
    except Exception:
        pass
    yield
    ai_service.set_router(None)
    ai_service.set_rag(None)
    ai_service.reset_rate_limits()
