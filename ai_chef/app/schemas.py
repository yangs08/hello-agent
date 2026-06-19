from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InputAssessment(BaseModel):
    status: Literal["chef_ready", "chat", "needs_rephrase"]
    reason: str = Field(description="Why this input landed in the status.")
    normalized_request: str = Field(description="Cleaned user intent.")


class ChefMemory(BaseModel):
    preferences: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    recent_ingredients: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    status: Literal["chef_ready", "chat", "needs_rephrase"]
    message: str
    memory: ChefMemory
    ingredients_analysis: str | None = None
    recipe_suggestion: str | None = None
