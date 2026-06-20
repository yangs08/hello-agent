from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.agents.chef.agent import chef_agent


def _agent_config(thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": "ai_chef.chat",
        "tags": ["ai-chef", "chat"],
        "metadata": {"session_id": thread_id},
    }


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "".join(text_parts)
    return ""


def run_chef_agent(
    message: str | list[dict[str, Any]],
    thread_id: str,
) -> str:
    config = _agent_config(thread_id)
    response = chef_agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = response.get("messages", [])
    if not messages:
        return ""
    return str(messages[-1].content or "")


def stream_chef_agent(
        message: str | list[dict[str, Any]],
        thread_id: str,
) -> Iterator[str]:
    config = _agent_config(thread_id)
    for chunk, _metadata in chef_agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="messages",
    ):

        try:
            yield _chunk_text(chunk)
        except Exception:
            yield "信息检索失败，请试试手动输入实物"
