"""Behavioral security and authorization regression tests."""

from __future__ import annotations

import pytest
from datetime import timedelta

from ai.documents import SourceDocument, pack_to_documents
from ai.embeddings import HashingEmbedder
from ai.rag_engine import RAGEngine
from auth import create_user, issue_reset_code
from database.connection import session_scope
from database.models import AIConversationMessage, Course, Lesson, utcnow
from database.repository import ConversationRepository, CourseRepository, KnowledgeDocumentRepository, LessonRepository, UserRepository
from security.rate_limit import InProcessRateLimiter, RateLimitExceeded
from security.uploads import UploadPolicy, validate_upload
from services import ai_service, course_service, learning_service, recommendation_service, user_service

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


def test_ai_request_budget_is_shared_across_chat_and_tutor(monkeypatch):
    user = create_user("budget-student", PW, "Budget Student")
    monkeypatch.setattr(ai_service, "_ai_limiter", InProcessRateLimiter(1, 60))
    ai_service.chat(user.id, "What is statistics?")
    with pytest.raises(RateLimitExceeded):
        ai_service.ask_tutor("Explain statistics", user_id=user.id)


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


def test_unlabelled_legacy_chunks_are_hidden_and_curated_topics_remain_public(tmp_path):
    index_path = tmp_path / "index.json"
    rag = RAGEngine(embedder=HashingEmbedder(), index_path=index_path)
    text = "Legacy secret course marker only appears in an unlabelled upload. " * 5
    rag.index_document(SourceDocument("doc:old", "Legacy upload", text, "old.txt"))
    assert rag.retrieve("legacy secret course marker", k=5, user_id=1, allowed_course_ids=set()) == []

    curated = pack_to_documents({"statistics": {"title": "Statistics", "definition": "Statistics explains data."}})
    assert curated[0].metadata["visibility"] == "public"
    # Simulate a pre-hardening persisted curated chunk without a visibility label.
    rag.index_document(SourceDocument(curated[0].doc_id, curated[0].title, curated[0].text,
                                      curated[0].source, {"topic": "statistics"}))
    loaded = RAGEngine(embedder=HashingEmbedder(), index_path=index_path)
    assert loaded.index_missing(curated) > 0
    assert any(hit.doc_id == curated[0].doc_id for hit in loaded.retrieve("statistics data", k=5))
    assert all(hit.doc_id != "doc:old" for hit in loaded.retrieve("legacy secret course marker", k=5))


def test_knowledge_document_management_enforces_role_and_ownership():
    student = create_user("student-sec", PW, "Student Sec")
    teacher_a = create_user("teacher-a", PW, "Teacher A", "teacher")
    teacher_b = create_user("teacher-b", PW, "Teacher B", "teacher")
    payload = ("Secure indexing content with enough words. " * 8).encode()
    with pytest.raises(PermissionError):
        ai_service.index_document("notes.txt", payload, uploaded_by=student.id)
    with pytest.raises(PermissionError):
        ai_service.index_document("notes.txt", payload, uploaded_by=None)
    result = ai_service.index_document("notes.txt", payload, uploaded_by=teacher_a.id)
    doc_id = int(result.doc_id.split(":")[1])
    with pytest.raises(PermissionError):
        ai_service.remove_document(doc_id, teacher_b.id)
    assert ai_service.remove_document(doc_id, teacher_a.id)


def test_equal_upload_bytes_do_not_cross_owner_or_visibility_boundaries():
    teacher_a = create_user("teacher-duplicate-a", PW, "Teacher A", "teacher")
    teacher_b = create_user("teacher-duplicate-b", PW, "Teacher B", "teacher")
    payload = ("Duplicated private lecture marker with useful context. " * 8).encode()
    public = ai_service.index_document("shared.txt", payload, uploaded_by=teacher_a.id)
    private = ai_service.index_document("private.txt", payload, uploaded_by=teacher_b.id, visibility="private")
    again = ai_service.index_document("shared-again.txt", payload, uploaded_by=teacher_a.id)
    assert public.doc_id != private.doc_id
    assert again.doc_id == public.doc_id
    with session_scope() as session:
        rows = KnowledgeDocumentRepository(session).list_all()
        assert len(rows) == 2
        assert {(row.uploaded_by, row.visibility) for row in rows} == {
            (teacher_a.id, "public"), (teacher_b.id, "private")
        }
    hits = ai_service.get_rag().retrieve("duplicated private lecture marker", k=10,
                                         user_id=teacher_a.id, allowed_course_ids=set())
    assert {hit.doc_id for hit in hits} == {public.doc_id}


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


def test_deactivated_account_cannot_use_private_ai_or_course_services():
    student = create_user("disabled-student", PW, "Disabled Student")
    teacher = create_user("disabled-teacher", PW, "Disabled Teacher", "teacher")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="active-check", title="Active Check", owner_id=teacher.id))
        course_id = course.id
        UserRepository(session).get(student.id).is_active = False
        UserRepository(session).get(teacher.id).is_active = False
    with pytest.raises(PermissionError):
        ai_service.chat(student.id, "What is statistics?")
    with pytest.raises(PermissionError):
        ai_service.ask_tutor("What is statistics?", user_id=student.id)
    with pytest.raises(PermissionError):
        ai_service.get_history(student.id, "session")
    with pytest.raises(PermissionError):
        ai_service.clear_session(student.id, "session")
    with pytest.raises(PermissionError):
        course_service.enroll(student.id, course_id)
    with pytest.raises(PermissionError):
        course_service.list_courses(student.id)
    with pytest.raises(PermissionError):
        course_service.create_course(teacher.id, "Denied Course", "", ["statistics"])
    with pytest.raises(PermissionError):
        course_service.course_completion_report(course_id, teacher.id)
    with pytest.raises(PermissionError):
        ai_service.index_document("notes.txt", b"valid text", uploaded_by=teacher.id)


def test_lesson_progress_requires_enrollment_and_active_account():
    student = create_user("progress-student", PW, "Progress Student")
    with session_scope() as session:
        course = CourseRepository(session).add(Course(slug="progress-guard", title="Progress Guard"))
        lesson = LessonRepository(session).add(
            Lesson(course_id=course.id, topic_key="statistics", title="Statistics", order_index=1)
        )
        course_id, lesson_id = course.id, lesson.id
    with pytest.raises(PermissionError):
        course_service.update_lesson_progress(student.id, lesson_id, percent=100, completed=True)
    assert course_service.next_lesson(student.id, course_id) is None
    assert course_service.enroll(student.id, course_id)
    course_service.update_lesson_progress(student.id, lesson_id, percent=100, completed=True)
    assert course_service.get_course(course_id, student.id).completed_lessons == 1
    with session_scope() as session:
        UserRepository(session).get(student.id).is_active = False
    with pytest.raises(PermissionError):
        course_service.update_lesson_progress(student.id, lesson_id, percent=50)


def test_deactivated_accounts_cannot_write_learning_data_or_administer_users():
    student = create_user("inactive-learning", PW, "Inactive Learning")
    teacher = create_user("inactive-resetter", PW, "Inactive Resetter", "teacher")
    admin = create_user("inactive-admin", PW, "Inactive Admin", "admin")
    learning_service.record_quiz_attempt(student.id, "statistics", 3, 5)
    plan = recommendation_service.get_plan(student.id)
    with session_scope() as session:
        users = UserRepository(session)
        for user_id in (student.id, teacher.id, admin.id):
            users.get(user_id).is_active = False
    with pytest.raises(PermissionError):
        learning_service.record_quiz_attempt(student.id, "statistics", 5, 5)
    with pytest.raises(PermissionError):
        learning_service.get_dashboard(student.id)
    with pytest.raises(PermissionError):
        learning_service.get_profile(student.id)
    with pytest.raises(PermissionError):
        recommendation_service.mark_step(student.id, plan.steps[0].id, "done")
    assert not issue_reset_code(teacher.id, student.username)[0]
    assert not user_service.set_active(admin.id, student.username, True)[0]
