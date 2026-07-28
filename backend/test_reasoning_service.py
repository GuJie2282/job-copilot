"""验证 stream_chat_with_reasoning（公共 reasoning 层）能拿 reasoning + content。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.services.llm_reasoning import stream_chat_with_reasoning


async def main():
    print("stream_chat_with_reasoning（glm-4.5）...")
    reasoning = []
    content = []
    async for kind, delta in stream_chat_with_reasoning(
        "2+3 等于几？请先思考再回答。", timeout=60.0
    ):
        if kind == "reasoning":
            reasoning.append(delta)
        else:
            content.append(delta)
    r = "".join(reasoning)
    c = "".join(content)
    print(f"\nreasoning {len(r)} 字: {r[:90]!r}")
    print(f"content   {len(c)} 字: {c[:90]!r}")
    assert r, "❌ 无 reasoning（reasoning 没拿到）"
    assert c, "❌ 无 content"
    print("\n✅ stream_chat_with_reasoning OK：reasoning + content 都拿到，分离 yield")


asyncio.run(main())
