from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.db import init_db, load_memory
from app.schemas import ChatResponse, ChefMemory
from app.services.chef import analyze_ingredients, handle_chat
from app.services.image import validate_image

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/memory/{user_id}", response_model=ChefMemory)
def get_memory(user_id: str) -> ChefMemory:
    init_db()
    return load_memory(user_id)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    user_id: str = Form("default"),
    message: str = Form(""),
    file: UploadFile | None = File(None),
) -> ChatResponse:
    init_db()
    image_analysis: str | None = None
    cleaned_message = message.strip()

    if file and file.filename:
        content = await file.read()
        validate_image(file.filename, content)
        try:
            image_analysis = analyze_ingredients(content)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Vision model error: {exc}") from exc

    return handle_chat(
        user_id=user_id,
        message=cleaned_message,
        image_analysis=image_analysis,
    )


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)) -> dict[str, str | None]:
    response = await chat(user_id="default", message="请根据这张图片给我私厨建议", file=file)
    return {
        "ingredients_analysis": response.ingredients_analysis,
        "recipe_suggestion": response.recipe_suggestion or response.message,
    }
