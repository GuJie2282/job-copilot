# -*- coding: utf-8 -*-
"""
evolve-resume-refine Tasks 3.4 / 6.2：split_reply_resume 切分 + 降级单测。

验证精修 LLM 结构化输出（<<<REPLY>>>说明<<<RESUME>>>简历）的切分：
- 正常切分 + 去代码块包裹
- 无标记 / 有 REPLY 无 RESUME 的降级（resume=None，调用方沿用上一版）

跑法：cd backend && python -m pytest test_refine_split.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.resume_generator import split_reply_resume  # noqa: E402


def test_normal_split_and_strip_codeblock():
    content = "<<<REPLY>>>我把经历量化了。<<<RESUME>>>\n```markdown\n# self-intro\nname: 张三\n```\n"
    reply, md = split_reply_resume(content)
    assert reply == "我把经历量化了。"
    assert md.startswith("# self-intro")
    assert "```" not in md  # 去代码块包裹


def test_no_marks_degrade():
    # 无任何标记：整段当说明，resume=None（调用方沿用上一版）
    reply, md = split_reply_resume("随便一段说明，没有标记")
    assert md is None
    assert reply == "随便一段说明，没有标记"


def test_reply_only_no_resume_degrade():
    # 有 REPLY 无 RESUME：说明有，简历缺
    reply, md = split_reply_resume("<<<REPLY>>>只有说明没有简历")
    assert md is None
    assert reply == "只有说明没有简历"


def test_resume_without_codeblock():
    reply, md = split_reply_resume("<<<REPLY>>>r<<<RESUME>>># self-intro\nname: 张三")
    assert md == "# self-intro\nname: 张三"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[OK] {name}")
    print("\n全部通过 ✓")
