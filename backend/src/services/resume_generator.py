"""
简历生成服务（resume_generator）

职责：基于「用户画像 + 目标岗位差距（Gap）」，从零生成一份针对该岗位的定制简历（Markdown）。
只生成、不优化旧简历——输入仅画像 + Gap + 岗位（对应 design 决策 2）。

核心：
- gap_rewrite_strategy：Gap 类型 → 改写策略指令（兑现 design 决策 4 的接口契约）
- generate_resume：调用 LLM 生成 Markdown 简历，沿用 jd_parser 的鲁棒范式（get_llm + 重试）

降级（对应 design 边界条件）：
- 无 Gap → 通用生成（不针对特定 Gap 定向强化）
- 画像信息不足 → prompt 引导 LLM 在缺素材处标注「待补充」，不虚构

作者：求职 Copilot 项目
日期：2026-07-22
"""

import re
import json
import time
import logging
from typing import List, Dict, Any, Optional, Generator, AsyncGenerator, Tuple

from src.graph.config import get_llm
from src.graph.prompts import get_resume_generation_prompt, get_resume_refine_prompt
from src.services.llm_retry import is_retryable

logger = logging.getLogger(__name__)


# ============================================================================
# Gap → 改写策略映射（对应 design 决策 4：兑现 JD 匹配的接口契约）
# ============================================================================

# 四类 Gap 的改写策略（每类一条可执行指令，拼进生成 prompt）
_GAP_STRATEGY = {
    "hard_skill": (
        "强化相关项目经历（把用到相邻/可迁移技能的项目前置并展开）+ "
        "转移焦点（放大候选人具备的相关能力，弱化缺口）"
    ),
    "soft_skill": (
        "STAR 改写（补情境/任务/行动/结果）+ 数据化"
        "（用带数据的具体事例佐证该软技能，消灭'沟通能力强'式空泛表述）"
    ),
    "implicit": (
        "挖掘可类比经历对冲（如无大厂背景→突出高复杂度/高影响力项目；"
        "无相关行业→突出可迁移方法论与成果）"
    ),
    "redline": (
        "策略性呈现 + 预警（绝不造假，但在简历中规避一票否决项的负面呈现，"
        "把读者注意力引向优势项）"
    ),
}


def gap_rewrite_strategy(gap_type: str) -> str:
    """
    按 Gap 类型返回对应的简历改写策略指令（对应 design 决策 4）。

    Args:
        gap_type: hard_skill / soft_skill / implicit / redline
    Returns:
        改写策略指令文本
    """
    return _GAP_STRATEGY.get(gap_type, "结合候选人经历针对性强化该方面")


def _format_gaps_with_strategy(gaps: List[Dict[str, Any]]) -> str:
    """
    把 Gap 清单格式化为「差距 + 改写策略」文本，喂给生成 prompt。
    每个 gap 一行：[类型] 要求（现状）→ 策略
    """
    lines = []
    for g in gaps:
        gtype = g.get("type", "")
        req = g.get("requirement", "")
        cur = g.get("current_state", "") or "画像中未体现"
        strategy = gap_rewrite_strategy(gtype)
        lines.append(f"- [{gtype}] {req}（现状：{cur}）→ 策略：{strategy}")
    return "\n".join(lines)


def _clean_markdown(text: str) -> str:
    """
    清理 LLM 输出：去掉首尾的 ```markdown / ``` 代码块包裹与多余空白。
    生成的是纯 Markdown 简历，不应被代码块包裹。
    """
    text = (text or "").strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)  # 去开头 ```markdown
    text = re.sub(r"\n```\s*$", "", text)                  # 去结尾 ```
    return text.strip()


def generate_resume(
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
    jd_text: Optional[str] = None,
    max_retries: int = 2,
) -> str:
    """
    基于画像 + Gap + 岗位，生成 Markdown 简历。

    Args:
        profile:         用户画像 dict（含基本信息/教育/工作/项目/技能等）
        gaps:            差距清单（每项含 type/requirement/current_state/...）；空则通用生成
        target_position: 目标岗位
        max_retries:     LLM 失败重试次数（默认 2，即最多 3 次尝试）
    Returns:
        Markdown 简历全文（纯文本，已去代码块包裹）
    Raises:
        重试耗尽后抛出最后异常
    """
    if not profile:
        raise ValueError("画像为空，无法生成简历")
    if not target_position:
        raise ValueError("目标岗位为空")

    # 画像序列化为文本喂给 LLM（保留结构，LLM 自行提取关键信息组织简历）
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""

    # 生成是创作任务，用 0.3 适度创造性（结构稳定 + 表述不死板）
    llm = get_llm(temperature=0.3)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            prompt = get_resume_generation_prompt(profile_text, gaps_text, target_position, has_gaps, jd_text)
            if attempt > 0:
                prompt = (
                    "上次生成失败。请直接输出 Markdown 简历全文，"
                    "不要代码块包裹，不要任何解释。\n\n" + prompt
                )
            response = llm.invoke(prompt)
            md = _clean_markdown(response.content)
            if not md or len(md) < 50:
                raise ValueError(f"生成内容过短（{len(md)} 字符），可能生成失败")
            logger.info(
                "resume_generated",
                extra={"position": target_position, "has_gaps": has_gaps, "length": len(md)},
            )
            return md
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)  # 1s → 2s → 4s
                logger.warning(
                    f"简历生成失败（第 {attempt + 1}/{max_retries + 1} 次），"
                    f"{delay:.1f}s 后重试：{type(e).__name__}: {e}"
                )
                time.sleep(delay)

    logger.error(f"简历生成重试 {max_retries} 次仍失败，放弃。最后错误：{last_error}")
    raise last_error


# ============================================================================
# 简历精修（路径 B：按用户反馈改写现有草稿）
# ============================================================================

def refine_resume(
    current_md: str,
    feedback: str,
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
    max_retries: int = 2,
) -> str:
    """
    按用户反馈精修现有简历草稿（路径 B 的改写核心）。

    与 generate_resume 的区别：以现有草稿为底，只改反馈涉及的部分，不重写整篇。

    Args:
        current_md:      当前简历草稿（Markdown）
        feedback:        用户反馈（要改什么）
        profile:         用户画像 dict
        gaps:            差距清单（参考）
        target_position: 目标岗位
        max_retries:     LLM 失败重试次数
    Returns:
        精修后的 Markdown 简历全文
    Raises:
        重试耗尽后抛出最后异常
    """
    if not current_md:
        raise ValueError("当前简历草稿为空，无法精修")
    if not feedback or not feedback.strip():
        raise ValueError("用户反馈为空，无法精修")

    profile_text = json.dumps(profile or {}, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""

    llm = get_llm(temperature=0.3)  # 精修适度创造性
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            prompt = get_resume_refine_prompt(
                current_md, feedback, profile_text, gaps_text, target_position, has_gaps
            )
            if attempt > 0:
                prompt = "上次精修失败。请直接输出修改后的完整 Markdown 简历，不要代码块包裹。\n\n" + prompt
            response = llm.invoke(prompt)
            md = _clean_markdown(response.content)
            if not md or len(md) < 50:
                raise ValueError(f"精修内容过短（{len(md)} 字符），可能失败")
            logger.info(
                "resume_refined",
                extra={"position": target_position, "feedback_len": len(feedback), "length": len(md)},
            )
            return md
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)
                logger.warning(
                    f"简历精修失败（第 {attempt + 1}/{max_retries + 1} 次），"
                    f"{delay:.1f}s 后重试：{type(e).__name__}: {e}"
                )
                time.sleep(delay)

    logger.error(f"简历精修重试 {max_retries} 次仍失败，放弃。最后错误：{last_error}")
    raise last_error


# ============================================================================
# 增量生成（流式：token 级输出，对应 change add-streaming-pipeline 决策 7/10）
# 与上面的同步版本并存：自由文本任务（简历生成/精修）用 stream 版逐字 yield，
# 供流式管线以 token 事件下发打字机效果。
# ============================================================================

def generate_resume_stream(
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
    jd_text: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    增量生成简历（路径 A），逐 token yield 文本片段。

    与 generate_resume 的区别：
    - 用 llm.stream(prompt) 增量产出，每来一个 token 就 yield，供流式管线逐字下发
    - 调用方拼接完整文本后，用 _clean_markdown 清理代码块包裹、做长度校验
    - 不内置重试：流式输出无法从中断处续传，失败直接抛（由调用方决定是否整段重来）

    Args:
        profile / gaps / target_position / jd_text：同 generate_resume
    Yields:
        token 文本片段（delta）
    """
    if not profile:
        raise ValueError("画像为空，无法生成简历")
    if not target_position:
        raise ValueError("目标岗位为空")

    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""
    prompt = get_resume_generation_prompt(profile_text, gaps_text, target_position, has_gaps, jd_text)

    # 生成是创作任务，温度同同步版本（0.3）；stream 逐 chunk 产出 token
    llm = get_llm(temperature=0.3)
    for chunk in llm.stream(prompt):
        delta = chunk.content or ""
        if delta:
            yield delta


async def generate_resume_reasoning_stream(
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
    jd_text: Optional[str] = None,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    增量生成简历（glm-4.5 reasoning），yield (kind, delta)：
      kind="reasoning" —— AI 思考过程（供前端思考区展示）
      kind="content"   —— 简历正文（Markdown）

    用 openai client 直调 glm-4.5 拿 reasoning_content（LangChain 默认丢）。
    与 generate_resume_stream（LangChain, glm-4-flash, 仅 content）并存。
    """
    if not profile:
        raise ValueError("画像为空，无法生成简历")
    if not target_position:
        raise ValueError("目标岗位为空")

    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""
    prompt = get_resume_generation_prompt(profile_text, gaps_text, target_position, has_gaps, jd_text)

    from src.services.llm_reasoning import stream_chat_with_reasoning
    async for kind, delta in stream_chat_with_reasoning(prompt, temperature=0.3):
        yield kind, delta


def refine_resume_stream(
    current_md: str,
    feedback: str,
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
) -> Generator[str, None, None]:
    """
    增量精修简历（路径 B），逐 token yield。

    约定同 generate_resume_stream（stream、不重试、调用方拼接后 clean）。Args 同 refine_resume。

    Yields:
        token 文本片段（delta）
    """
    if not current_md:
        raise ValueError("当前简历草稿为空，无法精修")
    if not feedback or not feedback.strip():
        raise ValueError("用户反馈为空，无法精修")

    profile_text = json.dumps(profile or {}, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""
    prompt = get_resume_refine_prompt(current_md, feedback, profile_text, gaps_text, target_position, has_gaps)

    llm = get_llm(temperature=0.3)
    for chunk in llm.stream(prompt):
        delta = chunk.content or ""
        if delta:
            yield delta


async def refine_resume_reasoning_stream(
    current_md: str,
    feedback: str,
    profile: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    target_position: str,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    增量精修简历（glm-4.5 reasoning），yield (kind, delta)：
      kind="reasoning" —— AI 思考过程（供前端思考区展示）
      kind="content"   —— 自然语言说明 + 改写后简历（prompt 约定用 <<<REPLY>>>/<<<RESUME>>> 分隔）

    用 openai client 直调 glm-4.5 拿 reasoning_content（LangChain 默认丢）。
    与 refine_resume_stream（LangChain, glm-4-flash, 仅 content）并存。
    """
    if not current_md:
        raise ValueError("当前简历草稿为空，无法精修")
    if not feedback or not feedback.strip():
        raise ValueError("用户反馈为空，无法精修")

    profile_text = json.dumps(profile or {}, ensure_ascii=False, indent=2)
    has_gaps = bool(gaps)
    gaps_text = _format_gaps_with_strategy(gaps) if has_gaps else ""
    prompt = get_resume_refine_prompt(current_md, feedback, profile_text, gaps_text, target_position, has_gaps)

    from src.services.llm_reasoning import stream_chat_with_reasoning
    async for kind, delta in stream_chat_with_reasoning(prompt, temperature=0.3):
        yield kind, delta


def split_reply_resume(content: str) -> Tuple[str, Optional[str]]:
    """
    切分精修 LLM 的结构化输出（prompt 约定：`<<<REPLY>>>说明<<<RESUME>>>简历`）。

    精修流式端点把 LLM 的 content 攒齐后调用本函数，切出「自然语言说明」与「改写后简历」，
    分别下发（说明走 token 事件、简历随 done 下发，使前端思考/说明/简历三层分离呈现）。

    Returns:
        (reply, resume_md)
        - 正常：reply=自然语言说明，resume_md=改写后的完整 Markdown 简历（已去代码块包裹）
        - 降级（无 <<<RESUME>>>）：reply=说明（或整段 content），resume_md=None
          → 调用方应沿用上一版简历并提示「本次未生成新简历」
    """
    reply_mark = "<<<REPLY>>>"
    resume_mark = "<<<RESUME>>>"

    r_idx = content.find(reply_mark)
    if r_idx < 0:
        # 无 REPLY 标记：LLM 未按约定输出，整段当说明，无新简历
        return content.strip(), None
    after_reply = content[r_idx + len(reply_mark):]

    s_idx = after_reply.find(resume_mark)
    if s_idx < 0:
        # 有 REPLY 无 RESUME：说明有，简历缺
        return after_reply.strip(), None

    reply = after_reply[:s_idx].strip()
    resume_md = _clean_markdown(after_reply[s_idx + len(resume_mark):].strip())
    return reply, resume_md
