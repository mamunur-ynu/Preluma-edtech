"""AI layer: provider failover (fake transport), RAG retrieval, memory, tutor service."""

import pytest

from ai.documents import DocumentError, SourceDocument, chunk_text, extract_text, pack_to_documents
from ai.embeddings import HashingEmbedder
from ai.llm_router import PROVIDERS, LLMRouter
from ai.memory import ConversationMemory
from ai.rag_engine import RAGEngine
from auth import create_user
from core.topics import TOPICS
from services import ai_service


def _ok(text):
    return lambda url, headers, body, timeout: {"choices": [{"message": {"content": text}}]}


# ── LLM router ───────────────────────────────────────────────────────────────
def test_router_is_unavailable_without_keys():
    router = LLMRouter(PROVIDERS, transport=_ok("hi"))
    assert not router.is_available() and router.active_label() == "Curated fallback"
    assert router.complete("sys", "hello").text == ""


def test_router_fails_over_to_the_next_provider(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k2")
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(url)
        if "groq" in url:
            raise ConnectionError("down")
        return {"choices": [{"message": {"content": "from openrouter"}}]}

    router = LLMRouter(PROVIDERS, transport=transport)
    result = router.complete("sys", "hello")
    assert result.ok and result.text == "from openrouter" and result.provider == "OpenRouter"
    assert "Groq" in router.last_error and len(calls) == 2


def test_router_never_leaks_api_keys_in_errors(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-key")

    def boom(*_):
        raise RuntimeError("super-secret-key was rejected")

    router = LLMRouter(PROVIDERS, transport=boom)
    router.complete("s", "u")
    assert "super-secret-key" not in router.last_error


def test_anthropic_wire_format(monkeypatch):
    for name in ("GROQ_API_KEY",):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    seen = {}

    def transport(url, headers, body, timeout):
        seen.update(headers=headers, body=body)
        return {"content": [{"type": "text", "text": "claude says hi"}]}

    result = LLMRouter(PROVIDERS, transport=transport).complete("be nice", "hello")
    assert result.text == "claude says hi" and seen["headers"]["x-api-key"] == "ak"
    assert seen["body"]["system"] == "be nice"


# ── chunking + embeddings + RAG ──────────────────────────────────────────────
def test_chunking_respects_size_and_covers_the_text():
    text = " ".join(f"Sentence number {i} talks about neural networks." for i in range(200))
    chunks = chunk_text(text, max_chars=400, overlap=50)
    assert len(chunks) > 5 and all(len(c) <= 450 for c in chunks)
    assert chunks[0].startswith("Sentence number 0") and "199" in chunks[-1]
    assert chunk_text("   ") == []


def test_hashing_embedder_is_deterministic_and_normalised():
    embedder = HashingEmbedder()
    a, b = embedder.embed(["gradient descent"])[0], embedder.embed(["gradient descent"])[0]
    assert a == b and abs(sum(x * x for x in a) - 1.0) < 1e-6


@pytest.fixture()
def rag():
    engine = RAGEngine(embedder=HashingEmbedder())
    engine.index_missing(pack_to_documents(TOPICS))
    return engine


def test_rag_retrieves_the_right_topic(rag):
    hits = rag.retrieve("what is overfitting in machine learning", k=3)
    assert hits and "machine learning" in " ".join(h.title.lower() + h.text.lower() for h in hits)
    assert hits[0].rank == 1 and hits[0].score >= hits[-1].score
    assert rag.retrieve("") == []


def test_rag_topic_filter_and_unknown_query(rag):
    hits = rag.retrieve("neural network layers weights", k=4, topic="neural network")
    assert hits and all(h.doc_id == "topic:neural network" for h in hits)
    assert rag.retrieve("zzzxqj qqwwee", k=3) == []


def test_uploaded_documents_are_indexed_and_removable(rag):
    doc = SourceDocument("doc:1", "Course notes", "The flux capacitor stabilises the quantum banana. " * 5, "notes.txt")
    assert rag.index_document(doc) > 0
    assert rag.retrieve("flux capacitor", k=1)[0].doc_id == "doc:1"
    rag.delete_document("doc:1")
    assert all(h.doc_id != "doc:1" for h in rag.retrieve("flux capacitor", k=3))


def test_extractive_answer_cites_sources(rag):
    hits = rag.retrieve("what is a neural network", k=3)
    answer = RAGEngine.extractive_answer("what is a neural network", hits)
    assert answer and "[1]" in answer


def test_index_persists_to_disk(tmp_path):
    path = tmp_path / "index.json"
    first = RAGEngine(embedder=HashingEmbedder(), index_path=path, vector_backend="memory")
    first.index_document(SourceDocument("d", "Doc", "Persistent knowledge about databases and indexes. " * 4, "d.txt"))
    second = RAGEngine(embedder=HashingEmbedder(), index_path=path, vector_backend="memory")
    assert second.store.count() == first.store.count() > 0


def test_unsupported_and_oversized_uploads_are_rejected():
    with pytest.raises(DocumentError):
        extract_text("virus.exe", b"MZ")
    with pytest.raises(DocumentError):
        extract_text("big.txt", b"x" * (50 * 1024 * 1024))
    assert extract_text("a.txt", "héllo".encode()) == "héllo"


# ── memory ───────────────────────────────────────────────────────────────────
def test_memory_keeps_recent_turns_and_summarises_older_ones():
    history = []
    for i in range(10):
        history += [{"role": "user", "content": f"Question {i}?"}, {"role": "assistant", "content": f"Answer {i}"}]
    view = ConversationMemory(max_recent_messages=4).build(history)
    assert len(view.recent) <= 4 and view.recent[0]["role"] == "user"
    assert "Question 7" in view.summary and "Question 9" not in view.summary      # newest turns stay verbatim
    assert "Question 0" not in view.summary                                        # summary is capped, not unbounded


# ── tutor service ────────────────────────────────────────────────────────────
@pytest.fixture()
def indexed_service():
    ai_service.set_rag(RAGEngine(embedder=HashingEmbedder()))
    ai_service.get_rag().index_missing(pack_to_documents(TOPICS))


def test_offline_tutor_is_grounded_and_flagged(indexed_service):
    reply = ai_service.ask_tutor("Explain overfitting in machine learning")
    assert reply.offline and reply.grounded and reply.sources
    assert reply.topic.lower() == "machine learning" and reply.sections["tiny_answer"]


def test_tutor_with_llm_uses_retrieved_context(indexed_service, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    prompts = []

    def transport(url, headers, body, timeout):
        prompts.append(body["messages"][0]["content"])
        return {"choices": [{"message": {"content": '{"concept":"c","tiny_answer":"t","explain_simply":"e",'
                                                    '"real_life_example":"r","common_mistake":"m","exam_angle":"x"}'}}]}

    ai_service.set_router(LLMRouter(PROVIDERS, transport=transport))
    reply = ai_service.ask_tutor("What is a neural network?")
    assert not reply.offline and reply.provider == "Groq" and reply.sections["tiny_answer"] == "t"
    assert "[1]" in prompts[0]                                  # retrieved passages were put in the prompt


def test_chat_saves_history_and_clears(indexed_service):
    user = create_user("nora", "Passw0rd!xyz", "Nora")
    first = ai_service.chat(user.id, "What is a database index?")
    ai_service.chat(user.id, "And why do joins matter?", session_id=first.session_id)
    history = ai_service.get_history(user.id, first.session_id)
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]
    assert ai_service.clear_session(user.id, first.session_id) == 4
    assert ai_service.get_history(user.id, first.session_id) == []


def test_empty_or_oversized_questions(indexed_service):
    with pytest.raises(ValueError):
        ai_service.ask_tutor("   ")
    reply = ai_service.ask_tutor("explain statistics " + "x" * 5000)
    assert reply.sections                                       # truncated, not crashed


def test_knowledge_base_upload_roundtrip(indexed_service):
    teacher = create_user("olga", "Passw0rd!xyz", "Olga", "teacher")
    result = ai_service.index_document("notes.txt", ("Zebra crossing protocol: always look left twice. " * 10).encode(),
                                       uploaded_by=teacher.id)
    assert result.chunks > 0 and ai_service.list_documents(teacher.id)[0]["title"] == "notes"
    assert ai_service.get_rag().retrieve("zebra crossing protocol", k=1)[0].doc_id == result.doc_id
    assert ai_service.remove_document(int(result.doc_id.split(":")[1]), teacher.id)
    assert ai_service.list_documents(teacher.id) == []
    with pytest.raises(DocumentError):
        ai_service.index_document("empty.txt", b"   ")
