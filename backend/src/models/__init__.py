"""
数据库模型包

导出所有数据库模型，方便其他模块导入

使用方式：
    from src.models import (
        User, VerificationCode, RefreshToken,
        UserProfileModel, JdMatchResultModel,
        Base, get_db
    )
"""

from src.models.base import Base, get_db
from src.models.user import User, VerificationCode, RefreshToken
from src.models.profile import UserProfileModel, JdMatchResultModel

__all__ = [
    "Base",                # SQLAlchemy Base 类
    "get_db",              # 数据库会话依赖注入
    "User",                # 用户模型
    "VerificationCode",    # 验证码模型
    "RefreshToken",        # 刷新令牌模型
    "UserProfileModel",    # 用户画像模型（简历解析产物）
    "JdMatchResultModel",  # JD 匹配结果模型
]
