"""
面经库服务（knowledge_service）
===============================

封装个人面经库 + 公司面经库的写入、检索、沉淀、冷启动。底层检索调 rag_service。

【个人库】（per-user 隔离，数据飞轮核心）
  - archive_episodes_from_session: 复盘后自动沉淀（transcript + debrief → 结构化条目）
  - search_personal:               语义+关键词检索（出题去重 / 复练弱项 / 成长对比）
  - get_recent_questions:          近期练过的问题（避免重复出题）
  - get_weakness_questions:        历史低分题（复练弱项）
  - delete_all_personal:           数据权利（删全部个人面经）

【公司库】（全局共享，混合冷启动）
  - add_company_question:  单条入库
  - search_company:        按公司/岗位检索（增强出题真实感）
  - seed_curated:          预置精选种子（幂等）
  - llm_augment_company:   LLM 扩充长尾岗位
  - add_ugc_company:       UGC 入口（脱敏）

来源优先级（spec）：curated > personal > ugc > llm_generated（权重见 rag_service）。
检索失败/embedding 失败均降级（BM25 兜底 + 不阻断出题）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.models.knowledge import PersonalEpisodeModel, CompanyQuestionModel
from src.services.rag_service import embed_text, embed_texts, hybrid_search

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 个人面经库
# ============================================================================

def archive_episodes_from_session(
    db: Session,
    user_id: str,
    session_id: str,
    transcript: List[Dict[str, Any]],
    debrief: Dict[str, Any],
    profile_snapshot: Optional[Dict[str, Any]] = None,
    question_bank: Optional[List[Dict[str, Any]]] = None,
    early_terminated: bool = False,
) -> int:
    """
    复盘后自动沉淀：把一场面试的 transcript 结构化为个人面经条目，批量入库。

    对应 spec「个人面经库写入 / 复盘后自动沉淀」：每条含
    岗位、公司、题型、问题、用户回答、评分、改进范例、发生时间。

    Args:
        transcript:        每轮 {round, question, answer, qid, is_probe, evaluation}
        debrief:           复盘报告（取 round_reviews.better_version）
        profile_snapshot:  画像快照（取 position/company）
        question_bank:     题库（按 qid 查 category）
        early_terminated:  来源会话是否提前结束（标注，spec 边界）

    Returns:
        入库条数
    """
    if not transcript:
        return 0

    profile_snapshot = profile_snapshot or {}
    targets = profile_snapshot.get("target_positions") or []
    companies = profile_snapshot.get("companies") or []
    position = targets[0] if targets else None
    company = companies[0] if companies else None

    # qid → category 映射（题库里有题型，transcript 里没存）
    qid2cat = {p.get("qid"): p.get("category") for p in (question_bank or [])}

    # round → better_version 映射
    reviews = debrief.get("round_reviews") or []
    round2better = {r.get("round"): r.get("better_version") for r in reviews if isinstance(r, dict)}

    # 批量算 embedding（一次 API 调用，省成本）
    questions = [t.get("question", "") for t in transcript]
    embeddings = embed_texts(questions)

    rows = []
    for i, t in enumerate(transcript):
        # 跳过反问环节（qid="qa"）—— 那是用户提问，不是被考查的题
        if t.get("qid") == "qa":
            continue
        ev = t.get("evaluation") or {}
        rows.append(PersonalEpisodeModel(
            user_id=user_id,
            session_id=session_id,
            position=position,
            company=company,
            category=t.get("category") or qid2cat.get(t.get("qid")),
            question=t.get("question", ""),
            my_answer=t.get("answer", ""),
            score=ev.get("score"),
            better_version=round2better.get(t.get("round")),
            happened_at=None,  # 用 default
            source="personal",
            embedding_json=(embeddings[i].tolist() if i < len(embeddings) and embeddings[i] is not None else None),
            early_terminated="true" if early_terminated else "false",
        ))

    if rows:
        db.add_all(rows)
        db.commit()
        logger.info(f"个人面经沉淀：user={user_id}, session={session_id}, {len(rows)} 条")
    return len(rows)


def _personal_to_candidate(row: PersonalEpisodeModel) -> Dict[str, Any]:
    """DB 行 → 检索候选 dict（text=question, vector=embedding, source=personal）。"""
    return {
        "text": row.question or "",
        "vector": row.embedding_json,
        "source": "personal",
        "position": row.position,
        "company": row.company,
        "category": row.category,
        "score": row.score,
        "better_version": row.better_version,
        "my_answer": row.my_answer,
        "session_id": row.session_id,
        "happened_at": row.created_at.isoformat() if row.created_at else None,
        "id": row.id,
    }


def search_personal(
    db: Session,
    user_id: str,
    query: str,
    top_k: int = 5,
    position: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    个人库检索（严格 user_id 隔离）。出题去重 / 复练 / 成长对比 用。

    对应 spec「个人面经库检索 / 跨岗位检索」。
    """
    q = db.query(PersonalEpisodeModel).filter(PersonalEpisodeModel.user_id == user_id)
    if position:
        q = q.filter(PersonalEpisodeModel.position == position)
    if company:
        q = q.filter(PersonalEpisodeModel.company == company)
    if category:
        q = q.filter(PersonalEpisodeModel.category == category)
    rows = q.all()
    if not rows:
        return []
    candidates = [_personal_to_candidate(r) for r in rows]
    return hybrid_search(query, candidates, top_k=top_k)


def get_recent_questions(db: Session, user_id: str, limit: int = 20) -> List[str]:
    """用户近期练过的问题文本（出题避免重复用）。"""
    rows = (
        db.query(PersonalEpisodeModel.question)
        .filter(PersonalEpisodeModel.user_id == user_id)
        .order_by(PersonalEpisodeModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows if r[0]]


def get_weakness_questions(db: Session, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """历史低分题（复练弱项——spec：优先将历史低分考查点纳入本轮）。"""
    rows = (
        db.query(PersonalEpisodeModel)
        .filter(
            PersonalEpisodeModel.user_id == user_id,
            PersonalEpisodeModel.score.isnot(None),
        )
        .order_by(PersonalEpisodeModel.score.asc())
        .limit(limit)
        .all()
    )
    return [_personal_to_candidate(r) for r in rows]


def get_history_for_topic(db: Session, user_id: str, topic: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """按考查点检索历史面经（复盘成长对比用）。"""
    return search_personal(db, user_id, topic, top_k=top_k)


def delete_all_personal(db: Session, user_id: str) -> int:
    """数据权利：删除该用户全部个人面经（spec 隐私与隔离 / 数据可删除）。"""
    deleted = (
        db.query(PersonalEpisodeModel)
        .filter(PersonalEpisodeModel.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info(f"删除个人面经：user={user_id}, {deleted} 条")
    return deleted


def list_personal(
    db: Session,
    user_id: str,
    offset: int = 0,
    limit: int = 20,
    position: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    个人库分页列表（纯浏览，无搜索词；支持岗位/公司/题型筛选）。
    与 search_personal 互补：有搜索词走语义检索，无词走本函数翻页。
    """
    q = db.query(PersonalEpisodeModel).filter(PersonalEpisodeModel.user_id == user_id)
    if position:
        q = q.filter(PersonalEpisodeModel.position == position)
    if company:
        q = q.filter(PersonalEpisodeModel.company == company)
    if category:
        q = q.filter(PersonalEpisodeModel.category == category)
    rows = q.order_by(PersonalEpisodeModel.created_at.desc()).offset(offset).limit(limit).all()
    return [_personal_to_candidate(r) for r in rows]


def delete_one_personal(db: Session, episode_id: str, user_id: str) -> bool:
    """
    删除单条个人面经（数据权利：精细删除）。
    带 user_id 校验防越权——只能删自己的，传他人 id 返回 False。
    """
    row = db.query(PersonalEpisodeModel).filter(
        PersonalEpisodeModel.id == episode_id,
        PersonalEpisodeModel.user_id == user_id,
    ).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ============================================================================
# 2. 公司面经库
# ============================================================================

def add_company_question(
    db: Session,
    company: Optional[str],
    position: Optional[str],
    category: Optional[str],
    question: str,
    context: Optional[str] = None,
    source: str = "curated",
    contributor_id: Optional[str] = None,
) -> CompanyQuestionModel:
    """单条公司面经入库（自动算 embedding）。"""
    emb = embed_text(question)
    row = CompanyQuestionModel(
        company=company,
        position=position,
        category=category,
        question=question,
        context=context,
        source=source,
        contributor_id=contributor_id,
        embedding_json=(emb.tolist() if emb is not None else None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _company_to_candidate(row: CompanyQuestionModel) -> Dict[str, Any]:
    """DB 行 → 检索候选。source 透传（hybrid_search 据此应用优先级权重）。"""
    return {
        "text": row.question or "",
        "vector": row.embedding_json,
        "source": row.source or "llm_generated",
        "category": row.category,
        "company": row.company,
        "position": row.position,
        "context": row.context,
        "id": row.id,
    }


def search_company(
    db: Session,
    query: str,
    top_k: int = 5,
    company: Optional[str] = None,
    position: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    公司库检索（全局共享，按公司/岗位过滤）。
    来源优先级由 hybrid_search 的 source 权重保证（curated>ugc>llm_generated）。
    """
    q = db.query(CompanyQuestionModel)
    if company:
        q = q.filter(CompanyQuestionModel.company == company)
    if position:
        q = q.filter(CompanyQuestionModel.position == position)
    rows = q.all()
    if not rows:
        return []
    candidates = [_company_to_candidate(r) for r in rows]
    return hybrid_search(query, candidates, top_k=top_k)


def add_ugc_company(
    db: Session,
    user_id: str,
    company: Optional[str],
    position: Optional[str],
    category: Optional[str],
    question: str,
    context: Optional[str] = None,
) -> CompanyQuestionModel:
    """
    UGC 入口（spec：脱敏处理，不暴露贡献者）。
    仅记录 contributor_id 供内部合规追溯，对外展示时不返回该字段（见 API 层）。
    """
    return add_company_question(
        db, company=company, position=position, category=category,
        question=question, context=context, source="ugc", contributor_id=user_id,
    )


def company_facets(db: Session) -> Dict[str, List[str]]:
    """
    公司库 facets：返回现有公司/岗位的去重列表，供前端侧边导航。
    """
    companies = [r[0] for r in db.query(CompanyQuestionModel.company)
                 .filter(CompanyQuestionModel.company.isnot(None))
                 .distinct().all() if r[0]]
    positions = [r[0] for r in db.query(CompanyQuestionModel.position)
                 .filter(CompanyQuestionModel.position.isnot(None))
                 .distinct().all() if r[0]]
    return {"companies": companies, "positions": positions}


# ============================================================================
# 3. 精选种子集（冷启动打底——spec：3-5 岗位 × 10-20 真题）
# ============================================================================

# 人工精选高频真题（产品/后端/运营 三岗起步）。来源：常见面试经验整理，非爬取。
CURATED_SEED: List[Dict[str, Any]] = [
    # ── 产品经理 ──
    {"company": None, "position": "产品经理", "category": "behavioral", "question": "讲一次你从 0 到 1 推动一个产品功能落地的经历，重点说你怎么发现需求、如何排优先级。", "context": "考查产品方法论与主动性"},
    {"company": None, "position": "产品经理", "category": "behavioral", "question": "分享一个你和研发/设计产生分歧、最终如何达成共识的真实案例。", "context": "考查跨职能协作与说服力"},
    {"company": None, "position": "产品经理", "category": "technical", "question": "如果 DAU 连续两周下滑 15%，你会从哪些维度排查？给出你的分析框架。", "context": "考查数据驱动与归因分析"},
    {"company": None, "position": "产品经理", "category": "case", "question": "让你为一个社区产品设计「冷启动」策略，你会怎么做？", "context": "考查产品策略与结构化思维"},
    {"company": None, "position": "产品经理", "category": "motivation", "question": "为什么想做产品经理而不是开发或运营？你觉得自己最核心的竞争力是什么？", "context": "考查职业认知与自我认知"},
    {"company": None, "position": "产品经理", "category": "technical", "question": "请解释什么是漏斗分析，你在实际工作中如何用它定位转化问题？", "context": "考查分析工具熟练度"},
    {"company": None, "position": "产品经理", "category": "behavioral", "question": "讲一次你做的一个失败的产品决策，事后你学到了什么？", "context": "考查反思能力与成长性"},
    {"company": None, "position": "产品经理", "category": "case", "question": "如果要提升某电商 App 的复购率，你会从哪些环节切入？", "context": "考查业务理解与增长思维"},
    # ── 后端开发 ──
    {"company": None, "position": "后端开发", "category": "technical", "question": "请讲讲你对缓存击穿、缓存穿透、缓存雪崩的理解，以及各自的应对方案。", "context": "高频八股，考查基础扎实度"},
    {"company": None, "position": "后端开发", "category": "technical", "question": "你设计过的一个高并发系统，瓶颈在哪？你是怎么定位和优化的？", "context": "考查工程经验"},
    {"company": None, "position": "后端开发", "category": "technical", "question": "MySQL 索引底层是什么结构？什么情况下索引会失效？", "context": "考查数据库基础"},
    {"company": None, "position": "后端开发", "category": "behavioral", "question": "讲一次你在线上紧急排查并修复一个 P0 故障的经历。", "context": "考查抗压与排障能力"},
    {"company": None, "position": "后端开发", "category": "case", "question": "设计一个短链生成服务，要求支持亿级 URL，你会怎么设计？", "context": "系统设计经典题"},
    {"company": None, "position": "后端开发", "category": "technical", "question": "分布式锁有哪些实现方式？各自优缺点？", "context": "考查分布式基础"},
    {"company": None, "position": "后端开发", "category": "motivation", "question": "你最近在学什么新技术？为什么学它？", "context": "考查技术热情与自驱"},
    {"company": None, "position": "后端开发", "category": "case", "question": "如何设计一个支持千万级 DAU 的消息已读未读系统？", "context": "系统设计"},
    # ── 运营 ──
    {"company": None, "position": "运营", "category": "behavioral", "question": "讲一次你策划的运营活动，目标和结果分别是什么？你贡献了什么？", "context": "考查运营操盘与数据化"},
    {"company": None, "position": "运营", "category": "case", "question": "给你一个新上线的内容社区，第一个月你怎么做冷启动拉新？", "context": "考查拉新策略"},
    {"company": None, "position": "运营", "category": "technical", "question": "你怎么做用户分层？不同分层你会用什么差异化运营策略？", "context": "考查用户运营方法论"},
    {"company": None, "position": "运营", "category": "motivation", "question": "运营工作很琐碎，你怎么保持热情和持续产出？", "context": "考查职业稳定性认知"},
    {"company": None, "position": "运营", "category": "behavioral", "question": "分享一个你通过数据分析发现机会、并成功提升指标的经历。", "context": "考查数据驱动运营"},
    {"company": None, "position": "运营", "category": "case", "question": "如果某次大促活动转化率低于预期，你会如何复盘和优化？", "context": "考查复盘能力"},
]


def seed_curated(db: Session) -> int:
    """
    预置精选种子集（幂等：已存在的题不重复录入）。
    对应 spec「精选种子打底」。启动时或手动调用一次即可。
    """
    existing = {r.question for r in db.query(CompanyQuestionModel.question).all()}
    new_rows = []
    for item in CURATED_SEED:
        if item["question"] in existing:
            continue
        emb = embed_text(item["question"])
        new_rows.append(CompanyQuestionModel(
            company=item.get("company"),
            position=item.get("position"),
            category=item.get("category"),
            question=item["question"],
            context=item.get("context"),
            source="curated",
            embedding_json=(emb.tolist() if emb is not None else None),
        ))
    if new_rows:
        db.add_all(new_rows)
        db.commit()
        logger.info(f"精选种子入库：{len(new_rows)} 条（已存在 {len(existing)} 条跳过）")
    return len(new_rows)


# ============================================================================
# 4. LLM 扩充长尾（spec：基于种子 + 公开信息生成，标注 llm_generated）
# ============================================================================

def llm_augment_company(
    db: Session,
    position: str,
    count: int = 5,
    company: Optional[str] = None,
) -> int:
    """
    当某岗位公司库题量不足时，用 LLM 基于岗位生成补充题，标注 llm_generated。
    失败降级（不阻断）。生成后自动入库（含 embedding）。
    """
    from src.graph.config import get_llm
    from src.graph.prompts import get_company_question_augment_prompt
    from src.services.llm_retry import invoke_llm_with_retry
    from src.services.jd_parser import _extract_json

    try:
        llm = get_llm(temperature=0.7, tier="strong")  # 公司库拟题：主力档（质量敏感）
        prompt = get_company_question_augment_prompt(position, count, company)
        resp = invoke_llm_with_retry(llm, prompt)
        data = _extract_json(resp.content)
        if isinstance(data, dict):
            data = data.get("questions") or []
        if not isinstance(data, list):
            return 0

        questions = [item.get("question", "") for item in data if isinstance(item, dict) and item.get("question")]
        if not questions:
            return 0
        embeddings = embed_texts(questions)

        rows = []
        for i, q in enumerate(questions):
            rows.append(CompanyQuestionModel(
                company=company,
                position=position,
                category=data[i].get("category") if i < len(data) and isinstance(data[i], dict) else None,
                question=q,
                context=data[i].get("context") if i < len(data) and isinstance(data[i], dict) else None,
                source="llm_generated",
                embedding_json=(embeddings[i].tolist() if i < len(embeddings) and embeddings[i] is not None else None),
            ))
        db.add_all(rows)
        db.commit()
        logger.info(f"LLM 扩充公司库：{position}, {len(rows)} 条")
        return len(rows)
    except Exception as e:
        logger.warning(f"LLM 扩充公司库失败，降级跳过：{type(e).__name__}: {e}")
        return 0
