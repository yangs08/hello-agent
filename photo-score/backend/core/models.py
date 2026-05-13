"""
模型管理模块
统一管理 Ollama 本地模型
"""

from typing import Optional
from langchain_ollama import ChatOllama


class ModelManager:
    """Ollama 模型管理器"""
    
    def __init__(
        self,
        model_name: str = "minicpm-v",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        num_ctx: int = 4096
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.num_ctx = num_ctx
        self._model = None
    
    @property
    def model(self) -> ChatOllama:
        """获取模型实例（懒加载）"""
        if self._model is None:
            self._model = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
                num_ctx=self.num_ctx
            )
        return self._model
    
    def invoke(self, messages: list, **kwargs) -> str:
        """调用模型"""
        response = self.model.invoke(messages, **kwargs)
        return response.content


# 全局模型管理器实例
model_manager = ModelManager()
