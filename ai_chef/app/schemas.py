from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatResponse(BaseModel):
    status: Literal["chat", "needs_rephrase"]
    session_id: str
    message: str
    image_id: int | None = None
    ingredients_analysis: str | None = None
    recipe_suggestion: str | None = None


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    last_message_at: str


class ImageAsset(BaseModel):
    id: int
    session_id: str
    filename: str
    content_type: str | None = None
    storage_path: str
    size_bytes: int
    created_at: str


class MessageRecord(BaseModel):
    id: int
    session_id: str
    role: str
    content_type: str
    content_text: str
    image_id: int | None = None
    image_filename: str | None = None
    image_content_type: str | None = None
    image_storage_path: str | None = None
    image_analysis: str | None = None
    created_at: str
