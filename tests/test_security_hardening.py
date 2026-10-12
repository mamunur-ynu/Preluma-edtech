"""Behavioral security and authorization regression tests."""

from __future__ import annotations

import pytest
from datetime import timedelta

from ai.documents import SourceDocument
from ai.embeddings import HashingEmbedder
from ai.rag_engine import RAGEngine
from auth import create_user
from database.connection import session_scope
from database.models import AIConversationMessage, Course, utcnow
from database.repository import ConversationRepository, CourseRepository
from security.rate_limit import InProcessRateLimiter, RateLimitExceeded
from security.uploads import UploadPolicy, validate_upload
from services import ai_service, course_service

PW = "Passw0rd!xyz"


def test_browser_persistence_is_off_unless_explicitly_enabled(monkeypatch):
    from components.session_bridge import persistence_available

    assert persistence_available() is False
    monkeypatch.setenv("PRELUMA_ALLOW_LEGACY_BROWSER_SESSION", "true")
    assert persistence_available() is True


def test_upload_validation_rejects_spoofed_content_and_path_traversal():
    policy = UploadPolicy(frozenset({".pdf", ".txt"}), 1024, "test file")
    with pytest.raises(ValueError, match="does not match"):
        validate_upload("report.pdf", b"MZ not a pdf", policy)
    checked = validate_upload("../../unsafe name.txt", b"safe text", policy)
    assert checked.filename == "unsafe name.txt"
    with pytest.raises(ValueError, match="NUL"):
        validate_upload("bad.txt", b"hello\x00world", policy)


def test_rate_limiter_enforces_sliding_window():
    limiter = InProcessRateLimiter(2, 60)
    limiter.check("student:1")
    limiter.check("student:1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("student:1")
    limiter.check("student:2")


def test_rag_filters_private_and_cross_course_documents_before_ranking():
    rag = RAGEngine(embedder=HashingEmbedder())
    text = "Orchid security protocol uses a violet handshake token. " * 5
    rag.index_document(SourceDocument("public", "Public", text, metadata={"visibility": "public"}))
    rag.index_document(
        SourceDocument(
            "course-a", "Course A", text, metadata={"visibility": "course", "course_id": 10, "uploaded_by": 1}
        )
    )
    rag.index_document(
        SourceDocument(
            "private", "Private", text, metadata={"visibility": "private", "uploaded_by": 2}
        )
    )
    student_one = rag.retrieve("orchid violet handshake", k=10, user_id=1, allowed_course_ids={10})
    assert {hit.doc_id for hit in student_one} == {"public", "course-a"}
    student_two = rag.retrieve("orchid violet handshake", k=10, user_id=2, allowed_course_ids=set())
    assert {hit.doc_id for hit in student_two} == {"public", "private"}


def test_knowledge_document_management_enforces_role_and_ownership():
    student = create_user("student-sec", PW, "Student Sec")
    teacher_a = create_user("teacher-a", PW, "Teacher A", "teacher")
    teacher_b = create_user("teacher-b", PW, "Teacher B", "teacher")
    payload = ("Secure indexing content with enough words. " * 8).encode()
    with pytest.raises(PermissionError):
        ai_service.index_document("notes.txt", payload, uploaded_by=student.id)
    result = ai_service.index_document("notes.txt", payload, uploaded_by=teacher_a.id)
    doc_id = int(result.doc_id.split(":")[1])
    with pytest.raises(PermissionError):
        ai_service.remove_document(doc_id, teacher_b.id)
    assert ai_service.remove_document(doc_id, teacher_a.id)


def test_teacher_cannot_read_another_teachers_owned_course_analytics():
    owner = create_user("owner-teacher", PW, "Owner Teacher", "teacher")
    outsider = create_user("other-teacher", PW, "Other Teacher", "teacher")
    student = create_user("course-student", PW, "Course Student")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="private-course", title="Private", owner_id=owner.id))
        course_id = course.id
    with pytest.raises(PermissionError):
        course_service.course_completion_report(course_id, outsider.id)
    with pytest.raises(PermissionError):
        course_service.course_completion_report(course_id, student.id)
    assert course_service.course_completion_report(course_id, owner.id) == []


def test_conversation_history_is_user_scoped_revocable_and_retained_for_a_bounded_period(monkeypatch):
    first = create_user("memory-one", PW, "Memory One")
    second = create_user("memory-two", PW, "Memory Two")
    monkeypatch.setenv("PRELUMA_CONVERSATION_RETENTION_DAYS", "1")
    session_id = ai_service.new_session_id()
    with session_scope() as session:
        ConversationRepository(session).add(
            AIConversationMessage(
                user_id=first.id,
                session_id=session_id,
                role="user",
                content="expired",
                created_at=utcnow() - timedelta(days=2),
            )
        )
    ai_service.chat(first.id, "What is statistics?", session_id=session_id)
    first_history = ai_service.get_history(first.id, session_id)
    assert all(item["content"] != "expired" for item in first_history)
    assert ai_service.get_history(second.id, session_id) == []
    assert ai_service.clear_session(second.id, session_id) == 0
    assert ai_service.clear_session(first.id, session_id) == len(first_history)
