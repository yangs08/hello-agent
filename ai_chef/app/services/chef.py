from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import OLLAMA_API_KEY, OLLAMA_BASE_URL, TEXT_MODEL, VISION_MODEL
from app.db import append_message, load_memory, recent_context, save_memory
from app.schemas import ChatResponse, ChefMemory, InputAssessment
from app.services.image import image_to_base64

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)


def _chat_completion(messages: list[dict[str, Any]], max_tokens: int = 1024) -> str:
    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


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


def _json_from_model(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end >= start:
        stripped = stripped[start : end + 1]
    return json.loads(stripped)


def assess_input(message: str, image_analysis: str | None) -> InputAssessment:
    if not message and not image_analysis:
        return InputAssessment(
            status="needs_rephrase",
            reason="No text or image was provided.",
            normalized_request="",
        )

    prompt = (
        "你是 AI 私厨的输入路由器。请只输出 JSON，不要 Markdown。\n"
        "status 只能是：\n"
        "- chef_ready: 用户给了食材、菜品、饮食目标、口味偏好、烹饪限制，或上传了可用食物/食材图片，可以给私厨建议。\n"
        "- chat: 普通寒暄、询问能力、补充偏好、问厨房相关常识，但暂时不需要完整菜谱。\n"
        "- needs_rephrase: 内容和私厨/饮食无关，或图片/文字无法判断食材，需要引导重新描述或重传。\n"
        "输出格式：{\"status\":\"...\",\"reason\":\"...\",\"normalized_request\":\"...\"}"
    )
    user_payload = {
        "message": message,
        "image_analysis": image_analysis,
    }

    try:
        raw = _chat_completion(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            max_tokens=300,
        )
        return InputAssessment.model_validate(_json_from_model(raw))
    except Exception:
        if image_analysis and "不适合" not in image_analysis:
            return InputAssessment(
                status="chef_ready",
                reason="Image analysis appears to contain food context.",
                normalized_request=message or "根据图片食材给出私厨建议",
            )
        cooking_keywords = ("吃", "菜", "食材", "做饭", "晚餐", "午餐", "早餐", "减脂", "过敏", "口味")
        if any(keyword in message for keyword in cooking_keywords):
            return InputAssessment(
                status="chef_ready",
                reason="Text contains cooking intent.",
                normalized_request=message,
            )
        return InputAssessment(
            status="chat",
            reason="Fallback to ordinary conversation.",
            normalized_request=message,
        )


def _update_memory(
    memory: ChefMemory,
    message: str,
    image_analysis: str | None,
    assistant_message: str,
) -> ChefMemory:
    prompt = (
        "你是 AI 私厨的记忆整理器。基于当前记忆和这一轮对话，更新长期记忆。"
        "只保留对后续私厨建议有帮助的信息：口味偏好、忌口、过敏、厨具、近期食材。"
        "每个列表最多 8 条，去重，输出 JSON，字段为 preferences/dislikes/allergies/equipment/recent_ingredients。"
    )
    payload = {
        "current_memory": memory.model_dump(),
        "user_message": message,
        "image_analysis": image_analysis,
        "assistant_message": assistant_message,
    }

    try:
        raw = _chat_completion(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=600,
        )
        return ChefMemory.model_validate(_json_from_model(raw))
    except Exception:
        return memory


def _guide_rephrase(assessment: InputAssessment) -> str:
    return (
        "我现在还没拿到足够的私厨信息。你可以告诉我现有食材、人数、口味、忌口、目标"
        "（比如减脂/快手/儿童餐），或者重新上传一张清楚的食材/菜品图片。"
        f"\n\n判断原因：{assessment.reason}"
    )


def _answer_chat(message: str, memory: ChefMemory, history: list[dict[str, str]]) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个温和、专业的 AI 私厨。用户可以普通聊天，但你的能力边界围绕饮食、烹饪、食材管理。"
                "如果还不能给菜谱，就自然追问 1-2 个关键问题。"
                f"用户长期记忆：{memory.model_dump_json(ensure_ascii=False)}"
            ),
        },
        *history,
        {"role": "user", "content": message or "用户上传了图片，但暂时只需要普通回应。"},
    ]
    return _chat_completion(messages, max_tokens=900)


def _suggest_recipe(
    request: str,
    memory: ChefMemory,
    history: list[dict[str, str]],
    image_analysis: str | None,
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是一位资深私厨。只有在用户输入足够且与饮食烹饪相关时才给建议。"
                "输出要包括：判断依据、推荐菜品、用料、步骤、替换方案、注意事项。"
                "结合用户记忆，但不要编造没有出现过的过敏或忌口。"
                f"用户长期记忆：{memory.model_dump_json(ensure_ascii=False)}"
            ),
        },
        *history,
        {
            "role": "user",
            "content": (
                f"用户请求：{request}\n"
                f"图片分析：{image_analysis or '无'}\n"
                "请给出本轮私厨建议。"
            ),
        },
    ]
    return _chat_completion(messages, max_tokens=1800)


def handle_chat(
    user_id: str,
    message: str,
    image_analysis: str | None,
) -> ChatResponse:
    memory = load_memory(user_id)
    history = recent_context(user_id)
    assessment = assess_input(message, image_analysis)

    append_message(
        user_id=user_id,
        role="user",
        content=message or "[uploaded image]",
        image_analysis=image_analysis,
    )

    if assessment.status == "needs_rephrase":
        assistant_message = _guide_rephrase(assessment)
        recipe = None
    elif assessment.status == "chat":
        assistant_message = _answer_chat(message, memory, history)
        recipe = None
    else:
        recipe = _suggest_recipe(
            request=assessment.normalized_request or message or "根据图片食材给出私厨建议",
            memory=memory,
            history=history,
            image_analysis=image_analysis,
        )
        assistant_message = recipe

    memory = _update_memory(memory, message, image_analysis, assistant_message)
    save_memory(user_id, memory)
    append_message(user_id=user_id, role="assistant", content=assistant_message)

    return ChatResponse(
        status=assessment.status,
        message=assistant_message,
        memory=memory,
        ingredients_analysis=image_analysis,
        recipe_suggestion=recipe,
    )
