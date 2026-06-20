from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

from app.config import OLLAMA_API_KEY, OLLAMA_BASE_URL, TEXT_MODEL, VISION_MODEL
from app.observability import configure_langsmith

configure_langsmith()

vision_model = init_chat_model(
    model=VISION_MODEL,
    model_provider="openai",
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY,
)
chat_model = ChatOpenAI(
    model=TEXT_MODEL,
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY,
    temperature=0.3,
    max_tokens=1800,
)
