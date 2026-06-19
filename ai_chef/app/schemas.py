from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatResponse(BaseModel):
    status: Literal["chat", "needs_rephrase"]
    session_id: str
    message: str
    url: str | None = None
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
