"""
API 限流配置

使用 slowapi 库实现速率限制：
- 全局限流（所有端点）
- 特定端点限流（如验证码接口）

防止：
- DDoS 攻击
- 暴力破解
- 接口滥用
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import os

# 创建 Limiter 实例
# 使用 IP 地址作为限流键（可自定义）
limiter = Limiter(key_func=get_remote_address)

# 从环境变量读取限流配置
GLOBAL_RATE_LIMIT = os.getenv("RATE_LIMIT_GLOBAL", "100/minute")
SEND_CODE_RATE_LIMIT = os.getenv("RATE_LIMIT_SEND_CODE", "5/minute")


def get_user_id(request: Request) -> str:
    """
    获取用户 ID（用于用户级限流）

    可以根据认证状态返回用户 ID 或邮箱
    未认证用户返回 IP 地址

    参数：
        request: FastAPI Request 对象

    返回：
        str: 用户标识符（ID 或 IP）
    """
    # 尝试从请求中获取用户信息
    # （需要认证的端点可以返回 user_id）
    # TODO: 实现用户级限流
    return get_remote_address(request)
