"""
services/ai_service.py — the AI tutor as a set of use cases.

Pipeline for a student question::

    question ─► detect topic + style ─► RAG retrieve (course material) ─► prompt + memory
                                                                              │
                      LLM router (8 providers, failover) ◄────────────────────┘
                              │ all providers down / no key?
                              ▼
                 offline answer from retrieved passages + curated topic pack

The UI (or a REST endpoint) never talks to providers, the vector store or the database
directly — only to the functions below.
"""

from __future__ import annotations

import json
import hashlib
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from cryptography.fernet import InvalidToken

from ai import prompts
from ai.documents import DocumentError, SourceDocument, extract_text, pack_to_documents
from ai.llm_router import LLMRouter, get_router
from ai.memory import ConversationMemory
from ai.rag_engine import RAGEngine, RetrievedChunk
from auth.validation import sanitize_text
from config import get_settings
from core.content_pack import tutor_sections
from core.topics import TOPICS
from database.connection import session_scope
from database.models import AIConversationMessage, KnowledgeDocument, utcnow
from database.repository import (
    ConversationRepository,
    CourseRepository,
    EnrollmentRepository,
    KnowledgeDocumentRepository,
    UserRepository,
)
from services._common import topic_key
from services._access import require_active_user
from security.rate_limit import DatabaseRateLimiter, InProcessRateLimiter, shared_limits_enabled
from security.document_crypto import decrypt_source, encrypt_source

logger = logging.getLogger("preluma.ai")

MAX_QUESTION_CHARS = 1000
detect_topic_from_question = prompts.detect_topic_from_question

_router: LLMRouter | None = None
_rag: RAGEngine | None = None
_rag_lock = threading.Lock()
_ai_limiter = InProcessRateLimiter(get_settings().ai_requests_per_minute, 60)


def _check_ai_limit(user_id: int | None) -> None:
    key = f"ai:{user_id if user_id is not None else 'anonymous'}"
    if shared_limits_enabled():
        DatabaseRateLimiter(get_settings().ai_requests_per_minute, 60).check(key)
    else:
        _ai_limiter.check(key)


def reset_rate_limits() -> None:
    """Clear in-process AI counters (test/support hook; no user data)."""
    _ai_limiter.reset()


# ── wiring ───────────────────────────────────────────────────────────────────
def router() -> LLMRouter:
    return _router or get_router()


def set_router(custom: LLMRouter | None) -> None:
    """Inject a router (tests use a fake transport)."""
    global _router
    _router = custom


def get_rag() -> RAGEngine:
    """Process-wide RAG engine; the curated topic library is indexed on first use."""
    global _rag
    with _rag_lock:
        if _rag is None:
            settings = get_settings()
            engine = RAGEngine(
                index_path=Path(settings.data_dir) / "vector_index.json",
                embedder_preference=settings.embedding_backend,
                vector_backend=settings.vector_backend,
            )
            engine.index_missing(pack_to_documents(TOPICS))
            reconcile_document_index(engine)
            _rag = engine
        return _rag


def set_rag(engine: RAGEngine | None) -> None:
    """Inject an engine (tests)."""
    global _rag
    with _rag_lock:
        _rag = engine


def reconcile_document_index(engine: RAGEngine) -> dict[str, int]:
    """Fail closed after interrupted uploads/deletes; restore trusted encrypted text.

    The database is authoritative for uploaded-document ownership. An index entry
    without matching metadata is removed. Recoverable rows are reindexed from
    authenticated encrypted source; legacy rows remain at zero until re-upload.
    """
    removed = missing = repaired = recovered = 0

    def restore(row: KnowledgeDocument, doc_id: str) -> bool:
        nonlocal recovered
        if not row.source_ciphertext:
            return False
        try:
            text = decrypt_source(row.source_ciphertext, row.content_sha256)
            metadata = {"course_id": row.course_id, "uploaded_by": row.uploaded_by,
                        "visibility": row.visibility, "content_sha256": row.content_sha256}
            chunks = engine.index_document(SourceDocument(doc_id, row.title, text, row.source, metadata))
            if not chunks:
                return False
        except (InvalidToken, ValueError, UnicodeError, RuntimeError, OSError):
            logger.exception("Could not restore encrypted document %s", doc_id)
            return False
        row.n_chunks = chunks
        recovered += 1
        return True

    with session_scope() as s:
        records = {f"doc:{row.id}": row for row in KnowledgeDocumentRepository(s).list_all()}
        for doc_id, count in engine.store.documents().items():
            if not doc_id.startswith("doc:"):
                continue
            row = records.get(doc_id)
            metadata = engine.store.document_metadata(doc_id) or {}
            expected = ({"course_id": row.course_id, "uploaded_by": row.uploaded_by,
                         "visibility": row.visibility, "content_sha256": row.content_sha256}
                        if row is not None else None)
            if row is None or any(metadata.get(key) != value for key, value in expected.items()) or (
                row.n_chunks > 0 and row.n_chunks != count
            ):
                engine.delete_document(doc_id)
                removed += 1
                if row is not None:
                    row.n_chunks = 0
                    restore(row, doc_id)
                continue
            if row.n_chunks != count:
                row.n_chunks = count
                repaired += 1
        for doc_id, row in records.items():
            if not engine.store.has_document(doc_id):
                row.n_chunks = 0
                if not restore(row, doc_id):
                    missing += 1
    if removed or missing or repaired or recovered:
        logger.warning("Reconciled document index: removed=%d missing=%d repaired=%d recovered=%d",
                       removed, missing, repaired, recovered)
    return {"removed": removed, "missing": missing, "repaired": repaired, "recovered": recovered}


# ── provider status (replaces the old llm.py helpers) ────────────────────────
def llm_available() -> bool:
    return router().is_available()


def available_providers() -> list[str]:
    return router().available_labels()


def active_provider() -> str:
    return router().active_label()


def last_error() -> str:
    return router().last_error


def complete_text(system: str, user: str) -> str:
    """Plain text completion ("" when no provider answered)."""
    return router().complete(system, user).text


# ── structured tutor (JSON answer) ───────────────────────────────────────────
def _fallback_sections(topic: str, raw: str) -> dict:
    return {"concept": topic, "tiny_answer": raw[:300], "explain_simply": "", "real_life_example": "",
            "common_mistake": "", "exam_angle": ""}


def llm_tutor(topic: str, question: str, style: str = "Normal Mode", context: str = "") -> dict | None:
    """Ask the LLM for the six-field tutor answer.  ``None`` if no provider answered."""
    question_style = prompts.detect_question_style(question)
    result = router().complete(
        prompts.tutor_system_prompt(question_style, style, context), prompts.tutor_user_prompt(topic, question)
    )
    if not result.ok:
        return None
    parsed = prompts.parse_json_object(result.text)
    if parsed and prompts.TUTOR_KEYS.issubset(parsed.keys()):
        return parsed
    return _fallback_sections(topic, result.text)


def generate_brain_brief(topic: str, definition: str, concepts: list) -> dict | None:
    result = router().complete(prompts.BRAIN_BRIEF_SYSTEM, prompts.brain_brief_user_prompt(topic, definition, concepts))
    if not result.ok:
        return None
    parsed = prompts.parse_json_object(result.text)
    return parsed if parsed and prompts.BRAIN_BRIEF_KEYS.issubset(parsed.keys()) else None


def generate_class_questions(topic: str, definition: str, concepts: list) -> list | None:
    result = router().complete(
        prompts.CLASS_QUESTIONS_SYSTEM, prompts.class_questions_user_prompt(topic, definition, concepts)
    )
    if not result.ok:
        return None
    cleaned = result.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        items = json.loads(cleaned)
        if isinstance(items, list) and len(items) >= 3:
            return [str(q) for q in items[:5]]
    except ValueError:
        pass
    return None


def free_chat(question: str, provider_name: str = "AI") -> str:
    """Stateless one-shot chat (legacy behaviour)."""
    return router().complete(prompts.free_chat_system(provider_name), question).text.strip()


def homework_tutor_intro(topic: str, weak_concepts: list, score_pct: float) -> str:
    result = router().complete(prompts.HW_INTRO_SYSTEM, prompts.hw_intro_user_prompt(topic, weak_concepts, score_pct))
    return result.text.strip() if result.ok else prompts.hw_intro_fallback(topic, weak_concepts, score_pct)


def homework_tutor_reply(topic: str, weak_concepts: list, history: list, question: str) -> str:
    result = router().complete(prompts.hw_reply_system(topic, weak_concepts), prompts.hw_reply_user_prompt(history, question))
    return result.text.strip() if result.ok else "That's a great question! Let me help you think through it step by step."


# ── RAG-grounded tutoring with memory ────────────────────────────────────────
@dataclass
class TutorReply:
    topic: str
    question_style: str
    sections: dict
    sources: list[RetrievedChunk] = field(default_factory=list)
    provider: str = ""
    grounded: bool = False          # answer used retrieved course material
    offline: bool = False           # no LLM answered; built from material + curated pack
    session_id: str = ""


def new_session_id() -> str:
    return str(uuid.uuid4())


def _retrieval_scope(user_id: int | None) -> tuple[set[int] | None, bool]:
    if user_id is None:
        return set(), False
    with session_scope() as s:
        user = UserRepository(s).get(user_id)
        if user is None:
            return set(), False
        if user.role in ("teacher", "admin"):
            return {course.id for course in CourseRepository(s).list_published()}, True
        return set(EnrollmentRepository(s).course_ids_for_user(user_id)), False


def _retrieve(question: str, topic: str, k: int, user_id: int | None = None) -> list[RetrievedChunk]:
    rag = get_rag()
    key = topic_key(topic)
    course_ids, include_staff = _retrieval_scope(user_id)
    kwargs = {
        "user_id": user_id,
        "allowed_course_ids": course_ids,
        "include_staff": include_staff,
    }
    chunks = rag.retrieve(question, k=k, topic=key if key in TOPICS else None, **kwargs) if key in TOPICS else []
    return chunks or rag.retrieve(question, k=k, **kwargs)


def _save_exchange(user_id: int, session_id: str, topic: str, style: str, question: str, answer: str,
                   sources: list[RetrievedChunk]) -> None:
    payload = json.dumps([{"rank": c.rank, "title": c.title, "source": c.source} for c in sources])
    with session_scope() as s:
        repo = ConversationRepository(s)
        repo.purge_older_than(
            user_id,
            utcnow() - timedelta(days=get_settings().conversation_retention_days),
        )
        repo.add(AIConversationMessage(user_id=user_id, session_id=session_id, role="user", content=question,
                                       topic=topic_key(topic)[:80], question_style=style))
        repo.add(AIConversationMessage(user_id=user_id, session_id=session_id, role="assistant", content=answer[:8000],
                                       topic=topic_key(topic)[:80], sources_json=payload))


def ask_tutor(
    question: str,
    *,
    topic: str | None = None,
    persona: str = "Normal Mode",
    user_id: int | None = None,
    session_id: str | None = None,
    k: int = 4,
) -> TutorReply:
    """Answer a question with the structured tutor, grounded in retrieved course material."""
    if user_id is not None:
        with session_scope() as s:
            require_active_user(s, user_id)
    _check_ai_limit(user_id)
    question = sanitize_text(question, MAX_QUESTION_CHARS)
    if not question:
        raise ValueError("Please type a question.")
    detected = prompts.detect_topic_from_question(question, topic or "General learning")
    style = prompts.detect_question_style(question)
    session_id = session_id or new_session_id()

    sources = _retrieve(question, detected, k, user_id)
    context = RAGEngine.build_context(sources)
    sections = llm_tutor(detected, question, persona, context)
    provider, offline = "", False
    if sections is not None:
        provider = router().last_provider
    else:
        offline = True
        from services.content_service import build_pack

        sections = tutor_sections(build_pack(detected, use_wikipedia=False), question)
        extract = RAGEngine.extractive_answer(question, sources)
        if extract:
            sections = {**sections, "explain_simply": extract + " " + str(sections.get("explain_simply", "")).strip()}

    reply = TutorReply(
        topic=detected, question_style=style, sections=sections, sources=sources, provider=provider,
        grounded=bool(sources), offline=offline, session_id=session_id,
    )
    if user_id is not None:
        answer = " ".join(str(sections.get(key, "")) for key in ("tiny_answer", "explain_simply")).strip()
        try:
            _save_exchange(user_id, session_id, detected, style, question, answer, sources)
        except Exception:                      # history is a convenience; never break the answer
            logger.exception("Could not save the conversation")
    return reply


@dataclass
class ChatReply:
    text: str
    sources: list[RetrievedChunk]
    provider: str
    offline: bool
    session_id: str


def chat(user_id: int, message: str, *, session_id: str | None = None, topic: str | None = None) -> ChatReply:
    """Free conversation with memory (last turns verbatim + summary of older ones)."""
    with session_scope() as s:
        require_active_user(s, user_id)
    _check_ai_limit(user_id)
    message = sanitize_text(message, MAX_QUESTION_CHARS)
    if not message:
        raise ValueError("Please type a message.")
    session_id = session_id or new_session_id()
    memory = ConversationMemory()
    with session_scope() as s:
        history = [{"role": m.role, "content": m.content}
                   for m in ConversationRepository(s).history(user_id, session_id, limit=40)]
    view = memory.build(history)

    detected = prompts.detect_topic_from_question(message, topic or "General learning")
    sources = _retrieve(message, detected, 3, user_id)
    context = RAGEngine.build_context(sources, max_chars=2400)
    system = prompts.free_chat_system(active_provider(), context)
    if view.summary:
        system += "\n\n" + view.summary
    result = router().complete(system, message, history=view.recent)

    offline = not result.ok
    if result.ok:
        text = result.text.strip()
    else:
        text = RAGEngine.extractive_answer(message, sources) or (
            "I couldn't reach an AI model right now, and I didn't find that in the course material. "
            "Try rephrasing, or ask about one of the topics in the library."
        )
    style = prompts.detect_question_style(message)
    try:
        _save_exchange(user_id, session_id, detected, style, message, text, sources)
    except Exception:
        logger.exception("Could not save the conversation")
    return ChatReply(text, sources, result.provider, offline, session_id)


def get_history(user_id: int, session_id: str, limit: int = 40) -> list[dict[str, str]]:
    with session_scope() as s:
        require_active_user(s, user_id)
        return [{"role": m.role, "content": m.content, "sources": m.sources_json}
                for m in ConversationRepository(s).history(user_id, session_id, limit)]


def clear_session(user_id: int, session_id: str) -> int:
    with session_scope() as s:
        require_active_user(s, user_id)
        return ConversationRepository(s).delete_session(user_id, session_id)


# ── knowledge base management (teachers) ─────────────────────────────────────
@dataclass(frozen=True)
class IndexResult:
    doc_id: str
    title: str
    chunks: int


def index_document(filename: str, data: bytes, *, uploaded_by: int,
                   course_id: int | None = None, title: str | None = None,
                   visibility: str | None = None) -> IndexResult:
    """Extract, chunk, embed and store an uploaded file.  Raises :class:`DocumentError` on bad files."""
    selected_visibility = visibility or ("course" if course_id is not None else "public")
    if selected_visibility not in {"public", "course", "private", "staff"}:
        raise ValueError("Unknown document visibility.")
    with session_scope() as s:
        users, courses = UserRepository(s), CourseRepository(s)
        actor = users.get(uploaded_by) if isinstance(uploaded_by, int) else None
        if actor is None or not actor.is_active or actor.role not in ("teacher", "admin"):
            raise PermissionError("Only active teachers or administrators may index course documents.")
        if course_id is not None:
            course = courses.get(course_id)
            if course is None:
                raise LookupError("Course not found.")
            if actor.role != "admin" and course.owner_id not in (None, actor.id):
                raise PermissionError("You may only manage documents for your own course.")
    text = extract_text(filename, data)
    safe_name = sanitize_text(Path(filename).name, 160)
    doc_title = sanitize_text(title or Path(filename).stem, 160) or "Untitled"
    digest = hashlib.sha256(data).hexdigest()
    ciphertext = encrypt_source(text, digest)
    with session_scope() as s:
        docs = KnowledgeDocumentRepository(s)
        existing = docs.get_by_digest(digest, course_id, uploaded_by, selected_visibility)
        if existing is not None:
            existing.title = doc_title
            existing.source = safe_name
            existing.source_ciphertext = ciphertext
        row = existing or docs.add(
            KnowledgeDocument(
                title=doc_title,
                source=safe_name,
                course_id=course_id,
                uploaded_by=uploaded_by,
                visibility=selected_visibility,
                content_sha256=digest,
                source_ciphertext=ciphertext,
            )
        )
        doc_id, row_id = f"doc:{row.id}", row.id
    metadata = {
        "course_id": course_id,
        "uploaded_by": uploaded_by,
        "visibility": selected_visibility,
        "content_sha256": digest,
    }
    chunks = get_rag().index_document(SourceDocument(doc_id, doc_title, text, safe_name, metadata))
    if chunks == 0:
        with session_scope() as s:
            KnowledgeDocumentRepository(s).delete(row_id)
        raise DocumentError("The file contains no usable text.")
    with session_scope() as s:
        record = s.get(KnowledgeDocument, row_id)
        if record is not None:
            record.n_chunks = chunks
    return IndexResult(doc_id, doc_title, chunks)


def list_documents(actor_id: int) -> list[dict[str, object]]:
    with session_scope() as s:
        user = UserRepository(s).get(actor_id)
        if user is None or not user.is_active or user.role not in ("teacher", "admin"):
            raise PermissionError("Only teachers or administrators may list knowledge documents.")
        course_ids = {course.id for course in CourseRepository(s).list_published()}
        return [{"id": d.id, "title": d.title, "source": d.source, "chunks": d.n_chunks,
                 "uploaded": d.created_at.strftime("%Y-%m-%d"), "visibility": d.visibility,
                 "course_id": d.course_id}
                for d in KnowledgeDocumentRepository(s).list_for_actor(
                    actor_id, is_staff=True, course_ids=course_ids
                )]


def remove_document(document_id: int, actor_id: int) -> bool:
    with session_scope() as s:
        users, docs = UserRepository(s), KnowledgeDocumentRepository(s)
        actor, document = users.get(actor_id), docs.get(document_id)
        if actor is None or not actor.is_active or actor.role not in ("teacher", "admin"):
            raise PermissionError("Only teachers or administrators may remove knowledge documents.")
        if document is None:
            return False
        if actor.role != "admin" and document.uploaded_by != actor.id:
            raise PermissionError("You may only remove documents that you uploaded.")
        # Remove searchable content first. If DB deletion later fails, the
        # retained metadata points to an unavailable document (safe to retry).
        get_rag().delete_document(f"doc:{document_id}")
        return docs.delete(document_id)


def rag_stats() -> dict:
    return get_rag().stats()
