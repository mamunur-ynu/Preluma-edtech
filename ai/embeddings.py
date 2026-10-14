"""
ai/embeddings.py — turn text into vectors.

Two interchangeable back ends behind one tiny interface (``name``, ``dim``, ``embed``):

* :class:`HashingEmbedder` — **default, zero dependencies.**  A "hashing trick" bag-of-words
  with word bigrams, light stemming and sub-linear term frequency, L2-normalised.  Deterministic
  (uses ``blake2b``, never Python's per-process ``hash``), instant, runs offline, and is good
  enough for keyword-heavy course material.
* :class:`SentenceTransformerEmbedder` — semantic embeddings from the ``sentence-transformers``
  library (``all-MiniLM-L6-v2`` by default).  Optional: install it and set
  ``PRELUMA_EMBEDDINGS=sentence-transformers`` (or leave ``auto``).

Why two?  Streamlit Cloud's free tier has ~1 GB RAM; PyTorch alone can exceed that.  The
architecture lets a laptop or a real server use semantic search without forcing it on the demo.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Protocol, Sequence

logger = logging.getLogger("preluma.embeddings")

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have how i in is it its of on or that the this to was "
    "what when where which who why will with you your do does did can could should would about "
    "into than then there these those they them their we our us not no yes if so such also more".split()
)


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens without stop-words, with a very small suffix stemmer."""
    tokens = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in _STOPWORDS or len(raw) < 2:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if raw.endswith(suffix) and len(raw) - len(suffix) >= 3:
                raw = raw[: -len(suffix)]
                break
        tokens.append(raw)
    return tokens


def _bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    sign = 1.0 if (value >> 63) & 1 else -1.0
    return value % dim, sign


class HashingEmbedder:
    """Dependency-free lexical embedder (see module docstring)."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = tokenize(text)
        features: dict[str, int] = {}
        for token in tokens:
            features[token] = features.get(token, 0) + 1
        for first, second in zip(tokens, tokens[1:]):
            gram = f"{first}_{second}"
            features[gram] = features.get(gram, 0) + 1
        vector = [0.0] * self.dim
        for feature, count in features.items():
            index, sign = _bucket(feature, self.dim)
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector


class SentenceTransformerEmbedder:
    """Semantic embeddings via ``sentence-transformers`` (lazy import, optional dependency)."""

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer  # raises ImportError if missing

        self.model_name = model_name or os.environ.get("PRELUMA_ST_MODEL", "all-MiniLM-L6-v2")
        self._model = SentenceTransformer(self.model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())
        self.name = f"st-{self.model_name}"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, row)) for row in vectors]


def get_embedder(preference: str = "auto") -> Embedder:
    """Pick a back end.  ``auto`` tries sentence-transformers and falls back to hashing."""
    preference = (preference or "auto").lower()
    if preference in ("auto", "sentence-transformers", "st"):
        try:
            return SentenceTransformerEmbedder()
        except ImportError:
            if preference != "auto":
                logger.warning("sentence-transformers is not installed; using the hashing embedder.")
        except Exception as exc:  # model download blocked, out of memory …
            logger.warning("Could not load sentence-transformers (%s); using the hashing embedder.", exc)
    return HashingEmbedder()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two (not necessarily normalised) vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
