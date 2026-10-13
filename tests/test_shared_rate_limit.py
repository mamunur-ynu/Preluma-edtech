"""Shared quota contracts using independent workers on synthetic SQLite files."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from auth import create_user, issue_reset_code, login
from ai.llm_router import LLMRouter, PROVIDERS
from database.connection import configure_database, session_scope
from security.rate_limit import DatabaseRateLimiter, RateLimitExceeded, shared_limits_enabled
from services import ai_service

PASSWORD = "Passw0rd!xyz"


def _shared_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'shared.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("PRELUMA_RATE_LIMIT_BACKEND", "database")
    configure_database(url)


def test_independent_instances_share_one_atomic_quota(tmp_path, monkeypatch):
    _shared_db(tmp_path, monkeypatch)
    first = DatabaseRateLimiter(2, 60)
    second = DatabaseRateLimiter(2, 60)
    first.check("student:one")
    second.check("student:one")
    with pytest.raises(RateLimitExceeded):
        first.check("student:one")
    assert second.count("student:one") == 3  # denial is committed
    with session_scope() as session:
        stored = session.execute(text("SELECT key_hash FROM rate_limit_buckets")).scalar_one()
    assert "student" not in stored
    with session_scope() as session:
        session.execute(text("UPDATE rate_limit_buckets SET window_start = 1"))
    second.check("fresh:subject")
    assert first.count("student:one") == 0
    second.clear("student:one")
    assert first.count("student:one") == 0


def test_concurrent_workers_cannot_oversubscribe(tmp_path, monkeypatch):
    _shared_db(tmp_path, monkeypatch)
    limit = 4

    def attempt(_):
        try:
            DatabaseRateLimiter(limit, 60).check("provider:all")
            return True
        except RateLimitExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(12)))
    assert sum(outcomes) == limit


def test_login_reset_and_ai_use_shared_database_counters(tmp_path, monkeypatch):
    _shared_db(tmp_path, monkeypatch)
    monkeypatch.setenv("PRELUMA_AI_REQUESTS_PER_MINUTE", "1")
    assert shared_limits_enabled()
    student = create_user("shared-student", PASSWORD, "Student")
    teacher = create_user("shared-teacher", PASSWORD, "Teacher", "teacher")
    for _ in range(5):
        assert login(student.username, "bad-password")[0] is None
    assert "Too many" in login(student.username, PASSWORD)[1]
    assert all(issue_reset_code(teacher.id, student.username)[0] for _ in range(3))
    assert not issue_reset_code(teacher.id, student.username)[0]
    ai_service.chat(student.id, "Explain statistics")
    with pytest.raises(RateLimitExceeded):
        ai_service.ask_tutor("Explain statistics", user_id=student.id)


def test_postgres_cannot_fall_back_to_process_local_limits(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://unused@localhost/unused")
    monkeypatch.setenv("PRELUMA_RATE_LIMIT_BACKEND", "memory")
    with pytest.raises(RuntimeError, match="require shared"):
        shared_limits_enabled()


def test_provider_budget_counts_actual_calls_and_stops_failover(tmp_path, monkeypatch):
    _shared_db(tmp_path, monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    monkeypatch.setenv("PRELUMA_PROVIDER_CALLS_PER_HOUR", "1")
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(url)
        return {"choices": [{"message": {"content": "synthetic answer"}}]}

    first_worker = LLMRouter(PROVIDERS[:1], transport=transport)
    second_worker = LLMRouter(PROVIDERS[:1], transport=transport)
    assert first_worker.complete("system", "question").ok
    denied = second_worker.complete("system", "another question")
    assert not denied.ok and "budget" in second_worker.last_error.lower()
    assert len(calls) == 1


def test_postgres_without_approved_provider_budget_makes_no_call(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://unused@localhost/unused")
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    called = []
    router = LLMRouter(PROVIDERS[:1], transport=lambda *args: called.append(args))
    assert not router.complete("system", "question").ok
    assert called == []
