from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import UPLOAD_DIR


def save_upload(filename: str, content: bytes) -> Path:
    ext = Path(filename).suffix.lower()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    path.write_bytes(content)
    return path
