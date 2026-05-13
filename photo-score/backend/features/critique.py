"""
单张点评功能模块
"""

import base64
from typing import Optional
from fastapi import UploadFile

from core.chains import critique_chain


class CritiqueService:
    """点评服务"""
    
    def __init__(self):
        self.chain = critique_chain
    
    async def critique_image(self, file: UploadFile) -> dict:
        """
        点评图片
        
        Args:
            file: 上传的图片文件
        
        Returns:
            点评结果
        """
        # 读取图片并转为 base64
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # 调用点评链
        result = self.chain.run(image_base64)
        
        return result
    
    def critique_image_base64(self, image_base64: str) -> dict:
        """
        点评图片（直接传入 base64）
        
        Args:
            image_base64: 图片的 base64 编码
        
        Returns:
            点评结果
        """
        return self.chain.run(image_base64)


# 全局服务实例
critique_service = CritiqueService()
