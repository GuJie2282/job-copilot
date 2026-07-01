"""
LangGraph 图定义（项目核心）。

这里把"节点"和"边"组装成一张状态机图。
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import AgentState
from src.nodes.chatbot import chatbot


def build_graph():
    """
    构建并编译 Agent 图。

    当前 MVP 结构：START → chatbot → END
    用 MemorySaver 做 checkpointer，实现多轮对话记忆。

    后续版本会在这里加更多节点和条件边（意图路由）：
        START → router → (profile | jd_match | resume | interview) → END
    """
    # 1. 创建状态图，指定状态类型是 AgentState
    builder = StateGraph(AgentState)

    # 2. 添加节点
    builder.add_node("chatbot", chatbot)

    # 3. 添加边：起点 → chatbot → 终点
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)

    # 4. 编译（加 checkpointer 开启记忆）
    return builder.compile(checkpointer=MemorySaver())


# 模块加载时构建好图，供 main.py 使用
graph = build_graph()
