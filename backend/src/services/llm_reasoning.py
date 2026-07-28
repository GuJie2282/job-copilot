"""
LLM reasoning stream 服务（绕过 LangChain，用 openai client 直调智谱 GLM-4.5）。

为什么不用 LangChain：ChatOpenAI.stream() 默认只读 delta.content，把智谱的
delta.reasoning_content **丢了**（spike 验证：LangChain 下 glm-4.5 前 30 chunk
content 全空 = 思考阶段，但 reasoning 没进 additional_kwargs）。必须用 openai
client 直调，显式读 delta.reasoning_content + delta.content。

供 add-reasoning-display 三模块（简历优化 / 简历解析 / JD 匹配）复用：
    async for kind, delta in stream_chat_with_reasoning(prompt):
        # kind == "reasoning"（思考过程）或 "content"（回答）
        ...

作者：求职 Copilot 项目
日期：2026-07-24
"""
import os
import logging
from typing import AsyncGenerator, Tuple

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# 复用 .env 的 LLM 配置（与 LangChain get_llm 同源：LLM_API_KEY / LLM_BASE_URL）
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """单例 AsyncOpenAI client（复用 .env 配置）。"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        )
    return _client


async def stream_chat_with_reasoning(
    prompt: str,
    model: str = "glm-4.5",
    temperature: float = 0.0,
    timeout: float = 120.0,
    system: str | None = None,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    用 glm-4.5 stream，增量 yield (kind, delta)：
      kind="reasoning" —— AI 思考过程（delta.reasoning_content）
      kind="content"   —— 最终回答（delta.content）

    reasoning 与 content 分离 yield，调用方按需转发（如 SSE reasoning / token 事件）。

    降级：reasoning_content 不存在时只 yield content（业务不阻断）。
    整体失败抛异常（调用方 catch 决定降级/重试）。

    Args:
        prompt:      用户提示词
        model:       默认 glm-4.5（当前唯一支持 reasoning 的档）
        temperature: 温度
        timeout:     请求超时（秒）
        system:      可选 system message
    Yields:
        (kind, delta)：kind ∈ {"reasoning", "content"}
    """
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
        timeout=timeout,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        # reasoning_content（智谱扩展字段，openai SDK delta 上用 getattr 取）
        rc = getattr(delta, "reasoning_content", None)
        if rc:
            yield ("reasoning", rc)
        if delta.content:
            yield ("content", delta.content)
