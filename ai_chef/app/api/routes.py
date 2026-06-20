from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse

from app.db import create_image, get_image, list_messages, list_sessions
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ImageRegisterRequest,
    MessageRecord,
    OssUploadTokenRequest,
    OssUploadTokenResponse,
    SessionSummary,
    UploadResponse,
)
from app.services.chef import handle_chat, stream_chat
from app.services.image import validate_image
from app.services.storage import create_oss_upload_token, save_upload

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
def get_image_file(image_id: int) -> Response:
    image = get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    path = Path(image.storage_path)
    if not path.exists():
        parsed = urlparse(image.url)
        if parsed.scheme in {"http", "https"}:
            return RedirectResponse(image.url)
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
    stored = save_upload(file.filename or "image.jpg", content, file.content_type)
    image = create_image(
        session_id=session_id.strip() or "default",
        filename=file.filename or Path(stored.storage_path).name,
        content_type=file.content_type,
        storage_path=stored.storage_path,
        size_bytes=len(content),
        url=stored.url,
    )
    upload_url = image.url
    if urlparse(upload_url).scheme not in {"http", "https"}:
        upload_url = str(request.url_for("get_image_file", image_id=image.id))
    return UploadResponse(url=upload_url, image=image)


@router.post("/oss/upload-token", response_model=OssUploadTokenResponse)
async def oss_upload_token(request: OssUploadTokenRequest) -> OssUploadTokenResponse:
    try:
        token = create_oss_upload_token(request.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return OssUploadTokenResponse(
        access_key_id=token.access_key_id,
        security_token=token.security_token,
        expiration=token.expiration,
        policy=token.policy,
        signature=token.signature,
        bucket=token.bucket,
        endpoint=token.endpoint,
        object_key=token.object_key,
        url=token.url,
    )


@router.post("/images/register", response_model=UploadResponse)
async def register_image(request: ImageRegisterRequest) -> UploadResponse:
    image = create_image(
        session_id=request.session_id.strip() or "default",
        filename=request.filename,
        content_type=request.content_type,
        storage_path=request.storage_path,
        size_bytes=request.size_bytes,
        url=request.url,
    )
    return UploadResponse(url=image.url, image=image)


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
