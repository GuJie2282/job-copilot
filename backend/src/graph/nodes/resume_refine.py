"""
简历精修 LangGraph 节点（resume_refine）—— 路径 B（人机协同，interrupt + checkpointer）

子图结构（同构 mock-interview 的长程会话范式）：
  refine_setup → refine ──interrupt(草稿+评估+反馈入口)──► [等用户反馈]
                    ▲                                          │
                    │                            Command(resume={action, feedback})
                    │                                          ▼
                    └────── route_after_refine ────────────────┘
                          (action=finalize → finalize；否则 refine 继续)
                                                   │ finalize
                                                   ▼
                                             finalize_node → END

核心机制：
- interrupt：refine 节点改写+评估后挂起，把草稿+评估+「待补充」提示交给前端，等用户反馈
- 路径 B 同构复用 mock-interview 的 checkpointer（get_interview_checkpointer），thread_id = resume 会话 ID
- 会话态（草稿/评估/轮次）在 checkpointer；仅 finalize 时落库（status=finalized）——会话态与持久态分离

作者：求职 Copilot 项目
日期：2026-07-22
"""

import re
import logging
from typing import Dict, Any, List, Optional

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from src.graph.state import FullAgentState
from src.graph.checkpointer import get_interview_checkpointer
from src.services.resume_generator import refine_resume
from src.services.resume_evaluator import evaluate_resume
from src.services.resume_validator import validate_resume_md
from src.services.resume_exporter import export_resume
from src.services.resume_store_service import get_resume, save_resume
from src.services.profile_service import get_profile
from src.models.base import SessionLocal
from src.models.profile import JdMatchResultModel

logger = logging.getLogger(__name__)


# ============================================================================
# 1. resume_refine_setup_node：加载草稿 + 画像 + gaps
# ============================================================================

def resume_refine_setup_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    加载要精修的草稿（resume_id）+ 画像 + gaps，准备进入精修循环。

    - 简历不存在 / 无权访问 → resume_status_code=error
    - 画像缺失 → resume_status_code=profile_missing
    """
    resume_id = state.get("resume_id")
    user_id = state.get("user_id")

    db = SessionLocal()
    try:
        row = get_resume(db, resume_id) if resume_id else None
        if row is None or row.user_id != user_id:
            return {
                "resume_status_code": "error",
                "messages": [AIMessage(content="❌ 简历不存在或无权访问")],
            }

        profile = get_profile(db, user_id) if user_id else None
        if profile is None:
            return {
                "resume_status_code": "profile_missing",
                "messages": [AIMessage(content="❌ 画像缺失，无法精修")],
            }

        # gaps：从关联匹配结果读（若有）
        gaps: List[Dict[str, Any]] = []
        if row.jd_result_id:
            jd = db.query(JdMatchResultModel).filter(JdMatchResultModel.id == row.jd_result_id).first()
            if jd and jd.gaps_json:
                gaps = jd.gaps_json

        return {
            "resume_md": row.content_md,
            "resume_eval": row.eval_report_json,
            "profile_snapshot": profile,
            "gaps_snapshot": gaps,
            "target_position": row.target_position,
            "resume_theme": row.theme,
            "resume_round": 0,
            "resume_mode": "refine",
            "resume_finalize_signal": False,
            "resume_user_feedback": None,
            "messages": [AIMessage(
                content=f"✅ 已加载草稿（{row.target_position} v{row.version}），进入精修模式"
            )],
        }
    finally:
        db.close()


def route_after_setup(state: Dict[str, Any]) -> str:
    """setup 后：出错/画像缺失 → END；否则 → refine"""
    if state.get("resume_status_code") in ("error", "profile_missing"):
        return "end"
    return "refine"


# ============================================================================
# 2. resume_refine_node：改写 + 评估 + interrupt（核心）
# ============================================================================

def resume_refine_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    精修一轮：有反馈则改写草稿 → 重新评估 → interrupt 展示草稿+评估，等用户反馈。

    第一次进入（无 feedback）：不改写，直接评估现有草稿并 interrupt（让用户先看当前版本）。
    后续（有 feedback，从上次 interrupt 恢复）：按反馈改写 → 评估 → 新 interrupt。

    interrupt 恢复值：{"action": "refine"|"finalize", "feedback": "..."}（由 API 构造 Command resume 传入）。
    """
    feedback = state.get("resume_user_feedback")
    md = state.get("resume_md") or ""
    profile = state.get("profile_snapshot") or {}
    gaps = state.get("gaps_snapshot") or []
    target_position = state.get("target_position")

    # 有反馈 → 改写
    if feedback:
        try:
            md = refine_resume(md, feedback, profile, gaps, target_position)
        except Exception as e:
            logger.warning(f"精修改写失败，沿用当前草稿：{e}")
            # 改写失败不阻断：沿用当前 md 继续评估 + interrupt

    # 重新评估（失败降级为 None）
    try:
        ev = evaluate_resume(md, target_position, gaps, profile)
    except Exception as e:
        logger.warning(f"精修评估失败（降级）：{e}")
        ev = None

    round_num = (state.get("resume_round") or 0) + 1

    # 画像追问（5.2.2）：从草稿提取「待补充」项，提示用户在反馈里补这些素材
    pending_hints = _extract_pending_hints(md)

    # ⭐ interrupt：挂起，把草稿+评估+待补充提示交给前端，等用户反馈
    user_resp = interrupt({
        "resume_md": md,
        "eval_report": ev,
        "round": round_num,
        "pending_hints": pending_hints,
        "message": ("查看当前草稿与评估，输入反馈继续精修；"
                    "或在「待补充」处补充具体细节后反馈；确认满意则定稿"),
    })

    # interrupt 恢复后：解析用户响应（action + feedback）
    user_resp = user_resp or {}
    action = user_resp.get("action", "refine")
    fb = user_resp.get("feedback", "")

    update: Dict[str, Any] = {
        "resume_md": md,
        "resume_eval": ev,
        "resume_round": round_num,
    }
    if action == "finalize":
        update["resume_finalize_signal"] = True
        update["resume_user_feedback"] = None
    else:
        update["resume_finalize_signal"] = False
        update["resume_user_feedback"] = fb
    return update


def route_after_refine(state: Dict[str, Any]) -> str:
    """refine 后：用户确认定稿 → finalize；否则回 refine（继续精修循环）"""
    return "finalize" if state.get("resume_finalize_signal") else "refine"


# ============================================================================
# 3. resume_finalize_node：校验 + 导出 + 落库 finalized
# ============================================================================

def resume_finalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    用户满意定稿：格式校验 → 导出 HTML → 落库为 finalized 新版本。
    格式校验有问题只提示，不阻断定稿（用户已确认满意）。
    """
    md = state.get("resume_md") or ""
    target_position = state.get("target_position") or ""
    user_id = state.get("user_id")
    profile = state.get("profile_snapshot") or {}
    name = profile.get("name") or "简历"
    title = f"{name}-{target_position}" if target_position else name

    # 格式校验（只提示）
    validation = validate_resume_md(md)

    # 导出 HTML（失败不阻断：html 留空，仍落库 Markdown）
    html = None
    theme = state.get("resume_theme")
    try:
        result = export_resume(md, target_position, title)
        html = result["html"]
        theme = result["theme"]
    except Exception as e:
        logger.warning(f"定稿导出 HTML 失败（仍落库 Markdown）：{e}")

    # 落库 finalized（新版本）
    resume_id_new, version = None, None
    db = SessionLocal()
    try:
        row = save_resume(
            db, user_id, target_position,
            content_md=md, html=html,
            eval_report=state.get("resume_eval") or None,
            eval_score=(state.get("resume_eval") or {}).get("overall_score"),
            theme=theme, status="finalized",
        )
        resume_id_new, version = row.id, row.version
    except Exception as e:
        logger.error(f"定稿落库失败：{e}")
        db.rollback()
    finally:
        db.close()

    msg = f"✅ 定稿完成（v{version}，finalized）"
    if not validation.passed:
        msg += f"；注意：格式校验仍有 {len(validation.errors)} 个问题（已按用户确认定稿）"
    return {
        "resume_id": resume_id_new,
        "resume_version": version,
        "resume_html": html,
        "resume_theme": theme,
        "resume_status": "finalized",
        "resume_status_code": "success",
        "messages": [AIMessage(content=msg)],
    }


# ============================================================================
# 辅助：提取「待补充」项（画像追问的弹药）
# ============================================================================

def _extract_pending_hints(md: str) -> List[str]:
    """
    从草稿提取「（待补充：xxx）」标记，作为画像追问提示。
    让用户在反馈里补充这些具体细节（简化的主动追问——MVP 不做多轮 probing）。
    """
    if not md:
        return []
    # 兼容中英文括号 + 中英文冒号
    return re.findall(r"[（(]待补充[：:]\s*([^）)]+)[）)]", md)


# ============================================================================
# 构建精修子图（独立图，带 checkpointer）
# ============================================================================

def build_resume_refine_graph(checkpointer=None):
    """
    构建简历精修子图（路径 B）并编译。

    Args:
        checkpointer: LangGraph checkpointer（默认复用 mock-interview 的会话 checkpointer，
                      支持 interrupt + 抗重启；thread_id = resume 会话 ID 区分不同精修会话）
    Returns:
        编译后的图（带 checkpointer，可 interrupt）
    """
    if checkpointer is None:
        checkpointer = get_interview_checkpointer()

    builder = StateGraph(FullAgentState)
    builder.add_node("refine_setup", resume_refine_setup_node)
    builder.add_node("refine", resume_refine_node)
    builder.add_node("finalize", resume_finalize_node)

    builder.set_entry_point("refine_setup")

    # setup → 出错 END；否则进 refine
    builder.add_conditional_edges(
        "refine_setup", route_after_setup,
        {"refine": "refine", "end": END},
    )
    # refine → 用户定稿去 finalize；否则回 refine（继续精修循环）
    builder.add_conditional_edges(
        "refine", route_after_refine,
        {"refine": "refine", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
