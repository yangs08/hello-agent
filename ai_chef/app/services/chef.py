from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.agents.chef import run_chef_agent
from app.db import append_message, get_image_by_url
from app.schemas import ChatResponse

_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

def _mime_type_for_path(path: Path, fallback: str = "image/jpeg") -> str:
    return _MIME_BY_EXTENSION.get(path.suffix.lower(), fallback)


def _infer_mime_type(content: bytes, fallback: str = "image/jpeg") -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def _decode_base64_image(value: str) -> tuple[str, str] | None:
    image_ref = "".join(value.split())
    if len(image_ref) < 64:
        return None

    image_ref += "=" * (-len(image_ref) % 4)
    try:
        content = base64.b64decode(image_ref, validate=True)
    except (binascii.Error, ValueError):
        return None

    return image_ref, _infer_mime_type(content)


def _data_url_from_image_url(url: str) -> str | None:
    image = get_image_by_url(url)
    if not image:
        return None

    path = Path(image.storage_path)
    if not path.exists():
        return None

    mime_type = image.content_type or _mime_type_for_path(path)
    image_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{image_base64}"


def _image_url_block(reference: str, mime_type: str = "image/jpeg") -> dict[str, Any]:
    image_ref = reference.strip()
    local_data_url = _data_url_from_image_url(image_ref)
    if local_data_url:
        image_ref = local_data_url
    elif image_ref.startswith("data:"):
        image_ref = image_ref
    elif urlparse(image_ref).scheme not in {"http", "https"}:
        decoded = _decode_base64_image(image_ref)
        if decoded:
            image_base64, inferred_mime_type = decoded
            image_ref = f"data:{inferred_mime_type or mime_type};base64,{image_base64}"

    return {
        "type": "image_url",
        "image_url": {
            "url": image_ref,
            "detail": "auto",
        },
    }



def _message_text(message: str | list[dict[str, Any]]) -> str:
    if isinstance(message, str):
        return message.strip()
    return json.dumps(message, ensure_ascii=False)


def handle_chat(
    session_id: str,
    message: str | list[dict[str, Any]],
) -> ChatResponse:
    thread_id = session_id
    content_text = _message_text(message)

    append_message(
        session_id=session_id,
        role="user",
        content_text=content_text,
    )
    assistant_message = run_chef_agent(message=content_text, thread_id=thread_id)

    append_message(
        session_id=session_id,
        role="assistant",
        content_text=assistant_message,
    )

    return ChatResponse(
        status="chat",
        session_id=session_id,
        message=assistant_message,
    )
