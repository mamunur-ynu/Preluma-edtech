"""Revision 06 is additive and reversible on a synthetic legacy schema."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
