"""
简历优化 API 路由（路径 A：自动生成）

功能：
1. POST /api/resume/generate   基于画像 + Gap 生成简历（同步返回 Markdown + 评估）
2. GET  /api/resume/list        查询当前用户的简历（按岗位分组）
3. GET  /api/resume/{id}        查看某份简历详情
4. GET  /api/resume/{id}/pdf    下载 PDF（Phase 3 占位，Phase 4 接入导出后补全）

router 命名 resume_optimize_router，避免与简历解析的 resume_router 冲突（两者共用 /api/resume 前缀）。

作者：求职 Copilot 项目
日期：2026-07-22
"""

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.deps import get_db
from src.services.resume_store_service import get_resume, list_resumes
from src.graph.graph import create_graph
from src.graph.state import create_initial_state
from src.graph.nodes.resume_refine import build_resume_refine_graph
from src.graph.checkpointer import get_interview_checkpointer
from langgraph.types import Command

resume_optimize_router = APIRouter()


# ============================================================================
# 请求 / 响应模型
# ============================================================================

class GenerateRequest(BaseModel):
    """简历生成请求"""
    target_position: str = Field(..., description="目标岗位", min_length=1)
    jd_result_id: Optional[str] = Field(None, description="关联的 JD 匹配结果 ID（用于读取 Gap；可选）")
    gaps: Optional[List[Dict[str, Any]]] = Field(
        None, description="可直接传入 Gap 清单（优先于 jd_result_id；都无则通用生成）"
    )
    user_id: Optional[str] = Field(None, description="用户 ID")


class ApiResponse(BaseModel):
    """统一响应"""
    status: str = Field(..., description="success / warning / error")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# ============================================================================
# API 1: 生成简历（路径 A，POST /api/resume/generate）
# ============================================================================

@resume_optimize_router.post("/generate", response_model=ApiResponse)
async def generate_resume_api(request: GenerateRequest):
    """
    基于画像 + Gap 生成简历（路径 A，同步返回 Markdown + 评估）。

    - 画像缺失 → PROFILE_MISSING（前端引导先建画像）
    - LLM 失败 → LLM_FAILED
    - 成功 → 返回 resume_id / version / content_md / html / eval_report / refine_offered
    """
    user_id = request.user_id
    if not user_id:
        return ApiResponse(status="error", message="缺少 user_id", data={"error_code": "NO_USER"})

    try:
        graph = create_graph()
        state = create_initial_state(user_id=user_id)
        state["intent"] = "resume_optimize"
        state["target_position"] = request.target_position
        if request.jd_result_id:
            state["jd_result_id"] = request.jd_result_id
        if request.gaps:
            state["gaps_snapshot"] = request.gaps  # 直接传入优先

        config = {"configurable": {"thread_id": user_id}}
        final = graph.invoke(state, config)

        code = final.get("resume_status_code")
        if code == "profile_missing":
            return ApiResponse(
                status="error",
                message="尚未建立个人画像，请先上传简历建立画像",
                data={"error_code": "PROFILE_MISSING"},
            )
        if code == "llm_failed":
            return ApiResponse(
                status="error",
                message=final.get("error") or "简历生成失败，请稍后重试",
                data={"error_code": "LLM_FAILED"},
            )
        if code == "error":
            return ApiResponse(
                status="error",
                message=final.get("error") or "简历生成失败",
                data={"error_code": "ERROR"},
            )

        return ApiResponse(
            status="success",
            message="简历生成完成",
            data={
                "resume_id": final.get("resume_id"),
                "version": final.get("resume_version"),
                "content_md": final.get("resume_md"),
                "html": final.get("resume_html"),
                "eval_report": final.get("resume_eval"),
                "refine_offered": final.get("resume_refine_offered"),
            },
        )
    except Exception as e:
        return ApiResponse(status="error", message=f"生成失败：{e}", data=None)


# ============================================================================
# API 2: 简历列表（GET /api/resume/list，按岗位分组）
# ============================================================================

@resume_optimize_router.get("/list", response_model=ApiResponse)
async def list_resumes_api(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    db: Session = Depends(get_db),
):
    """查询用户的简历（按岗位分组、版本倒序）。"""
    if not user_id:
        return ApiResponse(status="error", message="缺少 user_id", data=None)

    rows = list_resumes(db, user_id)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r.target_position, []).append({
            "id": r.id,
            "version": r.version,
            "status": r.status,
            "theme": r.theme,
            "eval_score": r.eval_score,
            "jd_result_id": r.jd_result_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return ApiResponse(
        status="success",
        message=f"共 {len(rows)} 份简历",
        data={"items": grouped},
    )


# ============================================================================
# API 3: 简历详情（GET /api/resume/{resume_id}）
# ============================================================================

@resume_optimize_router.get("/{resume_id}", response_model=ApiResponse)
async def get_resume_api(resume_id: str, db: Session = Depends(get_db)):
    """查看某份简历详情（含 Markdown、HTML、评估报告）。"""
    row = get_resume(db, resume_id)
    if not row:
        return ApiResponse(status="error", message="简历不存在", data=None)
    return ApiResponse(
        status="success",
        message="OK",
        data={
            "id": row.id,
            "user_id": row.user_id,
            "target_position": row.target_position,
            "version": row.version,
            "status": row.status,
            "theme": row.theme,
            "content_md": row.content_md,
            "html": row.html,
            "eval_report": row.eval_report_json,
            "eval_score": row.eval_score,
            "jd_result_id": row.jd_result_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        },
    )


# ============================================================================
# API 4: PDF 下载（GET /api/resume/{resume_id}/pdf，Phase 3 占位）
# ============================================================================

@resume_optimize_router.get("/{resume_id}/pdf", response_model=ApiResponse)
async def get_resume_pdf_api(resume_id: str, db: Session = Depends(get_db)):
    """
    获取简历 PDF。

    【Phase 3 占位】PDF 导出在 Phase 4 接入主题系统后支持；
    当前 HTML 字段为空，返回 warning + content_md，前端可按 Markdown 预览。
    """
    row = get_resume(db, resume_id)
    if not row:
        return ApiResponse(status="error", message="简历不存在", data=None)
    if not row.html:
        return ApiResponse(
            status="warning",
            message="PDF 导出尚未就绪（Phase 4 接入主题后支持），当前可使用 Markdown 内容预览",
            data={"content_md": row.content_md, "html": None},
        )
    return ApiResponse(status="success", message="OK", data={"html": row.html, "content_md": row.content_md})


# ============================================================================
# API 5: 路径 B 精修（POST /api/resume/{resume_id}/refine）
# ============================================================================

class RefineRequest(BaseModel):
    """精修请求"""
    user_id: str = Field(..., description="用户 ID")
    feedback: Optional[str] = Field(
        None, description="精修反馈；第一次精修不传（加载草稿并展示评估），后续传反馈按反馈改写"
    )


def _get_pending_interrupt(graph, config) -> Optional[Dict[str, Any]]:
    """取当前 interrupt 挂起的内容（草稿+评估+待补充提示，前端据此展示并接收反馈）。"""
    snap = graph.get_state(config)
    for task in snap.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


@resume_optimize_router.post("/{resume_id}/refine", response_model=ApiResponse)
async def refine_resume_api(resume_id: str, req: RefineRequest, db: Session = Depends(get_db)):
    """
    路径 B 精修（人机协同，interrupt + checkpointer）：
    - 第一次（无 feedback）：加载草稿 → 展示当前评估 → interrupt 等反馈
    - 后续（带 feedback）：按反馈改写草稿 → 重新评估 → interrupt 等下一步反馈

    每次返回当前草稿 + 评估 + 「待补充」提示（供前端展示反馈入口）。
    会话状态在 checkpointer（thread_id = resume_refine:{resume_id}），跨请求保持。
    """
    row = get_resume(db, resume_id)
    if not row or row.user_id != req.user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    try:
        graph = build_resume_refine_graph(get_interview_checkpointer())
        config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}

        if req.feedback:
            # 继续：Command resume 唤醒，按反馈改写
            graph.invoke(Command(resume={"action": "refine", "feedback": req.feedback}), config)
        else:
            # 第一次：invoke initial，加载草稿 → 跑到第一个 interrupt
            init = create_initial_state(user_id=req.user_id)
            init["resume_id"] = resume_id
            graph.invoke(init, config)

        state = graph.get_state(config).values
        code = state.get("resume_status_code")
        if code in ("error", "profile_missing"):
            return ApiResponse(
                status="error",
                message=state.get("error") or "精修失败",
                data={"error_code": "PROFILE_MISSING" if code == "profile_missing" else "ERROR"},
            )

        pending = _get_pending_interrupt(graph, config) or {}
        return ApiResponse(
            status="success",
            message=pending.get("message", "精修进行中"),
            data={
                "status": "awaiting_feedback",
                "resume_md": pending.get("resume_md"),
                "eval_report": pending.get("eval_report"),
                "round": pending.get("round"),
                "pending_hints": pending.get("pending_hints", []),
            },
        )
    except Exception as e:
        return ApiResponse(status="error", message=f"精修失败：{e}", data=None)


# ============================================================================
# API 6: 路径 B 定稿（POST /api/resume/{resume_id}/finalize）
# ============================================================================

class FinalizeRequest(BaseModel):
    """定稿请求"""
    user_id: str = Field(..., description="用户 ID")


@resume_optimize_router.post("/{resume_id}/finalize", response_model=ApiResponse)
async def finalize_resume_api(resume_id: str, req: FinalizeRequest, db: Session = Depends(get_db)):
    """
    路径 B 定稿：用户满意后，格式校验 → 导出 HTML → 落库为 finalized 新版本。

    前置：必须已通过 /refine 建立精修会话（checkpointer 有该 thread_id 状态）。
    会话态（草稿/评估/轮次）在 checkpointer；定稿时才落库（会话态与持久态分离）。
    """
    row = get_resume(db, resume_id)
    if not row or row.user_id != req.user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    try:
        graph = build_resume_refine_graph(get_interview_checkpointer())
        config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}
        graph.invoke(Command(resume={"action": "finalize"}), config)
        state = graph.get_state(config).values

        if state.get("resume_status_code") != "success":
            return ApiResponse(
                status="error",
                message=state.get("error") or "定稿失败",
                data={"error_code": "FINALIZE_FAILED"},
            )

        return ApiResponse(
            status="success",
            message="定稿完成",
            data={
                "resume_id": state.get("resume_id"),
                "version": state.get("resume_version"),
                "target_position": state.get("target_position"),
                "content_md": state.get("resume_md"),
                "html": state.get("resume_html"),
                "status": "finalized",
            },
        )
    except Exception as e:
        return ApiResponse(status="error", message=f"定稿失败：{e}", data=None)
