"""
LangGraph 状态机构建

功能：
1. 构建求职 Copilot 的状态机图
2. 注册所有节点和边
3. 支持对话和简历解析流程

作者：求职 Copilot 项目
日期：2026-07-03
"""

import os
from langgraph.graph import StateGraph, END
from typing import Dict, Any

# 导入状态定义
from src.graph.state import FullAgentState, create_initial_state

# 导入节点
from src.graph.nodes.profile import (
    router_node,
    file_parser_node,
    text_validation_node,
    quality_check_node,
    profile_extraction_node,
    confidence_calc_node,
    result_formatter_node,
    chatbot_node,
    should_continue_parsing,
    should_calculate_confidence,
)

# 导入 JD 匹配节点（区块二）
from src.graph.nodes.jd_match import (
    jd_intake_node,
    jd_quality_check_node,
    jd_parsing_node,
    profile_load_node,
    match_calc_node,
    gap_analysis_node,
    report_format_node,
    route_after_intake,
    route_after_quality,
    route_after_parsing,
    route_after_profile_load,
    route_after_match,
)

# 导入简历优化节点（区块三：路径 A 自动生成）
from src.graph.nodes.resume_optimize import (
    resume_prepare_node,
    resume_generate_node,
    resume_evaluate_node,
    resume_validate_node,
    resume_export_node,
    resume_persist_node,
    route_after_prepare,
    route_after_generate,
    route_after_evaluate,
    route_after_validate,
)


# ============================================================================
# 创建状态机图
# ============================================================================

def create_graph() -> StateGraph:
    """
    创建求职 Copilot 的状态机图

    Returns:
        graph: StateGraph 实例

    状态机结构：
    - START → router → [chatbot | file_parser | text_validation]
    - file_parser → quality_check → [profile_extraction | END]
    - text_validation → quality_check → [profile_extraction | END]
    - profile_extraction → confidence_calc → result_formatter → END
    - chatbot → END
    """

    # 创建状态机
    builder = StateGraph(FullAgentState)

    # ========================================================================
    # 添加节点
    # ========================================================================

    # 路由节点（判断意图）
    builder.add_node("router", router_node)

    # 简历解析流程节点
    builder.add_node("file_parser", file_parser_node)
    builder.add_node("text_validation", text_validation_node)
    builder.add_node("quality_check", quality_check_node)
    builder.add_node("profile_extraction", profile_extraction_node)
    builder.add_node("confidence_calc", confidence_calc_node)
    builder.add_node("result_formatter", result_formatter_node)

    # 对话节点
    builder.add_node("chatbot", chatbot_node)

    # JD 匹配流程节点（区块二）
    builder.add_node("jd_intake", jd_intake_node)
    builder.add_node("jd_quality_check", jd_quality_check_node)
    builder.add_node("jd_parsing", jd_parsing_node)
    builder.add_node("profile_load", profile_load_node)
    builder.add_node("match_calc", match_calc_node)
    builder.add_node("gap_analysis", gap_analysis_node)
    builder.add_node("report_format", report_format_node)

    # 简历优化流程节点（区块三：路径 A 自动生成）
    builder.add_node("resume_prepare", resume_prepare_node)
    builder.add_node("resume_generate", resume_generate_node)
    builder.add_node("resume_evaluate", resume_evaluate_node)
    builder.add_node("resume_validate", resume_validate_node)
    builder.add_node("resume_export", resume_export_node)
    builder.add_node("resume_persist", resume_persist_node)

    # ========================================================================
    # 添加边（edges）
    # ========================================================================

    # 设置入口点
    builder.set_entry_point("router")

    # 添加条件边：router 根据意图分发
    # - profile_parse：按简历来源分流（文件 → file_parser，文本 → text_validation）
    # - jd_match：JD 匹配子图
    # - chat：普通对话
    def _route_intent(state):
        intent = state.get("intent", "chat")
        if intent == "profile_parse":
            return "text_validation" if state.get("resume_source") == "text" else "file_parser"
        return intent

    builder.add_conditional_edges(
        "router",
        _route_intent,
        {
            "file_parser": "file_parser",
            "text_validation": "text_validation",
            "jd_match": "jd_intake",
            "resume_optimize": "resume_prepare",
            "chat": "chatbot",
        }
    )

    # 简历解析流程
    builder.add_edge("file_parser", "quality_check")
    builder.add_edge("text_validation", "quality_check")

    # 质量检测后的条件边：决定是否继续解析
    builder.add_conditional_edges(
        "quality_check",
        should_continue_parsing,
        {
            "profile_extraction": "profile_extraction",  # 继续解析
            "end": END,  # 结束（质量太差）
        }
    )

    # 画像提取后的条件边：决定是否计算置信度
    builder.add_conditional_edges(
        "profile_extraction",
        should_calculate_confidence,
        {
            "confidence_calc": "confidence_calc",  # 计算置信度
            "end": END,  # 结束（提取失败）
        }
    )

    # 完成流程
    builder.add_edge("confidence_calc", "result_formatter")
    builder.add_edge("result_formatter", END)

    # 对话流程
    builder.add_edge("chatbot", END)

    # JD 匹配流程（条件边串联：每步无效/失败 → END）
    builder.add_conditional_edges(
        "jd_intake", route_after_intake,
        {"quality": "jd_quality_check", "end": END}
    )
    builder.add_conditional_edges(
        "jd_quality_check", route_after_quality,
        {"parsing": "jd_parsing", "end": END}
    )
    builder.add_conditional_edges(
        "jd_parsing", route_after_parsing,
        {"profile_load": "profile_load", "end": END}
    )
    builder.add_conditional_edges(
        "profile_load", route_after_profile_load,
        {"match_calc": "match_calc", "end": END}
    )
    builder.add_conditional_edges(
        "match_calc", route_after_match,
        {"gap": "gap_analysis", "end": END}
    )
    builder.add_edge("gap_analysis", "report_format")
    builder.add_edge("report_format", END)

    # 简历优化流程（路径 A：条件边串联，评估/校验失败回 generate 重试，达上限带过）
    builder.add_conditional_edges(
        "resume_prepare", route_after_prepare,
        {"generate": "resume_generate", "end": END}
    )
    builder.add_conditional_edges(
        "resume_generate", route_after_generate,
        {"evaluate": "resume_evaluate", "end": END}
    )
    builder.add_conditional_edges(
        "resume_evaluate", route_after_evaluate,
        {"validate": "resume_validate", "generate": "resume_generate"}  # generate 为回边（迭代重试）
    )
    builder.add_conditional_edges(
        "resume_validate", route_after_validate,
        {"export": "resume_export", "generate": "resume_generate"}  # generate 为回边（格式修复）
    )
    builder.add_edge("resume_export", "resume_persist")
    builder.add_edge("resume_persist", END)

    # ========================================================================
    # 编译图
    # ========================================================================

    graph = builder.compile()

    return graph


# ============================================================================
# 运行状态机
# ============================================================================

def run_graph(
    user_input: str,
    intent: str = "chat",
    user_id: str = None,
    resume_file_path: str = None,
    resume_text: str = None
) -> Dict[str, Any]:
    """
    运行状态机

    Args:
        user_input: 用户输入（对话内容）
        intent: 用户意图（chat, profile_parse）
        user_id: 用户 ID
        resume_file_path: 简历文件路径（如果 intent 是 profile_parse）
        resume_text: 简历文本（如果 intent 是 profile_parse 且来源是文本）

    Returns:
        final_state: 最终状态

    示例：
        >>> # 对话示例
        >>> result = run_graph("你好", intent="chat")
        >>> print(result["messages"][-1].content)

        >>> # 简历解析示例
        >>> result = run_graph(
        ...     "",
        ...     intent="profile_parse",
        ...     resume_file_path="resume.pdf"
        ... )
        >>> print(result["user_profile"])
    """
    # 创建状态机
    graph = create_graph()

    # 创建初始状态
    initial_state = create_initial_state(user_id=user_id)

    # 添加用户输入
    from langchain_core.messages import HumanMessage
    if user_input:
        initial_state["messages"].append(HumanMessage(content=user_input))

    # 设置意图
    initial_state["intent"] = intent

    # 设置简历相关字段
    if resume_file_path:
        initial_state["resume_source"] = "file"
        initial_state["resume_file_path"] = resume_file_path
        initial_state["resume_file_name"] = os.path.basename(resume_file_path)

    if resume_text:
        initial_state["resume_source"] = "text"
        initial_state["resume_text"] = resume_text

    # 运行状态机
    config = {"configurable": {"thread_id": user_id or "default"}}
    final_state = graph.invoke(initial_state, config)

    return final_state


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LangGraph 状态机测试")
    print("=" * 60)

    # 测试 1：对话
    print("\n[TEST 1] 对话测试")
    try:
        result = run_graph("你好！我想了解一下求职 Copilot。", intent="chat")
        print(f"✓ 对话完成")
        if result.get("messages"):
            print(f"✓ 回复: {result['messages'][-1].content[:100]}...")
    except Exception as e:
        print(f"✗ 对话失败: {e}")

    # 测试 2：文本解析
    print("\n[TEST 2] 文本解析测试")
    test_resume = """
    张三
    电话：13800138000
    邮箱：zhangsan@example.com

    教育背景
    清华大学 计算机科学与技术 本科 2018-2022

    工作经历
    ABC公司 软件工程师 2022-至今
    技能：Python, Java, 机器学习
    """

    try:
        result = run_graph(
            "",
            intent="profile_parse",
            resume_text=test_resume
        )
        print(f"✓ 解析完成")
        print(f"✓ 质量分数: {result.get('profile_quality_score')}")
        if result.get("user_profile"):
            print(f"✓ 姓名: {result['user_profile'].get('name')}")
            print(f"✓ 邮箱: {result['user_profile'].get('email')}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")

    print("\n" + "=" * 60)
    print("状态机测试完成")
    print("=" * 60)
