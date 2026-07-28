"""
模拟面试 API 路由（会话式 —— 区别于 JD 匹配的一次性请求-响应）
================================================================

端点：
  POST /api/interview/sessions            创建会话 → session_id + 第一题
  POST /api/interview/sessions/{id}/answer 提交回答 → 下一题 OR 结束信号（多态响应）
  GET  /api/interview/sessions/{id}        查状态 + transcript（续面/刷新）
  GET  /api/interview/sessions/{id}/debrief 获取复盘报告
  GET  /api/interview/sessions             历史会话列表

会话式 API 的本质（对应 design.md 决策 12）：
  - 创建会话：跑图到第一个 interrupt，返回第一题
  - 提交回答：Command(resume) 唤醒图，跑下一轮；多态响应（继续问 / 已结束）
  - 状态由 checkpointer 保住（跨请求、抗重启），thread_id = session_id

作者：求职 Copilot 项目
日期：2026-07-20
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from langgraph.types import Command

from src.core.deps import get_db
from src.models.interview import InterviewSessionModel
from src.models.base import SessionLocal
from src.graph.state import create_initial_state
from src.graph.nodes.mock_interview import build_interview_graph
from src.graph.checkpointer import get_interview_checkpointer
from src.services.profile_service import get_profile

interview_router = APIRouter()


# ============================================================================
# 请求 / 响应模型
# ============================================================================

class CreateSessionRequest(BaseModel):
    """创建面试会话"""
    user_id: str = Field(..., description="用户 ID")
    interview_type: str = Field("full", description="面试类型: behavioral/technical/case/motivation/full/stress")
    intensity: str = Field("normal", description="档位: short/normal/deep/full")
    interview_mode: str = Field("real", description="模式: real 实战 / coach 教练")
    jd_result_id: Optional[str] = Field(None, description="关联的 JD 匹配结果（可选，无 JD 通用面试）")
    persona: Optional[Dict[str, Any]] = Field(None, description="面试官人设 {tone, role, stress_mode}")


class AnswerRequest(BaseModel):
    """提交一轮回答"""
    answer: str = Field(..., description="用户回答", min_length=1)


class ApiResponse(BaseModel):
    """统一响应"""
    status: str = Field(..., description="success / error")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# ============================================================================
# 辅助函数
# ============================================================================

def _get_graph():
    """获取面试图（带 checkpointer，每次新建编译图无状态，状态在 checkpointer）。"""
    return build_interview_graph(get_interview_checkpointer())


def _get_pending_question(graph, config) -> Optional[Dict[str, Any]]:
    """取当前 interrupt 挂起的问题（前端据此显示「面试官问了什么」）。"""
    snap = graph.get_state(config)
    for task in snap.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def _has_experience_detail(profile: Dict[str, Any]) -> bool:
    """画像是否有经历细节（面试个性化追问的弹药）。"""
    work = [d for d in (profile.get("work_descriptions") or []) if d]
    proj = [d for d in (profile.get("project_descriptions") or []) if d]
    return bool(work or proj)


def _session_summary(row: InterviewSessionModel) -> Dict[str, Any]:
    """会话列表项摘要。"""
    return {
        "id": row.id,
        "status": row.status,
        "interview_type": row.interview_type,
        "intensity": row.intensity,
        "interview_mode": row.interview_mode,
        "jd_result_id": row.jd_result_id,
        "avg_score": row.avg_score,
        "total_rounds": row.total_rounds,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


# ============================================================================
# API 1: 创建会话（POST /api/interview/sessions）
# ============================================================================

@interview_router.post("/sessions", response_model=ApiResponse)
async def create_session(req: CreateSessionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    创建模拟面试会话。

    异步开局（add-async-interview-setup）：画像检查 → 建 session(setup_pending) → 后台跑图出题 → 立即返回 session_id。
    第一题由前端轮询 getSession 获取（status: setup_pending → interviewing）。
    - 画像缺失：PROFILE_MISSING（同步返回，不进后台）
    - 画像经历细节不足：警告但不阻断（仍可通用面试）
    """
    # 画像就绪性检查
    profile = get_profile(db, req.user_id)
    if not profile:
        return ApiResponse(
            status="error",
            message="尚未建立个人画像，请先上传简历或手动填写建立画像",
            data={"error_code": "PROFILE_MISSING"},
        )
    detail_warning = None if _has_experience_detail(profile) else "画像经历细节不足，面试个性化追问可能受限，建议先补充工作/项目经历"

    # 建会话记录
    session = InterviewSessionModel(
        user_id=req.user_id,
        status="setup_pending",
        interview_type=req.interview_type,
        intensity=req.intensity,
        interview_mode=req.interview_mode,
        jd_result_id=req.jd_result_id,
        persona_json=req.persona,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 异步开局（add-async-interview-setup）：出题移到后台，立即返回 setup_pending
    init = create_initial_state(user_id=req.user_id)
    init["session_id"] = session.id
    init["interview_type"] = req.interview_type
    init["intensity"] = req.intensity
    init["interview_mode"] = req.interview_mode
    init["persona"] = req.persona or {}
    if req.jd_result_id:
        init["jd_result_id"] = req.jd_result_id

    background_tasks.add_task(_run_setup_background, session.id, init)

    return ApiResponse(
        status="success",
        message="面试正在准备",
        data={
            "session_id": session.id,
            "interview_status": "setup_pending",
            "detail_warning": detail_warning,
        },
    )


def _run_setup_background(session_id: str, init: Dict[str, Any]) -> None:
    """
    后台跑图到第一个 interrupt（出题），完成后置会话状态为 interviewing；失败置 error。

    - 在响应发出后、请求 db 关闭后执行，故内部新建独立 db session。
    - 同步 graph.invoke 由 Starlette BackgroundTasks 置于线程池跑，不阻塞事件循环。
    - 失败原因记 logger（前端据 status=error 显示 generic 重试提示）。
    """
    db = SessionLocal()
    try:
        graph = _get_graph()
        config = {"configurable": {"thread_id": session_id}}
        graph.invoke(init, config)  # session_setup 出题 → 抵达第一个 interrupt
        sess = db.query(InterviewSessionModel).filter(InterviewSessionModel.id == session_id).first()
        if sess and sess.status == "setup_pending":
            sess.status = "interviewing"
            db.commit()
        logger.info(f"后台出题完成 session={session_id}")
    except Exception as e:
        logger.exception(f"后台出题失败 session={session_id}: {type(e).__name__}: {e}")
        sess = db.query(InterviewSessionModel).filter(InterviewSessionModel.id == session_id).first()
        if sess:
            sess.status = "error"
            db.commit()
    finally:
        db.close()


# ============================================================================
# API 2: 提交回答（POST /api/interview/sessions/{id}/answer，多态响应）
# ============================================================================

@interview_router.post("/sessions/{session_id}/answer", response_model=ApiResponse)
async def submit_answer(session_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
    """
    提交一轮回答，唤醒图继续跑。响应多态：
      - 面试继续：{interview_status: "interviewing", next_question, coach_hint?}
      - 面试结束：{interview_status: "finished", debrief_id, total_rounds, avg_score}
    """
    session = db.query(InterviewSessionModel).filter(InterviewSessionModel.id == session_id).first()
    if not session:
        return ApiResponse(status="error", message="会话不存在", data={"error_code": "SESSION_NOT_FOUND"})
    if session.status == "finished":
        return ApiResponse(status="error", message="该面试已结束", data={"error_code": "ALREADY_FINISHED"})

    try:
        graph = _get_graph()
        config = {"configurable": {"thread_id": session_id}}
        graph.invoke(Command(resume=req.answer), config)
        state = graph.get_state(config).values

        # 情况 A：面试结束
        if state.get("interview_status") == "finished":
            debrief = state.get("debrief_report") or {}
            overview = debrief.get("overview") or {}
            session.status = "finished"
            session.avg_score = overview.get("avg_score")
            session.total_rounds = overview.get("total_rounds")
            session.debrief_report_json = debrief
            session.finished_at = datetime.utcnow()
            db.commit()
            return ApiResponse(
                status="success",
                message="面试结束，复盘已生成",
                data={
                    "interview_status": "finished",
                    "debrief_id": session.id,
                    "total_rounds": session.total_rounds,
                    "avg_score": session.avg_score,
                },
            )

        # 情况 B：面试继续
        next_q = _get_pending_question(graph, config)
        coach_hint = None
        if session.interview_mode == "coach":
            transcript = state.get("transcript") or []
            if transcript:
                coach_hint = (transcript[-1].get("evaluation") or {}).get("weakness")
        return ApiResponse(
            status="success",
            message="继续",
            data={
                "interview_status": "interviewing",
                "next_question": next_q,
                "coach_hint": coach_hint,
            },
        )
    except Exception as e:
        return ApiResponse(
            status="error",
            message=f"提交回答失败：{e}",
            data={"error_code": "ANSWER_FAILED"},
        )


# ============================================================================
# API 3: 查会话状态 + transcript（GET /api/interview/sessions/{id}）
# ============================================================================

@interview_router.get("/sessions/{session_id}", response_model=ApiResponse)
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """查会话状态与对话流水（用于续面、刷新、回看进度）。"""
    session = db.query(InterviewSessionModel).filter(InterviewSessionModel.id == session_id).first()
    if not session:
        return ApiResponse(status="error", message="会话不存在", data={"error_code": "SESSION_NOT_FOUND"})

    # 从 checkpointer 取 transcript（进行中状态在那）
    transcript: List[Dict[str, Any]] = []
    pending_question = None
    try:
        graph = _get_graph()
        config = {"configurable": {"thread_id": session_id}}
        snap = graph.get_state(config)
        transcript = (snap.values or {}).get("transcript") or []
        pending_question = _get_pending_question(graph, config)
    except Exception:
        pass  # checkpointer 读取失败不阻断，至少返回 session 元信息

    return ApiResponse(
        status="success",
        message="OK",
        data={
            **_session_summary(session),
            "transcript": transcript,
            "pending_question": pending_question,  # 进行中且有挂起问题时非空（续面用）
        },
    )


# ============================================================================
# API 4: 获取复盘（GET /api/interview/sessions/{id}/debrief）
# ============================================================================

@interview_router.get("/sessions/{session_id}/debrief", response_model=ApiResponse)
async def get_debrief(session_id: str, db: Session = Depends(get_db)):
    """获取某场面试的复盘报告（仅 finished 会话有完整复盘）。"""
    session = db.query(InterviewSessionModel).filter(InterviewSessionModel.id == session_id).first()
    if not session:
        return ApiResponse(status="error", message="会话不存在", data={"error_code": "SESSION_NOT_FOUND"})
    if session.status != "finished":
        return ApiResponse(
            status="error",
            message="面试尚未结束，暂无复盘",
            data={"error_code": "NOT_FINISHED", "current_status": session.status},
        )

    return ApiResponse(
        status="success",
        message="OK",
        data={
            "session_id": session.id,
            "debrief": session.debrief_report_json,
            "avg_score": session.avg_score,
            "total_rounds": session.total_rounds,
        },
    )


# ============================================================================
# API 5: 历史会话（GET /api/interview/sessions）
# ============================================================================

@interview_router.get("/sessions", response_model=ApiResponse)
async def list_sessions(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """查询当前用户的历史面试会话（时间倒序，最多 50 条）。"""
    rows = (
        db.query(InterviewSessionModel)
        .filter(InterviewSessionModel.user_id == user_id)
        .order_by(InterviewSessionModel.created_at.desc())
        .limit(50)
        .all()
    )
    return ApiResponse(
        status="success",
        message=f"共 {len(rows)} 条面试记录",
        data={"items": [_session_summary(r) for r in rows]},
    )
