from __future__ import annotations

import json
from contextlib import ExitStack

from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from openai import OpenAI

from app.config import CHECKPOINT_DB_PATH, OLLAMA_API_KEY, OLLAMA_BASE_URL, TEXT_MODEL, VISION_MODEL
from app.db import append_message
from app.schemas import ChatResponse
from app.services.image import image_to_base64

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
langchain_model = ChatOpenAI(
    model=TEXT_MODEL,
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY,
    temperature=0.3,
    max_tokens=1800,
)
_checkpoint_stack = ExitStack()
CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
checkpointer = _checkpoint_stack.enter_context(
    SqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
)
checkpointer.setup()
summarization_middleware = SummarizationMiddleware(
    model=langchain_model,
    trigger=("messages", 10),
    keep=("tokens", 3000),
)
chef_agent = create_agent(
    model=langchain_model,
    tools=[],
    system_prompt=(
        "你是一个温和、专业的 AI 私厨。用户可以普通对话，也可以基于食材、菜品图片、口味和目标获得私厨建议。"
        "每轮先结合当前消息和会话记忆判断用户意图："
        "普通聊天就自然回应；内容与饮食烹饪无关或图片/文字不足以判断时，引导用户重新描述或重传清楚的食材图片；"
        "如果输入足够，给出清晰、可执行的私厨建议，包括判断依据、推荐菜品、用料、步骤、替换方案和注意事项。"
    ),
    middleware=[summarization_middleware],
    checkpointer=checkpointer,
)


def analyze_ingredients(content: bytes) -> str:
    image_base64 = image_to_base64(content)
    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "你是私厨助手的视觉识别模块。请判断图片是否包含可烹饪食材、菜品、饮品或厨房场景。"
                            "如果不是，请明确说明不适合作为私厨建议依据。"
                            "如果是，请列出可见食材、状态、份量粗估、可能的限制，并说明适合的烹饪方向。"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "auto",
                        },
                    },
                ],
            },
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


def _guide_rephrase() -> str:
    return (
        "我现在还没拿到足够的私厨信息。你可以告诉我现有食材、人数、口味、忌口、目标"
        "（比如减脂/快手/儿童餐），或者重新上传一张清楚的食材/菜品图片。"
    )


def _run_agent(
    message: str,
    thread_id: str,
) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    response = chef_agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    messages = response.get("messages", [])
    if not messages:
        return ""
    return str(messages[-1].content or "")


def handle_chat(
    session_id: str,
    message: str,
    image_analysis: str | None,
    image_id: int | None = None,
) -> ChatResponse:
    thread_id = session_id
    has_input = bool(message or image_analysis or image_id)
    content_type = "mixed" if message and image_id else "image" if image_id else "text"

    append_message(
        session_id=session_id,
        role="user",
        content_text=message,
        content_type=content_type,
        image_id=image_id,
        image_analysis=image_analysis,
    )

    if has_input:
        agent_message = json.dumps(
            {
                "message": message,
                "image_analysis": image_analysis,
            },
            ensure_ascii=False,
        )
        assistant_message = _run_agent(message=agent_message, thread_id=thread_id)
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
        image_id=image_id,
        ingredients_analysis=image_analysis,
        recipe_suggestion=None,
    )
