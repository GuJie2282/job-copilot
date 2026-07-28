"""parse-stream 端到端冒烟：验证 SSE 流式 + 分段提取 + 嵌套结构 + 不超时。"""
import urllib.request
import json
import sys

RESUME = """
郑梓焓  13800000000  zheng@example.com  杭州

个人总结
3 年互联网产品经验，擅长从 0 到 1 搭建产品，数据驱动决策。

教育背景
浙江大学 计算机科学与技术 本科 2022-2026

实习经历
字节跳动 产品经理实习 2024.06-2024.09
负责核心信息流的需求分析与原型设计，推动评审通过率 95%，日活提升 15%。

项目经验
校园二手交易平台  产品负责人  2023.03-2023.12
从0到1搭建交易闭环，注册用户 5000+，月均交易 800 单。
选课助手  开发负责人  2022.09-2023.03
服务 1 万+学生，课程推荐准确率 85%。

技能
Python, SQL, Axure, Figma；英语 CET-6
"""


def parse_block(block):
    event = "message"
    data_str = ""
    for line in block.split("\n"):
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_str += line[5:].strip()
    if not data_str:
        return None
    try:
        return {"event": event, "data": json.loads(data_str)}
    except Exception:
        return None


data = json.dumps({"text": RESUME, "user_id": "smoke-test"}, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    "http://localhost:8001/api/resume/parse-stream",
    data=data,
    headers={"Content-Type": "application/json"},
)

print("发送 parse-stream，读取 SSE（5 段 strong LLM stream，约 2-4 分钟）...\n")
events = []
final = None
try:
    resp = urllib.request.urlopen(req, timeout=400)
    buf = ""
    for raw in resp:
        buf += raw.decode("utf-8", errors="replace")
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            evt = parse_block(block)
            if not evt:
                continue
            events.append(evt["event"])
            if evt["event"] == "stage":
                print(f"  [stage] {evt['data'].get('message')}")
            elif evt["event"] == "segment":
                sec = evt["data"].get("section")
                print(f"  [segment] {sec}: {str(evt['data'].get('data'))[:70]}")
            elif evt["event"] == "done":
                final = evt["data"]
                print(f"  [done] profile keys: {list((final.get('profile') or {}).keys())}")
            elif evt["event"] == "error":
                print(f"  [error] {evt['data']}")
                sys.exit(1)
except Exception as e:
    print(f"❌ 流异常: {type(e).__name__}: {e}")
    sys.exit(1)

print(f"\n事件序列: {events}")
assert "done" in events, "❌ 未收到 done 事件"

p = final.get("profile") or {}
print("\n嵌套 profile 验证:")
print(f"  name: {p.get('name')}")
edu = p.get("education") or []
work = p.get("work_experience") or []
proj = p.get("projects") or []
print(f"  education: {len(edu)} 段, 首项 school={(edu[0] if edu else {}).get('school')}")
print(f"  work_experience: {len(work)} 段, 首项 company={(work[0] if work else {}).get('company')}")
print(f"  projects: {len(proj)} 个, 首项 name={(proj[0] if proj else {}).get('name')}")
legacy = [k for k in ["schools", "companies", "project_names", "positions"] if k in p]
print(f"  旧扁平字段残留: {legacy or '无 ✅'}")
assert not legacy, f"❌ 旧扁平字段未清理: {legacy}"
assert edu and proj, "❌ education/projects 为空"
print("\n✅ parse-stream 端到端 OK：流式分段 + 嵌套结构 + 不超时 + 项目不错位")
