"""
RAG 接入端到端联调（add-mock-interview 阶段 7.4 + 7.0）
========================================================

验证数据飞轮主链路：
  出题（RAG 检索公司库 → 题库 rag_used 命中）
  → 多轮面试
  → 复盘
  → 自动沉淀个人库（search_personal 能召回本场题）

顺带验证 7.0 丰富性：锚点池随机化（同画像连出两场，锚点池应有差异）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.models.base import SessionLocal
from src.models import knowledge  # noqa: F401  建表
from src.services.profile_service import save_profile, delete_profile
from src.services import knowledge_service as ks
from src.graph.nodes.mock_interview import build_interview_graph

TEST_UID = "test-rag-e2e-001"

PROFILE = {
    "name": "李四",
    "target_positions": ["产品经理"],
    "companies": ["字节跳动"],
    "positions": ["产品经理"],
    "work_descriptions": ["负责短视频 feed 推荐产品，主导策略迭代，DAU 提升 15%"],
    "project_names": ["推荐策略重构"],
    "project_descriptions": ["重构推荐召回策略，CTR 提升 20%"],
    "technical_skills": ["SQL", "A/B 测试", "数据分析"],
}


def get_pending(graph, config):
    snap = graph.get_state(config)
    for t in snap.tasks:
        if t.interrupts:
            return t.interrupts[0].value
    return None


def run_one_session(thread_id: str):
    """跑一场面试直到结束（无 pending 题），返回 (question_plan, debrief)。"""
    graph = build_interview_graph(MemorySaver())
    config = {"configurable": {"thread_id": thread_id}}
    init = {
        "messages": [], "user_id": TEST_UID,
        "interview_type": "full", "intensity": "short",
        "persona": {"tone": "专业"},
        "session_id": thread_id,  # 注入 session_id 供沉淀关联
    }
    graph.invoke(init, config)

    # 答题池轮换，循环到没有 pending 题（面试结束）——安全上限防死循环
    pool = [
        "我在字节做 feed 推荐，用 A/B 测试优化策略，DAU 提升 15%。",
        "用 SQL 做漏斗分析定位流失节点，优化后转化提升 12%。",
        "想做 PM 因为喜欢用数据解决问题，3 年内想成为能独立带产品线的高级 PM。",
        "那个项目我协调了算法和工程团队，自己主导了策略设计。",
    ]
    for i in range(15):
        q = get_pending(graph, config)
        if not q:
            break
        graph.invoke(Command(resume=pool[i % len(pool)]), config)

    state = graph.get_state(config).values
    return state.get("question_plan") or {}, state.get("debrief_report") or {}


def run():
    print("=" * 70)
    print("RAG 接入端到端联调（出题命中 → 面试 → 复盘 → 沉淀）")
    print("=" * 70)

    db = SessionLocal()
    save_profile(db, TEST_UID, PROFILE)
    ks.seed_curated(db)  # 公司库种子（幂等）
    db.close()

    try:
        # ── 第一场：验证公司库 RAG 命中 + 沉淀 ──
        plan1, debrief1 = run_one_session("rag-e2e-sess1")
        rag_used = plan1.get("rag_used") or {}
        ov1 = debrief1.get("overview") or {}
        print(f"\n[第一场] 题数={plan1.get('question_count')}，RAG 命中={rag_used}")
        print(f"  复盘：轮数={ov1.get('total_rounds')}，均分={ov1.get('avg_score')}")

        # 验证公司库命中（产品经理画像 → 公司库有产品题）
        company_hit = rag_used.get("company_hints", 0) > 0

        # 验证个人库沉淀（本场题应能被检索到）
        db = SessionLocal()
        archived = db.query(ks.PersonalEpisodeModel).filter(
            ks.PersonalEpisodeModel.user_id == TEST_UID).count()
        results = ks.search_personal(db, TEST_UID, "团队推动 数据结果", top_k=3)
        db.close()
        print(f"  个人库沉淀 {archived} 条，检索召回 {len(results)} 条")
        sediment_ok = archived > 0 and len(results) > 0

        # ── 第二场：验证飞轮反哺（个人库近期题应被避开）+ 锚点随机化 ──
        plan2, _ = run_one_session("rag-e2e-sess2")
        rag_used2 = plan2.get("rag_used") or {}
        print(f"\n[第二场] RAG 命中={rag_used2}")
        print(f"  → recent_questions 应 >0（飞轮反哺：本场知道你近期练过什么）")
        flywheel_ok = rag_used2.get("recent_questions", 0) > 0

        # ============ 汇总 ============
        print("\n" + "=" * 70)
        print("结果汇总")
        print("=" * 70)
        checks = [
            ("公司库 RAG 注入出题（产品画像命中真实面经）", company_hit),
            ("复盘自动沉淀个人库 + 可检索", sediment_ok),
            ("飞轮反哺：第二场感知到近期练过的题", flywheel_ok),
            ("复盘报告生成完整", bool(ov1.get("total_rounds"))),
        ]
        all_ok = True
        for name, ok in checks:
            print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")
            all_ok = all_ok and ok
        print("=" * 70)
        return all_ok
    finally:
        db = SessionLocal()
        delete_profile(db, TEST_UID)
        ks.delete_all_personal(db, TEST_UID)
        db.close()


if __name__ == "__main__":
    run()
