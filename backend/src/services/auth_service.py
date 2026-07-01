"""
认证服务（Authentication Service）

提供所有认证相关的业务逻辑：
- 用户注册（验证码验证 + 密码哈希）
- 用户登录（密码验证 + Token 生成）
- 退出登录（删除 Refresh Token）
- Token 刷新（验证 Refresh Token + 生成新 Token）

这是 API 层和数据层之间的桥梁，处理核心业务逻辑
"""

from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from src.models.user import User, RefreshToken, VerificationCode
from src.schemas.auth import RegisterRequest, LoginRequest
from src.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)


def register_user(db: Session, register_data: RegisterRequest) -> User:
    """
    用户注册

    流程：
    1. 检查邮箱是否已注册
    2. 验证验证码是否有效
    3. 哈希密码
    4. 创建用户
    5. 标记验证码为已使用

    参数：
        db: 数据库会话
        register_data: 注册请求数据

    返回：
        User: 创建的用户对象

    异常：
        HTTPException 400: 邮箱已注册、验证码无效
    """
    # 1. 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == register_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    # 2. 查找有效的验证码
    verification_code = db.query(VerificationCode).filter(
        VerificationCode.email == register_data.email,
        VerificationCode.code == register_data.verification_code
    ).first()

    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码无效"
        )

    # 3. 检查验证码是否有效（未过期、未使用）
    if not verification_code.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码无效或已过期"
        )

    # 4. 标记验证码为已使用
    verification_code.used = True
    db.commit()

    # 5. 哈希密码
    password_hash = get_password_hash(register_data.password)

    # 6. 创建用户
    new_user = User(
        name=register_data.name,
        email=register_data.email,
        phone=register_data.phone,
        password_hash=password_hash,
        is_verified=True,  # 邮箱已验证（通过验证码）
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def login_user(db: Session, login_data: LoginRequest) -> tuple[User, str, str]:
    """
    用户登录

    流程：
    1. 查找用户
    2. 验证密码
    3. 生成 Access Token
    4. 生成 Refresh Token 并存储到数据库
    5. 删除用户的所有旧 Refresh Token（单设备登录）
    6. 更新最后登录时间

    参数：
        db: 数据库会话
        login_data: 登录请求数据

    返回：
        tuple: (用户对象, Access Token, Refresh Token)

    异常：
        HTTPException 401: 邮箱或密码错误
    """
    # 1. 查找用户
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 2. 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 3. 检查账户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # 4. 生成 Access Token
    access_token = create_access_token(data={
        "user_id": str(user.id),
        "email": user.email
    })

    # 5. 删除用户的所有旧 Refresh Token（单设备登录）
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()

    # 6. 生成新的 Refresh Token
    refresh_token_str = create_refresh_token(data={"user_id": str(user.id)})

    # 7. 存储 Refresh Token 到数据库
    refresh_token_obj = RefreshToken(
        user_id=str(user.id),
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=7)  # 7 天有效期
    )
    db.add(refresh_token_obj)

    # 8. 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()

    return user, access_token, refresh_token_str


def logout_user(db: Session, user_id: str) -> None:
    """
    用户退出登录

    删除用户的所有 Refresh Token

    参数：
        db: 数据库会话
        user_id: 用户 ID
    """
    # 删除该用户的所有 Refresh Token
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()


def refresh_token(db: Session, refresh_token_str: str) -> tuple[str, str]:
    """
    刷新 Access Token

    流程：
    1. 验证 Refresh Token 签名和过期时间
    2. 从数据库查找 Refresh Token（防伪造）
    3. 检查 Token 是否有效（未过期、未使用）
    4. 生成新的 Access Token
    5. 生成新的 Refresh Token（Token 轮换）
    6. 标记旧 Refresh Token 为已使用
    7. 存储新的 Refresh Token

    参数：
        db: 数据库会话
        refresh_token_str: Refresh Token 字符串

    返回：
        tuple: (新的 Access Token, 新的 Refresh Token)

    异常：
        HTTPException 401: Token 无效或过期
    """
    # 1. 验证 Refresh Token 签名和类型
    payload = verify_refresh_token(refresh_token_str)
    user_id = payload.get("user_id")

    # 2. 从数据库查找 Refresh Token
    token_obj = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token_str,
        RefreshToken.user_id == user_id
    ).first()

    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 无效"
        )

    # 3. 检查 Token 是否过期
    if not token_obj.is_valid():
        # 删除过期的 Token
        db.delete(token_obj)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 已过期"
        )

    # 4. 生成新的 Access Token
    new_access_token = create_access_token(data={"user_id": user_id})

    # 5. 生成新的 Refresh Token
    new_refresh_token_str = create_refresh_token(data={"user_id": user_id})

    # 6. 删除旧的 Refresh Token
    db.delete(token_obj)

    # 7. 存储新的 Refresh Token
    new_refresh_token_obj = RefreshToken(
        user_id=user_id,
        token=new_refresh_token_str,
        expires_at=datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(new_refresh_token_obj)
    db.commit()

    return new_access_token, new_refresh_token_str
