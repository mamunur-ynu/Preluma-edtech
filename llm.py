"""
Backward-compatibility shim for the former ``llm.py``.

Provider calls moved to ``ai.llm_router`` (table-driven, logged, testable), prompts to
``ai.prompts`` and use cases to ``services.ai_service``.  The legacy function names below are
kept so existing UI code keeps working.
"""
from __future__ import annotations

from ai.prompts import detect_question_style as _detect_question_style  # noqa: F401
from ai.prompts import detect_topic_from_question  # noqa: F401
from ai.prompts import parse_json_object as _parse_json  # noqa: F401
from services import ai_service as _svc


def available_providers() -> list[str]:
    return _svc.available_providers()


def active_provider() -> str:
    return _svc.active_provider()


def llm_available() -> bool:
    return _svc.llm_available()


def _call_llm(system: str, user: str) -> str:
    return _svc.complete_text(system, user)


def llm_tutor(topic: str, question: str, style: str = "Normal Mode") -> dict | None:
    return _svc.llm_tutor(topic, question, style)


def llm_brain_brief(topic: str, definition: str, concepts: list) -> dict | None:
    return _svc.generate_brain_brief(topic, definition, concepts)


def llm_class_questions(topic: str, definition: str, concepts: list) -> list | None:
    return _svc.generate_class_questions(topic, definition, concepts)


def llm_free_chat(question: str, provider_name: str = "AI") -> str:
    return _svc.free_chat(question, provider_name)


def llm_hw_tutor_intro(topic: str, weak_concepts: list, score_pct: float) -> str:
    return _svc.homework_tutor_intro(topic, weak_concepts, score_pct)


def llm_hw_tutor_reply(topic: str, weak_concepts: list, history: list, question: str) -> str:
    return _svc.homework_tutor_reply(topic, weak_concepts, history, question)
