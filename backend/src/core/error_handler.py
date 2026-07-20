"""
统一错误处理模块

提供结构化的错误响应格式，包含：
- ErrorResponse: 统一的错误响应模型
- ErrorCode: 错误码枚举
- ERROR_MESSAGES: 错误消息映射
- handle_errors: 异常处理装饰器

作者：求职 Copilot 项目
创建时间：2025-01-01
"""

import functools
import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Callable
from pydantic import BaseModel

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """错误码枚举

    命名规范：<DOMAIN>_<ERROR>_<DETAIL>

    错误域（Domain）：
    - AUTH_*: 认证相关错误
    - CODE_*: 验证码相关错误
    - TOKEN_*: Token 相关错误
    - VALID_*: 数据验证错误
    - SYSTEM_*: 系统级错误
    """

    # 认证错误 (AUTH_*)
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"

    # 验证码错误 (CODE_*)
    CODE_INVALID = "CODE_INVALID"
    CODE_EXPIRED = "CODE_EXPIRED"
    CODE_ALREADY_USED = "CODE_ALREADY_USED"
    CODE_RECENTLY_SENT = "CODE_RECENTLY_SENT"

    # Token 错误 (TOKEN_*)
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_MISSING = "TOKEN_MISSING"

    # 验证错误 (VALID_*)
    VALID_EMAIL_FORMAT = "VALID_EMAIL_FORMAT"
    VALID_PASSWORD_TOO_SHORT = "VALID_PASSWORD_TOO_SHORT"
    VALID_PASSWORD_TOO_LONG = "VALID_PASSWORD_TOO_LONG"
    VALID_PHONE_FORMAT = "VALID_PHONE_FORMAT"

    # 系统错误 (SYSTEM_*)
    SYSTEM_DATABASE_ERROR = "SYSTEM_DATABASE_ERROR"
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"


# 错误消息映射
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    # 认证错误
    ErrorCode.AUTH_EMAIL_EXISTS: "该邮箱已被注册，请直接登录",
    ErrorCode.AUTH_INVALID_CREDENTIALS: "邮箱或密码错误",
    ErrorCode.AUTH_ACCOUNT_DISABLED: "账户已被禁用，请联系管理员",

    # 验证码错误
    ErrorCode.CODE_INVALID: "验证码错误，请检查或重新获取",
    ErrorCode.CODE_EXPIRED: "验证码已过期（5分钟有效期），请重新获取",
    ErrorCode.CODE_ALREADY_USED: "验证码已使用，请重新获取",
    ErrorCode.CODE_RECENTLY_SENT: "验证码已发送，请稍后再试",

    # Token 错误
    ErrorCode.TOKEN_INVALID: "Token无效，请重新登录",
    ErrorCode.TOKEN_EXPIRED: "Token已过期，请重新登录",
    ErrorCode.TOKEN_MISSING: "未提供Token，请重新登录",

    # 验证错误
    ErrorCode.VALID_EMAIL_FORMAT: "邮箱格式不正确，请输入有效的邮箱地址",
    ErrorCode.VALID_PASSWORD_TOO_SHORT: "密码长度至少6位，请重新输入",
    ErrorCode.VALID_PASSWORD_TOO_LONG: "密码过长，请使用72字符以内的密码",
    ErrorCode.VALID_PHONE_FORMAT: "手机号格式不正确，请输入有效的手机号",

    # 系统错误
    ErrorCode.SYSTEM_DATABASE_ERROR: "数据库错误，请稍后重试",
    ErrorCode.SYSTEM_INTERNAL_ERROR: "系统内部错误，请稍后重试",
}


# 错误操作建议映射
ERROR_ACTIONS: Dict[ErrorCode, Optional[str]] = {
    ErrorCode.AUTH_EMAIL_EXISTS: "login",
    ErrorCode.AUTH_ACCOUNT_DISABLED: "contact_admin",
    ErrorCode.CODE_EXPIRED: "resend_code",
    ErrorCode.CODE_ALREADY_USED: "resend_code",
    ErrorCode.CODE_INVALID: "fix_code",
    ErrorCode.CODE_RECENTLY_SENT: "wait",
    ErrorCode.TOKEN_INVALID: "login",
    ErrorCode.TOKEN_EXPIRED: "login",
    ErrorCode.TOKEN_MISSING: "login",
    ErrorCode.VALID_EMAIL_FORMAT: "fix_email",
    ErrorCode.VALID_PASSWORD_TOO_SHORT: "fix_password",
    ErrorCode.VALID_PASSWORD_TOO_LONG: "fix_password",
    ErrorCode.VALID_PHONE_FORMAT: "fix_phone",
    # 系统错误不需要action
}


class ErrorResponse(BaseModel):
    """统一错误响应模型

    所有API错误响应必须使用此格式，确保前端能够智能处理错误
    """

    code: str  # 错误码（来自 ErrorCode 枚举）
    message: str  # 用户友好的中文消息
    details: Optional[Dict[str, Any]] = None  # 详细信息（仅开发环境）
    action: Optional[str] = None  # 建议操作（如 "login"、"resend_code"）

    @classmethod
    def create(
        cls,
        code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        override_message: Optional[str] = None,
    ) -> "ErrorResponse":
        """创建错误响应

        参数：
            code: 错误码
            details: 详细信息（仅开发环境）
            override_message: 覆盖默认错误消息（可选）

        返回：
            ErrorResponse: 错误响应对象
        """
        message = override_message or ERROR_MESSAGES.get(code, "未知错误")
        action = ERROR_ACTIONS.get(code)

        return cls(code=code.value, message=message, details=details, action=action)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 FastAPI 响应）"""
        data = {"code": self.code, "message": self.message}
        if self.details:
            data["details"] = self.details
        if self.action:
            data["action"] = self.action
        return data


def handle_errors(error_code_map: Optional[Dict[type, ErrorCode]] = None):
    """统一异常处理装饰器

    自动捕获函数中的异常并转换为结构化的HTTPException

    参数：
        error_code_map: 异常类型到错误码的映射字典
                       例如: {ValueError: ErrorCode.VALID_ERROR}

    使用示例：
        @handle_errors({ValueError: ErrorCode.VALID_ERROR})
        def my_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # FastAPI HTTPException 已经处理过，直接抛出
                raise
            except ValueError as e:
                # 数据验证错误
                logger.warning(f"Validation error in {func.__name__}: {e}")
                error_response = ErrorResponse.create(
                    code=error_code_map.get(ValueError, ErrorCode.SYSTEM_INTERNAL_ERROR),
                    details={"error_type": "ValueError", "error_message": str(e)} if _is_debug() else None,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.to_dict(),
                )
            except KeyError as e:
                # 键错误（通常是字典访问失败）
                logger.warning(f"Key error in {func.__name__}: {e}")
                error_response = ErrorResponse.create(
                    code=ErrorCode.SYSTEM_INTERNAL_ERROR,
                    details={"error_type": "KeyError", "error_message": str(e)} if _is_debug() else None,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_response.to_dict(),
                )
            except Exception as e:
                # 其他未捕获的异常
                logger.error(
                    f"Unexpected error in {func.__name__}: {e}",
                    exc_info=True,  # 包含堆栈信息
                )
                error_response = ErrorResponse.create(
                    code=ErrorCode.SYSTEM_INTERNAL_ERROR,
                    details={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc() if _is_debug() else None,
                    } if _is_debug() else None,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_response.to_dict(),
                )

        return wrapper

    return decorator


def _is_debug() -> bool:
    """检查是否为调试模式

    开发环境返回详细错误信息，生产环境仅返回用户友好消息
    """
    import os
    return os.getenv("DEBUG", "False").lower() == "true"
