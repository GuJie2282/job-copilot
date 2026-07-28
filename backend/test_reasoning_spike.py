"""Spike: GLM stream 是否暴露 reasoning_content（思考过程）。

智谱 GLM-4.5 是 reasoning 模型，stream 时 chunk 理论上含 reasoning_content（思考）
与 content（回答）分离。LangChain ChatOpenAI 适配智谱时，reasoning 可能在：
  - chunk.reasoning_content（若 LangChain 适配）
  - chunk.additional_kwargs['reasoning_content']
  - chunk.response_metadata
探测前几个 chunk 的结构，定位 reasoning 字段。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.graph.config import get_llm


def probe(model_name: str):
    print(f"\n===== {model_name} =====")
    try:
        llm = get_llm(model=model_name, temperature=0.0, timeout=90.0)
    except Exception as e:
        print(f"  初始化失败: {e}")
        return
    has_reasoning = False
    has_content = False
    print("  stream 中（前 4 个 chunk 的结构）...")
    for i, chunk in enumerate(llm.stream("如何评估一个人的产品能力？请先思考再回答，3 句话以内。")):
        content = getattr(chunk, "content", None) or ""
        rc_attr = getattr(chunk, "reasoning_content", None)
        aw = getattr(chunk, "additional_kwargs", {}) or {}
        rm = getattr(chunk, "response_metadata", {}) or {}
        aw_rc = aw.get("reasoning_content") if isinstance(aw, dict) else None
        if content:
            has_content = True
        if rc_attr or aw_rc:
            has_reasoning = True
        if i < 4:
            keys = list(chunk.model_dump().keys()) if hasattr(chunk, "model_dump") else "?"
            print(f"  chunk[{i}] keys={keys}")
            print(f"    content={content!r}")
            if rc_attr:
                print(f"    reasoning_content(attr)={str(rc_attr)[:60]!r}")
            if aw:
                print(f"    additional_kwargs={str(aw)[:80]!r}")
            if rm:
                print(f"    response_metadata={str(rm)[:80]!r}")
        if i > 30:
            break
    print(f"  → has_content={has_content}, has_reasoning={has_reasoning}")
    print(f"  {'✅ ' + model_name + ' 支持 reasoning stream' if has_reasoning else '⚠️ ' + model_name + ' stream 无 reasoning_content'}")


probe("glm-4.5")
probe("glm-4-flash")
