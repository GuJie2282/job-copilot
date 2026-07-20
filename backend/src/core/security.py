"""
核心安全功能

提供：
1. 密码哈希和验证（使用 passlib + bcrypt）
2. JWT Token 生成和验证（使用 python-jose）
3. Token 数据提取和验证

安全原则：
- 密码永不明文存储
- JWT Secret 从环境变量读取
- Token 包含最小必要信息
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os
import uuid

logger = logging.getLogger(__name__)

# ==================== 密码哈希配置 ====================

# 创建密码哈希上下文
# schemes=["bcrypt"]: 使用 bcrypt 算法（成本因子 12）
# deprecated="auto": 自动标记旧算法为已弃用
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    将用户输入的明文密码与数据库中的哈希密码进行比对

    参数：
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码

    返回：
        bool: 密码是否匹配

    示例：
        is_valid = verify_password("user_password", "$2b$12$...")
    """
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("password_verified", extra={"success": result})
        return result
    except Exception as e:
        logger.error("password_verify_error", extra={"error": str(e)}, exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    将明文密码转换为 bcrypt 哈希值

    参数：
        password: 明文密码

    返回：
        str: bcrypt 哈希字符串（格式：$2b$12$...）

    示例：
        hash = get_password_hash("user_password")
        # 输出：$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36...
    """
    return pwd_context.hash(password)


# ==================== JWT 配置 ====================

# 从环境变量读取 JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production-min-32-chars")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
# 不勾选"记住我"时 Refresh Token 的有效期（默认 1 天，临时登录）
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "1"))
# 勾选"记住我"时 Refresh Token 的有效期（默认 30 天，长期免登录）
REMEMBER_ME_REFRESH_TOKEN_DAYS = int(os.getenv("REMEMBER_ME_REFRESH_TOKEN_DAYS", "30"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 Access Token

    生成短期有效的 JWT Token（默认 15 分钟）

    参数：
        data: 要编码到 Token 中的数据（通常包含 user_id 和 email）
        expires_delta: 自定义过期时间（可选，默认使用配置值）

    返回：
        str: JWT Token 字符串

    Token 结构：
        Header: {"alg": "HS256", "typ": "JWT"}
        Payload: {"user_id": "...", "email": "...", "exp": ..., "iat": ...}
        Signature: HMAC-SHA256(Header + Payload, SECRET_KEY)

    示例：
        token = create_access_token(
            data={"user_id": str(user.id), "email": user.email}
        )
    """
    # 复制数据，避免修改原始字典
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 添加过期时间和签发时间
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"  # Token 类型标识
    })

    # 生成 JWT Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.debug("access_token_created", extra={"user_id": data.get("user_id", "unknown")})

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_days: Optional[int] = None) -> str:
    """
    创建 Refresh Token

    生成长期有效的 JWT Token，用于刷新 Access Token。
    有效期可按"记住我"动态调整：

    参数：
        data: 要编码到 Token 中的数据（包含 user_id 和 token_id）
        expires_days: 自定义有效期（天数）。
                      - 不传：用默认 REFRESH_TOKEN_EXPIRE_DAYS（不记住我，1 天）
                      - 传 30：勾选了"记住我"，30 天免登录

    返回：
        str: JWT Token 字符串

    注意：
        Refresh Token 应该存储在数据库中，以便撤销
    """
    # 复制数据
    to_encode = data.copy()

    # 生成唯一的 Token ID（用于数据库查找和撤销）
    token_id = str(uuid.uuid4())
    to_encode["token_id"] = token_id

    # 设置过期时间（按传入的天数，或默认值）
    days = expires_days if expires_days is not None else REFRESH_TOKEN_EXPIRE_DAYS
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"  # Token 类型标识
    })

    # 生成 JWT Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.debug("refresh_token_created", extra={"user_id": data.get("user_id", "unknown"), "token_id": token_id, "expires_days": days})

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    解码并验证 JWT Token

    验证 Token 签名和过期时间，提取 Payload 数据

    参数：
        token: JWT Token 字符串

    返回：
        Dict[str, Any]: Token Payload 数据

    异常：
        HTTPException: Token 无效或过期时抛出 401 错误

    示例：
        try:
            payload = decode_token(token)
            user_id = payload.get("user_id")
        except HTTPException:
            # Token 无效
            pass
    """
    try:
        # 解码 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        # Token 无效或过期
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 无效或已过期: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    验证 Access Token 并提取用户信息

    专门用于验证 Access Token，检查 Token 类型

    参数：
        token: JWT Token 字符串

    返回：
        Dict[str, Any]: Token Payload，包含 user_id、email 等

    异常：
        HTTPException: Token 无效、过期或类型错误时抛出 401
    """
    # 解码 Token
    payload = decode_token(token)

    # 检查 Token 类型
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误，期望 Access Token",
        )

    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    验证 Refresh Token 并提取用户信息

    专门用于验证 Refresh Token，检查 Token 类型

    参数：
        token: JWT Token 字符串

    返回：
        Dict[str, Any]: Token Payload，包含 user_id、token_id 等

    异常：
        HTTPException: Token 无效、过期或类型错误时抛出 401
    """
    # 解码 Token
    payload = decode_token(token)

    # 检查 Token 类型
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误，期望 Refresh Token",
        )

    return payload
