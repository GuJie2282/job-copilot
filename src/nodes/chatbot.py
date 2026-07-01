"""
对话节点（MVP 核心节点）。

一个节点 = 一个函数：接收 state，返回 state 的部分更新。
这个节点做的事：带上"求职教练"人设，调用 LLM 回复用户。
"""
from langchain_core.messages import SystemMessage

from src.config import get_llm
from src.state import AgentState
from src.prompts import SYSTEM_PROMPT

# 模块加载时创建一次 LLM（启动时即可校验 API Key 是否配置）
llm = get_llm()


def chatbot(state: AgentState) -> dict:
    """
    求职教练对话节点。

    输入：state（含历史 messages）
    输出：{"messages": [AI 的回复]} —— 会自动追加到对话历史
    """
    # 1. 把"人设"放在对话最前面，让模型始终记得自己是谁
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # 2. 调用 LLM 生成回复
    response = llm.invoke(messages)

    # 3. 返回新消息（add_messages 会自动把它追加进历史）
    return {"messages": [response]}
