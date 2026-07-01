"""
FastAPI 依赖注入（Dependencies）

提供可重用的依赖注入函数：
- get_current_user: 从 Token 中提取当前用户
- get_db: 获取数据库会话

使用方式（在路由中）：
    @app.get("/users/me")
    async def read_users_me(current_user: User = Depends(get_current_user)):
        return current_user
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from src.models.base import get_db
from src.models.user import User
from src.core.security import verify_access_token

# HTTP Bearer 认证方案
# 自动从 Authorization 头提取 Token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    从 Access Token 中提取当前用户

    这是受保护端点的核心依赖注入函数：
    1. 从 Authorization 头提取 Token
    2. 验证 Token 有效性
    3. 从 Token 中提取 user_id
    4. 从数据库查询用户信息
    5. 返回用户对象

    参数：
        credentials: HTTP Bearer 认证凭证（自动注入）
        db: 数据库会话（自动注入）

    返回：
        User: 当前登录的用户对象

    异常：
        HTTPException 401: Token 无效、过期或用户不存在

    使用示例：
        @app.get("/users/me")
        async def read_users_me(current_user: User = Depends(get_current_user)):
            return current_user

        @app.post("/api/jobs/apply")
        async def apply_job(
            job_id: int,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            # current_user 就是当前登录的用户
            pass
    """
    # 提取 Token 字符串
    token = credentials.credentials

    # 验证 Token 并提取 Payload
    payload = verify_access_token(token)

    # 从 Payload 中提取 user_id
    user_id: Optional[str] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户信息",
        )

    # 从数据库查询用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前激活用户（额外检查邮箱验证状态）

    与 get_current_user 类似，但额外要求邮箱已验证

    使用场景：
        - 需要邮箱验证的功能（如发布 JD、申请面试等）
        - 不允许未验证用户访问的端点

    返回：
        User: 当前登录且邮箱已验证的用户

    异常：
        HTTPException 403: 邮箱未验证
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱未验证，请先验证邮箱",
        )
    return current_user


# 重新导出 get_db（从 models/base.py）
__all__ = ["get_current_user", "get_current_active_user", "get_db"]
