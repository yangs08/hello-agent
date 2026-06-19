from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import create_image, get_image, list_messages, list_sessions
from app.schemas import ChatResponse, MessageRecord, SessionSummary
from app.services.chef import analyze_ingredients, handle_chat
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


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form("default"),
    message: str = Form(""),
    file: UploadFile | None = File(None),
) -> ChatResponse:
    image_analysis: str | None = None
    image_id: int | None = None
    cleaned_message = message.strip()
    cleaned_session_id = session_id.strip() or "default"

    if file and file.filename:
        content = await file.read()
        validate_image(file.filename, content)
        try:
            image_analysis = analyze_ingredients(content)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Vision model error: {exc}") from exc
        storage_path = save_upload(file.filename, content)
        image = create_image(
            session_id=cleaned_session_id,
            filename=file.filename,
            content_type=file.content_type,
            storage_path=str(storage_path),
            size_bytes=len(content),
        )
        image_id = image.id

    return handle_chat(
        session_id=cleaned_session_id,
        message=cleaned_message,
        image_analysis=image_analysis,
        image_id=image_id,
    )


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)) -> dict[str, str | None]:
    response = await chat(
        session_id="default",
        message="请根据这张图片给我私厨建议",
        file=file,
    )
    return {
        "ingredients_analysis": response.ingredients_analysis,
        "recipe_suggestion": response.recipe_suggestion or response.message,
    }
