"""
用户画像与 JD 匹配结果的数据模型

包含两张表：
1. user_profiles     - 用户个人画像（简历解析产物，按用户维度维护，一人一份）
2. jd_match_results  - JD 匹配结果（每次匹配一条，支持历史回看）

【设计说明：混合数据模型】
- 标量字段（姓名、邮箱、各维度得分等）用普通列存储：便于查询、排序、建索引。
- 不定长列表（教育/工作经历、技能、Gap 清单、JD 要求等）用 JSON 列存储：
  这些数据半结构化、会随业务演进，JSON 列可无损存取，无需频繁改表结构。
- 与 users 表分层：users 存「账户信息」（注册），user_profiles 存「求职档案」（简历解析画像），
  职责分离、互不冲突。

作者：求职 Copilot 项目
日期：2026-07-14
"""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey
from datetime import datetime
import uuid

# 导入 Base（SQLAlchemy 声明基类）
from src.models.base import Base


class UserProfileModel(Base):
    """
    用户个人画像表（与 users 表 1:1）

    存储简历解析产出的完整结构化画像，供 JD 匹配、简历优化、模拟面试等下游能力读取。
    每个 user_id 仅维护一份当前画像（unique 约束保证）。
    """
    __tablename__ = "user_profiles"

    # 主键（UUID，与 users 表风格一致；SQLite 用 String 存储）
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联用户：一人一份画像（unique），用户删除则画像级联删除
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="用户 ID（一人一份画像）"
    )

    # ── 标量字段：简历基本信息 ──
    name = Column(String(100), nullable=True, comment="姓名")
    email = Column(String(255), nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="电话")
    location = Column(String(255), nullable=True, comment="所在地")
    avatar_url = Column(String(500), nullable=True, comment="头像 URL（形如 /static/avatars/{user_id}.{ext}）")

    # ── 标量字段：求职目标中的标量部分 ──
    location_preference = Column(String(255), nullable=True, comment="期望工作地点")
    salary_range = Column(String(100), nullable=True, comment="期望薪资范围")
    industry = Column(String(100), nullable=True, comment="期望行业")

    # ── 画像元信息 ──
    quality_score = Column(Float, nullable=True, comment="简历文本质量分（0.0-1.0）")
    source = Column(String(20), nullable=True, comment="画像来源：file / text / manual")

    # ── JSON 列：不定长列表（会演进，整存无损） ──
    # 教育经历、工作经历、项目、技能、语言、目标岗位/公司等
    detail_json = Column(
        JSON,
        nullable=True,
        comment="画像明细：教育/工作/项目/技能/语言/目标岗位等不定长列表"
    )
    confidence_json = Column(JSON, nullable=True, comment="各字段置信度")

    # ── 时间戳 ──
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserProfileModel(user_id={self.user_id}, name={self.name})>"


class JdMatchResultModel(Base):
    """
    JD 匹配结果表（与 users 表 N:1）

    每次完成一次 JD 匹配写入一条记录，支持用户回看历史、横向对比、复算分析。
    """
    __tablename__ = "jd_match_results"

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联用户（一个用户可有多条历史匹配）
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID"
    )

    # 原始 JD 文本（留痕：便于复算与回看，不依赖外部状态即可还原分析过程）
    jd_text = Column(Text, nullable=True, comment="原始 JD 文本")

    # ── 标量列：总分 + 四维度得分（固定维度，便于排序与统计） ──
    overall_score = Column(Float, nullable=True, comment="总匹配度（0-100）")
    skill_score = Column(Float, nullable=True, comment="技能匹配度")
    experience_score = Column(Float, nullable=True, comment="经验匹配度")
    education_score = Column(Float, nullable=True, comment="学历匹配度")
    soft_skill_score = Column(Float, nullable=True, comment="软技能匹配度")

    # ── JSON 列：结构化但会演进的部分 ──
    job_profile_json = Column(JSON, nullable=True, comment="JD 解析出的要求画像（硬技能/软技能/隐性/红线四分类）")
    gaps_json = Column(JSON, nullable=True, comment="差距清单（Gap 四分类 + 应对建议）")
    confidence_json = Column(JSON, nullable=True, comment="各项置信度")

    # 匹配时间
    created_at = Column(DateTime, default=datetime.utcnow, comment="匹配时间")

    def __repr__(self):
        return f"<JdMatchResultModel(id={self.id}, user_id={self.user_id}, overall_score={self.overall_score})>"
