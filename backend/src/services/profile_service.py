"""
用户画像存取服务（profile_service）

职责：封装 user_profiles 表的读写，对上层屏蔽「混合数据模型」（标量列 + JSON 列）的细节。

对外提供三个核心操作：
- save_profile:    upsert（首次插入 / 已存在则覆盖更新），保证每个用户仅一份当前画像
- get_profile:     读取完整画像（标量 + 明细 JSON），不存在返回 None
- delete_profile:  删除画像

【无损序列化（对应任务 2.1.2）】
画像在 API 层是一个 dict（同时含标量字段和不定长列表）。本服务负责 dict ↔ 表结构的转换：
- 存库：把 dict 拆成「标量列」+「明细 JSON 列」分别写入。
- 读库：把「标量列」+「明细 JSON 列」合并回完整 dict。
这样上层始终用统一的画像 dict 进出，不感知表结构。

作者：求职 Copilot 项目
日期：2026-07-14
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.profile import UserProfileModel

logger = logging.getLogger(__name__)


# 画像 dict 中「存为标量列」的字段名。
# 注意：必须与 UserProfileModel 的标量列名一一对应（quality_score / source 除外，它们由专用参数管理）。
SCALAR_FIELDS = (
    "name",
    "email",
    "phone",
    "location",
    "location_preference",
    "salary_range",
    "industry",
)


# ----------------------------------------------------------------------------
# 内部转换：dict ↔ 表行
# ----------------------------------------------------------------------------

def _split_profile(profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    把画像 dict 拆成「标量列」与「明细 JSON」两部分。

    Returns:
        (scalars, detail):
          scalars - 应写入标量列的字段
          detail  - 其余字段（教育/工作/项目/技能等不定长列表），整体存入 detail_json
    """
    scalars: Dict[str, Any] = {}
    detail: Dict[str, Any] = {}
    for key, value in (profile or {}).items():
        if key in SCALAR_FIELDS:
            scalars[key] = value
        else:
            detail[key] = value
    return scalars, detail


def _merge_profile(row: UserProfileModel) -> Optional[Dict[str, Any]]:
    """
    把数据库行合并回完整的画像 dict（明细 JSON + 标量列 + 元信息）。

    row 为 None 时返回 None。
    """
    if row is None:
        return None

    # 1. 先放入明细 JSON（不定长列表）
    profile: Dict[str, Any] = dict(row.detail_json or {})

    # 2. 标量列覆盖写入（保证标量优先，避免与 detail_json 同名键冲突）
    for field in SCALAR_FIELDS:
        value = getattr(row, field, None)
        if value is not None:
            profile[field] = value

    # 3. 元信息（画像质量分 / 来源）也并入，便于上层直接展示
    if row.quality_score is not None:
        profile["quality_score"] = row.quality_score
    if row.source is not None:
        profile["source"] = row.source

    return profile


# ----------------------------------------------------------------------------
# 对外接口
# ----------------------------------------------------------------------------

def save_profile(
    db: Session,
    user_id: str,
    profile: Dict[str, Any],
    confidence: Optional[Dict[str, Any]] = None,
    quality_score: Optional[float] = None,
    source: Optional[str] = None,
) -> UserProfileModel:
    """
    保存画像（upsert）：首次插入；已存在则覆盖更新。保证每个用户仅一份当前画像。

    覆盖语义：明细 JSON 列整体替换为新 profile 的明细（未提供的字段会消失），
    这与 spec「覆盖更新而非产生重复」一致。

    Args:
        db:           数据库会话
        user_id:      用户 ID
        profile:      完整画像 dict（含标量与不定长列表）
        confidence:   各字段置信度（可选）
        quality_score: 简历文本质量分（可选）
        source:       画像来源 file/text/manual（可选）
    Returns:
        保存后的 UserProfileModel 实例
    """
    scalars, detail = _split_profile(profile or {})

    # 查是否已有画像（决定 insert 还是 update）
    row = db.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
    is_new = row is None
    if is_new:
        row = UserProfileModel(user_id=user_id)
        db.add(row)

    # 写标量列
    for field, value in scalars.items():
        setattr(row, field, value)

    # 写明细 JSON + 置信度 + 元信息
    row.detail_json = detail
    row.confidence_json = confidence
    if quality_score is not None:
        row.quality_score = quality_score
    if source is not None:
        row.source = source
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)

    logger.info("profile_saved", extra={"user_id": user_id, "is_new": is_new})
    return row


def get_profile(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    读取用户完整画像（标量 + 明细）。不存在返回 None。
    """
    row = db.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
    return _merge_profile(row)


def get_profile_confidence(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """读取画像的各字段置信度。无画像返回 None。"""
    row = db.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
    return row.confidence_json if row else None


def delete_profile(db: Session, user_id: str) -> bool:
    """
    删除用户画像。

    Returns:
        True  - 原本有画像，已删除
        False - 原本就没有画像
    """
    row = db.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    logger.info("profile_deleted", extra={"user_id": user_id})
    return True
