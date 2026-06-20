from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.db import create_image, get_image, list_messages, list_sessions
from app.schemas import ChatRequest, ChatResponse, MessageRecord, SessionSummary, UploadResponse
from app.services.chef import handle_chat, stream_chat
from app.services.image import validate_image
from app.services.storage import save_upload

router = APIRouter()


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sessions", response_model=list[SessionSummary])
def get_sessions() -> list[SessionSummary]:
    return list_sessions()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRecord])
def get_session_messages(session_id: str) -> list[MessageRecord]:
    return list_messages(session_id)


@router.api_route("/images/{image_id}", methods=["GET", "HEAD"])
def get_image_file(image_id: int) -> FileResponse:
    image = get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    path = Path(image.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(
        path,
        media_type=image.content_type,
        filename=image.filename,
        content_disposition_type="inline",
    )


@router.post("/uploads", response_model=UploadResponse)
async def upload_image(
    request: Request,
    session_id: str = Form("default"),
    file: UploadFile = File(...),
) -> UploadResponse:
    content = await file.read()
    validate_image(file.filename or "image.jpg", content)
    storage_path = save_upload(file.filename or "image.jpg", content)
    image = create_image(
        session_id=session_id.strip() or "default",
        filename=file.filename or storage_path.name,
        content_type=file.content_type,
        storage_path=str(storage_path),
        size_bytes=len(content),
    )
    absolute_url = str(request.url_for("get_image_file", image_id=image.id))
    return UploadResponse(url=absolute_url, image=image)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return handle_chat(
        session_id=request.session_id.strip() or "default",
        message=request.message,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id = request.session_id.strip() or "default"

    def events() -> Iterator[str]:
        try:
            for chunk in stream_chat(session_id=session_id, message=request.message):
                yield _sse_event("delta", {"text": chunk})
            yield _sse_event("done", {"status": "ok"})
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc) or "私厨暂时没有回应"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/analyze")
async def analyze_image(request: Request, file: UploadFile = File(...)) -> dict[str, str | None]:
    upload = await upload_image(request=request, session_id="default", file=file)
    response = await chat(ChatRequest(
        session_id="default",
        message=[
            {"type": "text", "text": "请根据这张图片给我私厨建议"},
            {"type": "image", "url": upload.url},
        ],
    ))
    return {
        "recipe_suggestion": response.message,
    }
