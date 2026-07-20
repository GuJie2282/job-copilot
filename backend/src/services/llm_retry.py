"""
LLM 调用重试机制

处理 LLM API 的偶发失败（超时、限流、5xx 等），提升解析成功率。
适用于智谱 GLM、DeepSeek、OpenAI 等 OpenAI 兼容接口。

设计要点：
1. 区分"可重试错误"（临时性，如超时/限流）和"不可重试错误"（确定性，如认证失败）
2. 指数退避（1s → 2s → 4s），避免冲击服务商
3. 重试次数有上限（默认 2 次），避免请求长时间挂起
"""
import time
import logging

logger = logging.getLogger(__name__)

# 默认重试配置
DEFAULT_MAX_RETRIES = 2  # 最多重试 2 次（首次 + 2 次重试 = 共 3 次尝试）
DEFAULT_BASE_DELAY = 1.0  # 首次重试延迟 1 秒，之后指数退避（1s → 2s → 4s）


def is_retryable(exc: Exception) -> bool:
    """
    判断异常是否值得重试。

    【可重试】（临时性错误，重试可能成功）：
      - 超时（APITimeoutError）
      - 限流（HTTP 429）
      - 服务端错误（HTTP 5xx）
      - 网络连接错误
      - JSON / 数据解析错误（LLM 偶发返回非合法 JSON）

    【不可重试】（确定性错误，重试也没用）：
      - 认证失败（401 / 403）：API Key 错误
      - 请求格式错误（400）：参数问题
      - 模型不存在（404）：模型名拼错

    【未知异常】：保守地返回 True（LLM 服务的临时问题较常见，重试成本低）。
    """
    # openai 错误对象通常带 status_code 属性
    status = getattr(exc, 'status_code', None)
    if status is not None:
        # 5xx 服务端错误 + 429 限流 → 重试
        if status >= 500 or status == 429:
            return True
        # 4xx 客户端错误（除 429）→ 不重试（认证、参数等，重试无用）
        if 400 <= status < 500:
            return False

    # 无 status_code 的异常：按类型名关键词判断
    exc_name = type(exc).__name__.lower()
    if any(kw in exc_name for kw in [
        'timeout', 'connection', 'ratelimit', 'retry',
        'value', 'json', 'validation'  # JSON 解析 / Pydantic 校验失败 → 重试（换次 LLM 可能就对了）
    ]):
        return True

    # 未知异常：保守重试
    return True


def invoke_llm_with_retry(
    llm,
    prompt,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY
):
    """
    带重试的 LLM 单次调用（仅处理 API 层异常）。

    适用场景：profile_extraction_node、extract 端点 等"只调用 invoke、不做外部 JSON 解析"的地方。
    （resume.py 的 parse-file / parse-text 有 JSON 解析步骤，用自己的 _extract_profile_with_retry。）

    Args:
        llm: LangChain Chat 模型实例
        prompt: 提示词（字符串或消息列表）
        max_retries: 最大重试次数（默认 2，即最多 3 次尝试）
        base_delay: 首次重试延迟（秒），之后指数退避

    Returns:
        llm.invoke 的返回值

    Raises:
        最后一次异常（所有重试失败后）
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            last_error = e
            # 不可重试错误（认证、参数等）→ 立即抛出，不浪费时间
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"LLM 调用失败（第 {attempt + 1}/{max_retries + 1} 次）："
                    f"{type(e).__name__}: {e}。{delay:.1f}s 后重试..."
                )
                time.sleep(delay)

    logger.error(f"LLM 调用 {max_retries + 1} 次均失败，放弃。最后错误：{last_error}")
    raise last_error
