"""Two independent engines observe one committed retrieval index."""

from ai.documents import SourceDocument
from ai.embeddings import HashingEmbedder
from ai.rag_engine import RAGEngine
from ai.vector_store import DatabaseVectorStore
from auth import create_user
from database.connection import session_scope
from database.models import VectorChunk
from services import ai_service


def _engine():
    return RAGEngine(embedder=HashingEmbedder(), vector_backend="database")


def test_independent_workers_see_upload_replacement_and_delete():
    first, second = _engine(), _engine()
    original = SourceDocument("doc:31", "Shared note", "The violet compass aligns the learning lattice. " * 5,
                              "notes.txt", {"visibility": "public", "uploaded_by": 1,
                                            "content_sha256": "a" * 64})
    first.index_document(original)
    assert second.store.has_document("doc:31")
    assert second.retrieve("violet compass", k=1)[0].doc_id == "doc:31"
    replacement = SourceDocument("doc:31", "Shared note", "The amber pendulum guides the new lesson. " * 5,
                                 "notes.txt", {"visibility": "public", "uploaded_by": 1,
                                               "content_sha256": "b" * 64})
    second.index_document(replacement)
    assert "amber pendulum" in first.retrieve("amber pendulum", k=1)[0].text
    assert "violet compass" not in first.retrieve("amber pendulum", k=1)[0].text
    first.delete_document("doc:31")
    assert second.store.has_document("doc:31") is False


def test_shared_store_reconciles_missing_uploaded_chunks():
    teacher = create_user("teacher", "Passw0rd!xyz", "Teacher", "teacher")
    first = _engine()
    ai_service.set_rag(first)
    result = ai_service.index_document(
        "note.txt", ("The blue lantern teaches database retrieval. " * 10).encode(),
        uploaded_by=teacher.id,
    )
    other_worker = _engine()
    assert other_worker.store.has_document(result.doc_id)
    with session_scope() as session:
        row = session.get(VectorChunk, f"{result.doc_id}#0")
        assert row.text.startswith("fernet:")
        assert "blue lantern" not in row.text
    first.delete_document(result.doc_id)
    assert ai_service.reconcile_document_index(other_worker)["recovered"] == 1
    assert first.store.has_document(result.doc_id)


def test_shared_backend_never_writes_local_json(tmp_path):
    engine = RAGEngine(embedder=HashingEmbedder(), vector_backend="database",
                       index_path=tmp_path / "unused.json")
    assert isinstance(engine.store, DatabaseVectorStore)
    engine.index_document(SourceDocument("topic:test", "Public", "A learning topic. " * 10,
                                         "Curated", {"visibility": "public"}))
    assert not (tmp_path / "unused.json").exists()
