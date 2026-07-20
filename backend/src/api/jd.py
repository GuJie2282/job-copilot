"""
JD 匹配 API 路由

功能：
1. POST /api/jd/match         提交 JD 文本，执行匹配（同步返回报告）
2. GET  /api/jd/history        查询当前用户的历史匹配（时间倒序）
3. GET  /api/jd/results/{id}   查看某次匹配详情

作者：求职 Copilot 项目
日期：2026-07-14
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.deps import get_db
from src.models.profile import JdMatchResultModel
from src.graph.graph import create_graph
from src.graph.state import create_initial_state

jd_router = APIRouter()


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

@jd_router.post("/match", response_model=ApiResponse)
async def match_jd(request: MatchRequest):
    """
    提交 JD 文本，执行匹配（同步，返回完整匹配报告）。

    流程：JD 校验 → 结构化解析 → 加载画像 → 匹配计算 → 差距分析 → 持久化 → 报告。
    - 画像缺失：返回 PROFILE_MISSING，前端引导先建立画像
    - JD 无效：返回 JD_INVALID
    - LLM 失败：返回 LLM_FAILED
    """
    user_id = request.user_id
    if not user_id:
        return ApiResponse(status="error", message="缺少 user_id", data={"error_code": "NO_USER"})

    try:
        # 构建并运行 JD 匹配图谱
        graph = create_graph()
        state = create_initial_state(user_id=user_id)
        state["intent"] = "jd_match"
        state["jd_text"] = request.jd_text
        config = {"configurable": {"thread_id": user_id}}
        final_state = graph.invoke(state, config)

        status = final_state.get("match_status")
        if status == "profile_missing":
            return ApiResponse(
                status="error",
                message="尚未建立个人画像，请先上传简历建立画像",
                data={"error_code": "PROFILE_MISSING"},
            )
        if status == "jd_invalid":
            return ApiResponse(
                status="error",
                message="JD 内容无效，请提供完整的职位描述（含职责/要求等）",
                data={"error_code": "JD_INVALID"},
            )
        if status == "error":
            return ApiResponse(
                status="error",
                message=final_state.get("error") or "匹配失败，请稍后重试",
                data={"error_code": "LLM_FAILED"},
            )

        mr = final_state.get("match_result", {})
        return ApiResponse(
            status="success",
            message="匹配完成",
            data={
                "result_id": final_state.get("result_id"),
                "overall_score": mr.get("overall_score"),
                "level": mr.get("level"),
                "dimension_scores": mr.get("dimension_scores"),
                "redline_hit": mr.get("redline_hit"),
                "job_profile": final_state.get("job_profile"),
                "gaps": final_state.get("gaps"),
            },
        )
    except Exception as e:
        return ApiResponse(status="error", message=f"匹配失败：{e}", data=None)


# ============================================================================
# API 2: 历史匹配（GET /api/jd/history）
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
