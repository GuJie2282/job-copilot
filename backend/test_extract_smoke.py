"""
Phase 5.1.5 分段提取冒烟（project 段）：验证 _extract_one_section + 分段 prompt +
stream + JSON 解析 + 嵌套输出端到端工作，重点确认「项目名/角色/详情绑在同一对象，不错位」。

手动跑：cd backend && .venv/Scripts/python.exe test_extract_smoke.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.services.profile_extractor import _extract_one_section
from src.graph.config import get_llm

RESUME = """
郑梓焓

项目经验
校园二手交易平台  产品负责人  2023.03-2023.12
从0到1搭建交易闭环，注册用户5000+，月均交易800单，获校级创新奖。
选课助手  开发负责人  2022.09-2023.03
服务1万+学生，课程推荐准确率85%，对接教务系统。
"""

llm = get_llm(temperature=0.0, tier="strong", timeout=120.0)
print("提取 project 段（stream，约 20-60s）...\n")
data, ok = _extract_one_section(RESUME, "project", llm)
print(f"ok={ok}\n")
print(json.dumps(data, ensure_ascii=False, indent=2))

assert ok, "❌ project 段提取失败"
assert isinstance(data, list) and len(data) >= 2, f"❌ 应至少 2 个项目，实际: {data!r}"

# 关键：每个项目的 name/role/description 必须绑在同一对象（不错位）
print("\n--- 逐项目核对（name/role/description 同属一对象）---")
for i, p in enumerate(data):
    name = p.get("name")
    role = p.get("role")
    desc = (p.get("description") or "")[:40]
    print(f"项目[{i}]: name={name!r} | role={role!r} | desc={desc!r}")
    assert name, f"❌ 项目[{i}] 缺 name"

# 验证两个项目名都来自原文、且各自独立（不错位/不合并）
names = [p.get("name") for p in data]
assert any("交易" in (n or "") for n in names), f"❌ 缺「交易台」项目，实际: {names}"
assert any("选课" in (n or "") for n in names), f"❌ 缺「选课助手」项目，实际: {names}"
print("\n✅ project 段分段提取 OK：嵌套对象数组，name/role/description 绑在同一对象（不错位）")
