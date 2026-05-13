"""
多轮对话功能模块
"""

import base64
from typing import Optional
from fastapi import UploadFile

from core.chains import chat_chain


class MultiTurnService:
    """多轮对话服务"""
    
    def __init__(self):
        self.chain = chat_chain
        self.conversation_history = {}  # 简单的内存存储
    
    async def chat_with_image(
        self,
        file: UploadFile,
        question: str,
        session_id: str = "default"
    ) -> dict:
        """
        与图片进行对话
        
        Args:
            file: 上传的图片文件
            question: 用户问题
            session_id: 会话 ID
        
        Returns:
            对话结果
        """
        # 读取图片并转为 base64
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # 获取历史记录
        history = self.conversation_history.get(session_id, [])
        
        # 调用对话链
        response = self.chain.run(image_base64, question, history)
        
        # 更新历史记录
        history.append({
            "user": question,
            "assistant": response
        })
        self.conversation_history[session_id] = history
        
        return {
            "response": response,
            "session_id": session_id,
            "history_length": len(history)
        }
    
    def clear_history(self, session_id: str = "default"):
        """清除对话历史"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]


# 全局服务实例
multi_turn_service = MultiTurnService()
