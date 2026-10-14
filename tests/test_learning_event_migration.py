"""Revision 06 is additive and reversible on a synthetic legacy schema."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
import pytest


def test_learning_event_migration_roundtrip(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        for name in ("users", "courses", "lessons"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_05")
    command.upgrade(config, "20261013_06")
    assert {"learning_events", "learning_outbox", "course_mastery"} <= set(inspect(engine).get_table_names())
    assert {"users", "courses", "lessons"} <= set(inspect(engine).get_table_names())
    command.downgrade(config, "20261013_05")
    assert "learning_events" not in inspect(engine).get_table_names()
    assert {"users", "courses", "lessons"} <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_outbox_quarantine_migration_roundtrip(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'quarantine.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        for name in ("users", "courses", "lessons"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_05")
    command.upgrade(config, "20261014_07")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_outbox")}
    assert {"quarantined_at", "quarantine_reason"} <= columns
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO users (id) VALUES (1)")
        connection.exec_driver_sql("""
            INSERT INTO learning_events
            (id, schema_version, event_type, user_id, source_type, source_id,
             producer, idempotency_key, occurred_at, recorded_at, payload_json)
            VALUES ('synthetic', 1, 'quiz.completed', 1, 'quiz_attempt', '1',
                    'learning_service', 'quiz:1', '2026-01-01', '2026-01-01', '{}')
        """)
        connection.exec_driver_sql("""
            INSERT INTO learning_outbox
            (event_id, created_at, quarantined_at, quarantine_reason)
            VALUES ('synthetic', '2026-01-01', '2026-01-02', 'invalid_evidence')
        """)
    with pytest.raises(RuntimeError, match="populated learning-event quarantine"):
        command.downgrade(config, "20261013_06")
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM learning_outbox WHERE event_id = 'synthetic'")
    command.downgrade(config, "20261013_06")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_outbox")}
    assert "quarantined_at" not in columns and "quarantine_reason" not in columns
    engine.dispose()


def test_quarantine_operator_migration_preserves_attribution(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'operator.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        for name in ("users", "courses", "lessons"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_05")
    command.upgrade(config, "20261014_07")
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO users (id) VALUES (1), (2)")
        connection.exec_driver_sql("""
            INSERT INTO learning_events
            (id, schema_version, event_type, user_id, source_type, source_id,
             producer, idempotency_key, occurred_at, recorded_at, payload_json)
            VALUES ('synthetic', 1, 'quiz.completed', 1, 'quiz_attempt', '1',
                    'learning_service', 'quiz:1', '2026-01-01', '2026-01-01', '{}')
        """)
        connection.exec_driver_sql("""
            INSERT INTO learning_outbox
            (event_id, created_at, quarantined_at, quarantine_reason)
            VALUES ('synthetic', '2026-01-01', '2026-01-02', 'invalid_evidence')
        """)
    command.upgrade(config, "20261014_08")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_outbox")}
    assert "quarantined_by_user_id" in columns
    assert any(
        fk["constrained_columns"] == ["quarantined_by_user_id"]
        for fk in inspect(engine).get_foreign_keys("learning_outbox")
    )
    with engine.begin() as connection:
        legacy_actor = connection.exec_driver_sql(
            "SELECT quarantined_by_user_id FROM learning_outbox WHERE event_id = 'synthetic'"
        ).scalar_one()
        assert legacy_actor is None  # Never invent an operator for earlier markers.
        connection.exec_driver_sql(
            "UPDATE learning_outbox SET quarantined_by_user_id = 2 WHERE event_id = 'synthetic'"
        )
    with pytest.raises(RuntimeError, match="quarantine operator audit"):
        command.downgrade(config, "20261014_07")
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM learning_outbox WHERE event_id = 'synthetic'")
    command.downgrade(config, "20261014_07")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_outbox")}
    assert "quarantined_by_user_id" not in columns
    engine.dispose()


def test_correction_actor_migration_preserves_legacy_and_guards_downgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'correction.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        for name in ("users", "courses", "lessons"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_05")
    command.upgrade(config, "20261014_08")
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO users (id) VALUES (1), (2)")
        connection.exec_driver_sql("""
            INSERT INTO learning_events
            (id, schema_version, event_type, user_id, source_type, source_id,
             producer, idempotency_key, occurred_at, recorded_at, payload_json)
            VALUES ('original', 1, 'quiz.completed', 1, 'quiz_attempt', '1',
                    'learning_service', 'quiz:1', '2026-01-01', '2026-01-01', '{}')
        """)
    command.upgrade(config, "20261014_09")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_events")}
    assert "actor_user_id" in columns
    assert any(
        fk["constrained_columns"] == ["actor_user_id"]
        for fk in inspect(engine).get_foreign_keys("learning_events")
    )
    with engine.begin() as connection:
        assert connection.exec_driver_sql(
            "SELECT actor_user_id FROM learning_events WHERE id = 'original'"
        ).scalar_one() is None
        connection.exec_driver_sql("""
            INSERT INTO learning_events
            (id, schema_version, event_type, user_id, source_type, source_id,
             producer, idempotency_key, actor_user_id, occurred_at, recorded_at, payload_json)
            VALUES ('correction', 1, 'quiz.voided', 1, 'learning_event', 'original',
                    'learning_correction', 'void:original', 2, '2026-01-02', '2026-01-02', '{}')
        """)
    with pytest.raises(RuntimeError, match="correction operator audit"):
        command.downgrade(config, "20261014_08")
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM learning_events WHERE id = 'correction'")
    command.downgrade(config, "20261014_08")
    columns = {column["name"] for column in inspect(engine).get_columns("learning_events")}
    assert "actor_user_id" not in columns
    engine.dispose()
