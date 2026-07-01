"""
用户相关的 Pydantic Schemas

定义用户信息的响应结构
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    """
    用户信息响应

    返回用户的基本信息（不包含敏感信息）

    属性：
        id: 用户 ID（UUID）
        name: 用户姓名
        email: 用户邮箱
        phone: 手机号（可选）
        avatar: 头像 URL（可选）
        created_at: 创建时间
    """
    id: str = Field(..., description="用户 ID")
    name: str = Field(..., description="用户姓名")
    email: EmailStr = Field(..., description="用户邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    avatar: Optional[str] = Field(None, description="头像 URL")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True  # 允许从 ORM 模型创建
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "张三",
                "email": "zhangsan@example.com",
                "phone": "+8613800138000",
                "avatar": "https://example.com/avatar.jpg",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }
