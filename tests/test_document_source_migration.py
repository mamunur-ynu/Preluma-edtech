"""Synthetic migration for encrypted document recovery source."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_encrypted_source_upgrade_and_downgrade(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'old.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE knowledge_documents (id INTEGER PRIMARY KEY, title VARCHAR(160))")
        connection.exec_driver_sql("INSERT INTO knowledge_documents (id, title) VALUES (9, 'Old notes')")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261013_02")
    command.upgrade(config, "20261013_03")
    assert "source_ciphertext" in {column["name"] for column in inspect(engine).get_columns("knowledge_documents")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT source_ciphertext FROM knowledge_documents WHERE id = 9")).scalar() is None
    command.downgrade(config, "20261013_02")
    assert "source_ciphertext" not in {column["name"] for column in inspect(engine).get_columns("knowledge_documents")}
    engine.dispose()
