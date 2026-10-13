"""
ai/vector_store.py — storage and nearest-neighbour search for embedded text chunks.

* :class:`InMemoryVectorStore` — pure Python, brute-force cosine, JSON persistence.  Exact and
  perfectly adequate for thousands of chunks (a course's lecture notes).
* :class:`FaissVectorStore` — same interface backed by FAISS (``pip install faiss-cpu``) for
  large collections.  Optional; chosen automatically when available and the corpus is big.
* :class:`DatabaseVectorStore` — committed relational chunks shared by PostgreSQL workers.

Stores keep chunk metadata beside the vectors and remember which embedder produced them. A
different embedder is never searched against old vectors, because those spaces are incomparable.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

from sqlalchemy import delete, select, text

from database.connection import session_scope
from database.models import VectorChunk
from security.document_crypto import decrypt_source, encrypt_source

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
    def document_metadata(self, doc_id: str) -> dict | None: ...
    def count(self) -> int: ...
    def documents(self) -> dict[str, int]: ...
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

    def document_metadata(self, doc_id: str) -> dict | None:
        return next((dict(c.metadata) for c in self._chunks if c.doc_id == doc_id), None)

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


class DatabaseVectorStore:
    """Committed database rows form the index seen by every worker.

    Brute-force scoring is intentional for modest class corpora. No process cache
    or local JSON is involved; a later pgvector adapter can replace this store.
    """

    def __init__(self, embedder_name: str, dim: int) -> None:
        self.embedder_name = embedder_name
        self.dim = dim

    def _rows(self) -> list[VectorChunk]:
        with session_scope() as session:
            rows = session.scalars(select(VectorChunk).where(
                VectorChunk.embedder == self.embedder_name, VectorChunk.dim == self.dim
            )).all()
            session.expunge_all()
        return rows

    @staticmethod
    def _record(chunk: Chunk, vector: Sequence[float], embedder: str, dim: int) -> VectorChunk:
        if len(vector) != dim:
            raise ValueError("Vector dimensions do not match the embedder.")
        digest = chunk.metadata.get("content_sha256")
        if chunk.doc_id.startswith("doc:") and not digest:
            raise ValueError("Uploaded database chunks require a source digest.")
        stored_text = "fernet:" + encrypt_source(chunk.text, digest).decode() if digest else chunk.text
        return VectorChunk(
            id=chunk.id, doc_id=chunk.doc_id, embedder=embedder, dim=dim,
            text=stored_text, source=chunk.source,
            metadata_json=json.dumps(chunk.metadata), vector_json=json.dumps(list(vector)),
        )

    def _write(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]],
               replacing: str | None = None) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if replacing is not None and any(chunk.doc_id != replacing for chunk in chunks):
            raise ValueError("Replacement chunks must belong to the same document.")
        records = [self._record(c, v, self.embedder_name, self.dim) for c, v in zip(chunks, vectors)]
        with session_scope() as session:
            if replacing is not None and session.bind.dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:doc_id))"), {"doc_id": replacing})
            if replacing is not None:
                session.execute(delete(VectorChunk).where(VectorChunk.doc_id == replacing))
            for record in records:
                session.execute(text(
                    "INSERT INTO vector_chunks (id, doc_id, embedder, dim, text, source, metadata_json, vector_json) "
                    "VALUES (:id, :doc_id, :embedder, :dim, :text, :source, :metadata_json, :vector_json) "
                    "ON CONFLICT (id) DO UPDATE SET doc_id = excluded.doc_id, embedder = excluded.embedder, "
                    "dim = excluded.dim, text = excluded.text, source = excluded.source, "
                    "metadata_json = excluded.metadata_json, vector_json = excluded.vector_json"
                ), {key: getattr(record, key) for key in (
                    "id", "doc_id", "embedder", "dim", "text", "source", "metadata_json", "vector_json"
                )})

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        self._write(chunks, vectors)

    def replace_document(self, doc_id: str, chunks: Sequence[Chunk],
                         vectors: Sequence[Sequence[float]]) -> None:
        self._write(chunks, vectors, replacing=doc_id)

    def delete_document(self, doc_id: str) -> int:
        with session_scope() as session:
            if session.bind.dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:doc_id))"), {"doc_id": doc_id})
            result = session.execute(delete(VectorChunk).where(VectorChunk.doc_id == doc_id))
            return result.rowcount or 0

    def search(self, vector: Sequence[float], k: int = 4,
               topic: str | None = None) -> list[tuple[Chunk, float]]:
        if len(vector) != self.dim:
            raise ValueError("Query dimensions do not match the embedder.")
        scored = []
        for row in self._rows():
            metadata = json.loads(row.metadata_json)
            if topic and metadata.get("topic") != topic:
                continue
            if row.doc_id.startswith("doc:") and not row.text.startswith("fernet:"):
                continue  # deny legacy/plaintext uploaded chunks in the shared store
            chunk_text = (decrypt_source(row.text.removeprefix("fernet:").encode(),
                                         metadata["content_sha256"])
                          if row.text.startswith("fernet:") else row.text)
            chunk = Chunk(row.id, row.doc_id, chunk_text, row.source, metadata)
            scored.append((chunk, _dot(vector, json.loads(row.vector_json))))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k]

    def has_document(self, doc_id: str) -> bool:
        return self.document_metadata(doc_id) is not None

    def document_metadata(self, doc_id: str) -> dict | None:
        with session_scope() as session:
            row = session.scalars(select(VectorChunk).where(
                VectorChunk.doc_id == doc_id, VectorChunk.embedder == self.embedder_name,
                VectorChunk.dim == self.dim
            ).limit(1)).first()
            return json.loads(row.metadata_json) if row else None

    def count(self) -> int:
        return sum(self.documents().values())

    def documents(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self._rows():
            counts[row.doc_id] = counts.get(row.doc_id, 0) + 1
        return counts

    def save(self) -> None:
        """Each mutation is already committed transactionally."""


def create_vector_store(
    backend: str, path: Path | None, embedder_name: str, dim: int, expected_size: int = 0
) -> VectorStore:
    """``backend``: ``database`` | ``memory`` | ``faiss`` | ``auto``."""
    backend = (backend or "auto").lower()
    if backend == "database":
        return DatabaseVectorStore(embedder_name, dim)
    if backend == "faiss" or (backend == "auto" and expected_size > 20_000):
        try:
            return FaissVectorStore(path, embedder_name, dim)
        except ImportError:
            logger.warning("faiss/numpy not installed; using the in-memory vector store.")
    return InMemoryVectorStore(path, embedder_name, dim)
