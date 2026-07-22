"""
JD 结构化解析服务（jd_parser）

职责：把职位描述（JD）文本解析为结构化的「要求画像」(job_profile)，
按四分类输出（硬技能 / 软技能 / 隐性偏好 / 红线项），每条要求保留原文依据。

采用与简历解析一致的鲁棒范式：JSON Prompt + 正则提取 + Pydantic 校验 + 重试，
兼容智谱 GLM / DeepSeek 等偶发返回非合法 JSON 的情况。

作者：求职 Copilot 项目
日期：2026-07-14
"""

import json
import re
import time
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from src.graph.config import get_llm
from src.graph.prompts import get_jd_parsing_prompt
from src.services.llm_retry import is_retryable

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型：要求画像（job_profile）
# ============================================================================

class JdRequirement(BaseModel):
    """JD 中的单条要求"""
    requirement: str = Field(..., description="要求内容")
    must_have: Optional[bool] = Field(True, description="True=必须项，False=加分项")
    evidence: Optional[str] = Field(None, description="JD 原文出处片段，便于追溯")
    confidence: Optional[float] = Field(None, description="解析置信度 0.0-1.0")


class JobProfile(BaseModel):
    """
    JD 解析出的要求画像（四分类）。

    与 user_profile 对称：user_profile 描述「用户有什么」，job_profile 描述「岗位要什么」，
    匹配 = 两者逐项对齐。
    """
    position_title: Optional[str] = None
    summary: Optional[str] = None
    hard_skills: List[JdRequirement] = []
    soft_skills: List[JdRequirement] = []
    implicit_preferences: List[JdRequirement] = []
    red_lines: List[JdRequirement] = []


# ============================================================================
# 解析（带重试）
# ============================================================================

def _extract_json(text: str) -> dict:
    """
    从 LLM 输出中提取 JSON。

    处理两种情况：
    1. 被 ```json ... ``` 代码块包裹（最常见）
    2. 裸 JSON（LLM 偶尔不包裹）
    """
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    raw = match.group(1) if match else text.strip()
    return json.loads(raw)


def parse_jd(jd_text: str, max_retries: int = 2) -> dict:
    """
    解析 JD 文本为结构化要求画像（job_profile dict）。

    Args:
        jd_text:    JD 原文
        max_retries: 最大重试次数（默认 2，即最多 3 次尝试）
    Returns:
        job_profile dict（含 position_title / summary / 四分类列表），
        每个分类是 requirement dict 的列表。
    Raises:
        最后一次异常（重试耗尽后抛出）
    """
    if not jd_text or not jd_text.strip():
        raise ValueError("JD 文本为空，无法解析")

    llm = get_llm(temperature=0.0, tier="strong")  # JD 解析：主力档（质量敏感）
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            prompt = get_jd_parsing_prompt(jd_text)
            # 重试时强化 JSON 格式要求
            if attempt > 0:
                prompt = (
                    "上次解析失败。请严格输出合法 JSON，必须包裹在 ```json 代码块中，"
                    "不要输出任何解释或多余文字。\n\n" + prompt
                )

            response = llm.invoke(prompt)
            data = _extract_json(response.content)

            # Pydantic 校验，保证结构合法
            profile = JobProfile(**data)
            logger.info(
                "jd_parsed",
                extra={
                    "position": profile.position_title,
                    "hard": len(profile.hard_skills),
                    "soft": len(profile.soft_skills),
                    "implicit": len(profile.implicit_preferences),
                    "redline": len(profile.red_lines),
                },
            )
            return profile.model_dump()

        except Exception as e:
            last_error = e
            # 不可重试错误（认证、参数等）→ 立即抛出
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)  # 1s → 2s → 4s
                logger.warning(
                    f"JD 解析失败（第 {attempt + 1}/{max_retries + 1} 次），"
                    f"{delay:.1f}s 后重试：{type(e).__name__}: {e}"
                )
                time.sleep(delay)

    logger.error(f"JD 解析重试 {max_retries} 次仍失败，放弃。最后错误：{last_error}")
    raise last_error
