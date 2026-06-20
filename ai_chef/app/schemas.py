from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str | list[dict[str, Any]]

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("message cannot be empty")
            return value

        if not value:
            raise ValueError("message cannot be empty")

        for part in value:
            part_type = part.get("type")
            if part_type == "text" and str(part.get("text") or "").strip():
                return value
            if part_type == "image" and (part.get("url") or part.get("data")):
                return value
            if part_type == "image_url" and part.get("image_url"):
                return value

        raise ValueError("message must include text or image content")


class ChatResponse(BaseModel):
    status: Literal["chat"]
    session_id: str
    message: str


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
    url: str
    size_bytes: int
    created_at: str


class UploadResponse(BaseModel):
    url: str
    image: ImageAsset


class MessageRecord(BaseModel):
    id: int
    session_id: str
    role: str
    content_type: str
    content_text: str
    url: str | None = None
    image_filename: str | None = None
    image_content_type: str | None = None
    image_storage_path: str | None = None
    image_analysis: str | None = None
    created_at: str


class VideoSearchResult(BaseModel):
    title: str | None = None
    url: str | None = None
    summary: str | None = None
    source_score: float | None = None


class VideoSearchResponse(BaseModel):
    status: Literal["ok", "missing_api_key", "search_error", "no_results"]
    query: str
    message: str | None = None
    results: list[VideoSearchResult] = []
