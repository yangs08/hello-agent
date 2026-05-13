"""
API 路由定义
"""

from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from features.critique import critique_service
from features.multi_turn import multi_turn_service

router = APIRouter()


@router.post("/critique")
async def critique_image(file: UploadFile = File(...)):
    """
    点评图片
    
    Args:
        file: 上传的图片文件
    
    Returns:
        点评结果
    """
    result = await critique_service.critique_image(file)
    return {"success": True, "data": result}


@router.post("/chat")
async def chat_with_image(
    file: UploadFile = File(...),
    question: str = Form(...),
    session_id: str = Form(default="default")
):
    """
    与图片进行对话
    
    Args:
        file: 上传的图片文件
        question: 用户问题
        session_id: 会话 ID
    
    Returns:
        对话结果
    """
    result = await multi_turn_service.chat_with_image(
        file=file,
        question=question,
        session_id=session_id
    )
    return {"success": True, "data": result}


@router.post("/chat/clear")
async def clear_chat_history(session_id: str = Form(default="default")):
    """
    清除对话历史
    
    Args:
        session_id: 会话 ID
    
    Returns:
        操作结果
    """
    multi_turn_service.clear_history(session_id)
    return {"success": True, "message": "History cleared"}
