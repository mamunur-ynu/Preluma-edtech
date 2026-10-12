"""
ai/vector_store.py — storage and nearest-neighbour search for embedded text chunks.

* :class:`InMemoryVectorStore` — pure Python, brute-force cosine, JSON persistence.  Exact and
  perfectly adequate for thousands of chunks (a course's lecture notes).
* :class:`FaissVectorStore` — same interface backed by FAISS (``pip install faiss-cpu``) for
  large collections.  Optional; chosen automatically when available and the corpus is big.

Both keep chunk metadata beside the vectors and remember which embedder produced them: if the
embedder changes (hashing → sentence-transformers) the stored index is discarded and rebuilt,
because vectors from different models are not comparable.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

logger = logging.getLogger("preluma.vectorstore")


@dataclass
class Chunk:
    id: str                       # unique, e.g. "topic:machine learning#2"
    doc_id: str                   # document the chunk came from
    text: str
    source: str = ""              # human-readable origin (file name, "Curated library")
    metadata: dict = field(default_factory=dict)


class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None: ...
    def search(self, vector: Sequence[float], k: int = 4, topic: str | None = None) -> list[tuple[Chunk, float]]: ...
    def delete_document(self, doc_id: str) -> int: ...
    def has_document(self, doc_id: str) -> bool: ...
    def count(self) -> int: ...
    def save(self) -> None: ...


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class InMemoryVectorStore:
    """Exact cosine search over L2-normalised vectors (so cosine == dot product)."""

    def __init__(self, path: Path | None = None, embedder_name: str = "", dim: int = 0) -> None:
        self.path = path
        self.embedder_name = embedder_name
        self.dim = dim
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []
        if path is not None:
            self._load()

    # ── write ────────────────────────────────────────────────────────────────
    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        known = {c.id: i for i, c in enumerate(self._chunks)}
        for chunk, vector in zip(chunks, vectors):
            if chunk.id in known:                      # replace in place → idempotent indexing
                self._chunks[known[chunk.id]] = chunk
                self._vectors[known[chunk.id]] = list(vector)
            else:
                known[chunk.id] = len(self._chunks)
                self._chunks.append(chunk)
                self._vectors.append(list(vector))

    def delete_document(self, doc_id: str) -> int:
        keep = [i for i, c in enumerate(self._chunks) if c.doc_id != doc_id]
        removed = len(self._chunks) - len(keep)
        self._chunks = [self._chunks[i] for i in keep]
        self._vectors = [self._vectors[i] for i in keep]
        return removed

    # ── read ─────────────────────────────────────────────────────────────────
    def search(self, vector: Sequence[float], k: int = 4, topic: str | None = None) -> list[tuple[Chunk, float]]:
        scored = []
        for chunk, stored in zip(self._chunks, self._vectors):
            if topic and chunk.metadata.get("topic") != topic:
                continue
            scored.append((chunk, _dot(vector, stored)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k]

    def has_document(self, doc_id: str) -> bool:
        return any(c.doc_id == doc_id for c in self._chunks)

    def count(self) -> int:
        return len(self._chunks)

    def documents(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for chunk in self._chunks:
            counts[chunk.doc_id] = counts.get(chunk.doc_id, 0) + 1
        return counts

    # ── persistence ──────────────────────────────────────────────────────────
    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "embedder": self.embedder_name,
            "dim": self.dim,
            "chunks": [asdict(c) for c in self._chunks],
            "vectors": [[round(v, 6) for v in vec] for vec in self._vectors],
        }
        # Write to a temp file then rename: a crash can never leave a half-written index.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp, self.path)

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("embedder") != self.embedder_name or payload.get("dim") != self.dim:
                logger.info("Vector index was built with another embedder; discarding it.")
                return
            self._chunks = [Chunk(**c) for c in payload["chunks"]]
            self._vectors = [list(v) for v in payload["vectors"]]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Could not read vector index %s (%s); starting empty.", self.path, exc)
            self._chunks, self._vectors = [], []


class FaissVectorStore(InMemoryVectorStore):
    """FAISS ``IndexFlatIP`` search with the same chunk bookkeeping as the in-memory store.

    The index is rebuilt from the stored vectors whenever the contents change, which keeps the
    code simple and correct (deletions are awkward in flat FAISS indexes).  Searching is the
    expensive, frequent operation and is what FAISS accelerates.
    """

    def __init__(self, path: Path | None = None, embedder_name: str = "", dim: int = 0) -> None:
        import faiss  # noqa: F401  (ImportError → caller falls back to in-memory)
        import numpy  # noqa: F401

        super().__init__(path, embedder_name, dim)
        self._index = None
        self._dirty = True

    def add(self, chunks, vectors) -> None:
        super().add(chunks, vectors)
        self._dirty = True

    def delete_document(self, doc_id: str) -> int:
        self._dirty = True
        return super().delete_document(doc_id)

    def _ensure_index(self) -> None:
        import faiss
        import numpy as np

        if not self._dirty and self._index is not None:
            return
        index = faiss.IndexFlatIP(self.dim)
        if self._vectors:
            index.add(np.asarray(self._vectors, dtype="float32"))
        self._index, self._dirty = index, False

    def search(self, vector, k: int = 4, topic: str | None = None):
        import numpy as np

        if not self._chunks:
            return []
        self._ensure_index()
        # Over-fetch when filtering by topic, then trim.
        fetch = len(self._chunks) if topic else min(k, len(self._chunks))
        scores, ids = self._index.search(np.asarray([vector], dtype="float32"), fetch)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            chunk = self._chunks[int(idx)]
            if topic and chunk.metadata.get("topic") != topic:
                continue
            results.append((chunk, float(score)))
        return results[:k]


def create_vector_store(
    backend: str, path: Path | None, embedder_name: str, dim: int, expected_size: int = 0
) -> InMemoryVectorStore:
    """``backend``: ``memory`` | ``faiss`` | ``auto`` (FAISS only for large collections)."""
    backend = (backend or "auto").lower()
    if backend == "faiss" or (backend == "auto" and expected_size > 20_000):
        try:
            return FaissVectorStore(path, embedder_name, dim)
        except ImportError:
            logger.warning("faiss/numpy not installed; using the in-memory vector store.")
    return InMemoryVectorStore(path, embedder_name, dim)
