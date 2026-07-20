"""
模拟面试会话数据模型

面试的「进行中状态」（进度/transcript/题库）由 checkpointer 管
（interview_checkpoints.db，见 graph/checkpointer.py），抗重启。
本表存「会话索引 / 历史 / 复盘快照」——供历史列表、复盘回看使用。

分层（对齐 design.md 决策 2 三层存储）：
  ① 业务档案（job_copilot.db 业务表）：画像/JD/面经
  ② 会话状态（interview_checkpoints.db）：面试进行中状态 ← checkpointer
  ③ 本表（job_copilot.db interview_sessions）：会话索引 + 复盘快照

作者：求职 Copilot 项目
日期：2026-07-20
"""

from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Integer
from datetime import datetime
import uuid

from src.models.base import Base


class InterviewSessionModel(Base):
    """
    模拟面试会话表（与 users N:1）。

    id 即 checkpointer 的 thread_id——业务记录与会话状态用同一标识关联。
    """
    __tablename__ = "interview_sessions"

    # 主键 = thread_id（checkpointer 用它恢复会话）
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="用户 ID",
    )

    # 会话状态：interviewing / paused / finished / error
    status = Column(String(20), nullable=False, comment="会话状态")

    # 配置快照（创建时选定）
    interview_type = Column(String(30), nullable=True, comment="面试类型")
    intensity = Column(String(20), nullable=True, comment="档位：short/normal/deep/full")
    interview_mode = Column(String(20), nullable=True, comment="模式：real/coach")
    jd_result_id = Column(String(36), nullable=True, comment="关联的 JD 匹配结果（可空）")
    persona_json = Column(JSON, nullable=True, comment="面试官人设")

    # 复盘快照（finished 时写入）
    avg_score = Column(Float, nullable=True, comment="平均分")
    total_rounds = Column(Integer, nullable=True, comment="总轮数")
    debrief_report_json = Column(JSON, nullable=True, comment="结构化复盘报告")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")

    def __repr__(self):
        return f"<InterviewSessionModel(id={self.id}, user_id={self.user_id}, status={self.status})>"
