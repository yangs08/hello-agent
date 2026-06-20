from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from app.agents.chef import run_chef_agent, stream_chef_agent
from app.db import append_message
from app.schemas import ChatResponse


def _message_text(message: str | list[dict[str, Any]]) -> str:
    if isinstance(message, str):
        return message.strip()
    return json.dumps(message, ensure_ascii=False)


def _normalize_message_part(part: dict[str, Any]) -> str | None:
    part_type = part.get("type")
    if part_type == "text":
        text = str(part.get("text") or "").strip()
        return text or None
    if part_type == "image":
        reference = str(part.get("url") or part.get("data") or "").strip()
        return (
            f"图片 URL: {reference}\n需要理解这张图片时，请调用 analyze_image 工具。"
            if reference
            else None
        )
    if part_type == "image_url":
        image_url = part.get("image_url")
        if isinstance(image_url, dict):
            reference = str(image_url.get("url") or "").strip()
        else:
            reference = str(image_url or "").strip()
        return (
            f"图片 URL: {reference}\n需要理解这张图片时，请调用 analyze_image 工具。"
            if reference
            else None
        )
    return json.dumps(part, ensure_ascii=False)


def _normalize_agent_message(message: str | list[dict[str, Any]]) -> str:
    if isinstance(message, str):
        return message.strip()

    parts = [
        normalized_part
        for part in message
        if (normalized_part := _normalize_message_part(part)) is not None
    ]
    return "\n\n".join(parts).strip()


def handle_chat(
    session_id: str,
    message: str | list[dict[str, Any]],
) -> ChatResponse:
    thread_id = session_id
    content_text = _message_text(message)
    agent_message = _normalize_agent_message(message)

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


def stream_chat(
    session_id: str,
    message: str | list[dict[str, Any]],
) -> Iterator[str]:
    thread_id = session_id
    content_text = _message_text(message)
    agent_message = _normalize_agent_message(message)
    chunks: list[str] = []

    append_message(
        session_id=session_id,
        role="user",
        content_text=content_text,
    )

    for chunk in stream_chef_agent(message=agent_message, thread_id=thread_id):
        chunks.append(chunk)
        yield chunk

    append_message(
        session_id=session_id,
        role="assistant",
        content_text="".join(chunks),
    )
