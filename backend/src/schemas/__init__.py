"""
Pydantic Schemas 包

导出所有请求和响应的数据结构
"""

from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SendCodeRequest,
    RefreshTokenRequest,
    UserResponse,
    TokenResponse,
    LoginResponse,
    RefreshTokenResponse,
)
from src.schemas.user import UserResponse as UserResp

__all__ = [
    # 认证请求
    "LoginRequest",
    "RegisterRequest",
    "SendCodeRequest",
    "RefreshTokenRequest",
    # 认证响应
    "UserResponse",
    "TokenResponse",
    "LoginResponse",
    "RefreshTokenResponse",
    # 用户响应
    "UserResp",
]
