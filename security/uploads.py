"""Content-aware validation for user uploads.

Browser MIME types and filename extensions are attacker controlled.  The
validator applies a narrow policy, normalises the basename, enforces a byte
limit, rejects empty/NUL-heavy payloads, and checks common file signatures.
It intentionally does not claim to be malware scanning; production object
storage should add quarantine and antivirus scanning before publication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UploadPolicy:
    extensions: frozenset[str]
    max_bytes: int
    label: str = "file"


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    extension: str
    data: bytes


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._()\- ]+")
_MAGIC: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".ppt": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}


def _safe_filename(raw: str, extension: str) -> str:
    basename = Path(str(raw or "")).name.strip().replace("\x00", "")
    stem = Path(basename).stem[:100]
    stem = _SAFE_NAME.sub("_", stem).strip(" ._") or "upload"
    return f"{stem}{extension}"


def _signature_matches(extension: str, data: bytes) -> bool:
    if extension == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    signatures = _MAGIC.get(extension)
    return not signatures or any(data.startswith(signature) for signature in signatures)


def validate_upload(filename: str, data: bytes, policy: UploadPolicy) -> ValidatedUpload:
    payload = bytes(data or b"")
    extension = Path(str(filename or "")).suffix.lower()
    allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in policy.extensions}
    if extension not in allowed:
        raise ValueError(f"Unsupported {policy.label} type. Allowed: {', '.join(sorted(allowed))}.")
    if not payload:
        raise ValueError(f"The uploaded {policy.label} is empty.")
    if len(payload) > policy.max_bytes:
        limit_mb = policy.max_bytes / (1024 * 1024)
        raise ValueError(f"The uploaded {policy.label} exceeds the {limit_mb:g} MB limit.")
    if not _signature_matches(extension, payload):
        raise ValueError(f"The {policy.label} content does not match its {extension} extension.")
    if extension in {".txt", ".md", ".markdown"}:
        if b"\x00" in payload[:4096]:
            raise ValueError("Text uploads may not contain binary NUL bytes.")
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                payload.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Text uploads must use UTF-8 or GB18030 encoding.")
    return ValidatedUpload(_safe_filename(filename, extension), extension, payload)
