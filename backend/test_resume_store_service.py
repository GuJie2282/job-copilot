# -*- coding: utf-8 -*-
"""
resume_store_service 单元测试（任务 1.2.3）

用内存 SQLite 隔离测试，不污染 job_copilot.db。
覆盖：保存 → 读取（含 eval_report 无损）→ 多版本自增 → 列表/分组 → 更新 → 删除。

跑法（在 backend 目录）：
    .venv/Scripts/python.exe test_resume_store_service.py
"""
import os
import sys

# 让脚本能 import src.*（无论从哪里启动）
BACKEND = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND, ".env"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.resume import ResumeModel
from src.services import resume_store_service as svc

# 内存 SQLite；只建 resumes 表（SQLite 默认不强制 FK，引用 users/jd_match_results 不影响测试）
_engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(_engine, tables=[ResumeModel.__table__])
_Session = sessionmaker(bind=_engine)


def _db():
    """新建一个会话"""
    return _Session()


def test_save_and_get():
    """保存 + 读取，验证字段与 eval_report 无损读回（任务 1.2.2 的验证）"""
    db = _db()
    row = svc.save_resume(
        db, "u1", "AI 产品经理",
        content_md="# self-intro\nname: 张三",
        eval_report={"overall_score": 82, "dimensions": {"jd_match": 75}, "passed": False},
        eval_score=82.0, theme="tech-dense", status="draft",
    )
    assert row.version == 1, f"首版应为 1，实际 {row.version}"
    assert row.id is not None

    got = svc.get_resume(db, row.id)
    assert got is not None
    assert got.content_md.startswith("# self-intro")
    # eval_report 无损读回（dict ↔ JSON 列往返）
    assert got.eval_report_json["overall_score"] == 82
    assert got.eval_report_json["dimensions"]["jd_match"] == 75
    assert got.eval_report_json["passed"] is False
    print("✓ test_save_and_get 通过（含 eval_report 无损读回）")
    db.close()


def test_multi_version():
    """同用户同岗位多次保存，版本号自动 1→2，next_version 返回 3"""
    db = _db()
    v1 = svc.save_resume(db, "u2", "后端工程师", content_md="v1")
    v2 = svc.save_resume(db, "u2", "后端工程师", content_md="v2")
    assert v1.version == 1 and v2.version == 2
    assert svc.next_version(db, "u2", "后端工程师") == 3
    print("✓ test_multi_version 通过（版本 1→2，下一版 3）")
    db.close()


def test_list_and_group():
    """list_resumes 按岗位分组、list_by_position 倒序"""
    db = _db()
    svc.save_resume(db, "u3", "AI PM", content_md="a1")
    svc.save_resume(db, "u3", "AI PM", content_md="a2")
    svc.save_resume(db, "u3", "后端", content_md="b1")

    all_rows = svc.list_resumes(db, "u3")
    assert len(all_rows) == 3, f"应 3 条，实际 {len(all_rows)}"

    ai = svc.list_by_position(db, "u3", "AI PM")
    assert len(ai) == 2 and ai[0].version == 2, "AI PM 倒序，首条应为 v2"
    print("✓ test_list_and_group 通过（共 3 条 / AI PM 2 版倒序）")
    db.close()


def test_update_and_delete():
    """更新（回填 html + 状态 finalized + eval_report）与删除"""
    db = _db()
    row = svc.save_resume(db, "u4", "测试岗", content_md="x")

    upd = svc.update_resume(
        db, row.id,
        html="<style>...</style>",
        status="finalized",
        eval_report={"overall_score": 90},
    )
    assert upd.html.startswith("<style>") and upd.status == "finalized"
    assert upd.eval_report_json["overall_score"] == 90

    assert svc.delete_resume(db, row.id) is True
    assert svc.get_resume(db, row.id) is None
    assert svc.delete_resume(db, row.id) is False  # 再删返回 False
    print("✓ test_update_and_delete 通过（回填 html/finalized/eval，删除成功）")
    db.close()


if __name__ == "__main__":
    test_save_and_get()
    test_multi_version()
    test_list_and_group()
    test_update_and_delete()
    print("\n✅ 全部 resume_store_service 测试通过")
