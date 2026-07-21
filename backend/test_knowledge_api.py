"""
面经库 API smoke 验证（add-mock-interview 阶段 B1）
===================================================

用 TestClient 验证面经库端点路由通 + 响应格式 + 隐私剔除（contributor_id 不外泄）。
service 层逻辑已在 test_knowledge_service 验证，这里只测 API 薄包装。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from fastapi.testclient import TestClient

from src.main import app
from src.models.base import SessionLocal
from src.services import knowledge_service as ks

client = TestClient(app)

UID = "test-knowledge-api-001"


def setup():
    db = SessionLocal()
    ks.seed_curated(db)  # 公司库种子（幂等）
    db.close()


def cleanup():
    """清测试 UGC（保留 curated 种子）。"""
    db = SessionLocal()
    from src.models.knowledge import CompanyQuestionModel
    db.query(CompanyQuestionModel).filter(
        CompanyQuestionModel.source == "ugc",
        CompanyQuestionModel.contributor_id == UID,
    ).delete(synchronize_session=False)
    ks.delete_all_personal(db, UID)
    db.commit()
    db.close()


def run():
    print("=" * 60)
    print("面经库 API smoke 验证")
    print("=" * 60)
    setup()
    cleanup()
    try:
        checks = []

        # 1. 公司库 facets
        r = client.get("/api/knowledge/company/facets")
        body = r.json()
        positions = (body.get("data") or {}).get("positions") or []
        checks.append(("GET /company/facets 返回岗位聚合", body["status"] == "success" and len(positions) > 0))
        print(f"  facets 岗位：{positions}")

        # 2. 公司库搜索（语义召回产品题）
        r = client.get("/api/knowledge/company", params={"q": "产品 DAU 下滑 排查"})
        items = (r.json().get("data") or {}).get("items") or []
        hit = any("DAU" in it["question"] or "下滑" in it["question"] for it in items)
        checks.append(("GET /company?q= 语义召回", r.json()["status"] == "success" and hit))

        # 3. 个人库列表（test user 初始应为空）
        r = client.get("/api/knowledge/personal", params={"user_id": UID})
        items = (r.json().get("data") or {}).get("items") or []
        checks.append(("GET /personal 空用户返回空列表", r.json()["status"] == "success" and len(items) == 0))

        # 4. UGC 贡献
        r = client.post("/api/knowledge/company/ugc", json={
            "user_id": UID, "position": "产品经理", "category": "behavioral",
            "question": "讲一次你跨部门推动一个有争议决策落地的完整经历。",
            "context": "考查跨部门协作与说服力",
        })
        checks.append(("POST /company/ugc 贡献成功", r.json().get("status") == "success"))

        # 5. 隐私剔除：UGC 后搜公司库，响应不应含 contributor_id / embedding_json
        r = client.get("/api/knowledge/company", params={"q": "跨部门 推动争议"})
        items = (r.json().get("data") or {}).get("items") or []
        leaked = any("contributor_id" in it or "embedding_json" in it for it in items)
        checks.append(("隐私剔除：响应无 contributor_id/embedding_json", not leaked))

        # 6. 来源标签透传（curated 题应有 source）
        r = client.get("/api/knowledge/company", params={"q": "产品", "top_k": 3})
        items = (r.json().get("data") or {}).get("items") or []
        has_source = all("source" in it for it in items) if items else False
        checks.append(("来源标签 source 透传", has_source))

        # ============ 汇总 ============
        print("\n" + "=" * 60)
        for name, ok in checks:
            print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")
        print("=" * 60)
        return all(ok for _, ok in checks)
    finally:
        cleanup()


if __name__ == "__main__":
    run()
