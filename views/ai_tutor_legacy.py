"""Original "Ask Preluma AI" page (kept for its persona and depth controls)."""

from __future__ import annotations

import re

import streamlit as st

from components.ui_components import page_intro
from engine import build_pack
from engine import tutor_sections
from services.ai_service import active_provider as _provider
from services.ai_service import available_providers
from services.ai_service import llm_available
from services.ai_service import llm_tutor
from services.ai_service import detect_topic_from_question

# Words that are not real questions and need a follow-up prompt instead of a topic answer
_GREETINGS = {"hi", "hello", "hey", "yo", "hiya", "sup", "ok", "okay", "sure",
               "test", "testing", "good", "nice", "great", "thanks", "thank you",
               "bye", "goodbye", "lol", "haha", "hmm", "yes", "no", "yeah"}


_VAGUE_WORDS = {"help", "explain", "tell me", "more", "details",
                "why", "how", "this", "it", "i do not understand"}


# Short phrases that are essentially greetings + requests for help with no topic
_HELP_PHRASES = {
    "i need help", "need help", "please help", "help me", "help please",
    "can you help", "can u help", "i need help please", "please help me",
    "hi i need help", "hello i need help", "hey i need help",
    "hi help me", "hello help me", "hey help me",
    "hi can you help", "hello can you help",
}


def _question_needs_clarification(question: str) -> bool:
    # Return True when the input is too vague to answer meaningfully.
    text = " ".join(str(question).strip().split())
    if not text:
        return True
    cleaned = re.sub(r"[^\w\s]", " ", text.casefold())
    cleaned = " ".join(cleaned.split())
    # Exact greeting word
    if cleaned in _GREETINGS:
        return True
    # Exact vague phrase
    if cleaned in _VAGUE_WORDS:
        return True
    # Known help-only phrases with no real topic
    if cleaned in _HELP_PHRASES:
        return True
    # Starts with a greeting then has only vague words (e.g. "hi i need help please")
    words = cleaned.split()
    if words and words[0] in _GREETINGS:
        rest_words = set(words[1:])
        all_vague = rest_words <= (_GREETINGS | _VAGUE_WORDS | {"i", "a", "me", "please", "u", "need", "some"})
        if all_vague:
            return True
    # Very short input with no academic content (3 words or fewer, none academic)
    if len(words) <= 3 and not any(len(w) > 6 for w in words):
        return True
    return False


def _natural_answer_text(response: dict, depth: str, persona: str = "Normal Mode") -> str:
    direct = str(response.get("tiny_answer", "")).strip()
    simple = str(response.get("explain_simply", "")).strip()
    example = str(response.get("real_life_example", "")).strip()
    mistake = str(response.get("common_mistake", "")).strip()
    exam = str(response.get("exam_angle", "")).strip()

    # For Roast/Coach: explain_simply carries the persona tone -- lead with it
    if persona in ("Roast Mode", "Coach Mode"):
        if depth == "Short":
            pieces = [simple, direct] if simple else [direct]
        elif depth == "Deep":
            pieces = [
                simple,
                f"To make this concrete: {example}" if example else "",
                f"Watch out: {mistake}" if mistake else "",
                f"For exams: {exam}" if exam else "",
            ]
        else:
            pieces = [
                simple,
                f"For example, {example}" if example else "",
            ]
    else:
        # Normal Mode: structured order
        if depth == "Short":
            pieces = [direct, simple]
        elif depth == "Deep":
            pieces = [
                direct,
                simple,
                f"To make this concrete, consider this example: {example}" if example else "",
                f"One important misunderstanding to avoid is the following: {mistake}" if mistake else "",
                f"For an exam or viva, the strongest way to remember the idea is: {exam}" if exam else "",
            ]
        else:
            pieces = [
                direct,
                simple,
                f"For example, {example}" if example else "",
            ]

    paragraphs = []
    for piece in pieces:
        piece = " ".join(str(piece).split())
        if piece:
            paragraphs.append(piece)
    return "\n\n".join(paragraphs)


def _clear_ai_chat() -> None:
    st.session_state.tutor_history = []
    st.session_state.ai_context_note = ""
    st.session_state["_ai_input_key"] = st.session_state.get("_ai_input_key", 0) + 1


def ask_preluma_ai_page():
    page_intro(
        "ai",
        "Adaptive academic tutor",
        "Ask Preluma AI",
        "Ask naturally. Preluma detects the topic, understands the learning goal, and adjusts the depth and teaching style.",
    )

    # No key notice
    if not llm_available():
        st.markdown(
            "<div style='background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.28);"
            "border-radius:16px;padding:14px 18px;margin-bottom:18px;'>"
            "<div style='font-size:11px;font-weight:800;color:#f59e0b;letter-spacing:.08em;"
            "text-transform:uppercase;margin-bottom:7px;'>Real AI -- One-time Setup Needed</div>"
            "<div style='font-size:13px;color:#94a3b8;line-height:1.7;'>"
            "To enable <b style='color:#e2e8f0;'>Gemini / ChatGPT / Claude</b> real answers:<br>"
            "1. Go to <b style='color:#38bdf8;'>Streamlit Cloud → Manage App → Settings → Secrets</b><br>"
            "2. Add: <code style='color:#34d399;background:rgba(52,211,153,.08);"
            "padding:2px 6px;border-radius:4px;'>GEMINI_API_KEY = &quot;your-key-here&quot;</code><br>"
            "3. Or use <code style='color:#34d399;background:rgba(52,211,153,.08);"
            "padding:2px 6px;border-radius:4px;'>OPENAI_API_KEY</code> for ChatGPT<br>"
            "<span style='color:#64748b;font-size:12px;'>Until then, Preluma uses curated Wikipedia-based answers -- still accurate, just not live AI.</span>"
            "</div></div>",
            unsafe_allow_html=True,
        )

    providers = available_providers()
    provider_label = _provider()
    use_context = False  # always open topic
    mission_topic = st.session_state.get("topic", "General learning")

    col_style, col_depth = st.columns(2)
    with col_style:
        mode = st.selectbox("Teaching style", ["Auto-detect", "Explain like I am 5", "Friendly Tutor", "Step-by-Step", "Exam/Viva Answer", "Give More Examples"])
    with col_depth:
        depth = st.selectbox("Answer depth", ["Balanced", "Short", "Deep"])

    st.markdown(
        f"<span class='context-chip'>Ask anything -- any topic</span>"
        f"<span class='context-chip'>Provider: {provider_label}</span>"
        f"<span class='context-chip'>Fallbacks ready: {len(providers)}</span>",
        unsafe_allow_html=True,
    )

    _input_key = f"_ai_draft_{st.session_state.get('_ai_input_key', 0)}"
    question = st.text_area(
        "Your question",
        key=_input_key,
        placeholder="Ask naturally, for example: I do not understand machine learning. First explain the basic idea, then tell me how it learns from data.",
        height=130,
    )

    ask_col, clear_col = st.columns([5, 1])
    ask = ask_col.button("Ask Preluma AI", use_container_width=True)
    clear_col.button("Clear", use_container_width=True, on_click=_clear_ai_chat)

    if ask and question.strip():
        detected_topic = detect_topic_from_question(question, mission_topic if use_context else "General learning")
        if _question_needs_clarification(question):
            raw = question.strip().casefold().strip(" ?.,!")
            provider_name = _provider() or "AI"
            # Pure greeting -- respond warmly like any real AI assistant
            if raw in _GREETINGS or (raw.split()[0] in _GREETINGS if raw.split() else False):
                reply = (
                    f"Hello! I am Preluma AI, powered by {provider_name}. "
                    f"How can I help you today? "
                    f"You can ask me anything -- any topic, any concept, any question. "
                    f"Just type what you want to understand."
                )
            else:
                # Vague input with no specific topic -- ask for one more detail
                reply = (
                    f"I am ready to help. Just tell me what topic or concept you want to understand "
                    f"and I will give you a clear, direct answer powered by {provider_name}."
                )
            st.session_state.tutor_history.append({
                "question": question.strip(),
                "topic": "General",
                "clarification": True,
                "answer_text": reply,
                "source": f"Preluma ({provider_name})",
            })
            st.session_state["_ai_input_key"] = st.session_state.get("_ai_input_key", 0) + 1
            st.rerun()
        else:
            style_prefix = {
                "Auto-detect": "Follow the user's wording and automatically match the requested teaching style. ",
                "Explain like I am 5": "Explain like I am 5 years old using a safe and memorable analogy. ",
                "Friendly Tutor": "Explain as a patient, natural, friendly tutor. ",
                "Step-by-Step": "Explain step by step and connect cause and effect. ",
                "Exam/Viva Answer": "Give an exam-ready and viva-ready answer. ",
                "Give More Examples": "Teach through multiple clear real-life examples. ",
            }[mode]
            depth_prefix = {
                "Short": "Answer briefly and directly. ",
                "Balanced": "Give a natural balanced explanation in connected paragraphs. ",
                "Deep": "Give a deep, accurate, mechanism-focused explanation in coherent paragraphs. Explain why and how, not only what. ",
            }[depth]
            routed_question = style_prefix + depth_prefix + question.strip()
            with st.spinner(f"Preluma AI is understanding your question about {detected_topic}..."):
                response = llm_tutor(detected_topic, routed_question, st.session_state.get("persona", "Normal Mode")) if llm_available() else None
                # Label the answer source so the student knows which AI answered
                if response:
                    source = f"{_provider()} AI"
                elif llm_available():
                    source = "Preluma Smart Answer"
                    err = st.session_state.pop("_llm_last_error", "")
                    if err:
                        st.warning(f"AI connection issue: {err}. Showing smart offline answer.", icon=None)
                else:
                    source = "Preluma Smart Answer"
                if response is None:
                    fallback_pack = build_pack(detected_topic, use_wikipedia=True)
                    response = tutor_sections(fallback_pack, routed_question, st.session_state.get("persona", "Normal Mode"))
            try:
                response["concept"] = detected_topic
                current_persona = "Normal Mode"
                answer_text = _natural_answer_text(response, depth, current_persona)
                st.session_state.tutor_history.append({"question":question.strip(),"topic":detected_topic,"response":response,"answer_text":answer_text,"source":source,"depth":depth,"persona":current_persona})
                st.session_state["_ai_draft"] = ""
                st.rerun()
            except Exception as _e:
                st.error(f"Could not format answer. Please try again. ({type(_e).__name__})")

    st.markdown("""
    <style>
    /* Premium chat shell */
    .ai-chat-shell {
        margin-top:24px;
        display:flex; flex-direction:column; gap:0;
    }
    /* User bubble -- right side */
    .chat-user {
        background:linear-gradient(135deg,rgba(56,189,248,.16),rgba(99,102,241,.12));
        border:1px solid rgba(56,189,248,.28); border-radius:20px 20px 4px 20px;
        padding:12px 18px; margin:0 0 4px auto;
        font-size:14px; color:#e2e8f0; line-height:1.55;
        max-width:72%; text-align:left;
        box-shadow:0 2px 12px rgba(56,189,248,.10);
    }
    /* AI meta label */
    .ai-meta {
        font-size:10px; color:#334155; margin:0 0 4px 4px;
        font-weight:700; letter-spacing:.06em; text-transform:uppercase;
    }
    /* AI bubble -- left side */
    .ai-main-answer {
        background:linear-gradient(145deg,rgba(15,23,42,.96),rgba(8,14,30,.98));
        border:1px solid rgba(255,255,255,.08); border-radius:4px 20px 20px 20px;
        padding:16px 20px; margin:0 auto 20px 0;
        font-size:14px; color:#cbd5e1; line-height:1.78;
        max-width:85%;
        box-shadow:0 4px 20px rgba(0,0,0,.30);
    }
    /* Quick prompt pills */
    .quick-pills { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 14px; }
    </style>
    """, unsafe_allow_html=True)
    history = st.session_state.get("tutor_history", [])[-8:]
    if history:
        st.markdown("<div class='ai-chat-shell'>", unsafe_allow_html=True)
        for index, item in enumerate(reversed(history)):
            # User bubble -- right aligned
            st.markdown(
                f"<div class='chat-user'>{item['question']}</div>",
                unsafe_allow_html=True,
            )
            # AI label + bubble
            topic_lbl = item.get("topic", "AI")
            src_lbl   = item.get("source", "Preluma AI")
            persona_lbl = item.get("persona", "Normal Mode")
            persona_colors = {"Normal Mode": "#38bdf8", "Coach Mode": "#34d399", "Roast Mode": "#fb923c"}
            p_color = persona_colors.get(persona_lbl, "#64748b")
            st.markdown(
                f"<div class='ai-meta'>{topic_lbl} &nbsp;·&nbsp; {src_lbl} &nbsp;·&nbsp; <span style='color:{p_color};'>{persona_lbl}</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='ai-main-answer'>{item.get('answer_text','')}</div>",
                unsafe_allow_html=True,
            )
            # Study support expander (only for real AI answers)
            if not item.get("clarification"):
                response = item.get("response", {})
                has_extra = any([
                    response.get("common_mistake"),
                    response.get("exam_angle"),
                    response.get("real_life_example"),
                ])
                if has_extra:
                    with st.expander("Study support -- mistake, exam line, example"):
                        if response.get("common_mistake"):
                            st.markdown(f"**Common mistake:** {response['common_mistake']}")
                        if response.get("exam_angle"):
                            st.markdown(f"**Exam line:** {response['exam_angle']}")
                        if response.get("real_life_example"):
                            st.markdown(f"**Example:** {response['real_life_example']}")
        st.markdown("</div>", unsafe_allow_html=True)
