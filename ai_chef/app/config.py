from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
VISION_MODEL = os.getenv("AI_CHEF_VISION_MODEL", "minicpm-v")
TEXT_MODEL = os.getenv("AI_CHEF_TEXT_MODEL", "qwen2.5:7b")
DB_PATH = Path(os.getenv("AI_CHEF_DB_PATH", BASE_DIR / "ai_chef.sqlite3"))

MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
