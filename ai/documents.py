"""
ai/documents.py — getting course material ready for the vector store.

* :func:`chunk_text` splits text into overlapping, paragraph-aware pieces (small enough to be
  specific, large enough to carry meaning).
* :func:`extract_text` reads ``.txt`` / ``.md`` / ``.pdf`` uploads (PDF needs ``pypdf``).
* :func:`pack_to_documents` turns the curated topic packs into indexable documents, so the
  tutor can retrieve from the built-in library with no uploads at all.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from security.uploads import UploadPolicy, validate_upload

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = (".txt", ".md", ".markdown", ".pdf")


class DocumentError(ValueError):
    """Raised with a user-presentable message when a file cannot be read."""


@dataclass(frozen=True)
class SourceDocument:
    doc_id: str
    title: str
    text: str
    source: str = ""
    metadata: dict = field(default_factory=dict)


def chunk_text(text: str, max_chars: int = 800, overlap: int = 120) -> list[str]:
    """Split ``text`` into chunks of at most ``max_chars`` characters.

    Paragraphs are kept together where possible; a paragraph longer than the limit is split on
    sentence boundaries; consecutive chunks share ``overlap`` characters of context so an idea
    that straddles a boundary is still retrievable.
    """
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    overlap = max(0, min(overlap, max_chars // 2))
    cleaned = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    if not cleaned:
        return []

    units: list[str] = []
    for paragraph in re.split(r"\n\s*\n", cleaned):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?。！？])\s+", paragraph):
            while len(sentence) > max_chars:                # pathological: no punctuation
                units.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            if current and len(current) + 1 + len(sentence) > max_chars:
                units.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            units.append(current)

    chunks: list[str] = []
    buffer = ""
    for unit in units:
        if buffer and len(buffer) + 2 + len(unit) > max_chars:
            chunks.append(buffer)
            tail = buffer[-overlap:] if overlap else ""
            buffer = f"{tail} {unit}".strip() if tail and len(tail) + 1 + len(unit) <= max_chars else unit
        else:
            buffer = f"{buffer}\n\n{unit}".strip() if buffer else unit
    if buffer:
        chunks.append(buffer)
    return chunks


def extract_text(filename: str, data: bytes) -> str:
    """Return the text of an uploaded file or raise :class:`DocumentError`."""
    try:
        checked = validate_upload(
            filename,
            data,
            UploadPolicy(frozenset(SUPPORTED_EXTENSIONS), MAX_UPLOAD_BYTES, "knowledge document"),
        )
    except ValueError as exc:
        raise DocumentError(str(exc)) from exc
    filename, data = checked.filename, checked.data
    name = filename.lower()
    if name.endswith((".txt", ".md", ".markdown")):
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):   # gb18030: common on Chinese campuses
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentError("Could not decode the text file (unknown encoding).")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentError("PDF support needs the 'pypdf' package (pip install pypdf).") from exc
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise DocumentError("This PDF could not be read (it may be encrypted or scanned).") from exc
        if not text.strip():
            raise DocumentError("No selectable text found in this PDF (scanned image?).")
        return text
    raise DocumentError(f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")


def pack_to_documents(topics: dict[str, dict]) -> list[SourceDocument]:
    """Convert curated topic packs into one document per topic (concepts become paragraphs)."""
    documents = []
    for key, pack in topics.items():
        title = str(pack.get("title", key.title()))
        parts = [f"{title}. {pack.get('definition', '')}", str(pack.get("simple", ""))]
        parts += [str(f) for f in pack.get("facts", [])]
        for name, concept in pack.get("concepts", {}).items():
            parts.append(
                f"{title} — {name}: {concept.get('definition', '')} "
                f"In simple words: {concept.get('kid', '')} Example: {concept.get('example', '')} "
                f"Common mistake: {concept.get('mistake', '')} Exam tip: {concept.get('exam', '')}"
            )
        for name, description in pack.get("applications", {}).items():
            parts.append(f"{title} application — {name}: {description}")
        for misconception in pack.get("misconceptions", []):
            parts.append(f"Common misconception about {title}: {misconception}")
        documents.append(
            SourceDocument(
                doc_id=f"topic:{key}",
                title=title,
                text="\n\n".join(p for p in parts if p.strip()),
                source="Curated topic library",
                metadata={"topic": key},
            )
        )
    return documents
