"""Synthetic old-schema migration preserves attempts without guessing their course."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_course_provenance_upgrade_and_downgrade(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'old.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE courses (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE lessons (id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL)")
        connection.exec_driver_sql("INSERT INTO courses (id) VALUES (3)")
        connection.exec_driver_sql("INSERT INTO lessons (id, course_id) VALUES (4, 3)")
        connection.exec_driver_sql(
            "CREATE TABLE quiz_attempts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "lesson_id INTEGER, topic VARCHAR(80) NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO quiz_attempts (id, user_id, topic, score, total) VALUES (7, 1, 'statistics', 4, 5)"
        )
        connection.exec_driver_sql(
            "INSERT INTO quiz_attempts (id, user_id, lesson_id, topic, score, total) "
            "VALUES (8, 1, 4, 'statistics', 4, 5)"
        )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_01")
    command.upgrade(config, "20261013_02")
    assert "course_id" in {column["name"] for column in inspect(engine).get_columns("quiz_attempts")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT course_id FROM quiz_attempts WHERE id = 7")).scalar() is None
        assert connection.execute(text("SELECT course_id FROM quiz_attempts WHERE id = 8")).scalar() == 3
    command.downgrade(config, "20261013_01")
    assert "course_id" not in {column["name"] for column in inspect(engine).get_columns("quiz_attempts")}
    engine.dispose()
