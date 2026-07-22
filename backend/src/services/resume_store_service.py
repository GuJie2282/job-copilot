"""
简历存取服务（resume_store_service）

职责：封装 resumes 表的读写，对上层屏蔽持久化细节。
支持「用户 + 目标岗位 + 版本」三维度的存取，是简历优化模块路径 A（自动生成落 draft）
与路径 B（精修定稿落 finalized）共同的持久化出口。

对外核心操作：
- save_resume:       保存一份简历（新版本），version 未指定则自动取下一版本号
- get_resume:        读取单份简历
- update_resume:     更新字段（导出后回填 html、状态变 finalized 等）
- list_resumes:      按用户查全部简历（岗位→版本倒序，前端再分组）
- list_by_position:  查某岗位的全部版本
- next_version:      计算下一版本号
- delete_resume:     删除一份简历

【eval_report 无损序列化（对应任务 1.2.2）】
6 维评估报告是一个嵌套 dict（维度得分/总分/通过判定/改进优先级）。
本服务直接将其赋给 ResumeModel.eval_report_json（SQLAlchemy JSON 列），
由 SQLAlchemy 自动完成 dict ↔ JSON 列的双向无损转换——
无需手写序列化代码，与 profile_service 的 detail_json、JD 匹配的 gaps_json 同一机制。
前提：eval_report 的值均为 JSON 原生类型（dict/list/str/num/bool/None），评估服务输出时保证。

作者：求职 Copilot 项目
日期：2026-07-22
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.resume import ResumeModel

logger = logging.getLogger(__name__)


def next_version(db: Session, user_id: str, target_position: str) -> int:
    """
    计算下一版本号 = 当前最大版本 + 1（无历史版本则 1）。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        target_position: 目标岗位
    Returns:
        下一个版本号（int，≥1）
    """
    row = (
        db.query(ResumeModel)
        .filter(
            ResumeModel.user_id == user_id,
            ResumeModel.target_position == target_position,
        )
        .order_by(ResumeModel.version.desc())
        .first()
    )
    return (row.version + 1) if row else 1


def save_resume(
    db: Session,
    user_id: str,
    target_position: str,
    *,
    content_md: Optional[str] = None,
    html: Optional[str] = None,
    eval_report: Optional[Dict[str, Any]] = None,
    eval_score: Optional[float] = None,
    theme: Optional[str] = None,
    jd_result_id: Optional[str] = None,
    version: Optional[int] = None,
    status: str = "draft",
) -> ResumeModel:
    """
    保存一份简历（写入新版本）。

    version 未指定时自动取 next_version（同用户同岗位自增）。
    建议路径 A 生成完传 status="draft"；路径 B 定稿传 status="finalized"。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        target_position: 目标岗位
        content_md: Markdown 简历全文
        html: 渲染后的 HTML（导出后回填）
        eval_report: 6 维评估报告 dict（存入 JSON 列，无损）
        eval_score: 综合评估分（便于排序）
        theme: 使用的主题标识
        jd_result_id: 关联的 JD 匹配结果 ID（可空）
        version: 版本号（不传则自动）
        status: 状态 draft / refining / finalized
    Returns:
        保存后的 ResumeModel 实例
    """
    if version is None:
        version = next_version(db, user_id, target_position)

    row = ResumeModel(
        user_id=user_id,
        target_position=target_position,
        version=version,
        status=status,
        content_md=content_md,
        html=html,
        eval_report_json=eval_report,  # dict → JSON 列（SQLAlchemy 自动无损转换）
        eval_score=eval_score,
        theme=theme,
        jd_result_id=jd_result_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(
        "resume_saved",
        extra={"user_id": user_id, "position": target_position, "version": version, "status": status},
    )
    return row


def get_resume(db: Session, resume_id: str) -> Optional[ResumeModel]:
    """读取单份简历。不存在返回 None。"""
    return db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()


def update_resume(db: Session, resume_id: str, **fields: Any) -> Optional[ResumeModel]:
    """
    更新简历字段（仅更新提供的非 None 字段）。

    典型用途：导出后回填 html、评估后回填 eval_report/eval_score、状态变 finalized。
    支持的字段名：content_md / html / eval_report（自动映射到列 eval_report_json）/
                  eval_score / theme / status / jd_result_id。

    Returns:
        更新后的 ResumeModel；不存在返回 None。
    """
    row = get_resume(db, resume_id)
    if row is None:
        return None

    # eval_report 是对外语义名，对应的列叫 eval_report_json
    if "eval_report" in fields:
        fields["eval_report_json"] = fields.pop("eval_report")

    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    logger.info("resume_updated", extra={"resume_id": resume_id, "fields": list(fields)})
    return row


def list_resumes(db: Session, user_id: str) -> List[ResumeModel]:
    """
    按用户查全部简历，按岗位再按版本倒序排列。
    前端可据此按岗位分组、取每个岗位的最新版本。
    """
    return (
        db.query(ResumeModel)
        .filter(ResumeModel.user_id == user_id)
        .order_by(ResumeModel.target_position, ResumeModel.version.desc())
        .all()
    )


def list_by_position(db: Session, user_id: str, target_position: str) -> List[ResumeModel]:
    """查某用户某岗位的全部版本（版本倒序，首条即最新版）。"""
    return (
        db.query(ResumeModel)
        .filter(
            ResumeModel.user_id == user_id,
            ResumeModel.target_position == target_position,
        )
        .order_by(ResumeModel.version.desc())
        .all()
    )


def delete_resume(db: Session, resume_id: str) -> bool:
    """
    删除一份简历。
    Returns: True 原本存在已删；False 原本不存在。
    """
    row = get_resume(db, resume_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    logger.info("resume_deleted", extra={"resume_id": resume_id})
    return True
