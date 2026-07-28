"""
追问质量 + 耗时验证（add-mock-interview 阶段 9.1 / 9.5.2）
=============================================================

验证评估质量 + 节奏决策（evolve-interview-pacing 后）：
  1. 信号差检测准确性：充分回答→命中信号多/倾向不追问；空洞/跑题→缺失信号/倾向追问
  2. LLM 节奏 action 合理：充分回答倾向 next；空洞回答倾向 probe
  3. 追问护栏：单题追问达上限(5)时，action=probe 被纠正为换题（护栏纯逻辑详见 test_pacing.py）
  4. 追问措辞合并产出：action=probe 时 next_probe_followup 非空
  5. 单轮评估耗时 < 15s（演示就绪硬指标）

注：节奏决策的边界/护栏纯逻辑测试在 test_pacing.py；本测试聚焦 LLM 评估质量 + 耗时，
直接测 evaluator 的 _llm_evaluate + _decide（单元级，快），不跑整图。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import time
from dotenv import load_dotenv
load_dotenv()

from src.graph.nodes.mock_interview import _llm_evaluate, _decide

# 一道行为面题 + 出题时预埋的两张地图
QUESTION = "讲一次你 push 团队达成目标、并拿到数据结果的经历。"
IDEAL_SIGNALS = ["量化结果", "个人主动性", "遇到困难与反思"]
PROBING_POINTS = ["具体的数据结果", "你个人的贡献", "过程中的冲突与化解"]

# 4 类回答（覆盖真实面试中的典型情况）
ANSWERS = {
    "充分（命中全部信号）": (
        "我推动推荐策略重构，主动协调算法和工程团队排期，过程中克服了排期冲突，"
        "最终 DAU 提升 15%、CTR 提升 20%，事后复盘了跨团队协作的改进点。"
    ),
    "部分（缺反思信号）": (
        "我主导了推荐策略重构，协调算法和工程，DAU 提升 15%。"
    ),
    "空洞（几乎无信号）": "就那样吧，挺普通的，没什么特别的。",
    "跑题": "我喜欢打篮球，每周打三次，周末还和朋友组队。",
}


def mock_state(probe_count: int = 0):
    """构造 _decide 所需的最小 state。"""
    return {
        "current_q_probes": probe_count,
        "question_plan": {"probing_limit": 3, "question_count": 5, "has_qa_session": True},
        "current_q_idx": 0,
        "qa_done": False,
        "question_bank": [{"qid": "q1"}],
    }


def run():
    print("=" * 70)
    print("追问质量 + 耗时验证（9.1 信号差检测 / 9.5.2 耗时）")
    print("=" * 70)
    print(f"\n题目：{QUESTION}")
    print(f"理想信号：{IDEAL_SIGNALS}")
    print(f"可挖掘点：{PROBING_POINTS}\n")

    results = {}
    timings = []

    for label, ans in ANSWERS.items():
        t0 = time.time()
        ev = _llm_evaluate(QUESTION, IDEAL_SIGNALS, PROBING_POINTS, ans, persona={})
        dt = time.time() - t0
        timings.append(dt)

        # probe_count=0：护栏不拦，看 LLM 的 action（evolve-interview-pacing 后由 LLM 自主决策）
        action_0 = _decide(mock_state(0), ev)
        # probe_count=5：达单题追问护栏上限，若 action=probe 应被纠正为换题
        action_max = _decide(mock_state(5), ev)

        results[label] = (ev, action_0, action_max)
        print(f"【{label}】耗时 {dt:.1f}s")
        print(f"  回答：{ans[:40]}")
        print(f"  命中信号：{ev['hit_signals']}")
        print(f"  缺失信号：{ev['miss_signals']}")
        print(f"  追问地图：{ev['miss_probe_map']}")
        print(f"  action：{ev.get('action')} | 评分：{ev['score']} | 追问额度0→{action_0} | 单题追问达上限→{action_max}\n")

    # ============ 质量断言 ============
    print("=" * 70)
    print("质量断言")
    print("=" * 70)
    full_ev = results["充分（命中全部信号）"][0]
    empty_ev = results["空洞（几乎无信号）"][0]

    checks = [
        ("充分回答评分高于空洞回答", full_ev["score"] > empty_ev["score"]),
        ("充分回答命中信号数 ≥ 空洞回答", len(full_ev["hit_signals"]) >= len(empty_ev["hit_signals"])),
        ("充分回答（额度0）不应追问", results["充分（命中全部信号）"][1] != "probe"),
        ("空洞回答（额度0）应触发追问", results["空洞（几乎无信号）"][1] == "probe"),
        ("追问护栏：单题追问达上限(5)时不 probe（换题/收尾）", all(results[l][2] != "probe" for l in ANSWERS)),
        ("追问基于地图：空洞回答的 miss_probe_map 非空", bool(empty_ev["miss_probe_map"])),
        ("追问措辞合并产出：空洞回答的 next_probe_followup 非空", bool(empty_ev.get("next_probe_followup"))),
        ("单轮评估耗时 < 15s（演示就绪硬上限）", max(timings) < 15),
        ("平均评估耗时 < 12s（合并后单次产出含追问措辞，基线略升；追问场景总 LLM 已 2→1）",
         (sum(timings) / len(timings)) < 12),
    ]
    for name, ok in checks:
        print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")
    print(f"\n耗时：max={max(timings):.1f}s avg={sum(timings)/len(timings):.1f}s")
    print("=" * 70)
    return all(ok for _, ok in checks)


if __name__ == "__main__":
    run()
