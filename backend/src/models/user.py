"""
用户相关数据库模型

包含三个表：
1. users - 用户基本信息表
2. verification_codes - 邮箱验证码表
3. refresh_tokens - 刷新令牌表

所有模型都继承自 sqlalchemy 的 Base 类
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# 导入 Base 类（SQLAlchemy 声明基类）
from src.models.base import Base


class User(Base):
    """
    用户表

    存储用户的基本信息，包括：
    - 个人信息（姓名、邮箱、手机）
    - 认证信息（密码哈希）
    - 状态信息（是否激活、是否验证）
    - 时间戳（创建时间、最后登录时间）
    """
    __tablename__ = "users"

    # 主键：使用 UUID（更安全，避免自增 ID 暴露用户数量）
    # 注意：SQLite 不支持原生 UUID，使用 String 存储
    # 切换到 PostgreSQL 时可以改用 UUID 类型
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False, comment="用户姓名")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="邮箱地址")
    phone = Column(String(20), nullable=True, comment="手机号（可选）")
    avatar = Column(String(500), nullable=True, comment="头像 URL")

    # 认证信息（密码使用 bcrypt 哈希存储，永不存储明文）
    password_hash = Column(String(255), nullable=False, comment="密码哈希（bcrypt）")

    # 状态信息
    is_active = Column(Boolean, default=True, comment="账户是否激活")
    is_verified = Column(Boolean, default=False, comment="邮箱是否已验证")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")

    # 关系：一个用户可以有多个 refresh_token
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class VerificationCode(Base):
    """
    验证码表

    存储邮箱验证码，用于：
    - 用户注册时验证邮箱真实性
    - 密码重置时验证用户身份
    - 其他需要邮箱验证的场景

    验证码特性：
    - 6 位数字（000000-999999）
    - 5 分钟有效期
    - 一次性使用
    """
    __tablename__ = "verification_codes"

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 验证码信息
    email = Column(String(255), nullable=False, index=True, comment="邮箱地址")
    code = Column(String(6), nullable=False, comment="6 位数字验证码")

    # 有效期
    expires_at = Column(DateTime, nullable=False, index=True, comment="过期时间")
    used = Column(Boolean, default=False, comment="是否已使用")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<VerificationCode(id={self.id}, email={self.email}, code=****{self.code[-2:]})>"

    def is_valid(self) -> bool:
        """
        检查验证码是否有效

        有效条件：
        1. 未被使用
        2. 未过期

        返回：
            bool: 验证码是否有效
        """
        return not self.used and datetime.utcnow() < self.expires_at


class RefreshToken(Base):
    """
    刷新令牌表

    存储 Refresh Token，用于：
    - Access Token 过期后刷新获取新的 Access Token
    - 单设备登录（踢出其他设备）
    - Token 撤销（退出登录）

    Token 管理：
    - 每个 Token 7 天有效期
    - 刷新后生成新 Token，旧 Token 失效
    - 退出登录时删除 Token
    """
    __tablename__ = "refresh_tokens"

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Token 信息
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户 ID")
    token = Column(String(500), unique=True, nullable=False, index=True, comment="Refresh Token 字符串")

    # 有效期
    expires_at = Column(DateTime, nullable=False, index=True, comment="过期时间")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：多对一（多个 token 属于一个用户）
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"

    def is_valid(self) -> bool:
        """
        检查 Token 是否有效

        有效条件：
        1. 未过期

        返回：
            bool: Token 是否有效
        """
        return datetime.utcnow() < self.expires_at
