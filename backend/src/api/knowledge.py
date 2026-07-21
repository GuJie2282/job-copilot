"""
面经库 API 路由（个人库 + 公司库）
==================================

端点：
  个人库（严格 user_id 隔离）：
    GET    /api/knowledge/personal            列表/搜索（有 q 走语义，无 q 走分页；支持筛选）
    GET    /api/knowledge/personal/weakness   历史低分题（复练入口）
    DELETE /api/knowledge/personal/{id}       删单条（user_id 校验防越权）
    DELETE /api/knowledge/personal            清空全部（数据权利）
  公司库（全局共享）：
    GET    /api/knowledge/company             搜索（按公司/岗位过滤）
    GET    /api/knowledge/company/facets      公司/岗位去重列表（侧边导航）
    POST   /api/knowledge/company/ugc         UGC 贡献（脱敏，不暴露贡献者）

隐私治理：公司库响应剔除 contributor_id / embedding_json（spec 隐私与隔离）。
来源透明：每条透传 source（curated/ugc/llm_generated/personal），前端据实标注。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.deps import get_db
from src.services import knowledge_service as ks

knowledge_router = APIRouter()


class ApiResponse(BaseModel):
    """统一响应"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class UgcContributeRequest(BaseModel):
    """UGC 贡献请求"""
    user_id: str
    company: Optional[str] = None
    position: Optional[str] = None
    category: Optional[str] = None
    question: str = Field(..., min_length=1, description="面经问题")
    context: Optional[str] = Field(None, description="考察点/背景（可选）")


# ============================================================================
# 序列化（剔除内部/隐私字段）
# ============================================================================

def _personal_public(c: Dict[str, Any]) -> Dict[str, Any]:
    """个人库条目 → 前端友好（剔除 vector / _vec_sim / _bm25 等内部字段）。"""
    return {
        "id": c.get("id"),
        "position": c.get("position"),
        "company": c.get("company"),
        "category": c.get("category"),
        "question": c.get("text"),
        "my_answer": c.get("my_answer"),
        "score": c.get("score"),
        "better_version": c.get("better_version"),
        "happened_at": c.get("happened_at"),
        "source": c.get("source"),
    }


def _company_public(c: Dict[str, Any]) -> Dict[str, Any]:
    """公司库条目 → 前端友好（剔除 contributor_id / embedding_json / vector，隐私）。"""
    return {
        "id": c.get("id"),
        "company": c.get("company"),
        "position": c.get("position"),
        "category": c.get("category"),
        "question": c.get("text"),
        "context": c.get("context"),
        "source": c.get("source"),
    }


# ============================================================================
# 个人库端点
# ============================================================================

@knowledge_router.get("/personal", response_model=ApiResponse)
async def list_personal_api(
    user_id: str = Query(..., description="用户 ID"),
    q: str = Query("", description="搜索词（空则浏览翻页）"),
    position: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """个人面经库：有搜索词走语义检索，无词走分页浏览；均支持岗位/公司/题型筛选。严格 user_id 隔离。"""
    if q and q.strip():
        results = ks.search_personal(db, user_id, q, top_k=limit, position=position, company=company, category=category)
    else:
        results = ks.list_personal(db, user_id, offset, limit, position, company, category)
    return ApiResponse(
        status="success",
        message=f"共 {len(results)} 条",
        data={"items": [_personal_public(r) for r in results]},
    )


@knowledge_router.get("/personal/weakness", response_model=ApiResponse)
async def weakness_api(
    user_id: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """历史低分题（复练弱项入口）。"""
    results = ks.get_weakness_questions(db, user_id, limit=limit)
    return ApiResponse(status="success", message="OK", data={"items": [_personal_public(r) for r in results]})


@knowledge_router.delete("/personal/{episode_id}", response_model=ApiResponse)
async def delete_one_api(
    episode_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """删除单条个人面经（带 user_id 校验防越权——只能删自己的）。"""
    ok = ks.delete_one_personal(db, episode_id, user_id)
    if not ok:
        return ApiResponse(status="error", message="条目不存在或无权删除", data={"error_code": "NOT_FOUND"})
    return ApiResponse(status="success", message="已删除", data={"deleted": True})


@knowledge_router.delete("/personal", response_model=ApiResponse)
async def delete_all_api(
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """清空个人面经库（数据权利）。"""
    n = ks.delete_all_personal(db, user_id)
    return ApiResponse(status="success", message=f"已清空 {n} 条", data={"deleted": n})


# ============================================================================
# 公司库端点
# ============================================================================

@knowledge_router.get("/company", response_model=ApiResponse)
async def search_company_api(
    q: str = Query("", description="搜索词"),
    company: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    top_k: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """公司面经库检索（全局共享，按公司/岗位过滤）。来源优先级由检索权重保证。"""
    results = ks.search_company(db, q, top_k=top_k, company=company, position=position)
    return ApiResponse(
        status="success",
        message=f"共 {len(results)} 条",
        data={"items": [_company_public(r) for r in results]},
    )


@knowledge_router.get("/company/facets", response_model=ApiResponse)
async def facets_api(db: Session = Depends(get_db)):
    """公司库 facets（公司/岗位去重列表，前端侧边导航用）。"""
    facets = ks.company_facets(db)
    return ApiResponse(status="success", message="OK", data=facets)


@knowledge_router.post("/company/ugc", response_model=ApiResponse)
async def ugc_api(req: UgcContributeRequest, db: Session = Depends(get_db)):
    """UGC 贡献（脱敏：contributor_id 仅内部追溯，响应不返回）。"""
    if len(req.question.strip()) < 5:
        return ApiResponse(status="error", message="问题过短，请补充完整面经", data={"error_code": "TOO_SHORT"})
    ks.add_ugc_company(db, req.user_id, req.company, req.position, req.category, req.question, req.context)
    return ApiResponse(status="success", message="感谢贡献！面经已收录（脱敏后共享）", data={"contributed": True})
