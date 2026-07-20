"""
认证服务（Authentication Service）

提供所有认证相关的业务逻辑：
- 用户注册（验证码验证 + 密码哈希）
- 用户登录（密码验证 + Token 生成）
- 退出登录（删除 Refresh Token）
- Token 刷新（验证 Refresh Token + 生成新 Token）

这是 API 层和数据层之间的桥梁，处理核心业务逻辑
"""

import time
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, Tuple

from src.models.user import User, RefreshToken, VerificationCode
from src.schemas.auth import RegisterRequest, LoginRequest
from src.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REMEMBER_ME_REFRESH_TOKEN_DAYS,
)
from src.core.error_handler import ErrorCode, ErrorResponse
from src.core.masking import mask_email, mask_phone, mask_token, mask_code

logger = logging.getLogger(__name__)


def register_user(db: Session, register_data: RegisterRequest) -> Tuple[User, str, str]:
    """
    用户注册（使用数据库事务保护）

    流程：
    1. 验证码事务：验证 + 标记已使用
    2. 用户创建事务：创建用户记录
    3. Token生成：生成Access Token和Refresh Token（非事务）

    参数：
        db: 数据库会话
        register_data: 注册请求数据

    返回：
        Tuple[User, str, str]: (用户对象, Access Token, Refresh Token)

    异常：
        HTTPException 400: 邮箱已注册、验证码无效、密码过长
        HTTPException 500: 系统内部错误
    """
    start_time = time.time()

    logger.info(
        "user_register_start",
        extra={"email": mask_email(register_data.email), "name": register_data.name},
    )

    try:
        # ========== 阶段1: 验证码事务 ==========
        with db.begin():
            logger.debug("verify_code_start", email=mask_email(register_data.email))

            verification_code = db.query(VerificationCode).filter(
                VerificationCode.email == register_data.email,
                VerificationCode.code == register_data.verification_code,
            ).first()

            if not verification_code:
                logger.warning(
                    "code_not_found",
                    extra={"email": mask_email(register_data.email)},
                )
                error_response = ErrorResponse.create(code=ErrorCode.CODE_INVALID)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            # 检查验证码状态
            if verification_code.used:
                logger.warning(
                    "code_already_used",
                    extra={
                        "email": mask_email(register_data.email),
                        "code": mask_code(verification_code.code),
                    },
                )
                error_response = ErrorResponse.create(code=ErrorCode.CODE_ALREADY_USED)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            if datetime.utcnow() > verification_code.expires_at:
                logger.warning(
                    "code_expired",
                    extra={
                        "email": mask_email(register_data.email),
                        "code": mask_code(verification_code.code),
                    },
                )
                error_response = ErrorResponse.create(code=ErrorCode.CODE_EXPIRED)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            # 标记验证码为已使用
            verification_code.used = True
            db.flush()

            logger.debug(
                "code_verified",
                extra={"code": mask_code(verification_code.code)},
            )

        # ========== 阶段2: 用户创建事务 ==========
        with db.begin():
            logger.debug("create_user_start", email=mask_email(register_data.email))

            # 检查邮箱是否已存在（双重检查）
            existing_user = (
                db.query(User).filter(User.email == register_data.email).first()
            )
            if existing_user:
                logger.warning(
                    "email_exists",
                    extra={"email": mask_email(register_data.email)},
                )
                error_response = ErrorResponse.create(code=ErrorCode.AUTH_EMAIL_EXISTS)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            # 验证密码长度
            password = register_data.password
            password_bytes = len(password.encode("utf-8"))
            logger.debug(
                "validate_password",
                extra={"length": len(password), "bytes": password_bytes},
            )

            if password_bytes > 72:
                logger.warning(
                    "password_too_long",
                    extra={"length": len(password), "bytes": password_bytes},
                )
                error_response = ErrorResponse.create(
                    code=ErrorCode.VALID_PASSWORD_TOO_LONG
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            if len(password) < 6:
                logger.warning(
                    "password_too_short",
                    extra={"length": len(password)},
                )
                error_response = ErrorResponse.create(
                    code=ErrorCode.VALID_PASSWORD_TOO_SHORT
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )

            # 哈希密码
            password_hash = get_password_hash(password)

            # 创建用户
            new_user = User(
                name=register_data.name,
                email=register_data.email,
                phone=register_data.phone,
                password_hash=password_hash,
                is_verified=True,  # 邮箱已验证（通过验证码）
                is_active=True,
            )
            db.add(new_user)
            db.flush()

            logger.debug(
                "user_created",
                extra={"user_id": str(new_user.id), "email": mask_email(new_user.email)},
            )

        # ========== 阶段3: Token生成（非事务）==========
        try:
            logger.debug("generate_token_start", extra={"user_id": str(new_user.id)})

            access_token = create_access_token(
                data={"user_id": str(new_user.id), "email": new_user.email}
            )
            refresh_token_str = create_refresh_token(data={"user_id": str(new_user.id)})

            # 存储 Refresh Token（独立事务）
            with db.begin():
                # 注册不勾选"记住我"，用默认有效期（与 create_refresh_token 默认值保持一致）
                refresh_token_obj = RefreshToken(
                    user_id=str(new_user.id),
                    token=refresh_token_str,
                    expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                )
                db.add(refresh_token_obj)

            logger.debug(
                "token_generated",
                extra={"user_id": str(new.id)},
            )

        except Exception as e:
            # Token生成失败，但用户已创建（可重新登录获取Token）
            logger.error(
                "token_generation_failed",
                extra={"user_id": str(new_user.id), "error": str(e)},
                exc_info=True,
            )
            error_response = ErrorResponse.create(
                code=ErrorCode.SYSTEM_INTERNAL_ERROR,
                override_message="系统错误，请重新登录",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_response.to_dict(),
            )

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "user_register_success",
            extra={
                "user_id": str(new_user.id),
                "email": mask_email(new_user.email),
                "duration_ms": duration_ms,
            },
        )

        return new_user, access_token, refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "user_register_error",
            extra={"email": mask_email(register_data.email), "error": str(e)},
            exc_info=True,
        )
        error_response = ErrorResponse.create(code=ErrorCode.SYSTEM_INTERNAL_ERROR)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.to_dict(),
        )


def login_user(db: Session, login_data: LoginRequest, request: Optional[Request] = None) -> Tuple[User, str, str]:
    """
    用户登录（使用数据库事务保护）

    流程：
    1. 用户认证（查询 + 密码验证 + 状态检查）
    2. Token管理（删除旧Token + 创建新Token）
    3. 更新最后登录时间
    所有数据库操作在单个事务内完成

    参数：
        db: 数据库会话
        login_data: 登录请求数据
        request: FastAPI请求对象（用于获取IP地址）

    返回：
        Tuple[User, str, str]: (用户对象, Access Token, Refresh Token)

    异常：
        HTTPException 401: 邮箱或密码错误
        HTTPException 403: 账户已被禁用
        HTTPException 500: 系统内部错误
    """
    start_time = time.time()

    # 获取客户端IP（request.client 在测试/代理场景可能为 None，需防御性处理）
    client_ip = request.client.host if request and request.client else "unknown"

    logger.info(
        "user_login_attempt",
        extra={"email": mask_email(login_data.email), "ip": client_ip},
    )

    try:
        # ========== 事务：用户认证 + Token管理 ==========
        with db.begin():
            # 1. 查找用户
            logger.debug("find_user", extra={"email": mask_email(login_data.email)})
            user = db.query(User).filter(User.email == login_data.email).first()

            if not user:
                logger.warning(
                    "user_login_failed",
                    extra={
                        "email": mask_email(login_data.email),
                        "reason": "user_not_found",
                        "ip": client_ip,
                    },
                )
                # 不区分用户不存在和密码错误（安全考虑）
                error_response = ErrorResponse.create(code=ErrorCode.AUTH_INVALID_CREDENTIALS)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_response.to_dict(),
                )

            # 2. 验证密码
            if not verify_password(login_data.password, user.password_hash):
                logger.warning(
                    "user_login_failed",
                    extra={
                        "user_id": str(user.id),
                        "email": mask_email(user.email),
                        "reason": "invalid_password",
                        "ip": client_ip,
                    },
                )
                error_response = ErrorResponse.create(code=ErrorCode.AUTH_INVALID_CREDENTIALS)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_response.to_dict(),
                )

            # 3. 检查账户状态
            if not user.is_active:
                logger.warning(
                    "user_login_disabled",
                    extra={
                        "user_id": str(user.id),
                        "email": mask_email(user.email),
                        "ip": client_ip,
                    },
                )
                error_response = ErrorResponse.create(code=ErrorCode.AUTH_ACCOUNT_DISABLED)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_response.to_dict(),
                )

            # 4. 删除用户的所有旧 Refresh Token（单设备登录）
            logger.debug(
                "delete_old_tokens",
                extra={"user_id": str(user.id)},
            )
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()

            # 5. 创建新的 Refresh Token（按"记住我"动态设置有效期）
            #    勾选记住我：30 天长期免登录；不勾选：1 天临时登录
            #    面试讲点：登录态有效期按用户选择动态调整，平衡安全与便利
            logger.debug(
                "create_refresh_token",
                extra={"user_id": str(user.id), "remember_me": login_data.remember_me},
            )
            refresh_days = (
                REMEMBER_ME_REFRESH_TOKEN_DAYS
                if login_data.remember_me
                else REFRESH_TOKEN_EXPIRE_DAYS
            )
            refresh_token_str = create_refresh_token(
                data={"user_id": str(user.id)},
                expires_days=refresh_days,
            )
            refresh_token_obj = RefreshToken(
                user_id=str(user.id),
                token=refresh_token_str,
                expires_at=datetime.utcnow() + timedelta(days=refresh_days),
            )
            db.add(refresh_token_obj)

            # 6. 更新最后登录时间
            logger.debug(
                "update_last_login",
                extra={"user_id": str(user.id)},
            )
            user.last_login = datetime.utcnow()

        # ========== 非事务：生成 Access Token ==========
        access_token = create_access_token(data={"user_id": str(user.id), "email": user.email})

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "user_login_success",
            extra={
                "user_id": str(user.id),
                "email": mask_email(user.email),
                "ip": client_ip,
                "duration_ms": duration_ms,
            },
        )

        return user, access_token, refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "user_login_error",
            extra={"email": mask_email(login_data.email), "error": str(e)},
            exc_info=True,
        )
        error_response = ErrorResponse.create(code=ErrorCode.SYSTEM_INTERNAL_ERROR)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.to_dict(),
        )


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


def refresh_token(db: Session, refresh_token_str: str, request: Optional[Request] = None) -> Tuple[str, str]:
    """
    刷新 Access Token（使用数据库事务保护）

    流程：
    1. 验证 Refresh Token 签名（事务外）
    2. Token轮换事务：验证 + 删除旧Token + 创建新Token
    3. 生成 Access Token（事务外）

    参数：
        db: 数据库会话
        refresh_token_str: Refresh Token 字符串
        request: FastAPI请求对象（用于获取IP地址）

    返回：
        Tuple[str, str]: (新的 Access Token, 新的 Refresh Token)

    异常：
        HTTPException 401: Token 无效或过期
        HTTPException 500: 系统内部错误
    """
    start_time = time.time()

    # 获取客户端IP（request.client 在测试/代理场景可能为 None，需防御性处理）
    client_ip = request.client.host if request and request.client else "unknown"

    try:
        # ========== 验证Token签名（事务外）==========
        logger.debug("verify_token_signature", extra={"ip": client_ip})
        payload = verify_refresh_token(refresh_token_str)
        user_id = payload.get("user_id")

        logger.info(
            "token_refresh_attempt",
            extra={"user_id": user_id, "ip": client_ip},
        )

        # ========== 事务：Token轮换 ==========
        with db.begin():
            # 1. 查询旧Token
            logger.debug("find_old_token", extra={"user_id": user_id})
            token_obj = (
                db.query(RefreshToken)
                .filter(RefreshToken.token == refresh_token_str, RefreshToken.user_id == user_id)
                .first()
            )

            if not token_obj:
                logger.warning(
                    "token_refresh_failed",
                    extra={"user_id": user_id, "reason": "token_not_found", "ip": client_ip},
                )
                error_response = ErrorResponse.create(code=ErrorCode.TOKEN_INVALID)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_response.to_dict(),
                )

            # 2. 检查Token是否过期
            if not token_obj.is_valid():
                logger.warning(
                    "token_refresh_failed",
                    extra={"user_id": user_id, "reason": "token_expired", "ip": client_ip},
                )
                # 删除过期Token
                db.delete(token_obj)
                error_response = ErrorResponse.create(code=ErrorCode.TOKEN_EXPIRED)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_response.to_dict(),
                )

            # 3. 删除旧Token
            logger.debug("delete_old_token", extra={"user_id": user_id})
            db.delete(token_obj)

            # 4. 创建新Token
            logger.debug("create_new_token", extra={"user_id": user_id})
            new_refresh_token_str = create_refresh_token(data={"user_id": user_id})
            # 刷新时不保留"记住我"标志（payload 未存储），统一用默认有效期
            # 如需刷新后仍保持长期登录，可将 remember_me 写入 token payload 后在此读取
            new_refresh_token_obj = RefreshToken(
                user_id=user_id,
                token=new_refresh_token_str,
                expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            )
            db.add(new_refresh_token_obj)

        # ========== 非事务：生成 Access Token ==========
        new_access_token = create_access_token(data={"user_id": user_id})

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "token_refresh_success",
            extra={
                "user_id": user_id,
                "old_token": mask_token(refresh_token_str),
                "new_token": mask_token(new_refresh_token_str),
                "duration_ms": duration_ms,
            },
        )

        return new_access_token, new_refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "token_refresh_error",
            extra={"error": str(e)},
            exc_info=True,
        )
        error_response = ErrorResponse.create(code=ErrorCode.SYSTEM_INTERNAL_ERROR)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.to_dict(),
        )


# ==================== 辅助函数 ====================


# ==================== 脱敏函数导入 ====================
# 已从 src.core.masking 导入：mask_email, mask_phone, mask_token, mask_code
