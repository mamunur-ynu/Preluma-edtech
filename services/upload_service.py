"""Safe local upload storage used by legacy Streamlit screens.

Files are validated before an atomic write under the configured runtime data
directory. Returned paths are relative identifiers; callers must not expose the
directory as public static storage in production.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from config import get_settings
from security.uploads import UploadPolicy, validate_upload

HOMEWORK_POLICY = UploadPolicy(frozenset({".pdf", ".doc", ".docx", ".txt"}), 10 * 1024 * 1024, "homework file")
PROFILE_IMAGE_POLICY = UploadPolicy(frozenset({".jpg", ".jpeg", ".png", ".webp"}), 5 * 1024 * 1024, "profile image")
PROJECT_FILE_POLICY = UploadPolicy(
    frozenset({".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}),
    25 * 1024 * 1024,
    "project file",
)


@dataclass(frozen=True)
class StoredUpload:
    filename: str
    relative_path: str
    sha256: str
    size: int


def store_private_upload(namespace: str, filename: str, data: bytes, policy: UploadPolicy) -> StoredUpload:
    checked = validate_upload(filename, data, policy)
    safe_namespace = "".join(c for c in namespace if c.isalnum() or c in "_-")[:48] or "misc"
    digest = hashlib.sha256(checked.data).hexdigest()
    stored_name = f"{digest[:16]}-{checked.filename}"
    root = get_settings().data_dir / "uploads" / safe_namespace
    root.mkdir(parents=True, exist_ok=True)
    target = root / stored_name
    if not target.exists():
        fd, temp_name = tempfile.mkstemp(prefix=".upload-", dir=root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(checked.data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
    return StoredUpload(checked.filename, str(Path("uploads") / safe_namespace / stored_name), digest, len(checked.data))
