"""
MockInterviewState 序列化验证（add-mock-interview 阶段 1.3.7）
==============================================================

验证面试状态里「复杂的 dict/list 字段」经 SqliteSaver checkpointer 往返无损：
  - persona（嵌套 dict）、profile_snapshot（dict）、running_scores（dict）
  - question_bank（list of dict）
  - transcript（reducer 累加字段）

这是 transcript 能跨轮累加、画像快照/人设不丢失的保证。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import os
import sqlite3
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "interview_state_test.db")


# 取 MockInterviewState 的代表性字段子集做序列化验证
class InterviewState(TypedDict):
    persona: Optional[Dict[str, Any]]
    profile_snapshot: Optional[Dict[str, Any]]
    running_scores: Optional[Dict[str, Any]]
    question_bank: Optional[List[Dict[str, Any]]]
    transcript: Annotated[List[Dict[str, Any]], add]


def ask(state):
    """单节点：interrupt 一次，恢复后写一轮 transcript。"""
    answer = interrupt({"question": "test"})
    return {"transcript": [{"round": 1, "question": "test", "answer": answer}]}


def build_graph(checkpointer):
    b = StateGraph(InterviewState)
    b.add_node("ask", ask)
    b.add_edge(START, "ask")
    b.add_edge("ask", END)
    return b.compile(checkpointer=checkpointer)


def run():
    print("=" * 70)
    print("MockInterviewState 序列化往返验证")
    print("=" * 70)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 填满复杂面试数据的初始状态
    init = {
        "persona": {
            "tone": "风趣",
            "role": {"company": "字节", "position": "高级产品经理", "seniority": "资深"},
            "stress_mode": False,
            "style_prompt": "语气轻松、爱用比喻",
        },
        "profile_snapshot": {
            "name": "张三",
            "work_descriptions": ["负责 A 产品 0-1", "带 5 人团队"],
            "project_descriptions": ["项目 X：提升了 20% 转化"],
        },
        "running_scores": {"communication": 70, "logic": 65, "expertise": 80, "resilience": 60, "fit": 75},
        "question_bank": [
            {"stem": "讲一次 push 团队的经历", "probing_points": ["数据？", "冲突？"], "ideal_signals": ["量化", "反思"]},
        ],
        "transcript": [],
    }

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cp = SqliteSaver(conn)
    cp.setup()
    graph = build_graph(cp)
    config = {"configurable": {"thread_id": "state-test"}}

    # 跑到 interrupt 存盘
    graph.invoke(init, config)
    # 恢复，写一轮 transcript
    graph.invoke(Command(resume="这是我的回答，含具体数据。"), config)

    state = graph.get_state(config).values
    conn.close()

    # 比对各字段
    checks = [
        ("persona 嵌套 dict 无损", state["persona"] == init["persona"]),
        ("profile_snapshot 无损", state["profile_snapshot"] == init["profile_snapshot"]),
        ("running_scores 无损", state["running_scores"] == init["running_scores"]),
        ("question_bank 无损", state["question_bank"] == init["question_bank"]),
        ("transcript reducer 累加", len(state["transcript"]) == 1 and state["transcript"][0]["answer"] == "这是我的回答，含具体数据。"),
    ]

    all_pass = True
    for name, ok in checks:
        print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")
        if not ok:
            all_pass = False
            print(f"        期望: {init.get(name.split(' ')[0].lower(), '...')}")
            print(f"        实际: {state.get(name.split(' ')[0].lower(), '...')}")

    print("\n" + "=" * 70)
    print(f"总结：{'✅ State 序列化往返无损' if all_pass else '❌ 有字段丢失，需排查'}")
    print("=" * 70)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return all_pass


if __name__ == "__main__":
    run()
