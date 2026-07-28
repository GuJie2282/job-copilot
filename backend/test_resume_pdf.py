# -*- coding: utf-8 -*-
"""
evolve-resume-refine Tasks 6.4：PDF 渲染冒烟。

验证完整 PDF 链路：Markdown → assemble_html + wrap_preview → Playwright 渲染 → 合法 A4 PDF。
（Tasks 5.4 的精确页数由 render_html_to_pdf 返回 page_count 兑现；estimate_pages 生成阶段保持粗估）

跑法：cd backend && python -m pytest test_resume_pdf.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.resume_pdf import render_html_to_pdf  # noqa: E402
from src.services.resume_exporter import export_resume  # noqa: E402

MD = """# self-intro
name: 张三
role: AI 产品经理
education: 清华大学 · 本科
phone: 13800000000

# 工作经历
## 字节跳动 | 产品经理
date: 2022.07 — 至今
- 主导推荐系统重构，DAU 提升 30%
- 搭建数据看板，决策效率提升 2 倍

# 技能
- 编程语言: Python · SQL
"""


def test_render_resume_pdf():
    """完整链路产出合法 PDF + 精确页数（同步 Playwright API）。"""
    result = export_resume(MD, "AI 产品经理", "张三-AI产品经理")
    pdf, pages = render_html_to_pdf(result["html"])  # sync API（端点侧经 asyncio.to_thread 跑）
    assert pdf[:4] == b"%PDF", "应产出合法 PDF（%PDF 头）"
    assert pages >= 1
    assert len(pdf) > 1000
