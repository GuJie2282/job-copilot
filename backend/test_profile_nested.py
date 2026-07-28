"""
Phase 4+5.1 后端静态验证（不依赖 LLM）：
- 4.1.1 UserProfile 嵌套结构 + Pydantic 校验
- 4.1.2 confidence 在嵌套结构下的路径（education[0].school 等）
- 4.1.3 历史扁平→嵌套迁移
- 4.1.4 存取（profile_service 迁移在读取层）
- 5.1.4 分段合并 _merge_sections
- import 链（resume.py 改动后语法/引用正确）

手动跑：cd backend && .venv/Scripts/python.exe test_profile_nested.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 1. import 链（含 resume.py 改动）
from src.graph.config import UserProfile, EducationItem, WorkExperienceItem, ProjectItem
from src.services.profile_extractor import _merge_sections, SECTION_ORDER, SECTION_LABEL
from src.services.profile_service import _migrate_legacy_flat_to_nested
from src.services.quality_checker import calculate_profile_confidence
from src.api.resume import _extract_profile_with_retry  # 触发 resume.py 语法/引用检查
print("✅ import 链正常（config/profile_extractor/profile_service/resume）")

# 2. UserProfile 嵌套校验（4.1.1）
profile_dict = {
    "name": "张三",
    "education": [{"school": "清华", "degree": "本科", "major": "CS", "graduation_year": "2022"}],
    "work_experience": [{"company": "A公司", "position": "PM", "duration": "2022-至今", "description": "负责XX"}],
    "projects": [{"name": "项目A", "role": "负责人", "description": "做了XX"}],
    "technical_skills": ["Python"],
}
up = UserProfile(**profile_dict)
assert up.education[0].school == "清华"
assert up.projects[0].name == "项目A"
assert up.work_experience[0].description == "负责XX"
dumped = up.model_dump()
assert "schools" not in dumped and "education" in dumped  # 旧字段已移除
print("✅ 4.1.1 UserProfile 嵌套校验 OK（旧扁平字段已移除）")

# 3. confidence 嵌套路径（4.1.2）
text = "张三 清华 本科 CS 2022 A公司 PM 负责XX 项目A 负责人 做了XX Python"
conf = calculate_profile_confidence(profile_dict, text)
assert "education[0].school" in conf, f"缺嵌套路径，实际: {list(conf.keys())}"
assert "projects[0].name" in conf
print(f"✅ 4.1.2 confidence 嵌套路径 OK（如 education[0].school、projects[0].name）")

# 4. 历史扁平→嵌套迁移（4.1.3）
legacy = {
    "name": "李四",
    "schools": ["北大", "复旦"],
    "degrees": ["本科", "硕士"],
    "majors": ["CS", "AI"],
    "graduation_years": ["2020", "2023"],
    "companies": ["B公司"],
    "positions": ["PM"],
    "durations": ["2023-至今"],
    "work_descriptions": ["管产品"],
    "project_names": ["项目B"],
    "project_roles": ["主R"],
    "project_descriptions": ["从0到1"],
}
migrated = _migrate_legacy_flat_to_nested(legacy)
assert len(migrated["education"]) == 2
assert migrated["education"][0]["school"] == "北大"
assert migrated["education"][1]["major"] == "AI"
assert migrated["work_experience"][0]["company"] == "B公司"
assert migrated["projects"][0]["name"] == "项目B"
assert "schools" not in migrated and "companies" not in migrated
# 已是新结构（无 legacy 字段）→ 空操作
new_struct = {"name": "X", "education": [{"school": "Y"}]}
assert _migrate_legacy_flat_to_nested(new_struct) == new_struct
print("✅ 4.1.3 历史扁平→嵌套迁移 OK（含空操作兜底）")

# 5. 分段合并（5.1.4）
parts = {
    "basic": {"name": "王五", "phone": "138", "email": None, "location": None, "self_summary": "PM"},
    "education": [{"school": "浙大"}],
    "work": [{"company": "C公司"}],
    "project": [{"name": "项目C"}],
    "skills": {"technical_skills": ["SQL"], "soft_skills": [], "languages": [], "achievements": ["奖"]},
}
merged = _merge_sections(parts)
assert merged["name"] == "王五"
assert merged["education"] == [{"school": "浙大"}]
assert merged["work_experience"] == [{"company": "C公司"}]
assert merged["projects"] == [{"name": "项目C"}]
assert merged["technical_skills"] == ["SQL"]
assert merged["achievements"] == ["奖"]
# 合并结果能通过 UserProfile 校验
UserProfile(**merged)
print("✅ 5.1.4 分段合并 OK，且合并结果通过 UserProfile 校验")

# 6. 段顺序与文案齐备（流式 stage 事件用）
assert SECTION_ORDER == ["basic", "education", "work", "project", "skills"]
assert all(s in SECTION_LABEL for s in SECTION_ORDER)
print("✅ 段顺序与进度文案齐备")

print("\n✅ Phase 4+5.1 后端静态验证全部通过")
