from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

RESOURCE_DIR = Path(os.getenv("AI_CHEF_RESOURCE_DIR", BASE_DIR / "resource"))
UPLOAD_DIR = RESOURCE_DIR / "uploads"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
VISION_MODEL = os.getenv("AI_CHEF_VISION_MODEL", "minicpm-v")
TEXT_MODEL = os.getenv("AI_CHEF_TEXT_MODEL", "qwen2.5:7b")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_SEARCH_URL = os.getenv("TAVILY_SEARCH_URL", "https://api.tavily.com/search")
LANGSMITH_TRACING = os.getenv(
    "LANGSMITH_TRACING",
    os.getenv("LANGSMITH_TRACKING", os.getenv("LANGCHAIN_TRACING_V2", "false")),
)
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-chef")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_CALLBACKS_BACKGROUND = os.getenv("LANGCHAIN_CALLBACKS_BACKGROUND", "true")
DB_PATH = Path(os.getenv("AI_CHEF_DB_PATH", RESOURCE_DIR / "ai_chef.sqlite3"))
CHECKPOINT_DB_PATH = Path(
    os.getenv("AI_CHEF_CHECKPOINT_DB_PATH", RESOURCE_DIR / "langgraph_checkpoints.sqlite3")
)

MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
