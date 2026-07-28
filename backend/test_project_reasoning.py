"""验证 project 段 reasoning 不循环（prompt 优化后）+ 提取所有项目（独立 + 实习里的）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.services.llm_reasoning import stream_chat_with_reasoning
from src.graph.prompts import get_section_extraction_prompt
from src.services.profile_extractor import _extract_json_loose

RESUME = """
郑梓焓  138  zheng@x  杭州

实习经历
字节跳动 产品实习 2024.06-2024.09
负责信息流产品，主导「内容推荐优化」项目，通过 AB 测试提升日活 15%。

项目经历
校园二手交易平台  产品负责人  2023.03-2023.12
从0到1搭建，用户 5000。
"""


async def main():
    prompt = get_section_extraction_prompt(RESUME, "project")
    reasoning = []
    content = []
    async for kind, delta in stream_chat_with_reasoning(prompt, temperature=0.0, timeout=120.0):
        if kind == "reasoning":
            reasoning.append(delta)
        else:
            content.append(delta)
    r = "".join(reasoning)
    c = "".join(content)
    print(f"reasoning {len(r)} 字（<3000 正常；>5000 疑似循环）")
    print(f"reasoning 预览（前 220 字）: {r[:220]!r}")
    print(f"\ncontent {len(c)} 字")
    data = _extract_json_loose(c)
    if isinstance(data, list):
        names = [p.get("name") for p in data if isinstance(p, dict)]
        print(f"提取到的项目: {names}")
        has_indep = any("交易" in (n or "") for n in names)
        has_intern = any(("推荐" in (n or "")) or ("内容" in (n or "")) for n in names)
        print(f"  独立项目（交易台）: {'✅' if has_indep else '❌'}")
        print(f"  实习项目（内容推荐）: {'✅' if has_intern else '❌'}")
        if len(r) < 5000:
            print(f"\n✅ reasoning 长度合理（{len(r)} 字），无明显循环")
        else:
            print(f"\n⚠️ reasoning 偏长（{len(r)} 字），可能仍有循环")
    else:
        print(f"content 解析失败: {c[:200]!r}")


asyncio.run(main())
