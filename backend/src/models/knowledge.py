"""
面经库数据模型（interview-knowledge-base）
==========================================

两张表，对应 spec 的两个数据结构：

1. personal_episodes — 个人面经库（per-user 隔离，每次面试复盘后自动沉淀）
   · 用户的「私有资产」，越用越厚，是数据飞轮壁垒的核心。
   · 严格按 user_id 隔离（spec 隐私与隔离需求）。

2. company_questions — 公司/岗位面经库（全局共享，混合冷启动）
   · 来源标签：curated（精选）/ ugc（用户贡献）/ llm_generated（AI 拟题）。
   · 全局共享，UGC 进库前脱敏（不记录可追溯个人的信息）。

【embedding 存储设计】
   - 用 question 文本的 embedding（智谱 embedding-3，2048 维）做检索。
   - embedding 存 JSON 列（list[float]）。2048 维 float32 每条 ~20KB 文本，
     个人库百条 ~2MB、公司库几百条 ~10MB，SQLite 轻松承载，检索毫秒级。
   - 不引向量库（见 rag_service.py 的诚实技术判断）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey, Index
from datetime import datetime
import uuid

from src.models.base import Base


class PersonalEpisodeModel(Base):
    """
    个人面经条目（与 users N:1）

    每场面试复盘后，把每轮问答结构化沉淀一条进该用户的个人库。
    下次面试可检索：避免重复出题 + 复练历史弱项；复盘可做成长对比。
    """
    __tablename__ = "personal_episodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联用户：严格隔离（查询必带 user_id），用户删除级联
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID（个人库隔离键）",
    )
    # 关联面试会话（一条会话可能沉淀多条，即每轮一条）
    session_id = Column(String(64), nullable=True, index=True, comment="来源面试会话 ID")

    # 结构化字段（对应 spec PersonalEpisode）
    position = Column(String(100), nullable=True, comment="岗位")
    company = Column(String(100), nullable=True, comment="公司（可为空）")
    category = Column(String(30), nullable=True, comment="题型: behavioral/technical/case/motivation")
    question = Column(Text, nullable=False, comment="面试问题")
    my_answer = Column(Text, nullable=True, comment="用户当时的回答")
    score = Column(Float, nullable=True, comment="该题评分")
    better_version = Column(Text, nullable=True, comment="改进范例（复盘生成）")

    happened_at = Column(DateTime, default=datetime.utcnow, comment="发生时间")
    source = Column(String(20), default="personal", comment="来源：固定 personal")

    # embedding（question 文本的向量，检索用；为空则只靠 BM25）
    embedding_json = Column(JSON, nullable=True, comment="question 文本的 embedding（list[float]）")

    # 是否提前结束的会话沉淀（spec：提前结束仍沉淀并标注）
    early_terminated = Column(String(10), default="false", comment="来源会话是否提前结束")

    created_at = Column(DateTime, default=datetime.utcnow, comment="入库时间")

    # 复合索引：按用户 + 岗位检索（出题去重/复练常用）
    __table_args__ = (
        Index("ix_personal_user_position", "user_id", "position"),
    )

    def __repr__(self):
        return f"<PersonalEpisode(user_id={self.user_id}, q={self.question[:20]})>"


class CompanyQuestionModel(Base):
    """
    公司/岗位面经条目（全局共享，无 user_id）

    混合冷启动三种来源（spec 公司面经库冷启动需求）：
      - curated（精选）：人工录入的高频真题，质量最高
      - ugc（用户贡献）：用户主动贡献，脱敏后入库
      - llm_generated（AI 拟题）：基于种子 + 公开信息生成填补长尾
    检索按 source 优先级排序（curated > ugc > llm_generated）。
    """
    __tablename__ = "company_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    company = Column(String(100), nullable=True, index=True, comment="公司（可空，长尾岗位用）")
    position = Column(String(100), nullable=True, index=True, comment="岗位")
    category = Column(String(30), nullable=True, comment="题型")
    question = Column(Text, nullable=False, comment="面经问题")
    context = Column(Text, nullable=True, comment="考察点/背景（可选）")

    source = Column(String(20), default="curated", comment="来源: curated/ugc/llm_generated")
    # UGC 的贡献者：仅留 user_id 用于合规追溯，对外展示脱敏（不暴露）
    contributor_id = Column(String(36), nullable=True, comment="UGC 贡献者（仅内部追溯，不对外）")

    embedding_json = Column(JSON, nullable=True, comment="question 文本的 embedding（list[float]）")

    created_at = Column(DateTime, default=datetime.utcnow, comment="入库时间")

    # 复合索引：按公司 + 岗位检索
    __table_args__ = (
        Index("ix_company_company_position", "company", "position"),
    )

    def __repr__(self):
        return f"<CompanyQuestion({self.company}/{self.position}, src={self.source})>"
