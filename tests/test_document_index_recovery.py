"""Crash-window recovery for uploaded-document metadata and persisted vectors."""

import pytest

from ai.documents import SourceDocument
from ai.embeddings import HashingEmbedder
from ai.rag_engine import RAGEngine
from auth import create_user
from database.connection import session_scope
from database.repository import KnowledgeDocumentRepository
from services import ai_service

PASSWORD = "Passw0rd!xyz"
PAYLOAD = ("The copper lantern protocol protects the quiet archive. " * 12).encode()


def _engine(path):
    return RAGEngine(embedder=HashingEmbedder(), index_path=path, vector_backend="memory")


def test_restart_removes_orphan_vectors_after_interrupted_delete(tmp_path):
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    path = tmp_path / "index.json"
    engine = _engine(path)
    ai_service.set_rag(engine)
    result = ai_service.index_document("notes.txt", PAYLOAD, uploaded_by=teacher.id)
    with session_scope() as session:
        KnowledgeDocumentRepository(session).delete(int(result.doc_id.split(":")[1]))
    restarted = _engine(path)
    assert restarted.store.has_document(result.doc_id)
    assert ai_service.reconcile_document_index(restarted)["removed"] == 1
    assert not _engine(path).store.has_document(result.doc_id)


def test_restart_marks_missing_vectors_for_reupload_and_retry(tmp_path):
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    path = tmp_path / "index.json"
    engine = _engine(path)
    ai_service.set_rag(engine)
    result = ai_service.index_document("notes.txt", PAYLOAD, uploaded_by=teacher.id)
    engine.delete_document(result.doc_id)
    restarted = _engine(path)
    assert ai_service.reconcile_document_index(restarted)["missing"] == 1
    with session_scope() as session:
        assert KnowledgeDocumentRepository(session).get(int(result.doc_id.split(":")[1])).n_chunks == 0
    ai_service.set_rag(restarted)
    retried = ai_service.index_document("notes.txt", PAYLOAD, uploaded_by=teacher.id)
    assert retried.doc_id == result.doc_id and retried.chunks > 0
    assert _engine(path).store.has_document(result.doc_id)


def test_restart_discards_tampered_scope_and_repairs_saved_count(tmp_path):
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    path = tmp_path / "index.json"
    engine = _engine(path)
    ai_service.set_rag(engine)
    result = ai_service.index_document("notes.txt", PAYLOAD, uploaded_by=teacher.id)
    row_id = int(result.doc_id.split(":")[1])
    with session_scope() as session:
        KnowledgeDocumentRepository(session).get(row_id).n_chunks = 0
    assert ai_service.reconcile_document_index(_engine(path))["repaired"] == 1
    with session_scope() as session:
        assert KnowledgeDocumentRepository(session).get(row_id).n_chunks == result.chunks

    engine.index_document(SourceDocument(result.doc_id, "Forged", PAYLOAD.decode(), "forged.txt",
                                         {"visibility": "public", "uploaded_by": 999,
                                          "content_sha256": "forged", "course_id": None}))
    restarted = _engine(path)
    assert ai_service.reconcile_document_index(restarted)["removed"] == 1
    assert restarted.store.document_metadata(result.doc_id) is None
    with session_scope() as session:
        assert KnowledgeDocumentRepository(session).get(row_id).n_chunks == 0


def test_failed_vector_delete_preserves_metadata_for_retry(tmp_path, monkeypatch):
    teacher = create_user("teacher", PASSWORD, "Teacher", "teacher")
    engine = _engine(tmp_path / "index.json")
    ai_service.set_rag(engine)
    result = ai_service.index_document("notes.txt", PAYLOAD, uploaded_by=teacher.id)
    row_id = int(result.doc_id.split(":")[1])

    def failed_delete(_doc_id):
        raise OSError("simulated index failure")

    with monkeypatch.context() as patch:
        patch.setattr(engine, "delete_document", failed_delete)
        with pytest.raises(OSError, match="simulated"):
            ai_service.remove_document(row_id, teacher.id)
    with session_scope() as session:
        assert KnowledgeDocumentRepository(session).get(row_id) is not None
    assert ai_service.remove_document(row_id, teacher.id)
    assert _engine(tmp_path / "index.json").store.has_document(result.doc_id) is False
