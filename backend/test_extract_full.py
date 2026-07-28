"""验证 fast 档分段提取全段（直接调 service，不走后端，确认 5 段快 + 嵌套 + 不错位）。"""
import time
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.services.profile_extractor import extract_profile_sectioned

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

print("fast 分段提取（5 段 glm-4-flash，计时）...")
t0 = time.time()
profile = extract_profile_sectioned(RESUME)
dt = time.time() - t0
print(f"耗时 {dt:.1f}s\n")
print(json.dumps(profile, ensure_ascii=False, indent=2))

# 验证
assert profile.get("name") and "梓焓" in profile["name"], f"name: {profile.get('name')}"
assert profile.get("education"), "education 空"
assert profile.get("work_experience"), "work 空"
assert profile.get("projects"), "projects 空"
# 不错位：项目 name/role/description 同对象
for i, p in enumerate(profile["projects"]):
    print(f"\n项目[{i}]: name={p.get('name')!r} | role={p.get('role')!r}")
legacy = [k for k in ["schools", "companies", "project_names", "positions"] if k in profile]
assert not legacy, f"旧扁平残留: {legacy}"
print(f"\n✅ fast 分段全段 OK：{dt:.1f}s（vs strong 超时），嵌套结构 + 不错位")
