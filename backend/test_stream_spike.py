"""
验证 get_llm(...).stream() 在智谱 GLM 上可用（对应 change add-streaming-pipeline 任务 1.3.2）。

手动跑（需 .env 配好 LLM_API_KEY）：
    cd backend && .venv/Scripts/python.exe test_stream_spike.py

确认点：
- llm.stream(prompt) 返回可迭代的 token 流
- 每个 chunk 含 .content 文本片段
- 拼接后是完整的连贯文本
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()  # 读 .env 的 LLM_API_KEY

from src.graph.config import get_llm

llm = get_llm(temperature=0.0)
print("stream 开始，逐 token 输出（前 12 个）：")
tokens = []
try:
    for chunk in llm.stream("用一句话介绍杭州，30 字以内。"):
        delta = chunk.content or ""
        if delta:
            tokens.append(delta)
            if len(tokens) <= 12:
                print(f"  token[{len(tokens)}]: {delta!r}")
except Exception as e:
    print(f"❌ stream 失败：{type(e).__name__}: {e}")
    sys.exit(1)

full = "".join(tokens)
print(f"\n共收到 {len(tokens)} 个非空 token")
print(f"完整文本：{full}")
assert len(tokens) > 0, "未收到任何 token"
print("✅ llm.stream() 在智谱 GLM 上可用，token 迭代器正常")
