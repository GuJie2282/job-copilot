"""Spike: openai client 直调智谱 GLM-4.5 stream，读 delta.reasoning_content。

LangChain ChatOpenAI 默认只读 delta.content，智谱的 reasoning_content 被丢。
绕过 LangChain 用 openai client 直调，确认 reasoning 能否拿到。
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
)

print("glm-4.5 stream via openai client，读 reasoning_content...")
has_reasoning = False
has_content = False
rc_total = ""
c_total = ""
try:
    stream = client.chat.completions.create(
        model="glm-4.5",
        messages=[{"role": "user", "content": "2+3 等于几？请先思考再回答。"}],
        stream=True,
    )
    for i, chunk in enumerate(stream):
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        rc = getattr(delta, "reasoning_content", None)
        c = delta.content
        if rc:
            has_reasoning = True
            rc_total += rc
            if len(rc_total) < 80:
                print(f"  [{i}] reasoning: {rc!r}")
        if c:
            has_content = True
            c_total += c
        if i > 200:
            break
except Exception as e:
    print(f"❌ 调用失败: {type(e).__name__}: {e}")
    raise SystemExit(1)

print(f"\nhas_reasoning={has_reasoning}, has_content={has_content}")
print(f"reasoning 累计 {len(rc_total)} 字, 预览: {rc_total[:100]!r}")
print(f"content 累计 {len(c_total)} 字, 预览: {c_total[:100]!r}")
print("\n✅ openai client 能拿到 reasoning_content → 可接思考过程显示"
      if has_reasoning else
      "❌ openai client 也拿不到 reasoning_content（智谱未暴露 / 需 thinking 参数）")
