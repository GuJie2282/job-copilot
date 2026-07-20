"""
认证 API 路由

提供所有认证相关的 HTTP 端点：
- POST /auth/register - 用户注册
- POST /auth/login - 用户登录
- POST /auth/send-code - 发送验证码
- POST /auth/logout - 退出登录
- POST /auth/refresh - 刷新 Token

所有端点遵循 RESTful 规范
"""

from fastapi import APIRouter, Depends, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Any

from src.models.base import get_db
from src.models.user import User
from src.core.deps import get_current_user
from src.core.limiter import limiter, SEND_CODE_RATE_LIMIT
from src.core.security import create_access_token, create_refresh_token
from src.services.code_service import send_verification_code as send_code_to_email  # 别名避免命名冲突
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SendCodeRequest,
    RefreshTokenRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenResponse,
)
from src.services.auth_service import (
    register_user,
    login_user,
    logout_user,
    refresh_token,
)
from src.services.code_service import send_verification_code

# 创建路由器
auth_router = APIRouter()

# HTTP Bearer 认证（用于受保护的端点）
security = HTTPBearer()


@auth_router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="用户通过邮箱和验证码注册账户，成功后返回用户信息和 Token",
)
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    用户注册

    流程：
    1. 验证验证码
    2. 创建用户
    3. 生成 Token
    4. 返回用户信息和 Token

    参数：
        register_data: 注册数据（姓名、邮箱、密码、验证码）

    返回：
        LoginResponse: 用户信息 + Access Token + Refresh Token

    异常：
        400: 邮箱已注册、验证码无效
    """
    # 注册用户（服务层已生成Token）
    user, access_token, refresh_token_str = register_user(db, register_data)

    # 返回响应
    return LoginResponse(user=user, token=access_token, refresh_token=refresh_token_str)


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description="用户通过邮箱和密码登录，成功后返回用户信息和 Token",
)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    用户登录

    流程：
    1. 验证邮箱和密码
    2. 生成 Token
    3. 返回用户信息和 Token

    参数：
        login_data: 登录数据（邮箱、密码）
        request: FastAPI请求对象

    返回：
        LoginResponse: 用户信息 + Access Token + Refresh Token

    异常：
        401: 邮箱或密码错误
        403: 账户已被禁用
    """
    # 登录用户（传递request以获取IP地址）
    user, access_token, refresh_token_str = login_user(db, login_data, request)

    # 返回响应
    return LoginResponse(user=user, token=access_token, refresh_token=refresh_token_str)


@auth_router.post(
    "/send-code",
    status_code=status.HTTP_200_OK,
    summary="发送验证码",
    description="发送 6 位数字验证码到指定邮箱（开发环境打印到控制台）"
)
@limiter.limit(SEND_CODE_RATE_LIMIT)  # 限流：每分钟 5 次
async def send_verification_code(
    request: Request,  # slowapi 限流需要 request 对象
    request_data: SendCodeRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    发送验证码

    参数：
        request_data: 请求数据（邮箱）

    返回：
        {"message": "验证码已发送"}

    注意：
        - 同一邮箱 5 分钟内只能发送一次
        - 验证码有效期 5 分钟
    """
    print(f"[DEBUG] 收到验证码请求，邮箱: {request_data.email}")  # 调试日志

    # 发送验证码
    send_code_to_email(db, request_data.email)  # 使用别名调用 service 函数

    print(f"[DEBUG] 验证码已发送到: {request_data.email}")  # 调试日志
    return {"message": "验证码已发送"}


@auth_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="退出登录",
    description="用户退出登录，删除服务器的 Refresh Token"
)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    退出登录

    删除用户的所有 Refresh Token

    参数：
        current_user: 当前登录用户（自动注入）

    返回：
        {"message": "退出登录成功"}
    """
    # 退出登录
    logout_user(db, str(current_user.id))

    return {"message": "退出登录成功"}


@auth_router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="刷新 Token",
    description="使用 Refresh Token 获取新的 Access Token"
)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    刷新 Token

    参数：
        refresh_data: Refresh Token
        request: FastAPI请求对象

    返回：
        RefreshTokenResponse: 新的 Access Token + 新的 Refresh Token

    异常：
        401: Token 无效或过期

    注意：
        - 刷新后生成新的 Refresh Token（旧 Token 失效）
        - Token 轮换机制提高安全性
    """
    # 刷新 Token（传递request以获取IP地址）
    new_access_token, new_refresh_token = refresh_token(
        db, refresh_data.refresh_token, request
    )

    return RefreshTokenResponse(token=new_access_token, refresh_token=new_refresh_token)

