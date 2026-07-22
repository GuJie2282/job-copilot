# -*- coding: utf-8 -*-
"""
resume_validator 单元测试 + Phase 2 模块 import 自检（任务 2.3 验证）。

覆盖：
- validator：合规简历通过 / 缺 self-intro 报错 / HTML 占位符报错
- generator：gap_rewrite_strategy / 生成 prompt 拼接
- evaluator：评估 prompt 拼接 / ResumeEvalReport Pydantic 构造
- import 自检：三个服务 + 两个 prompt 函数都能正常导入（无语法/导入链错误）

跑法（在 backend 目录）：
    .venv/Scripts/python.exe test_resume_validator.py
"""
import os
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND, ".env"))

# ── import 自检（触发完整导入链；不调用 LLM，不检查 API key）──
from src.services import resume_validator as rv
from src.services import resume_generator as rg
from src.services import resume_evaluator as rev
from src.graph.prompts import get_resume_generation_prompt, get_resume_evaluation_prompt
print("✓ import 自检通过（validator / generator / evaluator / prompts）")


# ── 一份合规简历（应通过 MD 校验）──
GOOD_MD = """# self-intro
name: 张三
role: AI 产品经理
phone: 13800000000
email: zhangsan@example.com
education: 清华大学 · 计算机科学与技术 · 本科 · 2022届

# 工作经历

## 某互联网公司 | 产品经理
date: 2022.07 — 至今

- 主导核心交易链路 redesign，日均订单处理量提升 30%
- 推动数据看板落地，决策效率提升 40%
"""

# ── 缺首模块 self-intro 的坏简历 ──
BAD_MD = """# 工作经历

## 某公司 | 产品经理
date: 2022.07 — 至今

- 做了一些事
"""


def test_validator_md_pass():
    r = rv.validate_resume_md(GOOD_MD)
    assert r.passed, f"合规简历应通过，但 errors={r.errors}"
    print(f"✓ 合规简历通过校验（warnings={len(r.warnings)}）")


def test_validator_md_fail():
    r = rv.validate_resume_md(BAD_MD)
    assert not r.passed, "缺 self-intro 应不通过"
    assert any("self-intro" in e for e in r.errors), "应报 self-intro 错误"
    print(f"✓ 坏简历正确拦截（errors={len(r.errors)}）")


def test_validator_html_placeholder():
    r = rv.validate_resume_html('<div class="name">{{name}}</div>')
    assert not r.passed, "占位符残留应报错"
    print(f"✓ HTML 占位符残留正确拦截（errors={len(r.errors)}）")


def test_gap_strategy():
    s = rg.gap_rewrite_strategy("hard_skill")
    assert "强化" in s
    assert rg.gap_rewrite_strategy("soft_skill") != rg.gap_rewrite_strategy("hard_skill")
    print("✓ gap_rewrite_strategy 四类策略正常")


def test_generation_prompt():
    p = get_resume_generation_prompt(
        '{"name": "张三"}', "- [hard_skill] Python（现状：无）→ 策略：强化", "AI PM", True
    )
    assert "AI PM" in p and "self-intro" in p and "STAR" in p
    # 无 Gap 通用模式
    p2 = get_resume_generation_prompt('{"name": "张三"}', "", "AI PM", False)
    assert "通用生成" in p2
    print("✓ 生成 prompt 拼接正常（有 Gap / 无 Gap 两种模式）")


def test_evaluation_prompt_and_model():
    p = get_resume_evaluation_prompt(GOOD_MD, "AI PM", "[]", '{"name": "张三"}')
    assert "basic_norm" in p and "quantification" in p and "0.25" in p
    print("✓ 评估 prompt 拼接正常（6 维 + 权重）")

    # Pydantic 模型构造（用六维齐全的示例）
    sample = {
        "overall_score": 80,
        "passed": False,
        "dimensions": {
            k: {"score": 80, "weight": 0.15, "passed": True, "items": []}
            for k in rev.DIMENSION_KEYS
        },
        "feedback_priorities": [{"priority": "high", "suggestion": "补量化指标"}],
    }
    report = rev.ResumeEvalReport(**sample)
    assert len(report.dimensions) == 6
    assert report.feedback_priorities[0].priority == "high"
    print(f"✓ ResumeEvalReport 构造正常（{len(report.dimensions)} 维）")


if __name__ == "__main__":
    test_validator_md_pass()
    test_validator_md_fail()
    test_validator_html_placeholder()
    test_gap_strategy()
    test_generation_prompt()
    test_evaluation_prompt_and_model()
    print("\n✅ Phase 2 验证全部通过（import + validator + prompt + Pydantic）")
