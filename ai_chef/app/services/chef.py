from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import (
    CHECKPOINT_DB_PATH,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    TAVILY_API_KEY,
    TAVILY_SEARCH_URL,
    TEXT_MODEL,
    VISION_MODEL,
)
from app.db import append_message, get_image_by_url, update_image_analysis_by_url
from app.schemas import ChatResponse, VideoSearchResponse, VideoSearchResult
from app.services.image import image_to_base64

client = init_chat_model(model=VISION_MODEL, model_provider="openai", base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
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


def analyze_ingredients(content: bytes) -> str:
    image_base64 = image_to_base64(content)
    response = client.invoke(
        [
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
        ]
    )
    return str(response.content or "")


@tool()
def analyze_image(url: str) -> str:
    """Analyze an uploaded food or ingredient image by URL when visual context is needed.
    Args:
        url: The uploaded URL of the image.
    """
    image = get_image_by_url(url)
    parsed_url = urlparse(url)

    if image:
        path = Path(image.storage_path)
        if not path.exists():
            return f"图片文件不存在：{url}。请让用户重新上传。"
        content = path.read_bytes()
    elif parsed_url.scheme in {"http", "https"}:
        try:
            with urlopen(url, timeout=20) as response:
                content = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            return f"无法读取图片 URL：{url}。错误：{exc}"
    else:
        return f"未找到图片 URL：{url}。请让用户重新上传。"

    analysis = analyze_ingredients(content)
    if image:
        update_image_analysis_by_url(url, analysis)
    return analysis


@tool()
def web_search(ingredients: str, goal: str = "") -> str:
    """Search Tavily for cooking video candidates by ingredients and return structured results for the agent to rank."""
    if not TAVILY_API_KEY:
        return VideoSearchResponse(
            status="missing_api_key",
            query="",
            message="TAVILY_API_KEY 未配置，无法搜索视频。请根据已知食材自行评估是否能做料理；如果食材不足或不可食用，直接说明不行。",
        ).model_dump_json(ensure_ascii=False)

    query = f"{ingredients} {goal} 做法 视频 料理 教程 recipe cooking video".strip()
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": 8,
        "include_answer": False,
        "include_raw_content": False,
    }
    request = Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        return VideoSearchResponse(
            status="search_error",
            query=query,
            message=f"Tavily 搜索失败：{exc}。请根据已知食材自行评估是否能做料理；如果食材不足或不可食用，直接说明不行。",
        ).model_dump_json(ensure_ascii=False)

    results = data.get("results") or []
    if not results:
        return VideoSearchResponse(
            status="no_results",
            query=query,
            message="没有搜索到相关料理视频。请根据已知食材判断是否仍能做料理；如果食材不足、不可食用或无法形成菜品，直接说明不行。",
        ).model_dump_json(ensure_ascii=False)

    return VideoSearchResponse(
        status="ok",
        query=query,
        results=[
            VideoSearchResult(
                title=item.get("title"),
                url=item.get("url"),
                summary=item.get("content"),
                source_score=item.get("score"),
            )
            for item in results[:8]
        ],
    ).model_dump_json(ensure_ascii=False)


chef_agent = create_agent(
    model=langchain_model,
    tools=[analyze_image, web_search],
    system_prompt=(
        "你是一个温和、专业的 AI 私厨。用户可以普通对话，也可以基于食材、菜品图片、口味和目标获得私厨建议。"
        "每轮先结合当前消息和会话记忆判断用户意图："
        "普通聊天就自然回应；内容与饮食烹饪无关或图片/文字不足以判断时，引导用户重新描述或重传清楚的食材图片；"
        "如果用户上传了图片，当前消息会提供图片 URL。需要理解图片时调用 analyze_image 工具，"
        "不要要求用户重新描述你可以用工具查看的图片。"
        "当你已经知道可用食材并准备给料理建议时，先调用 web_search 搜索相关料理；"
        "web_search 只返回候选结果，不会替你排序；你必须自己评估候选与食材、难度、步骤清晰度和用户目标的匹配程度，"
        "按可行性排序后只取前 3 个推荐给用户，并附上引用地址 URL。"
        "如果 web_search 没有结果或搜索失败，你要基于已知食材评估是否仍能做料理；"
        "如果食材不足、不可食用或无法形成菜品，直接说不行并说明原因。"
        "如果输入足够，给出清晰、可执行的私厨建议，包括判断依据、推荐菜品、用料、步骤、替换方案、注意事项和图片参考。"
    ),
    middleware=[summarization_middleware],
    checkpointer=checkpointer,
)


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
        url=url,
        ingredients_analysis=None,
        recipe_suggestion=None,
    )
