"""
SqliteSaver 持久化 checkpointer 验证（add-mock-interview 阶段 1.1.2/1.1.3/1.1.4）
=============================================================================

验证 SqliteSaver 能做到 MemorySaver 做不到的事：**抗重启持久化**。

核心测试（模拟进程重启）：
  1. 用 SqliteSaver 跑图到 interrupt，状态存进 db 文件
  2. 【丢弃所有内存对象】（graph、checkpointer、connection 全部 del）
  3. 【重连同一个 db 文件】，新建 graph + checkpointer
  4. 验证：get_state 能恢复之前的 thread 状态，Command(resume) 能从断点继续

同时验证现有 graph（简历/JD/chat）仍能正常编译，未因装新包而破坏。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import os
import sqlite3
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command


DB_PATH = os.path.join(os.path.dirname(__file__), "data", "interview_checkpoints_test.db")


# ============================================================================
# 1. 最小 interrupt 图（复用 spike 的结构，换成 SqliteSaver）
# ============================================================================

class S(TypedDict):
    idx: int
    questions: List[str]
    transcript: Annotated[List[Dict[str, Any]], add]
    decision: Optional[str]


def ask(state):
    if state["idx"] >= len(state["questions"]):
        return {"decision": "end"}
    q = state["questions"][state["idx"]]
    answer = interrupt({"question": q, "round": state["idx"] + 1})
    return {"transcript": [{"round": state["idx"] + 1, "question": q, "answer": answer}]}


def evaluate(state):
    last = state["transcript"][-1]
    if len(last["answer"]) > 5 and state["idx"] + 1 < len(state["questions"]):
        return {"decision": "next", "idx": state["idx"] + 1}
    if state["idx"] + 1 >= len(state["questions"]):
        return {"decision": "end"}
    return {"decision": "next", "idx": state["idx"] + 1}


def route(state):
    return state["decision"]


def build_graph(checkpointer):
    b = StateGraph(S)
    b.add_node("ask", ask)
    b.add_node("evaluate", evaluate)
    b.add_edge(START, "ask")
    b.add_edge("ask", "evaluate")
    b.add_conditional_edges("evaluate", route, {"next": "ask", "end": END})
    return b.compile(checkpointer=checkpointer)


def fresh_state():
    return {"idx": 0, "questions": ["第1题", "第2题"], "transcript": [], "decision": None}


# ============================================================================
# 2. 验证现有 graph 未被破坏（简历/JD/chat 仍可编译）
# ============================================================================

def check_existing_graph_healthy():
    print("[检查0] 现有 graph（简历/JD/chat）是否仍可正常导入编译...")
    try:
        from src.graph.graph import create_graph
        g = create_graph()
        print("    ✓ src.graph.graph.create_graph() 编译成功，现有功能未受影响")
        return True
    except Exception as e:
        print(f"    ✗ 现有 graph 编译失败：{type(e).__name__}: {e}")
        return False


# ============================================================================
# 3. 主验证：抗重启
# ============================================================================

def run_check():
    print("=" * 70)
    print("SqliteSaver 抗重启持久化验证")
    print("=" * 70)

    # 清理旧测试 db
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # ---------- 阶段 A：第一个"进程"，跑到 interrupt 存盘 ----------
    print("\n[阶段A] 第一个进程：建图 → 跑到 interrupt → 存盘")
    from langgraph.checkpoint.sqlite import SqliteSaver

    conn1 = sqlite3.connect(DB_PATH, check_same_thread=False)
    cp1 = SqliteSaver(conn1)
    cp1.setup()  # 建表
    graph1 = build_graph(cp1)
    config = {"configurable": {"thread_id": "resume-test"}}

    graph1.invoke(fresh_state(), config)  # 跑到 ask 的 interrupt 挂起
    q1 = graph1.get_state(config).tasks[0].interrupts[0].value
    print(f"    第1题已问：{q1['question']}（状态已存进 {os.path.basename(DB_PATH)}）")

    # 提交第1题回答 → 跑到第2题 interrupt
    graph1.invoke(Command(resume="这是第一题的充分回答"), config)
    q2 = graph1.get_state(config).tasks[0].interrupts[0].value
    print(f"    第2题已问：{q2['question']}（第1题已入库）")

    # 【模拟进程重启】：销毁所有内存对象 + 关闭连接
    print("\n[重启] 销毁 graph / checkpointer / connection 对象，模拟进程重启...")
    del graph1, cp1
    conn1.close()
    import gc; gc.collect()
    print("    ✓ 内存对象已释放，连接已关闭")

    # ---------- 阶段 B：第二个"进程"，从 db 文件恢复 ----------
    print("\n[阶段B] 第二个进程：重连同一 db → 恢复状态 → 继续面试")
    conn2 = sqlite3.connect(DB_PATH, check_same_thread=False)
    cp2 = SqliteSaver(conn2)
    cp2.setup()
    graph2 = build_graph(cp2)

    # 验证：新对象能拿到之前的 thread 状态（抗重启的关键）
    restored = graph2.get_state(config)
    check_resume_ok = restored.next is not None and len(restored.tasks) > 0
    restored_q = restored.tasks[0].interrupts[0].value if check_resume_ok else None
    print(f"    恢复到的待答问题：{restored_q['question'] if restored_q else '无'}")
    print(f"    [{'✓ PASS' if check_resume_ok else '✗ FAIL'}] 检查1 抗重启：重连后能恢复到第2题的 interrupt 状态")

    # 已答的第1题是否还在 transcript（跨进程数据完整）
    transcript_after = restored.values.get("transcript", [])
    check_t1 = len(transcript_after) == 1 and transcript_after[0]["round"] == 1
    print(f"    [{'✓ PASS' if check_t1 else '✗ FAIL'}] 检查2 跨进程数据完整：第1题回答仍在 transcript")

    # 继续提交第2题回答 → 应到 end
    graph2.invoke(Command(resume="这是第二题的充分回答"), config)
    final = graph2.get_state(config).values
    check_end = final.get("decision") == "end" and len(final.get("transcript", [])) == 2
    print(f"    [{'✓ PASS' if check_end else '✗ FAIL'}] 检查3 恢复后继续：第2题答完正常结束，transcript=2轮")

    conn2.close()

    # ---------- 总结 ----------
    all_pass = check_resume_ok and check_t1 and check_end
    print("\n" + "=" * 70)
    print(f"总结：{'✅ SqliteSaver 抗重启持久化验证通过' if all_pass else '❌ 有检查未通过'}")
    print("=" * 70)

    # 清理测试 db
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    return all_pass


if __name__ == "__main__":
    ok_existing = check_existing_graph_healthy()
    ok_sqlite = run_check()
    print("\n最终：", "✅ 全部通过，可进入 checkpointer 接入" if (ok_existing and ok_sqlite) else "❌ 需排查")
