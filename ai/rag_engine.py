"""
ai/rag_engine.py — Retrieval-Augmented Generation.

::

    course notes / books / PDFs ──► chunk ──► embed ──► vector store
                                                           │
    student question ─────────────► embed ──► top-k chunks ┘──► prompt context ──► LLM
                                                                      │
                                     (no LLM key?) extractive answer ◄┘

The engine is deliberately LLM-agnostic: it returns *retrieved passages with citations*;
``services.ai_service`` decides whether to feed them to a language model or, when no provider
is configured, to show the best passages directly (so the tutor still works offline).

Ranking is hybrid: ``0.75 × vector similarity + 0.25 × keyword overlap``.  The keyword term
rescues exact terms (acronyms, names) that dense/hashed vectors can blur.
"""

from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ai.documents import SourceDocument, chunk_text
from ai.embeddings import Embedder, get_embedder, tokenize
from ai.vector_store import Chunk, InMemoryVectorStore, create_vector_store

logger = logging.getLogger("preluma.rag")

VECTOR_WEIGHT = 0.75
KEYWORD_WEIGHT = 0.25
HEADING_WEIGHT = 0.15        # bonus when query terms appear in the chunk's heading (first 80 chars)


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    text: str
    source: str
    title: str
    score: float
    doc_id: str
    metadata: dict

    def citation(self) -> str:
        return f"[{self.rank}] {self.title}" + (f" — {self.source}" if self.source else "")


class RAGEngine:
    def __init__(
        self,
        embedder: Embedder | None = None,
        store: InMemoryVectorStore | None = None,
        *,
        index_path: Path | None = None,
        embedder_preference: str = "auto",
        vector_backend: str = "auto",
        min_score: float = 0.12,
    ) -> None:
        self.embedder = embedder or get_embedder(embedder_preference)
        self.store = store or create_vector_store(
            vector_backend, index_path, self.embedder.name, self.embedder.dim
        )
        self.min_score = min_score
        self._lock = threading.RLock()

    # ── indexing ─────────────────────────────────────────────────────────────
    def index_document(self, doc: SourceDocument, *, replace: bool = True, save: bool = True) -> int:
        """Chunk, embed and store a document.  Returns the number of chunks indexed."""
        pieces = chunk_text(doc.text)
        if not pieces:
            return 0
        chunks = [
            Chunk(
                id=f"{doc.doc_id}#{i}",
                doc_id=doc.doc_id,
                text=piece,
                source=doc.source,
                metadata={**doc.metadata, "title": doc.title},
            )
            for i, piece in enumerate(pieces)
        ]
        vectors = self.embedder.embed([c.text for c in chunks])
        with self._lock:
            if replace:
                self.store.delete_document(doc.doc_id)
            self.store.add(chunks, vectors)
            if save:
                self.store.save()
        return len(chunks)

    def index_missing(self, documents: Iterable[SourceDocument]) -> int:
        """Index only documents the store does not already contain (cheap start-up)."""
        added = 0
        with self._lock:
            for doc in documents:
                if not self.store.has_document(doc.doc_id):
                    added += self.index_document(doc, replace=False, save=False)
            if added:
                self.store.save()
        return added

    def delete_document(self, doc_id: str) -> int:
        with self._lock:
            removed = self.store.delete_document(doc_id)
            self.store.save()
        return removed

    # ── retrieval ────────────────────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        k: int = 4,
        topic: str | None = None,
        *,
        user_id: int | None = None,
        allowed_course_ids: set[int] | None = None,
        include_staff: bool = False,
    ) -> list[RetrievedChunk]:
        """Top passages after visibility filtering.

        Built-in topic packs are public. Uploaded passages must explicitly be
        public, owned by the requesting user, staff-only for staff, or attached
        to one of the requester's allowed courses.
        """
        query = (query or "").strip()
        if not query or self.store.count() == 0:
            return []
        query_vector = self.embedder.embed([query])[0]
        with self._lock:
            fetch = self.store.count() if allowed_course_ids is not None or user_id is not None else max(k * 4, 12)
            candidates = self.store.search(query_vector, k=max(fetch, k), topic=topic)
        query_terms = set(tokenize(query))
        rescored = []
        for chunk, vector_score in candidates:
            visibility = str(chunk.metadata.get("visibility", "public"))
            owner = chunk.metadata.get("uploaded_by")
            course_id = chunk.metadata.get("course_id")
            visible = (
                visibility == "public"
                or (visibility == "private" and user_id is not None and owner == user_id)
                or (visibility == "staff" and include_staff)
                or (
                    visibility == "course"
                    and course_id is not None
                    and allowed_course_ids is not None
                    and course_id in allowed_course_ids
                )
            )
            if not visible:
                continue
            overlap = heading = 0.0
            if query_terms:
                overlap = len(query_terms & set(tokenize(chunk.text))) / len(query_terms)
                heading = len(query_terms & set(tokenize(chunk.text[:80]))) / len(query_terms)
            rescored.append(
                (chunk, VECTOR_WEIGHT * vector_score + KEYWORD_WEIGHT * overlap + HEADING_WEIGHT * heading)
            )
        rescored.sort(key=lambda item: item[1], reverse=True)
        results = []
        for chunk, score in rescored:
            if score < self.min_score:
                continue
            results.append(
                RetrievedChunk(
                    rank=len(results) + 1,
                    text=chunk.text,
                    source=chunk.source,
                    title=str(chunk.metadata.get("title", chunk.doc_id)),
                    score=round(score, 3),
                    doc_id=chunk.doc_id,
                    metadata=dict(chunk.metadata),
                )
            )
            if len(results) >= k:
                break
        return results

    # ── prompt helpers ───────────────────────────────────────────────────────
    @staticmethod
    def build_context(chunks: Iterable[RetrievedChunk], max_chars: int = 3200) -> str:
        """Numbered passages for the prompt (stops before exceeding ``max_chars``)."""
        lines, used = [], 0
        for chunk in chunks:
            entry = f"<source id='{chunk.rank}' title='{chunk.title}'>\n{chunk.text}\n</source>"
            if used + len(entry) > max_chars and lines:
                break
            lines.append(entry)
            used += len(entry)
        return "\n\n".join(lines)

    @staticmethod
    def extractive_answer(query: str, chunks: list[RetrievedChunk], max_sentences: int = 3) -> str:
        """Offline fallback: the sentences of the best passages that overlap most with the query."""
        if not chunks:
            return ""
        terms = set(tokenize(query))
        scored = []
        for chunk in chunks[:3]:
            for sentence in re.split(r"(?<=[.!?。])\s+", chunk.text):
                sentence = sentence.strip()
                if len(sentence) < 25:
                    continue
                overlap = len(terms & set(tokenize(sentence)))
                scored.append((overlap, -chunk.rank, sentence, chunk.rank))
        scored.sort(reverse=True)
        picked, seen = [], set()
        best = scored[0][0] if scored else 0
        floor = max(1, math.ceil(0.75 * best))   # later sentences must be nearly as relevant as the best one
        for overlap, _, sentence, rank in scored:
            if picked and overlap < floor:   # don't pad the answer with weakly related sentences
                break
            if sentence not in seen:
                seen.add(sentence)
                picked.append(f"{sentence} [{rank}]")
            if len(picked) >= max_sentences:
                break
        return " ".join(picked)

    def stats(self) -> dict:
        return {
            "chunks": self.store.count(),
            "embedder": self.embedder.name,
            "dimensions": self.embedder.dim,
            "store": type(self.store).__name__,
        }
