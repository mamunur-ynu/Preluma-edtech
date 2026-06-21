"""LLM integration for Preluma. Supports Gemini, OpenAI, Anthropic, Groq, OpenRouter, Together AI, and Cerebras.
Providers are tried in order. If one fails the next one takes over automatically."""

import os
import json
import requests

_OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"
_GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TOGETHER_URL   = "https://api.together.xyz/v1/chat/completions"
_CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
_MISTRAL_URL    = "https://api.mistral.ai/v1/chat/completions"

_OPENAI_MODEL     = os.environ.get("OPENAI_MODEL",     "gpt-4.1-mini")
_ANTHROPIC_MODEL  = os.environ.get("ANTHROPIC_MODEL",  "claude-sonnet-4-20250514")
_GROQ_MODEL       = os.environ.get("GROQ_MODEL",       "llama-3.3-70b-versatile")
_GEMINI_MODEL     = os.environ.get("GEMINI_MODEL",     "gemini-1.5-flash")
_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
_TOGETHER_MODEL   = os.environ.get("TOGETHER_MODEL",   "meta-llama/Llama-3.3-70B-Instruct-Turbo")
_CEREBRAS_MODEL   = os.environ.get("CEREBRAS_MODEL",   "llama-3.3-70b")
_MISTRAL_MODEL    = os.environ.get("MISTRAL_MODEL",    "mistral-small-latest")
_TIMEOUT         = 20
_MAX_TOKENS      = 2200


def _key(name: str) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name, "")
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()



def _call_openai(system: str, user: str) -> str:
    key = _key("OPENAI_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _OPENAI_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""

def _call_anthropic(system: str, user: str) -> str:
    key = _key("ANTHROPIC_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _ANTHROPIC_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": _ANTHROPIC_MODEL, "max_tokens": _MAX_TOKENS, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        for block in resp.json().get("content", []):
            if block.get("type") == "text":
                return block["text"].strip()
    except Exception:
        pass
    return ""


def _call_groq(system: str, user: str) -> str:
    key = _key("GROQ_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _GROQ_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


def _log_error(msg: str) -> None:
    # Store the last LLM error in Streamlit session state so the UI can display it.
    try:
        import streamlit as st
        st.session_state["_llm_last_error"] = msg
    except Exception:
        pass


def _call_gemini(system: str, user: str) -> str:
    key = _key("GEMINI_API_KEY")
    if not key:
        return ""
    # Try the configured model first, then fall back to gemini-1.5-flash.
    models_to_try = list({_GEMINI_MODEL, "gemini-1.5-flash", "gemini-2.0-flash"})
    for model in models_to_try:
        try:
            resp = requests.post(
                f"{_GEMINI_URL.format(model=model)}?key={key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}],
                    "generationConfig": {"maxOutputTokens": _MAX_TOKENS, "temperature": 0.5},
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                return text
        except requests.HTTPError as e:
            _log_error(f"Gemini {model}: HTTP {e.response.status_code}")
        except Exception as e:
            _log_error(f"Gemini {model}: {type(e).__name__}")
    return ""



def _call_openrouter(system: str, user: str) -> str:
    key = _key("OPENROUTER_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _OPENROUTER_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://preluma-edtech.streamlit.app", "X-Title": "Preluma"},
            json={"model": _OPENROUTER_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _call_together(system: str, user: str) -> str:
    key = _key("TOGETHER_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _TOGETHER_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _call_cerebras(system: str, user: str) -> str:
    key = _key("CEREBRAS_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _CEREBRAS_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _CEREBRAS_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _call_mistral(system: str, user: str) -> str:
    key = _key("MISTRAL_API_KEY")
    if not key:
        return ""
    try:
        resp = requests.post(
            _MISTRAL_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _MISTRAL_MODEL, "max_tokens": _MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def available_providers() -> list[str]:
    providers: list[str] = []
    mapping = [
        ("OPENAI_API_KEY",    "OpenAI"),
        ("ANTHROPIC_API_KEY", "Claude (Anthropic)"),
        ("GEMINI_API_KEY",    "Gemini"),
        ("GROQ_API_KEY",      "Groq"),
        ("CEREBRAS_API_KEY",  "Cerebras"),
        ("MISTRAL_API_KEY",   "Mistral"),
        ("OPENROUTER_API_KEY","OpenRouter"),
        ("TOGETHER_API_KEY",  "Together AI"),
    ]
    for key_name, label in mapping:
        if _key(key_name):
            providers.append(label)
    return providers


def active_provider() -> str:
    providers = available_providers()
    return providers[0] if providers else "Curated fallback"


def llm_available() -> bool:
    return bool(available_providers())


def _call_llm(system: str, user: str) -> str:
    # One provider answers; the next providers are automatic fallbacks.
    for fn in (_call_groq, _call_cerebras, _call_mistral, _call_openrouter, _call_together, _call_openai, _call_anthropic):
        result = fn(system, user)
        if result:
            return result
    return ""


def detect_topic_from_question(question: str, fallback_topic: str = "General learning") -> str:
    """Extract an explicit topic so old mission context cannot override the user's question."""
    import re as _re
    raw = " ".join(str(question).strip().split())
    lowered = raw.casefold()

    # Vague words that should never become a topic
    _VAGUE = {
        "help", "explain", "tell", "more", "details", "why", "how",
        "this", "it", "please", "okay", "ok", "yes", "no", "what",
        "thanks", "thank", "understand", "know", "learn", "study",
    }

    # FIX: "ai" must be whole-word only (prevents "explain" → AI via expl-ai-n)
    common = {
        "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
        "neural network": "Neural Network",
        "quantum mechanics": "Quantum Mechanics",
        "statistics": "Statistics",
        "variance": "Variance",
        "python": "Python Programming",
        "photosynthesis": "Photosynthesis",
        "artificial intelligence": "Artificial Intelligence",
        "urban water management": "Urban Water Management",
    }
    for phrase, title in common.items():
        if phrase in lowered:
            return title
    # Whole-word match for short tokens that are substrings of common words
    if _re.search(r'\bai\b', lowered):
        return "Artificial Intelligence"

    prefixes = [
        "about ", "explain ", "what is ", "what are ", "tell me about ",
        "teach me ", "describe ", "define ", "how does ", "how do ",
    ]
    candidate = lowered
    for prefix in prefixes:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):]
            break
    cleanup = [
        " simply", " in simple words", " like i am 5", " step by step",
        " with an example", " and give one example", " please", "?", ".",
    ]
    for suffix in cleanup:
        candidate = candidate.replace(suffix, "")
    candidate = candidate.strip(" :,-")
    # FIX: reject vague single words that pass the length check (e.g. "help", "explain")
    if candidate in _VAGUE:
        return fallback_topic or "General learning"
    if 1 <= len(candidate.split()) <= 7 and len(candidate) >= 3:
        return candidate.title()
    return fallback_topic or "General learning"


def _parse_json(raw: str) -> dict | None:
    clean = raw.strip()
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            part = part.strip().lstrip("json").strip()
            if part.startswith("{"):
                clean = part
                break
    try:
        return json.loads(clean)
    except Exception:
        start, end = clean.find("{"), clean.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(clean[start:end+1])
            except Exception:
                pass
    return None


def _detect_question_style(question: str) -> str:
    """Detect how the student wants the answer delivered."""
    import re as _re
    q = question.lower()
    # FIX: added "simply", "easily" so "explain X simply" → child style
    if any(w in q for w in ["5 year", "5-year", "kid", "child", "simple", "simply",
                             "easy", "easily", "beginner", "basic", "like i am 5"]):
        return "child"
    # FIX: "example" check BEFORE "exam" so "give me an example" doesn't trigger exam
    if any(w in q for w in ["example", "real life", "real-life", "use case", "application"]):
        return "example"
    # FIX: use word-boundary so "exam" doesn't match inside "example"
    if _re.search(r'\b(exam|viva|marks|answer for|write for|definition)\b', q):
        return "exam"
    if any(w in q for w in ["difference", "vs", "compare", "versus", "between"]):
        return "compare"
    # FIX: added "deep", "deeply", "in depth" — user writing "explain X deeply" → deep style
    if any(w in q for w in ["why", "reason", "because", "how does", "how do",
                             "deep", "deeply", "in depth", "in detail", "detailed"]):
        return "deep"
    return "normal"


def llm_tutor(topic: str, question: str, style: str = "Normal Mode") -> dict | None:
    q_style = _detect_question_style(question)

    # Build explanation style instruction based on BOTH persona and question style
    explanation_style = {
        "child": (
            "CRITICAL: The student is asking you to explain like they are 5 years old. "
            "You MUST use a fun story or toy analogy. NEVER use technical words. "
            "Example of what GOOD child-style sounds like: "
            "'Imagine computers are people in different cities. A protocol is like agreeing to speak the same language before talking — like both agreeing to speak English so they understand each other.' "
            "Your explain_simply field MUST sound exactly like this — fun, story-like, zero jargon. "
            "If your explanation sounds like a textbook, you have FAILED. Rewrite it until a 5-year-old would smile."
        ),
        "exam": (
            "The student needs a precise exam-ready answer. "
            "tiny_answer: one-line definition. "
            "explain_simply: 3 key points a student must mention in an exam answer, numbered. "
            "exam_angle: exact phrasing to use in a viva or written exam. "
            "Be structured, precise, and academic throughout."
        ),
        "example": (
            "The student wants to learn through examples. "
            "In explain_simply: give TWO vivid real-world examples first, then derive the concept from them. "
            "In real_life_example: give a third completely different example. "
            "Never start with the definition — always lead with the example."
        ),
        "compare": (
            "The student wants to compare two things. "
            "In explain_simply: write a clear side-by-side comparison. "
            "Start with what they have in common, then what makes them different. "
            "Be specific — name exact differences, not vague statements."
        ),
        "deep": (
            "The student wants to understand the deep reason WHY or HOW something works. "
            "In explain_simply: go beyond the definition — explain the mechanism, cause, and effect. "
            "Use a step-by-step logical flow. Use an analogy to make the reasoning click. "
            "Do not just repeat the definition — explain the underlying logic."
        ),
        "normal": (
            "Give a clear, direct, accurate explanation. "
            "Start with the core idea in one sentence, add one concrete example, then name one common mistake."
        ),
    }.get(q_style, "Give a clear and accurate explanation.")

    persona_instruction = {
        "Coach Mode": (
            "You are an encouraging coach. Start with a short motivating line, "
            "then give the explanation. Make the student feel capable."
        ),
        "Roast Mode": (
            "Use one clever, light joke about the question before explaining seriously. "
            "Keep the humour respectful. The explanation itself must be fully correct and complete."
        ),
    }.get(style, "Be clear, direct, and confident.")

    system = f"""You are Preluma UltraTutor — a highly capable AI academic assistant for second-year university students at Yunnan University, School of Software. You answer in clear, natural, connected English. You are as capable as ChatGPT, Claude, or Gemini — give equally strong, complete, and intelligent answers.

Your MOST IMPORTANT job: detect HOW the student is asking and match your answer style EXACTLY to that.

REQUIRED STYLE FOR THIS RESPONSE:
{explanation_style}

PERSONA:
{persona_instruction}

STRICT RULES:
1. The "explain_simply" field must FULLY match the required style — not just partially
2. If child-style was requested: ZERO technical jargon in explain_simply
3. If exam-style was requested: every sentence must be exam-appropriate and precise
4. Never use bullet symbols (* or -) anywhere in your answer
5. Short depth: 1-2 tight paragraphs. Balanced: 3-4 connected paragraphs. Deep: 5-8 thorough paragraphs
6. Write flowing natural prose — never disconnected fragments or list sentences
7. Give COMPLETE answers — do not truncate or trail off mid-sentence
8. ONLY output a valid JSON object — no text before or after, no markdown fences"""

    user = (
        f"Topic: {topic}\n"
        f"Student question: {question}\n\n"
        "Respond with exactly this JSON structure:\n"
        '{"concept": "short name of what you are explaining", '
        '"tiny_answer": "one sharp sentence that directly answers the question", '
        '"explain_simply": "a natural connected explanation matched to the request; for deep requests explain mechanism, cause, effect, and why it matters in coherent paragraphs", '
        '"real_life_example": "one concrete vivid real-world example", '
        '"common_mistake": "one mistake students make about this", '
        '"exam_angle": "what to say in an exam or viva about this"}'
    )

    raw = _call_llm(system, user)
    if not raw:
        return None

    parsed = _parse_json(raw)
    if parsed:
        required = {"concept", "tiny_answer", "explain_simply", "real_life_example", "common_mistake", "exam_angle"}
        if required.issubset(parsed.keys()):
            return parsed

    return {
        "concept": topic,
        "tiny_answer": raw[:300],
        "explain_simply": "",
        "real_life_example": "",
        "common_mistake": "",
        "exam_angle": "",
    }


def llm_brain_brief(topic: str, definition: str, concepts: list) -> dict | None:
    system = (
        "You are Preluma, a pre-class learning assistant. "
        "Generate a short, engaging brain brief to help a student prepare for a lecture. "
        "Be concrete. Avoid vague academic language. "
        "Respond with ONLY a valid JSON object — no markdown, no preamble."
    )
    user = (
        f"Topic: {topic}\nDefinition: {definition}\nKey concepts: {', '.join(concepts)}\n\n"
        'Generate:\n{"hook": "one engaging sentence that makes the topic feel interesting and relevant", '
        '"simple": "explain the topic in 2 sentences a 15-year-old would understand", '
        '"example": "one vivid real-life example that anyone can relate to", '
        '"misconception": "one common wrong belief students have about this topic", '
        '"study_tip": "one concrete action the student can take right now before class"}'
    )
    raw = _call_llm(system, user)
    if not raw:
        return None
    parsed = _parse_json(raw)
    if parsed and {"hook", "simple", "example", "misconception", "study_tip"}.issubset(parsed.keys()):
        return parsed
    return None


def llm_class_questions(topic: str, definition: str, concepts: list) -> list | None:
    system = (
        "You are Preluma, a pre-class learning assistant. "
        "Generate 5 smart questions a well-prepared student would ask a professor in class. "
        "Questions should be specific, insightful, and show genuine preparation — not just basic definitions. "
        "Respond with ONLY a JSON array of 5 strings — no markdown, no preamble."
    )
    user = (
        f"Topic: {topic}\nDefinition: {definition}\nKey concepts: {', '.join(concepts)}\n\n"
        'Respond as: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]'
    )
    raw = _call_llm(system, user)
    if not raw:
        return None
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(clean)
        if isinstance(result, list) and len(result) >= 3:
            return [str(q) for q in result[:5]]
    except Exception:
        pass
    return None


def llm_free_chat(question: str, provider_name: str = "AI") -> str:
    """Call the LLM for natural free conversation — returns plain text, no JSON required."""
    system = (
        f"You are Preluma AI, a friendly and knowledgeable academic assistant powered by {provider_name}. "
        "You help university students with any question — academic topics, study advice, general questions, or just conversation. "
        "Respond naturally and helpfully in 2-4 sentences. Be warm, direct, and clear. "
        "Never refuse to answer. If you do not know something, say so honestly and offer what you do know."
    )
    result = _call_llm(system, question)
    return result.strip() if result else ""


def llm_hw_tutor_intro(topic: str, weak_concepts: list, score_pct: float) -> str:
    """Generate an opening study message after a homework attempt."""
    weak_str = ", ".join(weak_concepts) if weak_concepts else "general understanding"
    system = (
        "You are Preluma AI, a warm and encouraging homework tutor for university students. "
        "Your job is to help the student understand what they got wrong and guide them to improve. "
        "Be supportive, clear, and specific. Respond in 3-4 sentences of natural prose."
    )
    user = (
        f"The student just completed a homework on '{topic}' and scored {score_pct:.0f}%. "
        f"Their weak areas are: {weak_str}. "
        "Write a short, encouraging opening message that acknowledges their score, "
        "mentions the weak concept(s) they should focus on, and invites them to ask questions."
    )
    result = _call_llm(system, user)
    if result:
        return result.strip()
    return (
        f"Good effort on the {topic} homework! You scored {score_pct:.0f}%. "
        f"Let's work on strengthening your understanding of {weak_str}. "
        "Feel free to ask me anything about the topic!"
    )


def llm_hw_tutor_reply(topic: str, weak_concepts: list, history: list, question: str) -> str:
    """Reply to a student question in the homework AI tutor chat."""
    weak_str = ", ".join(weak_concepts) if weak_concepts else "the topic"
    history_text = ""
    for msg in history[-6:]:
        role = "Student" if msg.get("role") == "user" else "Tutor"
        history_text += f"{role}: {msg.get('text', '')}\n"
    system = (
        f"You are Preluma AI, a patient and knowledgeable tutor helping a student understand '{topic}'. "
        f"The student's weak areas are: {weak_str}. "
        "Give clear, helpful, encouraging answers in 2-4 sentences. "
        "Focus on building understanding, not just giving answers."
    )
    user = f"Conversation so far:\n{history_text}\nStudent: {question}\n\nTutor:"
    result = _call_llm(system, user)
    if result:
        return result.strip()
    return "That's a great question! Let me help you think through it step by step."

