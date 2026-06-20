from __future__ import annotations

from typing import Any

from app.agents.chef.agent import chef_agent


def run_chef_agent(
    message: str | list[dict[str, Any]],
    thread_id: str,
) -> str:
    config = {
        "configurable": {"thread_id": thread_id},
        "run_name": "ai_chef.chat",
        "tags": ["ai-chef", "chat"],
        "metadata": {"session_id": thread_id},
    }
    response = chef_agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = response.get("messages", [])
    if not messages:
        return ""
    return str(messages[-1].content or "")
