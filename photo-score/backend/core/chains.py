"""
LangChain 链模块
定义点评链和对话链
"""

import json
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage

from core.models import model_manager
from core.prompts import CRITIQUE_PROMPT, CHAT_SYSTEM_PROMPT, CHAT_USER_PROMPT


class CritiqueChain:
    """摄影点评链"""
    
    def __init__(self):
        self.model = model_manager
    
    def run(self, image_base64: str) -> dict:
        """
        执行点评
        
        Args:
            image_base64: 图片的 base64 编码
        
        Returns:
            点评结果字典
        """
        message = HumanMessage(content=[
            {"type": "text", "text": CRITIQUE_PROMPT},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ])
        
        response = self.model.invoke([message])
        
        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            # 如果解析失败，返回原始文本
            return {
                "error": "Failed to parse response",
                "raw_response": response
            }


class ChatChain:
    """多轮对话链"""
    
    def __init__(self):
        self.model = model_manager
    
    def run(self, image_base64: str, question: str, history: list = None) -> str:
        """
        执行对话
        
        Args:
            image_base64: 图片的 base64 编码
            question: 用户问题
            history: 对话历史
        
        Returns:
            AI 回复
        """
        messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT)
        ]
        
        # 添加对话历史
        if history:
            for msg in history:
                messages.append(HumanMessage(content=msg["user"]))
                messages.append(SystemMessage(content=msg["assistant"]))
        
        # 添加当前问题和图片
        user_message = HumanMessage(content=[
            {"type": "text", "text": CHAT_USER_PROMPT.format(question=question)},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ])
        messages.append(user_message)
        
        response = self.model.invoke(messages)
        return response


# 全局链实例
critique_chain = CritiqueChain()
chat_chain = ChatChain()
