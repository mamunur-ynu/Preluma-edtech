"""Synthetic schema roundtrip for the database-backed retrieval index."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_shared_vector_upgrade_and_downgrade(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'old.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    engine = create_engine(db_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_04")
    command.upgrade(config, "20261013_05")
    assert {"id", "doc_id", "embedder", "dim", "text", "source", "metadata_json", "vector_json"} == {
        column["name"] for column in inspect(engine).get_columns("vector_chunks")
    }
    command.downgrade(config, "20261013_04")
    assert "vector_chunks" not in inspect(engine).get_table_names()
    engine.dispose()
