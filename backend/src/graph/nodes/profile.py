"""
简历解析节点（LangGraph）

功能：
1. 路由节点（判断用户意图）
2. 文件解析节点（解析 PDF/Word）
3. 文本验证节点（验证粘贴文本）
4. 质量检测节点（检测文本质量）
5. 画像提取节点（LLM 提取）
6. 置信度计算节点（计算置信度）
7. 结果格式化节点（格式化输出）

作者：求职 Copilot 项目
日期：2026-07-03
"""

import json
import os
import tempfile
from typing import Dict, Any, Optional, Literal
from pathlib import Path

# LangGraph 相关
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END

# 本地服务
from src.services.resume_parser import parse_resume
from src.services.quality_checker import (
    check_text_quality,
    calculate_profile_confidence,
    format_quality_report,
    format_confidence_report
)
from src.graph.config import get_llm, get_structured_llm, UserProfile
from src.graph.prompts import get_extraction_prompt, create_chat_prompt_template
from src.services.llm_retry import invoke_llm_with_retry


# ============================================================================
# 1. 路由节点（router_node）
# ============================================================================

def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    路由节点：判断用户意图并分发到对应节点

    Args:
        state: 当前状态

    Returns:
        updated_state: 更新后的状态

    路由规则：
    - 如果 intent 是 "profile_parse"，进入简历解析流程
    - 如果 intent 是 "chat"，进入对话流程
    - 其他情况返回错误
    """
    intent = state.get("intent")

    if intent == "profile_parse":
        return {
            "current_step": "profile_parse",
            "messages": [SystemMessage(content="开始简历解析流程...")]
        }
    elif intent == "chat":
        return {
            "current_step": "chat",
        }
    elif intent == "jd_match":
        return {
            "current_step": "jd_match",
        }
    else:
        return {
            "error": f"未知的意图: {intent}",
            "current_step": "error"
        }


# ============================================================================
# 2. 文件解析节点（file_parser_node）
# ============================================================================

def file_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    文件解析节点：解析 PDF 或 Word 文件

    Args:
        state: 当前状态（应包含 resume_file_path）

    Returns:
        updated_state: 更新后的状态
        - resume_text: 提取的文本
        - parse_status: 解析状态
        - parse_warnings: 警告列表
        - parse_error: 错误信息
    """
    file_path = state.get("resume_file_path")

    if not file_path or not os.path.exists(file_path):
        return {
            "parse_status": "error",
            "parse_error": f"文件不存在: {file_path}",
            "messages": [AIMessage(content="❌ 文件不存在，请重新上传。")]
        }

    try:
        # 解析文件
        result, error = parse_resume(file_path)

        if error:
            return {
                "parse_status": "error",
                "parse_error": error,
                "messages": [AIMessage(content=f"❌ 解析失败：{error}")]
            }

        # 解析成功
        text = result.get("text", "")
        parser = result.get("parser", "unknown")
        file_size = result.get("file_size", 0)

        # 返回结果
        message = f"✅ 文件解析成功！\n"
        message += f"- 使用的解析器: {parser}\n"
        message += f"- 文件大小: {file_size / 1024:.2f} KB\n"
        message += f"- 提取的文本长度: {len(text)} 字符"

        return {
            "resume_text": text,
            "parse_status": "success",
            "messages": [AIMessage(content=message)]
        }

    except Exception as e:
        return {
            "parse_status": "error",
            "parse_error": f"文件解析异常: {str(e)}",
            "messages": [AIMessage(content=f"❌ 解析异常：{str(e)}")]
        }


# ============================================================================
# 3. 文本验证节点（text_validation_node）
# ============================================================================

def text_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    文本验证节点：验证粘贴的文本

    Args:
        state: 当前状态（应包含 resume_text）

    Returns:
        updated_state: 更新后的状态
    """
    text = state.get("resume_text", "")

    if not text or len(text.strip()) < 50:
        return {
            "parse_status": "error",
            "parse_error": "文本过短，请提供完整的简历文本（至少 50 字符）。",
            "messages": [AIMessage(content="❌ 文本过短，请提供完整的简历文本。")]
        }

    # 文本验证通过
    return {
        "parse_status": "success",
        "messages": [AIMessage(content="✅ 文本验证通过。")]
    }


# ============================================================================
# 4. 质量检测节点（quality_check_node）
# ============================================================================

def quality_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    质量检测节点：检测文本质量

    Args:
        state: 当前状态（应包含 resume_text）

    Returns:
        updated_state: 更新后的状态
        - profile_quality_score: 质量分数
        - parse_warnings: 警告列表
    """
    text = state.get("resume_text", "")

    if not text:
        return {
            "parse_status": "error",
            "parse_error": "文本为空，无法进行质量检测。",
            "messages": [AIMessage(content="❌ 文本为空。")]
        }

    # 进行质量检测
    quality_score, warnings = check_text_quality(text)

    # 生成质量报告
    report = format_quality_report(quality_score, warnings)

    # 返回结果
    return {
        "profile_quality_score": quality_score,
        "parse_warnings": warnings,
        "messages": [AIMessage(content=report)]
    }


# ============================================================================
# 5. 画像提取节点（profile_extraction_node）
# ============================================================================

def profile_extraction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    画像提取节点：使用 LLM 从文本中提取结构化画像

    Args:
        state: 当前状态（应包含 resume_text 和 profile_quality_score）

    Returns:
        updated_state: 更新后的状态
        - user_profile: 提取的画像
        - parse_status: 解析状态
    """
    text = state.get("resume_text", "")
    quality_score = state.get("profile_quality_score", 1.0)

    if not text:
        return {
            "parse_status": "error",
            "parse_error": "文本为空，无法提取画像。",
            "messages": [AIMessage(content="❌ 文本为空。")]
        }

    try:
        # 获取 LLM 实例
        llm = get_structured_llm(schema=UserProfile, temperature=0.0, tier="strong")  # 简历解析：主力档

        # 获取合适的 Prompt
        prompt = get_extraction_prompt(
            resume_text=text,
            quality_score=quality_score,
            is_retry=False
        )

        # 调用 LLM（带 API 异常重试）
        profile = invoke_llm_with_retry(llm, prompt)

        # 转换为字典格式
        profile_dict = profile.model_dump()

        # 返回结果
        message = "✅ 画像提取成功！\n"
        message += f"- 姓名: {profile_dict.get('name', '未提取')}\n"
        message += f"- 邮箱: {profile_dict.get('email', '未提取')}\n"
        message += f"- 教育经历: {len(profile_dict.get('schools', []))} 条\n"
        message += f"- 工作经历: {len(profile_dict.get('companies', []))} 条"

        return {
            "user_profile": profile_dict,
            "parse_status": "success",
            "messages": [AIMessage(content=message)]
        }

    except Exception as e:
        return {
            "parse_status": "error",
            "parse_error": f"LLM 提取失败: {str(e)}",
            "messages": [AIMessage(content=f"❌ 提取失败：{str(e)}")]
        }


# ============================================================================
# 6. 置信度计算节点（confidence_calc_node）
# ============================================================================

def confidence_calc_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    置信度计算节点：计算画像的置信度

    Args:
        state: 当前状态（应包含 user_profile 和 resume_text）

    Returns:
        updated_state: 更新后的状态
        - profile_confidence: 置信度结果
    """
    profile = state.get("user_profile")
    text = state.get("resume_text", "")

    if not profile or not text:
        return {
            "messages": [AIMessage(content="⚠️ 无法计算置信度（缺少画像或文本）。")]
        }

    # 计算置信度
    confidence_result = calculate_profile_confidence(profile, text)

    # 生成置信度报告
    report = format_confidence_report(confidence_result)

    # 返回结果
    return {
        "profile_confidence": confidence_result,
        "messages": [AIMessage(content=report)]
    }


# ============================================================================
# 7. 结果格式化节点（result_formatter_node）
# ============================================================================

def result_formatter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    结果格式化节点：格式化最终结果

    Args:
        state: 当前状态

    Returns:
        updated_state: 更新后的状态
    """
    profile = state.get("user_profile")
    quality_score = state.get("profile_quality_score", 0.0)
    confidence = state.get("profile_confidence", {})

    # 生成最终报告
    report = "\n" + "="*50 + "\n"
    report += "📊 简历解析完成\n"
    report += "="*50 + "\n\n"

    # 质量分数
    if quality_score >= 0.8:
        quality_level = "高质量"
    elif quality_score >= 0.6:
        quality_level = "中等质量"
    else:
        quality_level = "低质量"

    report += f"文本质量: {quality_score:.2f} ({quality_level})\n\n"

    # 画像摘要
    if profile:
        report += "基本信息:\n"
        report += f"- 姓名: {profile.get('name', '未提取')}\n"
        report += f"- 邮箱: {profile.get('email', '未提取')}\n"
        report += f"- 电话: {profile.get('phone', '未提取')}\n\n"

        # 统计高置信度字段
        high_conf_count = sum(1 for v in confidence.values() if v.get("score", 0) >= 0.8)
        total_count = len(confidence)

        report += f"置信度: {high_conf_count}/{total_count} 个字段为高置信度 (≥80%)\n\n"

    report += "="*50 + "\n"
    report += "✅ 解析完成！您可以：\n"
    report += "1. 查看完整画像\n"
    report += "2. 编辑画像信息\n"
    report += "3. 继续使用其他功能（JD 匹配、简历优化等）\n"

    return {
        "messages": [AIMessage(content=report)],
        "awaiting_confirmation": True
    }


# ============================================================================
# 8. 对话节点（chatbot_node）
# ============================================================================

def chatbot_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    对话节点：处理普通对话

    Args:
        state: 当前状态

    Returns:
        updated_state: 更新后的状态
    """
    messages = state.get("messages", [])

    if not messages:
        return {
            "messages": [AIMessage(content="你好！我是求职 Copilot，有什么可以帮你的？")]
        }

    # 获取 LLM 实例
    llm = get_llm(temperature=0.7, tier="fast")  # 对话节点：快档（延迟敏感）

    # 获取 Prompt 模板
    prompt_template = create_chat_prompt_template()

    # 调用 LLM
    response = llm.invoke(prompt_template.format_messages(messages=messages))

    return {
        "messages": [response]
    }


# ============================================================================
# 9. 条件边函数（conditional edges）
# ============================================================================

def should_continue_parsing(state: Dict[str, Any]) -> Literal["profile_extraction", "end"]:
    """
    判断是否继续解析

    规则：
    - 如果质量分数 >= 0.4，继续解析
    - 如果质量分数 < 0.4，结束（建议用户手动填写）
    """
    quality_score = state.get("profile_quality_score", 1.0)

    if quality_score >= 0.4:
        return "profile_extraction"
    else:
        return "end"


def should_calculate_confidence(state: Dict[str, Any]) -> Literal["confidence_calc", "end"]:
    """
    判断是否计算置信度

    规则：
    - 如果画像提取成功，继续计算置信度
    - 如果提取失败，结束
    """
    parse_status = state.get("parse_status")

    if parse_status == "success":
        return "confidence_calc"
    else:
        return "end"


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("简历解析节点测试")
    print("=" * 60)

    # 测试状态
    test_state = {
        "messages": [],
        "user_id": "test_user",
        "intent": "profile_parse",
        "resume_text": "张三\n电话：13800138000\n邮箱：zhangsan@example.com",
    }

    # 测试质量检测节点
    print("\n[TEST] 质量检测节点")
    result = quality_check_node(test_state)
    print(f"✓ 质量分数: {result.get('profile_quality_score')}")
    print(f"✓ 警告数量: {len(result.get('parse_warnings', []))}")

    print("\n" + "=" * 60)
