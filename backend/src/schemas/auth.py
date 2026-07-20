"""
认证相关的 Pydantic Schemas

定义所有认证 API 的请求和响应数据结构：
- 登录请求/响应
- 注册请求/响应
- Token 刷新请求/响应
- 验证码请求/响应

Pydantic 会自动验证数据：
- 类型检查（email 必须是字符串）
- 格式验证（EmailValidator 验证邮箱格式）
- 长度限制（密码至少 6 个字符）
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


# ==================== 请求 Schemas ====================

class LoginRequest(BaseModel):
    """
    登录请求

    用户使用邮箱和密码登录

    属性：
        email: 用户邮箱（必须符合邮箱格式）
        password: 用户密码（至少 6 个字符）
        remember_me: 是否记住我（勾选则 Refresh Token 有效期延长到 30 天，默认 False）
    """
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="用户密码")
    remember_me: bool = Field(default=False, description="是否记住我（延长登录态有效期）")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "zhangsan@example.com",
                "password": "password123",
                "remember_me": False
            }
        }


class RegisterRequest(BaseModel):
    """
    注册请求

    新用户注册账户

    属性：
        name: 用户姓名（2-50 个字符）
        email: 用户邮箱（必须符合邮箱格式）
        phone: 手机号（可选，符合 E.164 格式）
        password: 密码（6-100 个字符）
        verification_code: 邮箱验证码（6 位数字）
    """
    name: str = Field(..., min_length=2, max_length=50, description="用户姓名")
    email: EmailStr = Field(..., description="用户邮箱")
    phone: Optional[str] = Field(None, description="手机号（可选）")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    verification_code: str = Field(..., pattern=r"^\d{6}$", description="验证码（6位数字）")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """
        验证手机号格式（如果提供）

        支持格式：
        - +8613800138000（E.164 标准）
        - 13800138000（中国手机号）
        """
        if v is None:
            return v

        # 移除所有空格和短横线
        phone = v.replace(" ", "").replace("-", "")

        # 检查是否为数字
        if not phone.isdigit():
            raise ValueError("手机号必须为纯数字")

        # 检查长度（11 位或 12 位，含国际区号）
        if len(phone) not in [11, 12, 13]:
            raise ValueError("手机号长度无效")

        return phone

    class Config:
        json_schema_extra = {
            "example": {
                "name": "张三",
                "email": "zhangsan@example.com",
                "phone": "+8613800138000",
                "password": "password123",
                "verification_code": "123456"
            }
        }


class SendCodeRequest(BaseModel):
    """
    发送验证码请求

    请求发送验证码到指定邮箱

    属性：
        email: 目标邮箱
    """
    email: EmailStr = Field(..., description="目标邮箱")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "zhangsan@example.com"
            }
        }


class RefreshTokenRequest(BaseModel):
    """
    Token 刷新请求

    使用 Refresh Token 获取新的 Access Token

    属性：
        refresh_token: Refresh Token 字符串
    """
    refresh_token: str = Field(..., description="Refresh Token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ==================== 响应 Schemas ====================

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


class TokenResponse(BaseModel):
    """
    Token 响应

    登录/注册成功后返回的 Token 信息

    属性：
        access_token: Access Token（短期，15 分钟）
        refresh_token: Refresh Token（长期，7 天）
        token_type: Token 类型（默认 "Bearer"）
    """
    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    token_type: str = Field(default="bearer", description="Token 类型")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class LoginResponse(BaseModel):
    """
    登录/注册成功响应

    返回用户信息和 Token

    属性：
        user: 用户信息
        token: Access Token
        refresh_token: Refresh Token
    """
    user: UserResponse = Field(..., description="用户信息")
    token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "张三",
                    "email": "zhangsan@example.com",
                    "created_at": "2025-01-01T00:00:00Z"
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """
    Token 刷新响应

    刷新成功后返回新的 Token

    属性：
        token: 新的 Access Token
        refresh_token: 新的 Refresh Token
    """
    token: str = Field(..., description="新的 Access Token")
    refresh_token: str = Field(..., description="新的 Refresh Token")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
