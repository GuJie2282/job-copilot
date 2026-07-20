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
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import os

# 简单的限流配置（不从.env读取，避免编码问题）
GLOBAL_RATE_LIMIT = "100/minute"
SEND_CODE_RATE_LIMIT = "5/minute"

# 创建 Limiter 实例
# 注意：slowapi 默认会用 starlette Config 读 ".env"，而 starlette 在 Windows 下
# 用 GBK 解码——backend/.env 含中文注释会触发 UnicodeDecodeError，导致整个后端启动崩溃。
# 这里把 config_filename 指向一个不存在的文件，强制 Config 跳过文件读取。
# 限流配置走 default_limits（硬编码），环境变量由 main.py 的 load_dotenv() 用 UTF-8 加载。
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=None,  # 使用内存存储
    default_limits=[GLOBAL_RATE_LIMIT],
    config_filename="___skip_env_read___",  # 占位路径，避免读取真实 .env
)


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
    # （需要认证的端点可以返回用户 ID）
    # TODO: 实现用户级限流
    return get_remote_address(request)
