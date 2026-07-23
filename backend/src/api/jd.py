"""
JD 匹配 API 路由

功能：
1. POST /api/jd/match         提交 JD 文本，执行匹配（同步返回报告）
2. GET  /api/jd/history        查询当前用户的历史匹配（时间倒序）
3. GET  /api/jd/results/{id}   查看某次匹配详情

作者：求职 Copilot 项目
日期：2026-07-14
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.deps import get_db
from src.models.profile import JdMatchResultModel
from src.graph.graph import create_graph
from src.graph.state import create_initial_state
from src.services.gap_analyzer import enrich_gaps
from src.services.profile_service import get_profile

logger = logging.getLogger(__name__)

jd_router = APIRouter()


# ============================================================================
# SSE 工具
# ============================================================================

def _sse(event: str, data: Dict[str, Any]) -> str:
    """组装一条 SSE 事件（event 行 + data 行，以空行结束）。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _last_msg(update: Dict[str, Any]) -> Optional[str]:
    """从节点 update 的 messages 里取最后一条 AIMessage 文案（用于错误提示）。"""
    for m in reversed(update.get("messages") or []):
        content = getattr(m, "content", None)
        if content:
            return content
    return None


# ============================================================================
# 请求 / 响应模型
# ============================================================================

class MatchRequest(BaseModel):
    """JD 匹配请求"""
    jd_text: str = Field(..., description="职位描述（JD）文本", min_length=1)
    user_id: Optional[str] = Field(None, description="用户 ID")


class ApiResponse(BaseModel):
    """统一响应"""
    status: str = Field(..., description="success / error")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# ============================================================================
# API 1: 提交 JD 执行匹配（POST /api/jd/match）
# ============================================================================

@jd_router.post("/match")
async def match_jd(request: MatchRequest):
    """
    提交 JD 文本，流式执行匹配（SSE 阶段推送）。

    评分链：JD 校验 → 结构化解析 → 加载画像 → 匹配计算 → 持久化（分数秒出）。
    通过 SSE 持续下发事件，避免长请求超时；Gap 的 LLM 增补（隐性判断 + 建议）
    走独立的 /api/jd/{id}/enrich 端点 lazy 加载。

    事件流（text/event-stream）：
      event: stage  —— 阶段进度（{message, node}）
      event: score  —— 分数（overall_score / dimension_scores / level / redline_hit / result_id）
      event: done   —— 主链结束（{result_id, job_profile, gaps（规则骨架）}）
      event: error  —— 失败（{error_code, error_message}），随后关闭流
    """
    user_id = request.user_id
    if not user_id:
        # 流开始前缺参：直接回 JSON（无需 SSE）
        return ApiResponse(status="error", message="缺少 user_id", data={"error_code": "NO_USER"})

    async def event_stream():
        graph = create_graph()
        state = create_initial_state(user_id=user_id)
        state["intent"] = "jd_match"
        state["jd_text"] = request.jd_text
        config = {"configurable": {"thread_id": user_id}}

        # 失败状态 → 错误码 / 默认文案
        err_code = {"jd_invalid": "JD_INVALID", "profile_missing": "PROFILE_MISSING", "error": "LLM_FAILED"}
        default_msg = {
            "jd_invalid": "JD 内容无效，请提供完整的职位描述（含职责/要求等）",
            "profile_missing": "尚未建立个人画像，请先上传简历建立画像",
            "error": "匹配失败，请稍后重试",
        }
        # 阶段节点 → 进度文案
        stage_msg = {
            "jd_parsing": "正在解析 JD 要求…",
            "profile_load": "正在加载你的画像…",
            "match_calc": "正在比对匹配度…",
        }
        latest: Dict[str, Any] = {}  # 累积各节点 update（astream updates 每次只给 delta）

        try:
            async for chunk in graph.astream(state, config, stream_mode="updates"):
                for node, update in (chunk or {}).items():
                    if not isinstance(update, dict):
                        continue
                    latest.update(update)
                    mstatus = update.get("match_status")

                    # 失败分支 → error 事件后关闭
                    if mstatus in err_code:
                        msg = update.get("error") or _last_msg(update) or default_msg[mstatus]
                        yield _sse("error", {"error_code": err_code[mstatus], "error_message": msg})
                        return

                    # 阶段进度
                    if node in stage_msg:
                        yield _sse("stage", {"message": stage_msg[node], "node": node})

                    # 评分链终点：先 score（分数）后 done（骨架）
                    if node == "report_format" and mstatus == "success":
                        mr = latest.get("match_result", {}) or {}
                        yield _sse("score", {
                            "overall_score": mr.get("overall_score"),
                            "level": mr.get("level"),
                            "dimension_scores": mr.get("dimension_scores", {}),
                            "redline_hit": mr.get("redline_hit"),
                            "result_id": update.get("result_id"),
                        })
                        yield _sse("done", {
                            "result_id": update.get("result_id"),
                            "job_profile": latest.get("job_profile", {}),
                            "gaps": update.get("gaps", []),
                        })
        except Exception as e:
            logger.exception("JD 匹配流式处理异常")
            yield _sse("error", {"error_code": "LLM_FAILED", "error_message": f"匹配失败：{e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================================================
# API 2: Gap 增补（POST /api/jd/{result_id}/enrich）—— lazy 加载
# ============================================================================

class EnrichRequest(BaseModel):
    """Gap 增补请求（仅需 user_id 校验归属；result_id 在路径里）。"""
    user_id: Optional[str] = Field(None, description="用户 ID")


@jd_router.post("/{result_id}/enrich", response_model=ApiResponse)
async def enrich_gaps_api(result_id: str, request: EnrichRequest, db: Session = Depends(get_db)):
    """
    增补 Gap：跑隐性偏好判断 + Gap 建议生成（两段 LLM），回填同一匹配记录。

    评分链（/match）已秒出分数与规则 Gap 骨架；本端点补全隐性判断结果与 LLM 建议。
    失败降级为模板建议 / 隐性 partial，不影响已持久化的分数。
    """
    row = db.query(JdMatchResultModel).filter(JdMatchResultModel.id == result_id).first()
    if not row:
        return ApiResponse(status="error", message="匹配记录不存在", data=None)

    job_profile = row.job_profile_json or {}
    gaps = row.gaps_json or []
    user_profile = get_profile(db, row.user_id)
    if not user_profile:
        return ApiResponse(
            status="error", message="画像缺失，无法增补", data={"error_code": "PROFILE_MISSING"}
        )

    # 增补是同步 LLM 调用 → 丢线程池，避免阻塞事件循环（评分链已解阻塞，这里同样不阻塞）
    try:
        enriched = await asyncio.to_thread(enrich_gaps, gaps, job_profile, user_profile)
    except Exception as e:
        logger.exception("Gap 增补失败")
        return ApiResponse(status="error", message=f"增补失败：{e}", data=None)

    row.gaps_json = enriched
    db.commit()
    return ApiResponse(status="success", message="增补完成", data={"gaps": enriched})


# ============================================================================
# API 3: 历史匹配（GET /api/jd/history）
# ============================================================================

@jd_router.get("/history", response_model=ApiResponse)
async def match_history(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    db: Session = Depends(get_db),
):
    """查询当前用户的历史匹配（时间倒序，最多 50 条）。"""
    if not user_id:
        return ApiResponse(status="error", message="缺少 user_id", data=None)

    rows = (
        db.query(JdMatchResultModel)
        .filter(JdMatchResultModel.user_id == user_id)
        .order_by(JdMatchResultModel.created_at.desc())
        .limit(50)
        .all()
    )
    items = [
        {
            "id": r.id,
            "overall_score": r.overall_score,
            "dimension_scores": {
                "skill": r.skill_score,
                "experience": r.experience_score,
                "education": r.education_score,
                "soft_skill": r.soft_skill_score,
            },
            "position_title": (r.job_profile_json or {}).get("position_title"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return ApiResponse(
        status="success",
        message=f"共 {len(items)} 条历史匹配",
        data={"items": items},
    )


# ============================================================================
# API 3: 匹配详情（GET /api/jd/results/{result_id}）
# ============================================================================

@jd_router.get("/results/{result_id}", response_model=ApiResponse)
async def match_detail(result_id: str, db: Session = Depends(get_db)):
    """查看某次匹配的完整详情（含原始 JD、要求画像、Gap 清单，可复算）。"""
    row = db.query(JdMatchResultModel).filter(JdMatchResultModel.id == result_id).first()
    if not row:
        return ApiResponse(status="error", message="匹配记录不存在", data=None)

    return ApiResponse(
        status="success",
        message="OK",
        data={
            "id": row.id,
            "user_id": row.user_id,
            "jd_text": row.jd_text,
            "overall_score": row.overall_score,
            "dimension_scores": {
                "skill": row.skill_score,
                "experience": row.experience_score,
                "education": row.education_score,
                "soft_skill": row.soft_skill_score,
            },
            "job_profile": row.job_profile_json,
            "gaps": row.gaps_json,
            "confidence": row.confidence_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    )
