"""
JD 匹配 LangGraph 节点（jd_match）

子图结构与简历解析同构（对应 design.md 决策 8）：
  jd_intake → jd_quality_check → jd_parsing → profile_load
            → match_calc → gap_analysis → report_format

每个节点接收 state、返回 state 部分更新；条件边处理失败分支
（JD 无效 → END；画像缺失 → END 引导；LLM/计算失败 → END 降级）。

作者：求职 Copilot 项目
日期：2026-07-14
"""

import logging
from typing import Dict, Any

from langchain_core.messages import AIMessage
from langgraph.types import StreamWriter

from src.services.jd_parser import parse_jd, _extract_json, JobProfile
from src.services.llm_reasoning import stream_chat_with_reasoning
from src.graph.prompts import get_jd_parsing_prompt
from src.services.matcher import calculate_match
from src.services.gap_analyzer import build_gap_skeleton
from src.services.profile_service import get_profile, get_profile_confidence
from src.models.profile import JdMatchResultModel
from src.models.base import SessionLocal

logger = logging.getLogger(__name__)

# JD 输入约束
MIN_JD_LENGTH = 200
# 用于判断"是不是 JD"的典型结构关键词
JD_KEYWORDS = ["职责", "要求", "任职", "资格", "岗位", "负责", "职位", "我们需要"]


# ============================================================================
# 1. jd_intake_node：接收 JD + 长度校验
# ============================================================================

def jd_intake_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """接收 JD 文本，做基本长度校验。"""
    jd_text = (state.get("jd_text") or "").strip()
    if not jd_text:
        return {
            "match_status": "jd_invalid",
            "messages": [AIMessage(content="❌ 未收到 JD 文本")],
        }
    if len(jd_text) < MIN_JD_LENGTH:
        return {
            "match_status": "jd_invalid",
            "messages": [AIMessage(
                content=f"⚠️ JD 内容过少（{len(jd_text)} 字符），建议至少 {MIN_JD_LENGTH} 字符以便准确分析"
            )],
        }
    return {
        "match_status": "pending",
        "messages": [AIMessage(content="✅ 已接收 JD，开始分析...")],
    }


# ============================================================================
# 2. jd_quality_check_node：JD 质量门（结构关键词）
# ============================================================================

def jd_quality_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """检查 JD 是否含典型结构关键词，避免非 JD 内容进入解析。"""
    jd_text = state.get("jd_text", "")
    hit = [k for k in JD_KEYWORDS if k in jd_text]
    if not hit:
        return {
            "match_status": "jd_invalid",
            "messages": [AIMessage(
                content="⚠️ 未识别到典型 JD 结构（缺少「职责/要求/任职」等关键词），请确认粘贴的是职位描述"
            )],
        }
    return {"messages": [AIMessage(content=f"✅ JD 质量检查通过（命中关键词：{', '.join(hit[:3])}）")]}


# ============================================================================
# 3. jd_parsing_node：LLM 解析 JD → job_profile
# ============================================================================

async def jd_parsing_node(state: Dict[str, Any], writer: StreamWriter) -> Dict[str, Any]:
    """
    调用 LLM 把 JD 解析为四分类要求画像（glm-4.5 reasoning）。
    reasoning 经 writer 推 custom event（前端思考区），content 收集后解析为 job_profile。
    """
    jd_text = state.get("jd_text", "")
    if not jd_text or not jd_text.strip():
        return {
            "match_status": "error",
            "error": "JD 文本为空，无法解析",
            "messages": [AIMessage(content="❌ JD 文本为空，无法解析")],
        }
    try:
        prompt = get_jd_parsing_prompt(jd_text)
        content_parts: list = []
        async for kind, delta in stream_chat_with_reasoning(prompt, temperature=0.0, timeout=120.0):
            writer({"type": "reasoning" if kind == "reasoning" else "token", "delta": delta})
            if kind == "content":
                content_parts.append(delta)
        data = _extract_json("".join(content_parts))
        job_profile = JobProfile(**data).model_dump()
        n = sum(
            len(job_profile.get(c, []))
            for c in ("hard_skills", "soft_skills", "implicit_preferences", "red_lines")
        )
        return {
            "job_profile": job_profile,
            "messages": [AIMessage(
                content=f"✅ JD 解析完成：岗位「{job_profile.get('position_title') or '未知'}」，共 {n} 条要求"
            )],
        }
    except Exception as e:
        logger.error(f"JD 解析失败：{e}")
        return {
            "match_status": "error",
            "error": f"JD 解析失败：{e}",
            "messages": [AIMessage(content=f"❌ JD 解析失败：{e}")],
        }


# ============================================================================
# 4. profile_load_node：读用户画像（缺失则引导）
# ============================================================================

def profile_load_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """从 user_profiles 表读取用户画像。缺失则设 profile_missing。"""
    user_id = state.get("user_id")
    if not user_id:
        return {
            "match_status": "profile_missing",
            "messages": [AIMessage(content="❌ 未识别到用户，请先登录并建立画像")],
        }
    db = SessionLocal()
    try:
        profile = get_profile(db, user_id)
        if profile is None:
            return {
                "match_status": "profile_missing",
                "messages": [AIMessage(content="❌ 尚未建立个人画像，请先上传简历建立画像后再进行 JD 匹配")],
            }
        confidence = get_profile_confidence(db, user_id)
        # 画像存入 state（复用 user_profile 键），供 match_calc / gap_analysis 使用
        return {
            "user_profile": profile,
            "match_confidence": confidence,
        }
    finally:
        db.close()


# ============================================================================
# 5. match_calc_node：匹配计算
# ============================================================================

def match_calc_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """调用 matcher 计算匹配度（含隐性 LLM 判断）。"""
    job_profile = state.get("job_profile")
    user_profile = state.get("user_profile")
    confidence = state.get("match_confidence")
    if not job_profile or not user_profile:
        return {
            "match_status": "error",
            "messages": [AIMessage(content="❌ 缺少 JD 要求或用户画像，无法匹配")],
        }
    try:
        # with_implicit=False：评分链跳过隐性偏好 LLM（不影响总分），隐性项交由增补链 enrich
        result = calculate_match(job_profile, user_profile, confidence, with_implicit=False)
        dims = result["dimension_scores"]
        return {
            "match_result": result,
            "messages": [AIMessage(
                content=(f"✅ 匹配完成：总分 {result['overall_score']}（{result['level']}）｜"
                         f"技能 {dims['skill']} 经验 {dims['experience']} "
                         f"学历 {dims['education']} 软技能 {dims['soft_skill']}")
            )],
        }
    except Exception as e:
        logger.error(f"匹配计算失败：{e}")
        return {
            "match_status": "error",
            "error": str(e),
            "messages": [AIMessage(content=f"❌ 匹配计算失败：{e}")],
        }


# ============================================================================
# 6. report_format_node：写库（评分链终点）+ 组装报告骨架
# ============================================================================
# 注：原 gap_analysis 节点（隐性判断 + Gap 建议 LLM）已移出主图，改由独立的
# /api/jd/{id}/enrich 增补端点处理——评分链只剩 1 次 LLM（JD 解析），分数秒出。
# 此节点负责：生成规则 Gap 骨架（隐性占位"分析中"）+ 持久化 + 组装报告。

def report_format_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """持久化匹配结果到 jd_match_results，并组装报告消息。"""
    user_id = state.get("user_id")
    match_result = state.get("match_result", {})
    job_profile = state.get("job_profile", {})
    gaps = build_gap_skeleton(job_profile, match_result)  # 规则骨架（隐性占位"分析中"），无 LLM
    jd_text = state.get("jd_text", "")
    confidence = state.get("match_confidence")
    dims = match_result.get("dimension_scores", {})

    # 持久化匹配结果
    result_id = None
    if user_id:
        db = SessionLocal()
        try:
            row = JdMatchResultModel(
                user_id=user_id,
                jd_text=jd_text,
                overall_score=match_result.get("overall_score"),
                skill_score=dims.get("skill"),
                experience_score=dims.get("experience"),
                education_score=dims.get("education"),
                soft_skill_score=dims.get("soft_skill"),
                job_profile_json=job_profile,
                gaps_json=gaps,
                confidence_json=confidence,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            result_id = row.id
        except Exception as e:
            logger.error(f"匹配结果持久化失败：{e}")
            db.rollback()
        finally:
            db.close()

    # 组装报告
    overall = match_result.get("overall_score", 0)
    level = match_result.get("level", "")
    report = f"📊 JD 匹配报告\n{'=' * 40}\n总分：{overall}（{level}）\n"
    report += (f"技能 {dims.get('skill')} | 经验 {dims.get('experience')} | "
               f"学历 {dims.get('education')} | 软技能 {dims.get('soft_skill')}\n")
    if match_result.get("redline_hit"):
        report += "🚨 存在未满足的红线项，详见 Gap 清单\n"
    report += f"Gap 数量：{len(gaps)}\n{'=' * 40}"

    return {
        "result_id": result_id,
        "match_status": "success",
        "gaps": gaps,  # 规则 Gap 骨架（供 SSE done 事件下发；增补建议由 enrich 端点回填）
        "messages": [AIMessage(content=report)],
    }


# ============================================================================
# 条件边函数（控制流转 / 失败分支）
# ============================================================================

def route_after_intake(state: Dict[str, Any]) -> str:
    """intake 后：JD 无效 → END；否则 → quality_check"""
    return "end" if state.get("match_status") == "jd_invalid" else "quality"


def route_after_quality(state: Dict[str, Any]) -> str:
    """quality 后：无效 → END；否则 → parsing"""
    return "end" if state.get("match_status") == "jd_invalid" else "parsing"


def route_after_parsing(state: Dict[str, Any]) -> str:
    """parsing 后：失败 → END；否则 → profile_load"""
    return "end" if state.get("match_status") == "error" else "profile_load"


def route_after_profile_load(state: Dict[str, Any]) -> str:
    """profile_load 后：画像缺失 → END（引导建画像）；否则 → match_calc"""
    return "end" if state.get("match_status") == "profile_missing" else "match_calc"


def route_after_match(state: Dict[str, Any]) -> str:
    """match_calc 后：失败 → END；否则 → report_format（评分链终点，持久化骨架）"""
    return "end" if state.get("match_status") == "error" else "report"
