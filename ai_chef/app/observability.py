from __future__ import annotations

import os

from app.config import (
    LANGCHAIN_CALLBACKS_BACKGROUND,
    LANGSMITH_API_KEY,
    LANGSMITH_ENDPOINT,
    LANGSMITH_PROJECT,
    LANGSMITH_TRACING,
)


def configure_langsmith() -> None:
    """Configure LangSmith tracing from environment-backed app settings."""
    tracing_enabled = LANGSMITH_TRACING.lower() in {"1", "true", "yes", "on"}
    os.environ["LANGSMITH_TRACING"] = "true" if tracing_enabled else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if tracing_enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = LANGCHAIN_CALLBACKS_BACKGROUND

    if LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    if LANGSMITH_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT
