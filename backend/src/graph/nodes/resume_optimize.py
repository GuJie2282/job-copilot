"""
简历优化 LangGraph 节点（resume_optimize）—— 路径 A（自动迭代流水线）

子图结构与 JD 匹配同构（对应 design.md 决策 1 / 原则 4）：
  resume_prepare → resume_generate → resume_evaluate ─┐
                       ▲                               ├─ 重试（不通过且未达上限）
                       └───────────────────────────────┘
                  → resume_validate ─┐
                       ▲              ├─ 修复（格式 ERROR 且未达上限）
                       └──────────────┘
                  → resume_export → resume_persist → END

迭代控制：resume_round 统一计「生成次数」（评估重试 + 校验修复共用），
         达 resume_max_rounds（默认 3）强制交付，防无限循环。

路径 B（人机协同精修）的节点（resume_refine / resume_finalize）在 Phase 5 接入，
本文件仅实现路径 A。

作者：求职 Copilot 项目
日期：2026-07-22
"""

import logging
from typing import Dict, Any

from langchain_core.messages import AIMessage
from langgraph.types import StreamWriter

from src.services.resume_generator import (
    generate_resume,
    generate_resume_stream,
    generate_resume_reasoning_stream,
    _clean_markdown,
)
from src.services.resume_evaluator import evaluate_resume
from src.services.resume_validator import validate_resume_md
from src.services.profile_service import get_profile
from src.services.resume_store_service import save_resume
from src.services.resume_exporter import export_resume
from src.models.profile import JdMatchResultModel
from src.models.base import SessionLocal

logger = logging.getLogger(__name__)


# ============================================================================
# 1. resume_prepare_node：就绪性检查（画像 / Gap / 岗位）
# ============================================================================

def resume_prepare_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    加载画像 + Gap 快照 + 岗位，做就绪性检查。

    - 画像缺失 → resume_status_code=profile_missing（条件边→END 引导）
    - Gap：优先用 state.gaps_snapshot（API 直接传入），否则从 jd_result_id 关联的匹配结果读；
      无 Gap → gaps_snapshot=[]，标记为通用生成（不阻断）
    - 拷贝画像与 Gap 为快照，保证生成过程中一致
    """
    user_id = state.get("user_id")
    target_position = (state.get("target_position") or "").strip()

    if not target_position:
        return {
            "resume_status_code": "error",
            "messages": [AIMessage(content="❌ 未提供目标岗位")],
        }

    if not user_id:
        return {
            "resume_status_code": "profile_missing",
            "messages": [AIMessage(content="❌ 未识别到用户，请先登录并建立画像")],
        }

    # 读画像
    db = SessionLocal()
    try:
        profile = get_profile(db, user_id)
        if profile is None:
            return {
                "resume_status_code": "profile_missing",
                "messages": [AIMessage(content="❌ 尚未建立个人画像，请先上传简历建立画像后再生成简历")],
            }
    finally:
        db.close()

    # 读 Gap：优先 snapshot，其次关联匹配结果
    gaps = state.get("gaps_snapshot")
    if gaps is None:
        jd_result_id = state.get("jd_result_id")
        gaps = []
        if jd_result_id:
            db = SessionLocal()
            try:
                row = db.query(JdMatchResultModel).filter(JdMatchResultModel.id == jd_result_id).first()
                if row and row.gaps_json:
                    gaps = row.gaps_json
            finally:
                db.close()

    has_gaps = bool(gaps)
    return {
        "profile_snapshot": profile,      # 画像快照
        "gaps_snapshot": gaps,            # Gap 快照
        "resume_round": 0,                # 迭代计数清零
        "messages": [AIMessage(
            content=(f"✅ 就绪：岗位「{target_position}」，"
                     f"{'含 ' + str(len(gaps)) + ' 个 Gap 定向强化' if has_gaps else '通用生成（无 Gap）'}")
        )],
    }


# ============================================================================
# 2. resume_generate_node：调用生成服务
# ============================================================================

async def resume_generate_node(state: Dict[str, Any], writer: StreamWriter) -> Dict[str, Any]:
    """
    调用 resume_generator 生成 Markdown 简历（glm-4.5 reasoning），迭代轮次 +1。
    用 generate_resume_reasoning_stream 增量产出，逐 (kind, delta) 经 writer 推送 custom event：
      reasoning → SSE reasoning（AI 思考过程，前端思考区展示）
      content   → SSE token（简历正文）
    生成失败 → resume_status_code=llm_failed。
    """
    profile = state.get("profile_snapshot") or {}
    gaps = state.get("gaps_snapshot") or []
    target_position = state.get("target_position")
    jd_text = state.get("jd_text")
    try:
        content_parts: list = []
        async for kind, delta in generate_resume_reasoning_stream(profile, gaps, target_position, jd_text):
            # 推 custom event：reasoning 或 token，端点 astream custom 转 SSE
            writer({"type": "reasoning" if kind == "reasoning" else "token", "delta": delta})
            if kind == "content":
                content_parts.append(delta)
        md = _clean_markdown("".join(content_parts))
        if not md or len(md) < 50:
            raise ValueError(f"生成内容过短（{len(md)} 字符），可能生成失败")
        return {
            "resume_md": md,
            "resume_round": (state.get("resume_round") or 0) + 1,  # 生成次数 +1
            "messages": [AIMessage(content=f"✅ 简历草稿已生成（{len(md)} 字符）")],
        }
    except Exception as e:
        logger.error(f"简历生成失败：{e}")
        return {
            "resume_status_code": "llm_failed",
            "error": f"简历生成失败：{e}",
            "messages": [AIMessage(content=f"❌ 简历生成失败：{e}")],
        }


# ============================================================================
# 3. resume_evaluate_node：6 维评估（失败降级）
# ============================================================================

def resume_evaluate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 resume_evaluator 做 6 维评估。

    评估失败 → 降级：resume_eval 置 None，route_after_evaluate 据此跳到 validate
    （design 边界：评估失败降级为仅格式校验通过即交付）。
    """
    md = state.get("resume_md")
    target_position = state.get("target_position")
    gaps = state.get("gaps_snapshot") or []
    profile = state.get("profile_snapshot") or {}
    try:
        ev = evaluate_resume(md, target_position, gaps, profile)
        passed = ev.get("passed")
        score = ev.get("overall_score")
        return {
            "resume_eval": ev,
            "messages": [AIMessage(
                content=(f"✅ 评估完成：{score} 分（{'通过' if passed else '需改进'}）")
            )],
        }
    except Exception as e:
        logger.warning(f"简历评估失败（降级为仅格式校验）：{e}")
        return {
            "resume_eval": None,  # None 表示评估失败，route 据此降级
            "messages": [AIMessage(content=f"⚠️ 自动评估未完成（{e}），降级为仅格式校验，请人工复核")],
        }


# ============================================================================
# 4. resume_validate_node：格式硬校验
# ============================================================================

def resume_validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 resume_validator 做格式硬校验。

    校验结果并入 resume_eval.format_validation（供前端展示 + route 判定）。
    ERROR → route_after_validate 据此回 generate 修复（达上限则带 warning 交付）。
    """
    md = state.get("resume_md") or ""
    result = validate_resume_md(md)

    # 把格式校验结果并入评估报告（若评估失败 ev=None，这里建一个仅含 format_validation 的 dict）
    ev = dict(state.get("resume_eval") or {})
    ev["format_validation"] = {
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
    }

    if result.passed:
        msg = "✅ 格式校验通过"
    else:
        msg = f"⚠️ 格式校验有 {len(result.errors)} 个错误，将修复重试（或达上限带过）"
    return {"resume_eval": ev, "messages": [AIMessage(content=msg)]}


# ============================================================================
# 5. resume_export_node：装配 HTML + PDF（Phase 4 接入主题后补全）
# ============================================================================

def resume_export_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    装配 HTML 并套预览壳（Phase 4 已接入主题系统）。

    调 export_resume：选主题 → 装配 HTML → 套预览壳（A4 分页 + 打印 PDF）→ 审查 + 粗估页数。
    导出失败不阻断：HTML 留空，仍持久化 Markdown（前端可按 MD 预览，稍后重试导出）。
    """
    md = state.get("resume_md") or ""
    target_position = state.get("target_position") or ""
    # 标题 = 姓名-岗位（= 浏览器「另存为 PDF」默认文件名）
    name = (state.get("profile_snapshot") or {}).get("name") or "简历"
    avatar_url = (state.get("profile_snapshot") or {}).get("avatar_url") or ""
    title = f"{name}-{target_position}" if target_position else name

    try:
        result = export_resume(md, target_position, title, avatar_url)
        issues = result["audit"]["issues"]
        msg = (f"✅ HTML 导出完成（主题 {result['theme']}，"
               f"约 {result['pages']['estimated_pages']} 页）")
        if issues:
            msg += f"；装配审查：{'；'.join(issues)}"
        return {
            "resume_html": result["html"],
            "resume_theme": result["theme"],
            "messages": [AIMessage(content=msg)],
        }
    except Exception as e:
        logger.error(f"HTML 导出失败：{e}")
        return {
            "resume_html": None,
            "messages": [AIMessage(content=f"⚠️ HTML 导出失败（{e}），已持久化 Markdown，可稍后重试导出")],
        }


# ============================================================================
# 6. resume_persist_node：落库 + 返回报告
# ============================================================================

def resume_persist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    持久化简历到 resumes 表（status=draft，版本自动），返回 resume_id 与评估报告。

    标记 resume_refine_offered=True，前端据此展示「精修」入口（路径 B）。
    """
    user_id = state.get("user_id")
    target_position = state.get("target_position")
    md = state.get("resume_md")
    ev = state.get("resume_eval") or {}
    score = ev.get("overall_score")
    theme = state.get("resume_theme")
    jd_result_id = state.get("jd_result_id")

    resume_id, version = None, None
    if user_id:
        db = SessionLocal()
        try:
            row = save_resume(
                db, user_id, target_position,
                content_md=md,
                html=state.get("resume_html"),
                eval_report=ev or None,
                eval_score=score,
                theme=theme,
                jd_result_id=jd_result_id,
                status="draft",
            )
            resume_id, version = row.id, row.version
        except Exception as e:
            logger.error(f"简历持久化失败：{e}")
            db.rollback()
        finally:
            db.close()

    return {
        "resume_id": resume_id,
        "resume_version": version,
        "resume_status": "draft",
        "resume_status_code": "success",
        "resume_refine_offered": True,
        "messages": [AIMessage(
            content=(f"✅ 简历生成完成（v{version}，评估 {score if score is not None else '未评估'} 分）"
                     "，可进入精修或直接使用")
        )],
    }


# ============================================================================
# 条件边函数（控制流转 / 失败分支 / 迭代）
# ============================================================================

def route_after_prepare(state: Dict[str, Any]) -> str:
    """prepare 后：画像缺失/出错 → END；否则 → generate"""
    code = state.get("resume_status_code")
    if code in ("profile_missing", "error"):
        return "end"
    return "generate"


def route_after_generate(state: Dict[str, Any]) -> str:
    """generate 后：LLM 失败 → END；否则 → evaluate"""
    return "end" if state.get("resume_status_code") == "llm_failed" else "evaluate"


def route_after_evaluate(state: Dict[str, Any]) -> str:
    """
    evaluate 后：
    - 评估失败（resume_eval=None，降级）→ validate
    - 评估通过 → validate
    - 不通过且未达上限 → generate（重试）
    - 不通过但达上限 → validate（带不通过项交付）
    """
    ev = state.get("resume_eval")
    if ev is None:
        return "validate"  # 降级
    if ev.get("passed"):
        return "validate"
    if (state.get("resume_round") or 0) >= (state.get("resume_max_rounds") or 3):
        return "validate"  # 达上限
    return "generate"  # 重试


def route_after_validate(state: Dict[str, Any]) -> str:
    """
    validate 后：
    - 格式无 ERROR → export
    - 有 ERROR 且未达上限 → generate（修复）
    - 有 ERROR 但达上限 → export（带 warning 交付，不无限循环）
    """
    ev = state.get("resume_eval") or {}
    fmt = ev.get("format_validation") or {}
    passed = fmt.get("passed", True)
    if passed:
        return "export"
    if (state.get("resume_round") or 0) >= (state.get("resume_max_rounds") or 3):
        return "export"  # 达上限，带过
    return "generate"  # 修复
