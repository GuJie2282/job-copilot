"""
LangGraph interrupt 机制 spike（add-mock-interview 阶段 1.2）
============================================================

目的：验证模拟面试的核心技术机制——状态机「中断与恢复」。
这是方案 B（interrupt）的技术命门，跑通 = 整个模拟面试架构可行。

验证三件事：
  1. 节点内 interrupt(value) 能挂起图，并把 value（面试官的问题）交给调用方
  2. 调用方用 Command(resume=用户回答) 能从断点恢复，interrupt() 返回用户回答
  3. 恢复后条件边能正确路由（probe 追问 / next 下一题 / end 结束）

同时验证 checkpointer 跨 invoke 保持状态（同 thread_id）。

这里用 MemorySaver（内存）验证「机制」本身；
真正的持久化（SqliteSaver）在阶段 1.1 单独接入。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


# ============================================================================
# 1. 最小面试状态（模拟 MockInterviewState 的核心字段）
# ============================================================================

class SpikeState(TypedDict):
    """最小面试状态：只保留验证 interrupt 机制必需的字段。"""
    question_idx: int                                  # 当前题号
    questions: List[str]                               # 题库
    transcript: Annotated[List[Dict[str, Any]], add]   # 对话流水（自动累加）
    probe_count: int                                   # 本题已追问次数
    decision: Optional[str]                            # eval 后的路由决策


# ============================================================================
# 2. 节点：面试官（提问）—— interrupt 在这里发生
# ============================================================================

def interviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    面试官节点：问当前题，然后 interrupt 挂起等用户回答。

    关键：interrupt({"question": q}) 会【暂停整个图】，
    把 {"question": q} 作为「中断值」交给调用方（前端据此显示问题）。
    下一次 invoke(Command(resume=回答)) 时，interrupt() 才会返回用户的回答，
    这一行下面的代码才会继续执行。
    """
    idx = state["question_idx"]
    questions = state["questions"]

    # 题库问完 → 结束
    if idx >= len(questions):
        return {"decision": "end"}

    q = questions[idx]

    # ⭐ 核心：interrupt 挂起，等用户回答
    # 第一次 invoke 跑到这里就停；Command(resume=...) 后，answer 拿到用户回答
    answer = interrupt({"question": q, "round": idx + 1})

    # 恢复后：把这一轮写进 transcript
    return {
        "transcript": [{"round": idx + 1, "question": q, "answer": answer}],
    }


# ============================================================================
# 3. 节点：评估 + 路由决策（模拟 evaluator + route_round）
# ============================================================================

def evaluator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    评估节点：看用户回答，决定下一步动作（简化版决策逻辑）。

    真实实现里这里做「信号差检测」；spike 用简化规则验证路由：
      - 回答太短（<10 字）且本题追问未到 2 次 → probe（追问）
      - 还有下一题 → next
      - 题库问完 → end
    """
    last = state["transcript"][-1]
    answer = last["answer"]
    idx = state["question_idx"]
    probe_count = state["probe_count"]

    if len(answer) < 10 and probe_count < 2:
        decision = "probe"
    elif idx + 1 < len(state["questions"]):
        decision = "next"
    else:
        decision = "end"

    update = {"decision": decision}
    # probe：追问次数 +1（题号不动）；next：换题（追问清零，题号 +1）
    if decision == "probe":
        update["probe_count"] = probe_count + 1
    elif decision == "next":
        update["probe_count"] = 0
        update["question_idx"] = idx + 1
    return update


def route_after_eval(state: Dict[str, Any]) -> str:
    """条件边：根据 decision 路由到 interviewer（继续）或 END（结束）。"""
    return state["decision"]


# ============================================================================
# 4. 构建图 + 编译（必须带 checkpointer 才能 interrupt）
# ============================================================================

def build_spike_graph():
    """构建最小面试图：START → interviewer → evaluator → [probe|next → interviewer, end → END]"""
    builder = StateGraph(SpikeState)
    builder.add_node("interviewer", interviewer_node)
    builder.add_node("evaluator", evaluator_node)

    builder.add_edge(START, "interviewer")
    builder.add_edge("interviewer", "evaluator")
    builder.add_conditional_edges(
        "evaluator", route_after_eval,
        {"probe": "interviewer", "next": "interviewer", "end": END},
    )
    # ⭐ interrupt 必须配 checkpointer 编译，否则报错
    return builder.compile(checkpointer=MemorySaver())


# ============================================================================
# 5. 辅助：从图状态里取出「当前被问的问题」（前端要拿这个显示）
# ============================================================================

def get_current_question(graph, config) -> Optional[Dict[str, Any]]:
    """
    图在 interrupt 处挂起时，问题藏在 state 的 tasks 里。
    这是前端拿「面试官问了什么」的标准方式。
    """
    state_snapshot = graph.get_state(config)
    for task in state_snapshot.tasks:
        # interrupts 是个元组列表，每项 (interrupt_value,)
        if task.interrupts:
            return task.interrupts[0].value
    return None


# ============================================================================
# 6. 主流程：模拟一场完整面试（多轮 invoke）
# ============================================================================

def run_spike():
    print("=" * 70)
    print("LangGraph interrupt 机制 spike —— 模拟面试中断/恢复验证")
    print("=" * 70)

    graph = build_spike_graph()
    config = {"configurable": {"thread_id": "interview-spike-1"}}

    # 初始状态：2 道题的题库
    init_state = {
        "question_idx": 0,
        "questions": [
            "讲一次你 push 团队达成目标的经历",
            "说说你最大的优点",
        ],
        "transcript": [],
        "probe_count": 0,
        "decision": None,
    }

    # 模拟用户的几轮回答（有的故意很短，触发 probe 追问）
    canned_answers = [
        "短回答",                                                        # → 触发 probe
        "我在上家公司协调 3 个团队，推动跨部门项目提前 2 周交付，提升了 20% 效率。",  # → 充分，next
        "短",                                                            # 第二题 → probe
        "我的最大优点是数据驱动决策，比如用 A/B 测试把转化率提升了 15%。",   # → 充分，end
    ]

    # 第一轮：invoke 到 interrupt 挂起（没传 Command，图停在 interviewer 的 interrupt 处）
    graph.invoke(init_state, config)

    results = {"checks": []}

    for i, answer in enumerate(canned_answers, 1):
        # 取出当前被问的问题
        q_info = get_current_question(graph, config)
        if q_info is None:
            print(f"\n[轮 {i}] 没有挂起的问题 → 面试已结束")
            break

        print(f"\n[轮 {i}] 面试官问（第{q_info['round']}题）：{q_info['question']}")
        print(f"       用户答：{answer}")

        # 用 Command(resume=回答) 恢复图，继续跑到下一个 interrupt 或 END
        graph.invoke(Command(resume=answer), config)

        # 看恢复后的状态
        snapshot = graph.get_state(config)
        state_values = snapshot.values
        decision = state_values.get("decision")
        print(f"       → evaluator 决策：{decision} | 题号={state_values.get('question_idx')} 追问={state_values.get('probe_count')}")

    # ============================================================================
    # 验证清单
    # ============================================================================
    final = graph.get_state(config).values
    transcript = final.get("transcript", [])

    print("\n" + "=" * 70)
    print("验证结果")
    print("=" * 70)

    # 检查 1：interrupt 能挂起并取出问题
    ok1 = len(transcript) > 0
    print(f"[{'✓ PASS' if ok1 else '✗ FAIL'}] 检查1 interrupt 挂起 + 取出问题："
          f"transcript 记录了 {len(transcript)} 轮")

    # 检查 2：Command(resume) 恢复，回答进了 transcript
    ok2 = all("answer" in t and t["answer"] for t in transcript)
    print(f"[{'✓ PASS' if ok2 else '✗ FAIL'}] 检查2 Command(resume) 恢复：回答已写入 transcript")

    # 检查 3：probe 触发过（同一题问了多次）
    rounds = [t["round"] for t in transcript]
    has_probe = rounds.count(1) > 1 or rounds.count(2) > 1
    print(f"[{'✓ PASS' if has_probe else '✗ FAIL'}] 检查3 条件边 probe 路由："
          f"出现过追问（轮次序列={rounds}）")

    # 检查 4：图最终走到 END（decision=end，且无挂起任务）
    ended = final.get("decision") == "end" and not graph.get_state(config).next
    print(f"[{'✓ PASS' if ended else '✗ FAIL'}] 检查4 条件边 end 路由：图已结束（decision=end）")

    # 检查 5：checkpointer 跨 invoke 保住了状态（transcript 累积完整）
    ok5 = len(transcript) == len(canned_answers)
    print(f"[{'✓ PASS' if ok5 else '✗ FAIL'}] 检查5 checkpointer 跨 invoke 保状态："
          f"transcript 完整（{len(transcript)}/{len(canned_answers)}）")

    all_pass = ok1 and ok2 and has_probe and ended and ok5
    print("\n" + "=" * 70)
    print(f"总结：{'✅ interrupt 机制验证全部通过 —— 方案 B 技术可行' if all_pass else '❌ 有检查未通过，需排查'}")
    print("=" * 70)
    return all_pass


if __name__ == "__main__":
    run_spike()
