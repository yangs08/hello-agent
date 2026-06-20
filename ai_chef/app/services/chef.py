from __future__ import annotations

import json

from app.agents.chef import run_chef_agent
from app.db import append_message
from app.schemas import ChatResponse


def _guide_rephrase() -> str:
    return (
        "我现在还没拿到足够的私厨信息。你可以告诉我现有食材、人数、口味、忌口、目标"
        "（比如减脂/快手/儿童餐），或者重新上传一张清楚的食材/菜品图片。"
    )


def handle_chat(
    session_id: str,
    message: str,
    url: str | None = None,
) -> ChatResponse:
    thread_id = session_id
    has_input = bool(message or url)
    content_type = "mixed" if message and url else "image" if url else "text"

    append_message(
        session_id=session_id,
        role="user",
        content_text=message,
        content_type=content_type,
        url=url,
    )

    if has_input:
        agent_message = json.dumps(
            {
                "message": message,
                "url": url,
            },
            ensure_ascii=False,
        )
        assistant_message = run_chef_agent(message=agent_message, thread_id=thread_id)
    else:
        assistant_message = _guide_rephrase()

    append_message(
        session_id=session_id,
        role="assistant",
        content_text=assistant_message,
    )

    return ChatResponse(
        status="chat" if has_input else "needs_rephrase",
        session_id=session_id,
        message=assistant_message,
        url=url,
        ingredients_analysis=None,
        recipe_suggestion=None,
    )
