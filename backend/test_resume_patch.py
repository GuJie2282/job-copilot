# -*- coding: utf-8 -*-
"""
evolve-resume-refine Tasks 2.4 / 6.1：apply_patches_to_md 锚点局部回写单测。

验证每种可编辑原子（bullet / 经历 org·role / self-intro 字段 / contact / date / stack /
summary）编辑后回写正确，且**未编辑片段原样保留**（局部替换，不重建整份）。

跑法：cd backend && python -m pytest test_resume_patch.py -v
（或直接 python test_resume_patch.py）
"""
import os
import sys

# 让 src 可 import（无论从 backend/ 还是项目根跑）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from src.services.resume_exporter import apply_patches_to_md  # noqa: E402

MD = """# self-intro
name: 张三
role: AI 产品经理
education: 清华大学 · 计算机 · 本科 · 2022届
phone: 13800000000
email: zhangsan@example.com
location: 北京

# 工作经历
## 字节跳动 | 高级产品经理
date: 2022.07 — 至今
- 主导推荐系统重构，DAU 提升 30%
- 搭建数据看板，决策效率提升 2 倍

# 技能
- 编程语言: Python · SQL
- 工具: Figma · Axure
"""


def _ln(s, i):
    return s.splitlines()[i]


def test_bullet_rewrite_and_untouched_kept():
    out, _ = apply_patches_to_md(MD, [{"line": 11, "text": "主导推荐系统重构，DAU 提升 45%"}])
    assert _ln(out, 11) == "- 主导推荐系统重构，DAU 提升 45%"
    assert _ln(out, 12) == "- 搭建数据看板，决策效率提升 2 倍"  # 未编辑不变


def test_entry_org_role_merge_same_line():
    out, _ = apply_patches_to_md(MD, [
        {"line": 9, "field": "entry-org", "text": "ByteDance"},
        {"line": 9, "field": "entry-role", "text": "资深产品经理"},
    ])
    assert _ln(out, 9) == "## ByteDance | 资深产品经理"


def test_entry_org_only_role_preserved():
    out, _ = apply_patches_to_md(MD, [{"line": 9, "field": "entry-org", "text": "ByteDance"}])
    assert _ln(out, 9) == "## ByteDance | 高级产品经理"


def test_name_kv_keeps_key_prefix():
    out, _ = apply_patches_to_md(MD, [{"line": 1, "field": "name", "text": "李四"}])
    assert _ln(out, 1) == "name: 李四"


def test_contact_no_field_kv_fallback():
    out, _ = apply_patches_to_md(MD, [{"line": 4, "text": "13900000000"}])
    assert _ln(out, 4) == "phone: 13900000000"


def test_date_rewrite():
    out, _ = apply_patches_to_md(MD, [{"line": 10, "field": "date", "text": "2023.01 — 至今"}])
    assert _ln(out, 10) == "date: 2023.01 — 至今"


def test_stack_cat_chips_rebuild():
    out, _ = apply_patches_to_md(MD, [{"line": 15, "field": "stack", "cat": "编程语言", "chips": ["Python", "SQL", "Go"]}])
    assert _ln(out, 15) == "- 编程语言: Python · SQL · Go"


def test_out_of_range_patch_warns_and_keeps_md():
    out, w = apply_patches_to_md(MD, [{"line": 999, "text": "x"}])
    assert w, "应有 warning"
    assert out == MD, "越界 patch 不应改 md"


def test_line_count_stable_on_local_patch():
    out, _ = apply_patches_to_md(MD, [{"line": 11, "text": "新 bullet"}])
    assert len(out.splitlines()) == len(MD.splitlines())


if __name__ == "__main__":
    # 直接运行：逐个调用 test_ 函数，失败抛异常
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[OK] {name}")
    print("\n全部通过 ✓")
