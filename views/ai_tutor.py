"""AI tutor: RAG-grounded chat with memory, sources and a teacher knowledge base."""

from __future__ import annotations

import json

import streamlit as st

from auth import esc
from components.ui_components import current_user_id, empty_state, page_intro, source_note
from services import ai_service
from services.ai_service import DocumentError


def ai_tutor_page() -> None:
    page_intro("ai", "AI TUTOR", "Ask Preluma",
               "Answers are grounded in the course library — every claim shows its source.")
    user_id = current_user_id()
    if user_id is None:
        empty_state("Please log in again to chat with the tutor.")
        return

    is_teacher = st.session_state.get("user_role") == "teacher"
    tabs = st.tabs(["Chat", "Knowledge base"] if is_teacher else ["Chat"])

    with tabs[0]:
        _chat(user_id)
    if is_teacher:
        with tabs[1]:
            _knowledge_base(user_id)


def _chat(user_id: int) -> None:
    session_id = st.session_state.setdefault("_chat_session", ai_service.new_session_id())
    st.caption("🟢 Live AI: " + ai_service.active_provider() if ai_service.llm_available()
               else "🟡 Offline mode — answers come straight from the course material (add an API key for full AI).")

    for message in ai_service.get_history(user_id, session_id):
        with st.chat_message("user" if message["role"] == "user" else "assistant"):
            st.markdown(esc(message["content"]).replace("\n", "  \n"))
            if message["role"] == "assistant" and message.get("sources"):
                _show_sources(message["sources"])

    prompt = st.chat_input("Ask about any topic in your courses…")
    if prompt:
        with st.spinner("Thinking…"):
            try:
                ai_service.chat(user_id, prompt, session_id=session_id)
            except ValueError as exc:
                st.warning(str(exc))
        st.rerun()

    if st.button("🗑 Start a new conversation", key="new_chat"):
        st.session_state["_chat_session"] = ai_service.new_session_id()
        st.rerun()


def _show_sources(raw: str) -> None:
    try:
        items = json.loads(raw)
    except (TypeError, ValueError):
        return
    if items:
        with st.expander(f"Sources ({len(items)})"):
            for item in items:
                st.markdown(source_note(item.get("rank", 0), item.get("title", ""), item.get("source", "")),
                            unsafe_allow_html=True)


def _knowledge_base(user_id: int) -> None:
    st.markdown("Upload notes, slides text or PDFs. They are chunked, embedded and become searchable "
                "for every student's tutor.")
    stats = ai_service.rag_stats()
    st.caption(f"Index: {stats['chunks']} passages · embedder: {stats['embedder']} · store: {stats['store']}")
    upload = st.file_uploader("Add a document", type=["txt", "md", "pdf"], key="kb_upload")
    if upload is not None and st.button("Index document", type="primary", key="kb_index"):
        try:
            result = ai_service.index_document(upload.name, upload.getvalue(), uploaded_by=user_id)
            st.success(f"Indexed “{result.title}” into {result.chunks} passages.")
        except DocumentError as exc:
            st.error(str(exc))
    docs = ai_service.list_documents(user_id)
    if docs:
        st.markdown("**Uploaded documents**")
        for doc in docs:
            a, b = st.columns([5, 1])
            a.markdown(f"{esc(doc['title'])} — {doc['chunks']} passages · {esc(doc['uploaded'])}")
            if b.button("Remove", key=f"kb_rm_{doc['id']}"):
                ai_service.remove_document(int(doc["id"]), user_id)
                st.rerun()
    else:
        st.caption("No uploaded documents yet — the built-in topic library is always searchable.")
