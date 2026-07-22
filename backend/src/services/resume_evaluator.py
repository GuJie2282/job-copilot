"""
简历 6 维评估服务（resume_evaluator）

职责：对生成的简历做 LLM 内容评估（6 维度），输出结构化评估报告，
作为自动迭代（路径 A）与人工精修（路径 B）的依据。
**只评估、给建议，不直接改写**（改写由生成节点根据反馈做）。

六维（对应 design 决策 3 + amlei-resume skill 的 resume-evaluator.md）：
  基础规范 15% / JD 匹配 25% / 成果量化 25% / 结构清晰 10% / 差异化 15% / 语言表达 10%

沿用 jd_parser 鲁棒范式：JSON Prompt + _extract_json + Pydantic 校验 + 重试，
兼容智谱 GLM / DeepSeek 偶发返回非合法 JSON 的情况。

作者：求职 Copilot 项目
日期：2026-07-22
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from src.graph.config import get_llm
from src.graph.prompts import get_resume_evaluation_prompt
from src.services.llm_retry import is_retryable
from src.services.jd_parser import _extract_json  # 复用 JD 解析的 JSON 提取

logger = logging.getLogger(__name__)


# ============================================================================
# 评估报告 Pydantic 模型（对应 spec 数据结构 + design 决策 3）
# ============================================================================

class EvalCheckItem(BaseModel):
    """单个检查项"""
    check: str = Field(..., description="检查项名称")
    result: str = Field(..., description="pass / fail / partial")
    note: Optional[str] = Field(None, description="不通过时的具体建议；通过则 null")


class EvalDimension(BaseModel):
    """一个维度的评估结果"""
    score: float = Field(..., description="维度得分 0-100")
    weight: float = Field(..., description="权重")
    passed: bool = Field(..., description="该维度是否通过（无 fail 项）")
    items: List[EvalCheckItem] = Field(default_factory=list, description="该维度的检查项明细")


class FeedbackPriority(BaseModel):
    """改进优先级条目"""
    priority: str = Field(..., description="high / medium / low")
    suggestion: str = Field(..., description="可执行的改进建议")


class ResumeEvalReport(BaseModel):
    """完整 6 维评估报告"""
    overall_score: float = Field(..., description="加权总分 0-100")
    passed: bool = Field(..., description="整体是否通过（所有维度 passed）")
    dimensions: Dict[str, EvalDimension] = Field(
        ...,
        description="六维结果，key: basic_norm/jd_match/quantification/structure/differentiation/language",
    )
    feedback_priorities: List[FeedbackPriority] = Field(
        default_factory=list, description="按优先级排序的改进建议"
    )


# 六个维度的 key（用于校验 dimensions 完整性）
DIMENSION_KEYS = ["basic_norm", "jd_match", "quantification", "structure", "differentiation", "language"]


# ============================================================================
# 评估（带重试）
# ============================================================================

def evaluate_resume(
    resume_md: str,
    target_position: str,
    gaps: Optional[List[Dict[str, Any]]] = None,
    profile: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    对简历做 6 维 LLM 评估，返回评估报告 dict。

    Args:
        resume_md:       简历 Markdown 全文
        target_position: 目标岗位
        gaps:            差距清单（评估 JD 匹配维度时参考）
        profile:         用户画像（核对量化数字是否可追溯，对应 spec"量化可信度把关"）
        max_retries:     LLM 失败重试次数（默认 2，即最多 3 次）
    Returns:
        评估报告 dict（结构与 ResumeEvalReport 一致，可直接存 eval_report_json）
    Raises:
        重试耗尽后抛出最后异常
    """
    if not resume_md or len(resume_md) < 50:
        raise ValueError("简历内容过短，无法评估")

    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)[:2000] if profile else "（未提供画像）"
    gaps_text = json.dumps(
        [{"type": g.get("type"), "requirement": g.get("requirement")} for g in (gaps or [])],
        ensure_ascii=False,
    ) if gaps else "[]"

    # 评估要确定性（同一简历多次评估应一致），用 0.0 温度
    llm = get_llm(temperature=0.0)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            prompt = get_resume_evaluation_prompt(resume_md, target_position, gaps_text, profile_text)
            if attempt > 0:
                prompt = (
                    "上次评估失败。请严格输出合法 JSON，必须包裹在 ```json 代码块中，"
                    "不要输出任何解释。\n\n" + prompt
                )
            response = llm.invoke(prompt)
            data = _extract_json(response.content)

            # Pydantic 校验，保证结构合法
            report = ResumeEvalReport(**data)

            # 校验六维齐全（缺维度 → 视为本次输出不合规，进入重试）
            missing = [k for k in DIMENSION_KEYS if k not in report.dimensions]
            if missing:
                raise ValueError(f"评估缺失维度：{missing}")

            logger.info(
                "resume_evaluated",
                extra={"score": report.overall_score, "passed": report.passed},
            )
            return report.model_dump()

        except Exception as e:
            last_error = e
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)  # 1s → 2s → 4s
                logger.warning(
                    f"简历评估失败（第 {attempt + 1}/{max_retries + 1} 次），"
                    f"{delay:.1f}s 后重试：{type(e).__name__}: {e}"
                )
                time.sleep(delay)

    logger.error(f"简历评估重试 {max_retries} 次仍失败，放弃。最后错误：{last_error}")
    raise last_error
