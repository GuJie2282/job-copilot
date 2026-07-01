"""
配置：初始化 LLM。

默认用 DeepSeek（OpenAI 兼容接口，国内可直连，性价比高）。
想换模型（OpenAI / 通义 / 智谱），只改 .env，代码不用动。
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载 .env 里的环境变量
load_dotenv()


def get_llm() -> ChatOpenAI:
    """创建并返回一个 LLM 实例。"""
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        raise ValueError(
            "未配置 LLM_API_KEY！请复制 .env.example 为 .env，填入你的 API Key。\n"
            "DeepSeek 申请地址：https://platform.deepseek.com/"
        )

    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        api_key=api_key,
        temperature=0.7,   # 求职教练需要一点自然语气和创造力
    )
