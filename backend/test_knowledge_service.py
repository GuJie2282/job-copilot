"""
面经库服务验证（add-mock-interview 阶段 7.2 / 7.3）
====================================================

覆盖：
  公司库：种子入库（幂等）、检索（语义+来源优先级）、UGC 入口
  个人库：复盘后沉淀、检索、隐私隔离、删除（数据权利）

LLM 扩充（llm_augment_company）单独跑（花钱慢），本脚本默认跳过。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from src.models.base import Base, engine, SessionLocal
# 触发模型注册（建表用）
from src.models import knowledge  # noqa: F401
from src.services import knowledge_service as ks


# 两个测试用户（验证隔离）
UID_A = "test-rag-userA"
UID_B = "test-rag-userB"


def setup():
    Base.metadata.create_all(bind=engine)


def cleanup(db):
    """清测试数据（保留精选种子——那是真实可用数据）。"""
    from src.models.knowledge import PersonalEpisodeModel, CompanyQuestionModel
    db.query(PersonalEpisodeModel).filter(
        PersonalEpisodeModel.user_id.in_([UID_A, UID_B])
    ).delete(synchronize_session=False)
    db.query(CompanyQuestionModel).filter(
        CompanyQuestionModel.source != "curated"
    ).delete(synchronize_session=False)
    db.commit()


def test_company_seed_and_search(db):
    print("\n【公司库：种子入库 + 检索】")
    n = ks.seed_curated(db)
    total = db.query(ks.CompanyQuestionModel).count()
    print(f"  本次新增种子 {n} 条（幂等：已存在则跳过），公司库共 {total} 条")

    # 语义检索：用自然语言查，应召回语义相关的产品题
    results = ks.search_company(db, "产品上线后 DAU 下滑怎么排查 数据归因", top_k=3)
    print(f"  检索『DAU 下滑排查』→ top3：")
    for r in results:
        print(f"    [{r['_score']}] src={r['source']} | {r['text'][:38]}")
    # 期望：召回产品经理的「DAU 下滑排查」题
    hit_dau = any("DAU" in r["text"] or "下滑" in r["text"] for r in results)
    return hit_dau, total


def test_company_source_priority(db):
    print("\n【公司库：来源优先级 curated > ugc > llm_generated】")
    # 三条语义接近的产品题，来源不同
    ks.add_company_question(db, None, "产品经理", "case",
        "如果一个社区产品 DAU 突然连续下滑，你会怎么排查原因？", source="llm_generated")
    ks.add_ugc_company(db, "贡献者A", None, "产品经理", "case",
        "产品上线后核心指标下滑，你的归因排查思路是什么？")
    # curated 的同类题种子集里已有（DAU 下滑那题）

    results = ks.search_company(db, "产品 DAU 下滑怎么排查", top_k=5)
    # 找三条同义题各自的排名
    src_order = []
    for r in results:
        if any(k in r["text"] for k in ["下滑", "归因", "排查"]) and r["position"] == "产品经理":
            src_order.append(r["source"])
    print(f"  同义题召回顺序（按分数）：{src_order}")
    # 期望 curated 排在 ugc/llm 前面（权重更高）
    curated_idx = src_order.index("curated") if "curated" in src_order else 99
    return curated_idx == 0 if src_order else False


def test_personal_archive_and_search(db):
    print("\n【个人库：复盘沉淀 + 检索】")
    profile = {"target_positions": ["产品经理"], "companies": ["字节跳动"]}
    transcript = [
        {"round": 1, "qid": "q1", "is_probe": False,
         "question": "讲一次你 push 团队达成目标、并拿到数据结果的经历。",
         "answer": "我推动推荐策略重构，DAU 提升 15%。",
         "evaluation": {"score": 82}, "category": "behavioral"},
        {"round": 2, "qid": "qa", "is_probe": False,
         "question": "你有什么想问我的吗？", "answer": "团队结构？", "evaluation": {}},
    ]
    debrief = {"round_reviews": [{"round": 1, "better_version": "（改进版）用 STAR 重述…"}]}
    bank = [{"qid": "q1", "category": "behavioral"}]

    n = ks.archive_episodes_from_session(
        db, UID_A, "sess-1", transcript, debrief, profile, bank)
    print(f"  沉淀 {n} 条（反问 qid=qa 应跳过 → 期望 1 条）")

    # 检索：搜同主题
    results = ks.search_personal(db, UID_A, "团队推动的经历 数据结果", top_k=3)
    print(f"  检索『团队推动数据结果』→ {len(results)} 条")
    for r in results:
        print(f"    [{r['_score']}] {r['text'][:38]}")
    hit = n == 1 and len(results) >= 1 and results[0]["better_version"] is not None
    return hit


def test_personal_isolation(db):
    print("\n【个人库：隐私隔离】")
    # user B 搜 user A 的题 → 应为空
    results = ks.search_personal(db, UID_B, "团队推动", top_k=5)
    cnt_b = db.query(ks.PersonalEpisodeModel).filter(
        ks.PersonalEpisodeModel.user_id == UID_B).count()
    print(f"  userB 检索结果={len(results)} 条，userB 库中共 {cnt_b} 条（期望均 0）")
    return len(results) == 0 and cnt_b == 0


def test_personal_delete(db):
    print("\n【个人库：删除（数据权利）】")
    deleted = ks.delete_all_personal(db, UID_A)
    left = db.query(ks.PersonalEpisodeModel).filter(
        ks.PersonalEpisodeModel.user_id == UID_A).count()
    print(f"  删除 userA {deleted} 条，剩余 {left} 条（期望 0）")
    return left == 0


def run():
    print("=" * 70)
    print("面经库服务验证（7.2 个人库 + 7.3 公司库）")
    print("=" * 70)
    setup()
    db = SessionLocal()
    try:
        results = {
            "公司库种子+语义检索": test_company_seed_and_search(db)[0],
            "公司库来源优先级": test_company_source_priority(db),
            "个人库沉淀+检索": test_personal_archive_and_search(db),
            "个人库隐私隔离": test_personal_isolation(db),
            "个人库删除(数据权利)": test_personal_delete(db),
        }
        print("\n" + "=" * 70)
        print("结果汇总")
        print("=" * 70)
        for name, ok in results.items():
            print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")
        print("=" * 70)
    finally:
        cleanup(db)
        db.close()


if __name__ == "__main__":
    run()
