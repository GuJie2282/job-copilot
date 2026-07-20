"""
差距分析服务（gap_analyzer）

基于匹配结果生成结构化的差距清单（Gap），按四分类输出并附应对建议，
作为简历优化模块的输入契约（闭环接口，对应 design.md 决策 4）。

Gap 四分类：硬技能差距 / 软技能表述弱 / 隐性偏好缺位 / 红线预警
- 严重度：红线(critical) > 硬技能(high) > 隐性(medium) > 软技能(low)
- 建议由 LLM 生成（更贴合画像），LLM 失败时降级为模板建议（不阻断）
- 低置信度项标注 need_confirm（置信度传导）

作者：求职 Copilot 项目
日期：2026-07-14
"""

import time
import logging
from typing import Dict, List, Any

from src.graph.config import get_llm
from src.graph.prompts import get_gap_suggestion_prompt
from src.services.jd_parser import _extract_json
from src.services.llm_retry import is_retryable

logger = logging.getLogger(__name__)

# 严重度排序（前者更严重）
SEVERITY_ORDER = ["critical", "high", "medium", "low"]

# 模板建议（LLM 失败时降级用）
_TEMPLATE_SUGGESTION = {
    "hard_skill": "用 STAR 法则补充相关项目经历，强调量化成果；若完全无该技能经验，可放大相邻可迁移技能的价值。",
    "soft_skill": "在简历中用带数据的具体事例佐证该软技能，避免「沟通能力强」等空泛表述。",
    "implicit": "挖掘可类比的高质量经历来对冲该偏好（如无大厂背景，则突出高复杂度/高影响力的项目）。",
    "redline": "此项为硬性门槛，建议提前确认是否一票否决；简历中策略性呈现，必要时通过内推/猎头弥补。",
}


def _severity_for(gap_type: str) -> str:
    """按 Gap 类型赋严重度"""
    if gap_type == "redline":
        return "critical"
    if gap_type == "hard_skill":
        return "high"
    if gap_type == "implicit":
        return "medium"
    return "low"  # soft_skill


def _template_suggestion(gap_type: str) -> str:
    return _TEMPLATE_SUGGESTION.get(gap_type, "建议结合自身经历针对性补充。")


def _generate_suggestions(gaps: List[Dict], user_profile: Dict, max_retries: int = 2) -> List[str]:
    """
    LLM 批量生成每个 Gap 的应对建议。任何失败（含 API Key 缺失）都降级为模板建议。
    """
    # get_llm 失败（如未配置 API Key）→ 直接降级
    try:
        llm = get_llm(temperature=0.7)  # 建议适度创造性
    except Exception as e:
        logger.warning(f"get_llm 失败，Gap 建议降级模板：{e}")
        return [_template_suggestion(g["type"]) for g in gaps]

    profile_text = str({k: v for k, v in user_profile.items() if v})[:1500]
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            prompt = get_gap_suggestion_prompt(gaps, profile_text)
            if attempt > 0:
                prompt = "上次失败，请严格输出 ```json 包裹的合法 JSON。\n\n" + prompt
            resp = llm.invoke(prompt)
            data = _extract_json(resp.content)
            if isinstance(data, dict):
                data = data.get("suggestions") or data.get("items") or []
            # 期望 data: [{requirement, suggestion}, ...]
            sug_map = {}
            for item in data:
                if isinstance(item, dict):
                    key = item.get("requirement") or item.get("gap")
                    if key:
                        sug_map[key] = item.get("suggestion") or item.get("advice")
            return [sug_map.get(g["requirement"]) or _template_suggestion(g["type"]) for g in gaps]
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                break
            if attempt < max_retries:
                time.sleep(1.0 * (2 ** attempt))

    logger.warning(f"Gap 建议 LLM 生成失败，降级模板：{last_error}")
    return [_template_suggestion(g["type"]) for g in gaps]


def analyze_gaps(
    job_profile: Dict[str, Any],
    user_profile: Dict[str, Any],
    match_result: Dict[str, Any],
    max_retries: int = 2,
) -> List[Dict[str, Any]]:
    """
    基于匹配结果生成 Gap 清单。

    Args:
        job_profile:  JD 要求画像
        user_profile: 用户画像
        match_result: matcher 的输出（含 matched_items）
    Returns:
        gaps list，每项含：
          type / requirement / current_state / suggestion / severity / status / need_confirm
        按严重度降序排列（critical → low）。
    """
    items = match_result.get("matched_items", [])
    base_gaps: List[Dict] = []
    # 只提取四分类（硬技能/软技能/隐性/红线）的差距；
    # 经验/学历维度的差距已通过 dimension_scores 体现，不重复进 Gap 清单。
    for it in items:
        if it.get("category") in ("hard_skill", "soft_skill", "implicit", "redline") \
                and it.get("status") in ("missing", "partial"):
            base_gaps.append({
                "type": it.get("category"),
                "requirement": it.get("requirement"),
                "current_state": it.get("profile_evidence") or "画像中未体现",
                "status": it.get("status"),
                "need_confirm": it.get("need_confirm", False),
                "severity": _severity_for(it.get("category", "")),
            })

    if not base_gaps:
        return []

    # LLM 生成建议（失败降级模板）
    suggestions = _generate_suggestions(base_gaps, user_profile, max_retries)
    for g, s in zip(base_gaps, suggestions):
        g["suggestion"] = s

    # 按严重度降序排列
    base_gaps.sort(
        key=lambda g: SEVERITY_ORDER.index(g["severity"]) if g["severity"] in SEVERITY_ORDER else 99
    )

    return base_gaps
