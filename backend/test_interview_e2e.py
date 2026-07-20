"""
模拟面试端到端验证（add-mock-interview 阶段 3.3.5）
====================================================

跑一场完整的模拟面试，验证整个主循环：
  session_setup(出题) → interviewer(interrupt 提问)
    ⇄ evaluator(信号差检测 + 决策) → probe/next/end
  → debrief(复盘)

验证清单：
  1. 出题成功（question_bank 非空）
  2. interrupt 提问 + Command 恢复正常
  3. evaluator 信号差检测产出（score / miss_signals）
  4. probe 追问发生过（transcript 有 action=probe）
  5. 最终 end（interview_status=finished）
  6. debrief 复盘生成

用 MemorySaver（测试快、不污染 db）。evaluator 调真实 LLM。
测试用临时画像，跑完清理。

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

TEST_UID = "test-interview-e2e-001"

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


def get_pending_question(graph, config):
    """取当前 interrupt 挂起的问题（前端拿这个显示）。"""
    snap = graph.get_state(config)
    for t in snap.tasks:
        if t.interrupts:
            return t.interrupts[0].value
    return None


def run():
    print("=" * 70)
    print("模拟面试 端到端验证（short 档位：3 题 / 每题追问上限 1 / 无反问）")
    print("=" * 70)

    seed()
    try:
        graph = build_interview_graph(MemorySaver())
        config = {"configurable": {"thread_id": "e2e-1"}}
        init = {
            "messages": [],
            "user_id": TEST_UID,
            "interview_type": "full",
            "intensity": "short",
            "persona": {"tone": "专业", "role": {"company": "字节", "position": "高级PM"}},
        }

        # 跑到第一个 interrupt
        graph.invoke(init, config)

        # 模拟用户回答：第一个故意简短（触发 probe），后续充分
        answers = [
            "就那样吧",  # 题1：简短 → 期望 probe
            "我在字节负责 feed 推荐，用 A/B 测试优化召回策略，协调算法和工程团队，DAU 提升 15%，过程里解决了召回相关性下降的问题。",
            "没啥好说的",  # 题2：简短 → 期望 probe
            "我的优势是数据驱动，用漏斗分析定位流失节点，针对性优化使转化率提升 12%。",
            "还行",
            "我做过一个商家增长项目，通过分层运营策略，GMV 翻倍，这是我最自豪的成果。",
        ]

        for i, ans in enumerate(answers, 1):
            q = get_pending_question(graph, config)
            if not q:
                print(f"\n[轮 {i}] 无挂起问题 → 面试已结束")
                break
            tag = "追问" if q.get("is_probe") else "提问"
            print(f"\n[轮 {i}] 面试官{tag}（第{q.get('round')}题）：{q['question'][:60]}")
            print(f"       用户：{ans[:50]}")
            graph.invoke(Command(resume=ans), config)

        # ============ 结果分析 ============
        state = graph.get_state(config).values
        transcript = state.get("transcript") or []
        bank = state.get("question_bank") or []
        actions = [t.get("action") for t in transcript]

        print("\n" + "=" * 70)
        print("验证结果")
        print("=" * 70)

        checks = []
        checks.append(("出题成功", len(bank) > 0))
        checks.append(("interrupt 提问+恢复", len(transcript) > 0))
        checks.append(("evaluator 产出评分", all(isinstance(t.get("evaluation", {}).get("score"), (int, float)) for t in transcript if t.get("evaluation"))))
        checks.append(("probe 追问发生过", "probe" in actions))
        checks.append(("最终结束", state.get("interview_status") == "finished"))
        checks.append(("复盘生成", state.get("debrief_report") is not None))

        for name, ok in checks:
            print(f"[{'✓ PASS' if ok else '△ 待观察' if name=='probe 追问发生过' and not ok else '✗ FAIL'}] {name}")

        print(f"\n动作序列：{actions}")
        print(f"transcript 轮数：{len(transcript)}")
        print(f"平均分：{state.get('debrief_report', {}).get('overview', {}).get('avg_score')}")
        print(f"亮点：{state.get('highlights')}")
        print(f"失分：{state.get('weaknesses')}")

        print("\n逐轮评分：")
        for t in transcript:
            ev = t.get("evaluation") or {}
            print(f"  轮{t.get('round')} [{t.get('action')}] score={ev.get('score')} "
                  f"miss={ev.get('miss_signals')} probe={t.get('is_probe')}")

        all_ok = all(ok for _, ok in checks)
        print("\n" + "=" * 70)
        print(f"总结：{'✅ 模拟面试主循环端到端跑通' if all_ok else '⚠️ 部分检查未过（probe 依赖 LLM 判断，可能因回答已充分未触发）'}")
        print("=" * 70)
    finally:
        cleanup()


if __name__ == "__main__":
    run()
