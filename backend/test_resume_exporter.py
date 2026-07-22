# -*- coding: utf-8 -*-
"""
resume_exporter 装配测试（Phase 4 验证）。

验证：装配一份样例简历 → HTML 结构完整（style/header/sec-head/entry/bullet/chip）
     + ** 加粗转 <strong> + 预览壳无未填充占位符 + HTML 产物校验通过。

跑法（在 backend 目录）：
    .venv/Scripts/python.exe test_resume_exporter.py
"""
import os
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND, ".env"))

from src.services.resume_exporter import export_resume
from src.services.resume_validator import validate_resume_html

# 样例简历（覆盖 self-intro / 经历含 **加粗 / 技能 chips 三种结构）
SAMPLE = """# self-intro
name: 张三
role: 后端工程师
phone: 13800000000
email: zhangsan@example.com
location: 北京
education: 清华大学 · 计算机科学与技术 · 本科 · 2022届

# 工作经历

## 某互联网公司 | 后端工程师
date: 2022.07 — 至今

- 主导核心交易链路 redesign，**日均订单处理量提升 30%**
- 推动数据看板落地，决策效率提升 40%

# 技能
- 编程语言: Python · Java · Go
- 框架: FastAPI · Flask
"""


def test():
    result = export_resume(SAMPLE, target_position="后端工程师", title="张三-后端工程师")
    html = result["html"]            # 完整预览页
    body = result["body_html"]       # 产物正文（<style> + 原子）

    print(f"theme: {result['theme']}")
    print(f"full html length: {len(html)}, body length: {len(body)}")

    # 结构完整性
    assert "<style>" in body, "缺 <style>"
    assert 'class="resume-header"' in body, "缺 Header"
    assert "张三" in body, "Header 缺姓名"
    assert "后端工程师" in body, "Header 缺 role"
    assert "清华大学" in body, "Header 缺 education"
    assert 'class="sec-head"' in body, "缺 sec-head"
    assert 'class="entry"' in body, "缺 entry"
    assert 'class="bullet"' in body, "缺 bullet"
    assert 'class="chip"' in body, "缺技能 chip"
    assert "Python" in body and "Go" in body, "技能 chip 缺内容"

    # **加粗 → <strong>
    assert "<strong>日均订单处理量提升 30%</strong>" in body, "**未正确转 <strong>"

    # 预览壳无未填充占位符
    assert "{{" not in html, "预览页有未填充的 {{占位符}}"
    assert "<!--RESUME_BODY-->" not in html, "槽位 RESUME_BODY 未被替换"
    assert "<!--RESUME_STYLE-->" not in html, "槽位 RESUME_STYLE 未被替换"

    # HTML 产物硬校验（无占位符 + 有 Header）
    vr = validate_resume_html(body)
    assert vr.passed, f"HTML 校验未通过：{vr.errors}"

    # 审查结果
    audit = result["audit"]
    print(f"audit: modules={audit['md_modules']}, sec_head={audit['html_sec_head']}, "
          f"entries={audit['html_entries']}/{audit['md_entries']}, "
          f"bullets={audit['html_bullets']}/{audit['md_bullets']}")
    print(f"audit issues: {audit['issues'] or '无'}")
    print(f"pages: {result['pages']['estimated_pages']} 页（{result['pages']['char_count']} 字符）")

    print("\n✅ Phase 4 装配验证通过（结构完整 + 加粗转换 + 预览壳注入 + HTML 校验通过）")


if __name__ == "__main__":
    test()
