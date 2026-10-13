"""Synthetic migration for shared rate-limit counters."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_shared_bucket_upgrade_and_downgrade(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'old.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    engine = create_engine(db_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_03")
    command.upgrade(config, "20261013_04")
    assert {"key_hash", "window_start", "count"} == {
        column["name"] for column in inspect(engine).get_columns("rate_limit_buckets")
    }
    assert "ix_rate_limit_buckets_window_start" in {
        index["name"] for index in inspect(engine).get_indexes("rate_limit_buckets")
    }
    command.downgrade(config, "20261013_03")
    assert "rate_limit_buckets" not in inspect(engine).get_table_names()
    engine.dispose()
