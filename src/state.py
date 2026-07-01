"""
状态定义。

LangGraph 的核心思想：所有节点共享并读写同一个 State。
这个文件定义 State 长什么样。
"""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Agent 的共享状态。

    - messages：对话历史。
      Annotated[..., add_messages] 表示"新消息会自动追加到列表"，而不是覆盖。
      这是多轮对话能记住上下文的关键（reducer 机制）。
    """
    messages: Annotated[list, add_messages]

    # ===== 以下字段为后续版本扩展预留（MVP 暂未使用）=====
    # user_profile: dict    # 用户画像（结构化）
    # current_jd: str       # 当前分析的目标岗位 JD
    # intent: str           # 当前用户意图
