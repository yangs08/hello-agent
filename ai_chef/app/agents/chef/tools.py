from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from langchain_core.tools import tool

from app.agents.chef.models import vision_model
from app.config import TAVILY_API_KEY, TAVILY_SEARCH_URL
from app.db import get_image_by_url, update_image_analysis_by_url
from app.schemas import VideoSearchResponse, VideoSearchResult
from app.services.image import image_to_base64

_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _mime_type_for_path(path: Path) -> str:
    return _MIME_BY_EXTENSION.get(path.suffix.lower(), "image/jpeg")


def _infer_mime_type(content: bytes, fallback: str = "image/jpeg") -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def _decode_base64_image(reference: str) -> tuple[bytes, str] | None:
    image_ref = reference.strip()
    mime_type = "image/jpeg"

    if image_ref.startswith("data:"):
        header, separator, payload = image_ref.partition(",")
        if not separator or ";base64" not in header:
            return None
        mime_type = header.removeprefix("data:").split(";", 1)[0] or mime_type
    else:
        payload = "".join(image_ref.split())
        if len(payload) < 64:
            return None
        payload += "=" * (-len(payload) % 4)

    try:
        content = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None

    return content, _infer_mime_type(content, fallback=mime_type)


def analyze_ingredients(content: bytes, mime_type: str = "image/jpeg") -> str:
    image_base64 = image_to_base64(content)
    response = vision_model.invoke(
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
                            "url": f"data:{mime_type};base64,{image_base64}",
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
    """Analyze a food or ingredient image by uploaded URL, external URL, data URL, or base64.
    Args:
        url: The uploaded URL, external image URL, data:image base64 URL, or raw base64 image.
    """
    return analyze_image_reference(url)


def analyze_image_reference(url: str) -> str:
    decoded_image = _decode_base64_image(url)
    if decoded_image:
        content, mime_type = decoded_image
        return analyze_ingredients(content, mime_type=mime_type)

    parsed_url = urlparse(url)
    local_url = parsed_url.path if parsed_url.scheme in {"http", "https"} else url
    image = get_image_by_url(url) or get_image_by_url(local_url)

    if image:
        path = Path(image.storage_path)
        if path.exists():
            content = path.read_bytes()
            mime_type = _mime_type_for_path(path)
        elif urlparse(image.url).scheme in {"http", "https"}:
            try:
                with urlopen(image.url, timeout=20) as response:
                    content = response.read()
                    mime_type = response.headers.get_content_type() or image.content_type or "image/jpeg"
            except (HTTPError, URLError, TimeoutError) as exc:
                return f"无法读取图片 URL：{image.url}。错误：{exc}"
        else:
            return f"图片文件不存在：{url}。请让用户重新上传。"
    elif parsed_url.scheme in {"http", "https"}:
        try:
            with urlopen(url, timeout=20) as response:
                content = response.read()
                mime_type = response.headers.get_content_type() or "image/jpeg"
        except (HTTPError, URLError, TimeoutError) as exc:
            return f"无法读取图片 URL：{url}。错误：{exc}"
    else:
        return "未找到图片，且输入不是有效的 base64 图片。请让用户重新上传图片，或提供有效的图片 URL/base64。"

    analysis = analyze_ingredients(content, mime_type=mime_type)
    if image:
        update_image_analysis_by_url(image.url, analysis)
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
