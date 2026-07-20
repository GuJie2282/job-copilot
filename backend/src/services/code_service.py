"""
验证码服务（Verification Code Service）

提供验证码相关的业务逻辑：
- 生成验证码（6 位随机数字）
- 发送验证码（开发环境打印到控制台）
- 验证验证码（检查有效期、未使用）
- 清理过期验证码
"""

import random
import os
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.user import VerificationCode
from src.core.error_handler import ErrorCode, ErrorResponse
from src.core.masking import mask_email, mask_code

logger = logging.getLogger(__name__)


def generate_verification_code() -> str:
    """
    生成 6 位数字验证码

    返回：
        str: 6 位数字验证码（如 "123456"）
    """
    return str(random.randint(100000, 999999))


def send_verification_code(db: Session, email: str) -> str:
    """
    发送验证码到指定邮箱（使用数据库事务保护）

    流程：
    1. 生成 6 位验证码
    2. 检查该邮箱是否有未使用的验证码（5 分钟内）
    3. 如果有，返回该验证码（不重复生成）
    4. 如果没有，创建新验证码
    5. 开发环境：打印到控制台
    6. 生产环境：发送真实邮件（待实现）

    参数：
        db: 数据库会话
        email: 目标邮箱

    返回：
        str: 验证码

    注意：
        - 限流应该在 API 层处理（使用 slowapi）
        - 同一邮箱 5 分钟内只能发送一次
    """
    logger.info("send_code_start", extra={"email": mask_email(email)})

    try:
        # 检查 5 分钟内是否有未使用的验证码
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        existing_code = (
            db.query(VerificationCode)
            .filter(
                VerificationCode.email == email,
                VerificationCode.created_at >= five_minutes_ago,
                VerificationCode.used == False,
            )
            .first()
        )

        if existing_code:
            # 返回现有验证码（避免重复发送）
            logger.info("code_exists", extra={"email": mask_email(email)})
            code = existing_code.code
        else:
            # 生成新验证码
            code = generate_verification_code()
            logger.debug("code_generated", extra={"code": mask_code(code)})

            # 创建新验证码（事务内）
            with db.begin():
                # 清理该邮箱的旧已使用验证码（保持数据库整洁）
                db.query(VerificationCode).filter(
                    VerificationCode.email == email, VerificationCode.used == True
                ).delete()

                # 创建新验证码
                verification_code = VerificationCode(
                    email=email,
                    code=code,
                    expires_at=datetime.utcnow() + timedelta(minutes=5),
                    used=False,
                )
                db.add(verification_code)

        # 发送验证码
        env = os.getenv("ENV", "development")
        logger.debug("send_code", extra={"env": env, "email": mask_email(email)})

        if env == "development":
            # 开发环境：打印到控制台
            print(f"\n{'='*50}")
            print(f"📧 验证码发送到: {email}")
            print(f"🔢 验证码: {code}")
            print(f"⏰ 有效期: 5 分钟")
            print(f"{'='*50}\n")
        else:
            # 生产环境：发送真实邮件（待实现）
            # TODO: 实现邮件发送逻辑
            # from src.services.email_service import send_email
            # send_email(email, code)
            logger.debug("production_mode", extra={"email": mask_email(email)})

        logger.info("send_code_success", extra={"email": mask_email(email)})

        return code

    except Exception as e:
        logger.error("send_code_failed", extra={"email": mask_email(email), "error": str(e)}, exc_info=True)
        error_response = ErrorResponse.create(code=ErrorCode.SYSTEM_INTERNAL_ERROR)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.to_dict(),
        )


def verify_code(db: Session, email: str, code: str) -> bool:
    """
    验证验证码是否有效

    参数：
        db: 数据库会话
        email: 邮箱
        code: 验证码

    返回：
        bool: 验证码是否有效

    注意：
        此函数不修改验证码状态（不标记为已使用）
        标记已使用应该在注册时进行
    """
    verification_code = db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.code == code
    ).first()

    if not verification_code:
        return False

    return verification_code.is_valid()


def mark_code_used(db: Session, email: str, code: str) -> None:
    """
    标记验证码为已使用

    参数：
        db: 数据库会话
        email: 邮箱
        code: 验证码
    """
    verification_code = db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.code == code
    ).first()

    if verification_code:
        verification_code.used = True
        db.commit()


def cleanup_expired_codes(db: Session) -> int:
    """
    清理过期的验证码

    删除所有过期且已使用的验证码

    参数：
        db: 数据库会话

    返回：
        int: 删除的记录数
    """
    # 删除过期且已使用的验证码
    deleted_count = db.query(VerificationCode).filter(
        VerificationCode.used == True,
        VerificationCode.expires_at < datetime.utcnow()
    ).delete()

    db.commit()
    return deleted_count
