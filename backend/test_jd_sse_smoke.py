"""
JD 匹配 SSE 端点冒烟（验证区块一 jd.py 迁移无回归，任务 1.1.2 回归验证）。

用 urllib（标准库）发 POST + 流式读，避开 curl 在 Windows bash 下的中文 body 编码坑。
测试用户无画像 → 预期跑到 profile_missing 分支，能验证：
  - 后端 reload 了 jd.py（端点活、路由注册）
  - SSE 通道工作（stage / error 事件格式正确）

手动跑：cd backend && .venv/Scripts/python.exe test_jd_sse_smoke.py
"""
import json
import urllib.request
import urllib.error

DATA = json.dumps({
    "jd_text": (
        "高级产品经理岗位。职责：1) 负责公司核心产品线的规划与路线图制定；"
        "2) 深入调研用户需求，输出 PRD 与原型；3) 协调研发、设计、运营推进产品迭代；"
        "4) 建立数据指标体系，通过数据分析驱动决策。要求：本科及以上学历，"
        "计算机或相关专业优先；3 年以上互联网产品经验，有 toB SaaS 经验者优先；"
        "熟练使用 Axure、Figma、SQL 与数据分析工具；优秀的沟通协调与项目管理能力；"
        "有技术背景、能独立推进复杂项目者优先。"
    ),
    "user_id": "6c888cc9-ff0d-47b2-8d3e-09ea85f19a8b",
}, ensure_ascii=False).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8001/api/jd/match",
    data=DATA,
    headers={"Content-Type": "application/json"},
)

print("发送 JD 匹配请求，读取 SSE 流...\n")
seen_events = []
try:
    resp = urllib.request.urlopen(req, timeout=90)
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").rstrip("\n")
        if not line:
            continue
        print(line)
        if line.startswith("event:"):
            seen_events.append(line[6:].strip())
        if len(seen_events) >= 5:
            break
    print(f"\n=== 收到事件类型：{seen_events} ===")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"❌ HTTP {e.code}: {body[:300]}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")
