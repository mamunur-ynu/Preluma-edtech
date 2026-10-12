"""
ai/memory.py — conversation memory for the AI tutor.

Language models are stateless, so "memory" means choosing which earlier turns to send again.
:class:`ConversationMemory` keeps the **last few turns verbatim** and compresses everything
older into one short summary line ("Earlier the student asked about: …"), which keeps prompts
small while the tutor still remembers what the session was about.

The class is pure (it takes message dicts and returns message dicts).  Persistence lives in
``services.ai_service`` via the conversation repository, so the same memory logic works for
Streamlit, FastAPI or a test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

Message = Mapping[str, str]   # {"role": "user"|"assistant", "content": "..."}


@dataclass(frozen=True)
class MemoryView:
    summary: str                     # "" when there is nothing older than the window
    recent: list[dict[str, str]]     # verbatim messages, oldest first

    def as_prompt_prefix(self) -> str:
        return f"Conversation summary: {self.summary}\n" if self.summary else ""


class ConversationMemory:
    def __init__(self, max_recent_messages: int = 6, max_chars: int = 3000, max_summary_topics: int = 6) -> None:
        self.max_recent_messages = max_recent_messages
        self.max_chars = max_chars
        self.max_summary_topics = max_summary_topics

    def build(self, messages: Sequence[Message]) -> MemoryView:
        """Split ``messages`` into an old-part summary and a recent verbatim window."""
        cleaned = [
            {"role": "assistant" if m.get("role") == "assistant" else "user", "content": str(m.get("content", ""))}
            for m in messages
            if str(m.get("content", "")).strip()
        ]
        recent = cleaned[-self.max_recent_messages:]
        older = cleaned[: len(cleaned) - len(recent)]

        # Trim from the oldest side if the window is too long for the prompt budget.
        while recent and sum(len(m["content"]) for m in recent) > self.max_chars:
            older.append(recent.pop(0))
        # A conversation must start with a user turn for most providers.
        while recent and recent[0]["role"] != "user":
            older.append(recent.pop(0))

        return MemoryView(summary=self._summarize(older), recent=recent)

    def _summarize(self, older: Sequence[Message]) -> str:
        questions = [m["content"].strip().rstrip("?.! ") for m in older if m["role"] == "user"]
        if not questions:
            return ""
        shortened = [q if len(q) <= 80 else q[:77] + "…" for q in questions[-self.max_summary_topics:]]
        return "Earlier the student asked about: " + "; ".join(shortened) + "."
