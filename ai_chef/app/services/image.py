from __future__ import annotations

import base64
from pathlib import Path

from fastapi import HTTPException

from app.config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE


def validate_image(filename: str, content: bytes) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext or 'unknown'}. Allowed: {allowed}",
        )
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Max {MAX_IMAGE_SIZE // 1024 // 1024}MB",
        )


def image_to_base64(content: bytes) -> str:
    return base64.b64encode(content).decode("utf-8")
