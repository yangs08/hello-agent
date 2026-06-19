from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import create_image, get_image, list_messages, list_sessions
from app.schemas import ChatResponse, MessageRecord, SessionSummary, UploadResponse
from app.services.chef import handle_chat
from app.services.image import validate_image
from app.services.storage import save_upload

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sessions", response_model=list[SessionSummary])
def get_sessions() -> list[SessionSummary]:
    return list_sessions()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRecord])
def get_session_messages(session_id: str) -> list[MessageRecord]:
    return list_messages(session_id)


@router.get("/images/{image_id}")
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
    )


@router.post("/uploads", response_model=UploadResponse)
async def upload_image(
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
    return UploadResponse(url=image.url, image=image)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form("default"),
    message: str = Form(""),
    url: str = Form(""),
) -> ChatResponse:
    cleaned_message = message.strip()
    cleaned_url = url.strip() or None
    cleaned_session_id = session_id.strip() or "default"

    return handle_chat(
        session_id=cleaned_session_id,
        message=cleaned_message,
        url=cleaned_url,
    )


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)) -> dict[str, str | None]:
    upload = await upload_image(session_id="default", file=file)
    response = await chat(
        session_id="default",
        message="请根据这张图片给我私厨建议",
        url=upload.url,
    )
    return {
        "ingredients_analysis": response.ingredients_analysis,
        "recipe_suggestion": response.recipe_suggestion or response.message,
    }
