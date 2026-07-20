"""
模拟面试 API 验证（add-mock-interview 阶段 4.2.4）
===================================================

用 FastAPI TestClient 进程内测面试 API（不碰运行中的服务器）。
验证会话式 API 流程 + 多态响应 + checkpointer 集成 + 持久化：
  1. POST /api/interview/sessions      → 创建会话 + 第一题
  2. POST .../answer                    → 多态响应（继续问 / 结束）
  3. GET  .../sessions/{id}             → 状态 + transcript（续面）
  4. GET  .../sessions                  → 历史列表

不跑完整面试（省时），验证 API 接口契约即可。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient

from src.main import app
from src.models.base import SessionLocal
from src.services.profile_service import save_profile, delete_profile

client = TestClient(app)

TEST_UID = "test-interview-api-001"

PROFILE = {
    "name": "李四",
    "target_positions": ["产品经理"],
    "companies": ["字节跳动"],
    "positions": ["产品经理"],
    "work_descriptions": ["负责 feed 推荐产品，DAU 提升 15%"],
    "project_names": ["推荐重构"],
    "project_descriptions": ["CTR 提升 20%"],
    "technical_skills": ["SQL", "A/B 测试"],
}


def seed():
    db = SessionLocal()
    save_profile(db, TEST_UID, PROFILE)
    db.close()


def cleanup():
    db = SessionLocal()
    delete_profile(db, TEST_UID)
    # 清理本测试创建的会话记录
    from src.models.interview import InterviewSessionModel
    db.query(InterviewSessionModel).filter(InterviewSessionModel.user_id == TEST_UID).delete()
    db.commit()
    db.close()


def run():
    print("=" * 70)
    print("模拟面试 API 验证（TestClient 进程内）")
    print("=" * 70)

    seed()
    try:
        # ---------- 0. 画像缺失场景 ----------
        print("\n[0] 画像缺失场景（用不存在的 user_id）")
        r = client.post("/api/interview/sessions", json={
            "user_id": "nonexistent-user", "interview_type": "full", "intensity": "short"
        })
        d = r.json()
        print(f"    status={d['status']} error_code={d.get('data', {}).get('error_code')}")
        check0 = d["status"] == "error" and d.get("data", {}).get("error_code") == "PROFILE_MISSING"
        print(f"    [{'✓ PASS' if check0 else '✗ FAIL'}] 画像缺失正确返回 PROFILE_MISSING")

        # ---------- 1. 创建会话 ----------
        print("\n[1] POST /sessions（创建会话）")
        r = client.post("/api/interview/sessions", json={
            "user_id": TEST_UID,
            "interview_type": "full",
            "intensity": "short",
            "interview_mode": "real",
        })
        d = r.json()
        print(f"    status={d['status']} message={d['message']}")
        session_id = d["data"]["session_id"]
        first_q = d["data"]["first_question"]
        print(f"    session_id={session_id}")
        print(f"    第一题：{(first_q or {}).get('question', '')[:60]}")
        check1 = d["status"] == "success" and bool(first_q and first_q.get("question"))
        print(f"    [{'✓ PASS' if check1 else '✗ FAIL'}] 创建会话返回 session_id + 第一题")

        # ---------- 2. 提交回答（多态）----------
        print("\n[2] POST .../answer（提交回答，验证多态响应）")
        r = client.post(f"/api/interview/sessions/{session_id}/answer", json={
            "answer": "我在字节负责 feed 推荐，用 A/B 测试优化召回策略，DAU 提升 15%。"
        })
        d = r.json()
        status_field = d["data"].get("interview_status")
        print(f"    interview_status={status_field}")
        if status_field == "interviewing":
            print(f"    下一题：{(d['data'].get('next_question') or {}).get('question', '')[:60]}")
        check2 = d["status"] == "success" and status_field in ("interviewing", "finished")
        print(f"    [{'✓ PASS' if check2 else '✗ FAIL'}] 多态响应（interviewing/finished）")

        # ---------- 3. 查会话状态 + transcript ----------
        print("\n[3] GET .../sessions/{id}（查状态 + transcript，续面用）")
        r = client.get(f"/api/interview/sessions/{session_id}")
        d = r.json()
        transcript = d["data"].get("transcript") or []
        print(f"    status={d['data']['status']} transcript 轮数={len(transcript)}")
        check3 = d["status"] == "success" and len(transcript) >= 1
        print(f"    [{'✓ PASS' if check3 else '✗ FAIL'}] 续面能取到 transcript")

        # ---------- 4. 历史列表 ----------
        print("\n[4] GET .../sessions?user_id=（历史列表）")
        r = client.get(f"/api/interview/sessions?user_id={TEST_UID}")
        d = r.json()
        items = d["data"].get("items") or []
        print(f"    历史会话数：{len(items)}")
        check4 = d["status"] == "success" and len(items) >= 1
        print(f"    [{'✓ PASS' if check4 else '✗ FAIL'}] 历史列表含本场会话")

        # ---------- 5. 会话不存在场景 ----------
        print("\n[5] 会话不存在场景")
        r = client.get("/api/interview/sessions/nonexistent-session-id")
        d = r.json()
        check5 = d["status"] == "error" and d.get("data", {}).get("error_code") == "SESSION_NOT_FOUND"
        print(f"    [{'✓ PASS' if check5 else '✗ FAIL'}] 不存在会话返回 SESSION_NOT_FOUND")

        # ---------- 总结 ----------
        all_checks = [check0, check1, check2, check3, check4, check5]
        print("\n" + "=" * 70)
        print(f"总结：{'✅ 面试 API 流程验证通过' if all(all_checks) else '❌ 有检查未通过'} ({sum(all_checks)}/{len(all_checks)})")
        print("=" * 70)
    finally:
        cleanup()


if __name__ == "__main__":
    run()
