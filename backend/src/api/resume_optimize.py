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

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.deps import get_db
from fastapi.responses import StreamingResponse
from src.core.sse import sse, STAGE, TOKEN, REASONING, DONE, ERROR, STREAM_MEDIA_TYPE, STREAM_HEADERS
from src.services.resume_store_service import get_resume, list_resumes
from src.services.resume_exporter import assemble_html, wrap_preview, apply_patches_to_md
import asyncio
import re
from urllib.parse import quote

from src.services.resume_generator import refine_resume_reasoning_stream, split_reply_resume
from src.services.resume_pdf import render_html_to_pdf
from src.services.resume_evaluator import evaluate_resume
from src.services.profile_service import get_profile
from src.models.base import SessionLocal
from src.models.profile import JdMatchResultModel
from src.graph.graph import create_graph
from src.graph.state import create_initial_state
from src.graph.nodes.resume_refine import build_resume_refine_graph, resume_finalize_node
from src.graph.checkpointer import get_interview_checkpointer
from langgraph.types import Command

resume_optimize_router = APIRouter()

logger = logging.getLogger(__name__)


# ============================================================================
# 请求 / 响应模型
# ============================================================================

class GenerateRequest(BaseModel):
    """简历生成请求"""
    target_position: str = Field(..., description="目标岗位", min_length=1)
    jd_result_id: Optional[str] = Field(None, description="方式 B：关联的 JD 匹配结果 ID（读取其 Gap）")
    jd_text: Optional[str] = Field(None, description="方式 A：目标岗位 JD 原文（粘贴；可选，作生成上下文）")
    gaps: Optional[List[Dict[str, Any]]] = Field(
        None, description="可直接传入 Gap 清单（优先于 jd_result_id/jd_text；都无则通用生成）"
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

def _last_msg(update: Dict[str, Any]) -> Optional[str]:
    """从节点 update 的 messages 取最后一条 AIMessage 文案（用于错误提示）。"""
    for m in reversed(update.get("messages") or []):
        content = getattr(m, "content", None)
        if content:
            return content
    return None


@resume_optimize_router.post("/generate")
async def generate_resume_api(request: GenerateRequest):
    """
    基于画像 + Gap 生成简历（路径 A，SSE 流式：节点级 stage 进度 + done/error）。

    通过 graph.astream 持续下发节点进度，避免长请求超时；取代旧同步 invoke。
    画像缺失 → PROFILE_MISSING；LLM 失败 → LLM_FAILED。

    事件流（text/event-stream）：
      event: stage  —— 节点进度 {message, node}
      event: done   —— 完成 {resume_id, version, content_md, html, eval_report, refine_offered}
      event: error  —— 失败 {error_code, error_message}
    """
    user_id = request.user_id
    if not user_id:
        return ApiResponse(status="error", message="缺少 user_id", data={"error_code": "NO_USER"})

    async def event_stream():
        graph = create_graph()
        state = create_initial_state(user_id=user_id)
        state["intent"] = "resume_optimize"
        state["target_position"] = request.target_position
        if request.jd_result_id:
            state["jd_result_id"] = request.jd_result_id
        if request.jd_text:
            state["jd_text"] = request.jd_text
        if request.gaps:
            state["gaps_snapshot"] = request.gaps  # 直接传入优先

        config = {"configurable": {"thread_id": user_id}}

        stage_msg = {
            "resume_prepare": "准备画像与岗位…",
            "resume_generate": "生成简历草稿…",
            "resume_evaluate": "六维评估中…",
            "resume_validate": "格式校验…",
            "resume_export": "导出 HTML…",
            "resume_persist": "保存简历…",
        }
        err_code = {
            "profile_missing": "PROFILE_MISSING",
            "llm_failed": "LLM_FAILED",
            "error": "ERROR",
        }
        latest: Dict[str, Any] = {}

        try:
            async for chunk in graph.astream(state, config, stream_mode=["updates", "custom"]):
                # 多 stream_mode：chunk 为 (mode, data) 元组（0.2.x）；防御 dict
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                elif isinstance(chunk, dict) and len(chunk) == 1:
                    mode, data = next(iter(chunk.items()))
                else:
                    continue
                # custom 流：token（简历正文）/ reasoning（AI 思考），resume_generate_node 经 writer 推送
                if mode == "custom":
                    if isinstance(data, dict):
                        if data.get("type") == "token":
                            yield sse(TOKEN, {"delta": data.get("delta", "")})
                        elif data.get("type") == "reasoning":
                            yield sse(REASONING, {"delta": data.get("delta", "")})
                    continue
                if mode != "updates":
                    continue
                for node, update in (data or {}).items():
                    if not isinstance(update, dict):
                        continue
                    latest.update(update)
                    code = update.get("resume_status_code")

                    # 失败分支 → error 后关闭
                    if code in err_code:
                        if code == "profile_missing":
                            msg = "尚未建立个人画像，请先上传简历建立画像"
                        else:
                            msg = update.get("error") or _last_msg(update) or "简历生成失败，请稍后重试"
                        yield sse(ERROR, {"error_code": err_code[code], "error_message": msg})
                        return

                    # 节点进度（真实 stage，取代前端假进度）
                    if node in stage_msg:
                        yield sse(STAGE, {"message": stage_msg[node], "node": node})

                    # 终点：persist 成功 → done
                    if node == "resume_persist" and code == "success":
                        yield sse(DONE, {
                            "resume_id": latest.get("resume_id"),
                            "version": latest.get("resume_version"),
                            "content_md": latest.get("resume_md"),
                            "html": latest.get("resume_html"),
                            "eval_report": latest.get("resume_eval"),
                            "refine_offered": latest.get("resume_refine_offered"),
                        })
        except Exception as e:
            logger.exception("简历生成流式异常")
            yield sse(ERROR, {"error_code": "LLM_FAILED", "error_message": f"生成失败：{e}"})

    return StreamingResponse(
        event_stream(),
        media_type=STREAM_MEDIA_TYPE,
        headers=STREAM_HEADERS,
    )


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

@resume_optimize_router.get("/{resume_id}/pdf")
async def get_resume_pdf_api(
    resume_id: str,
    user_id: str = Query(..., description="用户 ID（校验属主 + 读精修会话态最新草稿）"),
    db: Session = Depends(get_db),
):
    """
    导出简历 PDF（服务端 Playwright 渲染 A4，直接下载，取代浏览器打印对话框）。

    - 读最新草稿：优先精修会话态（含未定稿的手改/对话改），否则落库
    - assemble HTML → Playwright 渲染 → 返回 application/pdf（附件下载，文件名「姓名-岗位」）
    - 渲染失败降级：返回 html + fallback_print，前端回退浏览器打印
    """
    row = get_resume(db, resume_id)
    if row is None or row.user_id != user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    # 读最新 MD：精修会话态（含未定稿改动）优先，否则落库
    graph = build_resume_refine_graph(get_interview_checkpointer())
    config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}
    snap = graph.get_state(config)
    cur_md = (snap.values.get("resume_md") if snap and snap.values else None) or row.content_md

    # 头像 URL：精修会话态优先，否则查落库画像（pdf 要正确显示头像）
    profile_snap = (snap.values.get("profile_snapshot") if snap and snap.values else None) or {}
    avatar_url = profile_snap.get("avatar_url") or ""
    if not avatar_url and row.user_id:
        avatar_url = (get_profile(db, row.user_id) or {}).get("avatar_url") or ""

    title = f"{row.target_position} · 简历" if row.target_position else "简历预览"
    full_html = wrap_preview(assemble_html(cur_md, avatar_url=avatar_url), title)

    try:
        # 放线程池跑同步 Playwright（Windows uvicorn 事件循环不支持子进程，见 render_html_to_pdf 注释）
        pdf_bytes, _pages = await asyncio.to_thread(render_html_to_pdf, full_html)
    except Exception as e:
        logger.warning(f"PDF 渲染失败（降级回浏览器打印）：{e}")
        return ApiResponse(
            status="warning",
            message="PDF 渲染失败，已降级为浏览器打印",
            data={"html": full_html, "content_md": cur_md, "fallback_print": True},
        )

    # 文件名：姓名-岗位（从 self-intro 解析 name）
    m = re.search(r'^name:\s*(.+)$', cur_md or '', re.MULTILINE)
    name = m.group(1).strip() if m else ""
    if name and row.target_position:
        filename = f"{name}-{row.target_position}.pdf"
    elif row.target_position:
        filename = f"{row.target_position}.pdf"
    else:
        filename = "简历.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


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
    ⚠️ 已被流式端点 /refine-stream 取代（对话式工作台主通道）；本同步端点保留作
    流式不可用时的降级通道（对应 spec「流式不可用时降级兼容」）。

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

    orchestrate 路径（与 refine-stream / patch-draft 一致）：从 checkpointer 读精修期间的
    最新草稿（含手动编辑回写），直接调 finalize 节点的业务逻辑（校验 + 导出 + 落库）。
    ⚠️ 不再 graph.invoke(Command(resume=...))：精修流式全程 update_state 直接写会话态，图的执行指针
    从未推进到 refine 节点的 interrupt，Command(resume=...) 找不到挂起的 interrupt 可恢复会报错
    （design 决策 8：refine-stream orchestrate 不走图 astream；finalize 同步改为 orchestrate）。
    """
    row = get_resume(db, resume_id)
    if not row or row.user_id != req.user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    try:
        graph = build_resume_refine_graph(get_interview_checkpointer())
        config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}
        snap = graph.get_state(config)
        values = (snap.values if snap and snap.values else {}) or {}

        # 会话态优先（精修期间 update_state 写入的最新草稿/评估，含 patch-draft 手动编辑回写），
        # 回落到落库草稿（未走精修会话也能定稿）
        md = values.get("resume_md") or row.content_md
        target_position = values.get("target_position") or row.target_position
        profile = values.get("profile_snapshot") or {}
        eval_report = values.get("resume_eval") or row.eval_report_json
        theme = values.get("resume_theme") or row.theme

        # 直接调 finalize 节点（纯业务逻辑：validate → export → save_resume，不依赖 graph 运行时）
        result = resume_finalize_node({
            "resume_md": md,
            "target_position": target_position,
            "user_id": req.user_id,
            "profile_snapshot": profile,
            "resume_theme": theme,
            "resume_eval": eval_report,
        })

        if result.get("resume_status_code") != "success":
            return ApiResponse(
                status="error",
                message="定稿失败",
                data={"error_code": "FINALIZE_FAILED"},
            )

        return ApiResponse(
            status="success",
            message="定稿完成",
            data={
                "resume_id": result.get("resume_id"),
                "version": result.get("resume_version"),
                "target_position": target_position,
                "content_md": md,
                "html": result.get("resume_html"),
                "status": "finalized",
            },
        )
    except Exception as e:
        logger.exception("定稿失败")
        return ApiResponse(status="error", message=f"定稿失败：{e}", data=None)


# ============================================================================
# API 7: 手动编辑回写（POST /api/resume/{resume_id}/patch-draft）
# ============================================================================

class PatchDraftRequest(BaseModel):
    """手动编辑回写请求：把左侧预览里用户改动的原子，按锚点局部回写到 Markdown 真相源。"""
    user_id: str = Field(..., description="用户 ID")
    patches: List[Dict[str, Any]] = Field(
        ...,
        description="锚点 patch 列表：[{line, field?, text?, cat?, chips?}]（line 对应 data-md-line）",
    )


@resume_optimize_router.post("/{resume_id}/patch-draft", response_model=ApiResponse)
async def patch_draft_api(resume_id: str, req: PatchDraftRequest, db: Session = Depends(get_db)):
    """
    手动编辑局部回写（精修工作台左侧「所见即所得」编辑的回写通道）。

    - 只替换被改的行，不重建整份 → 未编辑字段不丢失（真相源单一）
    - 仅更新 checkpointer 会话态草稿（thread_id = resume_refine:{id}），不落库（定稿才落库）
    - 返回回写后的新 MD + 重新装配的预览 HTML（带新锚点）+ 未命中告警

    会话未建立时，兜底以落库草稿为基线（并写入会话态），保证手改不丢。
    """
    row = get_resume(db, resume_id)
    if row is None or row.user_id != req.user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    graph = build_resume_refine_graph(get_interview_checkpointer())
    config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}

    # 读当前会话态草稿；无则兜底落库 content_md
    snap = graph.get_state(config)
    cur_md = (snap.values.get("resume_md") if snap and snap.values else None) or row.content_md

    # 局部回写（不重建整份）
    new_md, warnings = apply_patches_to_md(cur_md, req.patches)

    # 更新会话态（不落库）；resume_md 为普通字段，直接覆盖
    try:
        graph.update_state(config, {"resume_md": new_md})
    except Exception as e:
        logger.warning(f"patch-draft 更新会话态失败（仍返回新 MD 供前端刷新）：{e}")

    # 重新装配预览（带新锚点，供左侧继续编辑）
    title = f"{row.target_position} · 简历" if row.target_position else "简历预览"
    full_html = wrap_preview(assemble_html(new_md), title)

    return ApiResponse(
        status="success",
        message="已回写" + ("（部分未命中）" if warnings else ""),
        data={
            "resume_md": new_md,
            "html": full_html,
            "warnings": warnings,
        },
    )


# ============================================================================
# API 8: 精修流式（POST /api/resume/{resume_id}/refine-stream）—— 对话式工作台主通道
# ============================================================================

@resume_optimize_router.post("/{resume_id}/refine-stream")
async def refine_resume_stream_api(resume_id: str, req: RefineRequest, db: Session = Depends(get_db)):
    """
    精修流式（SSE，对话式工作台主通道）：reasoning + 结构化回复（说明 + 简历）。

    - 无 feedback：首次加载，下发当前草稿 + 评估（不改写）
    - 有 feedback：增量推送 AI 思考过程（reasoning，思考区打字机）→ content 攒齐后切分出
      自然语言说明（一次性）+ 改写后简历（done 一次性，不打字机）→ 评估 → 更新会话态
    - LLM 未按约定输出简历（无 <<<RESUME>>>）：resume 沿用上一版 + 提示（降级）

    设计取舍（见 design「精修流式的 orchestrate 路径」）：refine 子图保留 interrupt +
    checkpointer 作会话态存储，但流式路径在端点直接 orchestrate（get_state 读 / update_state
    写），不 invoke/astream graph——避开「astream × interrupt × Command resume × custom event」
    无先例组合的风险；同步 /refine 仍走 interrupt（降级通道）。
    """
    row = get_resume(db, resume_id)
    if row is None or row.user_id != req.user_id:
        return ApiResponse(status="error", message="简历不存在或无权访问", data={"error_code": "NOT_FOUND"})

    graph = build_resume_refine_graph(get_interview_checkpointer())
    config = {"configurable": {"thread_id": f"resume_refine:{resume_id}"}}

    async def event_stream():
        try:
            # 会话未建立则 setup（读落库草稿 + 画像 + gaps 写入 checkpointer 会话态）
            snap = graph.get_state(config)
            values = (snap.values if snap and snap.values else {}) or {}
            if not values.get("profile_snapshot"):
                sdb = SessionLocal()
                try:
                    profile_obj = get_profile(sdb, req.user_id) if req.user_id else None
                    if profile_obj is None:
                        yield sse(ERROR, {"error_code": "PROFILE_MISSING", "error_message": "尚未建立个人画像，无法精修"})
                        return
                    gaps: List[Dict[str, Any]] = []
                    if row.jd_result_id:
                        jd = sdb.query(JdMatchResultModel).filter(JdMatchResultModel.id == row.jd_result_id).first()
                        if jd and jd.gaps_json:
                            gaps = jd.gaps_json
                    setup_vals = {
                        "resume_md": row.content_md, "resume_eval": row.eval_report_json,
                        "profile_snapshot": profile_obj, "gaps_snapshot": gaps,
                        "target_position": row.target_position, "resume_round": 0,
                    }
                    graph.update_state(config, setup_vals)
                    values = setup_vals
                finally:
                    sdb.close()

            title = f"{row.target_position} · 简历" if row.target_position else "简历预览"
            cur_md = values.get("resume_md") or row.content_md
            profile = values.get("profile_snapshot") or {}
            avatar_url = profile.get("avatar_url") or ""  # 头像随简历渲染注入（不进 MD 真相源）
            gaps = values.get("gaps_snapshot") or []
            target_position = values.get("target_position") or row.target_position
            round_num = values.get("resume_round") or 0

            # 首次加载（无 feedback）：下发当前草稿，不改写
            if not req.feedback:
                yield sse(DONE, {
                    "reply": "", "resume_md": cur_md,
                    "html": wrap_preview(assemble_html(cur_md, avatar_url=avatar_url), title),
                    "eval_report": values.get("resume_eval"),
                    "round": round_num, "resumed": False,
                })
                return

            # 流式改写：reasoning 实时推（思考区打字机）；content 攒齐后切分
            content_full = ""
            seen_content = False
            async for kind, delta in refine_resume_reasoning_stream(
                cur_md, req.feedback, profile, gaps, target_position
            ):
                if kind == "reasoning":
                    yield sse(REASONING, {"delta": delta})
                else:
                    # 第一个 content 片段 = 思考结束、进入「修改中」（简历生成阶段）。
                    # content 此后攒齐不实时推，故这里推一个 stage 让前端切到「修改中」。
                    if not seen_content:
                        yield sse(STAGE, {"message": "修改中…", "node": "applying"})
                        seen_content = True
                    content_full += delta

            # 切分自然语言说明 + 改写后简历（降级：无简历则沿用上一版）
            reply, new_md = split_reply_resume(content_full)
            if reply:
                yield sse(TOKEN, {"delta": reply})  # 自然语言说明一次性下发
            final_md = new_md or cur_md
            if new_md:
                # 立即落草稿：done 秒级下发，让前端马上看到简历更新。
                # 不在此同步 evaluate——它会多一次 LLM 调用拖慢 done 数十秒，而工作台不展示评估分；
                # 评估留到定稿或后续异步（见 design 决策 8 的取舍同源）。
                graph.update_state(config, {
                    "resume_md": final_md, "resume_round": round_num + 1,
                })
            yield sse(DONE, {
                "reply": reply, "resume_md": final_md,
                "html": wrap_preview(assemble_html(final_md, avatar_url=avatar_url), title),
                "eval_report": None,
                "round": (round_num + 1) if new_md else round_num,
                "resumed": bool(new_md),
            })
        except Exception as e:
            logger.exception("精修流式异常")
            yield sse(ERROR, {"error_code": "LLM_FAILED", "error_message": f"精修失败：{e}"})

    return StreamingResponse(event_stream(), media_type=STREAM_MEDIA_TYPE, headers=STREAM_HEADERS)
