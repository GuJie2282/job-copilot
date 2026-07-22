"""
简历持久化数据模型

存储简历优化模块产出的简历：按「用户 + 目标岗位 + 版本」三个维度维护。
- 一个用户可为不同岗位各生成一份简历（换岗重定向，互不覆盖）
- 同一岗位的简历支持多版本（路径 B 精修迭代，每个定稿版本都留存）

【设计说明：混合数据模型】（沿用 user_profiles / jd_match_results 的风格）
- 标量字段（目标岗位、版本、状态、评估分等）用普通列：便于查询、排序、按岗位分组。
- 大文本（Markdown 简历、渲染 HTML）用 Text 列：内容长、无需索引。
- 半结构化且会演进的评估报告用 JSON 列：整存无损，无需频繁改表。

简历状态机：
- draft     ：路径 A 自动生成的草稿（首版）
- refining  ：路径 B 精修中（中间态实际走 checkpointer，不落库；此值保留以备扩展）
- finalized ：路径 B 精修定稿的版本

作者：求职 Copilot 项目
日期：2026-07-22
"""

from sqlalchemy import (
    Column, String, Float, DateTime, Text, JSON,
    ForeignKey, Integer, UniqueConstraint
)
from datetime import datetime
import uuid

# 导入 Base（SQLAlchemy 声明基类，与既有模型一致）
from src.models.base import Base


class ResumeModel(Base):
    """
    简历表（与 users 表 N:1，与 jd_match_results 表 N:1 可选）

    每次简历生成（路径 A）或定稿（路径 B）写入一条记录。
    (user_id, target_position, version) 联合唯一：保证同一用户同一岗位下版本号不重复。
    """

    __tablename__ = "resumes"

    # 联合唯一约束：同用户同岗位下，版本号唯一（防并发写入产生重复版本）
    __table_args__ = (
        UniqueConstraint("user_id", "target_position", "version", name="uq_resume_user_pos_ver"),
    )

    # 主键（UUID，与既有模型风格一致；SQLite 用 String 存储）
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联用户：一个用户可有多份简历（不同岗位 / 多版本），用户删除则简历级联删除
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID"
    )

    # 目标岗位：简历针对的岗位（按岗位维度分组查询，建索引）
    target_position = Column(String(100), nullable=False, index=True, comment="目标岗位")

    # 关联的 JD 匹配结果（可空：通用生成时不关联具体匹配；匹配被删则解除关联，简历保留）
    jd_result_id = Column(
        String(36),
        ForeignKey("jd_match_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联的 JD 匹配结果 ID（可空）"
    )

    # 版本号：同 user + 岗位 内自增（v1, v2, ...）
    version = Column(Integer, nullable=False, default=1, comment="版本号（同用户同岗位自增）")

    # 简历状态：draft / refining / finalized
    status = Column(String(20), nullable=False, default="draft", comment="状态：draft / refining / finalized")

    # 使用的主题标识（导出时选定，如 tech-dense / soe-formal）
    theme = Column(String(50), nullable=True, comment="使用的主题标识")

    # ── 大文本：简历内容 ──
    content_md = Column(Text, nullable=True, comment="Markdown 简历全文")
    html = Column(Text, nullable=True, comment="渲染后的 HTML（导出后填）")

    # ── JSON 列：6 维评估报告（结构会演进，整存无损） ──
    eval_report_json = Column(JSON, nullable=True, comment="6 维评估报告（维度得分/总分/通过判定/改进优先级）")

    # 综合评估分（从 eval_report 抽成标量列，便于按分数排序）
    eval_score = Column(Float, nullable=True, comment="综合评估分（0-100，便于排序）")

    # ── 时间戳 ──
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return (
            f"<ResumeModel(id={self.id}, user_id={self.user_id}, "
            f"position={self.target_position}, v{self.version}, {self.status})>"
        )
