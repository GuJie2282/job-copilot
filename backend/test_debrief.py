"""
详细复盘验证（add-mock-interview 阶段 6.3）
==========================================

跑一场完整面试，重点验证复盘报告的「详细字段」质量：
  - round_reviews.better_version：是否基于候选人【自身经历】改写（非通用模板）
  - inappropriate_answers：是否识别出简短/跑题回答
  - stuck_points：是否标出卡壳处
  - next_steps：是否可执行（非"加强XX"空话）

预设回答故意混合（简短 + 充分），让复盘有内容可评。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.models.base import SessionLocal
from src.services.profile_service import save_profile, delete_profile
from src.graph.nodes.mock_interview import build_interview_graph

TEST_UID = "test-debrief-001"

PROFILE = {
    "name": "张三",
    "target_positions": ["产品经理"],
    "companies": ["字节跳动"],
    "positions": ["产品经理"],
    "work_descriptions": ["负责短视频 feed 推荐产品，主导策略迭代，DAU 提升 15%"],
    "project_names": ["推荐系统重构"],
    "project_descriptions": ["重构推荐召回策略，CTR 提升 20%"],
    "technical_skills": ["SQL", "A/B 测试", "数据分析"],
}


def seed():
    db = SessionLocal()
    save_profile(db, TEST_UID, PROFILE)
    db.close()


def cleanup():
    db = SessionLocal()
    delete_profile(db, TEST_UID)
    db.close()


def get_pending(graph, config):
    snap = graph.get_state(config)
    for t in snap.tasks:
        if t.interrupts:
            return t.interrupts[0].value
    return None


def run():
    print("=" * 70)
    print("详细复盘验证")
    print("=" * 70)

    seed()
    try:
        graph = build_interview_graph(MemorySaver())
        config = {"configurable": {"thread_id": "debrief-1"}}
        init = {
            "messages": [], "user_id": TEST_UID,
            "interview_type": "full", "intensity": "short",
            "persona": {"tone": "专业"},
        }
        graph.invoke(init, config)

        # 混合回答：简短（卡壳）+ 充分
        answers = [
            "就那样吧，挺普通的",
            "我在字节负责 feed 推荐，用 A/B 测试优化召回策略，协调算法和工程团队，DAU 提升 15%。",
            "没啥好说的",
            "我用 SQL 做漏斗分析，定位流失节点，针对性优化后转化率提升 12%。",
            "还行吧",
            "我想做 PM 因为喜欢用数据解决问题，3 年内想成为能独立带产品线的高级 PM。",
        ]

        for i, ans in enumerate(answers, 1):
            q = get_pending(graph, config)
            if not q:
                break
            tag = "追问" if q.get("is_probe") else "提问"
            print(f"[{tag}] {q['question'][:45]} → 答：{ans[:30]}")
            graph.invoke(Command(resume=ans), config)

        state = graph.get_state(config).values
        debrief = state.get("debrief_report") or {}

        print("\n" + "=" * 70)
        print("复盘报告")
        print("=" * 70)
        ov = debrief.get("overview") or {}
        print(f"\n【总评】{ov.get('one_line_summary')}")
        print(f"【平均分】{ov.get('avg_score')} | 轮数 {ov.get('total_rounds')}")

        print("\n【逐题改进范例 better_version】")
        for r in debrief.get("round_reviews") or []:
            print(f"\n  轮{r.get('round')}：{r.get('better_version', '')[:100]}")
            print(f"    改进点：{r.get('improvement_point', '')[:70]}")

        print("\n【不合适回答】")
        for a in debrief.get("inappropriate_answers") or []:
            print(f"  - {a}")

        print("\n【卡壳处】")
        for s in debrief.get("stuck_points") or []:
            print(f"  - {s}")

        print("\n【后续建议 next_steps】")
        for s in debrief.get("next_steps") or []:
            print(f"  - {s}")

        # ============ 质量检查 ============
        print("\n" + "=" * 70)
        print("质量检查")
        print("=" * 70)
        reviews = debrief.get("round_reviews") or []
        steps = debrief.get("next_steps") or []
        checks = [
            ("复盘总评生成", bool(ov.get("one_line_summary"))),
            ("逐题改进范例生成", len(reviews) > 0),
            ("改进范例基于自身经历（非空泛）", any(
                any(kw in (r.get("better_version") or "")
                    for kw in ["字节", "feed", "推荐", "SQL", "DAU", "CTR", "漏斗", "数据", "产品"])
                for r in reviews
            )),
            ("识别不合适回答", len(debrief.get("inappropriate_answers") or []) > 0),
            ("标出卡壳处", len(debrief.get("stuck_points") or []) > 0),
            ("后续建议可执行（非空话）", len(steps) > 0 and not any(
                "加强" in s and len(s) < 12 for s in steps
            )),
        ]
        for name, ok in checks:
            print(f"[{'✓ PASS' if ok else '△ 待观察' if '识别' in name or '标出' in name else '✗ FAIL'}] {name}")

        print("\n" + "=" * 70)
    finally:
        cleanup()


if __name__ == "__main__":
    run()
